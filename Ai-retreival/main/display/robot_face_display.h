#pragma once

#include "ssd1306_driver.h"
#include <string>
#include <mutex>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

enum class RobotEmotion {
    NORMAL,
    LISTENING,
    THINKING,
    SPEAKING,
    HAPPY,
    SLEEP,
    CONFUSED,
    ANGRY,
    SAD
};

class RobotFaceDisplay {
public:
    RobotFaceDisplay(gpio_num_t sda_pin, gpio_num_t scl_pin);
    ~RobotFaceDisplay();

    bool Initialize();
    void Start();
    void Stop();

    void SetEmotion(RobotEmotion emotion, uint32_t duration_ms = 0);
    void ShowText(const std::string& text, uint32_t duration_ms = 0, const std::string& label = "VOICE AI:");
    void ClearText();

    RobotEmotion GetActiveEmotion();

private:
    SSD1306Driver driver_;
    TaskHandle_t render_task_ = nullptr;
    bool running_ = false;
    std::mutex mutex_;

    // Status Emosi
    RobotEmotion current_emotion_ = RobotEmotion::NORMAL;
    uint32_t emotion_end_ms_ = 0;

    // Status Teks Dialog / Marquee
    std::string text_;
    std::string text_label_ = "VOICE AI:";
    bool text_active_ = false;
    uint32_t text_start_ms_ = 0;
    uint32_t text_end_ms_ = 0;

    // Koordinat Fisika & Easing (XiaoZhi Math)
    float cur_left_x_ = 24.0f;
    float cur_right_x_ = 74.0f;
    float cur_y_ = 6.0f;
    float cur_w_ = 30.0f;
    float cur_h_ = 34.0f;
    float cur_radius_ = 8.0f;

    // Kedipan & Lirikan
    bool is_blinking_ = false;
    uint32_t blink_start_ms_ = 0;
    uint32_t next_blink_ms_ = 3000;
    int current_glance_ = 0; // 0=Center, 1=Left, 2=Right, 3=Up
    uint32_t next_glance_ms_ = 2000;

    void RenderLoop();
    void DrawFrame(uint32_t now_ms);
};
