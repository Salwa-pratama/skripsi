#ifndef POMODORO_CLIENT_H
#define POMODORO_CLIENT_H

#include <Arduino.h>

// Struktur Data Status Pomodoro dari Server Flask
struct PomodoroData {
  String mode;             // "WORK", "BREAK", "REST"
  String status;           // "RUNNING", "PAUSED", "STOPPED", "IDLE"
  String time_str;         // "24:58"
  int time_left;           // Detik tersisa (misal 1498)
  String cycle_str;        // "1/4"
  String task;             // "Belajar AI"
  String alert;            // Pesan peringatan (kosong jika aman)
  String emotion;          // "NORMAL", "FOCUS", "ANGRY", "SURPRISED", "HAPPY", "SLEEP"
  int focus;               // Persentase fokus (0 - 100)
  bool is_valid;           // True jika berhasil parse dari server
  bool is_active;          // True jika status aktif (RUNNING/PAUSED)
  unsigned long last_sync; // Waktu timestamp sinkron terakhir (millis)
};

// Fungsi Lifecycle & Akses
void setupPomodoroClient();
void updatePomodoroClient();
const PomodoroData& getPomodoroData();
bool isPomodoroActive();

#endif // POMODORO_CLIENT_H
