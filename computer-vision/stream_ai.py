"""
=============================================================================
ASISTEN BELAJAR AI - ESP32-S3 OV5640 STREAM PROCESSOR & HAND GESTURE TRACKING
=============================================================================
Implementasi presisi sesuai dokumen teknis "Panduan Konfigurasi Kamera ESP32-S3 (OV5640)":
1. Threaded Video Ingestion (Zero-Latency / Real-Time).
2. Image Enhancement Pipeline (Thermal Magenta Correction, CLAHE Backlight, 
   Bilateral Denoising, Sharpening Kernel).
3. Google MediaPipe Hands (21 Landmarks Skeleton & Hand Bounding Box).
4. Side-by-Side Interactive UI (Raw vs Enhanced AI) dengan hotkeys 'c', 'm', 's', 'q'.
5. Auto-reconnect handling & Auto-fallback (/capture) jika stream Wi-Fi terputus.
"""

import os
import sys
import time
import threading
import argparse
import requests
import cv2
import numpy as np

# Konfigurasi OpenCV FFmpeg: no-buffer, low-delay, dan stimeout 2 detik agar tidak hang 30 detik
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "fflags;nobuffer|flags;low_delay|stimeout;2000000|max_delay;50000"

from config import Config
from core.image_enhancer import ImageEnhancer
from core.mediapipe_detector import MediaPipeDetector

class VideoStreamThread:
    """
    Thread khusus penarikan frame agar pembacaan tidak blocking (Latency = 0).
    Mendukung MJPEG Stream, Snapshot Polling (/capture), dan Auto-Fallback.
    """
    def __init__(self, src=Config.DEFAULT_SOURCE):
        self.src = int(src) if str(src).isdigit() else str(src)
        self.is_snapshot_mode = "/capture" in str(self.src)
        self.cap = None
        self.frame = None
        self.running = True
        self.connected = False
        self.lock = threading.Lock()
        self.last_read_time = 0
        self.fps = 0.0
        self.session = requests.Session()

        if not self.is_snapshot_mode:
            self._start_capture()
        self.thread = threading.Thread(target=self._update, daemon=True)
        self.thread.start()

    def _start_capture(self):
        try:
            if self.cap is not None:
                self.cap.release()
            self.cap = cv2.VideoCapture(self.src)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                self.connected = True
            else:
                self.connected = False
        except Exception:
            self.connected = False

    def _check_and_fallback(self):
        src_str = str(self.src)
        if ":81" in src_str or "/stream" in src_str:
            base_ip = src_str.replace("http://", "").split(":")[0].split("/")[0]
            candidate_capture = f"http://{base_ip}/capture"
            try:
                res = self.session.get(candidate_capture, timeout=1.0)
                if res.status_code == 200:
                    print(f"🔄 [StreamThread] Port 81 stream offline, beralih otomatis ke: {candidate_capture}")
                    with self.lock:
                        self.src = candidate_capture
                        self.is_snapshot_mode = True
                    return True
            except Exception:
                pass
        return False

    def _update(self):
        fps_counter = 0
        fps_timer = time.time()
        failed_count = 0

        while self.running:
            if self.is_snapshot_mode:
                try:
                    res = self.session.get(str(self.src), timeout=1.5)
                    if res.status_code == 200:
                        img_arr = np.frombuffer(res.content, dtype=np.uint8)
                        frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                        if frame is not None:
                            with self.lock:
                                self.frame = frame
                                self.connected = True
                                self.last_read_time = time.time()
                            failed_count = 0
                        else:
                            self.connected = False
                    else:
                        self.connected = False
                except Exception:
                    self.connected = False
                    time.sleep(0.3)
                time.sleep(0.02)
            else:
                if self.cap is None or not self.cap.isOpened():
                    self.connected = False
                    failed_count += 1
                    if failed_count >= 2:
                        self._check_and_fallback()
                    time.sleep(1.0)
                    self._start_capture()
                    continue

                success, frame = self.cap.read()
                if success and frame is not None:
                    with self.lock:
                        self.frame = frame
                        self.connected = True
                        self.last_read_time = time.time()
                    failed_count = 0
                else:
                    self.connected = False
                    failed_count += 1
                    if failed_count >= 2:
                        self._check_and_fallback()
                    time.sleep(0.5)
                    self._start_capture()

            fps_counter += 1
            if time.time() - fps_timer >= 1.0:
                self.fps = round(fps_counter / (time.time() - fps_timer), 1)
                fps_counter = 0
                fps_timer = time.time()

    def read(self):
        with self.lock:
            if self.frame is not None and (time.time() - self.last_read_time < 3.0):
                return self.connected, self.frame.copy()
            return False, None

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()

def create_offline_placeholder(message="Menghubungkan ke ESP32..."):
    """Placeholder gelap modern saat kamera sedang menyambung kembali"""
    frame = np.zeros((300, 400, 3), dtype=np.uint8)
    frame[:] = (24, 28, 38)
    cv2.putText(frame, "ESP32-S3 OV5640 STREAM", (40, 120),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (140, 160, 180), 2, cv2.LINE_AA)
    cv2.putText(frame, message, (35, 170),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2, cv2.LINE_AA)
    cv2.putText(frame, "Auto-reconnecting...", (110, 220),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 120, 160), 1, cv2.LINE_AA)
    return frame

def main():
    parser = argparse.ArgumentParser(description="ESP32-S3 High-FPS Stream Processor & AI Hand Tracking")
    parser.add_argument("--source", type=str, default=Config.DEFAULT_SOURCE,
                        help="Stream URL atau device index webcam (misal: http://192.168.1.12/capture atau 0)")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("🚀 MEMULAI ESP32-S3 OV5640 STREAM PROCESSOR & AI GESTURE")
    print(f"📡 Video Source  : {args.source}")
    print("⌨️  Shortcut Keys:")
    print("    [c] : Toggle ON/OFF Image Enhancement (CLAHE + Denoise + Sharpen)")
    print("    [m] : Toggle ON/OFF MediaPipe 21 Landmarks Visualizer")
    print("    [s] : Toggle Side-by-Side View vs Single AI View")
    print("    [q] : Keluar dari program secara aman")
    print("=" * 65 + "\n")

    stream_thread = VideoStreamThread(args.source)
    enhancer = ImageEnhancer(enabled=True)
    detector = MediaPipeDetector()

    show_side_by_side = True
    process_fps = 0.0
    frame_count = 0
    t_start = time.time()

    window_name = "Asisten Belajar - ESP32 Stream AI (OV5640)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    try:
        while True:
            connected, raw_frame = stream_thread.read()

            if not connected or raw_frame is None:
                raw_frame = create_offline_placeholder()
                enhanced_frame = raw_frame.copy()
            else:
                # 1. Image Enhancement Pipeline
                if enhancer.enabled:
                    enhanced_frame = enhancer.enhance(raw_frame)
                else:
                    enhanced_frame = raw_frame.copy()

                # 2. MediaPipe Hand Tracking & Gestur
                if detector.enabled:
                    enhanced_frame, _, _, _ = detector.process_frame(enhanced_frame, draw=True)

            # Hitung FPS Processing Python
            frame_count += 1
            if time.time() - t_start >= 1.0:
                process_fps = round(frame_count / (time.time() - t_start), 1)
                frame_count = 0
                t_start = time.time()

            # Render Overlay HUD pada Enhanced Frame
            h, w = enhanced_frame.shape[:2]
            status_color = (0, 255, 120) if connected else (0, 0, 255)
            conn_txt = "CONNECTED" if connected else "CONNECTING..."
            
            # Bar status atas
            cv2.putText(enhanced_frame, f"Python FPS: {process_fps} | Stream: {stream_thread.fps} FPS", (15, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(enhanced_frame, f"ESP32: {conn_txt}", (w - 180, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 2, cv2.LINE_AA)

            # Bar status bawah (Hotkeys & Filter indicator)
            enh_status = "ON (CLAHE+Denoise+Sharp)" if enhancer.enabled else "OFF (Raw)"
            mp_status = "ON (21 Joints)" if detector.enabled else "OFF"
            bottom_txt = f"[c] Enhancer: {enh_status} | [m] AI: {mp_status} | [s] Side-by-Side: {'ON' if show_side_by_side else 'OFF'}"
            cv2.putText(enhanced_frame, bottom_txt, (15, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 220, 240), 1, cv2.LINE_AA)

            # Buat Tampilan Layar (Side-by-Side vs Single)
            if show_side_by_side:
                raw_resized = cv2.resize(raw_frame, (w, h))
                cv2.putText(raw_resized, "ORIGINAL RAW ESP32", (15, 25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 255), 2, cv2.LINE_AA)
                cv2.putText(raw_resized, "[Tanpa Filter Sisi ESP32]", (15, 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 170, 190), 1, cv2.LINE_AA)
                display_frame = np.hstack([raw_resized, enhanced_frame])
            else:
                display_frame = enhanced_frame

            cv2.imshow(window_name, display_frame)

            # Tangani Keyboard Shortcut
            key = cv2.waitKey(1) & 0xFF
            if key == ord('q'):
                print("👋 Menutup aplikasi...")
                break
            elif key == ord('c'):
                enhancer.enabled = not enhancer.enabled
                print(f"🔄 Image Enhancement diubah: {'AKTIF' if enhancer.enabled else 'NONAKTIF'}")
            elif key == ord('m'):
                detector.enabled = not detector.enabled
                print(f"🔄 MediaPipe AI diubah: {'AKTIF' if detector.enabled else 'NONAKTIF'}")
            elif key == ord('s'):
                show_side_by_side = not show_side_by_side
                print(f"🔄 Side-by-side view: {'AKTIF' if show_side_by_side else 'NONAKTIF (Full AI)'}")

    finally:
        stream_thread.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
