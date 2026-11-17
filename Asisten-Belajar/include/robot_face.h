#ifndef ROBOT_FACE_H
#define ROBOT_FACE_H

#include "oled_config.h"
#include "pomodoro_client.h"

// Inisialisasi status wajah robot
void initRobotFace();

// Render frame animasi mata robot Mochi dengan status pomodoro & ekspresi emosi realtime
void drawRobotFace(Adafruit_SSD1306 &display, const PomodoroData &data);

// Kontrol override ekspresi manual (misal saat AI berpikir atau berbicara)
void setFaceEmotionOverride(const String &emotion, unsigned long durationMs = 0);
void clearFaceEmotionOverride();
String getActiveFaceEmotion();

#endif // ROBOT_FACE_H
