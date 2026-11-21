import cv2
import numpy as np

class ImageEnhancer:
    """
    Pipeline Image Enhancement khusus kamera OV5640 pada ESP32-S3.
    Mengatasi:
    1. Semburat merah/magenta akibat thermal gradient & dark current (>50°C).
    2. Wajah/tangan gelap akibat backlight silau (Black Crush) menggunakan CLAHE.
    3. Noise bintik-bintik sensor panas menggunakan Bilateral Filter (edge-preserving).
    4. Kontur jari tangan yang pudar menggunakan Unsharp Masking / Sharpening Kernel.
    """
    def __init__(self, 
                 enabled=True, 
                 clahe_enabled=True, 
                 denoise_enabled=False, 
                 sharpen_enabled=True,
                 thermal_correction_enabled=False):
        self.enabled = enabled
        self.clahe_enabled = clahe_enabled
        self.denoise_enabled = denoise_enabled # Default False untuk menjaga 30+ FPS
        self.sharpen_enabled = sharpen_enabled
        self.thermal_correction_enabled = thermal_correction_enabled

        # CLAHE optimizer pada kanal L (Luminance) - nilai optimal untuk menerangkan wajah & tangan di kondisi redup
        self.clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(8, 8))
        self.gamma_lut = np.array([int(((i / 255.0) ** 0.8) * 255) for i in range(256)], dtype=np.uint8)

        # Sharpening kernel lembut untuk menjaga ketajaman tanpa membuat gambar pecah/bintik
        self.sharpen_kernel = np.array([
            [0, -0.2, 0],
            [-0.2, 1.8, -0.2],
            [0, -0.2, 0]
        ], dtype=np.float32)

    def correct_thermal_magenta(self, frame):
        """
        Meredam semburat magenta/merah termal akibat sensor OV5640 yang panas.
        Menggunakan koreksi white-balance lembut dan pelemahan channel merah jika dominan.
        """
        if frame is None:
            return frame

        # Hitung mean kanal warna B, G, R
        b_mean, g_mean, r_mean = cv2.mean(frame)[:3]

        # Jika kanal R secara signifikan lebih tinggi dari G (indikasi thermal magenta)
        if r_mean > (g_mean * 1.08) and g_mean > 10:
            scale_r = g_mean / (r_mean + 1e-5)
            # Batasi skala agar tidak membuat gambar menjadi hijau/pucat
            scale_r = max(0.85, min(0.98, scale_r))
            
            # Pisahkan channel, redam R
            b, g, r = cv2.split(frame)
            r = cv2.multiply(r, scale_r)
            return cv2.merge([b, g, r])

        return frame

    def apply_clahe(self, frame):
        """
        Koreksi Backlight & Black Crush secara adaptif.
        Menerangkan area gelap (tangan/wajah) tanpa membuat latar belakang putih/lampu overexposed.
        """
        if frame is None:
            return frame

        # Konversi ke ruang warna LAB
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)

        # Terapkan shadow lift LUT dan CLAHE pada kanal L (Luminance)
        l_lifted = cv2.LUT(l, self.gamma_lut)
        l_enhanced = self.clahe.apply(l_lifted)

        # Gabungkan kembali dan ubah ke BGR
        lab_enhanced = cv2.merge([l_enhanced, a, b])
        return cv2.cvtColor(lab_enhanced, cv2.COLOR_LAB2BGR)

    def apply_bilateral_denoise(self, frame):
        """
        Menghaluskan noise bintik termal sensor OV5640 dengan tetap
        mempertahankan ketajaman garis tepi jari tangan (edge-preserving).
        """
        if frame is None:
            return frame
        # Parameter optimal untuk latency rendah (high FPS) dan hasil halus
        return cv2.bilateralFilter(frame, d=5, sigmaColor=32, sigmaSpace=32)

    def apply_sharpening(self, frame):
        """
        Mempertajam garis tepi dan kontur sendi jari tangan
        sehingga landmark MediaPipe dapat mengunci posisi sendi dengan stabil.
        """
        if frame is None:
            return frame
        return cv2.filter2D(frame, -1, self.sharpen_kernel)

    def enhance(self, frame):
        """
        Menjalankan seluruh pipeline peningkatan kualitas citra secara berurutan.
        """
        if not self.enabled or frame is None:
            return frame

        enhanced = frame.copy()

        # 1. Koreksi thermal magenta jika ada
        if self.thermal_correction_enabled:
            enhanced = self.correct_thermal_magenta(enhanced)

        # 2. Koreksi Backlight & Under-exposure dengan CLAHE
        if self.clahe_enabled:
            enhanced = self.apply_clahe(enhanced)

        # 3. Denoising edge-preserving
        if self.denoise_enabled:
            enhanced = self.apply_bilateral_denoise(enhanced)

        # 4. Penajaman kontur jari untuk MediaPipe
        if self.sharpen_enabled:
            enhanced = self.apply_sharpening(enhanced)

        return enhanced
