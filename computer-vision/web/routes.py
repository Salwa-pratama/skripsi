import os
import base64
import requests
import cv2
import time
from flask import Blueprint, render_template, request, jsonify, Response
from config import Config

def create_routes(camera_streamer, mediapipe_detector, pomodoro_manager, sibi_translator=None, distraction_detector=None):
    main_bp = Blueprint('main', __name__)

    @main_bp.route('/')
    def dashboard():
        return render_template('dashboard.html', 
                               default_source=camera_streamer.source,
                               gemini_ready=bool(Config.GEMINI_API_KEY),
                               active_tab='pomodoro')

    @main_bp.route('/sibi')
    def sibi_page():
        """Halaman terpisah khusus Indonesian Sign Language (SIBI Abjad)."""
        return render_template('sibi.html',
                               default_source=camera_streamer.source,
                               active_tab='sibi',
                               model_loaded=sibi_translator.model_loaded if sibi_translator else False)

    @main_bp.route('/api/sibi/action', methods=['POST'])
    def sibi_action():
        if not sibi_translator:
            return jsonify({"status": "error", "message": "SIBI Translator tidak aktif"}), 500
        data = request.get_json() or {}
        action = data.get("action", "")
        if action == "space":
            sibi_translator.add_space()
        elif action == "backspace":
            sibi_translator.backspace()
        elif action == "clear":
            sibi_translator.clear()
        else:
            return jsonify({"status": "error", "message": f"Aksi '{action}' tidak dikenal"}), 400
        return jsonify({"status": "success", "state": sibi_translator.get_state()})

    @main_bp.route('/api/sibi/state', methods=['GET'])
    def sibi_state():
        if not sibi_translator:
            return jsonify({"status": "error"}), 500
        return jsonify(sibi_translator.get_state())

    @main_bp.route('/api/sibi/reload_model', methods=['POST'])
    def sibi_reload_model():
        if sibi_translator:
            sibi_translator.load_model()
            return jsonify({"status": "success", "model_loaded": sibi_translator.model_loaded})
        return jsonify({"status": "error"}), 500

    @main_bp.route('/video_feed')
    def video_feed():
        """
        Native High-Performance HTTP MJPEG Video Stream (Hardware-Accelerated di Browser).
        Menggunakan frame-id synchronizer agar setiap frame baru terkirim tepat 1 kali tanpa duplikasi/lag.
        """
        def gen():
            last_id = -1
            while True:
                fid, jpeg = camera_streamer.get_latest_frame_with_id()
                if fid != last_id and jpeg is not None:
                    last_id = fid
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
                else:
                    time.sleep(0.005) # Cek frame baru tiap 5ms (responsif hingga 60+ FPS)

        return Response(gen(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @main_bp.route('/api/tune_camera', methods=['POST'])
    def tune_camera():
        data = request.get_json() or {}
        ip = data.get("ip", "192.168.1.12")
        framesize = data.get("framesize", 10) # 10 = VGA 640x480
        quality = data.get("quality", 10)
        camera_streamer.tune_esp_camera(ip, framesize, quality)
        return jsonify({"status": "success", "message": f"Kamera diatur ke framesize={framesize}, quality={quality}"})

    @main_bp.route('/api/status', methods=['GET'])
    def api_status():
        cam_status = camera_streamer.get_status()
        pomo_status = pomodoro_manager.get_state()
        return jsonify({
            "camera": cam_status,
            "pomodoro": pomo_status,
            "ai": {
                "mediapipe_enabled": mediapipe_detector.enabled,
                "hands_enabled": getattr(mediapipe_detector, 'hands_enabled', True)
            }
        })

    @main_bp.route('/api/esp/pomodoro', methods=['GET'])
    def api_esp_pomodoro():
        """
        Ultra-Lightweight JSON Endpoint Khusus Layar OLED ESP32-S3 (128x64 SSD1306).
        Payload sangat ringkas (< 150 bytes), ramah buffer ArduinoJson & zero-lag untuk video stream.
        """
        pomo = pomodoro_manager.get_state()
        
        raw_mode = pomo.get("mode", "work")
        mode_str = "WORK"
        if raw_mode == "short_break":
            mode_str = "BREAK"
        elif raw_mode == "long_break":
            mode_str = "LONG_BREAK"

        # Alert singkat untuk layar OLED jika terdeteksi distraksi
        alert_str = ""
        live_flags = pomo.get("live_flags", {})
        abs_track = pomo.get("absence_tracking", {})

        if abs_track.get("tolerance_exceeded"):
            alert_str = "ABSEN!"
        elif live_flags.get("is_phone"):
            alert_str = "HP!"
        elif live_flags.get("is_head_down") and not pomo.get("allow_head_down", True):
            alert_str = "NUNDUK!"
        elif not abs_track.get("is_user_present", True):
            alert_str = "ABSEN"

        # Truncate nama task agar pas 1 baris di OLED 128x64 (maks 14 char)
        task_title = pomo.get("task_name", "Belajar Fokus")
        if len(task_title) > 14:
            task_title = task_title[:12] + ".."

        return jsonify({
            "mode": mode_str,
            "status": pomo.get("status", "stopped").upper(),
            "time_str": pomo.get("formatted_time", "25:00"),
            "time_left": int(pomo.get("time_left", 0)),
            "cycle_str": f"{pomo.get('current_cycle', 1)}/{pomo.get('target_cycles', 4)}",
            "task": task_title,
            "study_mode": pomo.get("study_mode", "book"),
            "alert": alert_str,
            "focus": int(pomo.get("focus_score", 100))
        })

    @main_bp.route('/api/camera_source', methods=['POST'])
    def change_source():
        data = request.get_json() or {}
        new_source = data.get("source", "").strip()
        if not new_source:
            return jsonify({"status": "error", "message": "Source tidak boleh kosong"}), 400
        
        camera_streamer.set_source(new_source)
        return jsonify({
            "status": "success",
            "message": f"Sumber kamera dialihkan ke: {new_source}",
            "current_source": str(camera_streamer.source)
        })

    @main_bp.route('/api/pomodoro/<action>', methods=['POST'])
    def pomodoro_action(action):
        data = request.get_json() or {}
        if action == "start":
            pomodoro_manager.start()
        elif action == "pause":
            pomodoro_manager.pause()
        elif action == "reset":
            pomodoro_manager.reset()
        elif action == "skip":
            pomodoro_manager.skip()
        elif action == "switch_mode":
            mode = data.get("mode", pomodoro_manager.MODE_WORK)
            pomodoro_manager.switch_mode(mode)
        elif action == "configure":
            study_mode = data.get("study_mode", "book")
            if distraction_detector:
                distraction_detector.set_study_mode(study_mode)
            pomodoro_manager.configure_session(
                task_name=data.get("task_name"),
                study_mode=study_mode,
                work_min=data.get("work_min"),
                short_break_min=data.get("short_break_min"),
                long_break_min=data.get("long_break_min"),
                target_cycles=data.get("target_cycles"),
                tolerance_pct=data.get("tolerance_pct")
            )
        elif action == "finish_choice":
            choice = data.get("choice", "save")
            pomodoro_manager.finish_session_choice(choice)
        else:
            return jsonify({"status": "error", "message": f"Aksi '{action}' tidak dikenali"}), 400

        return jsonify({"status": "success", "state": pomodoro_manager.get_state()})

    @main_bp.route('/api/toggle_ai', methods=['POST'])
    def toggle_ai():
        data = request.get_json() or {}
        feature = data.get("feature")
        enabled = data.get("enabled", True)

        if feature in ["mediapipe", "hands"]:
            mediapipe_detector.enabled = bool(enabled)
            mediapipe_detector.hands_enabled = bool(enabled)
        elif feature in ["distraction", "study_ai"]:
            if distraction_detector:
                distraction_detector.enabled = bool(enabled)
        else:
            return jsonify({"status": "error", "message": "Fitur AI tidak valid"}), 400

        return jsonify({
            "status": "success",
            "mediapipe_enabled": mediapipe_detector.enabled,
            "distraction_enabled": distraction_detector.enabled if distraction_detector else False
        })

    @main_bp.route('/api/toggle_enhancer', methods=['POST'])
    def toggle_enhancer():
        data = request.get_json() or {}
        feature = data.get("feature", "all")
        enabled = data.get("enabled", True)

        if feature == "all":
            camera_streamer.enhancer.enabled = bool(enabled)
        elif feature == "clahe":
            camera_streamer.enhancer.clahe_enabled = bool(enabled)
        elif feature == "denoise":
            camera_streamer.enhancer.denoise_enabled = bool(enabled)
        elif feature == "sharpen":
            camera_streamer.enhancer.sharpen_enabled = bool(enabled)
        elif feature == "thermal":
            camera_streamer.enhancer.thermal_correction_enabled = bool(enabled)
        else:
            return jsonify({"status": "error", "message": f"Fitur enhancer '{feature}' tidak valid"}), 400

        return jsonify({
            "status": "success",
            "enhancer": {
                "enabled": camera_streamer.enhancer.enabled,
                "clahe": camera_streamer.enhancer.clahe_enabled,
                "denoise": camera_streamer.enhancer.denoise_enabled,
                "sharpen": camera_streamer.enhancer.sharpen_enabled,
                "thermal": camera_streamer.enhancer.thermal_correction_enabled
            }
        })

    @main_bp.route('/api/chat', methods=['POST'])
    def api_chat():
        """Mendukung voice/chat multimodal asisten belajar (Gemini)"""
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        include_vision = data.get("include_vision", False)

        if not message:
            return jsonify({"error": "Pesan tidak boleh kosong"}), 400

        if not Config.GEMINI_API_KEY:
            return jsonify({"reply": "API Key Gemini belum disetel di file .env."})

        # Ambil frame kamera jika opsi vision diaktifkan
        image_b64 = None
        if include_vision:
            raw_frame = camera_streamer.get_raw_frame()
            if raw_frame is not None:
                ret, buf = cv2.imencode('.jpg', raw_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    image_b64 = base64.b64encode(buf).decode('utf-8')

        reply = _query_gemini(message, image_b64)
        return jsonify({"reply": reply, "vision_used": bool(image_b64)})

    return main_bp

def _query_gemini(prompt_text, image_b64=None):
    gemini_key = Config.GEMINI_API_KEY
    models = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    parts = [{
        "text": f"Kamu adalah Asisten Belajar AI ramah. Jawab ringkas dalam 2-3 kalimat.\nPertanyaan: {prompt_text}"
    }]
    if image_b64:
        parts.append({
            "inline_data": {
                "mime_type": "image/jpeg",
                "data": image_b64
            }
        })

    for model_name in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"
        try:
            res = requests.post(url, json={"contents": [{"parts": parts}]}, timeout=10)
            if res.status_code == 200:
                candidates = res.json().get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"].strip()
        except Exception:
            continue
    return "Maaf, asisten AI sedang tidak dapat merespons saat ini."
