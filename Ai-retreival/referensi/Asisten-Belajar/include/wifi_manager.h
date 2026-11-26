#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <Arduino.h>

// Menghubungkan ESP32-S3 ke WiFi (mode DHCP).
// Catatan: fitur web server kamera sudah dihapus total.
void setupWiFiAndServer(const char* ssid, const char* password);

#endif // WIFI_MANAGER_H
