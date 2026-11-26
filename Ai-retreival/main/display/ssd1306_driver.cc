#include "ssd1306_driver.h"
#include "font5x7.h"

#include <cmath>
#include <cstring>
#include <algorithm>
#include <esp_log.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

#define TAG "SSD1306"

SSD1306Driver::SSD1306Driver(gpio_num_t sda_pin, gpio_num_t scl_pin, uint8_t i2c_addr)
    : sda_pin_(sda_pin), scl_pin_(scl_pin), i2c_addr_(i2c_addr) {
    memset(buffer_, 0, sizeof(buffer_));
}

SSD1306Driver::~SSD1306Driver() {
    if (dev_handle_) {
        i2c_master_bus_rm_device(dev_handle_);
    }
    if (bus_handle_) {
        i2c_del_master_bus(bus_handle_);
    }
}

void SSD1306Driver::SendCommand(uint8_t cmd) {
    uint8_t tx_buf[2] = {0x00, cmd};
    i2c_master_transmit(dev_handle_, tx_buf, sizeof(tx_buf), 100);
}

bool SSD1306Driver::Initialize() {
    i2c_master_bus_config_t bus_config = {
        .i2c_port = I2C_NUM_0,
        .sda_io_num = sda_pin_,
        .scl_io_num = scl_pin_,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .intr_priority = 0,
        .trans_queue_depth = 0,
        .flags = {
            .enable_internal_pullup = true,
        },
    };
    esp_err_t err = i2c_new_master_bus(&bus_config, &bus_handle_);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create I2C master bus: %s", esp_err_to_name(err));
        return false;
    }

    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = i2c_addr_,
        .scl_speed_hz = 400000,
        .scl_wait_us = 0,
        .flags = {
            .disable_ack_check = false,
        },
    };
    err = i2c_master_bus_add_device(bus_handle_, &dev_config, &dev_handle_);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Failed to add I2C device: %s", esp_err_to_name(err));
        return false;
    }

    // Sequence Inisialisasi SSD1306 (128x64)
    static const uint8_t init_cmds[] = {
        0xAE,       // Display OFF
        0xD5, 0x80, // Set Display Clock Divide Ratio
        0xA8, 0x3F, // Set Multiplex Ratio (64)
        0xD3, 0x00, // Set Display Offset (0)
        0x40,       // Set Start Line (0)
        0x8D, 0x14, // Charge Pump ON (0x14)
        0x20, 0x00, // Memory Addressing Mode: Horizontal
        0xA1,       // Column Address 127 mapped to SEG0 (Mirror X)
        0xC8,       // Remapped Mode Scan from COM[N-1] to COM0
        0xDA, 0x12, // Set COM Pins Hardware Configuration
        0x81, 0xCF, // Set Contrast Control (0xCF)
        0xD9, 0xF1, // Set Pre-charge Period
        0xDB, 0x40, // Set VCOMH Deselect Level
        0xA4,       // Entire Display ON from RAM
        0xA6,       // Normal Display (Non-inverted)
        0xAF        // Display ON
    };

    for (size_t i = 0; i < sizeof(init_cmds); i++) {
        SendCommand(init_cmds[i]);
    }

    Clear();
    Refresh();
    ESP_LOGI(TAG, "SSD1306 OLED (128x64) initialized on SDA=%d, SCL=%d", sda_pin_, scl_pin_);
    return true;
}

void SSD1306Driver::Clear() {
    memset(buffer_, 0, sizeof(buffer_));
}

void SSD1306Driver::Refresh() {
    if (!dev_handle_) return;

    static const uint8_t setup_cmds[] = {
        0x21, 0, 127, // Set Column Address: 0 .. 127
        0x22, 0, 7    // Set Page Address: 0 .. 7
    };
    for (size_t i = 0; i < sizeof(setup_cmds); i++) {
        SendCommand(setup_cmds[i]);
    }

    // Kirim framebuffer 1024 byte dalam chunk via I2C (dengan prefix control 0x40)
    uint8_t packet[129];
    packet[0] = 0x40; // Control byte: Data stream
    for (int page = 0; page < 8; page++) {
        memcpy(packet + 1, buffer_ + (page * 128), 128);
        i2c_master_transmit(dev_handle_, packet, sizeof(packet), 100);
    }
}

void SSD1306Driver::DrawPixel(int x, int y, bool white) {
    if (x < 0 || x >= 128 || y < 0 || y >= 64) return;
    if (white) {
        buffer_[x + (y / 8) * 128] |= (1 << (y & 7));
    } else {
        buffer_[x + (y / 8) * 128] &= ~(1 << (y & 7));
    }
}

void SSD1306Driver::DrawFastHLine(int x, int y, int w, bool white) {
    for (int i = 0; i < w; i++) {
        DrawPixel(x + i, y, white);
    }
}

void SSD1306Driver::DrawFastVLine(int x, int y, int h, bool white) {
    for (int i = 0; i < h; i++) {
        DrawPixel(x, y + i, white);
    }
}

void SSD1306Driver::DrawLine(int x0, int y0, int x1, int y1, bool white) {
    int dx = std::abs(x1 - x0);
    int dy = std::abs(y1 - y0);
    int sx = (x0 < x1) ? 1 : -1;
    int sy = (y0 < y1) ? 1 : -1;
    int err = dx - dy;

    while (true) {
        DrawPixel(x0, y0, white);
        if (x0 == x1 && y0 == y1) break;
        int e2 = 2 * err;
        if (e2 > -dy) {
            err -= dy;
            x0 += sx;
        }
        if (e2 < dx) {
            err += dx;
            y0 += sy;
        }
    }
}

void SSD1306Driver::DrawRect(int x, int y, int w, int h, bool white) {
    DrawFastHLine(x, y, w, white);
    DrawFastHLine(x, y + h - 1, w, white);
    DrawFastVLine(x, y, h, white);
    DrawFastVLine(x + w - 1, y, h, white);
}

void SSD1306Driver::FillRect(int x, int y, int w, int h, bool white) {
    for (int i = 0; i < h; i++) {
        DrawFastHLine(x, y + i, w, white);
    }
}

void SSD1306Driver::DrawRoundRect(int x, int y, int w, int h, int r, bool white) {
    if (r <= 0) {
        DrawRect(x, y, w, h, white);
        return;
    }
    DrawFastHLine(x + r, y, w - 2 * r, white);
    DrawFastHLine(x + r, y + h - 1, w - 2 * r, white);
    DrawFastVLine(x, y + r, h - 2 * r, white);
    DrawFastVLine(x + w - 1, y + r, h - 2 * r, white);

    // Quarter circle corners
    int f = 1 - r;
    int ddF_x = 1;
    int ddF_y = -2 * r;
    int px = 0;
    int py = r;

    while (px < py) {
        if (f >= 0) {
            py--;
            ddF_y += 2;
            f += ddF_y;
        }
        px++;
        ddF_x += 2;
        f += ddF_x;

        DrawPixel(x + r - px, y + r - py, white);
        DrawPixel(x + r - py, y + r - px, white);
        DrawPixel(x + w - r - 1 + px, y + r - py, white);
        DrawPixel(x + w - r - 1 + py, y + r - px, white);
        DrawPixel(x + w - r - 1 + px, y + h - r - 1 + py, white);
        DrawPixel(x + w - r - 1 + py, y + h - r - 1 + px, white);
        DrawPixel(x + r - px, y + h - r - 1 + py, white);
        DrawPixel(x + r - py, y + h - r - 1 + px, white);
    }
}

void SSD1306Driver::FillRoundRect(int x, int y, int w, int h, int r, bool white) {
    if (r <= 0) {
        FillRect(x, y, w, h, white);
        return;
    }
    FillRect(x + r, y, w - 2 * r, h, white);

    // Rounded corners
    int f = 1 - r;
    int ddF_x = 1;
    int ddF_y = -2 * r;
    int px = 0;
    int py = r;

    while (px < py) {
        if (f >= 0) {
            py--;
            ddF_y += 2;
            f += ddF_y;
        }
        px++;
        ddF_x += 2;
        f += ddF_x;

        DrawFastVLine(x + r - px, y + r - py, 2 * py + 1 + h - 2 * r - 1, white);
        DrawFastVLine(x + r - py, y + r - px, 2 * px + 1 + h - 2 * r - 1, white);
        DrawFastVLine(x + w - r - 1 + px, y + r - py, 2 * py + 1 + h - 2 * r - 1, white);
        DrawFastVLine(x + w - r - 1 + py, y + r - px, 2 * px + 1 + h - 2 * r - 1, white);
    }
}

void SSD1306Driver::FillTriangle(int x0, int y0, int x1, int y1, int x2, int y2, bool white) {
    // Sort vertices by Y
    if (y0 > y1) { std::swap(x0, x1); std::swap(y0, y1); }
    if (y1 > y2) { std::swap(x1, x2); std::swap(y1, y2); }
    if (y0 > y1) { std::swap(x0, x1); std::swap(y0, y1); }

    if (y0 == y2) return;

    int dx01 = x1 - x0, dy01 = y1 - y0;
    int dx02 = x2 - x0, dy02 = y2 - y0;
    int dx12 = x2 - x1, dy12 = y2 - y1;

    for (int y = y0; y <= y2; y++) {
        int xa = (dy02 != 0) ? x0 + (y - y0) * dx02 / dy02 : x0;
        int xb = (y < y1) ? ((dy01 != 0) ? x0 + (y - y0) * dx01 / dy01 : x0)
                          : ((dy12 != 0) ? x1 + (y - y1) * dx12 / dy12 : x1);
        if (xa > xb) std::swap(xa, xb);
        DrawFastHLine(xa, y, xb - xa + 1, white);
    }
}

void SSD1306Driver::DrawChar(int x, int y, char c, bool white) {
    if (c < 32 || c > 126) c = ' ';
    int idx = (c - 32) * 5;
    for (int col = 0; col < 5; col++) {
        uint8_t line = font5x7[idx + col];
        for (int row = 0; row < 7; row++) {
            if (line & (1 << row)) {
                DrawPixel(x + col, y + row, white);
            }
        }
    }
}

void SSD1306Driver::DrawString(int x, int y, const char* str, bool white) {
    if (!str) return;
    int cur_x = x;
    while (*str) {
        if (*str == '\n') {
            cur_x = x;
            y += 8;
        } else {
            DrawChar(cur_x, y, *str, white);
            cur_x += 6;
        }
        str++;
    }
}
