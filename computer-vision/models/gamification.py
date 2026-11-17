"""Model Entity Profil Gamifikasi MDA (Focus XP, Python Coins, Daily Streak, Badges)."""

from datetime import date, datetime
from typing import List, Optional
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class GamificationProfile(Base):
    __tablename__ = "gamification_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    
    # Elemen MDA Player Progression
    focus_xp: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Akumulasi Poin Pengalaman Fokus")
    python_coins: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="Token Koin Reward Latihan")
    current_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="Tingkat Kemahiran (1-5)")
    level_title: Mapped[str] = mapped_column(String(50), default="Python Novice", nullable=False, comment="Gelar Tingkatan")
    daily_streak: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="Hari Belajar Berturut-turut")
    last_study_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="Tanggal Belajar Terakhir")
    
    # Badges / Lencana Prestasi (Array JSON string, misal: ["zero_ai", "zen_focus"])
    badges_unlocked: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False, comment="Daftar ID Lencana Terbuka")
    
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relasi balik ke User
    user: Mapped["User"] = relationship("User", back_populates="gamification_profile")

