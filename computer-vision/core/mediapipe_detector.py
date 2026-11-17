import os
import sys
import time
import cv2
import numpy as np

try:
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    HAS_MEDIAPIPE = True
except ImportError:
    HAS_MEDIAPIPE = False
    print("⚠️ [MediaPipeDetector] Library mediapipe belum terinstall.", flush=True)

class MediaPipeDetector:
    """
    Detector AI Murni Hand Tracking (MediaPipe Hands - 21 Sendi Jari).
    Fitur:
    1. Real-time 21 landmark sendi jari tangan berkecepatan tinggi (30+ FPS).
    2. EMA Temporal Smoothing untuk koordinat sendi agar mulus tanpa tremor/jitter.
    3. Visualisasi modern nan elegan (Garis Neon Cyan, Sendi Emas, Ujung Jari Aksen).
    """
    # 21 Landmark Hand Skeleton Connections
    HAND_CONNECTIONS = [
        (0, 1), (1, 2), (2, 3), (3, 4),        # Jempol (Thumb)
        (0, 5), (5, 6), (6, 7), (7, 8),        # Jari Telunjuk (Index)
        (5, 9), (9, 10), (10, 11), (11, 12),   # Jari Tengah (Middle)
        (9, 13), (13, 14), (14, 15), (15, 16), # Jari Manis (Ring)
        (13, 17), (17, 18), (18, 19), (19, 20),# Kelingking (Pinky)
        (0, 17)                                # Telapak (Palm Base)
    ]

    def __init__(self, **kwargs):
        self.enabled = True
        self.hands_enabled = True
        self.face_enabled = False
        self.latest_hands_info = []
        self.detector = None
        self.prev_coords = {}  # Cache untuk EMA smoothing per tangan
        self.last_seen_time = 0

        if HAS_MEDIAPIPE:
            self._init_models()

    def _init_models(self):
        """Inisialisasi HandLandmarker (Simple 21 Sendi Tangan)"""
        model_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model")
        hand_model_path = os.path.join(model_dir, "hand_landmarker.task")

        print("⏳ [MediaPipeDetector] Memuat model MediaPipe Hand Tracking (21 Sendi)...", flush=True)

        if os.path.exists(hand_model_path):
            try:
                base_options = python.BaseOptions(model_asset_path=hand_model_path)
                options = vision.HandLandmarkerOptions(
                    base_options=base_options,
                    num_hands=2,
                    min_hand_detection_confidence=0.65,
                    min_hand_presence_confidence=0.60,
                    min_tracking_confidence=0.60
                )
                self.detector = vision.HandLandmarker.create_from_options(options)
                print("✅ [MediaPipeDetector] MediaPipe Hand Tracking (21 Sendi) Siap Digunakan (High-Precision Confidence 0.65)!", flush=True)
            except Exception as e:
                print(f"⚠️ [MediaPipeDetector] Gagal memuat HandLandmarker: {e}", flush=True)
        else:
            print(f"⚠️ [MediaPipeDetector] File model {hand_model_path} tidak ditemukan.", flush=True)

    def draw_hand_skeleton(self, frame, hand_landmarks, handedness="Tangan", hand_idx=0):
        """
        Menggambar kerangka 21 landmark sendi jari tangan dengan smoothing visual dan efek neon.
        """
        h, w = frame.shape[:2]
        raw_coords = []
        for lm in hand_landmarks:
            cx = max(0, min(w - 1, int(lm.x * w)))
            cy = max(0, min(h - 1, int(lm.y * h)))
            raw_coords.append((cx, cy))

        # Exponential Moving Average (EMA) Smoothing untuk gerakan mulus
        coords = []
        hand_key = f"{handedness}_{hand_idx}"
        if hand_key in self.prev_coords and len(self.prev_coords[hand_key]) == len(raw_coords):
            for i, (cx, cy) in enumerate(raw_coords):
                px, py = self.prev_coords[hand_key][i]
                sx = int(0.75 * cx + 0.25 * px)
                sy = int(0.75 * cy + 0.25 * py)
                coords.append((sx, sy))
        else:
            coords = raw_coords
        self.prev_coords[hand_key] = coords

        # 1. Garis Tulang Sendi Jari (Neon Cyan-Gold)
        bone_color = (0, 230, 255)
        for p1, p2 in self.HAND_CONNECTIONS:
            cv2.line(frame, coords[p1], coords[p2], bone_color, 2, cv2.LINE_AA)

        # 2. Titik Sendi
        for i, (cx, cy) in enumerate(coords):
            # Ujung jari: aksen oranye terang dengan cincin putih
            if i in [4, 8, 12, 16, 20]:
                cv2.circle(frame, (cx, cy), 5, (0, 140, 255), -1, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 7, (255, 255, 255), 1, cv2.LINE_AA)
            elif i == 0:
                # Pergelangan tangan
                cv2.circle(frame, (cx, cy), 6, (255, 180, 0), -1, cv2.LINE_AA)
                cv2.circle(frame, (cx, cy), 8, (255, 255, 255), 1, cv2.LINE_AA)
            else:
                # Sendi biasa
                cv2.circle(frame, (cx, cy), 3, (0, 255, 160), -1, cv2.LINE_AA)

        # 3. Bounding Box & Label Handedness
        x_pts = [p[0] for p in coords]
        y_pts = [p[1] for p in coords]
        x_min, x_max = max(0, min(x_pts) - 15), min(w, max(x_pts) + 15)
        y_min, y_max = max(0, min(y_pts) - 15), min(h, max(y_pts) + 15)

        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), (0, 200, 255), 2)
        
        tag_text = f"{handedness} (21 Joints)"
        (tw, th), _ = cv2.getTextSize(tag_text, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        tag_y = max(th + 10, y_min - 8)
        cv2.rectangle(frame, (x_min, tag_y - th - 6), (x_min + tw + 10, tag_y + 4), (20, 24, 30), -1)
        cv2.rectangle(frame, (x_min, tag_y - th - 6), (x_min + tw + 10, tag_y + 4), (0, 200, 255), 1)
        cv2.putText(frame, tag_text, (x_min + 5, tag_y - 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

    def process_frame(self, frame, draw=True):
        """
        Memproses frame untuk tracking 21 sendi jari tangan.
        Mengembalikan: (frame_annotated, has_hands, hands_info, has_hands)
        """
        if not HAS_MEDIAPIPE or not self.enabled or frame is None or self.detector is None:
            return frame, False, [], False

        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        hands_info = []
        raw_lms = []
        try:
            res = self.detector.detect(mp_image)
            if res and res.hand_landmarks:
                self.last_seen_time = time.time()
                for i, landmarks in enumerate(res.hand_landmarks):
                    handedness = "Hand"
                    conf_score = 1.0
                    if i < len(res.handedness) and res.handedness[i]:
                        handedness = res.handedness[i][0].category_name
                        conf_score = float(res.handedness[i][0].score)

                    # Filter 1: Minimal confidence score 0.60 (mencegah fitur wajah terdeteksi sebagai tangan)
                    if conf_score < 0.60:
                        continue

                    # Filter 2: Verifikasi Anatomi Tangan (Jarak Pergelangan Tangan [0] ke Pangkal Jari Tengah [9])
                    # Pada false-positive di wajah, landmark 0 dan 9 sering kali tidak memiliki orientasi tangan yang valid
                    p_wrist = landmarks[0]
                    p_mcp = landmarks[9]
                    palm_dist_sq = (p_mcp.x - p_wrist.x) ** 2 + (p_mcp.y - p_wrist.y) ** 2
                    if palm_dist_sq < 0.0005:  # Terlalu rapat/mikro noise
                        continue

                    raw_lms.append(landmarks)
                    hands_info.append({
                        "handedness": handedness,
                        "gesture": f"{handedness} (Terlacak)",
                        "raw_gesture": handedness,
                        "confidence": round(conf_score, 2)
                    })

                    if draw:
                        self.draw_hand_skeleton(frame, landmarks, handedness, hand_idx=len(hands_info)-1)
            else:
                # Bersihkan cache koordinat jika tangan hilang lebih dari 0.5 detik
                if time.time() - self.last_seen_time > 0.5:
                    self.prev_coords.clear()

        except Exception:
            pass

        self.latest_raw_landmarks = raw_lms
        self.latest_hands_info = hands_info
        has_hands = len(hands_info) > 0

        if draw and has_hands:
            summary_txt = f"Hands: {len(hands_info)} Terlacak (21 Sendi)"
            cv2.putText(frame, summary_txt, (15, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 220, 255), 2, cv2.LINE_AA)

        return frame, has_hands, hands_info, has_hands

    def get_hands_status(self):
        return {
            "count": len(self.latest_hands_info),
            "hands": self.latest_hands_info
        }

    def close(self):
        try:
            if self.detector is not None:
                self.detector.close()
                self.detector = None
        except Exception:
            pass
