# CHECKLIST KONFIRMASI — Migrasi Asisten Belajar ke Fine-Tuned SBERT + Nonaktif Kamera

**Tanggal:** 22 November 2026
**Status:** ✅ Dieksekusi sesuai komentar pada tabel ringkasan (22 Nov 2026)
**Tujuan:** Mengunci 7 keputusan yang masih ambigu sebelum implementasi dimulai.

---

## Cara pakai

1. Baca tiap poin.
2. Centang `[x]` pada opsi yang kamu pilih (boleh pilih lebih dari satu jika disebutkan).
3. Tulis catatan tambahan di baris **"Catatan kamu"** bila perlu.
4. Setelah semua terisi, bilang **"checklist sudah diisi, lanjut"**.
5. Baru setelah itu implementasi dikerjakan.

---

## Ringkasan 7 Keputusan

| # | Topik | Rekomendasi | Sudah diisi? |
|---|-------|-------------|--------------|
| 1 | Engine Speech-to-Text (STT) | `faster-whisper` lokal (CPU) | [x] |
| 2 | Cara menghasilkan jawaban | Template + passage retrieval | [x] |
| 3 | Layout teks di OLED | Mata dikecilkan + 3–4 baris teks | [x] buat textnya berjalan aja dari kanan kekiri |
| 4 | Nasib Pomodoro & alarm | Pomodoro tetap, alarm HP/absen dihapus | [x] ya dihapus |
| 5 | Nasib Gemini | Dicabut dari alur utama, simpan sebagai fallback | [x]  ya dihapus |
| 6 | Cara hapus model CV + frontend | Hapus permanen via `git rm`, frontend dibersihkan | [x] ya dihapus|
| 7 | Threshold confidence | Tolak jawaban jika skor < 0.35 | [x] |

---

## 1. Engine Speech-to-Text (STT)

**Konteks:** Saat ini ESP tidak mengirim suara user, hanya mengirim kalimat tetap saat mic mendeteksi suara keras. Agar "yang diomongkan user" benar-benar diproses, audio harus diubah jadi teks. Fitur ini belum ada di project.

**Pilih satu:**

- [ ] **A. `faster-whisper` lokal di server** — gratis, offline, model `small` (±500 MB) atau `base` (±150 MB). Latency ±1–3 detik per ucapan pendek di CPU. *Rekomendasi.*
- [ ] **B. API STT online** (Groq Whisper / OpenAI Whisper / Google STT) — lebih cepat & akurat, tapi butuh internet + API key + biaya.
- [ ] **C. STT di sisi lain** (jelaskan): ______________________________________________

**Pilih ukuran model bila A:**

- [ ] `base` (ringan, akurasi cukup)
- [ ] `small` (lebih akurat, lebih berat) *Rekomendasi*
- [ ] `medium` (paling akurat, berat)

**Catatan kamu:** ____________________________________________________________

---

## 2. Cara Menghasilkan Jawaban

**Konteks:** Model fine-tuned yang kamu buat adalah **retrieval** (mirip pencarian makna), **bukan generator teks**. Output notebook-nya berupa template:
> "Halo pembelajar! Pertanyaanmu berkaitan dengan {bab}, khususnya {episode}. Ingat kembali konsep: {concept}..."

Artinya model memilih materi paling relevan, lalu jawaban disusun dari data tersebut.

**Pilih satu:**

- [ ] **A. Template apa adanya** (persis seperti notebook) — paling murni, tapi jawaban terasa kaku & berulang.
- [ ] **B. Template + cuplikan `passage_text`** — jawaban lebih informatif, tetap 100% dari korpus fine-tuned. *Rekomendasi.*
- [ ] **C. Hybrid: passage hasil retrieval diumpankan ke Gemini** — jawaban paling natural, tapi hasil akhirnya dipengaruhi LLM lagi (bukan murni fine-tuned).
- [ ] **D. Lainnya** (jelaskan): ______________________________________________

**Catatan kamu:** ____________________________________________________________

---

## 3. Layout Teks Hasil di OLED

**Konteks:** OLED 128×64. Sekarang mata robot memakai area `y=0–47` dan HUD 1 baris di `y=48–63`. Teks jawaban yang panjang tidak muat di 1 baris.

**Pilih satu:**

- [ ] **A. Mode jawaban: mata dikecilkan ke atas, 3–4 baris teks di bawah + scroll otomatis.** *Rekomendasi.*
- [ ] **B. Full-screen teks bergantian dengan wajah** (wajah hilang sementara saat menjawab).
- [ ] **C. Ticker 1 baris di bawah** (teks berjalan, mata tetap besar).
- [ ] **D. Lainnya** (jelaskan): ______________________________________________

**Perilaku setelah jawaban selesai:**

- [ ] Kembali otomatis ke wajah setelah ±5 detik
- [ ] Tetap tampil sampai user bertanya lagi
- [ ] Kembali saat audio selesai diputar

**Catatan kamu:** ____________________________________________________________

---

## 4. Nasib Pomodoro & Alarm

**Konteks:** Kamera dimatikan, jadi deteksi HP/absen dari server otomatis hilang. Fitur Pomodoro (timer, fokus, HUD) sebenarnya tidak butuh kamera.

**Pilih satu:**

- [ ] **A. Pomodoro tetap jalan, alarm HP/absen dihapus total.** *Rekomendasi.*
- [ ] **B. Pomodoro tetap jalan, alarm dipertahankan tapi dipicu manual/endpoint lain.**
- [ ] **C. Hapus Pomodoro juga, OLED & server fokus asisten tanya-jawab saja.**
- [ ] **D. Lainnya** (jelaskan): ______________________________________________

**Catatan kamu:** ____________________________________________________________

---

## 5. Nasib Gemini

**Konteks:** `/api/ai/ask` sekarang memakai Gemini. Kamu ingin model fine-tuned yang menjawab. Gemini masih berguna untuk pertanyaan di luar 303 materi atau untuk merangkai kalimat.

**Pilih satu:**

- [ ] **A. Gemini dicabut dari alur utama; disimpan sebagai fallback** bila confidence rendah / materi tidak ditemukan. *Rekomendasi.*
- [ ] **B. Hapus Gemini total** (kode, API key, dependency) — 100% lokal.
- [ ] **C. Gemini tetap jadi generator utama**, fine-tuned hanya untuk retrieval konteks.
- [ ] **D. Lainnya** (jelaskan): ______________________________________________

**Catatan kamu:** ____________________________________________________________

---

## 6. Cara Hapus Model CV & Frontend

**Konteks:** Di `computer-vision/model/` ada banyak model kamera/CV. Yang dipertahankan hanya `output_artifacts/`. Frontend juga masih memanggil `/video_feed` untuk widget kamera.

**6a. Cara menghapus file model & kode CV:**

- [ ] **A. Hapus permanen via `git rm`** (bisa dipulihkan dari riwayat git). *Rekomendasi.*
- [ ] **B. Pindahkan dulu ke folder `archive/`**, baru hapus setelah kamu yakin.
- [ ] **C. Jangan hapus apa pun, cukup jangan dipakai** (paling aman, folder tetap besar).

**6b. Frontend yang memanggil `/video_feed`:**

- [ ] **A. Bersihkan juga** (hapus widget kamera, status kamera, tombol stream). *Rekomendasi.*
- [ ] **B. Biarkan, nanti error-nya diterima** (tidak direkomendasikan).
- [ ] **C. Frontend tidak termasuk scope**, jangan disentuh.

**6c. File/folder yang akan dihapus (centang yang setuju):**

- [ ] `face_landmarker.task`
- [ ] `gesture_recognizer.task`
- [ ] `hand_landmarker.task`
- [ ] `MobileNetSSD_deploy.caffemodel` + `.prototxt`
- [ ] `phone_yolov5s.onnx`
- [ ] `yolov8n.onnx`
- [ ] `sibi_abjad_model.pkl` + `sibi_labels.json`
- [ ] folder `ssd_mobilenet_v2_coco_2018_03_29/` + `.pbtxt` + `.tar.gz`
- [ ] kode `core/camera_streamer.py`, `distraction_detector.py`, `phone_detector.py`, `coco_detector.py`, `mediapipe_detector.py`, `image_enhancer.py`
- [ ] endpoint `/video_feed`, `/api/camera/source`, thread `vision_pipeline_loop`
- [ ] **JANGAN hapus** `model/output_artifacts/` (wajib dipertahankan)

**Catatan kamu:** ____________________________________________________________

---

## 7. Threshold Confidence

**Konteks:** Kalau pertanyaan user di luar 303 materi, model tetap memilih top-1 (walau skornya rendah). Tanpa threshold, robot bisa menjawab ngawur.

**Pilih satu:**

- [ ] **A. Skor < 0.35 → tolak sopan** ("Materi ini belum ada di kurikulum, coba tanyakan topik Python lain"). *Rekomendasi.*
- [ ] **B. Skor < 0.25 → tolak** (lebih toleran, lebih sering menjawab).
- [ ] **C. Skor < 0.50 → tolak** (lebih ketat, lebih sering menolak).
- [ ] **D. Tanpa threshold** (selalu jawab top-1).
- [ ] **E. Nilai lain:** ________

**Catatan kamu:** ____________________________________________________________

---

## Tambahan Teknis (opsional, tapi sebaiknya dijawab)

Ini bukan bagian dari 7 keputusan, tapi memengaruhi implementasi:

- [ ] **Durasi rekaman mic:** otomatis berhenti setelah ____ detik hening / maksimal ____ detik. (Rekomendasi: hening 1,2 dtk, maks 8 dtk)
- [ ] **Suara TTS default:** `cowok` (`id-ID-ArdiNeural`) — konfirmasi?
- [ ] **IP server hardcoded** `10.19.170.155` — tetap, atau mau dibuat bisa dikonfigurasi?
- [ ] **Endpoint baru:** `POST /api/ai/voice` (upload WAV) dan `POST /api/ai/ask` (teks) — setuju?
- [ ] **Format audio upload:** WAV 16 kHz, 16-bit, mono — setuju?
- [ ] **Model di-load saat startup** (butuh ±1–2 detik + RAM ±1 GB) — setuju?

---

## Checklist Final Sebelum Eksekusi

- [x] Poin 1 (STT) sudah dijawab
- [x] Poin 2 (cara jawab) sudah dijawab
- [x] Poin 3 (OLED) sudah dijawab
- [x] Poin 4 (Pomodoro/alarm) sudah dijawab
- [x] Poin 5 (Gemini) sudah dijawab
- [x] Poin 6 (hapus model + frontend) sudah dijawab
- [x] Poin 7 (threshold) sudah dijawab
- [x] Tambahan teknis sudah dijawab
- [x] User bilang **"lanjut"**

> ✅ Checklist selesai. Implementasi dikerjakan 22 November 2026.

---

## Hasil Implementasi (22 Nov 2026)

| Area | Hasil |
|------|-------|
| STT | `faster-whisper` lokal, default `small`, decode WAV via NumPy (tanpa PyAV) |
| Retrieval | `core/retrieval_service.py`, model `model/output_artifacts/finetuned_sbert` |
| Jawaban | Template + `passage_text` (dipotong ±160 char) |
| Threshold | `RETRIEVAL_MIN_SCORE=0.35` |
| TTS | Edge-TTS `id-ID-ArdiNeural` (cowok), WAV 16 kHz stereo |
| OLED | Mata dikompres ke atas + marquee teks kanan → kiri, kembali ke wajah 6 dtk setelah audio |
| Pomodoro | Tetap berjalan; alarm HP/absen dihapus |
| Gemini | Dihapus dari kode, `.env`, dan dependency |
| Kamera | Firmware & server dibersihkan; pin kamera tidak diinisialisasi |
| Model CV | Semua dihapus dari `computer-vision/model/`, hanya `output_artifacts/` tersisa |
| Frontend | Widget kamera, tombol stream, modal, dan CSS kamera dihapus |
| Legacy | `computer-vision/archive/` (Flask + SIBI) dihapus |
| Verifikasi | Build PlatformIO OK, `tsc` OK, uji teks & suara end-to-end OK |

### Catatan Menjalankan Server

1. `pip install -r requirements.txt` (atau buka devcontainer).
2. Pastikan `ffmpeg` terpasang.
3. Jalankan `python app.py`.
4. Request suara pertama memicu unduhan model Whisper `small` (±500 MB). Model
   dimuat di background saat startup agar tidak memblokir FastAPI.
