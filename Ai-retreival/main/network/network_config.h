#pragma once

// =========================================================================
// KONFIGURASI JARINGAN & SERVER BACKEND ASISTEN BELAJAR AI
// =========================================================================

#ifndef DEFAULT_WIFI_SSID
#define DEFAULT_WIFI_SSID "Sembarang 4G"
#endif

#ifndef DEFAULT_WIFI_PASSWORD
#define DEFAULT_WIFI_PASSWORD "oppo1915"
#endif

#ifndef BACKEND_SERVER_HOST
#define BACKEND_SERVER_HOST "192.168.1.3"
#endif

#ifndef BACKEND_SERVER_PORT
#define BACKEND_SERVER_PORT 5000
#endif

#define BACKEND_BASE_URL "http://" BACKEND_SERVER_HOST ":5000"
#define BACKEND_AI_VOICE_URL BACKEND_BASE_URL "/api/ai/voice"
#define BACKEND_ESP_POMODORO_URL BACKEND_BASE_URL "/api/esp/pomodoro"
#define BACKEND_HEALTH_URL BACKEND_BASE_URL "/api/health"
