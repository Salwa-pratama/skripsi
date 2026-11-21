#ifndef POMODORO_CONFIG_H
#define POMODORO_CONFIG_H

// =========================================================================
// KONFIGURASI SERVER FLASK & ENDPOINT POMODORO
// =========================================================================

// Ganti "localhost" di bawah ini dengan alamat IP Laptop/Komputer Server Flask kamu
// Contoh: "http://192.168.1.10:5000/api/esp/pomodoro"
// IP laptop di hotspot "ananda" saat ini: 10.19.170.155
#define POMODORO_SERVER_URL    "http://10.19.170.155:5000/api/esp/pomodoro"

// Interval polling data ke server Flask (dalam milidetik)
#define POMODORO_POLL_INTERVAL_MS   1000

// Timeout koneksi HTTP agar tidak memblokir/mengganggu frame rate kamera OV5640 atau animasi OLED
#define POMODORO_HTTP_TIMEOUT_MS    150

#endif // POMODORO_CONFIG_H
