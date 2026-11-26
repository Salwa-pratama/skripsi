#include "asisten_belajar_board.h"
#include <esp_log.h>
#include <driver/gpio.h>

#define TAG "AsistenBelajarBoard"

AsistenBelajarBoard::AsistenBelajarBoard() {}

AsistenBelajarBoard::~AsistenBelajarBoard() {
    SetAmplifierPower(false);
    delete audio_codec_;
    delete led_;
}

void AsistenBelajarBoard::Initialize() {
    ESP_LOGI(TAG, "Initializing Asisten Belajar ESP32-S3 Board...");
    InitializeGpio();

    // 1. Inisialisasi status LED WS2812 pada GPIO 48
    led_ = new SingleLed(BUILTIN_LED_GPIO);

    // 2. Inisialisasi Audio Codec Duplex (I2S0 sharing BCLK 42 & WS 41)
    audio_codec_ = new NoAudioCodecDuplex(
        AUDIO_INPUT_SAMPLE_RATE,
        AUDIO_OUTPUT_SAMPLE_RATE,
        AUDIO_I2S_GPIO_BCLK,
        AUDIO_I2S_GPIO_WS,
        AUDIO_I2S_SPK_GPIO_DOUT,
        AUDIO_I2S_MIC_GPIO_DIN
    );

    // 3. Matikan Amplifier MAX98357A saat idle (SD Pin LOW = Shutdown 0.1 uA)
    // Amplifier hanya diaktifkan saat pemutaran suara agar mencegah lonjakan arus USB & noise mic
    SetAmplifierPower(false);

    ESP_LOGI(TAG, "Asisten Belajar Board initialized successfully.");
}

void AsistenBelajarBoard::InitializeGpio() {
    // Konfigurasi pin SD (Shutdown) Speaker MAX98357A sebagai Output
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << AUDIO_I2S_SPK_GPIO_SD),
        .mode = GPIO_MODE_OUTPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&io_conf));

    // Konfigurasi BOOT button (GPIO 0) sebagai Input Pull-Up
    gpio_config_t btn_conf = {
        .pin_bit_mask = (1ULL << BOOT_BUTTON_GPIO),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    ESP_ERROR_CHECK(gpio_config(&btn_conf));

    ESP_LOGI(TAG, "GPIO initialized: SPK_SD=%d (Output), BOOT_BTN=%d (Input PullUp)",
             AUDIO_I2S_SPK_GPIO_SD, BOOT_BUTTON_GPIO);
}

void AsistenBelajarBoard::SetAmplifierPower(bool enable) {
    amp_enabled_ = enable;
    gpio_set_level(AUDIO_I2S_SPK_GPIO_SD, enable ? 1 : 0);
    ESP_LOGI(TAG, "MAX98357A Amplifier Power set to: %s (GPIO %d = %d)",
             enable ? "ENABLED" : "SHUTDOWN", AUDIO_I2S_SPK_GPIO_SD, enable ? 1 : 0);
}

AudioCodec* AsistenBelajarBoard::GetAudioCodec() {
    return audio_codec_;
}

SingleLed* AsistenBelajarBoard::GetLed() {
    return led_;
}
