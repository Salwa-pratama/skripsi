"""Model Entity Log Sesi Pomodoro & Deteksi Distraksi."""

from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    task_name: Mapped[str] = mapped_column(String(100), default="Sesi Belajar Mandiri", nullable=False)
    mode: Mapped[str] = mapped_column(String(20), default="work", nullable=False, comment="work / short_break / long_break")
    target_duration_sec: Mapped[int] = mapped_column(Integer, default=1500, nullable=False, comment="25 Menit = 1500s")
    actual_focus_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Durasi riil mahasiswa fokus")
    cycles_completed: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Metrik Distraksi Visual (Computer Vision)
    phone_distraction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Frekuensi main HP")
    absence_distraction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Frekuensi meninggalkan tempat")
    focus_score: Mapped[int] = mapped_column(Integer, default=100, nullable=False, comment="Skor Fokus Akhir (0-100%)")
    
    # Reward Gamifikasi Sesi
    xp_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    coins_earned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    status: Mapped[str] = mapped_column(String(20), default="completed", nullable=False, comment="completed / aborted / paused")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    user: Mapped["User"] = relationship("User", back_populates="pomodoro_sessions")

