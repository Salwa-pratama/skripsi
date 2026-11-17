"""Model Entity Progress Bab & Evaluasi Sintaks AST."""

from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base


class ChapterProgress(Base):
    __tablename__ = "chapter_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    chapter_slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False, comment="Slug bab kurikulum")
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    ast_syntax_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submitted_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="Kode terakhir yang diuji mahasiswa")
    attempts_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="chapter_progresses")

