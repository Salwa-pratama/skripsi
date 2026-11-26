"""Speech-to-Text Service - faster-whisper (lokal, CPU).

Menerima byte audio dari ESP32-S3 (WAV PCM 16 kHz mono). Untuk format WAV,
audio didekode langsung dengan modul `wave` + NumPy sehingga tidak bergantung
pada versi PyAV/FFmpeg. Format lain (mis. webm dari browser) tetap didukung
lewat fallback file sementara.
"""

from __future__ import annotations

import io
import os
import tempfile
import threading
import wave
from typing import Optional

import numpy as np

from config import Config


class STTService:
    def __init__(self) -> None:
        self.model = None
        self._lock = threading.Lock()
        self._loaded = False
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Loading (lazy: model Whisper baru diunduh/dimuat saat request pertama)
    # ------------------------------------------------------------------
    def _ensure_model(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                from faster_whisper import WhisperModel

                print(
                    f"[STT] Memuat faster-whisper '{Config.WHISPER_MODEL_SIZE}' "
                    f"({Config.WHISPER_DEVICE}/{Config.WHISPER_COMPUTE_TYPE})... "
                    "unduhan pertama bisa memakan waktu.",
                    flush=True,
                )
                self.model = WhisperModel(
                    Config.WHISPER_MODEL_SIZE,
                    device=Config.WHISPER_DEVICE,
                    compute_type=Config.WHISPER_COMPUTE_TYPE,
                )
                self._loaded = True
                self._load_error = None
                print("[STT] Model Whisper siap menerima pertanyaan suara.", flush=True)
            except Exception as exc:  # noqa: BLE001
                self._load_error = str(exc)
                print(f"[STT ERROR] Gagal memuat model Whisper: {exc}", flush=True)
                raise

    # ------------------------------------------------------------------
    # Decoding WAV -> float32 mono 16 kHz
    # ------------------------------------------------------------------
    @staticmethod
    def _decode_wav(audio_bytes: bytes) -> np.ndarray:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wf:
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            sample_width = wf.getsampwidth()
            raw = wf.readframes(wf.getnframes())

        if sample_width == 1:
            data = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
        elif sample_width == 2:
            data = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
        elif sample_width == 4:
            data = np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
        else:
            raise ValueError(f"Lebar sample WAV tidak didukung: {sample_width} byte")

        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)

        if sample_rate != 16000 and data.size > 0:
            duration = data.size / float(sample_rate)
            target_len = max(1, int(duration * 16000))
            data = np.interp(
                np.linspace(0.0, data.size - 1, target_len, dtype=np.float32),
                np.arange(data.size, dtype=np.float32),
                data,
            ).astype(np.float32)

        return data

    # ------------------------------------------------------------------
    # Transcription
    # ------------------------------------------------------------------
    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        """Transkripsi byte audio menjadi teks Bahasa Indonesia."""
        if not audio_bytes:
            raise ValueError("File audio kosong.")

        self._ensure_model()
        assert self.model is not None

        audio_input = None
        temp_path: Optional[str] = None
        try:
            # Jalur utama: WAV dari ESP32 -> numpy (tanpa PyAV/FFmpeg).
            try:
                audio_input = self._decode_wav(audio_bytes)
            except Exception:
                # Fallback: format lain (webm/ogg/mp3) lewat file sementara.
                with tempfile.NamedTemporaryFile(
                    suffix=".audio", delete=False, dir=tempfile.gettempdir()
                ) as tmp:
                    tmp.write(audio_bytes)
                    temp_path = tmp.name
                audio_input = temp_path

            segments, _info = self.model.transcribe(
                audio_input,
                language=Config.WHISPER_LANGUAGE,
                beam_size=1,
                vad_filter=True,
                vad_parameters={"min_silence_duration_ms": 500},
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return text
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    def warmup(self) -> bool:
        """Muat model di background agar request suara pertama tidak menunggu unduhan."""
        try:
            self._ensure_model()
            return True
        except Exception:  # noqa: BLE001
            return False


# Singleton
stt_service = STTService()
