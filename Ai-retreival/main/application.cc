#include "application.h"
#include <esp_log.h>
#include <esp_system.h>
#include <esp_psram.h>
#include "board_pins.h"
#include "network/network_config.h"

#define TAG "Application"

Application::Application() {
    event_group_ = xEventGroupCreate();
    voice_queue_ = xQueueCreate(2, sizeof(VoiceJob));
    backend_ = std::make_unique<BackendClient>(BACKEND_SERVER_HOST, BACKEND_SERVER_PORT);
}

Application::~Application() {
    if (pomodoro_timer_) {
        esp_timer_stop(pomodoro_timer_);
        esp_timer_delete(pomodoro_timer_);
    }
    if (voice_queue_) {
        vQueueDelete(voice_queue_);
    }
    if (event_group_) {
        vEventGroupDelete(event_group_);
    }
}

bool Application::SetDeviceState(DeviceState state) {
    return state_machine_.TransitionTo(state);
}

void Application::Schedule(std::function<void()>&& callback) {
    {
        std::lock_guard<std::mutex> lock(mutex_);
        scheduled_tasks_.push_back(std::move(callback));
    }
    xEventGroupSetBits(event_group_, MAIN_EVENT_SCHEDULE);
}

void Application::Initialize() {
    ESP_LOGI(TAG, "==========================================================");
    ESP_LOGI(TAG, "  ASISTEN BELAJAR AI - XIAOZHI S3 ARCHITECTURE & BACKEND  ");
    ESP_LOGI(TAG, "==========================================================");

    // 1. Info Memori (PSRAM Octal 8MB)
    size_t psram_size = esp_psram_get_size();
    size_t psram_free = heap_caps_get_free_size(MALLOC_CAP_SPIRAM);
    ESP_LOGI(TAG, "Memori Sistem: PSRAM Total %u bytes (%.1f MB) | Free %u bytes",
             (unsigned)psram_size, (float)psram_size / (1024.0f * 1024.0f), (unsigned)psram_free);

    SetDeviceState(kDeviceStateStarting);

    // 2. Inisialisasi Abstraksi Board (GPIO & I2S Duplex)
    board_.Initialize();
    SingleLed* led = board_.GetLed();
    if (led) {
        led->SetColor(0, 0, 16); // Biru (Booting)
        led->TurnOn();
    }

    // 3. Inisialisasi Display OLED Robot Face (Mochi Eyes) di Core 0
    ESP_LOGI(TAG, "Inisialisasi OLED Wajah Robot SSD1306 (SDA=%d, SCL=%d)...",
             DISPLAY_SDA_PIN, DISPLAY_SCL_PIN);
    display_ = std::make_unique<RobotFaceDisplay>(DISPLAY_SDA_PIN, DISPLAY_SCL_PIN);
    if (display_->Initialize()) {
        display_->Start();
        display_->SetEmotion(RobotEmotion::NORMAL);
        display_->ShowText("Booting Asisten AI...", 2000, "SYSTEM:");
    }

    // 4. Inisialisasi Audio Subsystem & ESP-SR Neural Network di Core 1
    ESP_LOGI(TAG, "Inisialisasi AudioService & ESP-SR Neural Engine di Core 1...");
    audio_service_ = std::make_unique<AudioService>(board_.GetAudioCodec());

    audio_service_->SetWakeWordCallback([this](const std::string& wake_word) {
        last_detected_wake_word_ = wake_word;
        xEventGroupSetBits(event_group_, MAIN_EVENT_WAKE_WORD_DETECTED);
    });

    audio_service_->SetVadCallback([this](bool speaking) {
        last_vad_speaking_ = speaking;
        xEventGroupSetBits(event_group_, MAIN_EVENT_VAD_CHANGE);
    });

    audio_service_->SetSpeechRecordedCallback([this](const int16_t* data, size_t count) {
        VoiceJob job = {
            .pcm_data = data,
            .sample_count = count,
        };
        xQueueSend(voice_queue_, &job, 0);
        xEventGroupSetBits(event_group_, MAIN_EVENT_SEND_AUDIO);
    });

    if (audio_service_->Initialize()) {
        audio_service_->Start();
        // Nada startup siap
        audio_service_->PlayTone(440, 60);
        vTaskDelay(pdMS_TO_TICKS(30));
        audio_service_->PlayTone(659, 90);
        ESP_LOGI(TAG, "Audio Service & ESP-SR AFE aktif berjalan.");
    } else {
        ESP_LOGE(TAG, "Gagal menginisialisasi Audio Service!");
    }

    // 5. Observer Perubahan Status Perangkat
    state_machine_.AddStateChangeListener([this](DeviceState old_state, DeviceState new_state) {
        HandleStateChanged(old_state, new_state);
    });

    // 6. Buat Task Pekerja Voice di Core 0
    xTaskCreatePinnedToCore(VoiceWorkerTask, "voice_worker", 8192, this, 4, &voice_worker_task_, 0);

    // 7. Mulai Koneksi Jaringan WiFi Secara Asinkron (Non-Blocking)
    if (display_) {
        display_->ShowText("Menghubungkan WiFi...", 0, "NETWORK:");
    }
    auto& wifi = WifiManager::GetInstance();
    wifi.SetConnectedCallback([this](const std::string& ip) {
        xEventGroupSetBits(event_group_, MAIN_EVENT_NETWORK_CONNECTED);
    });
    wifi.SetDisconnectedCallback([this]() {
        xEventGroupSetBits(event_group_, MAIN_EVENT_NETWORK_DISCONNECTED);
    });
    wifi.StartNetwork(DEFAULT_WIFI_SSID, DEFAULT_WIFI_PASSWORD);

    // 8. Masuk ke State IDLE Standby
    SetDeviceState(kDeviceStateIdle);

    ESP_LOGI(TAG, "==========================================================");
    ESP_LOGI(TAG, "  SISTEM AKTIF: Panggil 'Hi ESP' untuk memicu robot!      ");
    ESP_LOGI(TAG, "==========================================================");
}

void Application::Run() {
    vTaskPrioritySet(nullptr, 10);

    const EventBits_t ALL_EVENTS =
        MAIN_EVENT_SCHEDULE | MAIN_EVENT_NETWORK_CONNECTED |
        MAIN_EVENT_NETWORK_DISCONNECTED | MAIN_EVENT_WAKE_WORD_DETECTED |
        MAIN_EVENT_VAD_CHANGE | MAIN_EVENT_SEND_AUDIO |
        MAIN_EVENT_PLAYBACK_DRAINED | MAIN_EVENT_CLOCK_TICK;

    while (true) {
        auto bits = xEventGroupWaitBits(event_group_, ALL_EVENTS, pdTRUE, pdFALSE, portMAX_DELAY);

        if (bits & MAIN_EVENT_SCHEDULE) {
            std::function<void()> task;
            while (true) {
                {
                    std::lock_guard<std::mutex> lock(mutex_);
                    if (scheduled_tasks_.empty()) break;
                    task = std::move(scheduled_tasks_.front());
                    scheduled_tasks_.pop_front();
                }
                if (task) task();
            }
        }

        if (bits & MAIN_EVENT_NETWORK_CONNECTED) {
            HandleNetworkConnected();
        }

        if (bits & MAIN_EVENT_NETWORK_DISCONNECTED) {
            HandleNetworkDisconnected();
        }

        if (bits & MAIN_EVENT_WAKE_WORD_DETECTED) {
            HandleWakeWordDetected();
        }

        if (bits & MAIN_EVENT_VAD_CHANGE) {
            HandleVadChange();
        }

        if (bits & MAIN_EVENT_SEND_AUDIO) {
            HandleSendAudio();
        }

        if (bits & MAIN_EVENT_PLAYBACK_DRAINED) {
            HandlePlaybackDrained();
        }
    }
}

void Application::HandleNetworkConnected() {
    std::string ip = WifiManager::GetInstance().GetIpAddress();
    ESP_LOGI(TAG, "Event: WiFi Terhubung! IP: %s", ip.c_str());
    if (display_) {
        display_->ShowText("WiFi OK: " + ip, 3000, "NETWORK:");
    }
    SingleLed* led = board_.GetLed();
    if (led && GetDeviceState() == kDeviceStateIdle) {
        led->SetColor(0, 16, 0); // Hijau lembut standby
        led->TurnOn();
    }
}

void Application::HandleNetworkDisconnected() {
    ESP_LOGW(TAG, "Event: WiFi Terputus.");
    if (display_) {
        display_->ShowText("WiFi Terputus!", 3000, "NETWORK:");
    }
    SingleLed* led = board_.GetLed();
    if (led && GetDeviceState() == kDeviceStateIdle) {
        led->SetColor(24, 16, 0); // Kuning peringatan
        led->TurnOn();
    }
}

void Application::HandleWakeWordDetected() {
    if (GetDeviceState() != kDeviceStateIdle) {
        return;
    }
    ESP_LOGI(TAG, ">>> EVENT: Wake Word '%s' Terdeteksi! <<<", last_detected_wake_word_.c_str());

    SetDeviceState(kDeviceStateListening);

    if (display_) {
        display_->SetEmotion(RobotEmotion::LISTENING, 10000);
        display_->ShowText("Hai! Ada yang bisa dibantu?", 2500, "VOICE AI:");
    }

    if (audio_service_) {
        audio_service_->PlayChime();
        audio_service_->SetState(AudioState::LISTENING);
    }
}

void Application::HandleVadChange() {
    if (GetDeviceState() != kDeviceStateListening) {
        return;
    }

    if (last_vad_speaking_) {
        ESP_LOGI(TAG, ">>> EVENT: Pengguna Mulai Bicara (VAD_SPEECH) <<<");
        if (display_) {
            display_->SetEmotion(RobotEmotion::LISTENING);
        }
        SingleLed* led = board_.GetLed();
        if (led) {
            led->SetColor(0, 24, 0); // Hijau aktif merekam
            led->TurnOn();
        }
    } else {
        ESP_LOGI(TAG, ">>> EVENT: Pengguna Selesai Bicara (VAD_SILENCE) <<<");
        if (audio_service_) {
            if (audio_service_->GetRecordedCount() >= 8000) { // >= 0.5 detik
                SetDeviceState(kDeviceStateThinking);
                audio_service_->SetState(AudioState::THINKING);
                audio_service_->StopRecording();
            } else {
                // Terlalu pendek (noise batuk / nafas sekejap), abaikan
                audio_service_->ClearRecordedData();
                SetDeviceState(kDeviceStateIdle);
                audio_service_->SetState(AudioState::IDLE);
            }
        }
    }
}

void Application::HandleSendAudio() {
    // Worker task yang akan mengambil data dari voice_queue_
}

void Application::HandlePlaybackDrained() {
    ESP_LOGI(TAG, "Playback drained, returning to Idle state.");
    SetDeviceState(kDeviceStateIdle);
    if (audio_service_) {
        audio_service_->SetState(AudioState::IDLE);
    }
}

void Application::HandleStateChanged(DeviceState old_state, DeviceState new_state) {
    SingleLed* led = board_.GetLed();

    switch (new_state) {
        case kDeviceStateStarting:
            if (led) {
                led->SetColor(0, 0, 16); // Biru boot
                led->TurnOn();
            }
            break;

        case kDeviceStateIdle:
            if (display_) {
                display_->SetEmotion(RobotEmotion::NORMAL);
            }
            if (led) {
                if (WifiManager::GetInstance().IsConnected()) {
                    led->SetColor(0, 16, 0); // Hijau lembut standby
                } else {
                    led->SetColor(24, 16, 0); // Kuning no-wifi
                }
                led->TurnOn();
            }
            break;

        case kDeviceStateListening:
            if (led) {
                led->SetColor(24, 20, 0); // Kuning emas
                led->TurnOn();
            }
            break;

        case kDeviceStateThinking:
            if (led) {
                led->SetColor(0, 0, 32); // Biru terang
                led->TurnOn();
            }
            break;

        case kDeviceStateSpeaking:
            if (led) {
                led->SetColor(0, 24, 24); // Cyan berbicara
                led->TurnOn();
            }
            break;

        case kDeviceStateFatalError:
            if (led) {
                led->SetColor(32, 0, 0); // Merah
                led->TurnOn();
            }
            break;

        default:
            break;
    }
}

void Application::VoiceWorkerTask(void* arg) {
    auto* app = static_cast<Application*>(arg);
    VoiceJob job;

    while (true) {
        if (xQueueReceive(app->voice_queue_, &job, portMAX_DELAY) == pdTRUE) {
            // 1. Visual OLED: Mode Berpikir
            if (app->display_) {
                app->display_->SetEmotion(RobotEmotion::THINKING, 60000);
                app->display_->ShowText("Mengirim ke AI server...", 0, "AI:");
            }

            // 2. Unggah audio pertanyaan ke backend POST /api/ai/voice
            VoiceResponse response;
            bool ok = app->backend_->UploadVoice(job.pcm_data, job.sample_count, response);

            if (ok && response.success) {
                ESP_LOGI(TAG, "STT Transkrip: \"%s\"", response.transcript.c_str());
                ESP_LOGI(TAG, "Jawaban AI    : \"%s\"", response.answer.c_str());
                ESP_LOGI(TAG, "Confidence    : %.3f | Matched: %s",
                         response.confidence, response.matched ? "YA" : "TIDAK");

                // Susun teks bergulir marquee: "Kamu: <tanya> >>> AI: <jawab>"
                std::string scroll_text;
                if (!response.transcript.empty() && response.transcript != "(suara tidak terdeteksi)") {
                    scroll_text = "Kamu: \"" + response.transcript + "\"  >>>  AI: " + response.display_text;
                } else {
                    scroll_text = response.display_text;
                }

                if (app->display_) {
                    app->display_->ShowText(scroll_text, 0, "VOICE AI:");
                }

                // 3. Putar audio streaming jawaban TTS dari server ke speaker MAX98357A
                if (!response.audio_wav_url.empty()) {
                    app->SetDeviceState(kDeviceStateSpeaking);
                    app->board_.SetAmplifierPower(true);
                    vTaskDelay(pdMS_TO_TICKS(15)); // Jeda unmute
                    if (app->audio_service_) {
                        app->audio_service_->SetState(AudioState::SPEAKING);
                    }
                    if (app->display_) {
                        app->display_->SetEmotion(RobotEmotion::SPEAKING, 60000);
                    }

                    app->backend_->StreamPlayAudio(response.audio_wav_url, app->board_.GetAudioCodec());
                    app->board_.SetAmplifierPower(false); // Matikan amplifier kembali ke mode standby
                }

                // 4. Periksa apakah hanya wake word pemicu awal ("Hi ESP")
                if (response.is_wake_word_only) {
                    ESP_LOGI(TAG, "Wake word greeting selesai, otomatis mendengarkan pertanyaan...");
                    if (app->display_) {
                        app->display_->SetEmotion(RobotEmotion::LISTENING, 10000);
                        app->display_->ShowText("Silakan bertanya...", 3000, "VOICE AI:");
                    }
                    app->SetDeviceState(kDeviceStateListening);
                    if (app->audio_service_) {
                        app->audio_service_->PlayChime();
                        app->audio_service_->SetState(AudioState::LISTENING);
                    }
                } else {
                    // Beri jeda membaca teks marquee sebelum kembali siaga (looping)
                    vTaskDelay(pdMS_TO_TICKS(4000));
                    app->SetDeviceState(kDeviceStateIdle);
                    if (app->audio_service_) {
                        app->audio_service_->SetState(AudioState::IDLE);
                    }
                }

            } else {
                ESP_LOGW(TAG, "Gagal mendapatkan jawaban dari backend AI!");
                if (app->display_) {
                    app->display_->SetEmotion(RobotEmotion::CONFUSED, 4000);
                    app->display_->ShowText("Gagal terhubung server!", 4000, "ERROR:");
                }
                if (app->audio_service_) {
                    app->audio_service_->PlayTone(300, 250);
                }
                vTaskDelay(pdMS_TO_TICKS(3000));
                app->SetDeviceState(kDeviceStateIdle);
                if (app->audio_service_) {
                    app->audio_service_->SetState(AudioState::IDLE);
                }
            }
        }
    }
}
