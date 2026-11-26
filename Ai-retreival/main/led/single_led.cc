#include "single_led.h"
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define TAG "SingleLed"

SingleLed::SingleLed(gpio_num_t gpio) : gpio_(gpio) {
    if (gpio == GPIO_NUM_NC) return;

    led_strip_config_t strip_config = {
        .strip_gpio_num = gpio,
        .max_leds = 1,
        .led_model = LED_MODEL_WS2812,
        .color_component_format = LED_STRIP_COLOR_COMPONENT_FMT_GRB,
        .flags = {
            .invert_out = false,
        },
    };

    led_strip_rmt_config_t rmt_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .resolution_hz = 10 * 1000 * 1000, // 10MHz
        .mem_block_symbols = 64,
        .flags = {
            .with_dma = false,
        },
    };

    esp_err_t err = led_strip_new_rmt_device(&strip_config, &rmt_config, &led_strip_);
    if (err == ESP_OK && led_strip_) {
        led_strip_clear(led_strip_);
        ESP_LOGI(TAG, "WS2812 RGB LED initialized on GPIO %d", gpio);
    } else {
        ESP_LOGE(TAG, "Failed to initialize WS2812 on GPIO %d: %s", gpio, esp_err_to_name(err));
        led_strip_ = nullptr;
    }
}

SingleLed::~SingleLed() {
    if (led_strip_) {
        led_strip_clear(led_strip_);
        led_strip_del(led_strip_);
    }
}

void SingleLed::SetColor(uint8_t r, uint8_t g, uint8_t b) {
    std::lock_guard<std::mutex> lock(mutex_);
    r_ = r;
    g_ = g;
    b_ = b;
    if (is_on_ && led_strip_) {
        led_strip_set_pixel(led_strip_, 0, r_, g_, b_);
        led_strip_refresh(led_strip_);
    }
}

void SingleLed::TurnOn() {
    std::lock_guard<std::mutex> lock(mutex_);
    is_on_ = true;
    if (led_strip_) {
        led_strip_set_pixel(led_strip_, 0, r_, g_, b_);
        led_strip_refresh(led_strip_);
    }
}

void SingleLed::TurnOff() {
    std::lock_guard<std::mutex> lock(mutex_);
    is_on_ = false;
    if (led_strip_) {
        led_strip_clear(led_strip_);
    }
}

void SingleLed::Blink(int times, int delay_ms) {
    for (int i = 0; i < times; i++) {
        TurnOn();
        vTaskDelay(pdMS_TO_TICKS(delay_ms));
        TurnOff();
        vTaskDelay(pdMS_TO_TICKS(delay_ms));
    }
}
