#ifndef AUDIO_TEST_H
#define AUDIO_TEST_H

#include <Arduino.h>

// =========================================================================
// DEFINISI PIN MODUL AUDIO ESP32-S3 (BEBAS DARI BENTROK KAMERA & PSRAM)
// =========================================================================
// 1. Bus I2S Digital Audio (Clock & Word Select Bersama)
#define I2S_BCLK_PIN        42   // Deret Kanan Pin 5 (BCLK MAX98357A & SCK INMP441)
#define I2S_WS_PIN          41   // Deret Kanan Pin 6 (LRC MAX98357A & WS INMP441)

// 2. Modul Speaker MAX98357A (Data In)
// ⚠️ JANGAN PAKAI GPIO 2 DI BOARD FREENOVE ESP32-S3 WROOM!
// GPIO 2 terhubung ke LED onboard (IO2) melalui resistor. Kalau dipakai sebagai
// I2S DIN, level HIGH sinyal audio dijepit oleh LED (~2V) sehingga MAX98357A
// salah baca bit -> suara kemresek/pecah, dan LED onboard menyala mengikuti
// data audio (terlihat seperti "lampu merah nyala sendiri").
// GPIO 1 bebas dari kamera, OLED, mic, PSRAM, dan LED onboard.
#define I2S_SPK_DIN_PIN      1   // Deret Kanan Pin 3 (DIN MAX98357A) - PIN BARU

// 2b. Modul Speaker MAX98357A Shutdown / Enable Pin (SD)
// Menyuplai 3.3V logic HIGH ke pin SD amplifier lewat GPIO, sehingga user
// TIDAK PERLU menumpuk solderan 3 kabel di pin 3V3 ESP32!
// Hubungkan pin SD MAX98357A ke GPIO 40 (Deret Kanan Pin 7, tepat di bawah WS GPIO 41).
#define I2S_SPK_SD_PIN      40   // Deret Kanan Pin 7 (SD MAX98357A Enable)

// 3. Modul Mikrofon INMP441 (Data Out)
#define I2S_MIC_SD_PIN      14   // Deret Kiri Pin 19 (SD INMP441)

// =========================================================================
// VOLUME SPEAKER (PERSEN) - DIKUNCI 100%
// -------------------------------------------------------------------------
// MAX98357A tidak punya register volume digital; kenyaringan diatur oleh
// amplitudo sampel PCM yang kita kirim + gain hardware (resistor GAIN).
// Nilai ini dipakai oleh playTone()/playDistractionAlertSound()/playSuccessChime()
// sehingga SEMUA bunyi keluar pada amplitudo penuh (32767/32767 = 100%).
// Ubah ke 100 bila ingin benar-benar maksimal (default).
// =========================================================================
#define SPEAKER_MASTER_VOLUME_PERCENT 100

// =========================================================================
// DEKLARASI DATA AUDIO RAW (510 - ALIVE) DARI CLIP.S
// =========================================================================
extern const uint8_t clip_start[] asm("clip_start");
extern const uint8_t clip_end[]   asm("clip_end");

// =========================================================================
// DEKLARASI FUNGSI SUBSISTEM AUDIO
// =========================================================================
void setupAudioSystem();
void initI2SSpeaker(int sampleRate = 16000);
void initI2SMicrophone(int sampleRate = 16000, bool rightChannel = false);

// Output Suara (Speaker MAX98357A)
void playTone(int freqHz, int durationMs);
void playDistractionAlertSound();     // Nada peringatan keras saat terdeteksi distraksi HP
void playSuccessChime();             // Melodi ceria saat selesai sesi belajar / apresiasi AI
bool playWavFromUrl(const char* url); // Streaming suara AI (Bahasa Indonesia 16kHz) dari Server

// Input Suara & Voice Trigger (Mikrofon INMP441)
int readMicPeak();
bool detectVoiceTrigger(int threshold = 1200);

// Baca sample mikrofon INMP441 yang sudah dikonversi ke PCM 16-bit mono.
// Dipakai oleh voice_client.cpp untuk merekam pertanyaan user menjadi WAV.
size_t readMicSamples(int16_t* out, size_t maxSamples, uint32_t timeoutMs = 60);

// Mode Diagnostik & Pengujian Audio Lengkap (Mode 5)
void setupAudioTest();
void loopAudioTest();

// Mode 6: Diagnostik khusus mikrofon INMP441 (VU meter + verdict wiring)
void setupMicTest();
void loopMicTest();

// Mode 7: tes speaker murni, struktur playback disamakan dengan C3 play_music.
void setupSpeakerOnlyTest();
void loopSpeakerOnlyTest();

// Mode 8: nada uji level rendah untuk memeriksa respons speaker/amplifier.
void setupAmpToneDiagnostic();
void loopAmpToneDiagnostic();

// Mode 9: MAX98357A tone test using classic 16-bit stereo C3 I2S format.
void setupAmpStereoToneDiagnostic();
void loopAmpStereoToneDiagnostic();

#endif // AUDIO_TEST_H
