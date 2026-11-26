#pragma once

#include <cstdint>
#include <cstddef>
#include <driver/gpio.h>
#include <driver/i2c_master.h>

class SSD1306Driver {
public:
    SSD1306Driver(gpio_num_t sda_pin, gpio_num_t scl_pin, uint8_t i2c_addr = 0x3C);
    ~SSD1306Driver();

    bool Initialize();
    void Clear();
    void Refresh();

    // Primitive Graphics
    void DrawPixel(int x, int y, bool white = true);
    void DrawFastHLine(int x, int y, int w, bool white = true);
    void DrawFastVLine(int x, int y, int h, bool white = true);
    void DrawLine(int x0, int y0, int x1, int y1, bool white = true);
    void DrawRect(int x, int y, int w, int h, bool white = true);
    void FillRect(int x, int y, int w, int h, bool white = true);
    void DrawRoundRect(int x, int y, int w, int h, int r, bool white = true);
    void FillRoundRect(int x, int y, int w, int h, int r, bool white = true);
    void FillTriangle(int x0, int y0, int x1, int y1, int x2, int y2, bool white = true);

    // Text Rendering
    void DrawChar(int x, int y, char c, bool white = true);
    void DrawString(int x, int y, const char* str, bool white = true);

    inline int width() const { return 128; }
    inline int height() const { return 64; }

private:
    gpio_num_t sda_pin_;
    gpio_num_t scl_pin_;
    uint8_t i2c_addr_;

    i2c_master_bus_handle_t bus_handle_ = nullptr;
    i2c_master_dev_handle_t dev_handle_ = nullptr;
    uint8_t buffer_[1024];

    void SendCommand(uint8_t cmd);
};
