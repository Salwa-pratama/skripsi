#include "wifi_manager.h"
#include <WiFi.h>
#include <esp_wifi.h>

// =========================================================================
// KONEKSI WIFI ESP32-S3 (DHCP)
// =========================================================================
void setupWiFiAndServer(const char* ssid, const char* password) {
  Serial.print("\nMenghubungkan ke WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);

  // DHCP: IP mengikuti subnet hotspot apa pun (tidak di-hardcode).
  Serial.println("Mode IP: DHCP (otomatis dari hotspot)");

  WiFi.begin(ssid, password);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 20) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi Terhubung!");
    Serial.print("IP ESP32-S3: http://");
    Serial.println(WiFi.localIP());

    // Daya pancar maksimal & modem sleep OFF agar upload audio & polling
    // Pomodoro tetap responsif.
    WiFi.setTxPower(WIFI_POWER_19_5dBm);
    WiFi.setSleep(false);
    esp_wifi_set_ps(WIFI_PS_NONE);
    Serial.printf("[WIFI] TxPower: 19.5 dBm | Modem Sleep: OFF | RSSI: %d dBm\n", WiFi.RSSI());
  } else {
    Serial.println("\n[WIFI TIMEOUT] Hotspot tidak terdeteksi. Berjalan di Mode Offline!");
    Serial.println("[INFO] Layar Wajah Robot Mochi tetap beranimasi normal di loop utama.");
  }
}
