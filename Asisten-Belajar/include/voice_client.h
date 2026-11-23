#ifndef VOICE_CLIENT_H
#define VOICE_CLIENT_H

#include <Arduino.h>

// Inisialisasi subsistem pertanyaan suara (mic INMP441 -> server AI).
void setupVoiceClient();

// Rekam pertanyaan user dari mikrofon, upload ke server, lalu putar jawaban
// TTS dan tampilkan teks jawaban di OLED. Return true jika berhasil.
bool askVoiceAssistantFromMic();

#endif // VOICE_CLIENT_H
