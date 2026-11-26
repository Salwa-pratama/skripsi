#include "audio_codec.h"
#include <esp_log.h>

#define TAG "AudioCodec"

AudioCodec::AudioCodec() {}

AudioCodec::~AudioCodec() {}

void AudioCodec::OutputData(const std::vector<int16_t>& data) {
    Write(data.data(), data.size());
}

bool AudioCodec::InputData(std::vector<int16_t>& data) {
    int samples = Read(data.data(), data.size());
    return samples > 0;
}

void AudioCodec::Start() {
    ESP_LOGI(TAG, "Audio codec started (Volume: %d%%)", output_volume_);
}

void AudioCodec::SetOutputVolume(int volume) {
    if (volume < 0) volume = 0;
    if (volume > 100) volume = 100;
    output_volume_ = volume;
    ESP_LOGI(TAG, "Set output volume to %d%%", output_volume_);
}

void AudioCodec::SetInputGain(float gain) {
    input_gain_ = gain;
    ESP_LOGI(TAG, "Set input gain to %.1f dB", input_gain_);
}

void AudioCodec::EnableInput(bool enable) {
    if (enable == input_enabled_) return;
    input_enabled_ = enable;
    ESP_LOGI(TAG, "Input %s", enable ? "enabled" : "disabled");
}

void AudioCodec::EnableOutput(bool enable) {
    if (enable == output_enabled_) return;
    output_enabled_ = enable;
    ESP_LOGI(TAG, "Output %s", enable ? "enabled" : "disabled");
}
