import os
import time
import math
import threading
from collections import deque
import cv2
import numpy as np

from config import Config
from core.coco_detector import CocoDetector

try:
    from core.phone_detector import YoloPhoneDetector
    HAS_YOLO_PHONE = True
except Exception:
    HAS_YOLO_PHONE = False

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
    Inference berjalan di background setiap ~80-100ms.

    Kelas HP (77) memakai ambang khusus yang lebih rendah (Config.COCO_PHONE_THRESHOLD)
    agar HP casing hitam / layar mati lebih mudah tertangkap. Skor mentahnya
    diekspos untuk voting temporal di StudyDistractionDetector.
    """
    def __init__(self, conf_thresh=Config.COCO_CONFIDENCE_THRESHOLD,
                 phone_thresh=Config.COCO_PHONE_THRESHOLD):
        self.phone_thresh = phone_thresh
        self.detector = CocoDetector(conf_thresh=conf_thresh, phone_thresh=phone_thresh)
        self.lock = threading.Lock()
        self.latest_objects = []
        self.has_phone = False
        self.has_person = False
        self.phone_conf = 0.0
        self.phone_box = None
        self.frame_to_process = None
        self.running = True

        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

    def feed_frame(self, frame):
        with self.lock:
            # Selalu pakai frame TERBARU: jika worker masih sibuk, frame lama
            # ditimpa agar hasil tidak "basi" (mis. masih melaporkan HP yang
            # sudah tidak ada).
            if frame is not None:
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
                    _, objs, has_phone, has_person = self.detector.process_frame(target_frame, draw=False)

                    # Skor HP dari COCO (max confidence kelas 77)
                    coco_conf = 0.0
                    coco_box = None
                    for o in objs:
                        if o.get("class_id") == 77:
                            if o["confidence"] > coco_conf:
                                coco_conf = float(o["confidence"])
                                coco_box = o.get("box")

                    if coco_conf < self.phone_thresh:
                        coco_conf, coco_box = 0.0, None

                    with self.lock:
                        self.latest_objects = objs
                        self.has_phone = bool(coco_conf >= self.phone_thresh)
                        self.has_person = has_person
                        self.phone_conf = coco_conf
                        self.phone_box = coco_box
                except Exception:
                    pass

            time.sleep(0.08)

    def get_results(self):
        with self.lock:
            return list(self.latest_objects), self.has_phone, self.has_person

    def get_phone(self):
        with self.lock:
            return self.phone_conf, self.phone_box

    def stop(self):
        self.running = False


class AsyncYoloPhoneWorker:
    """
    Worker terpisah untuk YOLOv8n (detektor HP sekunder).

    Dipisah dari AsyncCocoWorker supaya inference YOLO yang relatif berat (~0.6s)
    TIDAK memperlambat update deteksi COCO. Hasilnya digabung (fusi max) oleh
    StudyDistractionDetector.
    """
    def __init__(self, interval_sec=Config.PHONE_YOLO_INTERVAL_SEC):
        self.interval_sec = max(0.2, float(interval_sec))
        self.lock = threading.Lock()
        self.phone_conf = 0.0
        self.phone_box = None
        self.phone_src = None
        self.frame_to_process = None
        self.running = True
        self.detector = None

        if getattr(Config, "PHONE_YOLO_ENABLED", True) and HAS_YOLO_PHONE:
            try:
                self.detector = YoloPhoneDetector()
            except Exception:
                self.detector = None

        if self.detector is not None and self.detector.enabled:
            self.thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.thread.start()
        else:
            self.thread = None

    def feed_frame(self, frame):
        if self.detector is None or not self.detector.enabled or frame is None:
            return
        with self.lock:
            # Selalu pakai frame terbaru (hindari hasil basi).
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
                    conf, box, src = self.detector.score(target_frame)
                    if conf < Config.PHONE_YOLO_CONF:
                        conf, box, src = 0.0, None, None
                    with self.lock:
                        self.phone_conf = conf
                        self.phone_box = box
                        self.phone_src = src
                except Exception:
                    pass

            time.sleep(self.interval_sec)

    def get_phone(self):
        with self.lock:
            return self.phone_conf, self.phone_box, self.phone_src

    def stop(self):
        self.running = False


class AsyncFaceWorker:
    """
    Worker background untuk MediaPipe FaceLandmarker agar tidak memblokir streaming video (tetap 25-30+ FPS).
    Inference berjalan di background thread terpisah setiap ~60-80ms.
    """
    def __init__(self):
        self.lock = threading.Lock()
        self.face_detected = False
        self.head_down_instant = False
        self.pitch = 0.0
        self.face_box = None  # (fx_min, fy_min, fx_max, fy_max) normalized 0.0 - 1.0
        self.frame_to_process = None
        self.running = True
        self.face_detector = None

        if HAS_MEDIAPIPE:
            self._init_face_landmarker()

        self.thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.thread.start()

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
                print("✅ [AsyncFaceWorker] MediaPipe Face Landmarker Asinkron Siap!", flush=True)
            except Exception as e:
                print(f"⚠️ [AsyncFaceWorker] Gagal memuat FaceLandmarker: {e}", flush=True)

    @staticmethod
    def _compute_pitch_from_matrix(matrix_4x4):
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

    def feed_frame(self, frame):
        with self.lock:
            # Selalu pakai frame terbaru agar anotasi wajah tidak "basi".
            if frame is not None:
                self.frame_to_process = frame.copy()

    def _worker_loop(self):
        while self.running:
            target_frame = None
            with self.lock:
                if self.frame_to_process is not None:
                    target_frame = self.frame_to_process
                    self.frame_to_process = None

            if target_frame is not None and self.face_detector is not None:
                try:
                    rgb_frame = cv2.cvtColor(target_frame, cv2.COLOR_BGR2RGB)
                    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
                    res = self.face_detector.detect(mp_img)

                    f_detected = False
                    h_down = False
                    f_pitch = 0.0
                    f_box = None

                    if res and res.face_landmarks and len(res.face_landmarks) > 0:
                        f_detected = True
                        landmarks = res.face_landmarks[0]

                        if res.facial_transformation_matrixes and len(res.facial_transformation_matrixes) > 0:
                            f_pitch = self._compute_pitch_from_matrix(res.facial_transformation_matrixes[0])

                        pt_forehead = landmarks[10]
                        pt_nose = landmarks[1]
                        pt_chin = landmarks[152]

                        d_top = pt_nose.y - pt_forehead.y
                        d_bottom = pt_chin.y - pt_nose.y

                        is_pitch_down = (f_pitch < -12.0 or f_pitch > 20.0)
                        is_ratio_down = (d_top > 0 and (d_bottom / d_top) < 0.52)

                        if is_pitch_down or is_ratio_down:
                            h_down = True

                        f_box = (
                            min(lm.x for lm in landmarks),
                            min(lm.y for lm in landmarks),
                            max(lm.x for lm in landmarks),
                            max(lm.y for lm in landmarks),
                        )

                    with self.lock:
                        self.face_detected = f_detected
                        self.head_down_instant = h_down
                        self.pitch = round(f_pitch, 1)
                        self.face_box = f_box

                except Exception:
                    pass

            time.sleep(0.05)

    def get_results(self):
        with self.lock:
            return self.face_detected, self.head_down_instant, self.pitch, self.face_box

    def stop(self):
        self.running = False
        if self.face_detector is not None:
            try:
                self.face_detector.close()
            except Exception:
                pass


class StudyDistractionDetector:
    """
    Detektor Terpadu 3 Jenis Distraksi Belajar (ESP32-S3 / Kamera):
    1. Pengguna Meninggalkan Tempat (Absence / No Person)
    2. Bermain Handphone (COCO SSD MobileNet Class 77)
    3. Kepala Menunduk (Head Down / Bowing Down via MediaPipe Face Mesh & Head Pose Pitch)
    """

    def __init__(self):
        self.coco_worker = AsyncCocoWorker()
        self.yolo_worker = AsyncYoloPhoneWorker()
        self.face_worker = AsyncFaceWorker()
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

        # ---- Deteksi HP: voting temporal ----
        # Menyimpan (timestamp, confidence) beberapa frame terakhir. Deteksi HP
        # casing hitam bersifat fluktuatif: satu frame 0.30, frame berikut 0.03.
        # Dengan voting, beberapa hit dalam jendela waktu dianggap bukti nyata,
        # sedangkan satu hit nyasar tidak langsung memicu alarm.
        self.phone_hist = deque(maxlen=120)
        self.phone_conf_latest = 0.0
        self.phone_hits = 0
        self.phone_on_counter = 0.0
        self.phone_off_counter = 0.0
        self.phone_box = None      # koordinat pada frame yang sedang diproses
        self.phone_box_size = None # ukuran frame sumber box (untuk scaling)
        self.phone_source = None
        self.latest_telemetry = {}
        
        self.last_face_seen = 0.0
        self.head_pitch = 0.0
        self.last_tick = time.time()

    def set_study_mode(self, mode: str):
        """Menyetel mode belajar: 'book' (Buku/Menulis) atau 'screen' (Layar/PC)"""
        mode_clean = str(mode).lower().strip()
        if mode_clean in ["book", "writing", "meja", "buku"]:
            self.study_mode = "book"
            self.head_down_counter = 0.0
            self.is_head_down = False
        else:
            self.study_mode = "screen"

    def process_frame(self, frame, has_hands=False, draw=True, detect_frame=None):
        """
        Menganalisis frame kamera untuk 3 distraksi belajar secara NON-BLOCKING (Ultra-Fast 30+ FPS).

        Args:
            frame: frame untuk DITAMPILKAN / dianotasi (biasanya versi enhanced/terang).
            detect_frame: frame untuk INFERENSI. Sebaiknya frame MENTAH (raw) karena
                CLAHE menurunkan skor deteksi HP. Jika None, memakai `frame`.
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
                "phone_detected": False,
                "phone_confidence": 0.0
            }

        h, w = frame.shape[:2]
        source_frame = detect_frame if detect_frame is not None else frame

        # 1. Update Async Workers (Inference AI Berjalan di Background Tanpa Menahan Video Feed)
        #    Deteksi objek & HP memakai frame MENTAH; wajah memakai frame tampilan (enhanced)
        #    agar MediaPipe lebih stabil pada gambar berkontras rendah.
        self.coco_worker.feed_frame(source_frame)
        self.yolo_worker.feed_frame(source_frame)
        self.face_worker.feed_frame(frame)

        objects, has_phone_raw, has_person_raw = self.coco_worker.get_results()
        phone_conf, phone_box = self.coco_worker.get_phone()
        phone_source = "coco" if phone_conf > 0 else None
        face_detected, head_down_instant, pitch, face_box = self.face_worker.get_results()
        self.head_pitch = pitch

        # Fusi detektor HP: ambil skor tertinggi antara COCO dan YOLOv8n.
        # Kedua model punya pola kesalahan berbeda, sehingga gabungannya lebih
        # tahan terhadap HP casing hitam / layar mati.
        yolo_conf, yolo_box, yolo_src = self.yolo_worker.get_phone()
        if yolo_conf > phone_conf:
            phone_conf, phone_box, phone_source = yolo_conf, yolo_box, f"yolo-{yolo_src}" if yolo_src else "yolo"
        has_phone_raw = bool(phone_conf > 0.0)

        if face_detected:
            self.last_face_seen = now

        # 2. Gambar Anotasi Wajah Realtime (Jika Terdeteksi)
        if draw and face_detected and face_box is not None:
            fx_min = max(0, min(w - 1, int(face_box[0] * w)))
            fy_min = max(0, min(h - 1, int(face_box[1] * h)))
            fx_max = max(0, min(w, int(face_box[2] * w)))
            fy_max = max(0, min(h, int(face_box[3] * h)))

            color = (0, 165, 255) if head_down_instant else (0, 230, 120)
            cv2.rectangle(frame, (fx_min, fy_min), (fx_max, fy_max), color, 2)
            
            label_txt = f"Wajah: {'Menunduk!' if head_down_instant else 'Tegak/Fokus'}"
            cv2.putText(frame, label_txt, (fx_min, max(20, fy_min - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

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

        # --- Distraksi 2: Mainan Handphone ---
        # Voting temporal: HP casing hitam menghasilkan skor fluktuatif, jadi kita
        # akumulasi bukti dalam jendela waktu, bukan mengandalkan 1 frame.
        self.phone_conf_latest = phone_conf
        self.phone_source = phone_source
        self.phone_hist.append((now, phone_conf))

        window = getattr(Config, "PHONE_VOTE_WINDOW_SEC", 1.8)
        while self.phone_hist and (now - self.phone_hist[0][0]) > window:
            self.phone_hist.popleft()

        conf_thr = getattr(Config, "COCO_PHONE_THRESHOLD", 0.15)
        trigger_conf = getattr(Config, "PHONE_TRIGGER_CONF", 0.30)
        min_hits = getattr(Config, "PHONE_VOTE_MIN_HITS", 2)
        on_sec = getattr(Config, "PHONE_ON_SEC", 0.4)
        off_sec = getattr(Config, "PHONE_OFF_SEC", 0.8)

        recent_confs = [c for (_t, c) in self.phone_hist]
        recent_max = max(recent_confs) if recent_confs else 0.0
        self.phone_hits = sum(1 for c in recent_confs if c >= conf_thr)
        phone_evidence = (recent_max >= trigger_conf) or (self.phone_hits >= min_hits)

        # Hysteresis dua arah: butuh on_sec bukti untuk MENYALA, dan off_sec tanpa
        # bukti untuk MATI. Ini mencegah alarm berkedip (flicker) tanpa membuat
        # status "nyangkut" ON ketika HP sudah tidak terlihat.
        if phone_evidence:
            self.phone_on_counter = min(on_sec, self.phone_on_counter + dt)
            self.phone_off_counter = 0.0
        else:
            self.phone_off_counter = min(off_sec, self.phone_off_counter + dt)
            self.phone_on_counter = max(0.0, self.phone_on_counter - dt)

        if not self.is_phone and self.phone_on_counter >= on_sec:
            self.is_phone = True
        elif self.is_phone and self.phone_off_counter >= off_sec:
            self.is_phone = False
        self.phone_counter = self.phone_on_counter

        # Simpan box untuk digambar (skalakan dari frame sumber 320x240 ke frame tampilan)
        if phone_box is not None and phone_conf >= conf_thr:
            sx = w / 320.0
            sy = h / 240.0
            self.phone_box = [
                int(phone_box[0] * sx), int(phone_box[1] * sy),
                int(phone_box[2] * sx), int(phone_box[3] * sy),
            ]
        else:
            self.phone_box = None

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

        # 5b. Kotak kandidat HP dari fusi detektor (bila belum memicu alarm)
        if draw and self.phone_box is not None and not self.is_phone:
            bx1, by1, bx2, by2 = self.phone_box
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 200, 255), 2)
            tag = f"Kandidat HP {self.phone_conf_latest:.2f}"
            cv2.putText(frame, tag, (bx1, max(14, by1 - 6)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 255), 1, cv2.LINE_AA)

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

        telemetry = {
            "is_present": not self.is_absent,
            "is_absent": self.is_absent,
            "is_phone": self.is_phone,
            "is_head_down": self.is_head_down,
            "head_pitch": self.head_pitch,
            "study_mode": self.study_mode,
            "head_down_allowed": (self.study_mode == "book"),
            "face_detected": face_detected,
            "person_detected": has_person_raw,
            "phone_detected": has_phone_raw,
            "phone_confidence": round(self.phone_conf_latest, 3),
            "phone_hits": self.phone_hits,
            "phone_source": self.phone_source,
        }
        self.latest_telemetry = telemetry
        return frame, telemetry

    def close(self):
        try:
            self.coco_worker.stop()
            self.yolo_worker.stop()
            self.face_worker.stop()
        except Exception:
            pass
