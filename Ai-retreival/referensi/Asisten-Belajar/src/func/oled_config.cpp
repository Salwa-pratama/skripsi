#include "oled_config.h"
#include "robot_face.h"
#include "cyber_display.h"
#include "pomodoro_client.h"
#include <time.h>

// =========================================================================
// OBJEK DISPLAY OLED SSD1306 (ADAFRUIT GFX)
// =========================================================================
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// Konfigurasi Zona Waktu WIB (UTC+7)
const long  gmtOffset_sec = 7 * 3600;
const int   daylightOffset_sec = 0;

static unsigned long lastFrameTime = 0;
static const unsigned long FRAME_INTERVAL_MS = 30; // ~33 FPS animasi XiaoZhi ultra smooth

static bool oledReady = false;
static uint8_t activeOLEDAddress = SCREEN_ADDRESS;

Adafruit_SSD1306& getDisplay() {
  return display;
}

// Wrapper render yang aman
void renderOLED() {
  if (!oledReady) return;
  display.display();
}

// Catatan: GPIO 2 dialokasikan khusus untuk I2S Speaker DIN (MAX98357A),
// sehingga fungsi pinMode/digitalWrite pada pin 2 tidak boleh diaktifkan.
static void turnOffRedLedIO2() {
  // Dinonaktifkan demi integritas sinyal audio I2S (MAX98357A DIN: GPIO 2)
}

// Inisialisasi tampilan grafik ke layar fisik
static bool startDisplay() {
  if (!display.begin(SSD1306_SWITCHCAPVCC, activeOLEDAddress, false, false)) {
    Serial.printf("[OLED ERROR] Gagal inisialisasi driver Adafruit SSD1306 di alamat 0x%02X!\n", activeOLEDAddress);
    return false;
  }

  // Setel kontras maksimal (terang dan jernih)
  display.ssd1306_command(SSD1306_SETCONTRAST);
  display.ssd1306_command(0xFF);

  // Render Splash Screen
  display.clearDisplay();
  display.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  display.drawRect(2, 2, SCREEN_WIDTH - 4, SCREEN_HEIGHT - 4, SSD1306_WHITE);

  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(18, 14);
  display.println("ASISTEN BELAJAR");
  display.setCursor(24, 28);
  display.println("CYBER OS v1.0");

  display.drawFastHLine(6, 42, SCREEN_WIDTH - 12, SSD1306_WHITE);
  display.setCursor(14, 48);
  display.println("MOCHI ROBOT :: SIAP");

  display.display();
  Serial.println("[OLED] Splash screen BERHASIL dikirim ke layar fisik!");
  delay(1000);

  // Mulai animasi wajah robot
  initRobotFace();
  drawRobotFace(display, getPomodoroData());
  display.display();
  Serial.println("[OLED] Animasi Wajah Robot Mochi AKTIF dan BERJALAN!");
  return true;
}

// =========================================================================
// SETUP OLED
// =========================================================================
void setupOLED() {
  turnOffRedLedIO2();

  Serial.println("\n======================================================================");
  Serial.println("                 [INISIALISASI RESMI OLED SSD1306]                     ");
  Serial.println("======================================================================");

  // Inisialisasi Hardware I2C (SDA = GPIO 47, SCL = GPIO 21, 50 kHz murni tanpa toggling)
  Wire.begin(OLED_SDA_PIN, OLED_SCL_PIN, 50000);
  Wire.setTimeOut(50);
  delay(50);

  // Deteksi alamat I2C resmi (0x3C default, 0x3D cadangan)
  uint8_t foundAddr = 0;
  Wire.beginTransmission(0x3C);
  if (Wire.endTransmission() == 0) {
    foundAddr = 0x3C;
    Serial.println("[OLED] Alamat I2C terdeteksi: 0x3C (Standar 128x64) - ACK Sukses!");
  } else {
    Wire.beginTransmission(0x3D);
    if (Wire.endTransmission() == 0) {
      foundAddr = 0x3D;
      Serial.println("[OLED] Alamat I2C terdeteksi: 0x3D - ACK Sukses!");
    } else {
      Serial.println("[OLED] Memaksa alamat standar 0x3C...");
      foundAddr = 0x3C;
    }
  }

  activeOLEDAddress = foundAddr;
  Serial.printf("[1] Jalur I2C Terkunci: SDA=GPIO %d | SCL=GPIO %d (50 kHz)\n", OLED_SDA_PIN, OLED_SCL_PIN);
  Serial.printf("[2] Memulai driver Adafruit SSD1306 di alamat 0x%02X...\n", activeOLEDAddress);

  oledReady = startDisplay();

  Serial.println("======================================================================\n");
  configTime(gmtOffset_sec, daylightOffset_sec, "time.google.com", "pool.ntp.org", "time.windows.com");
}

// =========================================================================
// LOOP RENDER FRAME OLED (NON-BLOCKING ~25 FPS)
// =========================================================================
void updateOLED() {
  // Jika OLED belum terdeteksi saat boot, abaikan langsung
  if (!oledReady) {
    return;
  }

  unsigned long now = millis();
  if (now - lastFrameTime < FRAME_INTERVAL_MS) {
    return;
  }
  lastFrameTime = now;

  // Render animasi wajah robot realtime (XiaoZhi Easing Eyes)
  drawRobotFace(display, getPomodoroData());
  display.display(); // Pastikan buffer selalu dikirim ke kaca fisik
}

// =========================================================================
// TAMPILAN JAM DIGITAL STANDBY (JIKA DIPERLUKAN)
// =========================================================================
void updateOLEDClock() {
  static unsigned long lastClockUpdate = 0;
  if (millis() - lastClockUpdate < 1000) {
    return;
  }
  lastClockUpdate = millis();

  struct tm timeinfo;
  if (!getLocalTime(&timeinfo, 100)) {
    display.clearDisplay();
    display.setTextColor(SSD1306_WHITE);
    display.setTextSize(1);
    display.setCursor(10, 26);
    display.println("Menunggu Waktu NTP..");
    display.display();
    return;
  }

  char strTime[10];
  strftime(strTime, sizeof(strTime), "%H:%M:%S", &timeinfo);
  char strDate[20];
  strftime(strDate, sizeof(strDate), "%d-%m-%Y", &timeinfo);

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(18, 3);
  display.println("POMODORO CLOCK");
  display.drawLine(0, 14, 127, 14, SSD1306_WHITE);
  display.setTextSize(2);
  display.setCursor(16, 24);
  display.println(strTime);
  display.setTextSize(1);
  display.setCursor(32, 48);
  display.println(strDate);
  display.display();
}
