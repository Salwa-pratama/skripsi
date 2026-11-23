#include "pomodoro_client.h"
#include "pomodoro_config.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

static PomodoroData currentData = {
  .mode = "IDLE",
  .status = "STOPPED",
  .time_str = "00:00",
  .time_left = 0,
  .cycle_str = "0/0",
  .task = "",
  .alert = "",
  .emotion = "NORMAL",
  .focus = 100,
  .is_valid = false,
  .is_active = false,
  .last_sync = 0
};

static unsigned long lastPollTime = 0;

void setupPomodoroClient() {
  Serial.println("[POMODORO] Menginisialisasi Client Pomodoro...");
  Serial.printf("[POMODORO] Target URL: %s\n", POMODORO_SERVER_URL);
}

void updatePomodoroClient() {
  // Hanya fetch jika WiFi sudah terhubung
  if (WiFi.status() != WL_CONNECTED) {
    return;
  }

  // Polling non-blocking sesuai interval
  unsigned long now = millis();
  if (now - lastPollTime < POMODORO_POLL_INTERVAL_MS) {
    return;
  }
  lastPollTime = now;

  WiFiClient client;
  HTTPClient http;

  // Polling status Pomodoro untuk HUD OLED.
  // Fitur laporan IP untuk stream kamera sudah dihapus.
  const char* pollUrl = POMODORO_SERVER_URL;

  http.setTimeout(POMODORO_HTTP_TIMEOUT_MS);
  if (!http.begin(client, pollUrl)) {
    return;
  }

  int httpCode = http.GET();
  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();

    // Respons ~140 bytes, alokasi 512 bytes sangat aman di RAM
    JsonDocument doc;
    DeserializationError error = deserializeJson(doc, payload);

    if (!error) {
      currentData.mode = doc["mode"].as<const char*>() ? doc["mode"].as<const char*>() : "IDLE";
      currentData.status = doc["status"].as<const char*>() ? doc["status"].as<const char*>() : "STOPPED";
      currentData.time_str = doc["time_str"].as<const char*>() ? doc["time_str"].as<const char*>() : "00:00";
      currentData.time_left = doc["time_left"] | 0;
      currentData.cycle_str = doc["cycle_str"].as<const char*>() ? doc["cycle_str"].as<const char*>() : "-/-";
      currentData.task = doc["task"].as<const char*>() ? doc["task"].as<const char*>() : "";
      currentData.alert = doc["alert"].as<const char*>() ? doc["alert"].as<const char*>() : "";
      currentData.emotion = doc["emotion"].as<const char*>() ? doc["emotion"].as<const char*>() : "NORMAL";
      currentData.focus = doc["focus"] | 100;
      currentData.is_valid = true;
      currentData.last_sync = now;

      // Status aktif jika sesi sedang RUNNING atau PAUSED
      String st = currentData.status;
      st.toUpperCase();
      if (st == "RUNNING" || st == "PAUSED") {
        currentData.is_active = true;
      } else {
        currentData.is_active = false;
      }
    } else {
      Serial.printf("[POMODORO ERROR] Gagal parse JSON: %s\n", error.c_str());
    }
  } else {
    // Jika server tidak membalas / error HTTP
    // Jika sudah > 10 detik tidak ada balasan dari server, nonaktifkan mode pomodoro
    if (now - currentData.last_sync > 10000 && currentData.last_sync > 0) {
      currentData.is_active = false;
    }
  }

  http.end();
}

const PomodoroData& getPomodoroData() {
  return currentData;
}

bool isPomodoroActive() {
  return currentData.is_active;
}
