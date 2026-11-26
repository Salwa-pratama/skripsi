#pragma once

#include <driver/gpio.h>

// =========================================================================
// DEFINISI PIN HARDWARE FREENOVE ESP32-S3 WROOM (SUDAH TERSOLDER)
// =========================================================================

// 1. Bus I2S Digital Audio (Clock & Word Select Bersama)
#define AUDIO_INPUT_SAMPLE_RATE     16000
#define AUDIO_OUTPUT_SAMPLE_RATE    16000

#define AUDIO_I2S_GPIO_BCLK         GPIO_NUM_42  // Clock I2S bersama (SCK INMP441 & BCLK MAX98357A)
#define AUDIO_I2S_GPIO_WS           GPIO_NUM_41  // Word Select bersama (WS INMP441 & LRC MAX98357A)

// 2. Modul Speaker MAX98357A (Data Out ESP32-S3)
#define AUDIO_I2S_SPK_GPIO_DOUT     GPIO_NUM_1   // DIN MAX98357A (Bebas dari LED onboard IO2)
#define AUDIO_I2S_SPK_GPIO_SD       GPIO_NUM_40  // SD (Shutdown/Enable) MAX98357A - HIGH = Unmute / Aktif

// 3. Modul Mikrofon INMP441 (Data In ESP32-S3)
#define AUDIO_I2S_MIC_GPIO_DIN      GPIO_NUM_14  // SD INMP441 (Data Out Mic -> Data In ESP32)

// 4. Layar OLED SSD1306 (128x64) via I2C Hardware
#define DISPLAY_SDA_PIN             GPIO_NUM_47  // SDA OLED
#define DISPLAY_SCL_PIN             GPIO_NUM_21  // SCL OLED
#define DISPLAY_WIDTH               128
#define DISPLAY_HEIGHT              64

// 5. Indikator & Input Onboard
#define BUILTIN_LED_GPIO            GPIO_NUM_48  // WS2812 RGB LED Onboard (RMT)
#define BOOT_BUTTON_GPIO            GPIO_NUM_0   // Tombol BOOT ESP32-S3 (Active LOW)
