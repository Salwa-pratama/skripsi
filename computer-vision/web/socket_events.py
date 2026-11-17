import time
import base64
import threading
import cv2
from flask_socketio import SocketIO, emit

def init_socket_events(socketio: SocketIO, camera_streamer, mediapipe_detector, pomodoro_manager, 
                       sibi_translator=None, distraction_detector=None):
    """
    Mengelola event WebSocket dan loop pipeline pemrosesan video real-time berkinerja tinggi (30+ FPS).
    Integrasi:
    1. MediaPipe Hand Tracking (21 Sendi Jari) & SIBI Translator.
    2. Detektor 3 Distraksi Belajar (Meninggalkan Tempat, Main HP, Menunduk).
    3. Pomodoro Study Timer State Machine (Target Task, Preset, Toleransi %, & Riwayat).
    """
    def vision_pipeline_worker():
        fps_counter = 0
        fps_timer = time.time()
        sibi_timer = time.time()
        last_alert_time = 0
        last_loop_time = time.time()
        curr_fps = 0.0

        while True:
            start_time = time.time()
            dt = max(0.01, min(0.2, start_time - last_loop_time))
            last_loop_time = start_time
            
            # 1. Ambil frame kamera (Enhanced atau Raw)
            frame = camera_streamer.get_enhanced_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            # 2. Deteksi Sendi Jari Tangan (MediaPipe Hands - 21 Sendi)
            has_hands = False
            hands_status = {"count": 0, "hands": []}
            if mediapipe_detector and mediapipe_detector.enabled:
                frame, has_hands, hands_info, _ = mediapipe_detector.process_frame(frame, draw=True)
                hands_status = mediapipe_detector.get_hands_status()

            # 3. Deteksi 3 Jenis Distraksi Belajar Terpadu
            distraction_telem = {
                "is_present": True,
                "is_absent": False,
                "is_phone": False,
                "is_head_down": False,
                "head_pitch": 0.0
            }

            if distraction_detector and distraction_detector.enabled:
                frame, distraction_telem = distraction_detector.process_frame(frame, has_hands=has_hands, draw=True)
                
                # Update ke Pomodoro Manager
                pomodoro_manager.update_distraction_states(
                    is_absent=distraction_telem.get("is_absent", False),
                    is_phone=distraction_telem.get("is_phone", False),
                    is_head_down=distraction_telem.get("is_head_down", False),
                    dt=dt
                )

                # Broadcast Alert Toast jika ada distraksi baru saat mode WORK
                now = time.time()
                pomo_state = pomodoro_manager.get_state()
                if pomo_state["status"] == "running" and pomo_state["mode"] == "work" and (now - last_alert_time >= 4.0):
                    alert_reason = None
                    if distraction_telem.get("is_absent") and pomo_state["absence_tracking"]["tolerance_exceeded"]:
                        alert_reason = f"Toleransi Meninggalkan Tempat Terlampaui ({pomo_state['absence_tracking']['tolerance_pct']}%)!"
                    elif distraction_telem.get("is_phone"):
                        alert_reason = "Terdeteksi Bermain Handphone di Meja Belajar!"
                    elif distraction_telem.get("is_head_down") and not pomo_state.get("allow_head_down", True):
                        alert_reason = "Posisi Kepala Menunduk / Tertidur di Layar!"

                    if alert_reason:
                        last_alert_time = now
                        socketio.emit('distraction_alert', {
                            "reason": alert_reason,
                            "time": time.strftime("%H:%M:%S")
                        })

            # 4. Proses Penerjemah Bahasa Isyarat SIBI (Jika Aktif)
            if sibi_translator:
                raw_lms = getattr(mediapipe_detector, 'latest_raw_landmarks', [])
                sibi_translator.process_landmarks(raw_lms)

            # 5. Update frame yang sudah di-annotasi ke streamer untuk /video_feed
            camera_streamer.update_processed_frame(frame)

            # 6. Broadcast SIBI Telemetry (setiap ~100ms)
            now = time.time()
            if sibi_translator and (now - sibi_timer >= 0.1):
                sibi_timer = now
                socketio.emit('sibi_update', sibi_translator.get_state())

            # 7. Hitung Processing FPS & Telemetri Utama
            fps_counter += 1
            if now - fps_timer >= 1.0:
                curr_fps = round(fps_counter / (now - fps_timer), 1)
                fps_counter = 0
                fps_timer = now

                # Broadcast telemetri lengkap tiap detik ke dashboard
                socketio.emit('telemetry', {
                    "fps": curr_fps,
                    "camera_connected": camera_streamer.connected,
                    "port81_blocked": getattr(camera_streamer, 'port81_blocked', False),
                    "hands": hands_status,
                    "hands_detected": has_hands,
                    "distraction": distraction_telem,
                    "enhancer": camera_streamer.get_status().get("enhancer", {}),
                    "pomodoro": pomodoro_manager.get_state()
                })

            # Delay adaptif minimal untuk pacing stabil (~35 FPS)
            elapsed = time.time() - start_time
            if elapsed < 0.025:
                time.sleep(0.025 - elapsed)
            else:
                time.sleep(0.001)

    # Jalankan background worker vision pipeline
    worker_thread = threading.Thread(target=vision_pipeline_worker, daemon=True)
    worker_thread.start()

    # --- Socket.IO Event Handlers ---

    @socketio.on('sibi_action')
    def handle_sibi_action(data):
        if not sibi_translator:
            return
        action = data.get('action')
        if action == 'space':
            sibi_translator.add_space()
        elif action == 'backspace':
            sibi_translator.backspace()
        elif action == 'clear':
            sibi_translator.clear()
        socketio.emit('sibi_update', sibi_translator.get_state())

    @socketio.on('connect')
    def handle_connect(auth=None):
        emit('initial_state', {
            "source": str(camera_streamer.source),
            "pomodoro": pomodoro_manager.get_state(),
            "ai": {
                "mediapipe_enabled": mediapipe_detector.enabled if mediapipe_detector else False,
                "hands_enabled": getattr(mediapipe_detector, 'hands_enabled', True),
                "distraction_enabled": distraction_detector.enabled if distraction_detector else True
            },
            "enhancer": camera_streamer.get_status().get("enhancer", {})
        })

    @socketio.on('change_source')
    def handle_change_source(data):
        new_source = data.get("source")
        if new_source is not None:
            camera_streamer.set_source(new_source)
            emit('source_changed', {"source": str(camera_streamer.source)}, broadcast=True)

    @socketio.on('pomodoro_action')
    def handle_pomodoro_action(data):
        action = data.get("action")
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
        
        emit('pomodoro_update', pomodoro_manager.get_state(), broadcast=True)

    @socketio.on('configure_pomodoro')
    def handle_configure_pomodoro(data):
        """Menyetel task, mode belajar (buku/layar), durasi pomodoro, target siklus, dan toleransi absen"""
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
        emit('pomodoro_update', pomodoro_manager.get_state(), broadcast=True)

    @socketio.on('finish_pomodoro_session')
    def handle_finish_pomodoro_session(data):
        """Menangani pilihan user setelah seluruh siklus selesai ('repeat' atau 'save')"""
        choice = data.get("choice", "save")
        pomodoro_manager.finish_session_choice(choice)
        emit('pomodoro_update', pomodoro_manager.get_state(), broadcast=True)

    @socketio.on('toggle_ai')
    def handle_toggle_ai(data):
        feature = data.get("feature")
        enabled = data.get("enabled", True)
        if feature in ["mediapipe", "hands"]:
            if mediapipe_detector:
                mediapipe_detector.hands_enabled = bool(enabled)
                mediapipe_detector.enabled = bool(enabled)
        elif feature in ["distraction", "study_ai"]:
            if distraction_detector:
                distraction_detector.enabled = bool(enabled)

        emit('ai_toggled', {
            "feature": feature,
            "enabled": enabled,
            "mediapipe_enabled": mediapipe_detector.enabled if mediapipe_detector else False,
            "distraction_enabled": distraction_detector.enabled if distraction_detector else False
        }, broadcast=True)

    @socketio.on('toggle_enhancer')
    def handle_toggle_enhancer(data):
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

        emit('enhancer_toggled', camera_streamer.get_status().get("enhancer", {}), broadcast=True)
