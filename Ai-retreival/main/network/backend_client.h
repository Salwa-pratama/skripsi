#pragma once

#include <string>
#include <vector>
#include <functional>
#include "audio_codec.h"
#include "network_config.h"

struct VoiceResponse {
    bool success = false;
    int status_code = 0;
    std::string question;
    std::string answer;
    std::string display_text;
    std::string audio_wav_url;
    std::string emotion = "NORMAL";
    std::string transcript;
    float confidence = 0.0f;
    bool matched = false;
    bool wake_word_detected = false;
    bool is_wake_word_only = false;
};

struct PomodoroState {
    bool success = false;
    std::string mode = "WORK";
    std::string status = "STOPPED";
    std::string time_str = "25:00";
    int time_left = 1500;
    std::string cycle_str = "1/4";
    std::string task = "Belajar";
    std::string emotion = "NORMAL";
    int focus = 100;
};

class BackendClient {
public:
    BackendClient(const std::string& host = BACKEND_SERVER_HOST, int port = BACKEND_SERVER_PORT);
    ~BackendClient() = default;

    void SetServer(const std::string& host, int port);

    // Upload rekaman WAV pertanyaan user ke POST /api/ai/voice
    bool UploadVoice(const int16_t* pcm_data, size_t sample_count, VoiceResponse& response);

    // Stream & putar file WAV dari GET /api/ai/audio/{filename} ke MAX98357A I2S
    bool StreamPlayAudio(const std::string& wav_url, AudioCodec* codec,
                         std::function<void()> on_start_playback = nullptr);

    // Ambil status ultra-ringkas Pomodoro dari GET /api/esp/pomodoro
    bool GetPomodoro(PomodoroState& state);

    // Cek kesiapan model server dari GET /api/health
    bool CheckHealth();

    std::string GetBaseUrl() const { return base_url_; }

private:
    std::string host_;
    int port_;
    std::string base_url_;

    static void WriteWavHeader(uint8_t* header, uint32_t data_bytes, uint32_t sample_rate = 16000,
                               uint16_t channels = 1, uint16_t bits_per_sample = 16);
};
