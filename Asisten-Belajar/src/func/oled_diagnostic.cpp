#include "oled_diagnostic.h"
#include <Wire.h>
#include <WiFi.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include "robot_face.h"
#include "pomodoro_client.h"

#define PIN_SDA_DEFAULT 47
#define PIN_SCL_DEFAULT 21
#define SCREEN_WIDTH    128
#define SCREEN_HEIGHT   64

static Adafruit_SSD1306 testDisplay(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, -1);
static bool isOledReady = false;
static uint8_t activeAddr = 0x3C;
static unsigned long lastFrameTime = 0;
static unsigned long lastRetryTime = 0;

void setupTesOLEDDiagnostic() {
  // 1. Matikan WiFi radio agar daya 3.3V stabil 100% tanpa lonjakan arus RF
  WiFi.mode(WIFI_OFF);

  Serial.println("\n");
  Serial.println("================================================================================");
  Serial.println("           [MODE 2: TES KHUSUS OLED MANDIRI - ZERO INTERFERENCE]                ");
  Serial.println("================================================================================");
  Serial.println("[ATURAN & KEAMANAN LISTRIK]");
  Serial.println("  * VCC OLED : WAJIB 3.3V (3V3 ESP32-S3 Deret Kiri Pin 1)");
  Serial.println("  * GND OLED : GND ESP32-S3 (Deret Kanan Pin 20)");
  Serial.println("  * SDA OLED : GPIO 47");
  Serial.println("  * SCL OLED : GPIO 21");
  Serial.println("  * Seluruh modul lain (Kamera, WiFi, Audio) DINONAKTIFKAN agar daya stabil.");
  Serial.println("  * TIDAK ADA pengujian korslet / pin-toggling yang mengganggu listrik.");
  Serial.println("================================================================================");

  // 2. Buka bus Hardware I2C murni (SDA=47, SCL=21, 50 kHz stabil)
  Wire.begin(PIN_SDA_DEFAULT, PIN_SCL_DEFAULT, 50000);
  Wire.setTimeOut(100);

  Serial.println("[I2C] Menunggu kapasitor & reset internal OLED stabil (300 ms)...");
  delay(300);

  // 3. Pindai alamat I2C OLED (0x3C dan 0x3D) secara pasif
  Serial.println("[I2C] Menguji respon chip di alamat 0x3C dan 0x3D...");
  
  Wire.beginTransmission(0x3C);
  byte err3C = Wire.endTransmission();

  Wire.beginTransmission(0x3D);
  byte err3D = Wire.endTransmission();

  Serial.printf("  -> Alamat 0x3C: %s (Error code: %d)\n", (err3C == 0 ? "ACK SUKSES (DITEMUKAN!)" : "NACK / Tidak ada respon"), err3C);
  Serial.printf("  -> Alamat 0x3D: %s (Error code: %d)\n", (err3D == 0 ? "ACK SUKSES (DITEMUKAN!)" : "NACK / Tidak ada respon"), err3D);

  if (err3C == 0) {
    activeAddr = 0x3C;
  } else if (err3D == 0) {
    activeAddr = 0x3D;
  } else {
    // Pindai seluruh alamat 1..126 untuk cek apakah ada chip di alamat lain
    Serial.println("[I2C] Memindai seluruh alamat I2C (1..126) untuk mencari perangkat aktif...");
    uint8_t foundAny = 0;
    for (uint8_t a = 1; a < 127; a++) {
      Wire.beginTransmission(a);
      if (Wire.endTransmission() == 0) {
        Serial.printf("  ==> DITEMUKAN PERANGKAT I2C DI ALAMAT: 0x%02X <==\n", a);
        foundAny = a;
      }
    }
    if (foundAny != 0) {
      activeAddr = foundAny;
    } else {
      Serial.println("[I2C PERINGATAN] Belum ada respon ACK di seluruh alamat.");
      Serial.println("    Kemungkinan: Kabel jumper 3.3V/GND/SDA/SCL belum kontak rapat di breadboard.");
      activeAddr = 0x3C; // Tetap coba default
    }
  }

  Serial.printf("\n[OLED] Mengunci alamat: 0x%02X @ 50 kHz. Memulai inisialisasi Adafruit SSD1306...\n", activeAddr);

  if (!testDisplay.begin(SSD1306_SWITCHCAPVCC, activeAddr, false, false)) {
    Serial.println("[OLED ERROR] Gagal inisialisasi buffer Adafruit SSD1306!");
    isOledReady = false;
    return;
  }

  // Set kontras maksimum
  testDisplay.ssd1306_command(SSD1306_SETCONTRAST);
  testDisplay.ssd1306_command(0xFF);

  // --- TAHAP 1: LAYAR PUTIH SOLID (ALL PIXELS ON) ---
  Serial.println("\n--------------------------------------------------------------------------------");
  Serial.println("[TES 1/3] Mengisi seluruh 128x64 memori layar dengan piksel PUTIH PENUH...");
  testDisplay.clearDisplay();
  testDisplay.fillRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  testDisplay.display();
  Serial.println("  -> Buffer terkirim lewat I2C (display.display() selesai).");
  Serial.println("  >>> LIHAT KACA LAYAR SEKARANG: Apakah menyala PUTIH TERANG SOLID? (Tunggu 2 detik) <<<");
  delay(2000);

  // --- TAHAP 2: KOTAK BINGKAI DAN TEKS INFORMASI ---
  Serial.println("\n--------------------------------------------------------------------------------");
  Serial.println("[TES 2/3] Merender kotak bingkai dan teks info sistem...");
  testDisplay.clearDisplay();
  testDisplay.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  testDisplay.drawRect(2, 2, SCREEN_WIDTH - 4, SCREEN_HEIGHT - 4, SSD1306_WHITE);
  testDisplay.setTextSize(1);
  testDisplay.setTextColor(SSD1306_WHITE);
  testDisplay.setCursor(14, 15);
  testDisplay.println("OLED TERHUBUNG!");
  testDisplay.setCursor(14, 28);
  testDisplay.printf("ADDR: 0x%02X @ 50kHz", activeAddr);
  testDisplay.setCursor(14, 42);
  testDisplay.println("SDA:IO47 | SCL:IO21");
  testDisplay.setCursor(14, 52);
  testDisplay.println("ASISTEN BELAJAR");
  testDisplay.display();
  Serial.println("  -> Frame teks info berhasil dikirim.");
  Serial.println("  >>> LIHAT KACA LAYAR: Apakah muncul tulisan 'OLED TERHUBUNG!'? (Tunggu 2 detik) <<<");
  delay(2000);

  // --- TAHAP 3: INISIALISASI ANIMASI WAJAH XIAOZHI MOCHI ---
  Serial.println("\n--------------------------------------------------------------------------------");
  Serial.println("[TES 3/3] Memulai Animasi Wajah Robot XiaoZhi Mochi (~33 FPS)...");
  initRobotFace();
  isOledReady = true;

  drawRobotFace(testDisplay, getPomodoroData());
  testDisplay.display();
  Serial.println("  -> Animasi mata XiaoZhi Mochi AKTIF dan BERJALAN!");
  Serial.println("================================================================================\n");
}

void loopTesOLEDDiagnostic() {
  if (isOledReady) {
    unsigned long now = millis();
    // Render animasi wajah robot setiap 30 ms (~33 FPS)
    if (now - lastFrameTime >= 30) {
      lastFrameTime = now;
      drawRobotFace(testDisplay, getPomodoroData());
      testDisplay.display();
    }
  } else {
    // Jika saat boot belum mendeteksi, lakukan retry lembut setiap 2 detik tanpa mengganggu jalur
    unsigned long now = millis();
    if (now - lastRetryTime >= 2000) {
      lastRetryTime = now;
      Wire.beginTransmission(0x3C);
      byte err = Wire.endTransmission();
      if (err == 0) {
        Serial.println("[RETRY] Koneksi terdeteksi di 0x3C! Memulai ulang tampilan...");
        setupTesOLEDDiagnostic();
      } else {
        Serial.printf("[RETRY] Menunggu modul OLED membalas di 0x3C... (Code: %d)\n", err);
      }
    }
  }
}
