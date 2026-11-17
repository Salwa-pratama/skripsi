import os
import cv2
import time
import threading
import urllib.request
import numpy as np
import requests
from config import Config
from core.image_enhancer import ImageEnhancer

# OpenCV FFmpeg flags
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "fflags;nobuffer|flags;low_delay|stimeout;2000000|max_delay;50000"

class CameraStreamer:
    """
    Mengelola penarikan frame dari ESP32-S3 dengan performa maksimal (30+ FPS):
    1. Direct MJPEG Chunk Streamer (4KB low-latency chunks) - anti-stutter, video mulus.
    2. Auto-tuning resolusi ESP32 (VGA 640x480 & high quality JPEG).
    3. Auto-fallback ke Snapshot Mode (/capture) jika port 81 sedang dikunci oleh browser tab lain.
    4. Frame-ID synchronizer untuk pengiriman zero-duplicate ke browser via /video_feed.
    """
    def __init__(self, source=None):
        self.source = source if source is not None else Config.DEFAULT_SOURCE
        self.lock = threading.Lock()
        self.running = True
        self.connected = False
        self.last_frame_time = 0
        self.fps = 0.0
        self.port81_blocked = False
        
        self.latest_raw_frame = None
        self.latest_enhanced_frame = None
        self.latest_processed_frame = None
        self.latest_jpeg = None
        self.processed_frame_id = 0
        
        # Pipeline Image Enhancement (default nonaktif agar warna alami & bebas noise, bisa diaktifkan via checkbox)
        self.enhancer = ImageEnhancer(
            enabled=False,
            clahe_enabled=True,
            denoise_enabled=False,
            sharpen_enabled=True,
            thermal_correction_enabled=False
        )

        self.is_snapshot_mode = "/capture" in str(self.source)
        self.cap = None
        self.http_session = requests.Session()
        
        # Inisialisasi konfigurasi kamera ESP32 jika target adalah ESP32
        ip = self._source_ip()
        if ip:
            threading.Thread(target=self.tune_esp_camera, args=(ip, 10, 10), daemon=True).start()

        self.thread = threading.Thread(target=self._capture_worker, daemon=True)
        self.thread.start()

    def _source_ip(self):
        """Ambil IP host dari URL stream, mis. http://10.38.39.50:81/stream -> 10.38.39.50."""
        src = str(self.source)
        if src.startswith("http://") or src.startswith("https://"):
            try:
                return src.split("://", 1)[1].split(":")[0].split("/")[0]
            except Exception:
                return None
        return None

    def tune_esp_camera(self, ip="192.168.1.12", framesize=10, quality=10):
        """
        Mengonfigurasi sensor OV5640 pada ESP32:
        - framesize: 10 (VGA 640x480) - tajam dan ideal untuk MediaPipe
        - quality: 10 (High quality JPEG, menghilangkan artefak pecah/kotak-kotak)
        """
        try:
            requests.get(f"http://{ip}/control?var=framesize&val={framesize}", timeout=1.5)
            requests.get(f"http://{ip}/control?var=quality&val={quality}", timeout=1.5)
            print(f"✅ [CameraStreamer] Sensor ESP32 berhasil disetel ke VGA 640x480 (Quality: {quality})", flush=True)
        except Exception:
            pass

    def set_source(self, new_source):
        """Mengganti sumber video secara dinamis"""
        with self.lock:
            if str(new_source).isdigit():
                self.source = int(new_source)
            else:
                self.source = str(new_source).strip()
            
            self.is_snapshot_mode = "/capture" in str(self.source)
            self.connected = False
            self.port81_blocked = False
            
            if self.cap is not None:
                try:
                    self.cap.release()
                except Exception:
                    pass
                self.cap = None

        ip = self._source_ip()
        if ip:
            threading.Thread(target=self.tune_esp_camera, args=(ip, 10, 10), daemon=True).start()

    def _create_placeholder_frame(self, message="Menghubungkan ke ESP32..."):
        """Frame standby gelap modern"""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (20, 24, 33)

        cv2.putText(frame, "ESP32-S3 OV5640 VISION STREAM", (120, 180),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, message, (130, 240),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 165, 255), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Source: {self.source}", (140, 290),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (140, 150, 170), 1, cv2.LINE_AA)
        
        if self.port81_blocked:
            ip = self._source_ip() or "ESP32"
            cv2.putText(frame, f"PERINGATAN: Tutup tab http://{ip}/ di Chrome!", (80, 340),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 100, 255), 2, cv2.LINE_AA)
            cv2.putText(frame, "ESP32 hanya mengizinkan 1 koneksi stream pada port 81.", (90, 370),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (160, 180, 200), 1, cv2.LINE_AA)
        return frame

    def _read_direct_mjpeg(self, url):
        """
        Pembaca MJPEG byte-stream langsung via HTTP (30+ FPS & Low Latency).
        Menggunakan pembacaan chunk kecil (4096 bytes) tanpa blocking buffer besar sehingga video mengalir mulus tanpa patah-patah.
        """
        req = None
        try:
            req = urllib.request.urlopen(url, timeout=3.0)
            bytes_buf = bytearray()
            self.port81_blocked = False
            
            while self.running and not self.is_snapshot_mode:
                chunk = req.read(4096)
                if not chunk:
                    break
                bytes_buf.extend(chunk)

                # Jika buffer tertimbun terlalu banyak, lompat langsung ke frame terbaru
                if len(bytes_buf) > 65536:
                    last_start = bytes_buf.rfind(b'\xff\xd8')
                    if last_start != -1:
                        bytes_buf = bytes_buf[last_start:]

                a = bytes_buf.find(b'\xff\xd8')
                b = bytes_buf.find(b'\xff\xd9', a + 2) if a != -1 else -1

                if a != -1 and b != -1:
                    jpg = bytes_buf[a:b+2]
                    bytes_buf = bytes_buf[b+2:]

                    frame = cv2.imdecode(np.frombuffer(jpg, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        enhanced = self.enhancer.enhance(frame) if self.enhancer.enabled else frame
                        with self.lock:
                            self.latest_raw_frame = frame
                            self.latest_enhanced_frame = enhanced
                            self.connected = True
                            self.last_frame_time = time.time()
        finally:
            if req is not None:
                try:
                    req.close()
                except Exception:
                    pass

    def _capture_worker(self):
        fps_counter = 0
        fps_timer = time.time()
        last_recovery_check = 0

        while self.running:
            try:
                src_str = str(self.source)

                # 1. Mode Direct MJPEG Stream (misal http://192.168.1.12:81/stream)
                if src_str.startswith("http://") and ":81" in src_str:
                    try:
                        self._read_direct_mjpeg(src_str)
                    except Exception as e:
                        self.connected = False
                        self.port81_blocked = True
                        ip = self._source_ip() or "ESP32"
                        print(f"⚠️ [CameraStreamer] Stream ESP32 tidak bisa dibuka (cek IP/jaringan atau tutup tab http://{ip}/ di Chrome).", flush=True)
                        
                        # Fallback sementara ke /capture agar tidak blank
                        base_ip = src_str.replace("http://", "").split(":")[0].split("/")[0]
                        fallback_url = f"http://{base_ip}/capture"
                        try:
                            res = self.http_session.get(fallback_url, timeout=1.0)
                            if res.status_code == 200:
                                with self.lock:
                                    self.source = fallback_url
                                    self.is_snapshot_mode = True
                        except Exception:
                            pass
                        time.sleep(1.0)

                # 2. Mode Snapshot Polling (/capture)
                elif self.is_snapshot_mode:
                    try:
                        res = self.http_session.get(src_str, timeout=1.2)
                        if res.status_code == 200:
                            img_arr = np.frombuffer(res.content, dtype=np.uint8)
                            frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                            if frame is not None:
                                enhanced = self.enhancer.enhance(frame) if self.enhancer.enabled else frame
                                with self.lock:
                                    self.latest_raw_frame = frame
                                    self.latest_enhanced_frame = enhanced
                                    self.connected = True
                                    self.last_frame_time = time.time()
                            else:
                                self.connected = False
                        else:
                            self.connected = False
                    except Exception:
                        self.connected = False
                        time.sleep(0.3)
                    
                    # Cek berkala apakah port 81 sudah bebas dari Chrome (setiap 3 detik)
                    now = time.time()
                    ip = self._source_ip()
                    if ip and (now - last_recovery_check > 3.0):
                        last_recovery_check = now
                        t_stream = None
                        try:
                            stream_url = f"http://{ip}:81/stream"
                            t_stream = urllib.request.urlopen(stream_url, timeout=1.0)
                            print("🚀 [CameraStreamer] Port 81 stream telah bebas! Beralih kembali ke High-Speed Stream.", flush=True)
                            with self.lock:
                                self.source = stream_url
                                self.is_snapshot_mode = False
                                self.port81_blocked = False
                        except Exception:
                            pass
                        finally:
                            if t_stream is not None:
                                try:
                                    t_stream.close()
                                except Exception:
                                    pass

                    time.sleep(0.01)

                # 3. Mode OpenCV VideoCapture (Webcam Lokal index 0 atau file video)
                else:
                    if self.cap is None or not self.cap.isOpened():
                        self.cap = cv2.VideoCapture(self.source)
                        if self.cap.isOpened():
                            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                        else:
                            self.connected = False
                            time.sleep(1.0)
                            continue

                    success, frame = self.cap.read()
                    if success and frame is not None:
                        enhanced = self.enhancer.enhance(frame) if self.enhancer.enabled else frame
                        with self.lock:
                            self.latest_raw_frame = frame
                            self.latest_enhanced_frame = enhanced
                            self.connected = True
                            self.last_frame_time = time.time()
                    else:
                        self.connected = False
                        time.sleep(0.4)
                        if self.cap is not None:
                            self.cap.release()
                            self.cap = None

            except Exception:
                self.connected = False
                time.sleep(0.5)

            # Hitung FPS real-time
            fps_counter += 1
            now = time.time()
            if now - fps_timer >= 1.0:
                self.fps = round(fps_counter / (now - fps_timer), 1)
                fps_counter = 0
                fps_timer = now

    def get_raw_frame(self):
        with self.lock:
            if self.latest_raw_frame is not None and (time.time() - self.last_frame_time < 3.0):
                return self.latest_raw_frame.copy()
            return self._create_placeholder_frame("Menghubungkan ke ESP32...")

    def get_enhanced_frame(self):
        with self.lock:
            if self.latest_enhanced_frame is not None and (time.time() - self.last_frame_time < 3.0):
                return self.latest_enhanced_frame.copy()
            elif self.latest_raw_frame is not None and (time.time() - self.last_frame_time < 3.0):
                return self.enhancer.enhance(self.latest_raw_frame) if self.enhancer.enabled else self.latest_raw_frame.copy()
            return self._create_placeholder_frame("Menghubungkan ke ESP32...")

    def update_processed_frame(self, frame):
        with self.lock:
            self.latest_processed_frame = frame
            ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if ret:
                self.latest_jpeg = buf.tobytes()
                self.processed_frame_id += 1

    def get_latest_frame_with_id(self):
        with self.lock:
            return self.processed_frame_id, self.latest_jpeg

    def get_jpeg(self):
        with self.lock:
            if self.latest_jpeg is not None:
                return self.latest_jpeg
            placeholder = self._create_placeholder_frame()
            ret, buf = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return buf.tobytes() if ret else None

    def get_status(self):
        return {
            "source": str(self.source),
            "connected": self.connected and (time.time() - self.last_frame_time < 3.0),
            "fps": self.fps,
            "mode": "snapshot" if self.is_snapshot_mode else "stream",
            "port81_blocked": self.port81_blocked,
            "enhancer": {
                "enabled": self.enhancer.enabled,
                "clahe": self.enhancer.clahe_enabled,
                "denoise": self.enhancer.denoise_enabled,
                "sharpen": self.enhancer.sharpen_enabled,
                "thermal_correction": self.enhancer.thermal_correction_enabled
            }
        }

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
