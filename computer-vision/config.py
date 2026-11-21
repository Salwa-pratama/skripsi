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
    DEFAULT_ESP32_STREAM = os.getenv("ESP32_STREAM_URL", "http://10.19.170.50:81/stream")
    DEFAULT_ESP32_CAPTURE = os.getenv("ESP32_CAPTURE_URL", "http://10.19.170.50/capture")
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
    COCO_CONFIDENCE_THRESHOLD = 0.25

    # =====================================================================
    # DETEKSI HANDPHONE (tangguh untuk casing hitam / layar mati)
    # ---------------------------------------------------------------------
    # COCO-SSD & YOLO umumnya mengenali HP dari LAYAR yang menyala. Saat user
    # memegang HP normal (layar menghadap dirinya), kamera hanya melihat
    # PUNGGUNG HP yang hitam -> skor deteksi sangat rendah/fluktuatif.
    # Strategi kompensasi:
    #   1. Ambang khusus kelas "cell phone" diturunkan (kelas lain tetap 0.25).
    #   2. Deteksi dijalankan pada FRAME MENTAH (bukan hasil CLAHE) karena
    #      enhancement justru menurunkan skor HP (terbukti dari pengukuran).
    #   3. Fusi COCO + YOLOv8n (detektor HP sekunder, dijalankan di frame mentah).
    #   4. Voting temporal: butuh beberapa hit dalam jendela waktu agar tidak
    #      terpengaruh deteksi sesaat (fluktuatif) maupun false positive.
    # =====================================================================
    COCO_PHONE_THRESHOLD = 0.15      # ambang per-frame kelas HP (COCO class 77)
    PHONE_TRIGGER_CONF = 0.30        # 1 frame dengan skor >= ini = bukti kuat (langsung)
    PHONE_VOTE_WINDOW_SEC = 1.8      # jendela waktu voting temporal
    PHONE_VOTE_MIN_HITS = 2          # minimal jumlah hit >= COCO_PHONE_THRESHOLD
    PHONE_ON_SEC = 0.4               # durasi bukti untuk menyalakan alarm HP
    PHONE_OFF_SEC = 0.8              # durasi TANPA bukti untuk mematikan alarm HP
    PHONE_YOLO_ENABLED = True        # pakai YOLOv8n sebagai detektor HP sekunder (bila ada)
    PHONE_YOLO_CONF = 0.12           # ambang kelas HP pada YOLOv8n
    PHONE_YOLO_INTERVAL_SEC = 0.35   # interval minimum inference YOLO (hemat CPU)

    # MediaPipe Drowsiness & Face Config
    EAR_THRESHOLD = 0.22        # Eye Aspect Ratio threshold (dibawah ini dianggap mata tertutup)
    DROWSY_CONSECUTIVE_SEC = 2.0 # Jika mata tertutup > 2 detik, dianggap mengantuk

    # Pomodoro Defaults (dalam detik)
    POMODORO_WORK_TIME = 25 * 60
    POMODORO_SHORT_BREAK = 5 * 60
    POMODORO_LONG_BREAK = 15 * 60

    # Gemini API Key (optional untuk verbal reminder)
    GEMINI_API_KEY = os.getenv("GEMINI_API") or os.getenv("GEMINI_API_KEY")
