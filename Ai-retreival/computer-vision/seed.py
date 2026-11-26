"""Script Seeding Database Awal untuk Demo Skripsi.

Mengisi data mahasiswa, profil gamifikasi MDA, riwayat pomodoro,
dan leaderboard kompetitif (Mahasiswa Prodi Teknik Informatika UNP Kediri).
"""

from datetime import date, datetime, timedelta
from db.session import SessionLocal
from models.user import User
from models.gamification import GamificationProfile
from models.pomodoro_session import PomodoroSession
from models.chapter_progress import ChapterProgress


def seed_database():
    db = SessionLocal()
    try:
        print("🌱 [Seeding] Memulai inisialisasi data awal database...", flush=True)

        # Daftar Mahasiswa untuk Leaderboard Realistis
        students_data = [
            {
                "nim": "2313020005",
                "name": "Ahmad Fauzi",
                "avatar": "👨‍🎓",
                "xp": 620,
                "coins": 140,
                "level": 3,
                "title": "Logic Crafter",
                "streak": 5,
                "badges": ["zero_ai", "zen_focus", "ast_architect", "streak_builder"],
            },
            {
                "nim": "2313020018",
                "name": "Siti Rahmawati",
                "avatar": "👩‍💻",
                "xp": 480,
                "coins": 110,
                "level": 2,
                "title": "Syntax Apprentice",
                "streak": 4,
                "badges": ["zero_ai", "zen_focus", "ast_architect"],
            },
            {
                "nim": "2313020011",
                "name": "Bintang Maulana",
                "avatar": "👨‍💻",
                "xp": 350,
                "coins": 85,
                "level": 2,
                "title": "Syntax Apprentice",
                "streak": 3,
                "badges": ["zero_ai", "zen_focus"],
            },
            {
                "nim": "2313020023",
                "name": "Dimas Prasetyo",
                "avatar": "🧑‍💻",
                "xp": 210,
                "coins": 50,
                "level": 2,
                "title": "Syntax Apprentice",
                "streak": 2,
                "badges": ["zero_ai"],
            },
            {
                "nim": "2313020030",
                "name": "Rina Wulandari",
                "avatar": "👩‍🎓",
                "xp": 140,
                "coins": 30,
                "level": 1,
                "title": "Python Novice",
                "streak": 1,
                "badges": ["zero_ai"],
            },
        ]

        today = date.today()

        for s in students_data:
            existing_user = db.query(User).filter(User.nim == s["nim"]).first()
            if not existing_user:
                user = User(nim=s["nim"], name=s["name"], avatar=s["avatar"])
                db.add(user)
                db.flush()

                profile = GamificationProfile(
                    user_id=user.id,
                    focus_xp=s["xp"],
                    python_coins=s["coins"],
                    current_level=s["level"],
                    level_title=s["title"],
                    daily_streak=s["streak"],
                    last_study_date=today,
                    badges_unlocked=s["badges"],
                )
                db.add(profile)

                # Tambahkan riwayat sesi untuk user utama (Bintang Maulana)
                if s["nim"] == "2313020011":
                    session1 = PomodoroSession(
                        user_id=user.id,
                        task_name="Materi Percabangan (If-Else)",
                        mode="work",
                        target_duration_sec=1500,
                        actual_focus_sec=1500,
                        cycles_completed=1,
                        phone_distraction_count=0,
                        absence_distraction_count=0,
                        focus_score=100,
                        xp_earned=100,
                        coins_earned=25,
                        status="completed",
                        created_at=datetime.now() - timedelta(hours=2),
                    )
                    db.add(session1)

                    ch1 = ChapterProgress(
                        user_id=user.id,
                        chapter_slug="variabel-dan-tipe-data",
                        is_completed=True,
                        ast_syntax_valid=True,
                        submitted_code="nama = 'Bintang'\nnim = 2313020011\nprint(f'{nama} - {nim}')",
                        attempts_count=1,
                        completed_at=datetime.now() - timedelta(days=1),
                    )
                    db.add(ch1)

        db.commit()
        print("✅ [Seeding] Sukses! Data mahasiswa, profil gamifikasi, dan riwayat terisi.", flush=True)

    except Exception as exc:
        db.rollback()
        print(f"❌ [Seeding Error] Gagal seeding: {exc}", flush=True)
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()

