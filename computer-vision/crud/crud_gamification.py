"""CRUD Operations untuk Profil Gamifikasi MDA."""

from datetime import date, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from models.gamification import GamificationProfile
from models.user import User


LEVEL_THRESHOLDS = [
    (1, "Python Novice", 0, 200),
    (2, "Syntax Apprentice", 201, 500),
    (3, "Logic Crafter", 501, 1000),
    (4, "Algorithm Adept", 1001, 2000),
    (5, "Code Master", 2001, 999999),
]


def calculate_level(xp: int) -> tuple[int, str]:
    """Menghitung level dan gelar berdasarkan akumulasi Focus XP."""
    for lvl, title, min_xp, max_xp in LEVEL_THRESHOLDS:
        if min_xp <= xp <= max_xp:
            return lvl, title
    return 5, "Code Master"


def get_profile_by_user_id(db: Session, user_id: int) -> Optional[GamificationProfile]:
    return db.query(GamificationProfile).filter(GamificationProfile.user_id == user_id).first()


def get_or_create_profile(db: Session, user_id: int) -> GamificationProfile:
    profile = get_profile_by_user_id(db, user_id)
    if not profile:
        profile = GamificationProfile(
            user_id=user_id,
            focus_xp=0,
            python_coins=0,
            current_level=1,
            level_title="Python Novice",
            daily_streak=1,
            last_study_date=date.today(),
            badges_unlocked=["zero_ai"]  # Badge pemula
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def add_xp_and_coins(db: Session, user_id: int, xp_gain: int, coins_gain: int) -> GamificationProfile:
    """Menambahkan Focus XP dan Koin, serta mengevaluasi kenaikan level."""
    profile = get_or_create_profile(db, user_id)
    profile.focus_xp += max(0, xp_gain)
    profile.python_coins += max(0, coins_gain)

    # Evaluasi Level
    new_lvl, new_title = calculate_level(profile.focus_xp)
    profile.current_level = new_lvl
    profile.level_title = new_title

    # Update Streak Harian
    today = date.today()
    if profile.last_study_date:
        if profile.last_study_date == today - timedelta(days=1):
            profile.daily_streak += 1
        elif profile.last_study_date < today - timedelta(days=1):
            profile.daily_streak = 1  # Reset jika bolos lebih dari 1 hari
    profile.last_study_date = today

    db.commit()
    db.refresh(profile)
    return profile


def unlock_badge(db: Session, user_id: int, badge_id: str) -> GamificationProfile:
    """Membuka lencana baru jika belum dimiliki."""
    profile = get_or_create_profile(db, user_id)
    current_badges = list(profile.badges_unlocked)
    if badge_id not in current_badges:
        current_badges.append(badge_id)
        profile.badges_unlocked = current_badges
        db.commit()
        db.refresh(profile)
    return profile


def get_leaderboard(db: Session, limit: int = 10) -> List[Dict[str, Any]]:
    """Mengambil papan peringkat mahasiswa berdasarkan Focus XP & Streak."""
    results = (
        db.query(User, GamificationProfile)
        .join(GamificationProfile, User.id == GamificationProfile.user_id)
        .order_by(desc(GamificationProfile.focus_xp), desc(GamificationProfile.daily_streak))
        .limit(limit)
        .all()
    )

    leaderboard = []
    for rank, (user, profile) in enumerate(results, start=1):
        leaderboard.append({
            "rank": rank,
            "nim": user.nim,
            "name": user.name,
            "avatar": user.avatar or "👨‍💻",
            "focus_xp": profile.focus_xp,
            "python_coins": profile.python_coins,
            "level": profile.current_level,
            "level_title": profile.level_title,
            "daily_streak": profile.daily_streak,
            "badges_count": len(profile.badges_unlocked)
        })
    return leaderboard

