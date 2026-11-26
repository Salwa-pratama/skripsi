#ifndef OLED_CONFIG_H
#define OLED_CONFIG_H

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ==========================================
// KONFIGURASI LAYAR & PIN I2C OLED (128x64)
// ==========================================
#define SCREEN_WIDTH   128   // Lebar layar OLED (piksel)
#define SCREEN_HEIGHT  64    // Tinggi layar OLED (piksel)
#define OLED_RESET     -1    // Pin reset (-1 karena share reset ESP)
#define SCREEN_ADDRESS 0x3C  // Alamat I2C default OLED 0.96 / 1.3 inch

// Pin I2C Deret Kanan (GPIO 47 & 21) - Bebas dari bentrok kamera OV5640
#define OLED_SDA_PIN   47   // SDA: GPIO 47
#define OLED_SCL_PIN   21   // SCL: GPIO 21

// ==========================================
// DEKLARASI FUNGSI
// ==========================================
void setupOLED();
void updateOLED();
void renderOLED();
void updateOLEDClock();
Adafruit_SSD1306& getDisplay();

#endif // OLED_CONFIG_H
