# Asisten Belajar — Firmware ESP32-S3

Firmware robot pendamping belajar berbasis **Freenove ESP32-S3 WROOM**.
Kamera OV5640 sudah **dinonaktifkan total** beserta seluruh pin dan web server
kameranya.

## Peran ESP32

1. Menampilkan wajah robot / HUD Pomodoro di OLED SSD1306 128×64.
2. Merekam pertanyaan user dari mikrofon INMP441.
3. Mengunggah WAV 16 kHz ke server (`POST /api/ai/voice`).
4. Menampilkan teks jawaban hasil fine-tuned SBERT di bawah mata robot
   (marquee kanan → kiri).
5. Memutar suara jawaban Bahasa Indonesia (cowok/Ardi) ke speaker MAX98357A.
6. Polling status Pomodoro untuk HUD OLED.

## Pin yang Dipakai

| Modul | Pin |
|-------|-----|
| OLED SDA | GPIO 47 |
| OLED SCL | GPIO 21 |
| I2S BCLK (mic + speaker) | GPIO 42 |
| I2S WS / LRC | GPIO 41 |
| Speaker DIN MAX98357A | GPIO 1 |
| Speaker SD / Enable | GPIO 40 |
| Mic SD INMP441 | GPIO 14 |
| Status LED | GPIO 48 |

Pin kamera OV5640 (4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15, 16, 17, 18)
**tidak diinisialisasi** dan bebas dipakai untuk keperluan lain.

## Mode Kerja

| Mode | Fungsi |
|------|--------|
| 1 | Diagnostik seluruh GPIO |
| 2 | Diagnostik OLED / scanner I2C |
| 3 | **Full System** — OLED + Voice AI + WiFi (default) |
| 4 | OLED + Pomodoro HUD saja |
| 5 | Tes audio interaktif |
| 6 | Diagnostik mikrofon INMP441 |
| 7 | Tes speaker murni |
| 8 | Diagnostik amplifier MAX98357A |
| 9 | Pembanding format C3 16-bit stereo |

Pilih mode lewat Serial Monitor saat boot (3 detik), atau ubah `modeTes` di
`src/main.cpp`.

## Konfigurasi Server

Alamat server dipusatkan di `include/server_config.h`:

```cpp
#define SERVER_HOST "10.19.170.155"
#define SERVER_PORT 5000
```

Ubah `SERVER_HOST` jika IP laptop/server berubah.

## Build & Upload

```bash
cd Asisten-Belajar
pio run
pio run --target upload
pio device monitor
```

## Catatan Voice Trigger

- Mikrofon memicu rekaman saat peak > `18000`.
- Rekaman berhenti otomatis setelah hening 1,2 detik, maksimal 8 detik.
- Cooldown 4 detik setelah setiap interaksi agar suara speaker tidak memicu
  pertanyaan baru.
- Selama upload/proses, wajah OLED masuk mode `THINKING`; saat memutar jawaban
  masuk mode `SPEAKING`.

## File Penting

- `src/main.cpp` — alur utama, mode, voice trigger.
- `src/func/voice_client.cpp` — rekam, upload multipart WAV, tampilkan teks, putar TTS.
- `src/func/audio_test.cpp` — driver I2S mic/speaker, playback WAV.
- `src/func/robot_face.cpp` — animasi mata + marquee teks jawaban.
- `include/server_config.h` — alamat server.
