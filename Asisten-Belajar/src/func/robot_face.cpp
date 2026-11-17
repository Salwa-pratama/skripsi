#include "robot_face.h"
#include <Arduino.h>
#include <math.h>

// =========================================================================
// KONFIGURASI GEOMETRI DASAR MATA ROBOT XIAOZHI
// =========================================================================
static const int SCREEN_W = 128;
static const int SCREEN_H = 64;
static const int HUD_HEIGHT = 16;
static const int EYE_AREA_H = SCREEN_H - HUD_HEIGHT; // 48 piksel untuk mata

// Posisi & Ukuran Standar (XiaoZhi Architecture)
static const float BASE_EYE_WIDTH = 30.0f;
static const float BASE_EYE_HEIGHT = 34.0f;
static const float BASE_EYE_RADIUS = 8.0f;
static const float LEFT_BASE_X = 24.0f;
static const float RIGHT_BASE_X = 74.0f;
static const float BASE_EYE_Y = 6.0f;

// =========================================================================
// VARIABEL STATUS ANIMASI & EASING
// =========================================================================
static float curLeftX = LEFT_BASE_X;
static float curRightX = RIGHT_BASE_X;
static float curY = BASE_EYE_Y;
static float curW = BASE_EYE_WIDTH;
static float curH = BASE_EYE_HEIGHT;
static float curRadius = BASE_EYE_RADIUS;

// Easing Factor (0.0 < factor <= 1.0; 0.28 memberikan transisi yang mulus & kenyal)
static const float EASING_POS = 0.28f;
static const float EASING_SIZE = 0.35f;

// Lirikan Alami (Glance)
enum GlanceDirection {
  GLANCE_CENTER,
  GLANCE_LEFT,
  GLANCE_RIGHT,
  GLANCE_UP
};

static GlanceDirection currentGlance = GLANCE_CENTER;
static unsigned long nextGlanceTime = 0;

// Kedipan Alami (Blinking)
static bool isBlinking = false;
static unsigned long blinkStartTime = 0;
static const unsigned long BLINK_DURATION_MS = 140; // ms
static unsigned long nextBlinkTime = 0;

// Override Emosi Manual (misal saat AI merespon / berbicara)
static String manualEmotion = "";
static unsigned long manualEmotionEndTime = 0;

void setFaceEmotionOverride(const String &emotion, unsigned long durationMs) {
  manualEmotion = emotion;
  manualEmotion.toUpperCase();
  if (durationMs > 0) {
    manualEmotionEndTime = millis() + durationMs;
  } else {
    manualEmotionEndTime = 0;
  }
}

void clearFaceEmotionOverride() {
  manualEmotion = "";
  manualEmotionEndTime = 0;
}

String getActiveFaceEmotion() {
  if (manualEmotion.length() > 0) {
    if (manualEmotionEndTime == 0 || millis() < manualEmotionEndTime) {
      return manualEmotion;
    } else {
      manualEmotion = "";
    }
  }
  return "NORMAL";
}

void initRobotFace() {
  randomSeed(esp_random());
  nextGlanceTime = millis() + 2000;
  nextBlinkTime = millis() + 3500;
  curLeftX = LEFT_BASE_X;
  curRightX = RIGHT_BASE_X;
  curY = BASE_EYE_Y;
  curW = BASE_EYE_WIDTH;
  curH = BASE_EYE_HEIGHT;
  curRadius = BASE_EYE_RADIUS;
}

void drawRobotFace(Adafruit_SSD1306 &display, const PomodoroData &data) {
  unsigned long now = millis();

  // 1. Tentukan Emosi Aktif
  String emotion = getActiveFaceEmotion();
  if (emotion == "NORMAL") {
    emotion = data.emotion;
    emotion.toUpperCase();
  }

  // Prioritas Alert Distraksi
  if (data.alert == "HP!" || data.alert.indexOf("HP") >= 0) {
    emotion = "ANGRY";
  } else if (data.alert == "ABSEN!" || data.alert.indexOf("ABSEN") >= 0) {
    emotion = "SAD";
  }

  // 2. Evaluasi Kedipan Alami (Blink Cycle)
  if (emotion != "SLEEP" && emotion != "HAPPY") {
    if (!isBlinking && now >= nextBlinkTime) {
      isBlinking = true;
      blinkStartTime = now;
      nextBlinkTime = now + random(2800, 5200);
    }
  } else {
    isBlinking = false;
  }

  // 3. Evaluasi Lirikan Alami (Glance Cycle)
  if (emotion == "FOCUS") {
    currentGlance = GLANCE_CENTER; // Tatapan fokus ke pengguna saat sesi belajar aktif
  } else if (emotion == "THINKING") {
    currentGlance = GLANCE_UP;     // Menatap ke atas kanan saat berpikir
  } else if (!isBlinking && now >= nextGlanceTime) {
    int r = random(0, 100);
    if (r < 60) {
      currentGlance = GLANCE_CENTER;
    } else if (r < 75) {
      currentGlance = GLANCE_LEFT;
    } else if (r < 90) {
      currentGlance = GLANCE_RIGHT;
    } else {
      currentGlance = GLANCE_UP;
    }
    nextGlanceTime = now + random(2200, 4800);
  }

  // 4. Hitung Target Posisi & Offset
  float targetOffsetX = 0.0f;
  float targetOffsetY = 0.0f;
  float targetW = BASE_EYE_WIDTH;
  float targetH = BASE_EYE_HEIGHT;
  float targetRadius = BASE_EYE_RADIUS;

  switch (currentGlance) {
    case GLANCE_LEFT:  targetOffsetX = -6.0f; break;
    case GLANCE_RIGHT: targetOffsetX = 6.0f;  break;
    case GLANCE_UP:    targetOffsetY = -3.5f; break;
    case GLANCE_CENTER:
    default:           targetOffsetX = 0.0f; targetOffsetY = 0.0f; break;
  }

  // Efek Nafas Halus (Subtle Breathing: 1.2px, frekuensi 0.5Hz)
  if (emotion != "SLEEP") {
    float breath = sinf((float)now * 0.0032f) * 1.2f;
    targetOffsetY += breath;
  }

  // Modifikasi Target Berdasarkan Emosi
  if (emotion == "FOCUS") {
    targetH = 28.0f; // Sedikit menyipit fokus
  } else if (emotion == "SURPRISED") {
    targetH = 38.0f; // Membelalak kaget
    targetW = 32.0f;
  } else if (emotion == "THINKING") {
    // Menatap ke atas kanan dengan getaran halus mikir
    targetOffsetX = 5.0f;
    targetOffsetY = -4.0f;
    float shiver = sinf((float)now * 0.038f) * 2.2f;
    targetOffsetX += shiver;
  } else if (emotion == "SPEAKING") {
    // Pantulan ritmik robot berbicara (Audio Bounce ~3.5px)
    float voiceBounce = fabsf(sinf((float)now * 0.016f)) * 5.0f;
    targetOffsetY -= voiceBounce;
    targetH = 32.0f + sinf((float)now * 0.02f) * 4.0f;
  }

  // Kedipan Mata Menutup
  if (isBlinking) {
    unsigned long elapsed = now - blinkStartTime;
    if (elapsed < BLINK_DURATION_MS) {
      float blinkProgress = (elapsed < BLINK_DURATION_MS / 2)
        ? (float)elapsed / (BLINK_DURATION_MS / 2.0f)
        : 1.0f - ((float)(elapsed - BLINK_DURATION_MS / 2.0f) / (BLINK_DURATION_MS / 2.0f));
      targetH = targetH - (blinkProgress * (targetH - 3.0f));
      targetRadius = (targetH > 8.0f) ? (targetH / 3.0f) : 1.0f;
    } else {
      isBlinking = false;
    }
  }

  // 5. Physics Easing Interpolation (XiaoZhi Math)
  float targetLeftX = LEFT_BASE_X + targetOffsetX;
  float targetRightX = RIGHT_BASE_X + targetOffsetX;
  float targetY = BASE_EYE_Y + targetOffsetY;

  curLeftX  += (targetLeftX - curLeftX) * EASING_POS;
  curRightX += (targetRightX - curRightX) * EASING_POS;
  curY      += (targetY - curY) * EASING_POS;
  curW      += (targetW - curW) * EASING_SIZE;
  curH      += (targetH - curH) * EASING_SIZE;
  curRadius += (targetRadius - curRadius) * EASING_SIZE;

  // Nilai bulat untuk koordinat piksel
  int iLeftX = (int)(curLeftX + 0.5f);
  int iRightX = (int)(curRightX + 0.5f);
  int iY = (int)(curY + (BASE_EYE_HEIGHT - curH) * 0.5f);
  int iW = (int)(curW + 0.5f);
  int iH = (int)(curH + 0.5f);
  int iR = (int)(curRadius + 0.5f);
  if (iR < 1) iR = 1;
  if (iH < 2) iH = 2;

  // =========================================================================
  // 6. RENDER AREA MATA OLED (Y: 0 .. 47)
  // =========================================================================
  display.clearDisplay();

  if (emotion == "HAPPY") {
    // --- EKSPRESI GEMBIRA / SELEBRASI (^ _ ^) ---
    // Gambar kurva senyum tebal
    for (int t = 0; t < 5; t++) {
      display.drawLine(iLeftX, iY + 22 - t, iLeftX + iW / 2, iY + 7 - t, SSD1306_WHITE);
      display.drawLine(iLeftX + iW / 2, iY + 7 - t, iLeftX + iW, iY + 22 - t, SSD1306_WHITE);

      display.drawLine(iRightX, iY + 22 - t, iRightX + iW / 2, iY + 7 - t, SSD1306_WHITE);
      display.drawLine(iRightX + iW / 2, iY + 7 - t, iRightX + iW, iY + 22 - t, SSD1306_WHITE);
    }
    // Kilau Bintang Selebrasi di samping
    int starBob = ((now / 200) % 3);
    display.drawPixel(iLeftX - 6, iY + 11 + starBob, SSD1306_WHITE);
    display.drawPixel(iLeftX - 5, iY + 10 + starBob, SSD1306_WHITE);
    display.drawPixel(iRightX + iW + 5, iY + 11 - starBob, SSD1306_WHITE);
    display.drawPixel(iRightX + iW + 4, iY + 12 - starBob, SSD1306_WHITE);

  } else if (emotion == "SLEEP") {
    // --- EKSPRESI TIDUR / ISTIRAHAT (- -) ---
    for (int t = 0; t < 4; t++) {
      display.drawFastHLine(iLeftX, iY + 16 + t, iW, SSD1306_WHITE);
      display.drawFastHLine(iRightX, iY + 16 + t, iW, SSD1306_WHITE);
    }
    // Animasi Huruf Z Melayang
    int zCycle = (now / 600) % 3;
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    if (zCycle >= 0) { display.setCursor(110, 16); display.print("z"); }
    if (zCycle >= 1) { display.setCursor(116, 7);  display.print("Z"); }

  } else {
    // --- EKSPRESI SOLID: NORMAL / FOCUS / ANGRY / SAD / THINKING / SPEAKING ---
    display.fillRoundRect(iLeftX, iY, iW, iH, iR, SSD1306_WHITE);
    display.fillRoundRect(iRightX, iY, iW, iH, iR, SSD1306_WHITE);

    if (emotion == "ANGRY") {
      // Alis Miring Tegas Menukik ke Dalam (Peringatan HP!)
      display.fillTriangle(iLeftX + 6, iY, iLeftX + iW + 2, iY, iLeftX + iW + 2, iY + 15, SSD1306_BLACK);
      display.fillTriangle(iRightX - 2, iY, iRightX + iW - 6, iY, iRightX - 2, iY + 15, SSD1306_BLACK);

      // Garis Alis Tambahan di Atas
      display.drawLine(iLeftX, iY - 3, iLeftX + iW + 2, iY + 3, SSD1306_WHITE);
      display.drawLine(iRightX - 2, iY + 3, iRightX + iW, iY - 3, SSD1306_WHITE);

    } else if (emotion == "SAD") {
      // Kelopak Mata Sayu Menukik ke Luar (Pengguna Tidak di Tempat)
      display.fillTriangle(iLeftX - 2, iY, iLeftX + 12, iY, iLeftX - 2, iY + 14, SSD1306_BLACK);
      display.fillTriangle(iRightX + iW - 12, iY, iRightX + iW + 2, iY, iRightX + iW + 2, iY + 14, SSD1306_BLACK);

    } else if (!isBlinking && iH > 20) {
      // Pantulan Kilau Pupil Imut (XiaoZhi Specular Highlight)
      int hlOffset = (targetOffsetX > 1.0f) ? 3 : (targetOffsetX < -1.0f ? -3 : 0);
      display.fillRect(iLeftX + 17 + hlOffset, iY + 6, 4, 5, SSD1306_BLACK);
      display.fillRect(iRightX + 7 + hlOffset, iY + 6, 4, 5, SSD1306_BLACK);
    }
  }

  // =========================================================================
  // 7. MINI HUD CYBER POMODORO (Y: 48 .. 63)
  // =========================================================================
  display.drawFastHLine(0, 48, 128, SSD1306_WHITE);

  if (data.alert.length() > 0) {
    // Banner Alert Berkedip Invert (Hitam di atas latar Putih Menyala)
    bool alertInvert = ((now / 300) % 2 == 0);
    if (alertInvert) {
      display.fillRect(0, 50, 128, 14, SSD1306_WHITE);
      display.setTextColor(SSD1306_BLACK);
    } else {
      display.setTextColor(SSD1306_WHITE);
    }
    display.setTextSize(1);
    display.setCursor(4, 53);
    display.printf("! ALERT: %s !", data.alert.substring(0, 13).c_str());

  } else if (emotion == "SPEAKING") {
    // Status Saat AI Berbicara
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(6, 53);
    display.print("[AI] Menjawab Suara...");

  } else if (emotion == "THINKING") {
    // Status Saat AI Berpikir
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(6, 53);
    display.print("[AI] Sedang Berpikir...");

  } else if (data.is_active) {
    // Sesi Belajar Berjalan: Waktu Hitung Mundur & Fokus Skor
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(2, 53);
    display.printf("[%s] %s  F:%d%%",
      data.mode.length() > 0 ? data.mode.c_str() : "WORK",
      data.time_str.length() > 0 ? data.time_str.c_str() : "25:00",
      data.focus);

  } else {
    // Mode Siap / Standby
    display.setTextSize(1);
    display.setTextColor(SSD1306_WHITE);
    display.setCursor(8, 53);
    display.print("ASISTEN BELAJAR :: SIAP");
  }

  renderOLED();
}
