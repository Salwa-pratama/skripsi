"""Module AI Service - Text-to-Speech Bahasa Indonesia.

Gemini sudah dicabut dari sistem. Jawaban murni berasal dari model
Sentence-Transformer hasil fine-tuning (lihat core/retrieval_service.py).
Modul ini hanya menangani sintesis suara Edge-TTS dan konversi WAV untuk
ESP32-S3 (MAX98357A, 16 kHz, 16-bit, stereo).
"""

from __future__ import annotations

import asyncio
import hashlib
import os

import edge_tts

from config import Config


class AIService:
    def __init__(self) -> None:
        # Suara default: cowok Indonesia (Ardi).
        self.voice_gender = (Config.TTS_DEFAULT_VOICE or "cowok").lower()
        self.voices = {
            "cowok": "id-ID-ArdiNeural",
            "pria": "id-ID-ArdiNeural",
            "male": "id-ID-ArdiNeural",
            "cewek": "id-ID-GadisNeural",
            "wanita": "id-ID-GadisNeural",
            "female": "id-ID-GadisNeural",
        }

        # Direktori cache audio (MP3 + WAV hasil konversi)
        self.cache_dir = "/tmp/asisten_audio_cache"
        os.makedirs(self.cache_dir, exist_ok=True)

    # ------------------------------------------------------------------
    # Voice configuration
    # ------------------------------------------------------------------
    def set_voice(self, gender: str) -> bool:
        gender_clean = (gender or "").lower().strip()
        if gender_clean in self.voices:
            self.voice_gender = gender_clean
            return True
        return False

    def get_current_voice(self) -> str:
        return self.voices.get(self.voice_gender, "id-ID-ArdiNeural")

    # ------------------------------------------------------------------
    # Text-to-Speech
    # ------------------------------------------------------------------
    async def text_to_speech_async(self, text: str, voice_override: str | None = None) -> str:
        """Sintesis teks menjadi MP3, return path file."""
        voice = self.get_current_voice()
        if voice_override and voice_override.lower() in self.voices:
            voice = self.voices[voice_override.lower()]

        # Cache berdasarkan teks + suara agar pertanyaan berulang tidak
        # memanggil Edge-TTS lagi.
        hash_id = hashlib.md5(f"{text}_{voice}".encode("utf-8")).hexdigest()
        output_file = os.path.join(self.cache_dir, f"{hash_id}.mp3")

        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            return output_file

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        return output_file

    def text_to_speech(self, text: str, voice_override: str | None = None) -> str:
        """Wrapper sinkron untuk text_to_speech_async."""
        return asyncio.run(self.text_to_speech_async(text, voice_override))


# Singleton
ai_service = AIService()
