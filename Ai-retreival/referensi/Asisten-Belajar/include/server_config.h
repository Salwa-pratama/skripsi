#ifndef SERVER_CONFIG_H
#define SERVER_CONFIG_H

// =========================================================================
// KONFIGURASI ALAMAT SERVER ASISTEN BELAJAR
// -------------------------------------------------------------------------
// Ubah SERVER_HOST jika IP laptop/PC server berubah.
// IP laptop saat ini: 192.168.1.3
// =========================================================================
#define SERVER_HOST            "192.168.1.3"
#define SERVER_PORT            5000
#define SERVER_BASE_URL        "http://" SERVER_HOST ":5000"

// Endpoint pertanyaan suara (multipart WAV -> STT -> fine-tuned SBERT -> TTS)
#define AI_VOICE_URL           SERVER_BASE_URL "/api/ai/voice"

// Endpoint pertanyaan teks (untuk pengujian via Serial/HTTP)
#define AI_ASK_URL             SERVER_BASE_URL "/api/ai/ask"

// Endpoint status Pomodoro untuk HUD OLED
#define POMODORO_SERVER_URL    SERVER_BASE_URL "/api/esp/pomodoro"

#endif // SERVER_CONFIG_H
