#include "audio_test.h"
#include "oled_config.h"
#include <driver/i2s.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <math.h>

// =========================================================================
// DEFINISI PARAMETER AUDIO & BUFFER
// =========================================================================
#define I2S_PORT                I2S_NUM_0
#define DMA_BUFFER_LEN          512
#define DMA_BUFFER_COUNT        8

#if I2S_SPK_DIN_PIN == 2
#warning "I2S_SPK_DIN_PIN = GPIO2 = LED onboard Freenove ESP32-S3. Suara akan kemresek!"
#endif

static bool i2sInitialized = false;
static bool currentI2sIsSpeaker = false;
static bool currentMicRightChannel = false;
static int currentSampleRate = 0;

// =========================================================================
// INISIALISASI DRIVER I2S UNTUK SPEAKER (MAX98357A - MODE TX)
// =========================================================================
void initI2SSpeaker(int sampleRate) {
  if (i2sInitialized && currentI2sIsSpeaker && currentSampleRate == sampleRate) {
    return; // Sudah siap dalam mode speaker dengan sample rate sama
  }

  if (i2sInitialized) {
    i2s_driver_uninstall(I2S_PORT);
    i2sInitialized = false;
  }

  i2s_config_t spk_config = {
    // KONFIGURASI INI SAMA PERSIS DENGAN play_music.sh / tools/speaker_test:
    // 24 kHz, 16-bit, stereo, STAND_I2S, 8 x 512 DMA, tanpa APLL.
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = (uint32_t)sampleRate,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = DMA_BUFFER_COUNT,
    .dma_buf_len = DMA_BUFFER_LEN,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_BCLK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_SPK_DIN_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  esp_err_t installErr = i2s_driver_install(I2S_PORT, &spk_config, 0, NULL);
  if (installErr != ESP_OK) {
    Serial.printf("[I2S ERROR] Driver speaker gagal dipasang: %s\n",
                  esp_err_to_name(installErr));
    return;
  }

  esp_err_t pinErr = i2s_set_pin(I2S_PORT, &pin_config);
  if (pinErr != ESP_OK) {
    Serial.printf("[I2S ERROR] Konfigurasi pin gagal: %s (BCLK=%d WS=%d DIN=%d)\n",
                  esp_err_to_name(pinErr), I2S_BCLK_PIN, I2S_WS_PIN, I2S_SPK_DIN_PIN);
    i2s_driver_uninstall(I2S_PORT);
    return;
  }
  i2s_zero_dma_buffer(I2S_PORT);

  // Aktifkan amplifier MAX98357A via GPIO SD pin (3.3V logic HIGH)
  pinMode(I2S_SPK_SD_PIN, OUTPUT);
  digitalWrite(I2S_SPK_SD_PIN, HIGH);

  i2sInitialized = true;
  currentI2sIsSpeaker = true;
  currentSampleRate = sampleRate;
}

// =========================================================================
// INISIALISASI DRIVER I2S UNTUK MIKROFON (INMP441 - MODE RX)
// =========================================================================
void initI2SMicrophone(int sampleRate, bool rightChannel) {
  if (i2sInitialized && !currentI2sIsSpeaker && currentSampleRate == sampleRate &&
      currentMicRightChannel == rightChannel) {
    return; // Sudah siap dalam mode mikrofon dengan sample rate & channel sama
  }

  // Nonaktifkan amplifier MAX98357A (SD = LOW) saat merekam dari mic
  // agar tidak ada arus switching / kebocoran suara ke mikrofon
  pinMode(I2S_SPK_SD_PIN, OUTPUT);
  digitalWrite(I2S_SPK_SD_PIN, LOW);

  if (i2sInitialized) {
    i2s_driver_uninstall(I2S_PORT);
    i2sInitialized = false;
  }

  i2s_config_t mic_config = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
    .sample_rate = (uint32_t)sampleRate,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT, // INMP441 kirim 24-bit dalam slot 32-bit
    .channel_format = rightChannel ? I2S_CHANNEL_FMT_ONLY_RIGHT
                                   : I2S_CHANNEL_FMT_ONLY_LEFT, // L/R ke GND = LEFT
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 4,
    .dma_buf_len = 256,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };

  i2s_pin_config_t pin_config = {
    .bck_io_num = I2S_BCLK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = I2S_MIC_SD_PIN
  };

  i2s_driver_install(I2S_PORT, &mic_config, 0, NULL);
  i2s_set_pin(I2S_PORT, &pin_config);
  i2s_zero_dma_buffer(I2S_PORT);

  i2sInitialized = true;
  currentI2sIsSpeaker = false;
  currentMicRightChannel = rightChannel;
  currentSampleRate = sampleRate;
}

// =========================================================================
// SYNTHESIS & PLAYBACK AUDIO SINE WAVE KE SPEAKER
// =========================================================================
void playTone(int freqHz, int durationMs) {
  initI2SSpeaker(16000);

  int totalSamples = (16000 * durationMs) / 1000;
  if (totalSamples <= 0) return;

  int16_t buffer[128 * 2]; // Stereo L+R
  int chunkSize = 128;
  float phase = 0.0f;
  float phaseIncrement = (2.0f * (float)M_PI * (float)freqHz) / 16000.0f;
  // Volume dikunci ke SPEAKER_MASTER_VOLUME_PERCENT (100% = amplitudo PCM penuh).
  int amplitude = (freqHz == 0) ? 0
                                : (int)((32767L * (long)SPEAKER_MASTER_VOLUME_PERCENT) / 100L);

  int remaining = totalSamples;
  while (remaining > 0) {
    int toGen = (remaining > chunkSize) ? chunkSize : remaining;
    for (int i = 0; i < toGen; i++) {
      int16_t sample = 0;
      if (freqHz > 0) {
        sample = (int16_t)(sinf(phase) * (float)amplitude);
        phase += phaseIncrement;
        if (phase >= 2.0f * (float)M_PI) phase -= 2.0f * (float)M_PI;
      }
      buffer[i * 2]     = sample; // Left
      buffer[i * 2 + 1] = sample; // Right
    }

    size_t bytesWritten = 0;
    i2s_write(I2S_PORT, buffer, toGen * 2 * sizeof(int16_t), &bytesWritten, portMAX_DELAY);
    remaining -= toGen;
  }
}

// Nada Peringatan Distraksi HP (Dua beep tegas bernada tinggi)
void playDistractionAlertSound() {
  playTone(880, 150); // A5
  delay(50);
  playTone(880, 200); // A5
  i2s_zero_dma_buffer(I2S_PORT);
}

// Melodi Ceria Selebrasi Selesai Sesi / Jawaban AI Siap
void playSuccessChime() {
  playTone(523, 100); // C5
  delay(30);
  playTone(659, 100); // E5
  delay(30);
  playTone(784, 180); // G5
  i2s_zero_dma_buffer(I2S_PORT);
}

// =========================================================================
// STREAMING FILE AUDIO WAV (16kHz, 16-BIT STEREO) DARI SERVER
// =========================================================================
bool playWavFromUrl(const char* url) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[AUDIO] WiFi tidak tersambung, batal streaming audio.");
    return false;
  }

  initI2SSpeaker(16000);

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(8000);

  Serial.printf("[AUDIO] Mengambil audio stream: %s\n", url);
  if (!http.begin(client, url)) {
    Serial.println("[AUDIO ERROR] Gagal inisialisasi HTTP client.");
    return false;
  }

  int httpCode = http.GET();
  if (httpCode != HTTP_CODE_OK) {
    Serial.printf("[AUDIO ERROR] HTTP GET kode: %d\n", httpCode);
    http.end();
    return false;
  }

  int totalBytes = http.getSize();
  WiFiClient *stream = http.getStreamPtr();

  // Lewati 44 bytes WAV Header standar
  uint8_t wavHeader[44];
  int headerRead = stream->readBytes(wavHeader, 44);
  if (headerRead < 44) {
    Serial.println("[AUDIO ERROR] Header WAV tidak valid atau terpotong.");
    http.end();
    return false;
  }

  // Buffer chunk streaming
  uint8_t buffer[512];
  int remaining = (totalBytes > 44) ? (totalBytes - 44) : -1;
  unsigned long startPlay = millis();

  while (http.connected() && (remaining > 0 || remaining == -1)) {
    size_t availableBytes = stream->available();
    if (availableBytes > 0) {
      int toRead = (availableBytes > sizeof(buffer)) ? sizeof(buffer) : availableBytes;
      if (remaining > 0 && toRead > remaining) toRead = remaining;

      int bytesRead = stream->readBytes(buffer, toRead);
      if (bytesRead > 0) {
        // Boost digital gain 2.0x dengan batas saturasi (cegah distorsi)
        int16_t* pcm16 = (int16_t*)buffer;
        int numSamples = bytesRead / sizeof(int16_t);
        for (int i = 0; i < numSamples; ++i) {
          int32_t val = (int32_t)(pcm16[i] * 2.0f);
          pcm16[i] = (int16_t)constrain(val, -32768, 32767);
        }

        size_t written = 0;
        i2s_write(I2S_PORT, buffer, bytesRead, &written, portMAX_DELAY);
        if (remaining > 0) remaining -= bytesRead;
      }
    } else {
      delay(2);
      if (millis() - startPlay > 15000) break;
    }
  }

  i2s_zero_dma_buffer(I2S_PORT);
  http.end();
  Serial.println("[AUDIO] Pemutaran audio WAV selesai.");
  return true;
}

// =========================================================================
// PEMBACAAN AMPLITUDO MIKROFON (INMP441)
// =========================================================================
int readMicPeak() {
  initI2SMicrophone(16000);

  int32_t rawSamples[128];
  size_t bytesRead = 0;
  esp_err_t err = i2s_read(I2S_PORT, rawSamples, sizeof(rawSamples), &bytesRead, pdMS_TO_TICKS(40));

  int32_t peak = 0;
  if (err == ESP_OK && bytesRead > 0) {
    int samplesCount = bytesRead / sizeof(int32_t);
    for (int i = 0; i < samplesCount; i++) {
      int32_t val = rawSamples[i] >> 14;
      if (val < 0) val = -val;
      if (val > peak) peak = val;
    }
  }
  return (int)peak;
}

// Voice Trigger / Voice Activity Detection (VAD) via Mikrofon INMP441
bool detectVoiceTrigger(int threshold) {
  int peak = readMicPeak();
  return (peak >= threshold);
}

// =========================================================================
// BACA SAMPLE MIKROFON UNTUK PEREKAMAN WAV (PCM 16-bit MONO)
// -------------------------------------------------------------------------
// INMP441 mengirim 24-bit di dalam slot 32-bit. Nilai >> 14 dipakai agar
// skalanya konsisten dengan readMicPeak() (threshold VAD 18000), lalu
// di-clamp ke int16 supaya aman ditulis sebagai PCM WAV.
// =========================================================================
size_t readMicSamples(int16_t* out, size_t maxSamples, uint32_t timeoutMs) {
  if (!out || maxSamples == 0) return 0;

  initI2SMicrophone(16000);

  static int32_t rawSamples[512];
  size_t toRead = (maxSamples > 512) ? 512 : maxSamples;
  size_t bytesRead = 0;

  esp_err_t err = i2s_read(
    I2S_PORT,
    rawSamples,
    toRead * sizeof(int32_t),
    &bytesRead,
    (timeoutMs == 0 ? 1 : timeoutMs) / portTICK_PERIOD_MS
  );

  if (err != ESP_OK || bytesRead == 0) return 0;

  size_t count = bytesRead / sizeof(int32_t);
  for (size_t i = 0; i < count; i++) {
    int32_t val = rawSamples[i] >> 14;
    out[i] = (int16_t)constrain(val, -32768, 32767);
  }
  return count;
}

// =========================================================================
// INISIALISASI SUBSISTEM AUDIO (UNTUK MODE FULL SYSTEM)
// =========================================================================
void setupAudioSystem() {
  initI2SSpeaker(16000);
  Serial.println("[AUDIO] Subsistem Audio ESP32-S3 Siap (MAX98357A Speaker & INMP441 Mic)!");
  Serial.println("[AUDIO] Mode Komunikasi: VOICE TRIGGER (Mikrofon Otomatis).");
}

// =========================================================================
// MODE 5: DIAGNOSTIK & TESTER HARDWARE AUDIO INTERAKTIF (SPEAKER & MIC)
// =========================================================================

enum AudioTestSubMode {
  SUBMODE_MUSIC,  // Memutar musik 510 - ALIVE (24kHz Hi-Fi)
  SUBMODE_MIC     // Menampilkan VU Meter & Level Realtime Mikrofon INMP441
};

static AudioTestSubMode currentSubMode = SUBMODE_MUSIC;
// Multiplier volume software (PCM clip peak 6058/32767).
// Nilai 3.0x menghasilkan amplitudo ~18200/32767 (~55% full scale, lantang & jernih).
static float volume_mult = 3.0f;
static size_t music_sample_idx = 0;
static unsigned long lastOledUpdate = 0;
static unsigned long lastMicPrint = 0;

static void printAudioHelp() {
  Serial.println("\n======================================================================");
  Serial.println("  🎵🎤 PENGUJIAN AUDIO INTERAKTIF ESP32-S3 (SPEAKER & MIKROFON INMP441)");
  Serial.println("======================================================================");
  Serial.println("Hardware Terpasang (Bus I2S Bersama):");
  Serial.println("  * BCLK (Bit Clock)     : GPIO 42 (MAX98357A & INMP441)");
  Serial.println("  * WS / LRC (Word Sel)  : GPIO 41 (MAX98357A & INMP441)");
  Serial.println("  * DIN (Speaker Out)    : GPIO 1  (MAX98357A)  <-- PIN BARU!");
  Serial.println("  * SD (Mic Data In)     : GPIO 14 (INMP441)");
  Serial.println("  * GND & VCC            : GND Exoskeleton & 3.3V ESP32");
  Serial.println("----------------------------------------------------------------------");
  Serial.println("CATATAN PENTING:");
  Serial.println("  GPIO 2 di board Freenove ESP32-S3 WROOM adalah pin LED onboard.");
  Serial.println("  GPIO 2 terhubung ke LED onboard; jangan gunakan untuk DIN.");
  Serial.println("  Pastikan kabel DIN MAX98357A benar-benar di GPIO 1.");
  Serial.println("  Pindahkan jumper DIN MAX98357A dari header 'GPIO 2' ke 'GPIO 1'");
  Serial.println("  (Deret KANAN Pin 3 / Pin ke-3 dari atas).");
  Serial.println("----------------------------------------------------------------------");
  Serial.println("PERINTAH SERIAL MONITOR (Ketik karakter lalu tekan Enter jika perlu):");
  Serial.println("  [s] atau [p] -> Mode SPEAKER : Putar Musik '510 - ALIVE' (24kHz)");
  Serial.println("  [m]          -> Mode MIKROFON: VU Meter Realtime (Persis test_mic.sh)");
  Serial.println("  [+] atau [w] -> Volume Musik +0.2x");
  Serial.println("  [-]          -> Volume Musik -0.2x");
  Serial.println("  [1] .. [5]   -> Preset Volume Musik (1.0x, 1.5x, 2.0x, 2.5x, 3.0x)");
  Serial.println("  [?] atau [h] -> Cetak ulang panduan bantuan ini");
  Serial.println("======================================================================\n");
}

static void updateOledMusicDisplay() {
  Adafruit_SSD1306 &disp = getDisplay();
  disp.clearDisplay();

  // Border retro futuristik
  disp.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  disp.drawFastHLine(0, 14, SCREEN_WIDTH, SSD1306_WHITE);

  disp.setTextSize(1);
  disp.setTextColor(SSD1306_WHITE);
  disp.setCursor(6, 4);
  disp.print("SPK: MAX98357A [24kHz]");

  disp.setCursor(6, 18);
  disp.print("Track: 510 - ALIVE");

  disp.setCursor(6, 29);
  disp.printf("Volume: %.1fx", volume_mult);

  // Volume Bar
  disp.drawRect(6, 40, 116, 9, SSD1306_WHITE);
  int w = map(constrain((int)(volume_mult * 10.0f), 4, 40), 4, 40, 0, 112);
  if (w > 0) {
    disp.fillRect(8, 42, w, 5, SSD1306_WHITE);
  }

  disp.setCursor(6, 52);
  disp.print("[m]=Tes Mic  [+/-]=Vol");

  disp.display();
}

static void updateOledMicDisplay(int max_val, int rms, const char* status) {
  Adafruit_SSD1306 &disp = getDisplay();
  disp.clearDisplay();

  disp.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  disp.drawFastHLine(0, 14, SCREEN_WIDTH, SSD1306_WHITE);

  disp.setTextSize(1);
  disp.setTextColor(SSD1306_WHITE);
  disp.setCursor(6, 4);
  disp.print("MIC: INMP441 VU METER");

  disp.setCursor(6, 18);
  disp.printf("Status: %s", status);

  // VU Meter Bar (0 - 5000)
  disp.drawRect(6, 30, 116, 11, SSD1306_WHITE);
  int bar_w = map(constrain(max_val, 0, 5000), 0, 5000, 0, 112);
  if (bar_w > 0) {
    disp.fillRect(8, 32, bar_w, 7, SSD1306_WHITE);
  }

  disp.setCursor(6, 44);
  disp.printf("Peak: %-5d RMS: %-5d", max_val, rms);

  disp.setCursor(6, 53);
  disp.print("[s]=Putar Musik");

  disp.display();
}

void setupAudioTest() {
  Serial.begin(115200);
  delay(500);

  // ---------------------------------------------------------------------
  // MATIKAN SEMUA LED ONBOARD DULU
  // LED IO2 = LED user. Sebelumnya pin ini dipakai sebagai I2S DIN sehingga
  // menyala mengikuti data audio. Sekarang DIN pindah ke GPIO 1, jadi LED
  // IO2 kita matikan permanen agar tidak mengganggu/membingungkan.
  // ---------------------------------------------------------------------
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);          // LED user IO2 OFF
  neopixelWrite(48, 0, 0, 0);    // WS2812 RGB IO48 OFF (tidak merah/nyala)

  // Inisialisasi Layar OLED agar langsung menyala
  setupOLED();

  // Tampilkan panduan di Serial Monitor
  printAudioHelp();

  if (I2S_SPK_DIN_PIN == 2) {
    Serial.println("⚠️  PERINGATAN: DIN speaker masih di GPIO 2 (pin LED onboard)!");
    Serial.println("    Suara akan kemresek. Pindahkan jumper DIN ke GPIO 1.\n");
  }

  // Mode awal: Langsung memutar musik "510 - ALIVE" ke Speaker MAX98357A
  currentSubMode = SUBMODE_MUSIC;
  updateOledMusicDisplay();   // Render OLED dulu (I2C 50 kHz lambat)
  initI2SSpeaker(24000);      // Baru nyalakan I2S agar DMA tidak underrun
  music_sample_idx = 0;

  Serial.println("▶️  [MODE SPEAKER] Memutar lagu '510 - ALIVE' (24kHz Hi-Fi)...");
  Serial.printf("🔊 Multiplier Volume Awal: %.1fx (Ketik [m] untuk beralih ke Tes Mic)\n\n", volume_mult);
}

void loopAudioTest() {
  // -----------------------------------------------------------------------
  // 1. PEMBACAAN KONTROL DARI SERIAL MONITOR
  // -----------------------------------------------------------------------
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\r' || c == '\n') return; // Abaikan newline

    if (c == 'm' || c == 'M') {
      // Pindah ke Mode Pengujian Mikrofon
      if (currentSubMode != SUBMODE_MIC) {
        currentSubMode = SUBMODE_MIC;
        i2s_zero_dma_buffer(I2S_PORT);
        initI2SMicrophone(16000);
        // Mute amplifier saat mode mic: tahan DIN MAX98357A ke LOW
        pinMode(I2S_SPK_DIN_PIN, OUTPUT);
        digitalWrite(I2S_SPK_DIN_PIN, LOW);
        Serial.println("\n========================================================");
        Serial.println("🎤 [MODE MIKROFON] INMP441 Sound Level & VU Meter Monitor");
        Serial.println("========================================================");
        Serial.println("Speaker dimatikan untuk mencegah feedback/dengung.");
        Serial.println("Silakan berbicara, berbisik, atau tepuk tangan di depan mic.");
        Serial.println("Ketik [s] untuk kembali ke pemutaran musik.\n");
      }
    } else if (c == 's' || c == 'S' || c == 'p' || c == 'P') {
      // Pindah ke Mode Pemutaran Musik Speaker
      if (currentSubMode != SUBMODE_MUSIC) {
        currentSubMode = SUBMODE_MUSIC;
        initI2SSpeaker(24000);
        Serial.println("\n========================================================");
        Serial.println("🎵 [MODE SPEAKER] Memutar '510 - ALIVE' (24kHz Stereo)");
        Serial.println("========================================================");
        Serial.printf("🔊 Multiplier Volume: %.1fx\n", volume_mult);
        updateOledMusicDisplay();
      }
    } else if (c == '1') {
      if (currentSubMode == SUBMODE_MIC) {
        // Jika di mode mic dan tekan 1, pindah ke musik
        currentSubMode = SUBMODE_MUSIC;
        initI2SSpeaker(24000);
        updateOledMusicDisplay();
      } else {
        volume_mult = 1.0f;
        Serial.printf("🔊 Volume: %.1fx (Original Clean)\n", volume_mult);
        updateOledMusicDisplay();
      }
    } else if (c == '2') {
      if (currentSubMode == SUBMODE_MUSIC) {
        volume_mult = 1.5f;
        Serial.printf("🔊 Volume: %.1fx (1.5x)\n", volume_mult);
        updateOledMusicDisplay();
      }
    } else if (c == '3') {
      volume_mult = 2.0f;
      Serial.printf("🔊 Volume: %.1fx (2.0x Rekomendasi)\n", volume_mult);
      if (currentSubMode == SUBMODE_MUSIC) updateOledMusicDisplay();
    } else if (c == '4') {
      volume_mult = 2.5f;
      Serial.printf("🔊 Volume: %.1fx (2.5x Kencang)\n", volume_mult);
      if (currentSubMode == SUBMODE_MUSIC) updateOledMusicDisplay();
    } else if (c == '5') {
      volume_mult = 3.0f;
      Serial.printf("🔊 Volume: %.1fx (3.0x Maksimal)\n", volume_mult);
      if (currentSubMode == SUBMODE_MUSIC) updateOledMusicDisplay();
    } else if (c == '+' || c == 'w') {
      volume_mult = min(5.0f, volume_mult + 0.5f);
      Serial.printf("🔊 Volume: %.1fx\n", volume_mult);
      if (currentSubMode == SUBMODE_MUSIC) updateOledMusicDisplay();
    } else if (c == '-' || c == 'x') {
      volume_mult = max(0.5f, volume_mult - 0.5f);
      Serial.printf("🔊 Volume: %.1fx\n", volume_mult);
      if (currentSubMode == SUBMODE_MUSIC) updateOledMusicDisplay();
    } else if (c == '?' || c == 'h') {
      printAudioHelp();
    }
  }

  // -----------------------------------------------------------------------
  // 2. EKSEKUSI SUBMODE AKTIF
  // -----------------------------------------------------------------------
  if (currentSubMode == SUBMODE_MUSIC) {
    // Mode Speaker: Mengalirkan potongan audio 24kHz ke MAX98357A
    const int16_t* pcm_data = (const int16_t*)clip_start;
    size_t total_samples = (clip_end - clip_start) / sizeof(int16_t);

    constexpr size_t CHUNK = 256;
    int16_t stereo_buf[CHUNK * 2];

    size_t n = (total_samples - music_sample_idx < CHUNK) ? (total_samples - music_sample_idx) : CHUNK;
    for (size_t i = 0; i < n; i++) {
      int32_t val = (int32_t)(pcm_data[music_sample_idx + i] * volume_mult);
      if (val > 32767) val = 32767;
      if (val < -32768) val = -32768;
      stereo_buf[i * 2]     = (int16_t)val; // Channel L
      stereo_buf[i * 2 + 1] = (int16_t)val; // Channel R
    }

    size_t bytes_written = 0;
    const size_t expected_bytes = n * 2 * sizeof(int16_t);
    esp_err_t writeErr = i2s_write(I2S_PORT, stereo_buf, expected_bytes,
                                   &bytes_written, portMAX_DELAY);
    if (writeErr != ESP_OK || bytes_written != expected_bytes) {
      static unsigned long lastI2SErrorPrint = 0;
      if (millis() - lastI2SErrorPrint >= 1000) {
        lastI2SErrorPrint = millis();
        Serial.printf("[I2S ERROR] write=%s bytes=%u/%u\n",
                      esp_err_to_name(writeErr), (unsigned)bytes_written,
                      (unsigned)expected_bytes);
      }
    }
    music_sample_idx += n;

    // Loop otomatis jika audio habis
    if (music_sample_idx >= total_samples) {
      music_sample_idx = 0;
    }

  } else {
    // Mode Mikrofon: Baca buffer INMP441 & Tampilkan VU Meter
    constexpr size_t SAMPLES = 256;
    int32_t rx_buf[SAMPLES];
    size_t bytes_read = 0;

    i2s_read(I2S_PORT, rx_buf, sizeof(rx_buf), &bytes_read, portMAX_DELAY);
    int count = bytes_read / sizeof(int32_t);

    static int32_t prev_in = 0;
    static int32_t prev_out = 0;
    int32_t max_val = 0;
    int64_t sum_sq = 0;

    for (int i = 0; i < count; i++) {
      // INMP441 kirim signed 24-bit dalam slot 32-bit (geser 14 bit)
      int32_t input = rx_buf[i] >> 14;

      // Filter DC-Blocker (menghilangkan offset DC / ground hum)
      int32_t hp = input - prev_in + ((int64_t)prev_out * 32604 >> 15);
      prev_in = input;
      prev_out = hp;

      int32_t abs_s = abs(hp);
      if (abs_s > max_val) max_val = abs_s;
      sum_sq += (int64_t)hp * hp;
    }

    int32_t rms = count > 0 ? sqrt(sum_sq / count) : 0;

    // Cetak ke Serial & perbarui OLED setiap 100ms
    if (millis() - lastMicPrint >= 100) {
      lastMicPrint = millis();

      // Skala visual karakter: 0 - 5000
      int bar_len = map(constrain(max_val, 0, 5000), 0, 5000, 0, 25);
      char bar[30];
      for (int b = 0; b < 25; b++) {
        bar[b] = (b < bar_len) ? '#' : '-';
      }
      bar[25] = '\0';

      const char* status = "HENING";
      if (max_val > 1500) {
        status = "🔊 SUARA KERAS / TEPUK TANGAN";
      } else if (max_val > 300) {
        status = "🗣️ BICARA NORMAL";
      } else if (max_val > 50) {
        status = "🤫 BISIKAN / SUARA KECIL";
      }

      Serial.printf("Mic: [%s] Peak:%-5d RMS:%-5d | %s\n", bar, max_val, rms, status);

      // Perbarui layar OLED
      const char* shortStatus = (max_val > 1500) ? "KERAS!" : ((max_val > 300) ? "BICARA" : ((max_val > 50) ? "BISIK" : "HENING"));
      updateOledMicDisplay(max_val, rms, shortStatus);
    }
  }
}

// =========================================================================
// MODE 6: DIAGNOSTIK MIKROFON INMP441 (VU METER + VERDICT WIRING)
// =========================================================================
// Wiring yang diuji (sesuai Panduan_Wiring_dan_Pinout):
//   VDD  -> 3V3 (JANGAN 5V)
//   GND  -> GND
//   SCK  -> GPIO 42 (shared BCLK MAX98357A)
//   WS   -> GPIO 41 (shared LRC MAX98357A)
//   SD   -> GPIO 14
//   L/R  -> GND (LEFT channel)
// =========================================================================

static bool          micUseRightChannel = false;
static int32_t       micNoiseFloor      = -1;
static int32_t       micPeakAll         = 0;
static int32_t       micPeakWin         = 0;
static int32_t       micRmsWin          = 0;
static unsigned long micWinStart        = 0;
static unsigned long micLastSerial      = 0;
static unsigned long micLastOled        = 0;

static void printMicHelp() {
  Serial.println("\n======================================================================");
  Serial.println("  🎤 DIAGNOSTIK MIKROFON INMP441 - ESP32-S3 FREENOVE WROOM");
  Serial.println("======================================================================");
  Serial.println("Wiring wajib (persis panduan):");
  Serial.println("  VDD  -> 3V3    (JANGAN 5V!)");
  Serial.println("  GND  -> GND    (satu rel dengan ESP32)");
  Serial.println("  SCK  -> GPIO 42  (shared dengan BCLK MAX98357A)");
  Serial.println("  WS   -> GPIO 41  (shared dengan LRC MAX98357A)");
  Serial.println("  SD   -> GPIO 14");
  Serial.println("  L/R  -> GND      (LEFT channel mono)");
  Serial.println("----------------------------------------------------------------------");
  Serial.println("Catatan: header INMP441 WAJIB disolder. Kalau hanya ditumpangkan,");
  Serial.println("clock 1 MHz akan putus-putus dan peak mic bisa 0/1 terus.");
  Serial.println("----------------------------------------------------------------------");
  Serial.println("Perintah Serial:");
  Serial.println("  [c] -> ganti channel LEFT <-> RIGHT (tes wiring pin L/R)");
  Serial.println("  [r] -> reset hitungan peak / mulai ukur ulang");
  Serial.println("  [h] -> tampilkan bantuan ini");
  Serial.println("======================================================================\n");
}

static void updateOledMicTestDisplay(int peak, int rms, const char* status) {
  Adafruit_SSD1306 &disp = getDisplay();
  disp.clearDisplay();

  disp.drawRect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, SSD1306_WHITE);
  disp.drawFastHLine(0, 14, SCREEN_WIDTH, SSD1306_WHITE);

  disp.setTextSize(1);
  disp.setTextColor(SSD1306_WHITE);
  disp.setCursor(6, 4);
  disp.print("MIC TEST: INMP441");

  disp.setCursor(6, 17);
  disp.printf("CH:%-5s Noise:%d", micUseRightChannel ? "RIGHT" : "LEFT",
               (int)micNoiseFloor);

  disp.drawRect(6, 28, 116, 11, SSD1306_WHITE);
  int bar_w = map(constrain(peak, 0, 5000), 0, 5000, 0, 112);
  if (bar_w > 0) {
    disp.fillRect(8, 30, bar_w, 7, SSD1306_WHITE);
  }

  disp.setCursor(6, 43);
  disp.printf("Peak:%-5d RMS:%-5d", peak, rms);

  disp.setCursor(6, 54);
  disp.printf("%s [c]=CH [r]=RST", status);

  disp.display();
}

void setupMicTest() {
  Serial.begin(115200);
  delay(500);

  // Matikan LED onboard supaya tidak bikin bingung saat pengukuran.
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);
  neopixelWrite(48, 0, 0, 0);

  // Mute amplifier MAX98357A: tahan DIN (GPIO 1) LOW selama tes mic.
  pinMode(I2S_SPK_DIN_PIN, OUTPUT);
  digitalWrite(I2S_SPK_DIN_PIN, LOW);

  setupOLED();
  printMicHelp();

  micUseRightChannel = false;
  initI2SMicrophone(16000, micUseRightChannel);

  Serial.println("[MIC] Kalibrasi noise floor 2 detik. Mohon DIAM (jangan bicara)...");
  delay(300);

  int32_t maxNoise = 0;
  unsigned long t0 = millis();
  while (millis() - t0 < 2000) {
    int32_t rx[256];
    size_t bytesRead = 0;
    i2s_read(I2S_PORT, rx, sizeof(rx), &bytesRead, 200 / portTICK_PERIOD_MS);
    int n = bytesRead / sizeof(int32_t);

    for (int i = 0; i < n; i++) {
      int32_t v = rx[i] >> 14;
      if (v < 0) v = -v;
      if (v > maxNoise) maxNoise = v;
    }
    delay(5);
  }

  micNoiseFloor = maxNoise;
  Serial.printf("[MIC] Noise floor saat diam : %d\n", (int)micNoiseFloor);
  Serial.printf("[MIC] Channel aktif         : %s\n",
                micUseRightChannel ? "RIGHT" : "LEFT");
  Serial.println("[MIC] Sekarang BICARA atau TEPUK TANGAN di depan mic...\n");

  micPeakAll = 0;
  micPeakWin = 0;
  micRmsWin = 0;
  micWinStart = millis();
  micLastSerial = 0;
  micLastOled = 0;
}

void loopMicTest() {
  // -----------------------------------------------------------------------
  // Perintah Serial
  // -----------------------------------------------------------------------
  while (Serial.available() > 0) {
    int c = Serial.read();

    if (c == 'c' || c == 'C') {
      micUseRightChannel = !micUseRightChannel;
      initI2SMicrophone(16000, micUseRightChannel);
      micPeakAll = 0;
      micPeakWin = 0;
      micRmsWin = 0;
      micWinStart = millis();
      Serial.printf("\n[MIC] Channel diganti -> %s\n",
                    micUseRightChannel ? "RIGHT" : "LEFT");
      Serial.println("[MIC] Kalau LEFT senyap tapi RIGHT bersuara, berarti pin L/R mic salah (harus ke GND).\n");
    } else if (c == 'r' || c == 'R') {
      micPeakAll = 0;
      micPeakWin = 0;
      micRmsWin = 0;
      micWinStart = millis();
      Serial.println("\n[MIC] Statistik di-reset. Silakan bicara lagi...\n");
    } else if (c == 'h' || c == 'H' || c == '?') {
      printMicHelp();
    }
  }

  // -----------------------------------------------------------------------
  // Baca blok I2S dari INMP441
  // -----------------------------------------------------------------------
  int32_t rx[256];
  size_t bytesRead = 0;
  i2s_read(I2S_PORT, rx, sizeof(rx), &bytesRead, portMAX_DELAY);

  int n = bytesRead / sizeof(int32_t);
  if (n <= 0) return;

  static int32_t prevIn = 0;
  static int32_t prevOut = 0;
  static int32_t rawMin = 0x7FFFFFFF;
  static int32_t rawMax = -0x7FFFFFFF;

  int32_t peak = 0;
  int64_t sumSq = 0;

  for (int i = 0; i < n; i++) {
    // INMP441: signed 24-bit di dalam slot 32-bit
    int32_t input = rx[i] >> 14;

    if (input < rawMin) rawMin = input;
    if (input > rawMax) rawMax = input;

    // DC blocker (high-pass) untuk membuang offset/dengung listrik
    int32_t hp = input - prevIn + ((int64_t)prevOut * 32604 >> 15);
    prevIn = input;
    prevOut = hp;

    int32_t a = (hp < 0) ? -hp : hp;
    if (a > peak) peak = a;
    sumSq += (int64_t)hp * hp;
  }

  int32_t rms = (int32_t)sqrt((double)sumSq / (double)n);

  if (peak > micPeakAll) micPeakAll = peak;
  if (peak > micPeakWin) micPeakWin = peak;
  if (rms > micRmsWin) micRmsWin = rms;

  // -----------------------------------------------------------------------
  // Log serial tiap 250 ms (jangan terlalu sering supaya DMA tidak starve)
  // -----------------------------------------------------------------------
  if (millis() - micLastSerial >= 250) {
    micLastSerial = millis();

    int bar_len = map(constrain(peak, 0, 5000), 0, 5000, 0, 25);
    char bar[30];
    for (int b = 0; b < 25; b++) bar[b] = (b < bar_len) ? '#' : '-';
    bar[25] = '\0';

    const char* status = "HENING";
    if (peak > 1500) status = "KERAS / TEPUK TANGAN";
    else if (peak > 300) status = "BICARA NORMAL";
    else if (peak > 50) status = "BISIKAN";

    Serial.printf("[MICLOG] ch=%s [%s] peak=%-5d rms=%-5d noise=%-4d raw=%d..%d | %s\n",
                  micUseRightChannel ? "R" : "L", bar, (int)peak, (int)rms,
                  (int)micNoiseFloor, (int)rawMin, (int)rawMax, status);

    rawMin = 0x7FFFFFFF;
    rawMax = -0x7FFFFFFF;
  }

  // -----------------------------------------------------------------------
  // OLED tiap 1000 ms (I2C 50 kHz lambat, jangan terlalu sering)
  // -----------------------------------------------------------------------
  if (millis() - micLastOled >= 1000) {
    micLastOled = millis();

    const char* shortStatus = (peak > 1500) ? "KERAS!" :
                              ((peak > 300) ? "BICARA" :
                              ((peak > 50) ? "BISIK" : "HENING"));
    updateOledMicTestDisplay(peak, rms, shortStatus);
  }

  // -----------------------------------------------------------------------
  // Ringkasan + verdict tiap 8 detik
  // -----------------------------------------------------------------------
  if (millis() - micWinStart >= 8000) {
    Serial.println("\n----------------- [HASIL TES MIKROFON 8 DETIK] -----------------");
    Serial.printf("  Channel aktif   : %s\n", micUseRightChannel ? "RIGHT" : "LEFT");
    Serial.printf("  Noise floor     : %d\n", (int)micNoiseFloor);
    Serial.printf("  Peak tertinggi  : %d\n", (int)micPeakAll);
    Serial.printf("  RMS tertinggi   : %d\n", (int)micRmsWin);

    if (micPeakAll < 20) {
      Serial.println("  VERDICT: ❌ TIDAK ADA SINYAL SAMA SEKALI.");
      Serial.println("  Cek urutan ini:");
      Serial.println("   1. VDD mic = 3.3V (BUKAN 5V), GND nyambung.");
      Serial.println("   2. SD  -> GPIO 14, SCK -> GPIO 42, WS -> GPIO 41.");
      Serial.println("   3. L/R -> GND.");
      Serial.println("   4. Header INMP441 disolder? Pin floating = peak 0/1.");
      Serial.println("   5. Tekan [c] untuk tes channel RIGHT.");
    } else if (micPeakAll < 200) {
      Serial.println("  VERDICT: ⚠️ SINYAL LEMAH / DIDOMINASI NOISE.");
      Serial.println("  Cek kabel SD/SCK/WS (kendor), VDD 3.3V, dan grounding.");
    } else if (micPeakAll < 1000) {
      Serial.println("  VERDICT: ✅ MIC MERESPONS (level pelan).");
      Serial.println("  Coba bicara lebih dekat / tepuk tangan untuk tes penuh.");
    } else {
      Serial.println("  VERDICT: ✅ MIC BEKERJA BAIK.");
    }

    if (micNoiseFloor > 800) {
      Serial.println("  ⚠️ Noise floor tinggi: cek grounding, kabel I2S kepanjangan,");
      Serial.println("     atau speaker MAX98357A ikut bergetar di breadboard.");
    }

    Serial.println("-----------------------------------------------------------------");
    Serial.println("  Lanjut mendengarkan... ([c] ganti channel, [r] reset)\n");

    micPeakAll = 0;
    micPeakWin = 0;
    micRmsWin = 0;
    micWinStart = millis();
  }
}

// =========================================================================
// MODE 7: SPEAKER ONLY — playback loop sengaja mengikuti C3 play_music.
// OLED, mic, Wi-Fi, kamera, dan animasi tidak dijalankan pada mode ini.
// S3 pinout tetap BCLK=42, WS=41, DIN=1 (GPIO2 adalah LED board).
// =========================================================================
static float speakerOnlyVolume = 3.0f; // Default 3.0x lantang & jernih.
static size_t speakerOnlySampleIdx = 0;

void setupSpeakerOnlyTest() {
  Serial.begin(115200);
  delay(800);

  // Cegah LED di GPIO2 ikut menerima data audio; pin itu bukan DIN S3.
  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);
  neopixelWrite(48, 0, 0, 0);

  // Aktifkan amplifier MAX98357A via pin SD (GPIO 40 = 3.3V)
  pinMode(I2S_SPK_SD_PIN, OUTPUT);
  digitalWrite(I2S_SPK_SD_PIN, HIGH);

  Serial.println("\n============================================================");
  Serial.println(" ESP32-S3 SPEAKER-ONLY TEST (play_music C3 playback method)");
  Serial.println("============================================================");
  Serial.println("S3 pinout: BCLK GPIO42 | WS GPIO41 | DIN GPIO1 | SD GPIO40");
  Serial.println("XiaoZhi-style: 24kHz | 32-bit slot | LEFT mono | I2S standard");
  Serial.println("PCM 16-bit dinaikkan ke slot 32-bit (seperti NoAudioCodecSimplex)");
  Serial.printf("Volume awal %.1fx. Tekan 1=1.0x, 2=1.5x, 3=2.0x, -=turun, +=naik\n",
                speakerOnlyVolume);
  Serial.println("Tidak menjalankan OLED, mic, kamera, Wi-Fi, atau efek audio.");

  const int16_t *pcm = (const int16_t*)clip_start;
  const size_t sampleCount = (clip_end - clip_start) / sizeof(int16_t);
  int32_t peak = 0;
  for (size_t i = 0; i < sampleCount; ++i) {
    int32_t value = pcm[i];
    if (value < 0) value = -value;
    if (value > peak) peak = value;
  }
  Serial.printf("PCM samples=%u, peak=%ld, duration=%.2fs @ 24kHz\n",
                (unsigned)sampleCount, (long)peak,
                (double)sampleCount / 24000.0);

  // XiaoZhi NoAudioCodecSimplex mengirim PCM di dalam slot 32-bit mono-kiri.
  // Jangan panggil initI2SSpeaker(): fungsi itu memakai 16-bit stereo seperti
  // tes C3, bukan format TX XiaoZhi yang sedang kita bandingkan.
  if (i2sInitialized) {
    i2s_driver_uninstall(I2S_PORT);
    i2sInitialized = false;
  }

  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 24000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = I2S_BCLK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_SPK_DIN_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  esp_err_t err = i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
  if (err == ESP_OK) err = i2s_set_pin(I2S_PORT, &pins);
  if (err != ESP_OK) {
    Serial.printf("[FATAL] XiaoZhi-style I2S init gagal: %s\n", esp_err_to_name(err));
    i2s_driver_uninstall(I2S_PORT);
    return;
  }
  i2s_zero_dma_buffer(I2S_PORT);
  i2sInitialized = true;
  currentI2sIsSpeaker = true;
  currentSampleRate = 24000;

  speakerOnlySampleIdx = 0;
  Serial.println("[SPEAKER-ONLY] Mulai playback.\n");
}

void loopSpeakerOnlyTest() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '1') speakerOnlyVolume = 1.0f;
    else if (c == '2') speakerOnlyVolume = 2.0f;
    else if (c == '3') speakerOnlyVolume = 3.0f;
    else if (c == '4') speakerOnlyVolume = 4.0f;
    else if (c == '+') speakerOnlyVolume = min(5.0f, speakerOnlyVolume + 0.5f);
    else if (c == '-') speakerOnlyVolume = max(0.5f, speakerOnlyVolume - 0.5f);
    else continue;
    Serial.printf("[SPEAKER-ONLY] Volume %.1fx\n", speakerOnlyVolume);
  }

  if (!i2sInitialized || !currentI2sIsSpeaker || currentSampleRate != 24000) {
    delay(100);
    return;
  }

  const int16_t *pcm = (const int16_t*)clip_start;
  const size_t totalSamples = (clip_end - clip_start) / sizeof(int16_t);
  constexpr size_t CHUNK = 256;
  int32_t monoBuffer[CHUNK];

  // XiaoZhi NoAudioCodec::Write scales int16 by 65536 into int32.
  // MAX98357A reads left-aligned 16-bit PCM from a 32-bit I2S slot.
  const size_t count = min(CHUNK, totalSamples - speakerOnlySampleIdx);
  for (size_t i = 0; i < count; ++i) {
    int32_t value = (int32_t)((float)pcm[speakerOnlySampleIdx + i] * speakerOnlyVolume);
    value = constrain(value, -32768, 32767);
    monoBuffer[i] = value * 65536;
  }

  // Cek complete write: jika tidak lengkap, tampilkan; jangan diam-diam lanjut
  // dan menggeser indeks karena dapat menghilangkan sampel / menghasilkan klik.
  size_t bytesWritten = 0;
  const size_t expectedBytes = count * sizeof(int32_t);
  const esp_err_t err = i2s_write(I2S_PORT, monoBuffer, expectedBytes,
                                  &bytesWritten, portMAX_DELAY);
  if (err != ESP_OK || bytesWritten != expectedBytes) {
    Serial.printf("[I2S WRITE ERROR] %s, %u/%u bytes\n",
                  esp_err_to_name(err), (unsigned)bytesWritten,
                  (unsigned)expectedBytes);
    delay(5);
  } else {
    speakerOnlySampleIdx += count;
    if (speakerOnlySampleIdx >= totalSamples) {
      // Klip ini C3 loop dengan jeda 200ms; tiru perilaku itu.
      speakerOnlySampleIdx = 0;
      Serial.println("[SPEAKER-ONLY] Clip selesai; loop ulang.");
      delay(200);
    }
  }
}

// =========================================================================
// MODE 8: LOW-LEVEL TONE TEST FOR MAX98357A
// Firmware can verify I2S setup/write, but cannot electrically measure whether
// the amplifier IC or the part marked "105" is damaged.
// =========================================================================
static int ampTestFrequency = 440;
static bool ampTestMuted = false;
static float ampTestPhase = 0.0f;
static float ampToneAmplitude = 20000.0f; // Default 20000/32767 (~61% full-scale, kencang & jernih)

void setupAmpToneDiagnostic() {
  Serial.begin(115200);
  delay(500);

  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);
  neopixelWrite(48, 0, 0, 0);

  // Aktifkan amplifier MAX98357A via pin SD (GPIO 40 = 3.3V)
  pinMode(I2S_SPK_SD_PIN, OUTPUT);
  digitalWrite(I2S_SPK_SD_PIN, HIGH);

  if (i2sInitialized) {
    i2s_driver_uninstall(I2S_PORT);
    i2sInitialized = false;
  }

  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 24000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_32BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = I2S_BCLK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_SPK_DIN_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  esp_err_t err = i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
  if (err == ESP_OK) err = i2s_set_pin(I2S_PORT, &pins);
  if (err != ESP_OK) {
    Serial.printf("[AMP-DIAG][I2S INIT FAIL] %s\n", esp_err_to_name(err));
    i2s_driver_uninstall(I2S_PORT);
    return;
  }
  i2s_zero_dma_buffer(I2S_PORT);
  i2sInitialized = true;
  currentI2sIsSpeaker = true;
  currentSampleRate = 24000;
  ampTestPhase = 0.0f;
  ampTestMuted = false;

  Serial.println("\n[AMP-DIAG] MAX98357A tone test (High Volume)");
  Serial.println("TX: GPIO1 DIN, GPIO42 BCLK, GPIO41 LRC, GPIO40 SD; slot 32-bit mono LEFT @24kHz");
  Serial.println("Commands: 4=440Hz, 8=880Hz, 1=1000Hz, +=naikkan vol, -=turunkan vol, m=mute.");
  Serial.println("Amplitude awal: 20000/32767 (~61% full scale).");
}

void loopAmpToneDiagnostic() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '4') { ampTestFrequency = 440; ampTestMuted = false; }
    else if (c == '8') { ampTestFrequency = 880; ampTestMuted = false; }
    else if (c == '1') { ampTestFrequency = 1000; ampTestMuted = false; }
    else if (c == '+') { ampToneAmplitude = min(32000.0f, ampToneAmplitude + 3000.0f); }
    else if (c == '-') { ampToneAmplitude = max(3000.0f, ampToneAmplitude - 3000.0f); }
    else if (c == 'm' || c == 'M') ampTestMuted = !ampTestMuted;
    else continue;
    Serial.printf("[AMP-DIAG] %s, %d Hz, amplitude %.0f/32767\n",
                  ampTestMuted ? "MUTE" : "PLAY", ampTestFrequency, ampToneAmplitude);
    i2s_zero_dma_buffer(I2S_PORT);
  }

  if (!i2sInitialized || !currentI2sIsSpeaker || currentSampleRate != 24000) {
    delay(100);
    return;
  }

  constexpr size_t N = 256;
  int32_t buffer[N];
  const float phaseStep = 2.0f * (float)M_PI * (float)ampTestFrequency / 24000.0f;
  for (size_t i = 0; i < N; ++i) {
    const int32_t pcm16 = ampTestMuted ? 0 : (int32_t)(sinf(ampTestPhase) * ampToneAmplitude);
    buffer[i] = pcm16 * 65536; // 16-bit PCM left-aligned in 32-bit slot
    ampTestPhase += phaseStep;
    if (ampTestPhase >= 2.0f * (float)M_PI) ampTestPhase -= 2.0f * (float)M_PI;
  }

  size_t written = 0;
  const size_t expected = sizeof(buffer);
  const esp_err_t err = i2s_write(I2S_PORT, buffer, expected, &written, portMAX_DELAY);
  if (err != ESP_OK || written != expected) {
    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 1000) {
      lastPrint = millis();
      Serial.printf("[AMP-DIAG][I2S WRITE FAIL] %s, %u/%u bytes\n",
                    esp_err_to_name(err), (unsigned)written, (unsigned)expected);
    }
  }
}

// =========================================================================
// MODE 9: SAME TEST TONE, CLASSIC C3 16-BIT STEREO I2S FORMAT
// This is a format comparison only; it is not a hardware self-test.
// =========================================================================
static int ampStereoFrequency = 440;
static bool ampStereoMuted = false;
static float ampStereoPhase = 0.0f;
static float ampStereoAmplitude = 20000.0f; // Default 20000/32767 (~61% full-scale, kencang & jernih)

void setupAmpStereoToneDiagnostic() {
  Serial.begin(115200);
  delay(500);

  pinMode(2, OUTPUT);
  digitalWrite(2, LOW);
  neopixelWrite(48, 0, 0, 0);

  // Aktifkan amplifier MAX98357A via pin SD (GPIO 40 = 3.3V)
  pinMode(I2S_SPK_SD_PIN, OUTPUT);
  digitalWrite(I2S_SPK_SD_PIN, HIGH);

  if (i2sInitialized) {
    i2s_driver_uninstall(I2S_PORT);
    i2sInitialized = false;
  }

  // Classic C3 play_music format: standard I2S, 24 kHz, 16-bit stereo.
  i2s_config_t cfg = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = 24000,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 512,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  i2s_pin_config_t pins = {
    .bck_io_num = I2S_BCLK_PIN,
    .ws_io_num = I2S_WS_PIN,
    .data_out_num = I2S_SPK_DIN_PIN,
    .data_in_num = I2S_PIN_NO_CHANGE
  };

  esp_err_t err = i2s_driver_install(I2S_PORT, &cfg, 0, NULL);
  if (err == ESP_OK) err = i2s_set_pin(I2S_PORT, &pins);
  if (err != ESP_OK) {
    Serial.printf("[AMP-DIAG-9][I2S INIT FAIL] %s\n", esp_err_to_name(err));
    i2s_driver_uninstall(I2S_PORT);
    return;
  }
  i2s_zero_dma_buffer(I2S_PORT);
  i2sInitialized = true;
  currentI2sIsSpeaker = true;
  currentSampleRate = 24000;
  ampStereoPhase = 0.0f;
  ampStereoMuted = false;

  Serial.println("\n[AMP-DIAG-9] MAX98357A tone: classic C3 I2S format (High Volume)");
  Serial.println("TX: GPIO1 DIN, GPIO42 BCLK, GPIO41 LRC, GPIO40 SD; 16-bit stereo @24kHz");
  Serial.println("Commands: 4=440Hz, 8=880Hz, 1=1000Hz, +=naikkan vol, -=turunkan vol, m=mute.");
  Serial.println("Amplitude awal: 20000/32767 (~61% full scale).");
}

void loopAmpStereoToneDiagnostic() {
  while (Serial.available() > 0) {
    const char c = (char)Serial.read();
    if (c == '4') { ampStereoFrequency = 440; ampStereoMuted = false; }
    else if (c == '8') { ampStereoFrequency = 880; ampStereoMuted = false; }
    else if (c == '1') { ampStereoFrequency = 1000; ampStereoMuted = false; }
    else if (c == '+') { ampStereoAmplitude = min(32000.0f, ampStereoAmplitude + 3000.0f); }
    else if (c == '-') { ampStereoAmplitude = max(3000.0f, ampStereoAmplitude - 3000.0f); }
    else if (c == 'm' || c == 'M') ampStereoMuted = !ampStereoMuted;
    else continue;
    Serial.printf("[AMP-DIAG-9] %s, %d Hz, amplitude %.0f/32767\n",
                  ampStereoMuted ? "MUTE" : "PLAY", ampStereoFrequency, ampStereoAmplitude);
    i2s_zero_dma_buffer(I2S_PORT);
  }

  if (!i2sInitialized || !currentI2sIsSpeaker || currentSampleRate != 24000) {
    delay(100);
    return;
  }

  constexpr size_t N = 256;
  int16_t stereoBuffer[N * 2];
  const float phaseStep = 2.0f * (float)M_PI * (float)ampStereoFrequency / 24000.0f;
  for (size_t i = 0; i < N; ++i) {
    const int16_t sample = ampStereoMuted
        ? 0
        : (int16_t)(sinf(ampStereoPhase) * ampStereoAmplitude);
    stereoBuffer[i * 2] = sample;     // left
    stereoBuffer[i * 2 + 1] = sample; // right
    ampStereoPhase += phaseStep;
    if (ampStereoPhase >= 2.0f * (float)M_PI) ampStereoPhase -= 2.0f * (float)M_PI;
  }

  size_t written = 0;
  const size_t expected = sizeof(stereoBuffer);
  const esp_err_t err = i2s_write(I2S_PORT, stereoBuffer, expected,
                                  &written, portMAX_DELAY);
  if (err != ESP_OK || written != expected) {
    static unsigned long lastPrint = 0;
    if (millis() - lastPrint > 1000) {
      lastPrint = millis();
      Serial.printf("[AMP-DIAG-9][I2S WRITE FAIL] %s, %u/%u bytes\n",
                    esp_err_to_name(err), (unsigned)written, (unsigned)expected);
    }
  }
}
