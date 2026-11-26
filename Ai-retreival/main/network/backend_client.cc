#include "backend_client.h"
#include <esp_log.h>
#include <esp_http_client.h>
#include <esp_heap_caps.h>
#include <cJSON.h>
#include <cstring>
#include <algorithm>

#define TAG "BackendClient"

BackendClient::BackendClient(const std::string& host, int port)
    : host_(host), port_(port) {
    char url[64];
    snprintf(url, sizeof(url), "http://%s:%d", host_.c_str(), port_);
    base_url_ = url;
}

void BackendClient::SetServer(const std::string& host, int port) {
    host_ = host;
    port_ = port;
    char url[64];
    snprintf(url, sizeof(url), "http://%s:%d", host_.c_str(), port_);
    base_url_ = url;
}

void BackendClient::WriteWavHeader(uint8_t* header, uint32_t data_bytes, uint32_t sample_rate,
                                   uint16_t channels, uint16_t bits_per_sample) {
    uint32_t byte_rate = sample_rate * channels * (bits_per_sample / 8);
    uint16_t block_align = channels * (bits_per_sample / 8);
    uint32_t riff_size = 36 + data_bytes;

    memcpy(header, "RIFF", 4);
    header[4] = (uint8_t)(riff_size & 0xFF);
    header[5] = (uint8_t)((riff_size >> 8) & 0xFF);
    header[6] = (uint8_t)((riff_size >> 16) & 0xFF);
    header[7] = (uint8_t)((riff_size >> 24) & 0xFF);

    memcpy(header + 8, "WAVEfmt ", 8);
    header[16] = 16; header[17] = 0; header[18] = 0; header[19] = 0; // Subchunk1Size
    header[20] = 1; header[21] = 0;                                  // AudioFormat: PCM
    header[22] = (uint8_t)(channels & 0xFF);
    header[23] = (uint8_t)((channels >> 8) & 0xFF);

    header[24] = (uint8_t)(sample_rate & 0xFF);
    header[25] = (uint8_t)((sample_rate >> 8) & 0xFF);
    header[26] = (uint8_t)((sample_rate >> 16) & 0xFF);
    header[27] = (uint8_t)((sample_rate >> 24) & 0xFF);

    header[28] = (uint8_t)(byte_rate & 0xFF);
    header[29] = (uint8_t)((byte_rate >> 8) & 0xFF);
    header[30] = (uint8_t)((byte_rate >> 16) & 0xFF);
    header[31] = (uint8_t)((byte_rate >> 24) & 0xFF);

    header[32] = (uint8_t)(block_align & 0xFF);
    header[33] = (uint8_t)((block_align >> 8) & 0xFF);

    header[34] = (uint8_t)(bits_per_sample & 0xFF);
    header[35] = (uint8_t)((bits_per_sample >> 8) & 0xFF);

    memcpy(header + 36, "data", 4);
    header[40] = (uint8_t)(data_bytes & 0xFF);
    header[41] = (uint8_t)((data_bytes >> 8) & 0xFF);
    header[42] = (uint8_t)((data_bytes >> 16) & 0xFF);
    header[43] = (uint8_t)((data_bytes >> 24) & 0xFF);
}

bool BackendClient::UploadVoice(const int16_t* pcm_data, size_t sample_count, VoiceResponse& response) {
    response.success = false;
    if (!pcm_data || sample_count == 0) {
        ESP_LOGE(TAG, "PCM data kosong, batal kirim ke server.");
        return false;
    }

    const char* boundary = "----ESP32AiRetrievalBoundary";
    uint32_t data_bytes = (uint32_t)(sample_count * sizeof(int16_t));
    uint32_t wav_bytes = 44 + data_bytes;

    std::string head = std::string("--") + boundary + "\r\n";
    head += "Content-Disposition: form-data; name=\"audio\"; filename=\"question.wav\"\r\n";
    head += "Content-Type: audio/wav\r\n\r\n";

    std::string tail = std::string("\r\n--") + boundary + "--\r\n";

    size_t total_body_size = head.length() + wav_bytes + tail.length();

    // Alokasikan payload di PSRAM Octal 8MB
    uint8_t* body = static_cast<uint8_t*>(heap_caps_malloc(total_body_size, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
    if (!body) {
        body = static_cast<uint8_t*>(malloc(total_body_size));
    }
    if (!body) {
        ESP_LOGE(TAG, "Gagal alokasi buffer upload sebesar %u bytes!", (unsigned)total_body_size);
        return false;
    }

    size_t offset = 0;
    memcpy(body + offset, head.c_str(), head.length());
    offset += head.length();

    WriteWavHeader(body + offset, data_bytes, 16000, 1, 16);
    offset += 44;

    memcpy(body + offset, pcm_data, data_bytes);
    offset += data_bytes;

    memcpy(body + offset, tail.c_str(), tail.length());

    std::string post_url = base_url_ + "/api/ai/voice";
    ESP_LOGI(TAG, "Mengunggah %.1f KB rekaman suara ke '%s'...",
             (float)total_body_size / 1024.0f, post_url.c_str());

    esp_http_client_config_t config = {};
    config.url = post_url.c_str();
    config.method = HTTP_METHOD_POST;
    config.timeout_ms = 18000; // Timeout 18 detik untuk Whisper STT + SBERT + EdgeTTS
    config.buffer_size = 2048;
    config.buffer_size_tx = 2048;

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) {
        ESP_LOGE(TAG, "Gagal inisialisasi HTTP client!");
        free(body);
        return false;
    }

    std::string content_type = std::string("multipart/form-data; boundary=") + boundary;
    esp_http_client_set_header(client, "Content-Type", content_type.c_str());

    esp_err_t err = esp_http_client_open(client, total_body_size);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Gagal membuka koneksi HTTP: %s", esp_err_to_name(err));
        esp_http_client_cleanup(client);
        free(body);
        return false;
    }

    int bytes_written = esp_http_client_write(client, (const char*)body, total_body_size);
    free(body); // Bebaskan buffer upload sesegera mungkin
    body = nullptr;

    if (bytes_written < 0) {
        ESP_LOGE(TAG, "Gagal mengirim data body!");
        esp_http_client_cleanup(client);
        return false;
    }

    int content_length = esp_http_client_fetch_headers(client);
    int status_code = esp_http_client_get_status_code(client);
    response.status_code = status_code;

    if (status_code != 200) {
        ESP_LOGE(TAG, "HTTP Server merespons error status: %d (len: %d)", status_code, content_length);
        esp_http_client_cleanup(client);
        return false;
    }

    std::string response_str;
    char read_buf[512];
    int r = 0;
    while ((r = esp_http_client_read(client, read_buf, sizeof(read_buf) - 1)) > 0) {
        read_buf[r] = '\0';
        response_str.append(read_buf, r);
    }
    esp_http_client_cleanup(client);

    ESP_LOGI(TAG, "Respons server diterima (%u bytes): %s",
             (unsigned)response_str.length(),
             response_str.substr(0, std::min<size_t>(response_str.length(), 200)).c_str());

    // Parsing JSON Respons
    cJSON* root = cJSON_Parse(response_str.c_str());
    if (!root) {
        ESP_LOGE(TAG, "Gagal parse cJSON respons server!");
        return false;
    }

    cJSON* item_status = cJSON_GetObjectItem(root, "status");
    if (item_status && item_status->valuestring) {
        if (strcmp(item_status->valuestring, "success") == 0) {
            response.success = true;
        }
    }

    cJSON* item_q = cJSON_GetObjectItem(root, "question");
    if (item_q && item_q->valuestring) response.question = item_q->valuestring;

    cJSON* item_ans = cJSON_GetObjectItem(root, "answer");
    if (item_ans && item_ans->valuestring) response.answer = item_ans->valuestring;

    cJSON* item_disp = cJSON_GetObjectItem(root, "display_text");
    if (item_disp && item_disp->valuestring) {
        response.display_text = item_disp->valuestring;
    } else {
        response.display_text = response.answer;
    }

    cJSON* item_wav = cJSON_GetObjectItem(root, "audio_wav_url");
    if (item_wav && item_wav->valuestring) response.audio_wav_url = item_wav->valuestring;

    cJSON* item_emo = cJSON_GetObjectItem(root, "emotion");
    if (item_emo && item_emo->valuestring) response.emotion = item_emo->valuestring;

    cJSON* item_trans = cJSON_GetObjectItem(root, "transcript");
    if (item_trans && item_trans->valuestring) response.transcript = item_trans->valuestring;

    cJSON* item_conf = cJSON_GetObjectItem(root, "confidence");
    if (item_conf) response.confidence = (float)item_conf->valuedouble;

    cJSON* item_matched = cJSON_GetObjectItem(root, "matched");
    if (item_matched) response.matched = cJSON_IsTrue(item_matched);

    cJSON* item_wake = cJSON_GetObjectItem(root, "wake_word_detected");
    if (item_wake) response.wake_word_detected = cJSON_IsTrue(item_wake);

    cJSON* item_wake_only = cJSON_GetObjectItem(root, "is_wake_word_only");
    if (item_wake_only) response.is_wake_word_only = cJSON_IsTrue(item_wake_only);

    cJSON_Delete(root);
    return response.success;
}

bool BackendClient::StreamPlayAudio(const std::string& wav_url, AudioCodec* codec,
                                    std::function<void()> on_start_playback) {
    if (!codec || wav_url.empty()) return false;

    std::string full_url = (wav_url.rfind("http", 0) == 0) ? wav_url : (base_url_ + wav_url);
    ESP_LOGI(TAG, "Streaming audio WAV dari: '%s'...", full_url.c_str());

    esp_http_client_config_t config = {};
    config.url = full_url.c_str();
    config.method = HTTP_METHOD_GET;
    config.timeout_ms = 10000;
    config.buffer_size = 2048;

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) {
        ESP_LOGE(TAG, "Gagal membuat HTTP client untuk streaming audio!");
        return false;
    }

    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "Gagal koneksi streaming audio: %s", esp_err_to_name(err));
        esp_http_client_cleanup(client);
        return false;
    }

    int content_length = esp_http_client_fetch_headers(client);
    int status_code = esp_http_client_get_status_code(client);
    if (status_code != 200) {
        ESP_LOGE(TAG, "Streaming audio gagal, HTTP status: %d", status_code);
        esp_http_client_cleanup(client);
        return false;
    }

    // 1. Baca 44-byte WAV header
    uint8_t wav_header[44];
    int header_read = esp_http_client_read(client, (char*)wav_header, 44);
    if (header_read < 44) {
        ESP_LOGE(TAG, "Header WAV tidak lengkap atau terpotong!");
        esp_http_client_cleanup(client);
        return false;
    }

    uint16_t channels = wav_header[22] | (wav_header[23] << 8);
    uint32_t sample_rate = wav_header[24] | (wav_header[25] << 8) | (wav_header[26] << 16) | (wav_header[27] << 24);
    ESP_LOGI(TAG, "WAV Info: %lu Hz, %d channel(s), total bytes: %d",
             (unsigned long)sample_rate, (int)channels, content_length);

    if (on_start_playback) {
        on_start_playback();
    }

    // 2. Baca chunk streaming dan langsung salurkan ke I2S MAX98357A
    uint8_t chunk_buf[1024];
    std::vector<int16_t> mono_buf(512);
    int remaining = (content_length > 44) ? (content_length - 44) : -1;

    while (remaining > 0 || remaining == -1) {
        int to_read = sizeof(chunk_buf);
        if (remaining > 0 && to_read > remaining) to_read = remaining;

        int bytes_read = esp_http_client_read(client, (char*)chunk_buf, to_read);
        if (bytes_read <= 0) {
            break; // Selesai stream
        }

        if (channels == 2) {
            // Stereo ke Mono (ambil channel Kiri)
            int num_stereo_samples = bytes_read / sizeof(int16_t);
            int num_mono_samples = num_stereo_samples / 2;
            if (mono_buf.size() < (size_t)num_mono_samples) {
                mono_buf.resize(num_mono_samples);
            }
            int16_t* in_samples = (int16_t*)chunk_buf;
            for (int i = 0; i < num_mono_samples; i++) {
                mono_buf[i] = in_samples[i * 2];
            }
            codec->Write(mono_buf.data(), num_mono_samples);
        } else {
            // Mono murni
            int num_samples = bytes_read / sizeof(int16_t);
            codec->Write((const int16_t*)chunk_buf, num_samples);
        }

        if (remaining > 0) remaining -= bytes_read;
        vTaskDelay(pdMS_TO_TICKS(1)); // Yield agar task lain tetap bernapas
    }

    esp_http_client_cleanup(client);
    ESP_LOGI(TAG, "Pemutaran streaming audio selesai.");
    return true;
}

bool BackendClient::GetPomodoro(PomodoroState& state) {
    state.success = false;
    std::string url = base_url_ + "/api/esp/pomodoro";

    esp_http_client_config_t config = {};
    config.url = url.c_str();
    config.method = HTTP_METHOD_GET;
    config.timeout_ms = 4000;

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) return false;

    esp_err_t err = esp_http_client_open(client, 0);
    if (err != ESP_OK) {
        esp_http_client_cleanup(client);
        return false;
    }

    esp_http_client_fetch_headers(client);
    int status_code = esp_http_client_get_status_code(client);
    if (status_code != 200) {
        esp_http_client_cleanup(client);
        return false;
    }

    std::string resp;
    char buf[256];
    int r = 0;
    while ((r = esp_http_client_read(client, buf, sizeof(buf) - 1)) > 0) {
        buf[r] = '\0';
        resp.append(buf, r);
    }
    esp_http_client_cleanup(client);

    cJSON* root = cJSON_Parse(resp.c_str());
    if (!root) return false;

    cJSON* m = cJSON_GetObjectItem(root, "mode");
    if (m && m->valuestring) state.mode = m->valuestring;

    cJSON* s = cJSON_GetObjectItem(root, "status");
    if (s && s->valuestring) state.status = s->valuestring;

    cJSON* t = cJSON_GetObjectItem(root, "time_str");
    if (t && t->valuestring) state.time_str = t->valuestring;

    cJSON* tl = cJSON_GetObjectItem(root, "time_left");
    if (tl) state.time_left = tl->valueint;

    cJSON* cy = cJSON_GetObjectItem(root, "cycle_str");
    if (cy && cy->valuestring) state.cycle_str = cy->valuestring;

    cJSON* tk = cJSON_GetObjectItem(root, "task");
    if (tk && tk->valuestring) state.task = tk->valuestring;

    cJSON* em = cJSON_GetObjectItem(root, "emotion");
    if (em && em->valuestring) state.emotion = em->valuestring;

    cJSON* fc = cJSON_GetObjectItem(root, "focus");
    if (fc) state.focus = fc->valueint;

    state.success = true;
    cJSON_Delete(root);
    return true;
}

bool BackendClient::CheckHealth() {
    std::string url = base_url_ + "/api/health";
    esp_http_client_config_t config = {};
    config.url = url.c_str();
    config.method = HTTP_METHOD_GET;
    config.timeout_ms = 4000;

    esp_http_client_handle_t client = esp_http_client_init(&config);
    if (!client) return false;

    esp_err_t err = esp_http_client_perform(client);
    int status = esp_http_client_get_status_code(client);
    esp_http_client_cleanup(client);

    return (err == ESP_OK && status == 200);
}
