#pragma once

#include <driver/gpio.h>
#include <led_strip.h>
#include <cstdint>
#include <mutex>

class SingleLed {
public:
    explicit SingleLed(gpio_num_t gpio);
    ~SingleLed();

    void SetColor(uint8_t r, uint8_t g, uint8_t b);
    void TurnOn();
    void TurnOff();
    void Blink(int times, int delay_ms);

private:
    gpio_num_t gpio_;
    led_strip_handle_t led_strip_ = nullptr;
    std::mutex mutex_;
    uint8_t r_ = 0;
    uint8_t g_ = 0;
    uint8_t b_ = 0;
    bool is_on_ = false;
};
