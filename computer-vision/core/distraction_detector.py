import os
import time
import math
import threading
import cv2
import numpy as np

from config import Config
from core.coco_detector import CocoDetector

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False

class AsyncCocoWorker:
    """
    Worker background untuk SSD MobileNet COCO agar tidak membebani video stream (tetap 30+ FPS).
    Inference berjalan di background setiap ~100-200ms.
    """
    def __init__(self):
        self.detector = CocoDetector()
        self.lock = threading.Lock()
        self.latest_objects = []
        self.has_phone = False
        self.has_person = False
        self.frame_to_process = None
        self.running = True
        
        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def feed_frame(self, frame):
        with self.lock:
            # Update frame yang akan dianalisis jika worker sedang luang
            if self.frame_to_process is None and frame is not None:
                # Resize ke 320x240 untuk efisiensi transfer & inference cepat
                self.frame_to_process = cv2.resize(frame, (320, 240))

    def _worker_loop(self):
        while self.running:
            target_frame = None
            with self.lock:
                if self.frame_to_process is not None:
                    target_frame = self.frame_to_process
                    self.frame_to_process = None

            if target_frame is not None:
                try:
                    _, objs, phone, person = self.detector.process_frame(target_frame, draw=False)
                    with self.lock:
                        self.latest_objects = objs
                        self.has_phone = phone
                        self.has_person = person
                except Exception:
                    pass

            time.sleep(0.08)

    def get_results(self):
        with self.lock:
            return list(self.latest_objects), self.has_phone, self.has_person

    def stop(self):
        self.running = False


class StudyDistractionDetector:
    """
    Detektor Terpadu 3 Jenis Distraksi Belajar (ESP32-S3 / Kamera):
    1. Pengguna Meninggalkan Tempat (Absence / No Person)
    2. Bermain Handphone (COCO SSD MobileNet Class 77)
    3. Kepala Menunduk (Head Down / Bowing Down via MediaPipe Face Mesh & Head Pose Pitch)
    """

    def __init__(self):
        self.coco_worker = AsyncCocoWorker()
        self.face_detector = None
        self.enabled = True
        
        # Study Mode: 'book' (Membaca/Menulis Buku - Menunduk Diizinkan) atau 'screen' (Layar/Komputer)
        self.study_mode = "book"
        self.task_name = "Sesi Belajar Fokus"

        # Debouncing & Thresholds
        self.absence_counter = 0.0
        self.phone_counter = 0.0
        self.head_down_counter = 0.0
        
        self.is_absent = False
        self.is_phone = False
        self.is_head_down = False
        
        self.last_face_seen = 0.0
        self.head_pitch = 0.0
        self.last_tick = time.time()

        if HAS_MEDIAPIPE:
            self._init_face_landmarker()

    def set_study_mode(self, mode: str):
        """Menyetel mode belajar: 'book' (Buku/Menulis) atau 'screen' (Layar/PC)"""
        mode_clean = str(mode).lower().strip()
        if mode_clean in ["book", "writing", "meja", "buku"]:
            self.study_mode = "book"
            self.head_down_counter = 0.0
            self.is_head_down = False
        else:
            self.study_mode = "screen"

    def _init_face_landmarker(self):
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
        face_model_path = os.path.join(model_dir, "face_landmarker.task")
        
        if os.path.exists(face_model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=face_model_path)
                options = vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    output_facial_transformation_matrixes=True,
                    num_faces=1,
                    min_face_detection_confidence=0.35,
                    min_face_presence_confidence=0.35
                )
                self.face_detector = vision.FaceLandmarker.create_from_options(options)
                print("✅ [DistractionDetector] MediaPipe Face Landmarker (Head Pose & Pitch) Siap!", flush=True)
            except Exception as e:
                print(f"⚠️ [DistractionDetector] Gagal memuat FaceLandmarker: {e}", flush=True)

    @staticmethod
    def _compute_pitch_from_matrix(matrix_4x4):
        """Menghitung sudut pitch (menunduk/tegak) dari transformasi 4x4 MediaPipe"""
        try:
            R = np.array(matrix_4x4)[:3, :3]
            sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
            if sy >= 1e-6:
                pitch = math.degrees(math.atan2(R[2, 1], R[2, 2]))
            else:
                pitch = math.degrees(math.atan2(-R[1, 2], R[1, 1]))
            return pitch
        except Exception:
            return 0.0

    def process_frame(self, frame, has_hands=False, draw=True):
        """
        Menganalisis frame kamera untuk 3 distraksi belajar.
        Mengembalikan: (annotated_frame, telemetry_dict)
        """
        now = time.time()
        dt = min(0.2, max(0.01, now - self.last_tick))
        self.last_tick = now

        if frame is None or not self.enabled:
            return frame, {
                "is_present": True,
                "is_absent": False,
                "is_phone": False,
                "is_head_down": False,
                "head_pitch": 0.0,
                "face_detected": False,
                "person_detected": False,
                "phone_detected": False
            }

        h, w = frame.shape[:2]
        
        # 1. Update Async COCO Worker
        self.coco_worker.feed_frame(frame)
        objects, has_phone_raw, has_person_raw = self.coco_worker.get_results()

        # 2. Deteksi Wajah & Head Pose (MediaPipe FaceLandmarker)
        face_detected = False
        head_down_instant = False
        pitch = 0.0

        if self.face_detector is not None:
            try:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                res = self.face_detector.detect(mp_img)

                if res and res.face_landmarks and len(res.face_landmarks) > 0:
                    face_detected = True
                    self.last_face_seen = now
                    landmarks = res.face_landmarks[0]

                    # Periksa pitch dari facial transformation matrix jika tersedia
                    if res.facial_transformation_matrixes and len(res.facial_transformation_matrixes) > 0:
                        pitch = self._compute_pitch_from_matrix(res.facial_transformation_matrixes[0])
                        self.head_pitch = round(pitch, 1)

                    # Geometri titik wajah (Nose 1, Forehead 10, Chin 152)
                    pt_forehead = landmarks[10]
                    pt_nose = landmarks[1]
                    pt_chin = landmarks[152]

                    d_top = pt_nose.y - pt_forehead.y
                    d_bottom = pt_chin.y - pt_nose.y

                    # Rasio menunduk: saat kepala menunduk ke meja, dagu tertarik ke dalam/atas relatif ke hidung
                    is_pitch_down = (pitch < -12.0 or pitch > 20.0) # Tergantung polaritas sudut
                    is_ratio_down = (d_top > 0 and (d_bottom / d_top) < 0.52)

                    if is_pitch_down or is_ratio_down:
                        head_down_instant = True

                    if draw:
                        # Gambar bounding box wajah elegan
                        fx_min = int(min(lm.x for lm in landmarks) * w)
                        fx_max = int(max(lm.x for lm in landmarks) * w)
                        fy_min = int(min(lm.y for lm in landmarks) * h)
                        fy_max = int(max(lm.y for lm in landmarks) * h)

                        color = (0, 165, 255) if head_down_instant else (0, 230, 120)
                        cv2.rectangle(frame, (fx_min, fy_min), (fx_max, fy_max), color, 2)
                        
                        label_txt = f"Wajah: {'Menunduk!' if head_down_instant else 'Tegak/Fokus'}"
                        cv2.putText(frame, label_txt, (fx_min, max(20, fy_min - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)
            except Exception:
                pass

        # 3. Evaluasi Kehadiran Pengguna (Presence) - Poin 1 Engineering:
        # PRIMER: COCO-SSD (SSD MobileNet Person) sangat tangguh untuk kamera burik/low-res
        # SEKUNDER: MediaPipe Face Landmarker & Hand Tracking
        is_present_instant = bool(has_person_raw or face_detected or has_hands)

        # 4. Debouncing State Distraksi:
        
        # --- Distraksi 1: Meninggalkan Tempat (Absent) ---
        if not is_present_instant:
            self.absence_counter += dt
            if self.absence_counter >= 3.0:
                self.is_absent = True
        else:
            self.absence_counter = max(0.0, self.absence_counter - (dt * 2.0))
            if self.absence_counter <= 0.5:
                self.is_absent = False

        # --- Distraksi 2: Mainan Handphone (Phone via COCO-SSD Class 77) ---
        if has_phone_raw:
            self.phone_counter += dt
            if self.phone_counter >= 1.2:
                self.is_phone = True
        else:
            self.phone_counter = max(0.0, self.phone_counter - (dt * 1.5))
            if self.phone_counter <= 0.3:
                self.is_phone = False

        # --- Distraksi 3: Menunduk (Head Down) - Poin 2 & 4 Engineering:
        # Jika mode belajar adalah 'book' (Membaca/Menulis Buku), menunduk adalah hal normal & BUKAN distraksi!
        if self.study_mode == "book":
            head_down_instant = False
            self.head_down_counter = 0.0
            self.is_head_down = False
        else:
            # Mode Layar/Komputer: Menunduk hanya dievaluasi jika face terdeteksi menunduk tajam > 4 detik
            if head_down_instant:
                self.head_down_counter += dt
                if self.head_down_counter >= 4.0:
                    self.is_head_down = True
            else:
                self.head_down_counter = max(0.0, self.head_down_counter - (dt * 1.5))
                if self.head_down_counter <= 0.5:
                    self.is_head_down = False

        # 5. Gambar Bounding Box Objek COCO (HP, Person, Laptop)
        if draw and objects:
            for obj in objects:
                box = obj.get("box", [0, 0, 0, 0])
                # Scale box dari 320x240 ke ukuran frame saat ini
                scale_x = w / 320.0
                scale_y = h / 240.0
                bx1 = int(box[0] * scale_x)
                by1 = int(box[1] * scale_y)
                bx2 = int(box[2] * scale_x)
                by2 = int(box[3] * scale_y)

                is_phone_obj = obj.get("is_distraction", False)
                if is_phone_obj:
                    # Kotak Merah Menyala Berdenyut untuk HP
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 0, 255), 3)
                    tag = "DISTRAKSI: HANDPHONE"
                    (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                    cv2.rectangle(frame, (bx1, max(0, by1 - th - 10)), (bx1 + tw + 10, by1), (0, 0, 255), -1)
                    cv2.putText(frame, tag, (bx1 + 5, by1 - 5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)

        # 6. Render Banner Status pada Frame
        if draw:
            # Banner Status Bawah Layar
            if self.is_absent:
                banner_color = (0, 0, 220) # Merah
                banner_text = "PERINGATAN: PENGGUNA TIDAK DI MEJA (COCO-SSD Person: Tidak Terdeteksi)!"
            elif self.is_phone:
                banner_color = (0, 0, 240) # Merah
                banner_text = "PERINGATAN: TERDETEKSI BERMAIN HANDPHONE DI MEJA!"
            elif self.is_head_down and self.study_mode == "screen":
                banner_color = (0, 140, 255) # Oranye
                banner_text = "PERINGATAN: KEPALA MENUNDUK / TERTIDUR DI LAYAR!"
            else:
                banner_color = (0, 180, 80) # Hijau
                mode_badge = "📖 BUKU / MENULIS" if self.study_mode == "book" else "💻 LAYAR / PC"
                banner_text = f"STATUS: FOKUS BELAJAR [{mode_badge}]"

            cv2.rectangle(frame, (0, h - 32), (w, h), (20, 24, 30), -1)
            cv2.line(frame, (0, h - 32), (w, h - 32), banner_color, 2)
            cv2.circle(frame, (18, h - 16), 5, banner_color, -1)
            cv2.putText(frame, banner_text, (32, h - 11),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return frame, {
            "is_present": not self.is_absent,
            "is_absent": self.is_absent,
            "is_phone": self.is_phone,
            "is_head_down": self.is_head_down,
            "head_pitch": self.head_pitch,
            "study_mode": self.study_mode,
            "head_down_allowed": (self.study_mode == "book"),
            "face_detected": face_detected,
            "person_detected": has_person_raw,
            "phone_detected": has_phone_raw
        }

    def close(self):
        try:
            self.coco_worker.stop()
            if self.face_detector is not None:
                self.face_detector.close()
                self.face_detector = None
        except Exception:
            pass
