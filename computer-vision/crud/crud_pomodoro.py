"""CRUD Operations untuk Riwayat Sesi Pomodoro & Progress Bab AST."""

from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from models.pomodoro_session import PomodoroSession
from models.chapter_progress import ChapterProgress
from crud.crud_gamification import add_xp_and_coins, unlock_badge


def record_pomodoro_session(db: Session, user_id: int, data: Dict[str, Any]) -> PomodoroSession:
    """Mencatat sesi Pomodoro dan mengalokasikan reward XP & Koin ke profil user."""
    focus_score = int(data.get("focus_score", 100))
    phone_distractions = int(data.get("phone_distractions", 0))
    absence_distractions = int(data.get("absence_distractions", 0))
    
    # Hitung reward: Sesi selesai = +100 XP, +25 Koin
    xp_earned = 100 if focus_score >= 60 else 40
    coins_earned = 25 if focus_score >= 80 else 10

    # Penalti jika distraksi banyak
    if phone_distractions > 2:
        coins_earned = max(0, coins_earned - 10)

    session = PomodoroSession(
        user_id=user_id,
        task_name=data.get("task_name", "Sesi Belajar Fokus"),
        mode=data.get("mode", "work"),
        target_duration_sec=int(data.get("target_duration_sec", 1500)),
        actual_focus_sec=int(data.get("actual_focus_sec", 1500)),
        cycles_completed=int(data.get("cycles_completed", 1)),
        phone_distraction_count=phone_distractions,
        absence_distraction_count=absence_distractions,
        focus_score=focus_score,
        xp_earned=xp_earned,
        coins_earned=coins_earned,
        status=data.get("status", "completed"),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Sinkronkan perolehan ke profil Gamifikasi MDA
    add_xp_and_coins(db, user_id, xp_earned, coins_earned)

    # Evaluasi Badge: Zen Focus (jika sesi 25 menit 0 distraksi HP)
    if phone_distractions == 0 and session.mode == "work":
        unlock_badge(db, user_id, "zen_focus")

    return session


def record_chapter_progress(
    db: Session,
    user_id: int,
    chapter_slug: str,
    submitted_code: str,
    ast_valid: bool,
    is_completed: bool
) -> ChapterProgress:
    """Menyimpan submission kode dan validasi simpul pohon AST."""
    progress = (
        db.query(ChapterProgress)
        .filter(ChapterProgress.user_id == user_id, ChapterProgress.chapter_slug == chapter_slug)
        .first()
    )

    if not progress:
        progress = ChapterProgress(
            user_id=user_id,
            chapter_slug=chapter_slug,
            attempts_count=1
        )
        db.add(progress)
    else:
        progress.attempts_count += 1

    progress.submitted_code = submitted_code
    progress.ast_syntax_valid = ast_valid

    if is_completed and not progress.is_completed:
        progress.is_completed = True
        progress.completed_at = datetime.now()
        # Berikan reward quest pertama kali selesai: +50 XP, +20 Koin
        add_xp_and_coins(db, user_id, 50, 20)
        unlock_badge(db, user_id, "ast_architect")

    db.commit()
    db.refresh(progress)
    return progress

