import os
import math
import json
import time
import pickle

class SibiTranslator:
    """
    Penerjemah Bahasa Isyarat SIBI / BISINDO Abjad (Fingerspelling)
    Menggunakan 21 landmark MediaPipe Hands untuk:
    1. Ekstraksi fitur ter-normalisasi (Invariant posisi & skala).
    2. Klasifikasi huruf A-Z dengan model AI.
    3. Temporal Debouncing Buffer untuk merangkai huruf menjadi kata dan kalimat.
    """

    CONFIRMATION_FRAMES = 10  # Minimal frame stabil sebelum huruf dicatat (~0.3 detik)
    COOLDOWN_FRAMES = 15      # Jeda pencegahan duplikasi huruf yang sama
    MIN_CONFIDENCE = 0.60     # Ambang batas keyakinan prediksi

    def __init__(self, model_path: str = None, labels_path: str = None):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = model_path or os.path.join(self.base_dir, "model", "sibi_abjad_model.pkl")
        self.labels_path = labels_path or os.path.join(self.base_dir, "model", "sibi_labels.json")

        self.model = None
        self.labels = []
        self.model_loaded = False

        # State Penerjemahan
        self.current_letter = ""
        self.current_confidence = 0.0
        self.consecutive_letter = ""
        self.consecutive_count = 0
        self.cooldown_counter = 0
        self.last_appended_letter = ""

        # Buffer Teks
        self.current_word = ""
        self.sentence = ""
        self.history = []

        self.load_model()

    def load_model(self):
        """Memuat model classifier terlatih jika sudah tersedia."""
        if os.path.exists(self.model_path) and os.path.exists(self.labels_path):
            try:
                with open(self.model_path, "rb") as f:
                    self.model = pickle.load(f)
                with open(self.labels_path, "r", encoding="utf-8") as f:
                    self.labels = json.load(f)
                self.model_loaded = True
                print(f"✓ [SibiTranslator] Model SIBI Abjad berhasil dimuat ({len(self.labels)} kelas).", flush=True)
            except Exception as e:
                print(f"⚠️ [SibiTranslator] Gagal memuat model: {e}", flush=True)
                self.model_loaded = False
        else:
            self.model_loaded = False
            print("ℹ️ [SibiTranslator] Model belum dilatih. Sistem menggunakan mode persiapan / fallback.", flush=True)

    @staticmethod
    def extract_normalized_features(landmarks) -> list:
        """
        Normalisasi 21 koordinat landmark tangan:
        1. Translasi: Menjadikan Wrist (Landmark 0) sebagai titik acuan (0, 0, 0).
        2. Skala: Membagi seluruh koordinat dengan jarak pergelangan tangan ke MCP jari tengah (Landmark 9).
        Menghasilkan 63 fitur terstandarisasi yang bebas dari pengaruh jarak tangan ke kamera.
        """
        if not landmarks or len(landmarks) < 21:
            return []

        # Titik acuan: Wrist (index 0)
        wrist_x = landmarks[0].x
        wrist_y = landmarks[0].y
        wrist_z = landmarks[0].z

        # Jarak skala ke pangkal jari tengah (index 9)
        ref_x = landmarks[9].x - wrist_x
        ref_y = landmarks[9].y - wrist_y
        ref_z = landmarks[9].z - wrist_z
        scale = math.sqrt(ref_x**2 + ref_y**2 + ref_z**2)
        if scale == 0:
            scale = 1.0

        features = []
        for lm in landmarks:
            rel_x = (lm.x - wrist_x) / scale
            rel_y = (lm.y - wrist_y) / scale
            rel_z = (lm.z - wrist_z) / scale
            features.extend([rel_x, rel_y, rel_z])

        return features

    def _heuristic_fallback(self, landmarks):
        """
        Klasifikasi heuristik sederhana saat model AI belum dilatih,
        agar tampilan web UI langsung responsif dan bisa diuji dengan beberapa pose dasar.
        """
        if not landmarks or len(landmarks) < 21:
            return "", 0.0

        # Cek jari terbuka vs terlipat
        wrist_y = landmarks[0].y
        thumb_tip = landmarks[4]
        index_tip = landmarks[8]
        middle_tip = landmarks[12]
        ring_tip = landmarks[16]
        pinky_tip = landmarks[20]

        index_mcp = landmarks[5]
        middle_mcp = landmarks[9]
        ring_mcp = landmarks[13]
        pinky_mcp = landmarks[17]

        index_open = index_tip.y < index_mcp.y
        middle_open = middle_tip.y < middle_mcp.y
        ring_open = ring_tip.y < ring_mcp.y
        pinky_open = pinky_tip.y < pinky_mcp.y

        # Pose 'B': 4 jari tegak lurus, jempol melipat
        if index_open and middle_open and ring_open and pinky_open:
            return "B", 0.90
        # Pose 'A': semua jari melipat kepal
        elif not index_open and not middle_open and not ring_open and not pinky_open:
            return "A", 0.88
        # Pose 'L': jempol dan telunjuk tegak
        elif index_open and not middle_open and not ring_open and not pinky_open:
            return "L", 0.85
        # Pose 'V': telunjuk dan tengah tegak
        elif index_open and middle_open and not ring_open and not pinky_open:
            return "V", 0.85
        # Pose 'I': hanya kelingking tegak
        elif pinky_open and not index_open and not middle_open and not ring_open:
            return "I", 0.82

        return "", 0.0

    def process_landmarks(self, raw_hand_landmarks_list):
        """
        Memproses landmark tangan frame saat ini dan memperbarui kata/kalimat.
        """
        if self.cooldown_counter > 0:
            self.cooldown_counter -= 1

        if not raw_hand_landmarks_list or len(raw_hand_landmarks_list) == 0:
            # Tangan keluar dari frame
            self.current_letter = ""
            self.current_confidence = 0.0
            self.consecutive_count = 0
            self.last_appended_letter = ""
            return

        landmarks = raw_hand_landmarks_list[0]
        detected_letter = ""
        confidence = 0.0

        if self.model_loaded and self.model is not None:
            features = self.extract_normalized_features(landmarks)
            if features:
                try:
                    # Prediksi probabilitas
                    probs = self.model.predict_proba([features])[0]
                    max_idx = probs.argmax()
                    confidence = float(probs[max_idx])
                    if confidence >= self.MIN_CONFIDENCE and max_idx < len(self.labels):
                        detected_letter = str(self.labels[max_idx])
                except Exception:
                    # Fallback ke predict langsung jika model tidak support predict_proba
                    try:
                        pred = self.model.predict([features])[0]
                        detected_letter = str(pred)
                        confidence = 0.80
                    except Exception:
                        detected_letter = ""
        else:
            # Fallback heuristik sementara
            detected_letter, confidence = self._heuristic_fallback(landmarks)

        self.current_letter = detected_letter
        self.current_confidence = round(confidence, 2)

        # Logika Debouncing & Stabilitas
        if detected_letter and detected_letter == self.consecutive_letter:
            self.consecutive_count += 1
            if (self.consecutive_count >= self.CONFIRMATION_FRAMES and
                self.cooldown_counter == 0 and
                detected_letter != self.last_appended_letter):

                self.append_letter(detected_letter)
                self.last_appended_letter = detected_letter
                self.cooldown_counter = self.COOLDOWN_FRAMES
        else:
            self.consecutive_letter = detected_letter
            self.consecutive_count = 1
            if detected_letter != self.last_appended_letter:
                self.last_appended_letter = ""

    def append_letter(self, letter: str):
        """Menambahkan satu huruf ke kata yang sedang dieja."""
        self.current_word += letter.upper()

    def add_space(self):
        """Menyelesaikan kata aktif dan memasukkannya ke kalimat."""
        if self.current_word:
            if self.sentence:
                self.sentence += " " + self.current_word
            else:
                self.sentence = self.current_word
            self.current_word = ""
            self.last_appended_letter = ""

    def backspace(self):
        """Menghapus huruf terakhir dari kata aktif, atau kata terakhir dari kalimat."""
        if self.current_word:
            self.current_word = self.current_word[:-1]
        elif self.sentence:
            words = self.sentence.split()
            if words:
                words.pop()
                self.sentence = " ".join(words)
        self.last_appended_letter = ""

    def clear(self):
        """Mereset seluruh teks dan menyimpan ke riwayat jika ada isi."""
        full_text = self.get_full_text()
        if full_text and full_text not in self.history:
            self.history.append(full_text)
        self.current_word = ""
        self.sentence = ""
        self.last_appended_letter = ""

    def get_full_text(self) -> str:
        """Menggabungkan kalimat selesai dan kata yang sedang dieja."""
        if self.sentence and self.current_word:
            return f"{self.sentence} {self.current_word}"
        elif self.sentence:
            return self.sentence
        return self.current_word

    def get_state(self) -> dict:
        """Mengambil status telemetri untuk dikirim ke UI."""
        progress = 0.0
        if self.CONFIRMATION_FRAMES > 0:
            progress = min(1.0, self.consecutive_count / self.CONFIRMATION_FRAMES)

        return {
            "current_letter": self.current_letter,
            "confidence": int(self.current_confidence * 100),
            "current_word": self.current_word,
            "sentence": self.sentence,
            "full_text": self.get_full_text(),
            "progress": round(progress, 2),
            "model_loaded": self.model_loaded,
            "history": self.history[-5:]
        }
