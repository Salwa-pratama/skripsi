#include <Arduino.h>
#include <WiFi.h>
#include <esp_wifi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "camera_config.h"
#include "tespin_config.h"
#include "camera_server.h"
#include "healt_check.h"
#include "oled_config.h"
#include "robot_face.h"
#include "pomodoro_client.h"
#include "audio_test.h"
#include "oled_diagnostic.h"

// =========================================================================
// PIN INDIKATOR & STATUS LED
// =========================================================================
#define STATUS_LED_PIN 48
static unsigned long lastBlinkTime = 0;
static bool ledState = false;

// =========================================================================
// PILIHAN MODE KERJA ESP32:
// 1 = Tes Kelistrikan & Korslet SELURUH GPIO (pull-up/down, drive, matriks pin)
// 2 = Tes Scanner I2C & Spesifikasi Layar OLED (SSD1306 / SH1106)
// 3 = Full System Dual-Core: Kamera OV5640 (Core 0) + Robot Eyes XiaoZhi & Voice Trigger AI (Core 1) [DEFAULT]
// 4 = Layar Saja (Robot Eyes XiaoZhi / Pomodoro Cyber HUD Tanpa Kamera)
// 5 = Tes Interaktif Audio (INMP441 Mic + MAX98357A Speaker, Voice Trigger)
// 6 = Diagnostik Mikrofon INMP441 (VU meter + verdict wiring)
// 7 = Tes speaker murni (meniru play_music C3, tanpa OLED/mic/Wi-Fi)
// 8 = Diagnostik MAX98357A: nada uji level rendah dan status I2S
// 9 = Pembanding nada diagnostik format klasik C3: 16-bit stereo
// =========================================================================
int modeTes = 3; // DEFAULT: Mode 3 (Full System Dual-Core Asisten Belajar AI)

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
  Serial.println("  [3] FULL SYSTEM (Kamera + OLED + Voice AI + WiFi)   <-- DEFAULT");
  Serial.println("  [4] OLED saja (tanpa kamera)");
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
const char* ssid = "ananda";
const char* password = "oppo1915";

// URL Endpoint Asisten Belajar AI Backend (FastAPI Computer Vision)
// IP laptop di hotspot "ananda" saat ini: 10.19.170.155
// Ubah di sini jika IP laptop berubah.
const char* AI_ASK_URL = "http://10.19.170.155:5000/api/ai/ask";
const char* SERVER_BASE_URL = "http://10.19.170.155:5000";

// =========================================================================
// DUAL-CORE FREERTOS ARCHITECTURE (SOLUSI 1)
// Core 0: Dedicated Streaming Kamera OV5640 & Web Server (Non-Stop)
// Core 1: OLED XiaoZhi Robot Eyes + Polling Status + Audio I2S & Voice Trigger AI
// =========================================================================
TaskHandle_t cameraTaskHandle = NULL;
static bool cameraInitialized = false;

void cameraCore0Task(void *pvParameters) {
  Serial.printf("\n[CORE 0] Task Kamera aktif di CPU Core: %d\n", xPortGetCoreID());

  // 1. Inisialisasi Hardware Kamera OV5640 di Core 0
  setupTesKamera();
  cameraInitialized = true;

  // 2. Jalankan HTTP Web Server kamera (Stream MJPEG di port 81, Snapshot di port 80)
  startCameraServer();
  Serial.println("[CORE 0] Web Server Streaming Kamera OV5640 SIAP!");

  // Loop pengawas kamera di Core 0 (Low Priority background supervisor)
  while (true) {
    vTaskDelay(pdMS_TO_TICKS(2000));
  }
}

// =========================================================================
// FUNGSI INTERAKSI ASISTEN BELAJAR AI (GEMINI + EDGE-TTS)
// =========================================================================
void askAIService(const char* prompt) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[AI] WiFi tidak tersambung! Batal mengirim prompt AI.");
    return;
  }

  Serial.printf("\n=======================================================\n");
  Serial.printf("[AI REQUEST] Pertanyaan Suara: \"%s\"\n", prompt);
  Serial.printf("=======================================================\n");

  // Alihkan ekspresi wajah robot ke mode THINKING (Mikir + Shiver)
  setFaceEmotionOverride("THINKING", 15000);
  renderOLED();

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(18000); // 18s batas timeout respons Gemini & Edge-TTS

  if (!http.begin(client, AI_ASK_URL)) {
    Serial.println("[AI ERROR] Gagal menghubungi endpoint server AI.");
    clearFaceEmotionOverride();
    return;
  }

  http.addHeader("Content-Type", "application/json");

  // Buat Payload JSON
  JsonDocument reqDoc;
  reqDoc["prompt"] = prompt;
  reqDoc["include_image"] = false;
  String reqPayload;
  serializeJson(reqDoc, reqPayload);

  int httpCode = http.POST(reqPayload);
  if (httpCode == HTTP_CODE_OK) {
    String respPayload = http.getString();
    JsonDocument respDoc;
    DeserializationError err = deserializeJson(respDoc, respPayload);

    if (!err) {
      const char* answerText = respDoc["answer"] | "";
      const char* audioWavUrl = respDoc["audio_wav_url"] | "";
      const char* respEmotion = respDoc["emotion"] | "speaking";

      Serial.printf("[AI JAWABAN] %s\n", answerText);

      if (strlen(audioWavUrl) > 0) {
        // Alihkan ekspresi wajah robot ke mode SPEAKING (Bouncing Eyes)
        setFaceEmotionOverride("SPEAKING", 30000);
        renderOLED();

        // Bangun Full URL untuk streaming file WAV
        String fullAudioUrl = String(SERVER_BASE_URL) + String(audioWavUrl);
        Serial.printf("[AI AUDIO] Memutar suara via I2S: %s\n", fullAudioUrl.c_str());

        // Stream audio WAV ke MAX98357A speaker
        playWavFromUrl(fullAudioUrl.c_str());
      }
    } else {
      Serial.printf("[AI ERROR] Gagal parse JSON respons: %s\n", err.c_str());
    }
  } else {
    Serial.printf("[AI ERROR] HTTP POST Gagal dengan kode: %d\n", httpCode);
  }

  http.end();
  clearFaceEmotionOverride();
  Serial.println("[AI] Interaksi selesai, kembali ke mode normal.");
}

// =========================================================================
// VOICE TRIGGER & ALARM DISTRAKSI (BUNYI TERUS-MENERUS)
// -------------------------------------------------------------------------
// Volume speaker dikunci 100% lewat SPEAKER_MASTER_VOLUME_PERCENT (audio_test.h).
// Saat alert "HP!" atau "ABSEN!" aktif, updateAlarmSound() memainkan nada sirene
// pendek bergantian TANPA HENTI (non-blocking) sehingga OLED, WiFi, dan polling
// status tetap berjalan normal.
// =========================================================================
static bool alarmSoundActive = false;
static String alarmReason = "";
static int alarmToneStep = 0;
static unsigned long alarmNextToneMs = 0;
static unsigned long lastVoiceCheck = 0;
static unsigned long lastAiTriggerTime = 0;

// True jika server melaporkan HP terdeteksi atau pengguna absen.
static bool isAlertActive(const PomodoroData &pData) {
  const String &a = pData.alert;
  return (a == "HP!" || a.indexOf("HP") >= 0 ||
          a == "ABSEN!" || a.indexOf("ABSEN") >= 0);
}

void handleVoiceAndAlerts() {
  unsigned long now = millis();
  const PomodoroData &pData = getPomodoroData();

  // 1. Tentukan apakah alarm harus berbunyi (HP terdeteksi ATAU pengguna absen).
  //    Data dianggap basi bila > 8 detik tidak ada sinkron dari server (mis. WiFi
  //    putus) -> alarm dimatikan agar tidak berbunyi selamanya.
  bool stale = (pData.last_sync == 0) || (now - pData.last_sync > 8000);
  bool wantAlarm = isAlertActive(pData) && !stale;

  if (wantAlarm != alarmSoundActive) {
    alarmSoundActive = wantAlarm;
    if (alarmSoundActive) {
      alarmReason = pData.alert;
      alarmToneStep = 0;
      alarmNextToneMs = now;
      Serial.printf("\n[ALARM] AKTIF (%s): speaker berbunyi terus-menerus @ volume 100%%.\n",
                    alarmReason.c_str());
    } else {
      Serial.println("\n[ALARM] NONAKTIF: speaker berhenti berbunyi.");
    }
  }

  // 2. Voice Trigger hanya saat alarm TIDAK berbunyi. Bus I2S sedang dipakai
  //    speaker; ini juga mencegah feedback suara speaker masuk ke mikrofon.
  if (!alarmSoundActive && now - lastVoiceCheck >= 200 && now - lastAiTriggerTime >= 45000) {
    lastVoiceCheck = now;
    int peak = readMicPeak();
    // Threshold suara bicara jelas (>18000) agar ketikan keyboard & suara ruangan tidak memicu AI palsu
    if (peak > 18000) {
      lastAiTriggerTime = now;
      Serial.printf("\n[VOICE TRIGGER] Suara pengguna terdeteksi (Peak: %d)! Meminta saran belajar...\n", peak);
      askAIService("Berikan saya tips belajar fokus dan motivasi singkat 1 kalimat.");
    }
  }
}

// Dipanggil setiap iterasi loop utama. Memainkan satu nada pendek lalu
// menjadwalkan nada berikutnya, sehingga sirene terdengar hampir bersambung
// tanpa memblokir sistem terlalu lama.
void updateAlarmSound() {
  if (!alarmSoundActive) return;

  unsigned long now = millis();
  if (now < alarmNextToneMs) return;

  // Nada berbeda: HP = tinggi & mendesak, ABSEN = rendah & memanggil.
  bool absen = (alarmReason.indexOf("ABSEN") >= 0);
  int freq = absen ? ((alarmToneStep % 2 == 0) ? 520 : 400)
                   : ((alarmToneStep % 2 == 0) ? 880 : 640);

  playTone(freq, 120);   // 120 ms per nada, volume 100% (lihat audio_test.h)
  alarmToneStep++;

  // Jeda sangat pendek -> bunyi nyaris terus-menerus.
  alarmNextToneMs = millis() + 30;
}

// =========================================================================
// SETUP UTAMA (CORE 1)
// =========================================================================
void setup() {
  Serial.begin(115200);
  delay(1500); // Jeda agar Serial Monitor siap
  setCpuFrequencyMhz(240); // 240 MHz Maksimal ESP32-S3 Dual-Core (Streaming kamera lancar & FPS tinggi)

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
    Serial.println("  [ASISTEN BELAJAR] SISTEM UTAMA DUAL-CORE ESP32-S3 (VOICE TRIGGER)   ");
    Serial.println("======================================================================");

    // 1. Inisialisasi Layar OLED DULUAN agar tampilan mata robot menyala instan!
    setupOLED();

    // 2. Inisialisasi Subsistem Audio (MAX98357A & INMP441)
    setupAudioSystem();

    // 3. Hubungkan ke Jaringan WiFi
    setupWiFiAndServer(ssid, password);

    // 4. Inisialisasi Client Pomodoro / Companion
    setupPomodoroClient();

    // 5. Jalankan Task Dedicated Kamera OV5640 di CPU Core 0 (FreeRTOS Dual-Core)
    xTaskCreatePinnedToCore(
      cameraCore0Task,      // Fungsi task
      "CameraCore0Task",    // Nama task
      4096,                 // Stack size (bytes)
      NULL,                 // Parameter
      1,                    // Priority
      &cameraTaskHandle,    // Task handle
      0                     // CPU Core 0!
    );
    Serial.println("[SYSTEM] Task Kamera berhasil dipin ke CPU Core 0.");
    Serial.println("[SYSTEM] Core 1 menjalankan Antarmuka OLED, Audio, dan Voice Trigger AI.");

    // Putar melodi sambutan saat boot siap
    playSuccessChime();

  } else if (modeTes == 4) {
    // Mode Layar Mandiri (Tanpa Kamera - OLED langsung menyala)
    setupOLED();
    setupWiFiAndServer(ssid, password);
    setupPomodoroClient();
  } else if (modeTes == 5) {
    // Mode Tes Interaktif Audio (Voice Trigger)
    setupAudioTest();
  } else if (modeTes == 6) {
    // Mode Diagnostik Mikrofon INMP441
    setupMicTest();
  } else if (modeTes == 7) {
    // Mode tes speaker murni untuk membandingkan dengan firmware ESP32-C3
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
// LOOP UTAMA (CORE 1 - NON-BLOCKING)
// =========================================================================
void loop() {
  if (modeTes == 1) {
    loopTesPin();
  } else if (modeTes == 2) {
    loopTesOLEDDiagnostic();
  } else if (modeTes == 3 || modeTes == 4) {
    // 1. Sinkronisasi data Pomodoro secara non-blocking (setiap 1 detik)
    updatePomodoroClient();

    // 2. Render Animasi Layar OLED (Wajah Robot XiaoZhi Math & Status Pomodoro HUD) ~33 FPS
    updateOLED();
    // 3. Tangani Voice Trigger Mikrofon & Peringatan Distraksi HP
    handleVoiceAndAlerts();

    // 3b. Sirene alarm terus-menerus saat HP terdeteksi / pengguna absen
    updateAlarmSound();

    // 4. Diagnostik Kesehatan Sistem ESP32 (Suhu, RAM, PSRAM, RSSI)
    healtCheck();

    // 5. Indikator LED berkedip setiap 500ms jika WiFi aktif
    if (WiFi.status() == WL_CONNECTED) {
      if (millis() - lastBlinkTime >= 500) {
        lastBlinkTime = millis();
        ledState = !ledState;
        digitalWrite(STATUS_LED_PIN, ledState ? HIGH : LOW);
        neopixelWrite(STATUS_LED_PIN, ledState ? 20 : 0, ledState ? 20 : 0, ledState ? 20 : 0);
      }
    }

    // 6. PENJAGA WI-FI (setiap 5 detik): paksa modem sleep OFF.
    // Setiap kali ESP32 reconnect ke hotspot, setting power-save bisa kembali aktif dan
    // membuat RTT melonjak 500-3000ms (stream jadi lambat). Guard ini menormalkannya kembali.
    static unsigned long lastWifiGuard = 0;
    if (millis() - lastWifiGuard >= 5000) {
      lastWifiGuard = millis();
      if (WiFi.status() == WL_CONNECTED) {
        WiFi.setSleep(false);
        esp_wifi_set_ps(WIFI_PS_NONE);
      }
    }

    // Jeda 5ms agar FreeRTOS IDLE task & network driver di Core 1 dapat bernapas
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
