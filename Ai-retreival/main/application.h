#pragma once

#include <freertos/FreeRTOS.h>
#include <freertos/event_groups.h>
#include <freertos/task.h>
#include <freertos/queue.h>
#include <esp_timer.h>

#include <string>
#include <memory>
#include <deque>
#include <mutex>
#include <functional>

#include "device_state.h"
#include "device_state_machine.h"
#include "boards/asisten_belajar_board.h"
#include "display/robot_face_display.h"
#include "audio/audio_service.h"
#include "network/wifi_manager.h"
#include "network/backend_client.h"

// FreeRTOS Main Event Bits (Mengadopsi pola event Xiaozhi)
#define MAIN_EVENT_SCHEDULE             (1 << 0)
#define MAIN_EVENT_NETWORK_CONNECTED    (1 << 1)
#define MAIN_EVENT_NETWORK_DISCONNECTED (1 << 2)
#define MAIN_EVENT_WAKE_WORD_DETECTED   (1 << 3)
#define MAIN_EVENT_VAD_CHANGE           (1 << 4)
#define MAIN_EVENT_SEND_AUDIO           (1 << 5)
#define MAIN_EVENT_STATE_CHANGED        (1 << 6)
#define MAIN_EVENT_PLAYBACK_DRAINED     (1 << 7)
#define MAIN_EVENT_CLOCK_TICK           (1 << 8)

class Application {
public:
    static Application& GetInstance() {
        static Application instance;
        return instance;
    }

    Application(const Application&) = delete;
    Application& operator=(const Application&) = delete;

    void Initialize();
    void Run();

    DeviceState GetDeviceState() const { return state_machine_.GetState(); }
    bool SetDeviceState(DeviceState state);

    void Schedule(std::function<void()>&& callback);

    AudioService* GetAudioService() { return audio_service_.get(); }
    RobotFaceDisplay* GetDisplay() { return display_.get(); }
    AsistenBelajarBoard* GetBoard() { return &board_; }

private:
    Application();
    ~Application();

    std::mutex mutex_;
    EventGroupHandle_t event_group_ = nullptr;
    std::deque<std::function<void()>> scheduled_tasks_;

    DeviceStateMachine state_machine_;

    AsistenBelajarBoard board_;
    std::unique_ptr<RobotFaceDisplay> display_;
    std::unique_ptr<AudioService> audio_service_;
    std::unique_ptr<BackendClient> backend_;

    struct VoiceJob {
        const int16_t* pcm_data;
        size_t sample_count;
    };
    QueueHandle_t voice_queue_ = nullptr;
    TaskHandle_t voice_worker_task_ = nullptr;

    bool last_vad_speaking_ = false;
    std::string last_detected_wake_word_ = "Hi ESP";
    esp_timer_handle_t pomodoro_timer_ = nullptr;

    void HandleNetworkConnected();
    void HandleNetworkDisconnected();
    void HandleWakeWordDetected();
    void HandleVadChange();
    void HandleSendAudio();
    void HandleStateChanged(DeviceState old_state, DeviceState new_state);
    void HandlePlaybackDrained();

    static void VoiceWorkerTask(void* arg);
};
