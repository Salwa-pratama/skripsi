#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include "wifi_manager.h"
#include "tespin_config.h"
#include "healt_check.h"
#include "oled_config.h"
#include "robot_face.h"
#include "pomodoro_client.h"
#include "audio_test.h"
#include "oled_diagnostic.h"
#include "voice_client.h"
#include "server_config.h"

// =========================================================================
// PIN INDIKATOR & STATUS LED
// =========================================================================
#define STATUS_LED_PIN 48
static unsigned long lastBlinkTime = 0;
static bool ledState = false;

// =========================================================================
// PILIHAN MODE KERJA ESP32 (KAMERA SUDAH DINONAKTIFKAN TOTAL):
// 1 = Tes Kelistrikan & Korslet SELURUH GPIO (pull-up/down, drive, matriks pin)
// 2 = Tes Scanner I2C & Spesifikasi Layar OLED (SSD1306 / SH1106)
// 3 = Full System: OLED + Mic INMP441 + Speaker MAX98357A + Voice AI [DEFAULT]
// 4 = Layar Saja (Robot Eyes XiaoZhi / Pomodoro Cyber HUD)
// 5 = Tes Interaktif Audio (INMP441 Mic + MAX98357A Speaker)
// 6 = Diagnostik Mikrofon INMP441 (VU meter + verdict wiring)
// 7 = Tes speaker murni (meniru play_music C3, tanpa OLED/mic/Wi-Fi)
// 8 = Diagnostik MAX98357A: nada uji level rendah dan status I2S
// 9 = Pembanding nada diagnostik format klasik C3: 16-bit stereo
// =========================================================================
int modeTes = 3; // DEFAULT: Mode 3 (Full System Asisten Belajar AI tanpa kamera)

// =========================================================================
// BOOT MENU: pilih mode lewat Serial Monitor tanpa compile ulang
// Set ke 0 kalau ingin langsung masuk ke modeTes di atas tanpa jeda.
// =========================================================================
#define ENABLE_BOOT_MENU 1

static int readModeFromSerial() {
  Serial.println();
  Serial.println("======================================================================");
  Serial.println("        ASISTEN BELAJAR - PEMILIH MODE (BOOT MENU)");
  Serial.println("======================================================================");
  Serial.println("Target: FREENOVE ESP32-S3 WROOM (Dual-Core FreeRTOS)");
  Serial.println("  [1] Diagnostik SELURUH GPIO + scan korslet");
  Serial.println("  [2] Diagnostik OLED / scanner I2C");
  Serial.println("  [3] FULL SYSTEM (OLED + Voice AI + WiFi)   <-- DEFAULT");
  Serial.println("  [4] OLED saja (Pomodoro HUD)");
  Serial.println("  [5] Tes audio interaktif (musik 510-ALIVE + mic)");
  Serial.println("  [6] Tes MIKROFON INMP441 (VU meter + diagnosa wiring)");
  Serial.println("  [7] Tes SPEAKER murni (format TX XiaoZhi 32-bit)");
  Serial.println("  [8] Diagnostik amplifier MAX98357A (nada mono)");
  Serial.println("  [9] Bandingkan format C3 klasik (16-bit stereo)");
  Serial.printf("Tekan angka 1-9 lalu Enter. Otomatis masuk Mode %d dalam 3 detik...\n", modeTes);
  Serial.println("======================================================================");

  unsigned long start = millis();
  while (millis() - start < 3000) {
    while (Serial.available() > 0) {
      int c = Serial.read();
      if (c >= '1' && c <= '9') {
        Serial.printf("\n>> Mode %d dipilih.\n", c - '0');
        delay(150);
        return c - '0';
      }
    }
    delay(20);
  }

  Serial.printf("\n>> Timeout, otomatis masuk ke Mode %d (Sistem Utama Asisten Belajar).\n", modeTes);
  return modeTes;
}

// Konfigurasi koneksi jaringan WiFi
const char* ssid = "Sembarang 4G";
const char* password = "oppo1915";

// =========================================================================
// VOICE ASSISTANT: MIC -> SERVER (STT + SBERT) -> TTS -> SPEAKER
// -------------------------------------------------------------------------
// Alur lengkap ditangani voice_client.cpp:
//   1. Mikrofon INMP441 mendeteksi ucapan user (peak > 18000).
//   2. Rekaman WAV 16 kHz mono diunggah ke POST /api/ai/voice.
//   3. Server melakukan faster-whisper STT + retrieval fine-tuned SBERT.
//   4. Teks jawaban tampil di OLED (marquee kanan -> kiri).
//   5. File WAV jawaban diputar ke speaker MAX98357A.
// Kamera OV5640 dan seluruh pin kameranya sudah tidak diinisialisasi.
// =========================================================================
static unsigned long lastVoiceCheck = 0;
static unsigned long lastVoiceInteraction = 0;

void handleVoiceAssistant() {
  unsigned long now = millis();

  // Cek level mikrofon tiap 200 ms agar loop OLED tetap halus.
  if (now - lastVoiceCheck < 200) return;
  lastVoiceCheck = now;

  // Cooldown 2 detik agar suara speaker tidak memicu pertanyaan baru.
  if (now - lastVoiceInteraction < 2000) return;

  if (detectVoiceTrigger(1200)) {
    lastVoiceInteraction = millis();
    // Berikan teks "Mendengarkan..." di bawah mata robot secara instan saat voice trigger aktif
    setFaceEmotionOverride("LISTENING", 10000);
    updateOLED();
    askVoiceAssistantFromMic();
    lastVoiceInteraction = millis(); // mulai cooldown setelah interaksi selesai
  }
}

// =========================================================================
// SETUP UTAMA
// =========================================================================
void setup() {
  Serial.begin(115200);
  delay(1500); // Jeda agar Serial Monitor siap
  setCpuFrequencyMhz(240); // 240 MHz Maksimal ESP32-S3 Dual-Core

#if ENABLE_BOOT_MENU
  modeTes = readModeFromSerial();
#endif

  pinMode(STATUS_LED_PIN, OUTPUT);

  if (modeTes == 1) {
    setupTesPin();
  } else if (modeTes == 2) {
    setupTesOLEDDiagnostic();
  } else if (modeTes == 3) {
    Serial.println("\n======================================================================");
    Serial.println("  [ASISTEN BELAJAR] FULL SYSTEM ESP32-S3 (VOICE AI, TANPA KAMERA)      ");
    Serial.println("======================================================================");

    // 1. Layar OLED lebih dulu agar mata robot menyala instan.
    setupOLED();

    // 2. Subsistem audio (MAX98357A speaker & INMP441 mic).
    setupAudioSystem();

    // 3. Klien pertanyaan suara (rekam -> upload -> TTS).
    setupVoiceClient();

    // 4. Koneksi WiFi.
    setupWiFiAndServer(ssid, password);

    // 5. Client Pomodoro untuk HUD OLED.
    setupPomodoroClient();

    Serial.println("[SYSTEM] Kamera OV5640: NONAKTIF (pin kamera tidak dipakai).");
    Serial.println("[SYSTEM] Core 1 menjalankan OLED, Audio, Voice AI, dan Pomodoro.");

    // Putar melodi sambutan saat boot siap.
    playSuccessChime();
    lastVoiceInteraction = millis(); // Jeda 2 detik setelah melodi boot agar tidak memicu mic sendiri

  } else if (modeTes == 4) {
    // Mode Layar Mandiri (OLED langsung menyala)
    setupOLED();
    setupWiFiAndServer(ssid, password);
    setupPomodoroClient();
  } else if (modeTes == 5) {
    setupAudioTest();
  } else if (modeTes == 6) {
    setupMicTest();
  } else if (modeTes == 7) {
    setupSpeakerOnlyTest();
  } else if (modeTes == 8) {
    setupAmpToneDiagnostic();
  } else if (modeTes == 9) {
    setupAmpStereoToneDiagnostic();
  } else {
    Serial.println("Mode tidak dikenal! Pastikan modeTes bernilai 1 sampai 9.");
  }
}

// =========================================================================
// LOOP UTAMA (NON-BLOCKING)
// =========================================================================
void loop() {
  if (modeTes == 1) {
    loopTesPin();
  } else if (modeTes == 2) {
    loopTesOLEDDiagnostic();
  } else if (modeTes == 3 || modeTes == 4) {
    // 1. Sinkronisasi data Pomodoro non-blocking.
    updatePomodoroClient();

    // 2. Render animasi wajah / teks jawaban di OLED.
    updateOLED();

    // 3. Voice assistant hanya pada Mode 3 (butuh mic + server AI).
    if (modeTes == 3) {
      handleVoiceAssistant();
    }

    // 4. Diagnostik kesehatan ESP32 (suhu, RAM, PSRAM, RSSI).
    healtCheck();

    // 5. Indikator LED berkedip setiap 500 ms jika WiFi aktif.
    if (WiFi.status() == WL_CONNECTED) {
      if (millis() - lastBlinkTime >= 500) {
        lastBlinkTime = millis();
        ledState = !ledState;
        digitalWrite(STATUS_LED_PIN, ledState ? HIGH : LOW);
        neopixelWrite(STATUS_LED_PIN, ledState ? 20 : 0, ledState ? 20 : 0, ledState ? 20 : 0);
      }
    }

    // 6. Penjaga WiFi: paksa modem sleep OFF setiap 5 detik.
    static unsigned long lastWifiGuard = 0;
    if (millis() - lastWifiGuard >= 5000) {
      lastWifiGuard = millis();
      if (WiFi.status() == WL_CONNECTED) {
        WiFi.setSleep(false);
        esp_wifi_set_ps(WIFI_PS_NONE);
      }
    }

    vTaskDelay(pdMS_TO_TICKS(5));
  } else if (modeTes == 5) {
    loopAudioTest();
  } else if (modeTes == 6) {
    loopMicTest();
  } else if (modeTes == 7) {
    loopSpeakerOnlyTest();
  } else if (modeTes == 8) {
    loopAmpToneDiagnostic();
  } else if (modeTes == 9) {
    loopAmpStereoToneDiagnostic();
  }
}
