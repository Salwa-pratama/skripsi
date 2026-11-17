#ifndef CYBER_DISPLAY_H
#define CYBER_DISPLAY_H

#include "oled_config.h"
#include "pomodoro_client.h"

// Render tampilan Pomodoro bertema Cyberpunk / Cyber Crime HUD
void drawCyberPomodoro(Adafruit_SSD1306 &display, const PomodoroData &data);

#endif // CYBER_DISPLAY_H
