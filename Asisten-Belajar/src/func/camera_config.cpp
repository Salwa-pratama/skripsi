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
  config.frame_size = FRAMESIZE_HVGA;        // 480x320 -> ~5.1 KB/frame (mode tercepat OV5640, <= buffer TCP 5.7 KB)
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;     // Continuous non-blocking capture (selalu ambil frame terbaru, anti-lag)
  config.fb_location = CAMERA_FB_IN_PSRAM;
  config.jpeg_quality = 24;                  // Kompresi hemat bandwidth namun wajah tetap jelas
  config.fb_count = 2;                      // 2 buffer untuk streaming lancar

  // Memulai inisialisasi
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Gagal inisialisasi kamera! Error code: 0x%x\n", err);
    return;
  }
  Serial.println("KAMERA BERHASIL TERDETEKSI DAN SIAP DIGUNAKAN!");

  sensor_t *s = esp_camera_sensor_get();
  // Untuk konfigurasi rotasi kamera & penyesuaian kualitas gambar terang, tajam & wajah jelas
  if(s != NULL) {
    s->set_framesize(s, FRAMESIZE_HVGA);  // 480x320: mode tercepat + frame ~5.1 KB (aman di bawah buffer TCP ESP32)
    s->set_vflip(s, 1);                   // 1 = Balik vertikal
    s->set_hmirror(s, 1);                 // 1 = Balik horizontal

    // Pengaturan Sensor untuk Gambar Terang, Jernih & Wajah Terlihat Jelas:
    s->set_denoise(s, 0);                 // 0 = Matikan filter denoise internal
    s->set_special_effect(s, 0);
    s->set_lenc(s, 0);                    // 0 = Matikan Lens Correction (Hilangkan semburat ungu)
    s->set_dcw(s, 0);                     // 0 = Matikan DCW (Warna natural, tidak over-processed)
    s->set_brightness(s, 2);              // 2 = Boost kecerahan maksimal (+2) agar wajah tidak siluet
    s->set_contrast(s, 0);                // 0 = Kontras natural
    s->set_saturation(s, 0);              // 0 = Saturasi natural

    // Manual Exposure TERKALIBRASI: cukup terang di bawah lampu plafon, TAPI tetap di dalam
    // periode frame sensor (<=400 baris) supaya OV5640 tetap berputar ~30 FPS.
    s->set_exposure_ctrl(s, 0);           // 0 = Manual AEC (anti wajah gelap karena backlight)
    s->set_aec_value(s, 400);             // 400 = Kecerahan wajah optimal tanpa mencekik VSYNC
    s->set_gain_ctrl(s, 0);               // 0 = Manual AGC
    s->set_agc_gain(s, 26);               // 26 = Penguatan analog tinggi: terang tanpa menambah exposure time
    s->set_gainceiling(s, GAINCEILING_32X);
    s->set_bpc(s, 1);                     // 1 = Koreksi piksel rusak (hot pixels)
    s->set_wpc(s, 1);
    s->set_raw_gma(s, 1);
  }
}

void loopTesKamera() {
   // Tidak perlu loop untuk tes deteksi ini
  delay(10000);
}

