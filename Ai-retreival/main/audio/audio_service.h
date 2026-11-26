#pragma once

#include "audio_codec.h"
#include "audio_engine.h"
#include "engines/afe_audio_engine.h"
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <memory>
#include <functional>
#include <mutex>
#include <vector>

enum class AudioState {
    IDLE,       // Standby: Hanya WakeNet ("Hi ESP") yang aktif. Perekaman VAD OFF.
    LISTENING,  // Merekam pertanyaan user: WakeNet pause, Neural VAD & PSRAM buffer ON.
    THINKING,   // Selesai merekam, mengirim ke AI backend. Perekaman OFF.
    SPEAKING    // Memutar suara TTS di speaker. Mic dipause untuk cegah feedback.
};

class AudioService {
public:
    AudioService(AudioCodec* codec);
    ~AudioService();

    bool Initialize();
    void Start();
    void Stop();

    void SetState(AudioState state);
    AudioState GetState() const { return state_; }

    void SetWakeWordCallback(std::function<void(const std::string&)> cb);
    void SetVadCallback(std::function<void(bool)> cb);
    void SetSpeechRecordedCallback(std::function<void(const int16_t* data, size_t count)> cb);

    // Kontrol Perekaman Suara ke PSRAM Octal 8MB
    void StartRecording();
    void StopRecording();
    void ClearRecordedData();
    bool IsRecording() const { return is_recording_; }
    const int16_t* GetRecordedData() const { return psram_record_buffer_; }
    size_t GetRecordedCount() const { return recorded_sample_count_; }

    void PlayTone(int freq_hz, int duration_ms);
    void PlayChime();

    AudioEngine* GetEngine() { return engine_.get(); }
    AudioCodec* GetCodec() { return codec_; }

private:
    AudioCodec* codec_ = nullptr;
    std::unique_ptr<AfeAudioEngine> engine_;
    TaskHandle_t input_task_ = nullptr;
    bool running_ = false;

    AudioState state_ = AudioState::IDLE;

    // Buffer Rekaman Suara di PSRAM (8 detik x 16 kHz = 128.000 samples = 256 KB)
    static constexpr size_t kMaxRecordSamples = 16000 * 8;
    int16_t* psram_record_buffer_ = nullptr;
    size_t recorded_sample_count_ = 0;
    bool is_recording_ = false;
    std::mutex record_mutex_;

    std::function<void(const std::string&)> wake_word_cb_;
    std::function<void(bool)> vad_cb_;
    std::function<void(const int16_t* data, size_t count)> speech_recorded_cb_;

    void InputLoop();
};
