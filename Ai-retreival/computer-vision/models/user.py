"""Model Entity Pengguna (Mahasiswa)."""

from datetime import datetime
from typing import List, Optional
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nim: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False, comment="Nomor Induk Mahasiswa")
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="Nama Lengkap Mahasiswa")
    avatar: Mapped[Optional[str]] = mapped_column(String(255), default="🤖", nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relasi 1-to-1 ke Gamification Profile (Focus XP, Coins, Streak)
    gamification_profile: Mapped["GamificationProfile"] = relationship(
        "GamificationProfile", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    # Relasi 1-to-many ke Sesi Pomodoro
    pomodoro_sessions: Mapped[List["PomodoroSession"]] = relationship(
        "PomodoroSession", back_populates="user", cascade="all, delete-orphan"
    )

    # Relasi 1-to-many ke Progress Materi & AST
    chapter_progresses: Mapped[List["ChapterProgress"]] = relationship(
        "ChapterProgress", back_populates="user", cascade="all, delete-orphan"
    )

