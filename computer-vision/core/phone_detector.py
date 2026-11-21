import os
import cv2
import numpy as np

from config import Config


class YoloPhoneDetector:
    """
    Detektor HP sekunder berbasis YOLOv8n (ONNX) — dijalankan lewat OpenCV DNN
    sehingga tidak butuh PyTorch / ultralytics.

    Mengapa perlu detektor kedua?
    - SSD-MobileNet COCO dan YOLO sama-sama paling mudah mengenali HP saat
      LAYAR menyala. Saat user memegang HP normal (layar menghadap dirinya),
      kamera hanya melihat punggung HP yang hitam.
    - Dua model memiliki pola kesalahan berbeda. Menggabungkan skor keduanya
      (fusi max) meningkatkan peluang salah satu "melihat" HP.
    - Selain frame penuh, detektor juga memeriksa crop bagian bawah frame
      (area tipikal HP dipegang/diletakkan) dengan upscale, agar objek kecil
      menjadi lebih terlihat oleh model.
    """

    # Indeks kelas "cell phone" pada COCO 80-kelas (0-based).
    PHONE_CLASS_ID = 67

    def __init__(self, model_path=None, conf_thresh=Config.PHONE_YOLO_CONF, input_size=640):
        self.conf_thresh = conf_thresh
        self.input_size = input_size
        self.net = None
        self.enabled = False

        if model_path is None:
            model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "model", "yolov8n.onnx")

        if os.path.exists(model_path):
            try:
                self.net = cv2.dnn.readNetFromONNX(model_path)
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.enabled = True
                print("✅ [YoloPhoneDetector] YOLOv8n ONNX siap (detektor HP sekunder).", flush=True)
            except Exception as e:
                print(f"⚠️ [YoloPhoneDetector] Gagal memuat model: {e}", flush=True)
        else:
            print(f"ℹ️ [YoloPhoneDetector] Model tidak ditemukan ({model_path}); lewati detektor sekunder.", flush=True)

    def _infer_letterbox(self, image):
        """Jalankan YOLOv8n pada satu gambar. Kembalikan (conf_max, box) dalam koordinat gambar asli."""
        h0, w0 = image.shape[:2]
        if h0 < 8 or w0 < 8:
            return 0.0, None

        size = self.input_size
        r = min(size / h0, size / w0)
        nw, nh = int(w0 * r), int(h0 * r)
        canvas = np.full((size, size, 3), 114, np.uint8)
        dw, dh = (size - nw) // 2, (size - nh) // 2
        canvas[dh:dh + nh, dw:dw + nw] = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_LINEAR)

        blob = cv2.dnn.blobFromImage(canvas, 1 / 255.0, (size, size), swapRB=True, crop=False)
        self.net.setInput(blob)
        out = self.net.forward()[0]  # (84, N)
        if out.ndim != 2:
            return 0.0, None

        # Ultralytics YOLOv8 export: (84, 8400) -> transpose ke (N, 84)
        if out.shape[0] < out.shape[1]:
            out = out.T

        scores = out[:, 4:]
        if scores.shape[1] <= self.PHONE_CLASS_ID:
            return 0.0, None

        class_scores = scores[:, self.PHONE_CLASS_ID]
        idx = int(np.argmax(class_scores))
        best = float(class_scores[idx])
        if best < self.conf_thresh:
            return best, None

        cx, cy, bw, bh = out[idx, :4]
        x1 = (cx - bw / 2 - dw) / r
        y1 = (cy - bh / 2 - dh) / r
        x2 = (cx + bw / 2 - dw) / r
        y2 = (cy + bh / 2 - dh) / r
        box = [
            int(max(0, min(w0 - 1, x1))),
            int(max(0, min(h0 - 1, y1))),
            int(max(0, min(w0, x2))),
            int(max(0, min(h0, y2))),
        ]
        return best, box

    def score(self, frame):
        """
        Kembalikan (confidence, box, source) terbaik dari:
          - frame penuh
          - crop bagian bawah (tempat HP biasanya dipegang)
        `box` selalu dalam koordinat frame asli.
        """
        if not self.enabled or self.net is None or frame is None:
            return 0.0, None, None

        best_conf, best_box, best_src = 0.0, None, None

        try:
            conf, box = self._infer_letterbox(frame)
            if conf > best_conf:
                best_conf, best_box, best_src = conf, box, "full"
        except Exception:
            pass

        # Crop bagian bawah frame (55%-100% tinggi), upscale 1.5x agar HP lebih besar.
        try:
            h, w = frame.shape[:2]
            y0 = int(h * 0.45)
            bottom = frame[y0:h, :]
            if bottom.size > 0:
                bottom_up = cv2.resize(
                    bottom, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC
                )
                conf, box = self._infer_letterbox(bottom_up)
                if conf > best_conf and box is not None:
                    # Kembalikan koordinat ke frame asli
                    bx1, by1, bx2, by2 = box
                    best_conf = conf
                    best_box = [
                        int(bx1 / 1.5),
                        int(by1 / 1.5) + y0,
                        int(bx2 / 1.5),
                        int(by2 / 1.5) + y0,
                    ]
                    best_src = "bottom"
        except Exception:
            pass

        return best_conf, best_box, best_src
