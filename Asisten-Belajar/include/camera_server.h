#ifndef CAMERA_SERVER_H
#define CAMERA_SERVER_H

#include <Arduino.h>

// Deklarasi fungsi untuk konek WiFi dan nyalakan server
void setupWiFiAndServer(const char* ssid, const char* password);
void startCameraServer(); // Deklarasi fungsi penyala server dari file app_httpd.cpp

#endif
