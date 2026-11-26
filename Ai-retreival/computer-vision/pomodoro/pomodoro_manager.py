import os
import json
import time
import threading
from config import Config

class PomodoroManager:
    """
    Sistem Pengelola Sesi Belajar & Pomodoro State Machine Lengkap:
    1. Konfigurasi Fleksibel:
       - Nama Task yang dikerjakan.
       - Rasio waktu belajar (Work), istirahat pendek (Short Break), dan istirahat panjang (Long Break).
       - Target siklus Pomodoro (misal 2, 3, 4 siklus) sebelum istirahat panjang & sesi selesai.
       - Batas toleransi meninggalkan tempat dalam persentase (%) durasi sesi belajar.
    2. Deteksi & Pencatatan 3 Jenis Distraksi:
       - Meninggalkan tempat (Absence) + pelacakan batas toleransi.
       - Bermain handphone.
       - Kepala menunduk (potensi tidur, sembunyi main HP, ngelamun).
    3. Konfirmasi Penyelesaian Sesi, Pengulangan Siklus, & Penyimpanan Riwayat Belajar.
    """

    MODE_WORK = "work"
    MODE_SHORT_BREAK = "short_break"
    MODE_LONG_BREAK = "long_break"

    STATUS_STOPPED = "stopped"
    STATUS_RUNNING = "running"
    STATUS_PAUSED = "paused"
    STATUS_COMPLETED = "completed"

    def __init__(self):
        self.lock = threading.Lock()
        
        # Konfigurasi Task & Timer
        self.task_name = "Sesi Belajar Fokus"
        self.study_mode = "book"  # 'book' (Membaca/Menulis - Menunduk Diizinkan) atau 'screen' (Layar/Komputer)
        self.allow_head_down = True
        self.target_cycles = 4
        self.current_cycle = 1
        
        self.durations = {
            self.MODE_WORK: 25 * 60,
            self.MODE_SHORT_BREAK: 5 * 60,
            self.MODE_LONG_BREAK: 15 * 60
        }
        
        # Toleransi Meninggalkan Tempat (Default 10%)
        self.absence_tolerance_pct = 10.0
        
        # Status & State Machine
        self.mode = self.MODE_WORK
        self.status = self.STATUS_STOPPED
        self.time_left = float(self.durations[self.mode])
        self.cycles_completed = 0
        self.total_work_seconds_completed = 0
        
        # Metrik 3 Kategori Distraksi
        self.distraction_counts = {
            "absent": 0,
            "phone": 0,
            "head_down": 0
        }
        self.distraction_durations = {
            "absent": 0.0,
            "phone": 0.0,
            "head_down": 0.0
        }
        
        # Live State Pemantauan Kehadiran
        self.is_user_present = True
        self.current_absence_sec = 0.0
        self.session_absence_sec = 0.0
        self.is_phone_detected = False
        self.is_head_down_detected = False
        
        # State Debouncing Log Insiden
        self._last_logged_states = {
            "absent": False,
            "phone": False,
            "head_down": False
        }
        
        # Override Emosi Sementara (misal saat menyelesaikan Quest Kode)
        self.happy_override_until = 0.0
        
        # Riwayat Sesi & Log Aktivitas
        self.events_log = []
        self.session_summary = None
        self.study_history = []
        
        # Background worker thread untuk countdown timer
        self.running = True
        self.thread = threading.Thread(target=self._timer_worker, daemon=True)
        self.thread.start()

    @property
    def absence_tolerance_sec(self):
        """Total batas toleransi waktu absen dalam detik untuk durasi belajar aktif"""
        work_sec = self.durations[self.MODE_WORK]
        return round((self.absence_tolerance_pct / 100.0) * work_sec, 1)

    def _timer_worker(self):
        last_tick = time.time()
        while self.running:
            time.sleep(0.5)
            with self.lock:
                now = time.time()
                elapsed = now - last_tick
                last_tick = now

                if self.status == self.STATUS_RUNNING:
                    self.time_left -= elapsed
                    if self.mode == self.MODE_WORK:
                        self.total_work_seconds_completed += elapsed
                        
                    if self.time_left <= 0:
                        self.time_left = 0
                        self._handle_session_completed()

    def _handle_session_completed(self):
        """Otomatis transisi mode saat timer habis atau target siklus tercapai"""
        if self.mode == self.MODE_WORK:
            self.cycles_completed += 1
            self.add_event("success", f"🎯 Sesi Belajar Siklus #{self.current_cycle} Selesai! ({self.task_name})")

            # Cek apakah seluruh target siklus pomodoro sudah selesai
            if self.current_cycle >= self.target_cycles:
                self.mode = self.MODE_LONG_BREAK
                self.status = self.STATUS_COMPLETED
                self.time_left = self.durations[self.mode]
                self._generate_session_summary()
                self.add_event("success", f"🏆 SELAMAT! Seluruh {self.target_cycles} Siklus Pomodoro Selesai! Waktunya Istirahat Panjang.")
                return
            else:
                self.mode = self.MODE_SHORT_BREAK
                self.current_cycle += 1
                self.status = self.STATUS_STOPPED
                self.time_left = self.durations[self.mode]
                self.add_event("info", f"Waktu Istirahat Pendek Dimulai ({int(self.durations[self.mode]//60)} menit)")
        else:
            self.add_event("info", f"Waktu istirahat selesai! Masuk ke Siklus Belajar #{self.current_cycle}.")
            self.mode = self.MODE_WORK
            self.status = self.STATUS_STOPPED
            self.time_left = self.durations[self.mode]

    def _generate_session_summary(self):
        """Menghasilkan rekapitulasi data sesi belajar untuk konfirmasi & riwayat"""
        total_distractions = sum(self.distraction_counts.values())
        focus_score = max(0, 100 - (total_distractions * 4) - int(self.session_absence_sec / 30))
        tolerance_exceeded = self.session_absence_sec > self.absence_tolerance_sec

        self.session_summary = {
            "task_name": self.task_name,
            "study_mode": self.study_mode,
            "allow_head_down": self.allow_head_down,
            "target_cycles": self.target_cycles,
            "cycles_completed": self.cycles_completed,
            "total_focus_minutes": round(self.total_work_seconds_completed / 60, 1),
            "work_duration_min": int(self.durations[self.MODE_WORK] // 60),
            "short_break_min": int(self.durations[self.MODE_SHORT_BREAK] // 60),
            "long_break_min": int(self.durations[self.MODE_LONG_BREAK] // 60),
            "distraction_counts": dict(self.distraction_counts),
            "distraction_durations": {k: round(v, 1) for k, v in self.distraction_durations.items()},
            "total_distractions": total_distractions,
            "session_absence_sec": round(self.session_absence_sec, 1),
            "absence_tolerance_sec": self.absence_tolerance_sec,
            "absence_tolerance_pct": self.absence_tolerance_pct,
            "tolerance_exceeded": tolerance_exceeded,
            "focus_score": focus_score,
            "completed_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def configure_session(self, task_name=None, study_mode=None, work_min=None, short_break_min=None, 
                          long_break_min=None, target_cycles=None, tolerance_pct=None):
        """
        Menyetel konfigurasi sesi Pomodoro:
        - task_name: Nama target belajar
        - study_mode: 'book' (Membaca/Menulis Buku) atau 'screen' (Layar/Komputer)
        - work_min: Menit belajar per siklus (Default 25)
        - short_break_min: Menit istirahat pendek (Default 5)
        - long_break_min: Menit istirahat panjang (Default 15)
        - target_cycles: Berapa kali siklus pomodoro dijalankan (Default 4)
        - tolerance_pct: Batas toleransi meninggalkan tempat (%)
        """
        with self.lock:
            if task_name is not None and str(task_name).strip():
                self.task_name = str(task_name).strip()

            if study_mode is not None:
                mode_clean = str(study_mode).lower().strip()
                if mode_clean in ["book", "writing", "meja", "buku"]:
                    self.study_mode = "book"
                    self.allow_head_down = True
                else:
                    self.study_mode = "screen"
                    self.allow_head_down = False

            if work_min is not None:
                self.durations[self.MODE_WORK] = max(60, int(float(work_min) * 60))

            if short_break_min is not None:
                self.durations[self.MODE_SHORT_BREAK] = max(30, int(float(short_break_min) * 60))

            if long_break_min is not None:
                self.durations[self.MODE_LONG_BREAK] = max(60, int(float(long_break_min) * 60))

            if target_cycles is not None:
                self.target_cycles = max(1, int(target_cycles))

            if tolerance_pct is not None:
                self.absence_tolerance_pct = max(1.0, min(50.0, float(tolerance_pct)))

            # Reset timer jika sedang stopped
            if self.status in [self.STATUS_STOPPED, self.STATUS_COMPLETED]:
                self.mode = self.MODE_WORK
                self.status = self.STATUS_STOPPED
                self.time_left = float(self.durations[self.MODE_WORK])
                self.current_cycle = 1

            mode_title = "📖 Mode Buku/Menulis" if self.study_mode == "book" else "💻 Mode Layar/PC"
            self.add_event("info", f"Konfigurasi Pomodoro: '{self.task_name}' [{mode_title}] ({int(self.durations[self.MODE_WORK]//60)}m Belajar, {self.target_cycles} Siklus, Toleransi Absen {self.absence_tolerance_pct}%)")

    def update_distraction_states(self, is_absent: bool, is_phone: bool, is_head_down: bool, dt: float = 0.5):
        """
        Menerima input status real-time dari Vision Pipeline dan mengakumulasi metrik distraksi.
        Poin 2 & 4 Engineering: Jika pengguna belajar dengan buku/menulis, menunduk TIDAK dihitung sebagai distraksi!
        """
        with self.lock:
            self.is_user_present = not is_absent
            self.is_phone_detected = is_phone

            # Filter Menunduk Berdasarkan Mode Belajar
            if self.study_mode == "book" or self.allow_head_down:
                effective_head_down = False
            else:
                effective_head_down = is_head_down
            
            self.is_head_down_detected = effective_head_down

            # Hanya catat & akumulasi metrik saat sesi BELAJAR (WORK) sedang berjalan (RUNNING)
            if self.status != self.STATUS_RUNNING or self.mode != self.MODE_WORK:
                return

            # 1. Distraksi: Meninggalkan Tempat (Absen)
            if is_absent:
                self.current_absence_sec += dt
                self.session_absence_sec += dt
                self.distraction_durations["absent"] += dt
                
                # Catat insiden saat baru terdeteksi absen
                if not self._last_logged_states["absent"]:
                    self.distraction_counts["absent"] += 1
                    self.add_event("warning", f"🚶‍♂️ Pengguna Meninggalkan Tempat (Insiden #{self.distraction_counts['absent']})")
                    self._last_logged_states["absent"] = True

                # Cek jika melebihi toleransi waktu absen
                if self.session_absence_sec > self.absence_tolerance_sec and not getattr(self, '_tolerance_warned', False):
                    self.add_event("danger", f"⚠️ Peringatan: Batas toleransi meninggalkan tempat ({self.absence_tolerance_pct}%) telah terlampaui!")
                    self._tolerance_warned = True
            else:
                self.current_absence_sec = 0.0
                self._last_logged_states["absent"] = False

            # 2. Distraksi: Mainan Handphone
            if is_phone:
                self.distraction_durations["phone"] += dt
                if not self._last_logged_states["phone"]:
                    self.distraction_counts["phone"] += 1
                    self.add_event("danger", f"📱 Terdeteksi Mainan Handphone (Insiden #{self.distraction_counts['phone']})")
                    self._last_logged_states["phone"] = True
            else:
                self._last_logged_states["phone"] = False

            # 3. Distraksi: Kepala Menunduk (Hanya untuk Mode Layar/PC)
            if effective_head_down:
                self.distraction_durations["head_down"] += dt
                if not self._last_logged_states["head_down"]:
                    self.distraction_counts["head_down"] += 1
                    self.add_event("warning", f"🙇 Terdeteksi Menunduk/Tertidur di Layar (Insiden #{self.distraction_counts['head_down']})")
                    self._last_logged_states["head_down"] = True
            else:
                self._last_logged_states["head_down"] = False

    def finish_session_choice(self, action="save"):
        """
        Menangani konfirmasi setelah seluruh siklus pomodoro selesai:
        - action = 'repeat': Ulangi siklus dengan task/konfigurasi yang sama
        - action = 'save': Simpan hasil sesi ke riwayat dan reset timer ke awal
        """
        with self.lock:
            if not self.session_summary:
                self._generate_session_summary()

            if self.session_summary:
                self.study_history.insert(0, dict(self.session_summary))
                if len(self.study_history) > 20:
                    self.study_history = self.study_history[:20]

            if action == "repeat":
                self.mode = self.MODE_WORK
                self.status = self.STATUS_STOPPED
                self.time_left = float(self.durations[self.MODE_WORK])
                self.current_cycle = 1
                self.cycles_completed = 0
                self.total_work_seconds_completed = 0
                self.session_absence_sec = 0.0
                self.current_absence_sec = 0.0
                self._tolerance_warned = False
                self.distraction_counts = {"absent": 0, "phone": 0, "head_down": 0}
                self.distraction_durations = {"absent": 0.0, "phone": 0.0, "head_down": 0.0}
                self.session_summary = None
                self.add_event("success", f"🔄 Mengulang siklus baru untuk task: '{self.task_name}'")
            else:
                self.mode = self.MODE_WORK
                self.status = self.STATUS_STOPPED
                self.time_left = float(self.durations[self.MODE_WORK])
                self.current_cycle = 1
                self.cycles_completed = 0
                self.total_work_seconds_completed = 0
                self.session_absence_sec = 0.0
                self.current_absence_sec = 0.0
                self._tolerance_warned = False
                self.distraction_counts = {"absent": 0, "phone": 0, "head_down": 0}
                self.distraction_durations = {"absent": 0.0, "phone": 0.0, "head_down": 0.0}
                self.session_summary = None
                self.add_event("info", "Sesi selesai dan tersimpan ke Riwayat Belajar.")

    def start(self):
        with self.lock:
            if self.status != self.STATUS_RUNNING:
                self.status = self.STATUS_RUNNING
                self.add_event("info", f"Timer dimulai (Siklus #{self.current_cycle} - {self.mode.upper()})")

    def pause(self):
        with self.lock:
            if self.status == self.STATUS_RUNNING:
                self.status = self.STATUS_PAUSED
                self.add_event("info", "Timer dijeda")

    def reset(self):
        with self.lock:
            self.status = self.STATUS_STOPPED
            self.time_left = float(self.durations[self.mode])
            self.current_absence_sec = 0.0
            self.add_event("info", "Timer direset")

    def skip(self):
        with self.lock:
            self._handle_session_completed()

    def switch_mode(self, new_mode):
        with self.lock:
            if new_mode in self.durations:
                self.mode = new_mode
                self.status = self.STATUS_STOPPED
                self.time_left = float(self.durations[new_mode])
                self.add_event("info", f"Ganti mode ke {new_mode}")

    def trigger_quest_passed(self, duration_sec=6.0):
        """Memicu ekspresi bahagia robot (HAPPY) saat mahasiswa menyelesaikan quest koding"""
        with self.lock:
            self.happy_override_until = time.time() + duration_sec
            self.add_event("success", "🎉 Quest Kode Berhasil! Robot merayakan selebrasi bersama pengguna.")

    def add_event(self, event_type, message):
        curr_time = time.strftime("%H:%M:%S")
        self.events_log.insert(0, {
            "time": curr_time,
            "type": event_type,  # 'info', 'warning', 'danger', 'success'
            "message": message
        })
        if len(self.events_log) > 40:
            self.events_log = self.events_log[:40]

    def get_state(self):
        with self.lock:
            total = float(self.durations[self.mode])
            pct = 100 - int((self.time_left / total) * 100) if total > 0 else 0
            minutes = int(self.time_left) // 60
            seconds = int(self.time_left) % 60
            formatted_time = f"{minutes:02d}:{seconds:02d}"

            # Hitung persentase batas toleransi absen yang sudah terpakai
            tol_sec = self.absence_tolerance_sec
            absence_pct_used = min(100, int((self.session_absence_sec / tol_sec) * 100)) if tol_sec > 0 else 0
            is_tol_exceeded = self.session_absence_sec > tol_sec

            # Hitung skor fokus sesi (100% dikurangi penalti insiden distraksi)
            total_distractions = sum(self.distraction_counts.values())
            focus_score = max(0, 100 - (total_distractions * 4) - int(self.session_absence_sec / 30))

            # Tentukan ekspresi robot realtime (MDA Framework: Aesthetics & Companion Feedback)
            now_ts = time.time()
            if now_ts < self.happy_override_until:
                emotion = "HAPPY"
            elif self.mode in [self.MODE_SHORT_BREAK, self.MODE_LONG_BREAK]:
                emotion = "SLEEP"
            elif self.is_phone_detected:
                emotion = "ANGRY"
            elif not self.is_user_present or is_tol_exceeded:
                emotion = "SURPRISED"
            elif self.status == self.STATUS_RUNNING:
                emotion = "FOCUS"
            else:
                emotion = "NORMAL"

            return {
                "task_name": self.task_name,
                "study_mode": self.study_mode,
                "allow_head_down": self.allow_head_down,
                "mode": self.mode,
                "status": self.status,
                "emotion": emotion,
                "time_left": int(self.time_left),
                "total_duration": int(total),
                "progress_percent": pct,
                "formatted_time": formatted_time,
                "target_cycles": self.target_cycles,
                "current_cycle": self.current_cycle,
                "cycles_completed": self.cycles_completed,
                
                # Pengaturan Durasi dalam Menit
                "config": {
                    "work_min": int(self.durations[self.MODE_WORK] // 60),
                    "short_break_min": int(self.durations[self.MODE_SHORT_BREAK] // 60),
                    "long_break_min": int(self.durations[self.MODE_LONG_BREAK] // 60),
                    "target_cycles": self.target_cycles,
                    "study_mode": self.study_mode,
                    "allow_head_down": self.allow_head_down,
                    "tolerance_pct": self.absence_tolerance_pct,
                    "tolerance_sec": tol_sec
                },

                # Pelacakan 3 Kategori Distraksi
                "distractions": {
                    "counts": dict(self.distraction_counts),
                    "durations": {k: round(v, 1) for k, v in self.distraction_durations.items()},
                    "total_count": total_distractions
                },

                # Metrik Toleransi Meninggalkan Tempat
                "absence_tracking": {
                    "is_user_present": self.is_user_present,
                    "current_absence_sec": round(self.current_absence_sec, 1),
                    "session_absence_sec": round(self.session_absence_sec, 1),
                    "tolerance_sec": tol_sec,
                    "tolerance_pct": self.absence_tolerance_pct,
                    "absence_pct_used": absence_pct_used,
                    "tolerance_exceeded": is_tol_exceeded
                },

                # Status Deteksi Live Lainnya
                "live_flags": {
                    "is_phone": self.is_phone_detected,
                    "is_head_down": self.is_head_down_detected
                },

                "focus_score": focus_score,
                "events": self.events_log[:15],
                "session_summary": self.session_summary,
                "study_history": self.study_history[:10]
            }
