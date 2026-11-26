#pragma once

#include <esp_wn_iface.h>
#include <esp_wn_models.h>
#include <model_path.h>

#include <string>
#include <vector>
#include <functional>
#include <atomic>
#include <mutex>

#include "audio_codec.h"
#include "wake_word.h"

class EspWakeWord : public WakeWord {
public:
    EspWakeWord();
    virtual ~EspWakeWord();

    virtual bool Initialize(AudioCodec* codec, srmodel_list_t* models_list) override;
    virtual void Feed(const std::vector<int16_t>& data) override;
    virtual void OnWakeWordDetected(std::function<void(const std::string& wake_word)> callback) override;
    virtual void Start() override;
    virtual void Stop() override;
    virtual size_t GetFeedSize() override;
    virtual const std::string& GetLastDetectedWakeWord() const override { return last_detected_wake_word_; }

private:
    esp_wn_iface_t* wakenet_iface_ = nullptr;
    model_iface_data_t* wakenet_data_ = nullptr;
    srmodel_list_t* wakenet_model_ = nullptr;
    bool owns_models_ = false;
    AudioCodec* codec_ = nullptr;
    std::atomic<bool> running_ = false;

    std::function<void(const std::string& wake_word)> wake_word_detected_callback_;
    std::string last_detected_wake_word_ = "Hi ESP";
    std::vector<int16_t> input_buffer_;
    std::mutex input_buffer_mutex_;
};
