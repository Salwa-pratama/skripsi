# Asisten Belajar AI — FastAPI Server

Server ini menjalankan **model Sentence-Transformer hasil fine-tuning** untuk
menjawab pertanyaan belajar Python dari robot ESP32-S3. Seluruh fitur kamera /
computer-vision (COCO-SSD, YOLO, MediaPipe, SIBI) sudah **dihapus**.

## Alur Sistem

```
Mic INMP441 (ESP32) -> rekam WAV 16 kHz
        -> POST /api/ai/voice
        -> faster-whisper (STT Bahasa Indonesia)
        -> fine-tuned SBERT retrieval (303 passage materi)
        -> jawaban teks
        -> Edge-TTS id-ID-ArdiNeural (suara cowok)
        -> WAV 16 kHz stereo -> speaker MAX98357A
        -> teks jawaban tampil di OLED (marquee kanan -> kiri)
```

## Artefak Model

Semua artefak berada di `model/output_artifacts/`:

- `finetuned_sbert/` — model fine-tuned (`paraphrase-multilingual-MiniLM-L12-v2`)
- `corpus_metadata.json` — 303 passage materi (bab, episode, konsep, teks)
- `corpus_embeddings_finetuned.npy` — matriks embedding 303 × 384

## Endpoint Utama

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| POST | `/api/ai/voice` | Upload WAV pertanyaan → STT → retrieval → TTS |
| POST | `/api/ai/ask` | Pertanyaan teks → retrieval → TTS |
| GET | `/api/ai/audio/{file}` | Streaming MP3 / WAV 16 kHz untuk ESP32 |
| POST/GET | `/api/ai/voice/config` | Atur / lihat suara (`cowok` / `cewek`) |
| GET | `/api/esp/pomodoro` | Status ringkas Pomodoro untuk OLED |
| GET | `/api/health` | Status server + kesiapan model |

Contoh uji teks:

```bash
curl -X POST http://localhost:5000/api/ai/ask \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Gimana cara membuat fungsi dengan parameter default?"}'
```

Contoh uji suara:

```bash
curl -X POST http://localhost:5000/api/ai/voice \
  -F "audio=@pertanyaan.wav" \
  -F "voice=cowok"
```

## Instalasi

```bash
cd computer-vision
python3 -m venv .venv
source .venv/bin/activate

# Opsional: torch CPU-only agar tidak mengunduh build CUDA
pip install torch --index-url https://download.pytorch.org/whl/cpu

pip install -r requirements.txt
```

Prasyarat sistem:

- `ffmpeg` terpasang (untuk konversi MP3 → WAV via `pydub`).
- Request suara pertama akan mengunduh model faster-whisper (`small`, ±500 MB).
  Jika ingin offline penuh, unduh model sekali lalu set `WHISPER_MODEL_SIZE`
  ke path lokal.

Konfigurasi ada di `.env` (lihat `.env.example`).

## Menjalankan

```bash
python app.py
# atau
uvicorn server:app --host 0.0.0.0 --port 5000
```

Buka dokumentasi interaktif: <http://localhost:5000/docs>

## Catatan

- Model fine-tuned bersifat **retrieval**, bukan generator. Jawaban disusun dari
  `chapter_title`, `episode_title`, `concept`, dan `passage_text` teratas.
- Jika cosine similarity < `RETRIEVAL_MIN_SCORE` (default `0.35`), robot menolak
  dengan sopan karena pertanyaan dianggap di luar kurikulum.
- Database MySQL bersifat opsional untuk endpoint gamifikasi/Pomodoro. Endpoint
  AI tetap berjalan tanpa database.
