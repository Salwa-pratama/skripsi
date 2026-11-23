#ifndef POMODORO_CONFIG_H
#define POMODORO_CONFIG_H

#include "server_config.h"

// =========================================================================
// KONFIGURASI SERVER POMODORO
// -------------------------------------------------------------------------
// URL server dipusatkan di include/server_config.h
// (POMODORO_SERVER_URL otomatis mengikuti SERVER_HOST).
// =========================================================================

// Interval polling data ke server (dalam milidetik)
#define POMODORO_POLL_INTERVAL_MS   1000

// Timeout koneksi HTTP agar tidak memblokir animasi OLED.
#define POMODORO_HTTP_TIMEOUT_MS    150

#endif // POMODORO_CONFIG_H
