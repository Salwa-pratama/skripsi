import os
from flask import Flask
from flask_socketio import SocketIO

from config import Config
from core.camera_streamer import CameraStreamer
from core.mediapipe_detector import MediaPipeDetector
from core.distraction_detector import StudyDistractionDetector
from core.sibi_translator import SibiTranslator
from pomodoro.pomodoro_manager import PomodoroManager
from web.routes import create_routes
from web.socket_events import init_socket_events

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = Config.SECRET_KEY

    print("🚀 [System] Menginisialisasi komponen Asisten Belajar AI & Vision Pipeline...", flush=True)
    
    # 1. Camera Streamer (ESP32-S3 High-Speed Streamer)
    camera_streamer = CameraStreamer(source=Config.DEFAULT_SOURCE)
    
    # 2. MediaPipe Pure Hand Tracking (21 Sendi Jari)
    mediapipe_detector = MediaPipeDetector()

    # 3. Integrated Study Distraction Detector (Absence, Phone, Head Down)
    distraction_detector = StudyDistractionDetector()
    
    # 4. SIBI Translator (Abjad Classifier & Word Assembler)
    sibi_translator = SibiTranslator()

    # 5. Pomodoro Study Timer State Machine
    pomodoro_manager = PomodoroManager()

    # 6. Registrasi Route Blueprint
    main_bp = create_routes(camera_streamer, mediapipe_detector, pomodoro_manager, 
                            sibi_translator=sibi_translator, distraction_detector=distraction_detector)
    app.register_blueprint(main_bp)

    # 7. Inisialisasi WebSocket (Socket.IO)
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")
    init_socket_events(socketio, camera_streamer, mediapipe_detector, pomodoro_manager, 
                       sibi_translator=sibi_translator, distraction_detector=distraction_detector)

    return app, socketio

app, socketio = create_app()

if __name__ == '__main__':
    port = Config.PORT
    print(f"\n=======================================================", flush=True)
    print(f"🌟 ASISTEN BELAJAR AI - PURE HAND TRACKING & POMODORO", flush=True)
    print(f"📡 Server berjalan di: http://localhost:{port}", flush=True)
    print(f"📷 Default Source: {Config.DEFAULT_SOURCE}", flush=True)
    print(f"=======================================================\n", flush=True)
    socketio.run(app, host=Config.HOST, port=port, debug=False, allow_unsafe_werkzeug=True)
