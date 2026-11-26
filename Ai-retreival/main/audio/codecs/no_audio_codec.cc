#include "no_audio_codec.h"

#include <esp_log.h>
#include <cmath>
#include <cstring>
#include <vector>
#include <algorithm>

#define TAG "NoAudioCodec"

NoAudioCodec::~NoAudioCodec() {
    if (rx_handle_ != nullptr) {
        i2s_channel_disable(rx_handle_);
        i2s_del_channel(rx_handle_);
    }
    if (tx_handle_ != nullptr) {
        i2s_channel_disable(tx_handle_);
        i2s_del_channel(tx_handle_);
    }
}

NoAudioCodecDuplex::NoAudioCodecDuplex(int input_sample_rate, int output_sample_rate,
                                       gpio_num_t bclk, gpio_num_t ws,
                                       gpio_num_t dout, gpio_num_t din) {
    duplex_ = true;
    input_sample_rate_ = input_sample_rate;
    output_sample_rate_ = output_sample_rate;
    output_volume_ = 90; // Default volume 90%

    // 1. Buat kanal I2S duplex master (TX untuk MAX98357A, RX untuk INMP441)
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(XIAOZHI_I2S_PORT(0), I2S_ROLE_MASTER);
    chan_cfg.dma_desc_num = AUDIO_CODEC_DMA_DESC_NUM;
    chan_cfg.dma_frame_num = AUDIO_CODEC_DMA_FRAME_NUM;
    chan_cfg.auto_clear_after_cb = true;

    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, &tx_handle_, &rx_handle_));

    // 2. Konfigurasi Standar Philips I2S 32-bit (Standar Xiaozhi untuk Mikrofon INMP441 24-bit)
    // INMP441 membutuhkan 32 clock cycle per slot untuk mengirimkan 24-bit audio secara presisi
    i2s_std_config_t std_cfg = {
        .clk_cfg = {
            .sample_rate_hz = (uint32_t)output_sample_rate_,
            .clk_src = I2S_CLK_SRC_DEFAULT,
            .ext_clk_freq_hz = 0,
            .mclk_multiple = I2S_MCLK_MULTIPLE_256,
        },
        .slot_cfg = {
            .data_bit_width = I2S_DATA_BIT_WIDTH_32BIT,
            .slot_bit_width = I2S_SLOT_BIT_WIDTH_32BIT,
            .slot_mode = I2S_SLOT_MODE_STEREO,
            .slot_mask = I2S_STD_SLOT_BOTH,
            .ws_width = I2S_DATA_BIT_WIDTH_32BIT,
            .ws_pol = false,
            .bit_shift = true,
            .left_align = false,
            .big_endian = false,
            .bit_order_lsb = false,
        },
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = bclk,
            .ws = ws,
            .dout = dout,
            .din = din,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };

    ESP_ERROR_CHECK(i2s_channel_init_std_mode(tx_handle_, &std_cfg));
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_handle_, &std_cfg));

    ESP_LOGI(TAG, "Duplex 32-bit Stereo I2S channels initialized on BCLK=%d, WS=%d, DOUT=%d, DIN=%d",
             bclk, ws, dout, din);
}

int NoAudioCodec::Write(const int16_t* data, int samples) {
    if (!tx_handle_ || samples <= 0) return 0;
    std::lock_guard<std::mutex> lock(data_if_mutex_);

    // Terapkan volume factor dan kirim ke Left & Right (Stereo) dalam 32-bit slot
    std::vector<int32_t> stereo_buf(samples * 2);
    int32_t volume_factor = (int32_t)output_volume_ * 65536 / 100;

    for (int i = 0; i < samples; i++) {
        int64_t temp = (int64_t)data[i] * volume_factor;
        int32_t val;
        if (temp > INT32_MAX) val = INT32_MAX;
        else if (temp < INT32_MIN) val = INT32_MIN;
        else val = static_cast<int32_t>(temp);

        stereo_buf[i * 2]     = val; // Left Channel
        stereo_buf[i * 2 + 1] = val; // Right Channel
    }

    size_t bytes_written = 0;
    esp_err_t err = i2s_channel_write(tx_handle_, stereo_buf.data(),
                                      stereo_buf.size() * sizeof(int32_t),
                                      &bytes_written, portMAX_DELAY);
    if (err != ESP_OK) return 0;
    return (bytes_written / sizeof(int32_t)) / 2;
}

int NoAudioCodec::Read(int16_t* dest, int samples) {
    if (!rx_handle_ || samples <= 0) return 0;
    size_t bytes_read = 0;
    constexpr uint32_t kReadTimeoutMs = 200;

    std::vector<int32_t> bit32_buffer(samples * 2);
    esp_err_t err = i2s_channel_read(rx_handle_, bit32_buffer.data(),
                                     bit32_buffer.size() * sizeof(int32_t),
                                     &bytes_read, pdMS_TO_TICKS(kReadTimeoutMs));
    if (err != ESP_OK || bytes_read == 0) {
        return 0;
    }

    int read_frames = (bytes_read / sizeof(int32_t)) / 2;
    for (int i = 0; i < read_frames; i++) {
        // Ambil data 24-bit mikrofon INMP441 dan geser >> 12 ke rentang PCM 16-bit
        int32_t left = bit32_buffer[i * 2] >> 12;
        int32_t right = bit32_buffer[i * 2 + 1] >> 12;

        // Pilih channel yang aktif (L/R INMP441 terhubung ke GND atau VDD)
        int32_t val = (std::abs(left) >= std::abs(right)) ? left : right;
        dest[i] = (val > INT16_MAX) ? INT16_MAX : (val < -INT16_MAX) ? -INT16_MAX : (int16_t)val;
    }
    return read_frames;
}

void NoAudioCodec::EnableInput(bool enable) {
    std::lock_guard<std::mutex> lock(data_if_mutex_);
    if (enable == input_enabled_) return;
    if (enable) {
        ESP_ERROR_CHECK(i2s_channel_enable(rx_handle_));
    } else {
        ESP_ERROR_CHECK(i2s_channel_disable(rx_handle_));
    }
    AudioCodec::EnableInput(enable);
}

void NoAudioCodec::EnableOutput(bool enable) {
    std::lock_guard<std::mutex> lock(data_if_mutex_);
    if (enable == output_enabled_) return;
    if (enable) {
        ESP_ERROR_CHECK(i2s_channel_enable(tx_handle_));
    } else {
        ESP_ERROR_CHECK(i2s_channel_disable(tx_handle_));
    }
    AudioCodec::EnableOutput(enable);
}
