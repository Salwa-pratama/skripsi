#include "camera_server.h"
#include <WiFi.h>
#include <esp_wifi.h>

// Fungsi utama untuk setup WiFi dan Server
void setupWiFiAndServer(const char* ssid, const char* password) {
  Serial.print("\nMenghubungkan ke WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);

  // DHCP: IP mengikuti subnet hotspot apa pun (tidak di-hardcode).
  // IP hasil DHCP dilaporkan otomatis ke backend lewat query ?ip=... pada
  // polling /api/esp/pomodoro, sehingga URL stream di backend ikut diperbarui.
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
    Serial.print("Buka browser di laptop dan ketik IP ini -> http://");
    Serial.println(WiFi.localIP());

    // Maksimalkan daya pancar & matikan modem sleep secara permanen setelah koneksi berhasil
    // Menghilangkan latency ping 500-3000ms -> turun ke ~2ms (anti-drop stream kamera)
    WiFi.setTxPower(WIFI_POWER_19_5dBm);
    WiFi.setSleep(false);
    esp_wifi_set_ps(WIFI_PS_NONE);
    Serial.printf("[WIFI] TxPower: 19.5 dBm | Modem Sleep: OFF | RSSI: %d dBm\n", WiFi.RSSI());
    // Catatan: Web server kamera (startCameraServer) dijalankan terpisah di Core 0
    // melalui task cameraCore0Task setelah kamera selesai diinisialisasi.
  } else {
    Serial.println("\n[WIFI TIMEOUT] Hotspot tidak terdeteksi. Berjalan di Mode Offline!");
    Serial.println("[INFO] Layar Wajah Robot Mochi tetap beranimasi normal di loop utama.");
  }
}
