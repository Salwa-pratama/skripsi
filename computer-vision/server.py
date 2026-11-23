"""FastAPI Core Server - Asisten Belajar AI & Physical Companion.

Menyatukan:
1. Retrieval materi Python dengan model Sentence-Transformer fine-tuned.
2. Speech-to-Text pertanyaan suara ESP32-S3 (faster-whisper, Bahasa Indonesia).
3. Text-to-Speech Bahasa Indonesia (Edge-TTS, default suara cowok/Ardi).
4. Endpoint Ultra-Ringkas untuk Layar OLED ESP32-S3 (/api/esp/pomodoro).
5. Pomodoro State Machine & Kontrol Gamifikasi MDA.
6. Database MySQL & ORM SQLAlchemy 2.0.
7. Dokumentasi Interaktif Otomatis via Swagger UI (/docs).

Catatan: seluruh fitur kamera / computer-vision sudah dihapus.
"""

from __future__ import annotations

import os
import re
import time
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import Config
from core.ai_service import ai_service
from core.ast_validator import validate_and_run
from core.retrieval_service import retrieval_service
from core.stt_service import stt_service
from pomodoro.pomodoro_manager import PomodoroManager

# Database Modules
from db.session import get_db
from crud.crud_user import get_or_create_default_user
from crud.crud_gamification import get_or_create_profile, get_leaderboard
from crud.crud_pomodoro import record_pomodoro_session, record_chapter_progress

# =========================================================================
# INISIALISASI KOMPONEN UTAMA
# =========================================================================
pomodoro_manager = PomodoroManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Muat model fine-tuned sekali saat startup (STT dimuat lazy)."""
    try:
        retrieval_service.load()
    except Exception as exc:  # noqa: BLE001
        print(
            f"⚠️ [STARTUP] Model fine-tuned belum siap: {exc}\n"
            "   Endpoint AI akan mengembalikan 503 sampai artefak & dependency benar.",
            flush=True,
        )

    print(
        f"[STT] faster-whisper '{Config.WHISPER_MODEL_SIZE}' dimuat di background "
        "agar request suara pertama langsung siap.",
        flush=True,
    )

    # Warmup STT di background: unduhan model pertama (±500 MB untuk 'small')
    # tidak memblokir startup FastAPI.
    import threading

    threading.Thread(target=stt_service.warmup, daemon=True).start()
    yield


# Inisialisasi App FastAPI
app = FastAPI(
    title="Asisten Belajar AI & IoT Backend",
    version="2.0.0",
    description=(
        "Backend API Engine untuk Platform Pembelajaran Python & Robot Pendamping "
        "ESP32-S3. Menjawab pertanyaan suara dengan model Sentence-Transformer "
        "fine-tuned, lalu mengubah jawaban menjadi suara Bahasa Indonesia."
    ),
    lifespan=lifespan,
)

# CORS Middleware agar Frontend Next.js (port 3000) bisa mengakses API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================================
# MODEL PYDANTIC (VALIDASI REQUEST)
# =========================================================================
class CodeValidationRequest(BaseModel):
    code: str = Field(..., description="Kode sumber Python yang diketikkan pengguna")
    chapter_slug: Optional[str] = Field(default="percabangan", description="Slug bab materi")
    required_nodes: List[str] = Field(default=[], description="Daftar node AST yang disyaratkan")
    expected_output_snippet: str = Field(default="", description="Snippet teks output yang diharapkan")
    trigger_emotion_on_pass: bool = Field(default=True, description="Picu ekspresi senang di robot jika lolos")


class PomodoroConfigureRequest(BaseModel):
    task_name: Optional[str] = Field(default=None, description="Nama misi/tugas")
    work_min: Optional[int] = Field(default=25, description="Durasi fokus dalam menit")
    short_break_min: Optional[int] = Field(default=5, description="Durasi istirahat pendek")
    long_break_min: Optional[int] = Field(default=15, description="Durasi istirahat panjang")
    target_cycles: Optional[int] = Field(default=4, description="Target jumlah siklus")


class AIAskRequest(BaseModel):
    prompt: str = Field(..., description="Pertanyaan teks untuk asisten belajar")
    voice: Optional[str] = Field(None, description="Pilihan suara: 'cowok' (Ardi) atau 'cewek' (Gadis)")


class VoiceConfigRequest(BaseModel):
    voice: str = Field("cowok", description="Pilihan suara: 'cowok' atau 'cewek'")


# =========================================================================
# HELPER ASISTEN BELAJAR
# =========================================================================
def _build_ai_payload(question: str, answer_data: dict, voice: Optional[str]) -> dict:
    """Sintesis TTS + bentuk payload respons standar untuk ESP32/Frontend."""
    answer = answer_data.get("answer", "")
    voice_pref = voice or ai_service.voice_gender

    audio_filename = ""
    wav_filename = ""
    try:
        audio_path = ai_service.text_to_speech(answer, voice_pref)
        if audio_path:
            audio_filename = os.path.basename(audio_path)
            wav_filename = audio_filename.replace(".mp3", ".wav")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ [TTS Warning] Gagal sintesis suara: {exc}", flush=True)

    return {
        "status": "success",
        "question": question,
        "answer": answer,
        "display_text": answer_data.get("display_text", answer),
        "matched": answer_data.get("matched", False),
        "confidence": answer_data.get("confidence", 0.0),
        "chapter": answer_data.get("chapter"),
        "chapter_slug": answer_data.get("chapter_slug"),
        "episode": answer_data.get("episode"),
        "episode_id": answer_data.get("episode_id"),
        "concept": answer_data.get("concept"),
        "passage": answer_data.get("passage"),
        "alternatives": answer_data.get("alternatives", []),
        "emotion": answer_data.get("emotion", "speaking"),
        "voice": ai_service.get_current_voice(),
        "audio_url": f"/api/ai/audio/{audio_filename}" if audio_filename else "",
        "audio_wav_url": f"/api/ai/audio/{wav_filename}" if wav_filename else "",
    }


def _answer_text(question: str, voice: Optional[str]) -> dict:
    """Retrieval + TTS untuk pertanyaan berbentuk teks."""
    try:
        answer_data = retrieval_service.answer(question)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Model retrieval belum siap: {exc}",
        ) from exc
    return _build_ai_payload(question, answer_data, voice)


# Pola regex pengenalan wake word "Hi ESP" dan variasi fonetik Indonesianya:
# Cocok dengan: "hi esp", "hai esp", "halo esp", "hei esp", "hey esp", "he esp", "esp"
# Termasuk variasi fonetik STT Whisper: "hai sp", "hi sp", "hai sb", "hai usb"
_WAKE_WORD_RE = re.compile(
    r"^\s*(?:h[ai]i?|halo|hei|hey|he)?\s*(?:esp|sp|usb|sb)\b[\s,!?:.-]*",
    re.IGNORECASE
)


def _process_voice_wake_word(transcript: str) -> tuple[bool, str]:
    """
    Mengecek apakah transkrip diawali dengan wake word "Hi ESP" (atau variasinya).
    Mengembalikan (is_wake_word, query_setelah_wake_word).
    """
    clean_t = (transcript or "").strip()
    match = _WAKE_WORD_RE.match(clean_t)
    if not match:
        # Cek jika kata "esp" muncul di bagian awal kalimat (<12 karakter pertama)
        esp_match = re.search(r"\b(esp|sp)\b", clean_t, re.IGNORECASE)
        if esp_match and esp_match.start() < 12:
            remainder = clean_t[esp_match.end():].strip(" ,;:-?!")
            return True, remainder
        return False, clean_t

    remainder = clean_t[match.end():].strip(" ,;:-?!")
    return True, remainder


# =========================================================================
# ROUTE ENDPOINTS
# =========================================================================
@app.get("/", include_in_schema=False)
def root():
    """Redirect root ke Swagger UI interaktif."""
    return RedirectResponse(url="/docs")


@app.get("/api/health", tags=["Health"])
def health_check():
    """Pemeriksaan status server + kesiapan model."""
    return {
        "status": "ok",
        "timestamp": time.time(),
        "retrieval_ready": retrieval_service.is_loaded,
        "retrieval_error": retrieval_service.load_error,
        "stt_ready": stt_service.is_loaded,
        "stt_error": stt_service.load_error,
        "tts_voice": ai_service.get_current_voice(),
    }


@app.get("/api/esp/pomodoro", tags=["ESP32 IoT"])
def get_esp_pomodoro(ip: Optional[str] = None):
    """
    Endpoint Ultra-Ringkas Khusus Layar OLED ESP32-S3 (SSD1306).
    Payload kecil, dipanggil setiap 1 detik oleh ESP32 secara non-blocking.

    Parameter `ip` masih diterima untuk kompatibilitas firmware lama, tetapi
    tidak lagi dipakai karena fitur kamera/streaming sudah dihapus.
    """
    del ip  # tidak dipakai lagi
    pomo = pomodoro_manager.get_state()

    raw_mode = pomo.get("mode", "work")
    mode_str = "WORK"
    if raw_mode == "short_break":
        mode_str = "BREAK"
    elif raw_mode == "long_break":
        mode_str = "REST"

    # Deteksi distraksi berbasis kamera sudah dihapus -> alert selalu kosong.
    alert_str = ""

    # Truncate judul task agar pas 14 char
    task_title = pomo.get("task_name", "Belajar Fokus")
    if len(task_title) > 14:
        task_title = task_title[:12] + ".."

    return {
        "mode": mode_str,
        "status": pomo.get("status", "stopped").upper(),
        "time_str": pomo.get("formatted_time", "25:00"),
        "time_left": int(pomo.get("time_left", 0)),
        "cycle_str": f"{pomo.get('current_cycle', 1)}/{pomo.get('target_cycles', 4)}",
        "task": task_title,
        "alert": alert_str,
        "emotion": pomo.get("emotion", "NORMAL"),
        "focus": int(pomo.get("focus_score", 100)),
    }


@app.get("/api/status", tags=["Status & Monitoring"])
def get_system_status():
    """Status lengkap sistem untuk konsumsi Frontend Next.js."""
    pomo_status = pomodoro_manager.get_state()
    return {
        "pomodoro": pomo_status,
        "ai": {
            "detected_emotion": pomo_status.get("emotion", "NORMAL"),
            "retrieval_ready": retrieval_service.is_loaded,
            "retrieval_error": retrieval_service.load_error,
            "stt_ready": stt_service.is_loaded,
            "voice_gender": ai_service.voice_gender,
            "voice_model": ai_service.get_current_voice(),
            "min_confidence": Config.RETRIEVAL_MIN_SCORE,
        },
    }


# =========================================================================
# ENDPOINTS DATABASE & GAMIFIKASI MDA (MySQL)
# =========================================================================
@app.get("/api/user/profile", tags=["Gamifikasi MDA"])
def get_user_profile(db: Session = Depends(get_db)):
    """Mengambil profil mahasiswa dan status gamifikasi MDA."""
    user = get_or_create_default_user(db)
    profile = get_or_create_profile(db, user.id)
    return {
        "id": user.id,
        "nim": user.nim,
        "name": user.name,
        "avatar": user.avatar or "👨‍💻",
        "gamification": {
            "focus_xp": profile.focus_xp,
            "python_coins": profile.python_coins,
            "level": profile.current_level,
            "level_title": profile.level_title,
            "daily_streak": profile.daily_streak,
            "badges_unlocked": profile.badges_unlocked,
        },
    }


@app.get("/api/leaderboard", tags=["Gamifikasi MDA"])
def get_leaderboard_endpoint(db: Session = Depends(get_db)):
    """Mengambil daftar papan peringkat kompetitif mahasiswa TI UNP Kediri."""
    return {
        "leaderboard": get_leaderboard(db, limit=10),
        "total_players": 5,
    }


@app.post("/api/pomodoro/{action}", tags=["Pomodoro & Gamifikasi"])
def pomodoro_action(
    action: str,
    config: Optional[PomodoroConfigureRequest] = None,
    db: Session = Depends(get_db),
):
    """
    Mengontrol state machine Pomodoro dan menyimpan ke Database saat sesi selesai:
    - start: Memulai sesi belajar fokus (25m)
    - pause: Menjeda sesi
    - reset: Mengulang timer ke awal
    - finish: Menyimpan sesi ke tabel pomodoro_sessions dan memberi reward XP & Koin
    - quest_passed: Memvalidasi keberhasilan quest koding & memicu ekspresi HAPPY
    - configure: Mengatur durasi & target sesi
    """
    action_clean = action.lower().strip()

    if action_clean == "start":
        pomodoro_manager.start()
    elif action_clean == "pause":
        pomodoro_manager.pause()
    elif action_clean == "reset":
        pomodoro_manager.reset()
    elif action_clean == "skip":
        pomodoro_manager.skip()
    elif action_clean == "quest_passed":
        pomodoro_manager.trigger_quest_passed(duration_sec=7.0)
    elif action_clean == "finish":
        user = get_or_create_default_user(db)
        state = pomodoro_manager.get_state()
        saved_session = record_pomodoro_session(db, user.id, {
            "task_name": state.get("task_name"),
            "mode": state.get("mode"),
            "target_duration_sec": state.get("total_duration", 1500),
            "actual_focus_sec": state.get("total_duration", 1500) - state.get("time_left", 0),
            "cycles_completed": state.get("cycles_completed", 1),
            "phone_distractions": 0,
            "absence_distractions": 0,
            "focus_score": state.get("focus_score", 100),
            "status": "completed",
        })
        pomodoro_manager.reset()
        profile = get_or_create_profile(db, user.id)
        return {
            "status": "success",
            "message": "Sesi Pomodoro berhasil disimpan ke database MySQL!",
            "session_id": saved_session.id,
            "xp_earned": saved_session.xp_earned,
            "coins_earned": saved_session.coins_earned,
            "updated_profile": {
                "focus_xp": profile.focus_xp,
                "python_coins": profile.python_coins,
                "current_level": profile.current_level,
                "level_title": profile.level_title,
                "daily_streak": profile.daily_streak,
            },
        }
    elif action_clean == "configure":
        if config:
            pomodoro_manager.configure_session(
                task_name=config.task_name,
                work_min=config.work_min,
                short_break_min=config.short_break_min,
                long_break_min=config.long_break_min,
                target_cycles=config.target_cycles,
            )
    else:
        raise HTTPException(status_code=400, detail=f"Aksi Pomodoro '{action}' tidak dikenal")

    return {"status": "success", "action": action_clean, "state": pomodoro_manager.get_state()}


@app.post("/api/code/validate", tags=["AST Code Validation"])
def validate_code(req: CodeValidationRequest, db: Session = Depends(get_db)):
    """
    Memvalidasi kode Python mahasiswa:
    1. Memeriksa sintaks dengan AST.
    2. Menghitung pemenuhan required nodes.
    3. Mengeksekusi kode secara aman dengan batas timeout.
    4. Jika lolos: simpan progres, beri reward, dan picu emosi HAPPY.
    """
    result = validate_and_run(
        code=req.code,
        required_nodes=req.required_nodes,
        expected_output_snippet=req.expected_output_snippet,
    )

    passed = result.get("passed", False)

    user = get_or_create_default_user(db)
    chapter_slug = req.chapter_slug or "percabangan"
    record_chapter_progress(
        db=db,
        user_id=user.id,
        chapter_slug=chapter_slug,
        submitted_code=req.code,
        ast_valid=result.get("ast", {}).get("syntaxValid", False),
        is_completed=passed,
    )

    if passed and req.trigger_emotion_on_pass:
        pomodoro_manager.trigger_quest_passed(duration_sec=7.0)

    profile = get_or_create_profile(db, user.id)
    result["gamification"] = {
        "focus_xp": profile.focus_xp,
        "python_coins": profile.python_coins,
        "level": profile.current_level,
        "level_title": profile.level_title,
        "daily_streak": profile.daily_streak,
        "badges": profile.badges_unlocked,
    }

    return result


# =========================================================================
# ENDPOINTS ASISTEN BELAJAR (FINE-TUNED SBERT + STT + EDGE-TTS)
# =========================================================================
@app.post("/api/ai/ask", tags=["Asisten Belajar AI"])
def ask_ai_assistant(req: AIAskRequest):
    """
    Pertanyaan teks -> retrieval fine-tuned SBERT -> jawaban + TTS cowok Indonesia.
    """
    return _answer_text(req.prompt, req.voice)


@app.post("/api/ai/voice", tags=["Asisten Belajar AI"])
def ask_ai_voice(
    audio: UploadFile = File(..., description="Rekaman WAV pertanyaan user dari ESP32-S3"),
    voice: Optional[str] = Form(None, description="Pilihan suara: 'cowok' atau 'cewek'"),
):
    """
    Pertanyaan suara -> faster-whisper (STT) -> retrieval fine-tuned SBERT ->
    jawaban teks + file WAV 16 kHz untuk speaker ESP32-S3.

    Endpoint dibuat sinkron agar Edge-TTS dapat memakai event loop sendiri
    (dijalankan FastAPI di threadpool, bukan di event loop utama).
    """
    raw_audio = audio.file.read()
    if not raw_audio:
        raise HTTPException(status_code=400, detail="File audio kosong.")

    # Batas aman: 8 detik WAV 16 kHz mono 16-bit ~= 256 KB.
    if len(raw_audio) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Ukuran audio terlalu besar (maks 5 MB).")

    try:
        transcript = stt_service.transcribe_bytes(raw_audio)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=503,
            detail=f"Speech-to-Text belum siap: {exc}",
        ) from exc

    transcript = (transcript or "").strip()
    if not transcript:
        question = "(suara tidak terdeteksi)"
        answer_data = {
            "answer": "Maaf, aku belum mendengar pertanyaanmu dengan jelas. "
                      "Coba ulangi lebih dekat ke mikrofon ya.",
            "display_text": "Suara belum jelas. Coba ulangi lebih dekat ke mic.",
            "matched": False,
            "confidence": 0.0,
            "emotion": "confused",
        }
        return _build_ai_payload(question, answer_data, voice)

    # Deteksi Voice Trigger / Wake Word "Hi ESP"
    wake_detected, question_after_wake = _process_voice_wake_word(transcript)

    if wake_detected:
        if not question_after_wake:
            # Pengguna hanya memicu wake word "Hi ESP"
            wake_answer = {
                "answer": "Halo! Aku ESP, asisten belajarmu. Aku siap mendengarkan, ada yang ingin kamu tanyakan?",
                "display_text": "Halo! Aku ESP, siap membantu. Silakan bertanya.",
                "matched": True,
                "confidence": 1.0,
                "emotion": "happy",
            }
            payload = _build_ai_payload(transcript, wake_answer, voice)
            payload["transcript"] = transcript
            payload["wake_word_detected"] = True
            payload["is_wake_word_only"] = True
            return payload

        # Pengguna mengucapkan "Hi ESP [pertanyaan]" dalam satu tarikan nafas
        payload = _answer_text(question_after_wake, voice)
        payload["transcript"] = transcript
        payload["wake_word_detected"] = True
        payload["is_wake_word_only"] = False
        return payload

    # Fallback jika pertanyaan diajukan langsung tanpa wake word
    payload = _answer_text(transcript, voice)
    payload["transcript"] = transcript
    payload["wake_word_detected"] = False
    payload["is_wake_word_only"] = False
    return payload


@app.get("/api/ai/audio/{filename}", tags=["Asisten Belajar AI"])
def get_ai_audio(filename: str):
    """Streaming file audio (MP3 atau 16 kHz WAV untuk ESP32 I2S)."""
    safe_name = os.path.basename(filename)
    file_path = os.path.join(ai_service.cache_dir, safe_name)

    if safe_name.endswith(".wav"):
        if not os.path.exists(file_path):
            mp3_path = file_path.replace(".wav", ".mp3")
            if os.path.exists(mp3_path):
                try:
                    from pydub import AudioSegment

                    sound = AudioSegment.from_mp3(mp3_path)
                    # 16 kHz, 16-bit, 2 channel (stereo untuk I2S MAX98357A)
                    sound = sound.set_frame_rate(16000).set_channels(2).set_sample_width(2)
                    sound.export(file_path, format="wav")
                except Exception as exc:  # noqa: BLE001
                    print(f"Error converting MP3 to WAV: {exc}", flush=True)
                    raise HTTPException(
                        status_code=500, detail="Gagal konversi audio ke WAV"
                    ) from exc
            else:
                raise HTTPException(status_code=404, detail="File audio MP3 sumber tidak ditemukan")
        return FileResponse(file_path, media_type="audio/wav")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File audio tidak ditemukan")
    return FileResponse(file_path, media_type="audio/mpeg")


@app.post("/api/ai/voice/config", tags=["Asisten Belajar AI"])
def configure_voice(req: VoiceConfigRequest):
    """Mengatur jenis suara default: 'cowok' (Ardi) atau 'cewek' (Gadis)."""
    if ai_service.set_voice(req.voice):
        return {
            "status": "success",
            "message": f"Suara berhasil diatur ke '{req.voice}' ({ai_service.get_current_voice()})",
        }
    raise HTTPException(status_code=400, detail="Pilihan suara hanya 'cowok' atau 'cewek'")


@app.get("/api/ai/voice/config", tags=["Asisten Belajar AI"])
def get_voice_setting():
    """Mendapatkan pengaturan suara aktif saat ini."""
    return {
        "voice_gender": ai_service.voice_gender,
        "voice_model": ai_service.get_current_voice(),
    }


@app.get("/api/esp/companion", tags=["ESP32-S3 Physical Companion"])
def get_esp_companion_state():
    """
    Endpoint terpadu untuk ESP32-S3 Physical Robot Companion:
    Mengembalikan emosi OLED (happy, neutral, thinking, speaking), status timer
    Pomodoro, dan pengaturan suara aktif. Deteksi distraksi kamera dihapus.
    """
    pomo = pomodoro_manager.get_state()
    emotion = pomo.get("emotion", "NORMAL").lower()

    mapped_emotion = "neutral"
    if emotion in ["happy", "celebrating"]:
        mapped_emotion = "happy"
    elif emotion in ["angry", "distracted", "warning"]:
        mapped_emotion = "angry"
    elif emotion in ["thinking", "evaluating"]:
        mapped_emotion = "thinking"
    elif emotion in ["speaking", "talking"]:
        mapped_emotion = "speaking"

    return {
        "emotion": mapped_emotion,
        "mode": pomo.get("mode", "WORK"),
        "time_left": pomo.get("time_left", 0),
        "focus_score": pomo.get("focus_score", 100),
        "alert": "",
        "voice_gender": ai_service.voice_gender,
        "retrieval_ready": retrieval_service.is_loaded,
    }


if __name__ == "__main__":
    import uvicorn

    port = Config.PORT if hasattr(Config, "PORT") else 5000
    host = Config.HOST if hasattr(Config, "HOST") else "0.0.0.0"
    print("\n=======================================================", flush=True)
    print("🌟 ASISTEN BELAJAR AI - FASTAPI & FINE-TUNED SBERT", flush=True)
    print(f"📡 Swagger API Documentation : http://localhost:{port}/docs", flush=True)
    print(f"🧠 Retrieval Model            : {Config.FINETUNED_MODEL_DIR}", flush=True)
    print(f"🎙️  Voice Endpoint            : POST http://localhost:{port}/api/ai/voice", flush=True)
    print(f"🤖 ESP32-S3 OLED Endpoint     : http://localhost:{port}/api/esp/pomodoro", flush=True)
    print("=======================================================\n", flush=True)
    uvicorn.run("server:app", host=host, port=port, reload=False)
