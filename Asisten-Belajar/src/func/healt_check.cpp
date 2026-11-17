#include "healt_check.h"


// ==========================================
// MONITOR KESEHATAN SISTEM ESP32 (DIAGNOSTIK)
// ==========================================
void healtCheck() {
  static unsigned long lastPantau = 0;

  // Cetak status setiap 3 detik sekali
  if (millis() - lastPantau >= 3000) {
    lastPantau = millis();

    float suhu = temperatureRead();
    uint32_t freeRam = ESP.getFreeHeap() / 1024;    // dalam KB
    uint32_t freePsram = ESP.getFreePsram() / 1024; // dalam KB
    int sinyalWiFi = WiFi.RSSI();                   // dalam dBm

    Serial.printf("\n[STATUS ESP32] Suhu: %.1f C | Free RAM: %u KB | Free PSRAM: %u KB | WiFi: %d dBm\n",
                  suhu, freeRam, freePsram, sinyalWiFi);

    // Deteksi Dini Hal Kritis:
    if (suhu >= 75.0) {
      Serial.println("⚠️ [PERINGATAN KRITIS] Suhu ESP32 panas (>75 C)! Disarankan pasang heatsink kecil.");
    }
    if (freeRam < 50) {
      Serial.println("⚠️ [PERINGATAN KRITIS] RAM internal hampir habis (<50 KB)! Berpotensi Crash/Kernel Panic.");
    }
    if (sinyalWiFi < -75) {
      Serial.println("⚠️ [PERINGATAN WIFI] Sinyal WiFi lemah (<-75 dBm)! Bisa menyebabkan video delay/drop.");
    }
  }
}
