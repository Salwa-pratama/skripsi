#include "camera_config.h"


// ==========================================
// FUNCTION TES KAMERA (MODE 2)
// ==========================================
void setupTesKamera() {
  delay(2000);
  Serial.println("\nMemulai tes inisialisasi modul kamera OV5640...");

  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;  // XCLK MHz
  config.frame_size = FRAMESIZE_CIF;         // 400x296
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 22;
  config.fb_count = 2;                      // 2 buffer untuk streaming lancar

  // Memulai inisialisasi
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Gagal inisialisasi kamera! Error code: 0x%x\n", err);
    return;
  }
  Serial.println("KAMERA BERHASIL TERDETEKSI DAN SIAP DIGUNAKAN!");

  sensor_t *s = esp_camera_sensor_get();
  // Untuk konfigurasi rotasi kamera
  if(s != NULL) {
    s->set_vflip(s, 1); // 1 = putar balik, 0 = normal
    s->set_hmirror(s, 1); // 1 = mirror, 0 = normal

    // Optimasi FPS:
    s->set_denoise(s, 0);
    s->set_special_effect(s, 0);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);

    s->set_framesize(s, FRAMESIZE_CIF);




    // s->set_gainceiling(s, GAINCEILING_8X); // Perkuat penangkapan cahaya di area gelap
    s->set_lenc(s, 0);             // 0 = Matikan Lens Correction (hilangkan semburat ungu)
    s->set_dcw(s, 0);              // 0 = Matikan Advanced AWB (warna lebih stabil)

  }
}

void loopTesKamera() {
   // Tidak perlu loop untuk tes deteksi ini
  delay(10000);
}

