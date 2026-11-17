import os
from dotenv import load_dotenv

load_dotenv(override=True)

class Config:
    # Server Settings
    SECRET_KEY = os.getenv("SECRET_KEY", "asisten-belajar-secret-2026")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", 5000))

    # Camera Stream Source
    # Default URL ESP32-S3 (Stream MJPEG atau Snapshot Capture)
    DEFAULT_ESP32_STREAM = os.getenv("ESP32_STREAM_URL", "http://192.168.1.12:81/stream")
    DEFAULT_ESP32_CAPTURE = os.getenv("ESP32_CAPTURE_URL", "http://192.168.1.12/capture")
    DEFAULT_SOURCE = os.getenv("CAMERA_SOURCE", DEFAULT_ESP32_STREAM)

    # COCO-SSD / MobileNet Model Paths
    MODEL_PB = os.path.join(os.path.dirname(__file__), "model", "ssd_mobilenet_v2_coco_2018_03_29", "frozen_inference_graph.pb")
    MODEL_PBTXT = os.path.join(os.path.dirname(__file__), "model", "ssd_mobilenet_v2_coco_2018_03_29.pbtxt")
    
    # COCO Labels
    COCO_LABELS = {
        1: "Person (User)",
        73: "Laptop",
        77: "Cell Phone (Distraction!)",
        84: "Book"
    }
    COCO_CONFIDENCE_THRESHOLD = 0.35

    # MediaPipe Drowsiness & Face Config
    EAR_THRESHOLD = 0.22        # Eye Aspect Ratio threshold (dibawah ini dianggap mata tertutup)
    DROWSY_CONSECUTIVE_SEC = 2.0 # Jika mata tertutup > 2 detik, dianggap mengantuk

    # Pomodoro Defaults (dalam detik)
    POMODORO_WORK_TIME = 25 * 60
    POMODORO_SHORT_BREAK = 5 * 60
    POMODORO_LONG_BREAK = 15 * 60

    # Gemini API Key (optional untuk verbal reminder)
    GEMINI_API_KEY = os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY")
