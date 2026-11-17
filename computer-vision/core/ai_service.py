"""
Module AI Service - Asisten Belajar
Integrasi Gemini API + Multimodal Vision + Edge-TTS (Suara Cowok/Cewek Bahasa Indonesia)
"""

import os
import io
import time
import base64
import asyncio
import hashlib
import requests
import edge_tts
from dotenv import load_dotenv

from config import Config

# Pastikan environment termuat dari folder computer-vision
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path, override=True)

class AIService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY")
        # Model default yang terbukti aktif dan sangat cepat
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"
        
        # Pengaturan Suara Default (bisa 'cowok' atau 'cewek')
        self.voice_gender = os.getenv("VOICE_GENDER", "cewek").lower()
        self.voices = {
            "cowok": "id-ID-ArdiNeural",
            "pria": "id-ID-ArdiNeural",
            "male": "id-ID-ArdiNeural",
            "cewek": "id-ID-GadisNeural",
            "wanita": "id-ID-GadisNeural",
            "female": "id-ID-GadisNeural",
        }

        # Direktori cache audio
        self.cache_dir = "/tmp/asisten_audio_cache"
        os.makedirs(self.cache_dir, exist_ok=True)

        # System Prompt Asisten Belajar
        self.system_prompt = (
            "Kamu adalah Asisten Belajar AI cerdas, ramah, dan suportif. "
            "Nama panggilannmu adalah Robot Asisten Belajar. "
            "Gunakan selalu bahasa Indonesia yang alami, santun, jelas, dan memotivasi. "
            "Bantu siswa/mahasiswa memahami materi pelajaran, pemrograman Python, matematika, "
            "dan sains. Jawablah secara ringkas, to the point, dan mudah dipahami ketika dibacakan suara."
        )

    def set_voice(self, gender: str):
        gender_clean = gender.lower().strip()
        if gender_clean in self.voices:
            self.voice_gender = gender_clean
            return True
        return False

    def get_current_voice(self) -> str:
        return self.voices.get(self.voice_gender, "id-ID-GadisNeural")

    def ask_gemini(self, prompt: str, image_bytes: bytes = None) -> dict:
        """
        Kirim pertanyaan ke Gemini API (dengan opsi gambar kamera OV5640).
        Mengembalikan dict: {'text': ..., 'emotion': ...}
        """
        if not self.api_key:
            return {
                "text": "Maaf, kunci Gemini API belum dikonfigurasi di file .env server.",
                "emotion": "sad"
            }

        url = f"{self.base_url}/{self.model_name}:generateContent?key={self.api_key}"

        parts = []
        # Tambahkan instruksi sistem
        parts.append({"text": f"[Instruksi Sistem: {self.system_prompt}]\n\nPertanyaan Pengguna: {prompt}"})

        # Jika ada gambar dari kamera OV5640, tambahkan ke parts sebagai inline base64
        if image_bytes:
            encoded_img = base64.b64encode(image_bytes).decode("utf-8")
            parts.append({
                "inline_data": {
                    "mime_type": "image/jpeg",
                    "data": encoded_img
                }
            })

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 800,
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                
                # Deteksi emosi sederhana untuk mata robot OLED
                emotion = "speaking"
                text_lower = text.lower()
                if any(w in text_lower for w in ["hebat", "selamat", "bagus", "senang", "keren"]):
                    emotion = "happy"
                elif any(w in text_lower for w in ["hati-hati", "salah", "awas", "distraksi"]):
                    emotion = "angry"
                
                return {"text": text, "emotion": emotion}
            else:
                err_msg = f"Error {resp.status_code}: {resp.text}"
                print("Gemini API Error:", err_msg)
                return {
                    "text": "Maaf, sedang ada kendala jaringan saat menghubungi layanan AI.",
                    "emotion": "confused"
                }
        except Exception as e:
            print("Gemini Request Exception:", e)
            return {
                "text": "Terjadi kesalahan saat memproses jawaban AI.",
                "emotion": "sad"
            }

    async def text_to_speech_async(self, text: str, voice_override: str = None) -> str:
        """
        Sintesis suara Bahasa Indonesia menggunakan Microsoft Edge-TTS.
        Menyimpan file audio ke cache dan mengembalikan path file mp3.
        """
        voice = self.get_current_voice()
        if voice_override and voice_override.lower() in self.voices:
            voice = self.voices[voice_override.lower()]

        # Generate unique hash filename
        hash_id = hashlib.md5(f"{text}_{voice}".encode("utf-8")).hexdigest()
        output_file = os.path.join(self.cache_dir, f"{hash_id}.mp3")

        if os.path.exists(output_file):
            return output_file

        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        return output_file

    def text_to_speech(self, text: str, voice_override: str = None) -> str:
        """Wrapper sinkron untuk text_to_speech_async."""
        return asyncio.run(self.text_to_speech_async(text, voice_override))

# Singleton instance
ai_service = AIService()
