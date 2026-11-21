import os
import cv2
import numpy as np
from config import Config

class CocoDetector:
    """
    Deteksi objek meja belajar (Orang, Laptop, Buku, HP) menggunakan
    SSD MobileNet V2 COCO melalui OpenCV DNN.
    """
    def __init__(self, pb_path=Config.MODEL_PB, pbtxt_path=Config.MODEL_PBTXT,
                 conf_thresh=Config.COCO_CONFIDENCE_THRESHOLD,
                 phone_thresh=Config.COCO_PHONE_THRESHOLD):
        self.conf_thresh = conf_thresh
        # Ambang khusus kelas "cell phone" (77). Lebih rendah dari objek lain karena
        # HP casing hitam / layar mati hanya menghasilkan skor rendah yang fluktuatif.
        self.phone_thresh = phone_thresh
        self.net = None
        self.labels = Config.COCO_LABELS
        self.enabled = True

        if os.path.exists(pb_path) and os.path.exists(pbtxt_path):
            try:
                self.net = cv2.dnn.readNetFromTensorflow(pb_path, pbtxt_path)
                # Gunakan OpenCL acceleration jika tersedia
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                print("✅ [CocoDetector] Model SSD MobileNet COCO berhasil dimuat.")
            except Exception as e:
                print(f"⚠️ [CocoDetector] Gagal memuat model COCO: {e}")
        else:
            print(f"⚠️ [CocoDetector] File model tidak ditemukan di: {pb_path}")

    def process_frame(self, frame, draw=True):
        """
        Mendeteksi objek pada frame dan menggambar bounding box.
        Mengembalikan: (frame_annotated, detected_objects_list, has_phone)
        """
        if self.net is None or not self.enabled or frame is None:
            return frame, [], False

        h, w = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (300, 300)), swapRB=True, crop=False)
        self.net.setInput(blob)
        detections = self.net.forward()

        detected_objects = []
        has_phone = False
        has_person = False

        for i in range(detections.shape[2]):
            confidence = float(detections[0, 0, i, 2])
            class_id = int(detections[0, 0, i, 1])
            # Ambang per-kelas: kelas HP (77) memakai ambang lebih rendah agar HP
            # casing hitam / layar mati tetap tertangkap (difilter lagi oleh voting temporal).
            threshold = self.phone_thresh if class_id == 77 else self.conf_thresh
            if confidence > threshold:
                if class_id in self.labels:
                    label_name = self.labels[class_id]
                    is_distraction = (class_id == 77) # Cell Phone
                    is_person = (class_id == 1)       # Person

                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")

                    # Validasi koordinat batas frame
                    startX = max(0, startX)
                    startY = max(0, startY)
                    endX = min(w, endX)
                    endY = min(h, endY)

                    if is_distraction:
                        has_phone = True
                    if is_person:
                        has_person = True

                    detected_objects.append({
                        "label": label_name,
                        "class_id": class_id,
                        "confidence": round(confidence, 3),
                        "box": [startX, startY, endX, endY],
                        "is_distraction": is_distraction,
                        "is_person": is_person
                    })

                    if draw:
                        # Warna: Merah untuk HP distraksi, Cyan/Emerald untuk objek belajar, Biru untuk Person
                        if is_distraction:
                            color = (0, 0, 245) # Merah
                        elif is_person:
                            color = (255, 180, 0) # Biru/Gold
                        else:
                            color = (0, 220, 130) # Emerald
                        
                        # Kotak Bounding Box dengan ketebalan modern
                        cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
                        
                        # Label background badge
                        tag = f"{label_name} ({int(confidence * 100)}%)"
                        (text_w, text_h), baseline = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
                        badge_y1 = max(0, startY - text_h - 8)
                        badge_y2 = startY
                        cv2.rectangle(frame, (startX, badge_y1), (startX + text_w + 10, badge_y2), color, -1)
                        cv2.putText(frame, tag, (startX + 5, badge_y2 - 4),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

        return frame, detected_objects, has_phone, has_person
