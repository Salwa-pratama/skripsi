#include "camera_server.h"
#include <WiFi.h>

// Fungsi utama untuk setup WiFi dan Server
void setupWiFiAndServer(const char* ssid, const char* password) {
  Serial.print("\nMenghubungkan ke WiFi: ");
  Serial.println(ssid);

  WiFi.mode(WIFI_STA);

  // Static IP agar alamat ESP32 selalu sama (192.168.1.50) sesuai subnet router 192.168.1.x
  IPAddress local_IP(192, 168, 1, 50);
  IPAddress gateway(192, 168, 1, 1);
  IPAddress subnet(255, 255, 255, 0);
  IPAddress primaryDNS(192, 168, 1, 1);
  IPAddress secondaryDNS(8, 8, 8, 8);

  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("Gagal set static IP, lanjut pakai DHCP...");
  } else {
    Serial.println("Static IP ESP32: 192.168.1.50");
  }

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
    // Menjalankan HTTP Web Server lengkap dengan UI Setting bawaan Espressif
    startCameraServer();
  } else {
    Serial.println("\n[WIFI TIMEOUT] Hotspot tidak terdeteksi. Berjalan di Mode Offline!");
    Serial.println("[INFO] Layar Wajah Robot Mochi tetap beranimasi normal di loop utama.");
  }
}
