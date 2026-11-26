#include "robot_face_display.h"
#include <cmath>
#include <esp_log.h>
#include <esp_random.h>
#include <esp_timer.h>

#define TAG "RobotFace"

static inline uint32_t get_millis() {
    return (uint32_t)(esp_timer_get_time() / 1000ULL);
}

RobotFaceDisplay::RobotFaceDisplay(gpio_num_t sda_pin, gpio_num_t scl_pin)
    : driver_(sda_pin, scl_pin) {}

RobotFaceDisplay::~RobotFaceDisplay() {
    Stop();
}

bool RobotFaceDisplay::Initialize() {
    if (!driver_.Initialize()) {
        ESP_LOGE(TAG, "Failed to initialize SSD1306 driver");
        return false;
    }
    ESP_LOGI(TAG, "Robot Face Display initialized.");
    return true;
}

void RobotFaceDisplay::Start() {
    if (running_) return;
    running_ = true;

    // Pin rendering task to Core 0 with priority 2, keeping Core 1 dedicated to Audio & Neural AI
    xTaskCreatePinnedToCore([](void* arg) {
        auto* display = static_cast<RobotFaceDisplay*>(arg);
        display->RenderLoop();
        vTaskDelete(nullptr);
    }, "robot_face", 4096, this, 2, &render_task_, 0);

    ESP_LOGI(TAG, "Robot Face rendering task started on Core 0 (~30 FPS)");
}

void RobotFaceDisplay::Stop() {
    running_ = false;
    if (render_task_) {
        vTaskDelay(pdMS_TO_TICKS(50));
        render_task_ = nullptr;
    }
}

void RobotFaceDisplay::SetEmotion(RobotEmotion emotion, uint32_t duration_ms) {
    std::lock_guard<std::mutex> lock(mutex_);
    current_emotion_ = emotion;
    uint32_t now = get_millis();
    emotion_end_ms_ = (duration_ms > 0) ? (now + duration_ms) : 0;
}

void RobotFaceDisplay::ShowText(const std::string& text, uint32_t duration_ms, const std::string& label) {
    std::lock_guard<std::mutex> lock(mutex_);
    text_ = text;
    text_label_ = label;
    text_active_ = !text_.empty();
    uint32_t now = get_millis();
    text_start_ms_ = now;
    text_end_ms_ = (duration_ms > 0) ? (now + duration_ms) : 0;
}

void RobotFaceDisplay::ClearText() {
    std::lock_guard<std::mutex> lock(mutex_);
    text_active_ = false;
    text_.clear();
}

RobotEmotion RobotFaceDisplay::GetActiveEmotion() {
    std::lock_guard<std::mutex> lock(mutex_);
    uint32_t now = get_millis();
    if (emotion_end_ms_ > 0 && now >= emotion_end_ms_) {
        current_emotion_ = RobotEmotion::NORMAL;
        emotion_end_ms_ = 0;
    }
    return current_emotion_;
}

void RobotFaceDisplay::RenderLoop() {
    while (running_) {
        uint32_t now = get_millis();
        DrawFrame(now);
        driver_.Refresh();
        vTaskDelay(pdMS_TO_TICKS(33)); // ~30 FPS
    }
}

void RobotFaceDisplay::DrawFrame(uint32_t now) {
    driver_.Clear();

    RobotEmotion emotion = GetActiveEmotion();

    std::string active_text;
    std::string active_label;
    bool has_text = false;
    uint32_t text_start = 0;
    {
        std::lock_guard<std::mutex> lock(mutex_);
        if (text_active_ && text_end_ms_ > 0 && now >= text_end_ms_) {
            text_active_ = false;
        }
        has_text = text_active_;
        active_text = text_;
        active_label = text_label_;
        text_start = text_start_ms_;
    }

    // 1. Kedipan Alami (Blink Cycle: 2.8 .. 5.2 detik)
    if (emotion != RobotEmotion::SLEEP && emotion != RobotEmotion::HAPPY) {
        if (!is_blinking_ && now >= next_blink_ms_) {
            is_blinking_ = true;
            blink_start_ms_ = now;
            next_blink_ms_ = now + 2800 + (esp_random() % 2400);
        }
    } else {
        is_blinking_ = false;
    }

    // 2. Lirikan Alami (Glance Cycle)
    if (emotion == RobotEmotion::LISTENING) {
        current_glance_ = 0; // Tatapan fokus ke depan saat mendengarkan
    } else if (emotion == RobotEmotion::THINKING) {
        current_glance_ = 3; // Menatap ke atas saat berpikir
    } else if (!is_blinking_ && now >= next_glance_ms_) {
        uint32_t r = esp_random() % 100;
        if (r < 60) current_glance_ = 0;      // Center
        else if (r < 75) current_glance_ = 1; // Left
        else if (r < 90) current_glance_ = 2; // Right
        else current_glance_ = 3;             // Up
        next_glance_ms_ = now + 2200 + (esp_random() % 2600);
    }

    // 3. Offset Target Berdasarkan Lirikan
    float target_offset_x = 0.0f;
    float target_offset_y = 0.0f;
    float target_w = 30.0f;
    float target_h = 34.0f;
    float target_radius = 8.0f;

    switch (current_glance_) {
        case 1: target_offset_x = -6.0f; break; // Kiri
        case 2: target_offset_x = 6.0f;  break; // Kanan
        case 3: target_offset_y = -3.5f; break; // Atas
        default: break;
    }

    // Nafas halus (Breathing)
    if (emotion != RobotEmotion::SLEEP) {
        float breath = std::sin((float)now * 0.0032f) * 1.2f;
        target_offset_y += breath;
    }

    // Modifikasi Bentuk Berdasarkan Emosi
    if (emotion == RobotEmotion::LISTENING) {
        // Mata membulat antusias fokus menyimak
        target_h = 36.0f;
        target_w = 32.0f;
        target_radius = 9.0f;
        target_h += std::sin((float)now * 0.014f) * 1.8f;
    } else if (emotion == RobotEmotion::THINKING) {
        // Menatap ke atas dengan getaran mikir
        target_offset_x = 5.0f;
        target_offset_y = -4.0f;
        target_offset_x += std::sin((float)now * 0.038f) * 2.2f;
    } else if (emotion == RobotEmotion::SPEAKING) {
        // Audio bounce saat berbicara
        float bounce = std::fabs(std::sin((float)now * 0.016f)) * 5.0f;
        target_offset_y -= bounce;
        target_h = 32.0f + std::sin((float)now * 0.02f) * 4.0f;
    } else if (emotion == RobotEmotion::CONFUSED) {
        // Satu mata agak beda tinggi / miring (bingung)
        target_offset_x = -3.0f;
        target_offset_y = 2.0f;
        target_h = 28.0f;
    }

    // Kedipan Menutup
    if (is_blinking_) {
        constexpr uint32_t kBlinkDurationMs = 140;
        uint32_t elapsed = now - blink_start_ms_;
        if (elapsed < kBlinkDurationMs) {
            float progress = (elapsed < kBlinkDurationMs / 2)
                ? (float)elapsed / (kBlinkDurationMs / 2.0f)
                : 1.0f - ((float)(elapsed - kBlinkDurationMs / 2.0f) / (kBlinkDurationMs / 2.0f));
            target_h -= (progress * (target_h - 3.0f));
            target_radius = (target_h > 8.0f) ? (target_h / 3.0f) : 1.0f;
        } else {
            is_blinking_ = false;
        }
    }

    // Physics Easing Interpolation (XiaoZhi Easing Formula)
    constexpr float kEasingPos = 0.28f;
    constexpr float kEasingSize = 0.35f;

    float target_left_x = 24.0f + target_offset_x;
    float target_right_x = 74.0f + target_offset_x;
    float target_y = 6.0f + target_offset_y;

    cur_left_x_  += (target_left_x - cur_left_x_) * kEasingPos;
    cur_right_x_ += (target_right_x - cur_right_x_) * kEasingPos;
    cur_y_       += (target_y - cur_y_) * kEasingPos;
    cur_w_       += (target_w - cur_w_) * kEasingSize;
    cur_h_       += (target_h - cur_h_) * kEasingSize;
    cur_radius_  += (target_radius - cur_radius_) * kEasingSize;

    int i_left_x = (int)(cur_left_x_ + 0.5f);
    int i_right_x = (int)(cur_right_x_ + 0.5f);
    int i_y = (int)(cur_y_ + (34.0f - cur_h_) * 0.5f);
    int i_w = (int)(cur_w_ + 0.5f);
    int i_h = (int)(cur_h_ + 0.5f);
    int i_r = (int)(cur_radius_ + 0.5f);
    if (i_r < 1) i_r = 1;
    if (i_h < 2) i_h = 2;

    if (has_text) {
        // Kompres mata ke area atas (0..26) saat marquee teks dialog tampil
        i_h = (i_h * 45) / 100;
        if (i_h < 3) i_h = 3;
        i_y = 1 + (26 - i_h) / 2;
        if (i_y < 0) i_y = 0;
    }

    // 4. Render Mata ke OLED
    if (emotion == RobotEmotion::HAPPY) {
        // Ekspresi Gembira (^ _ ^)
        for (int t = 0; t < 4; t++) {
            driver_.DrawLine(i_left_x, i_y + 20 - t, i_left_x + i_w / 2, i_y + 6 - t, true);
            driver_.DrawLine(i_left_x + i_w / 2, i_y + 6 - t, i_left_x + i_w, i_y + 20 - t, true);

            driver_.DrawLine(i_right_x, i_y + 20 - t, i_right_x + i_w / 2, i_y + 6 - t, true);
            driver_.DrawLine(i_right_x + i_w / 2, i_y + 6 - t, i_right_x + i_w, i_y + 20 - t, true);
        }
    } else if (emotion == RobotEmotion::SLEEP) {
        // Ekspresi Tidur (- -)
        for (int t = 0; t < 4; t++) {
            driver_.DrawFastHLine(i_left_x, i_y + 15 + t, i_w, true);
            driver_.DrawFastHLine(i_right_x, i_y + 15 + t, i_w, true);
        }
    } else {
        // Ekspresi Solid: NORMAL / LISTENING / THINKING / SPEAKING
        driver_.FillRoundRect(i_left_x, i_y, i_w, i_h, i_r, true);
        driver_.FillRoundRect(i_right_x, i_y, i_w, i_h, i_r, true);

        // Pupil specular highlight (kilau imut)
        if (!is_blinking_ && i_h > 20) {
            int hl_offset = (target_offset_x > 1.0f) ? 3 : (target_offset_x < -1.0f ? -3 : 0);
            driver_.FillRect(i_left_x + 17 + hl_offset, i_y + 6, 4, 5, false);
            driver_.FillRect(i_right_x + 7 + hl_offset, i_y + 6, 4, 5, false);
        }
    }

    // 5. Render Area Bawah Layar: Marquee Teks atau Status HUD
    if (has_text) {
        driver_.DrawFastHLine(0, 28, 128, true);
        driver_.DrawString(0, 31, active_label.c_str(), true);

        int text_width = (int)active_text.length() * 6;
        int travel = text_width + 128 + 24;
        if (travel < 1) travel = 1;
        int offset = (int)(((now - text_start) / 12) % (unsigned long)travel);
        int x = 128 - offset;
        driver_.DrawString(x, 46, active_text.c_str(), true);
    } else {
        // Mini HUD Status (Y: 48 .. 63)
        driver_.DrawFastHLine(0, 48, 128, true);

        if (emotion == RobotEmotion::LISTENING) {
            int dots = (now / 250) % 4;
            char msg[32];
            snprintf(msg, sizeof(msg), "Mendengarkan%.*s", dots, "...");
            driver_.DrawString(8, 52, msg, true);

            int wave = (now / 150) % 3;
            driver_.DrawString(104, 52, (wave == 0) ? "))" : (wave == 1 ? ")))" : " )"), true);
        } else if (emotion == RobotEmotion::THINKING) {
            driver_.DrawString(8, 52, "[AI] Berpikir...", true);
        } else if (emotion == RobotEmotion::SPEAKING) {
            driver_.DrawString(8, 52, "[AI] Menjawab...", true);
        } else {
            // Mode Normal Standby
            driver_.DrawString(12, 52, "ASISTEN BELAJAR AI", true);
        }
    }
}
