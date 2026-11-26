#include "afe_audio_engine.h"
#include <esp_log.h>
#include <cstring>
#include <sstream>

#define TAG "AfeAudioEngine"

AfeAudioEngine::AfeAudioEngine() {
    event_group_ = xEventGroupCreate();
}

AfeAudioEngine::~AfeAudioEngine() {
    if (processing_task_) {
        vTaskDelete(processing_task_);
        processing_task_ = nullptr;
    }
    if (afe_data_ && afe_iface_) {
        afe_iface_->destroy(afe_data_);
        afe_data_ = nullptr;
    }
    if (models_) {
        esp_srmodel_deinit(models_);
        models_ = nullptr;
    }
    if (event_group_) {
        vEventGroupDelete(event_group_);
    }
}

bool AfeAudioEngine::Initialize(AudioCodec* codec) {
    codec_ = codec;
    if (!codec_) {
        ESP_LOGE(TAG, "Codec is null!");
        return false;
    }

    // 1. Inisialisasi Model Neural Network dari Partisi Flash 'model'
    models_ = esp_srmodel_init("model");
    if (!models_) {
        ESP_LOGW(TAG, "esp_srmodel_init('model') null, mencoba partisi default NULL...");
        models_ = esp_srmodel_init(NULL);
    }

    char* wakenet_model_name = nullptr;
    if (models_ && models_->num > 0) {
        wakenet_model_name = esp_srmodel_filter(models_, ESP_WN_PREFIX, nullptr);
        for (int i = 0; i < models_->num; i++) {
            ESP_LOGI(TAG, "SR Model terdeteksi [%d]: %s", i, models_->model_name[i]);
        }
    }

    if (wakenet_model_name) {
        auto words = esp_srmodel_get_wake_words(models_, wakenet_model_name);
        if (words) {
            std::stringstream ss(words);
            std::string word;
            while (std::getline(ss, word, ';')) {
                wake_words_.push_back(word);
            }
            ESP_LOGI(TAG, "WakeNet Model Aktif: '%s' (Trigger Words: '%s')", wakenet_model_name, words);
        }
    } else {
        ESP_LOGW(TAG, "Tidak ada model WakeNet ditemukan di flash.");
        wake_words_.push_back("Hi ESP");
    }

    // 2. Konfigurasi ESP-AFE (Acoustic Front-End) untuk 1 mikrofon (input_format="M")
    char* vad_model_name = models_ == nullptr ? nullptr : esp_srmodel_filter(models_, ESP_VADN_PREFIX, nullptr);
    const char* input_format = "M"; // 1 microphone (INMP441)
    afe_config_t* afe_config = afe_config_init(input_format, models_, AFE_TYPE_VC, AFE_MODE_HIGH_PERF);
    if (!afe_config) {
        ESP_LOGE(TAG, "Gagal alokasi AFE config via afe_config_init!");
        return false;
    }

    afe_config->wakenet_init = (wakenet_model_name != nullptr);
    afe_config->wakenet_model_name = wakenet_model_name;
    afe_config->vad_init = true;
    afe_config->vad_mode = VAD_MODE_3; // Level 3 agresif membedakan bicara vs hening
    afe_config->vad_min_noise_ms = 100;
    if (vad_model_name != nullptr) {
        afe_config->vad_model_name = vad_model_name;
    }
    afe_config->memory_alloc_mode = AFE_MEMORY_ALLOC_MORE_PSRAM; // Alokasi di PSRAM Octal 8MB
    afe_config->ns_init = false;
    afe_config->aec_init = false;
    afe_config->agc_init = false;

    afe_iface_ = esp_afe_handle_from_config(afe_config);
    if (afe_iface_) {
        afe_data_ = afe_iface_->create_from_config(afe_config);
    }
    afe_config_free(afe_config);

    if (!afe_iface_ || !afe_data_) {
        ESP_LOGE(TAG, "Gagal membuat ESP-AFE instance!");
        return false;
    }

    afe_iface_->print_pipeline(afe_data_);

    // 3. Jalankan Task Inferensi AFE di Core 1
    BaseType_t res = xTaskCreatePinnedToCore([](void* arg) {
        auto* engine = static_cast<AfeAudioEngine*>(arg);
        engine->ProcessingTask();
        vTaskDelete(nullptr);
    }, "audio_afe", 6144, this, 4, &processing_task_, 1);

    if (res != pdPASS) {
        ESP_LOGE(TAG, "Gagal membuat task audio_afe di Core 1!");
        return false;
    }

    ESP_LOGI(TAG, "ESP-AFE Neural Engine siap di Core 1 (PSRAM mode).");

    // Default standby: hanya WakeNet yang aktif
    EnableWakeWordDetection(true);
    EnableVoiceProcessing(false);

    return true;
}

void AfeAudioEngine::Feed(std::vector<int16_t>&& data) {
    if (!afe_data_ || data.empty()) return;
    EventBits_t bits = xEventGroupGetBits(event_group_);
    if ((bits & kAfeActive) == 0) return;

    std::lock_guard<std::mutex> lock(input_mutex_);
    input_buffer_.insert(input_buffer_.end(), data.begin(), data.end());

    size_t chunk_size = afe_iface_->get_feed_chunksize(afe_data_);
    while (input_buffer_.size() >= chunk_size) {
        afe_iface_->feed(afe_data_, input_buffer_.data());
        input_buffer_.erase(input_buffer_.begin(), input_buffer_.begin() + chunk_size);
    }
}

void AfeAudioEngine::EnableWakeWordDetection(bool enable) {
    if (enable) {
        xEventGroupSetBits(event_group_, kWakeWordEnabled);
    } else {
        xEventGroupClearBits(event_group_, kWakeWordEnabled);
    }
    UpdateActiveState();
}

void AfeAudioEngine::EnableVoiceProcessing(bool enable) {
    if (enable) {
        xEventGroupSetBits(event_group_, kVoiceProcessingEnabled);
    } else {
        xEventGroupClearBits(event_group_, kVoiceProcessingEnabled);
        is_speaking_ = false;
    }
    UpdateActiveState();
}

void AfeAudioEngine::ResetVadState() {
    is_speaking_ = false;
    std::lock_guard<std::mutex> lock(input_mutex_);
    input_buffer_.clear();
}

bool AfeAudioEngine::IsWakeWordDetectionEnabled() const {
    return (xEventGroupGetBits(event_group_) & kWakeWordEnabled) != 0;
}

bool AfeAudioEngine::IsVoiceProcessingEnabled() const {
    return (xEventGroupGetBits(event_group_) & kVoiceProcessingEnabled) != 0;
}

void AfeAudioEngine::OnWakeWordDetected(std::function<void(const std::string& wake_word)> callback) {
    wake_word_callback_ = std::move(callback);
}

void AfeAudioEngine::OnVadStateChange(std::function<void(bool speaking)> callback) {
    vad_callback_ = std::move(callback);
}

void AfeAudioEngine::OnOutput(std::function<void(std::vector<int16_t>&& data)> callback) {
    output_callback_ = std::move(callback);
}

void AfeAudioEngine::UpdateActiveState() {
    EventBits_t bits = xEventGroupGetBits(event_group_);
    bool active = (afe_data_ != nullptr) && ((bits & kWakeWordEnabled) || (bits & kVoiceProcessingEnabled));
    if (active) {
        xEventGroupSetBits(event_group_, kAfeActive);
    } else {
        xEventGroupClearBits(event_group_, kAfeActive);
    }
    ApplyAfeControls();
}

void AfeAudioEngine::ApplyAfeControls() {
    if (!afe_data_ || !afe_iface_) return;
    EventBits_t bits = xEventGroupGetBits(event_group_);
    if (bits & kWakeWordEnabled) {
        afe_iface_->enable_wakenet(afe_data_);
    } else {
        afe_iface_->disable_wakenet(afe_data_);
    }
}

void AfeAudioEngine::ProcessingTask() {
    while (true) {
        xEventGroupWaitBits(event_group_, kAfeActive, pdFALSE, pdTRUE, portMAX_DELAY);
        if (!afe_data_ || !afe_iface_) {
            vTaskDelay(pdMS_TO_TICKS(10));
            continue;
        }

        afe_fetch_result_t* result = afe_iface_->fetch_with_delay(afe_data_, portMAX_DELAY);
        if (!result || result->ret_value == ESP_FAIL) {
            continue;
        }

        EventBits_t bits = xEventGroupGetBits(event_group_);

        // 1. Evaluasi Deteksi WakeNet ("Hi ESP")
        if ((bits & kWakeWordEnabled) && result->wakeup_state == WAKENET_DETECTED) {
            int model_idx = result->wakenet_model_index - 1;
            if (model_idx >= 0 && model_idx < (int)wake_words_.size()) {
                last_detected_wake_word_ = wake_words_[model_idx];
            } else if (!wake_words_.empty()) {
                last_detected_wake_word_ = wake_words_[0];
            } else {
                last_detected_wake_word_ = "Hi ESP";
            }

            ESP_LOGI(TAG, ">>> [WAKENET] Wake Word Terdeteksi: '%s' <<<", last_detected_wake_word_.c_str());
            if (wake_word_callback_) {
                wake_word_callback_(last_detected_wake_word_);
            }
        }

        // 2. Evaluasi Neural VAD (Deteksi Suara Bicara Manusia)
        if (bits & kVoiceProcessingEnabled) {
            if (result->vad_state == VAD_SPEECH && !is_speaking_) {
                is_speaking_ = true;
                ESP_LOGI(TAG, "[VAD] Pengguna Mulai Berbicara (VAD_SPEECH)");
                if (vad_callback_) vad_callback_(true);
            } else if (result->vad_state == VAD_SILENCE && is_speaking_) {
                is_speaking_ = false;
                ESP_LOGI(TAG, "[VAD] Pengguna Selesai Berbicara / Hening (VAD_SILENCE)");
                if (vad_callback_) vad_callback_(false);
            }

            // Salurkan Audio Output Bersih ke Buffer Perekaman
            if (output_callback_ && result->data && result->data_size > 0) {
                int samples = result->data_size / sizeof(int16_t);
                std::vector<int16_t> out_chunk(result->data, result->data + samples);
                output_callback_(std::move(out_chunk));
            }
        }
    }
}
