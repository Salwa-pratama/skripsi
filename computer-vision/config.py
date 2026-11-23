"""Konfigurasi terpusat Asisten Belajar AI (FastAPI).

Fokus server sekarang:
1. Retrieval materi Python memakai model Sentence-Transformer hasil fine-tuning.
2. Speech-to-Text (faster-whisper) untuk pertanyaan suara dari ESP32-S3.
3. Text-to-Speech Bahasa Indonesia (Edge-TTS, default suara cowok/Ardi).
4. State machine Pomodoro & gamifikasi MDA.

Seluruh fitur kamera/computer-vision sudah dihapus.
"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # izinkan modul retrieval diuji tanpa python-dotenv
    load_dotenv = None

BASE_DIR = Path(__file__).resolve().parent
if load_dotenv is not None:
    load_dotenv(BASE_DIR / ".env", override=True)


class Config:
    # =====================================================================
    # Server
    # =====================================================================
    SECRET_KEY = os.getenv("SECRET_KEY", "asisten-belajar-secret-2026")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))

    # =====================================================================
    # Model Fine-Tuned SBERT & Korpus Materi
    # ---------------------------------------------------------------------
    # Artefak hasil notebook training-model/train/chatbot_finetuned.ipynb
    # dipindahkan ke: computer-vision/model/output_artifacts/
    # =====================================================================
    ARTIFACTS_DIR = Path(
        os.getenv("ARTIFACTS_DIR", str(BASE_DIR / "model" / "output_artifacts"))
    )
    FINETUNED_MODEL_DIR = ARTIFACTS_DIR / "finetuned_sbert"
    CORPUS_METADATA_FILE = ARTIFACTS_DIR / "corpus_metadata.json"
    CORPUS_EMBEDDINGS_FILE = ARTIFACTS_DIR / "corpus_embeddings_finetuned.npy"

    # Ambang minimal cosine similarity. Di bawah nilai ini pertanyaan dianggap
    # di luar 303 materi kurikulum, sehingga robot menolak dengan sopan.
    RETRIEVAL_MIN_SCORE = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.35"))
    RETRIEVAL_TOP_K = int(os.getenv("RETRIEVAL_TOP_K", "3"))

    # =====================================================================
    # Speech-to-Text (faster-whisper, lokal di CPU)
    # =====================================================================
    WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "id")

    # =====================================================================
    # Text-to-Speech
    # =====================================================================
    # Default: cowok Indonesia (id-ID-ArdiNeural).
    TTS_DEFAULT_VOICE = os.getenv("VOICE_GENDER", "cowok")

    # =====================================================================
    # Pomodoro Defaults (detik)
    # =====================================================================
    POMODORO_WORK_TIME = 25 * 60
    POMODORO_SHORT_BREAK = 5 * 60
    POMODORO_LONG_BREAK = 15 * 60
