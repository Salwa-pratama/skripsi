#include "voice_client.h"

#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <esp32-hal-psram.h>

#include "audio_test.h"
#include "robot_face.h"
#include "oled_config.h"
#include "server_config.h"

// =========================================================================
// KONFIGURASI PEREKAMAN PERTANYAAN USER
// =========================================================================
static const uint32_t RECORD_SAMPLE_RATE   = 16000; // Hz (cocok dengan faster-whisper)
static const uint32_t MAX_RECORD_MS        = 8000;  // batas maksimal rekaman
static const uint32_t MIN_SPEECH_MS        = 500;   // minimal durasi bicara
static const uint32_t SILENCE_STOP_MS      = 1200;  // berhenti setelah hening 1,2 dtk
static const int      VOICE_TRIGGER_PEAK   = 1200;  // threshold suara bicara manusia normal
static const int      SILENCE_PEAK         = 250;   // ambang hening di bawah suara manusia
static const size_t   MAX_SAMPLES          = (RECORD_SAMPLE_RATE * MAX_RECORD_MS) / 1000;
static const size_t   FRAME_SAMPLES        = 512;

static inline void putLE16(uint8_t* p, uint16_t v) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)((v >> 8) & 0xFF);
}

static inline void putLE32(uint8_t* p, uint32_t v) {
  p[0] = (uint8_t)(v & 0xFF);
  p[1] = (uint8_t)((v >> 8) & 0xFF);
  p[2] = (uint8_t)((v >> 16) & 0xFF);
  p[3] = (uint8_t)((v >> 24) & 0xFF);
}

// Tulis header WAV 44 byte (PCM 16-bit mono).
static void writeWavHeader(uint8_t* header, uint32_t dataBytes) {
  memcpy(header, "RIFF", 4);
  putLE32(header + 4, 36 + dataBytes);
  memcpy(header + 8, "WAVE", 4);
  memcpy(header + 12, "fmt ", 4);
  putLE32(header + 16, 16);                 // subchunk1 size
  putLE16(header + 20, 1);                  // PCM
  putLE16(header + 22, 1);                  // mono
  putLE32(header + 24, RECORD_SAMPLE_RATE);
  putLE32(header + 28, RECORD_SAMPLE_RATE * 2); // byte rate
  putLE16(header + 32, 2);                  // block align
  putLE16(header + 34, 16);                 // bits per sample
  memcpy(header + 36, "data", 4);
  putLE32(header + 40, dataBytes);
}

// =========================================================================
// SETUP
// =========================================================================
void setupVoiceClient() {
  Serial.println("[VOICE] Subsistem pertanyaan suara siap.");
  Serial.printf("[VOICE] Endpoint STT: %s\n", AI_VOICE_URL);
  Serial.printf("[VOICE] Rekaman maks %lu ms | hening berhenti %lu ms\n",
                (unsigned long)MAX_RECORD_MS, (unsigned long)SILENCE_STOP_MS);
}

// =========================================================================
// REKAM PERTANYAAN USER
// -------------------------------------------------------------------------
// Mengembalikan jumlah sample PCM 16-bit yang direkam (0 = gagal/tidak ada
// suara). Buffer `pcm` harus sudah dialokasikan minimal MAX_SAMPLES.
// =========================================================================
static size_t recordUserSpeech(int16_t* pcm) {
  if (!pcm) return 0;

  initI2SMicrophone(RECORD_SAMPLE_RATE, false);

  size_t totalSamples = 0;
  bool heardSpeech = false;
  unsigned long startMs = millis();
  unsigned long speechStartMs = 0;
  unsigned long lastVoiceMs = 0;
  unsigned long lastOledRefresh = 0;

  int16_t frame[FRAME_SAMPLES];

  while (millis() - startMs < (MAX_RECORD_MS + 2500)) {
    size_t n = readMicSamples(frame, FRAME_SAMPLES, 60);
    if (n == 0) {
      delay(2);
      continue;
    }

    int peak = 0;
    for (size_t i = 0; i < n; i++) {
      int v = frame[i];
      if (v < 0) v = -v;
      if (v > peak) peak = v;
    }

    unsigned long now = millis();

    if (!heardSpeech) {
      // Tunggu suara pertama yang cukup jelas (misal pemicu "Hi ESP").
      if (peak < VOICE_TRIGGER_PEAK) continue;
      heardSpeech = true;
      speechStartMs = now;
      lastVoiceMs = now;
      Serial.printf("\n[VOICE] Voice trigger aktif (peak %d), mulai merekam...\n", peak);
      setFaceEmotionOverride("LISTENING", 10000);
      updateOLED();
    }

    // Refresh OLED secara berkala (~33 ms) agar animasi mata & teks "Mendengarkan..." aktif
    if (now - lastOledRefresh >= 33) {
      lastOledRefresh = now;
      updateOLED();
    }

    size_t remaining = MAX_SAMPLES - totalSamples;
    if (remaining == 0) break;
    size_t toCopy = (n < remaining) ? n : remaining;
    memcpy(pcm + totalSamples, frame, toCopy * sizeof(int16_t));
    totalSamples += toCopy;

    if (peak >= SILENCE_PEAK) lastVoiceMs = now;

    bool longEnough = (now - speechStartMs) >= MIN_SPEECH_MS;
    bool silentEnough = (now - lastVoiceMs) >= SILENCE_STOP_MS;
    if (longEnough && silentEnough) break;
  }

  if (!heardSpeech || totalSamples < (RECORD_SAMPLE_RATE * MIN_SPEECH_MS) / 1000) {
    Serial.println("[VOICE] Tidak ada ucapan yang cukup jelas. Batal.");
    return 0;
  }

  Serial.printf("[VOICE] Rekaman selesai: %u sample (%.1f detik)\n",
                (unsigned)totalSamples,
                (float)totalSamples / (float)RECORD_SAMPLE_RATE);
  return totalSamples;
}

// =========================================================================
// UPLOAD WAV (multipart/form-data) KE SERVER
// =========================================================================
static bool uploadWav(const int16_t* pcm, size_t totalSamples, String& responseOut) {
  const char* boundary = "----ESP32AsistenBelajarBoundary";
  uint32_t dataBytes = (uint32_t)(totalSamples * sizeof(int16_t));
  uint32_t wavBytes = 44 + dataBytes;

  String head = String("--") + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"audio\"; filename=\"question.wav\"\r\n";
  head += "Content-Type: audio/wav\r\n\r\n";
  String tail = String("\r\n--") + boundary + "--\r\n";

  size_t totalBody = head.length() + wavBytes + tail.length();

  // Buffer besar -> prioritaskan PSRAM.
  uint8_t* body = (uint8_t*)ps_malloc(totalBody);
  if (!body) body = (uint8_t*)malloc(totalBody);
  if (!body) {
    Serial.println("[VOICE ERROR] Gagal alokasi buffer upload.");
    return false;
  }

  size_t offset = 0;
  memcpy(body + offset, head.c_str(), head.length());
  offset += head.length();
  writeWavHeader(body + offset, dataBytes);
  offset += 44;
  memcpy(body + offset, pcm, dataBytes);
  offset += dataBytes;
  memcpy(body + offset, tail.c_str(), tail.length());

  WiFiClient client;
  HTTPClient http;
  http.setTimeout(8000);
  http.setReuse(false);

  if (!http.begin(client, AI_VOICE_URL)) {
    Serial.println("[VOICE ERROR] Gagal membuka koneksi ke server AI.");
    free(body);
    return false;
  }

  http.addHeader("Content-Type", String("multipart/form-data; boundary=") + boundary);
  Serial.printf("[VOICE] Mengirim %.1f KB audio ke server...\n", totalBody / 1024.0f);

  int httpCode = http.POST(body, totalBody);
  free(body);

  bool ok = false;
  if (httpCode == HTTP_CODE_OK) {
    responseOut = http.getString();
    ok = true;
  } else {
    Serial.printf("[VOICE ERROR] HTTP %d: %s\n", httpCode,
                  http.getString().substring(0, 180).c_str());
  }

  http.end();
  return ok;
}

// =========================================================================
// ALUR UTAMA: REKAM -> UPLOAD -> TAMPILKAN TEKS -> PUTAR TTS
// =========================================================================
bool askVoiceAssistantFromMic() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[VOICE] WiFi belum tersambung, batal bertanya.");
    clearFaceEmotionOverride();
    return false;
  }

  // Tampilkan visual "Mendengarkan..." di OLED secara instan
  setFaceEmotionOverride("LISTENING", 10000);
  updateOLED();

  int16_t* pcm = (int16_t*)ps_malloc(MAX_SAMPLES * sizeof(int16_t));
  if (!pcm) pcm = (int16_t*)malloc(MAX_SAMPLES * sizeof(int16_t));
  if (!pcm) {
    Serial.println("[VOICE ERROR] Gagal alokasi buffer rekaman.");
    clearFaceEmotionOverride();
    return false;
  }

  size_t totalSamples = recordUserSpeech(pcm);
  if (totalSamples == 0) {
    free(pcm);
    clearFaceEmotionOverride();
    return false;
  }

  // Wajah robot: mode berpikir + status di OLED.
  setFaceEmotionOverride("THINKING", 60000);
  renderOLED();

  String response;
  bool uploaded = uploadWav(pcm, totalSamples, response);
  free(pcm);

  if (!uploaded) {
    clearFaceEmotionOverride();
    return false;
  }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, response);
  if (err) {
    Serial.printf("[VOICE ERROR] Gagal parse JSON: %s\n", err.c_str());
    clearFaceEmotionOverride();
    return false;
  }

  const char* transcript = doc["transcript"] | "(tidak ada transkrip)";
  const char* answer = doc["answer"] | "";
  const char* displayText = doc["display_text"] | answer;
  const char* audioWavUrl = doc["audio_wav_url"] | "";
  const char* emotion = doc["emotion"] | "speaking";
  float confidence = doc["confidence"] | 0.0f;
  bool matched = doc["matched"] | false;
  bool wakeDetected = doc["wake_word_detected"] | false;
  bool isWakeOnly = doc["is_wake_word_only"] | false;

  Serial.println("\n=======================================================");
  Serial.printf("[STT] Ucapan user       : \"%s\"\n", transcript);
  Serial.printf("[WAKE WORD 'Hi ESP']    : %s\n", wakeDetected ? "TERDETEKSI" : "TIDAK ADA");
  Serial.printf("[SBERT] Confidence      : %.4f | matched: %s\n", confidence, matched ? "YA" : "TIDAK");
  Serial.printf("[JAWABAN] %s\n", answer);
  Serial.println("=======================================================");

  String userText = transcript;
  userText.trim();

  String aiText = displayText;
  if (aiText.length() == 0) aiText = answer;
  aiText.trim();

  // Susun teks lengkap: memunculkan teks ucapan user yang baru saja dibicarakan,
  // lalu diikuti oleh teks jawaban AI, berjalan geser dari kanan ke kiri (marquee)
  String fullScrollText = "";
  if (userText.length() > 0 && !userText.equals("(suara tidak terdeteksi)") && !userText.equals("(tidak ada transkrip)")) {
    fullScrollText = "Kamu: \"" + userText + "\"  >>>  AI: " + aiText;
  } else {
    fullScrollText = aiText;
  }
  if (fullScrollText.length() > 400) {
    fullScrollText = fullScrollText.substring(0, 397) + "...";
  }

  // Tampilkan teks ucapan user & jawaban AI di OLED (marquee kanan -> kiri).
  showAnswerText(fullScrollText, 0, "VOICE AI:");
  setFaceEmotionOverride("SPEAKING", 60000);
  renderOLED();

  bool played = false;
  if (strlen(audioWavUrl) > 0) {
    String fullAudioUrl = String(SERVER_BASE_URL) + String(audioWavUrl);
    Serial.printf("[VOICE] Memutar TTS: %s\n", fullAudioUrl.c_str());
    played = playWavFromUrl(fullAudioUrl.c_str());
  } else {
    Serial.println("[VOICE] Server tidak mengirim audio_wav_url.");
  }

  // Jika pemicu hanya wake-word greeting ("Hi ESP"), sambut user lalu otomatis
  // masuki mode "Mendengarkan..." untuk merekam pertanyaan berikutnya!
  if (isWakeOnly) {
    clearAnswerText();
    setFaceEmotionOverride("LISTENING", 10000);
    updateOLED();
    Serial.println("\n[VOICE] Wake word 'Hi ESP' aktif! Melanjutkan mendengarkan pertanyaan user...");

    int16_t* pcmNext = (int16_t*)ps_malloc(MAX_SAMPLES * sizeof(int16_t));
    if (!pcmNext) pcmNext = (int16_t*)malloc(MAX_SAMPLES * sizeof(int16_t));
    if (pcmNext) {
      size_t nextSamples = recordUserSpeech(pcmNext);
      if (nextSamples > 0) {
        setFaceEmotionOverride("THINKING", 60000);
        renderOLED();

        String nextResponse;
        bool nextUp = uploadWav(pcmNext, nextSamples, nextResponse);
        free(pcmNext);

        if (nextUp) {
          JsonDocument doc2;
          if (!deserializeJson(doc2, nextResponse)) {
            const char* ans2 = doc2["answer"] | "";
            const char* disp2 = doc2["display_text"] | ans2;
            const char* wav2 = doc2["audio_wav_url"] | "";
            const char* trans2 = doc2["transcript"] | "";
            float conf2 = doc2["confidence"] | 0.0f;
            bool match2 = doc2["matched"] | false;

            Serial.printf("[STT 2] Ucapan user : \"%s\"\n", trans2);
            Serial.printf("[SBERT 2] Conf: %.4f | Matched: %s\n", conf2, match2 ? "YA" : "TIDAK");
            Serial.printf("[JAWABAN 2] %s\n", ans2);

            String u2 = trans2;
            u2.trim();
            String a2 = disp2;
            if (a2.length() == 0) a2 = ans2;
            a2.trim();

            String full2 = "";
            if (u2.length() > 0 && !u2.equals("(suara tidak terdeteksi)") && !u2.equals("(tidak ada transkrip)")) {
              full2 = "Kamu: \"" + u2 + "\"  >>>  AI: " + a2;
            } else {
              full2 = a2;
            }
            if (full2.length() > 400) full2 = full2.substring(0, 397) + "...";

            showAnswerText(full2, 0, "VOICE AI:");
            setFaceEmotionOverride("SPEAKING", 60000);
            renderOLED();

            if (strlen(wav2) > 0) {
              String u2Url = String(SERVER_BASE_URL) + String(wav2);
              playWavFromUrl(u2Url.c_str());
            }
            showAnswerText(full2, 6000, "VOICE AI:");
            clearFaceEmotionOverride();
            return true;
          }
        }
      } else {
        free(pcmNext);
      }
    }
  }

  // Setelah audio selesai, tampilkan teks 6 detik lagi lalu kembali ke standby ("ASISTEN BELAJAR")
  showAnswerText(fullScrollText, 6000, "VOICE AI:");
  clearFaceEmotionOverride();
  Serial.printf("[VOICE] Selesai. Audio %s.\n", played ? "diputar" : "gagal diputar");
  return true;
}
