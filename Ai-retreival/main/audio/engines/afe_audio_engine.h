#pragma once

#include "audio_engine.h"
#include <esp_afe_sr_iface.h>
#include <esp_afe_sr_models.h>
#include <esp_mn_models.h>
#include <esp_wn_iface.h>
#include <esp_wn_models.h>
#include <model_path.h>

#include <vector>
#include <string>
#include <functional>
#include <mutex>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <freertos/event_groups.h>

class AfeAudioEngine : public AudioEngine {
public:
    AfeAudioEngine();
    virtual ~AfeAudioEngine();

    virtual bool Initialize(AudioCodec* codec) override;
    virtual void Feed(std::vector<int16_t>&& data) override;
    virtual void EnableWakeWordDetection(bool enable) override;
    virtual void EnableVoiceProcessing(bool enable) override;

    virtual bool IsWakeWordDetectionEnabled() const override;
    virtual bool IsVoiceProcessingEnabled() const override;

    virtual void OnWakeWordDetected(std::function<void(const std::string& wake_word)> callback) override;
    virtual void OnVadStateChange(std::function<void(bool speaking)> callback) override;
    virtual void OnOutput(std::function<void(std::vector<int16_t>&& data)> callback) override;

    void ResetVadState();
    virtual const std::string& GetLastDetectedWakeWord() const override { return last_detected_wake_word_; }

private:
    AudioCodec* codec_ = nullptr;
    const esp_afe_sr_iface_t* afe_iface_ = nullptr;
    esp_afe_sr_data_t* afe_data_ = nullptr;
    srmodel_list_t* models_ = nullptr;

    TaskHandle_t processing_task_ = nullptr;
    EventGroupHandle_t event_group_ = nullptr;

    std::vector<std::string> wake_words_;
    std::string last_detected_wake_word_ = "Hi ESP";
    bool is_speaking_ = false;

    std::vector<int16_t> input_buffer_;
    std::mutex input_mutex_;

    std::function<void(const std::string& wake_word)> wake_word_callback_;
    std::function<void(bool speaking)> vad_callback_;
    std::function<void(std::vector<int16_t>&& data)> output_callback_;

    static constexpr EventBits_t kWakeWordEnabled        = (1 << 0);
    static constexpr EventBits_t kVoiceProcessingEnabled = (1 << 1);
    static constexpr EventBits_t kAfeActive              = (1 << 2);

    void ProcessingTask();
    void UpdateActiveState();
    void ApplyAfeControls();
};
