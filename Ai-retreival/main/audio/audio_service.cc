#include "audio_service.h"
#include "board_pins.h"
#include <esp_log.h>
#include <driver/gpio.h>
#include <esp_heap_caps.h>
#include <cmath>
#include <cstring>
#include <vector>

#define TAG "AudioService"

AudioService::AudioService(AudioCodec* codec) : codec_(codec) {
    engine_ = std::make_unique<AfeAudioEngine>();
}

AudioService::~AudioService() {
    Stop();
    if (psram_record_buffer_) {
        free(psram_record_buffer_);
        psram_record_buffer_ = nullptr;
    }
}

bool AudioService::Initialize() {
    if (!codec_) {
        ESP_LOGE(TAG, "AudioCodec is null!");
        return false;
    }

    if (!engine_->Initialize(codec_)) {
        ESP_LOGE(TAG, "Gagal inisialisasi AFE Audio Engine!");
        return false;
    }

    // Alokasi buffer rekaman di PSRAM Octal 8MB (256 KB)
    if (!psram_record_buffer_) {
        psram_record_buffer_ = (int16_t*)heap_caps_malloc(
            kMaxRecordSamples * sizeof(int16_t),
            MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
        if (!psram_record_buffer_) {
            ESP_LOGW(TAG, "Alokasi PSRAM gagal, mencoba heap internal...");
            psram_record_buffer_ = (int16_t*)malloc(kMaxRecordSamples * sizeof(int16_t));
        }
        if (psram_record_buffer_) {
            ESP_LOGI(TAG, "Buffer rekaman suara siap (%u bytes di PSRAM).",
                     (unsigned)(kMaxRecordSamples * sizeof(int16_t)));
        } else {
            ESP_LOGE(TAG, "Gagal alokasi buffer rekaman suara!");
            return false;
        }
    }

    // Hook output clean audio dari AFE untuk ditampung ke buffer rekaman saat LISTENING
    engine_->OnOutput([this](std::vector<int16_t>&& chunk) {
        if (state_ == AudioState::LISTENING && is_recording_) {
            std::lock_guard<std::mutex> lock(record_mutex_);
            size_t remaining = kMaxRecordSamples - recorded_sample_count_;
            size_t to_copy = (chunk.size() < remaining) ? chunk.size() : remaining;

            if (to_copy > 0 && psram_record_buffer_) {
                memcpy(psram_record_buffer_ + recorded_sample_count_, chunk.data(), to_copy * sizeof(int16_t));
                recorded_sample_count_ += to_copy;
            }

            if (recorded_sample_count_ >= kMaxRecordSamples) {
                is_recording_ = false;
                ESP_LOGI(TAG, "Perekaman mencapai batas maksimal (8 detik).");
                SetState(AudioState::THINKING);
                if (speech_recorded_cb_) {
                    speech_recorded_cb_(psram_record_buffer_, recorded_sample_count_);
                }
            }
        }
    });

    // Teruskan event WakeNet
    engine_->OnWakeWordDetected([this](const std::string& wake_word) {
        if (state_ == AudioState::IDLE) {
            ESP_LOGI(TAG, ">>> EVENT: WakeNet Trigger '%s' <<<", wake_word.c_str());
            if (wake_word_cb_) {
                wake_word_cb_(wake_word);
            }
        }
    });

    // Teruskan event VAD
    engine_->OnVadStateChange([this](bool speaking) {
        if (state_ == AudioState::LISTENING) {
            if (vad_cb_) {
                vad_cb_(speaking);
            }
        }
    });

    codec_->EnableInput(true);
    codec_->EnableOutput(true);

    SetState(AudioState::IDLE);
    ESP_LOGI(TAG, "AudioService initialized successfully in IDLE mode.");
    return true;
}

void AudioService::Start() {
    if (running_) return;
    running_ = true;

    // Jalankan input task di Core 1
    xTaskCreatePinnedToCore([](void* arg) {
        auto* service = static_cast<AudioService*>(arg);
        service->InputLoop();
        vTaskDelete(nullptr);
    }, "audio_input", 4096, this, 5, &input_task_, 1);

    ESP_LOGI(TAG, "AudioService InputTask started on Core 1.");
}

void AudioService::Stop() {
    running_ = false;
    if (input_task_) {
        vTaskDelay(pdMS_TO_TICKS(50));
        input_task_ = nullptr;
    }
}

void AudioService::SetState(AudioState state) {
    state_ = state;
    switch (state) {
        case AudioState::IDLE:
            ESP_LOGI(TAG, "[STATE] -> IDLE: Siaga mendengarkan 'Hi ESP'...");
            engine_->EnableWakeWordDetection(true);
            engine_->EnableVoiceProcessing(false);
            engine_->ResetVadState();
            ClearRecordedData();
            break;

        case AudioState::LISTENING:
            ESP_LOGI(TAG, "[STATE] -> LISTENING: Merekam pertanyaan user...");
            engine_->EnableWakeWordDetection(false);
            engine_->EnableVoiceProcessing(true);
            engine_->ResetVadState();
            StartRecording();
            break;

        case AudioState::THINKING:
            ESP_LOGI(TAG, "[STATE] -> THINKING: Mengirim ke AI server...");
            engine_->EnableWakeWordDetection(false);
            engine_->EnableVoiceProcessing(false);
            is_recording_ = false;
            break;

        case AudioState::SPEAKING:
            ESP_LOGI(TAG, "[STATE] -> SPEAKING: Memutar suara TTS...");
            engine_->EnableWakeWordDetection(false);
            engine_->EnableVoiceProcessing(false);
            is_recording_ = false;
            break;
    }
}

void AudioService::StartRecording() {
    std::lock_guard<std::mutex> lock(record_mutex_);
    recorded_sample_count_ = 0;
    is_recording_ = true;
    ESP_LOGI(TAG, "[AUDIO] Memulai perekaman pertanyaan ke PSRAM...");
}

void AudioService::StopRecording() {
    std::lock_guard<std::mutex> lock(record_mutex_);
    if (!is_recording_) return;
    is_recording_ = false;
    ESP_LOGI(TAG, "[AUDIO] Perekaman selesai. Total sample: %u (%.2f detik).",
             (unsigned)recorded_sample_count_,
             (float)recorded_sample_count_ / 16000.0f);

    if (speech_recorded_cb_ && recorded_sample_count_ > 0) {
        speech_recorded_cb_(psram_record_buffer_, recorded_sample_count_);
    }
}

void AudioService::ClearRecordedData() {
    std::lock_guard<std::mutex> lock(record_mutex_);
    recorded_sample_count_ = 0;
    is_recording_ = false;
}

void AudioService::SetWakeWordCallback(std::function<void(const std::string&)> cb) {
    wake_word_cb_ = std::move(cb);
}

void AudioService::SetVadCallback(std::function<void(bool)> cb) {
    vad_cb_ = std::move(cb);
}

void AudioService::SetSpeechRecordedCallback(std::function<void(const int16_t* data, size_t count)> cb) {
    speech_recorded_cb_ = std::move(cb);
}

void AudioService::PlayTone(int freq_hz, int duration_ms) {
    if (!codec_) return;
    gpio_set_level(AUDIO_I2S_SPK_GPIO_SD, 1);
    vTaskDelay(pdMS_TO_TICKS(10)); // Jeda unmute amplifier

    constexpr int kSampleRate = 16000;
    int num_samples = (kSampleRate * duration_ms) / 1000;
    std::vector<int16_t> tone(num_samples);
    for (int i = 0; i < num_samples; i++) {
        float phase = 2.0f * M_PI * (float)freq_hz * (float)i / (float)kSampleRate;
        // Amplified sine wave with smooth attack/decay
        float envelope = 1.0f;
        if (i < 80) envelope = (float)i / 80.0f;
        else if (i > num_samples - 80) envelope = (float)(num_samples - i) / 80.0f;
        tone[i] = static_cast<int16_t>(std::sin(phase) * 16000.0f * envelope);
    }
    codec_->Write(tone.data(), tone.size());
    vTaskDelay(pdMS_TO_TICKS(20));
    gpio_set_level(AUDIO_I2S_SPK_GPIO_SD, 0); // Matikan amplifier kembali ke mode standby
}

void AudioService::PlayChime() {
    gpio_set_level(AUDIO_I2S_SPK_GPIO_SD, 1);
    vTaskDelay(pdMS_TO_TICKS(10));
    // 2-tone melodic greeting chime: 587 Hz (D5) -> 880 Hz (A5)
    PlayTone(587, 90);
    vTaskDelay(pdMS_TO_TICKS(20));
    PlayTone(880, 130);
    vTaskDelay(pdMS_TO_TICKS(10));
    gpio_set_level(AUDIO_I2S_SPK_GPIO_SD, 0);
}

void AudioService::InputLoop() {
    constexpr int kChunkSamples = 512;
    std::vector<int16_t> buffer(kChunkSamples);

    while (running_) {
        // Hanya feed audio ke engine saat tidak sedang memutar TTS di speaker
        if (state_ != AudioState::SPEAKING) {
            int read_samples = codec_->Read(buffer.data(), kChunkSamples);
            if (read_samples > 0) {
                std::vector<int16_t> chunk(buffer.begin(), buffer.begin() + read_samples);
                engine_->Feed(std::move(chunk));
            } else {
                vTaskDelay(pdMS_TO_TICKS(5));
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(15));
        }
    }
}
