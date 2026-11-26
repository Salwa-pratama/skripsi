#include "esp_wake_word.h"
#include <esp_log.h>

#define TAG "EspWakeWord"

EspWakeWord::EspWakeWord() {}

EspWakeWord::~EspWakeWord() {
    if (wakenet_data_ != nullptr && wakenet_iface_ != nullptr) {
        wakenet_iface_->destroy(wakenet_data_);
        wakenet_data_ = nullptr;
    }
    if (owns_models_ && wakenet_model_ != nullptr) {
        esp_srmodel_deinit(wakenet_model_);
        wakenet_model_ = nullptr;
    }
}

bool EspWakeWord::Initialize(AudioCodec* codec, srmodel_list_t* models_list) {
    codec_ = codec;

    if (models_list == nullptr) {
        wakenet_model_ = esp_srmodel_init("model");
        owns_models_ = (wakenet_model_ != nullptr);
    } else {
        wakenet_model_ = models_list;
        owns_models_ = false;
    }

    if (wakenet_model_ == nullptr || wakenet_model_->num <= 0) {
        ESP_LOGE(TAG, "Model WakeNet tidak ditemukan di flash!");
        return false;
    }

    char* model_name = esp_srmodel_filter(wakenet_model_, ESP_WN_PREFIX, nullptr);
    if (model_name == nullptr) {
        ESP_LOGE(TAG, "Tidak ada model WakeNet berawalan ESP_WN_PREFIX!");
        return false;
    }

    wakenet_iface_ = (esp_wn_iface_t*)esp_wn_handle_from_name(model_name);
    if (wakenet_iface_ == nullptr) {
        ESP_LOGE(TAG, "Interface WakeNet tidak ditemukan untuk model: %s", model_name);
        return false;
    }

    wakenet_data_ = wakenet_iface_->create(model_name, DET_MODE_95);
    if (wakenet_data_ == nullptr) {
        ESP_LOGE(TAG, "Gagal membuat instance WakeNet %s!", model_name);
        return false;
    }

    int frequency = wakenet_iface_->get_samp_rate(wakenet_data_);
    int audio_chunksize = wakenet_iface_->get_samp_chunksize(wakenet_data_);
    ESP_LOGI(TAG, "EspWakeWord siap (%s): Freq %d Hz, Chunksize %d samples",
             model_name, frequency, audio_chunksize);

    return true;
}

void EspWakeWord::OnWakeWordDetected(std::function<void(const std::string& wake_word)> callback) {
    wake_word_detected_callback_ = std::move(callback);
}

void EspWakeWord::Start() {
    running_ = true;
}

void EspWakeWord::Stop() {
    running_ = false;
    std::lock_guard<std::mutex> lock(input_buffer_mutex_);
    input_buffer_.clear();
}

void EspWakeWord::Feed(const std::vector<int16_t>& data) {
    if (wakenet_data_ == nullptr) return;

    std::lock_guard<std::mutex> lock(input_buffer_mutex_);
    if (!running_) return;

    input_buffer_.insert(input_buffer_.end(), data.begin(), data.end());

    int chunksize = wakenet_iface_->get_samp_chunksize(wakenet_data_);
    while (input_buffer_.size() >= static_cast<size_t>(chunksize)) {
        int res = wakenet_iface_->detect(wakenet_data_, input_buffer_.data());
        if (res > 0) {
            char* word_name = wakenet_iface_->get_word_name(wakenet_data_, res);
            last_detected_wake_word_ = word_name ? word_name : "Hi ESP";
            running_ = false;
            input_buffer_.clear();

            ESP_LOGI(TAG, ">>> [EspWakeWord] Wake Word Terdeteksi: '%s' <<<",
                     last_detected_wake_word_.c_str());

            if (wake_word_detected_callback_) {
                wake_word_detected_callback_(last_detected_wake_word_);
            }
            break;
        }
        input_buffer_.erase(input_buffer_.begin(), input_buffer_.begin() + chunksize);
    }
}

size_t EspWakeWord::GetFeedSize() {
    if (wakenet_data_ == nullptr) return 0;
    return wakenet_iface_->get_samp_chunksize(wakenet_data_);
}
