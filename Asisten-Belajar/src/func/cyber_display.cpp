#include "cyber_display.h"
#include <Arduino.h>

void drawCyberPomodoro(Adafruit_SSD1306 &display, const PomodoroData &data) {
  unsigned long now = millis();
  display.clearDisplay();

  // ==========================================
  // 1. CYBER FRAME / SUDUT BRACKET HUD
  // ==========================================
  // Sudut Kiri-Atas
  display.drawFastHLine(0, 0, 7, SSD1306_WHITE);
  display.drawFastVLine(0, 0, 7, SSD1306_WHITE);

  // Sudut Kanan-Atas
  display.drawFastHLine(120, 0, 8, SSD1306_WHITE);
  display.drawFastVLine(127, 0, 7, SSD1306_WHITE);

  // Sudut Kiri-Bawah
  display.drawFastHLine(0, 63, 7, SSD1306_WHITE);
  display.drawFastVLine(0, 56, 7, SSD1306_WHITE);

  // Sudut Kanan-Bawah
  display.drawFastHLine(120, 63, 8, SSD1306_WHITE);
  display.drawFastVLine(127, 56, 7, SSD1306_WHITE);

  // ==========================================
  // 2. HEADER HUD: MODE & FOCUS PERCENTAGE
  // ==========================================
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);

  // Mode badge (contoh: SYS//WORK atau SYS//BRK)
  String modeStr = data.mode;
  modeStr.toUpperCase();
  if (modeStr.length() == 0) modeStr = "WORK";

  // Kotak terbalik futuristik untuk label MODE
  display.fillRect(9, 2, 42, 9, SSD1306_WHITE);
  display.setTextColor(SSD1306_BLACK);
  display.setCursor(11, 3);
  display.print(modeStr.substring(0, 6));

  // Siklus di samping mode (contoh: [1/4])
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(54, 3);
  display.printf("[%s]", data.cycle_str.c_str());

  // Focus Level HUD di kanan atas (FOC:100%)
  display.setCursor(86, 3);
  display.printf("F:%d%%", data.focus);

  // Garis separator atas futuristik
  display.drawFastHLine(0, 13, 128, SSD1306_WHITE);
  display.drawPixel(64, 14, SSD1306_WHITE); // Tech tick mark tengah

  // ==========================================
  // 3. CENTER CYBER HUD: HITUNG MUNDUR (TIMER)
  // ==========================================
  // Frame kotak digital tengah
  display.drawRect(26, 17, 76, 26, SSD1306_WHITE);
  display.drawRect(28, 19, 72, 22, SSD1306_WHITE); // Garis ganda

  // Titik aksen sudut cyber pada kotak timer
  display.fillRect(25, 16, 3, 3, SSD1306_WHITE);
  display.fillRect(100, 16, 3, 3, SSD1306_WHITE);
  display.fillRect(25, 41, 3, 3, SSD1306_WHITE);
  display.fillRect(100, 41, 3, 3, SSD1306_WHITE);

  // Deteksi status PAUSED untuk efek kedip cyber
  bool isPaused = data.status.equalsIgnoreCase("PAUSED");
  bool showTimer = true;
  if (isPaused) {
    // Kedap kedip tiap 500ms
    showTimer = ((now / 500) % 2 == 0);
  }

  if (showTimer) {
    display.setTextSize(2);
    display.setTextColor(SSD1306_WHITE);
    // Format "MM:SS" (lebar ~60px) -> Pusatkan di koordinat X:34, Y:22
    display.setCursor(34, 23);
    if (data.time_str.length() > 0) {
      display.print(data.time_str);
    } else {
      display.print("25:00");
    }
  } else {
    // Saat jeda dan timer blank, tampilkan teks [ PAUSED ]
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(40, 27);
    display.print("PAUSED");
  }

  // ==========================================
  // 4. FOOTER HUD: TASK / CYBER BREACH ALERT
  // ==========================================
  // Garis separator bawah
  display.drawFastHLine(0, 46, 128, SSD1306_WHITE);

  if (data.alert.length() > 0) {
    // --- MODE PERINGATAN / ALERT CYBER (Kedap-Kedip Invert) ---
    bool alertInvert = ((now / 350) % 2 == 0);
    if (alertInvert) {
      display.fillRect(0, 48, 128, 15, SSD1306_WHITE);
      display.setTextColor(SSD1306_BLACK);
    } else {
      display.setTextColor(SSD1306_WHITE);
    }
    display.setTextSize(1);
    display.setCursor(4, 51);
    display.printf("! ALERT: %s", data.alert.substring(0, 14).c_str());
  } else {
    // --- MODE NORMAL CYBER COMMAND PROMPT ---
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(4, 49);
    
    // Tampilkan nama tugas dengan prefix terminal '>'
    String taskDisplay = data.task;
    if (taskDisplay.length() == 0) taskDisplay = "FOCUS MODE";
    if (taskDisplay.length() > 18) taskDisplay = taskDisplay.substring(0, 17) + "..";
    display.printf("> %s", taskDisplay.c_str());

    // Mini progress bar cyber di bagian paling bawah
    int totalSec = 25 * 60; // Asumsi default 25 menit
    if (data.time_left > totalSec) totalSec = data.time_left;
    int progressWidth = 0;
    if (totalSec > 0 && data.time_left >= 0) {
      progressWidth = map(data.time_left, 0, totalSec, 0, 116);
      if (progressWidth > 116) progressWidth = 116;
    }

    display.drawRect(6, 58, 116, 4, SSD1306_WHITE);
    if (progressWidth > 0) {
      display.fillRect(7, 59, progressWidth, 2, SSD1306_WHITE);
    }
  }

  // Kirim data buffer ke layar fisik OLED
  renderOLED();
}
