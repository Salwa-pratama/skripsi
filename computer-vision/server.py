"""FastAPI Core Server - Asisten Belajar AI & Physical Companion.

Menyatukan:
1. Endpoint Ultra-Ringkas untuk Layar OLED ESP32-S3 (/api/esp/pomodoro).
2. Live Streaming MJPEG dengan Vision Overlays (/video_feed).
3. Evaluasi Pohon Sintaksis Abstrak AST (/api/code/validate).
4. Pomodoro State Machine & Kontrol Gamifikasi MDA (/api/pomodoro/{action}).
5. Database MySQL & ORM SQLAlchemy 2.0 (Leaderboard, User Profile, Focus XP, Streak).
6. Dokumentasi Interaktif Otomatis via Swagger UI (/docs).
"""

from __future__ import annotations

import time
import threading
from contextlib import asynccontextmanager
from typing import List, Optional, Dict, Any

import cv2
from fastapi import FastAPI, HTTPException, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse, FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from config import Config
from core.camera_streamer import CameraStreamer
from core.distraction_detector import StudyDistractionDetector
from core.ast_validator import validate_and_run
from core.ai_service import ai_service
from pomodoro.pomodoro_manager import PomodoroManager

# Database Modules
from db.session import get_db
from crud.crud_user import get_or_create_default_user
from crud.crud_gamification import get_or_create_profile, get_leaderboard
from crud.crud_pomodoro import record_pomodoro_session, record_chapter_progress

# =========================================================================
# INISIALISASI KOMPONEN UTAMA
# =========================================================================
camera_streamer = CameraStreamer(source=Config.DEFAULT_SOURCE)
distraction_detector = StudyDistractionDetector()
pomodoro_manager = PomodoroManager()

# Background Vision Thread Controller
vision_running = True
vision_thread: Optional[threading.Thread] = None


def vision_pipeline_loop():
    """Loop background untuk inferensi Computer Vision (HP & Keberadaan Pengguna)."""
    global vision_running
    last_loop_time = time.time()

    print("🚀 [Vision Pipeline] Worker aktif memantau tangkapan kamera...", flush=True)
    while vision_running:
        start_time = time.time()
        dt = max(0.01, min(0.2, start_time - last_loop_time))
        last_loop_time = start_time

        frame = camera_streamer.get_enhanced_frame()
        if frame is None:
            time.sleep(0.01)
            continue

        if distraction_detector and distraction_detector.enabled:
            # Jalankan deteksi objek HP & Kehadiran Pengguna
            processed_frame, distraction_telem = distraction_detector.process_frame(
                frame, has_hands=False, draw=True
            )

            # Update status Pomodoro Manager
            pomodoro_manager.update_distraction_states(
                is_absent=distraction_telem.get("is_absent", False),
                is_phone=distraction_telem.get("is_phone", False),
                is_head_down=False,  # Head-down dinonaktifkan sesuai catatan engineering
                dt=dt,
            )

            # Simpan processed frame untuk video_feed
            camera_streamer.update_processed_frame(processed_frame)
        else:
            camera_streamer.update_processed_frame(frame)

        # Cap loop ~25-30 FPS
        elapsed = time.time() - start_time
        sleep_time = max(0.005, 0.033 - elapsed)
        time.sleep(sleep_time)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager FastAPI: menjalankan worker saat startup dan mematikan saat shutdown."""
    global vision_running, vision_thread
    vision_running = True
    vision_thread = threading.Thread(target=vision_pipeline_loop, daemon=True)
    vision_thread.start()
    yield
    vision_running = False
    if vision_thread and vision_thread.is_alive():
        vision_thread.join(timeout=1.0)


# Inisialisasi App FastAPI
app = FastAPI(
    title="Asisten Belajar AI & IoT Backend",
    version="1.0.0",
    description="Backend API Engine untuk Platform Pembelajaran Python & Robot Pendamping ESP32-S3",
    lifespan=lifespan,
)

# CORS Middleware agar Frontend Next.js (port 3000) bisa mengakses API tanpa hambatan
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


class CameraSourceRequest(BaseModel):
    source: str = Field(..., description="URL atau index stream kamera (misal http://192.168.1.12:81/stream)")


# =========================================================================
# ROUTE ENDPOINTS
# =========================================================================
@app.get("/", include_in_schema=False)
def root():
    """Redirect root ke Swagger UI interaktif."""
    return RedirectResponse(url="/docs")


@app.get("/api/health", tags=["Health"])
def health_check():
    """Pemeriksaan status server."""
    return {"status": "ok", "timestamp": time.time()}


@app.get("/api/esp/pomodoro", tags=["ESP32 IoT"])
def get_esp_pomodoro():
    """
    Endpoint Ultra-Ringkas Khusus Layar OLED ESP32-S3 (SSD1306).
    Payload < 150 bytes, dipanggil setiap 1 detik oleh ESP32 non-blocking.
    Menghasilkan nilai ekspresi robot (emotion) untuk pilar Aesthetics MDA.
    """
    pomo = pomodoro_manager.get_state()

    raw_mode = pomo.get("mode", "work")
    mode_str = "WORK"
    if raw_mode == "short_break":
        mode_str = "BREAK"
    elif raw_mode == "long_break":
        mode_str = "REST"

    # Evaluasi teks alert singkat untuk OLED
    alert_str = ""
    live_flags = pomo.get("live_flags", {})
    abs_track = pomo.get("absence_tracking", {})

    if live_flags.get("is_phone"):
        alert_str = "HP!"
    elif not abs_track.get("is_user_present", True) or abs_track.get("tolerance_exceeded"):
        alert_str = "ABSEN!"

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
    cam_status = camera_streamer.get_status()
    pomo_status = pomodoro_manager.get_state()
    return {
        "camera": cam_status,
        "pomodoro": pomo_status,
        "ai": {
            "distraction_enabled": distraction_detector.enabled if distraction_detector else False,
            "detected_emotion": pomo_status.get("emotion", "NORMAL"),
        },
    }


# =========================================================================
# ENDPOINTS DATABASE & GAMIFIKASI MDA (MySQL)
# =========================================================================
@app.get("/api/user/profile", tags=["Gamifikasi MDA"])
def get_user_profile(db: Session = Depends(get_db)):
    """Mengambil profil mahasiswa dan status gamifikasi MDA (Focus XP, Koin, Level, Streak, Badges)."""
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
        }
    }


@app.get("/api/leaderboard", tags=["Gamifikasi MDA"])
def get_leaderboard_endpoint(db: Session = Depends(get_db)):
    """Mengambil daftar papan peringkat kompetitif mahasiswa TI UNP Kediri."""
    return {
        "leaderboard": get_leaderboard(db, limit=10),
        "total_players": 5
    }


@app.post("/api/pomodoro/{action}", tags=["Pomodoro & Gamifikasi"])
def pomodoro_action(
    action: str,
    config: Optional[PomodoroConfigureRequest] = None,
    db: Session = Depends(get_db)
):
    """
    Mengontrol state machine Pomodoro dan menyimpan ke Database saat sesi selesai:
    - start: Memulai sesi belajar fokus (25m)
    - pause: Menjeda sesi
    - reset: Mengulang timer ke awal
    - finish: Menyimpan sesi ke tabel pomodoro_sessions di MySQL dan memberi reward XP & Koin
    - quest_passed: Memvalidasi keberhasilan quest koding & memicu ekspresi HAPPY di robot OLED
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
        # Simpan sesi Pomodoro ke Database MySQL
        user = get_or_create_default_user(db)
        state = pomodoro_manager.get_state()
        saved_session = record_pomodoro_session(db, user.id, {
            "task_name": state.get("task_name"),
            "mode": state.get("mode"),
            "target_duration_sec": state.get("total_duration", 1500),
            "actual_focus_sec": state.get("total_duration", 1500) - state.get("time_left", 0),
            "cycles_completed": state.get("cycles_completed", 1),
            "phone_distractions": state.get("distractions", {}).get("counts", {}).get("phone", 0),
            "absence_distractions": state.get("distractions", {}).get("counts", {}).get("absent", 0),
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
            }
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
    2. Menghitung pemenuhan required nodes (misal If, For, FunctionDef).
    3. Mengeksekusi kode secara aman dengan batas timeout.
    4. Jika lolos:
       - Menyimpan riwayat ke tabel chapter_progress di MySQL.
       - Memberikan reward Focus XP & Python Coins di database.
       - Otomatis memicu emosi bahagia (HAPPY) pada robot pendamping ESP32.
    """
    result = validate_and_run(
        code=req.code,
        required_nodes=req.required_nodes,
        expected_output_snippet=req.expected_output_snippet,
    )

    passed = result.get("passed", False)

    # Catat submission ke database MySQL
    user = get_or_create_default_user(db)
    chapter_slug = req.chapter_slug or "percabangan"
    record_chapter_progress(
        db=db,
        user_id=user.id,
        chapter_slug=chapter_slug,
        submitted_code=req.code,
        ast_valid=result.get("ast", {}).get("syntaxValid", False),
        is_completed=passed
    )

    if passed and req.trigger_emotion_on_pass:
        pomodoro_manager.trigger_quest_passed(duration_sec=7.0)

    # Muat profil terbaru setelah reward diberikan
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


@app.get("/video_feed", tags=["Camera Stream"])
def video_feed():
    """
    High-Performance HTTP MJPEG Video Stream (Hardware-Accelerated di Browser).
    Dapat disematkan langsung di Frontend Next.js via tag <img src="http://localhost:5000/video_feed" />.
    """
    def gen():
        last_id = -1
        while True:
            fid, jpeg = camera_streamer.get_latest_frame_with_id()
            if fid != last_id and jpeg is not None:
                last_id = fid
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + jpeg + b"\r\n"
                )
            else:
                time.sleep(0.01)

    return StreamingResponse(gen(), media_type="multipart/x-mixed-replace; boundary=frame")


@app.post("/api/camera/source", tags=["Camera Settings"])
def change_camera_source(req: CameraSourceRequest):
    """Mengalihkan sumber kamera (misal RTSP, URL ESP32, atau indeks webcam 0)."""
    camera_streamer.set_source(req.source)
    return {
        "status": "success",
        "current_source": str(camera_streamer.source),
    }


# =========================================================================
# ENDPOINTS ASISTEN BELAJAR AI (GEMINI & EDGE-TTS INDONESIA)
# =========================================================================
class AIAskRequest(BaseModel):
    prompt: str = Field(..., description="Pertanyaan untuk asisten belajar")
    voice: Optional[str] = Field(None, description="Pilihan suara: 'cowok' (Ardi) atau 'cewek' (Gadis)")
    use_camera: Optional[bool] = Field(False, description="Apakah menyertakan tangkapan kamera OV5640 untuk dianalisa Gemini")


class VoiceConfigRequest(BaseModel):
    voice: str = Field("cewek", description="Pilihan suara: 'cowok' atau 'cewek'")


@app.post("/api/ai/ask", tags=["Asisten Belajar AI"])
def ask_ai_assistant(req: AIAskRequest):
    """
    Bertanya ke Gemini AI dalam Bahasa Indonesia + Sintesis Suara (TTS Cowok/Cewek).
    Mendukung Multimodal Vision (analisa frame kamera OV5640).
    """
    image_bytes = None
    if req.use_camera:
        frame = camera_streamer.get_enhanced_frame()
        if frame is not None:
            success, encoded_image = cv2.imencode(".jpg", frame)
            if success:
                image_bytes = encoded_image.tobytes()

    # Tanya ke Gemini
    ai_resp = ai_service.ask_gemini(prompt=req.prompt, image_bytes=image_bytes)
    text = ai_resp.get("text", "")
    emotion = ai_resp.get("emotion", "speaking")

    # Sintesis suara Bahasa Indonesia
    voice_pref = req.voice or ai_service.voice_gender
    audio_path = ai_service.text_to_speech(text, voice_pref)
    audio_filename = os.path.basename(audio_path)
    wav_filename = audio_filename.replace(".mp3", ".wav")

    return {
        "status": "success",
        "question": req.prompt,
        "answer": text,
        "emotion": emotion,
        "voice": ai_service.get_current_voice(),
        "audio_url": f"/api/ai/audio/{audio_filename}",
        "audio_wav_url": f"/api/ai/audio/{wav_filename}",
    }


@app.get("/api/ai/audio/{filename}", tags=["Asisten Belajar AI"])
def get_ai_audio(filename: str):
    """Streaming file audio (MP3 atau 16kHz WAV untuk ESP32 I2S) hasil sintesis suara Bahasa Indonesia."""
    file_path = os.path.join(ai_service.cache_dir, filename)
    
    # Jika ESP32 meminta format WAV (16kHz, 16-bit PCM)
    if filename.endswith(".wav"):
        if not os.path.exists(file_path):
            mp3_path = file_path.replace(".wav", ".mp3")
            if os.path.exists(mp3_path):
                try:
                    from pydub import AudioSegment
                    sound = AudioSegment.from_mp3(mp3_path)
                    # Standarkan ke 16000Hz, 16-bit, 2 channel (Stereo L+R untuk I2S MAX98357A)
                    sound = sound.set_frame_rate(16000).set_channels(2).set_sample_width(2)
                    sound.export(file_path, format="wav")
                except Exception as e:
                    print(f"Error converting MP3 to WAV: {e}")
                    raise HTTPException(status_code=500, detail="Gagal konversi audio ke WAV")
            else:
                raise HTTPException(status_code=404, detail="File audio MP3 sumber tidak ditemukan")
        return FileResponse(file_path, media_type="audio/wav")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File audio tidak ditemukan")
    return FileResponse(file_path, media_type="audio/mpeg")


@app.post("/api/ai/voice", tags=["Asisten Belajar AI"])
def configure_voice(req: VoiceConfigRequest):
    """Mengatur jenis suara default: 'cowok' (Ardi) atau 'cewek' (Gadis)."""
    if ai_service.set_voice(req.voice):
        return {
            "status": "success",
            "message": f"Suara berhasil diatur ke '{req.voice}' ({ai_service.get_current_voice()})"
        }
    raise HTTPException(status_code=400, detail="Pilihan suara hanya 'cowok' atau 'cewek'")


@app.get("/api/ai/voice", tags=["Asisten Belajar AI"])
def get_voice_setting():
    """Mendapatkan pengaturan suara aktif saat ini."""
    return {
        "voice_gender": ai_service.voice_gender,
        "voice_model": ai_service.get_current_voice()
    }


@app.get("/api/esp/companion", tags=["ESP32-S3 Physical Companion"])
def get_esp_companion_state():
    """
    Endpoint terpadu untuk ESP32-S3 Physical Robot Companion:
    Mengembalikan emosi OLED (happy, neutral, thinking, speaking, angry),
    status timer pomodoro, dan pesan peringatan jika terdeteksi distraksi.
    """
    pomo = pomodoro_manager.get_state()
    emotion = pomo.get("emotion", "NORMAL").lower()

    # Petakan emosi ke format mata robot XiaoZhi
    mapped_emotion = "neutral"
    if emotion in ["happy", "celebrating"]:
        mapped_emotion = "happy"
    elif emotion in ["angry", "distracted", "warning"]:
        mapped_emotion = "angry"
    elif emotion in ["thinking", "evaluating"]:
        mapped_emotion = "thinking"
    elif emotion in ["speaking", "talking"]:
        mapped_emotion = "speaking"

    distractions = pomo.get("distractions", {}).get("active", {})
    alert_msg = ""
    if distractions.get("phone", False):
        alert_msg = "Distraksi: Simpan HP-mu!"
        mapped_emotion = "angry"
    elif distractions.get("absent", False):
        alert_msg = "Pengguna tidak di tempat"
        mapped_emotion = "sad"

    return {
        "emotion": mapped_emotion,
        "mode": pomo.get("mode", "WORK"),
        "time_left": pomo.get("time_left", 0),
        "focus_score": pomo.get("focus_score", 100),
        "alert": alert_msg,
        "voice_gender": ai_service.voice_gender
    }


if __name__ == "__main__":
    import uvicorn

    port = Config.PORT if hasattr(Config, "PORT") else 5000
    host = Config.HOST if hasattr(Config, "HOST") else "0.0.0.0"
    print(f"\n=======================================================", flush=True)
    print(f"🌟 ASISTEN BELAJAR AI - FASTAPI & MYSQL CORE BACKEND", flush=True)
    print(f"📡 Swagger API Documentation : http://localhost:{port}/docs", flush=True)
    print(f"🐬 phpMyAdmin Web Interface  : http://localhost:8080", flush=True)
    print(f"📷 Video Stream MJPEG Feed    : http://localhost:{port}/video_feed", flush=True)
    print(f"🤖 ESP32-S3 OLED Endpoint    : http://localhost:{port}/api/esp/pomodoro", flush=True)
    print(f"=======================================================\n", flush=True)
    uvicorn.run("server:app", host=host, port=port, reload=False)
