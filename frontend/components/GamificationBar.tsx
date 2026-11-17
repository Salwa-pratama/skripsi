"use client";

import { useEffect, useState } from "react";
import { LeaderboardModal } from "./LeaderboardModal";
import { BadgesModal } from "./BadgesModal";

type GamificationData = {
  focus_xp: number;
  python_coins: number;
  level: number;
  level_title: string;
  daily_streak: number;
  badges_unlocked: string[];
};

type UserProfileResponse = {
  id: number;
  nim: string;
  name: string;
  avatar: string;
  gamification: GamificationData;
};

const FASTAPI_URL = "http://localhost:5000";

const LEVEL_TARGETS: Record<number, { min: number; max: number }> = {
  1: { min: 0, max: 200 },
  2: { min: 201, max: 500 },
  3: { min: 501, max: 1000 },
  4: { min: 1001, max: 2000 },
  5: { min: 2001, max: 5000 },
};

export function GamificationBar() {
  const [profile, setProfile] = useState<UserProfileResponse | null>(null);
  const [isLeaderboardOpen, setIsLeaderboardOpen] = useState(false);
  const [isBadgesOpen, setIsBadgesOpen] = useState(false);

  useEffect(() => {
    let isMounted = true;

    async function fetchProfile() {
      try {
        const res = await fetch(`${FASTAPI_URL}/api/user/profile`, { cache: "no-store" });
        if (res.ok) {
          const data = (await res.json()) as UserProfileResponse;
          if (isMounted) setProfile(data);
        }
      } catch {
        // Fallback state jika backend belum aktif
      }
    }

    fetchProfile();
    const interval = setInterval(fetchProfile, 2000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  const game = profile?.gamification || {
    focus_xp: 350,
    python_coins: 85,
    level: 2,
    level_title: "Syntax Apprentice",
    daily_streak: 3,
    badges_unlocked: ["zero_ai", "zen_focus"],
  };

  const currentLvlTarget = LEVEL_TARGETS[game.level] || { min: 0, max: 500 };
  const xpInLevel = Math.max(0, game.focus_xp - currentLvlTarget.min);
  const xpNeeded = currentLvlTarget.max - currentLvlTarget.min;
  const progressPercent = Math.min(100, Math.max(5, Math.round((xpInLevel / xpNeeded) * 100)));

  return (
    <>
      <div className="gamification-header-bar">
        {/* Level & Gelar MDA */}
        <div className="game-stat-item level-item" title="Tingkatan Kemahiran Pemrograman Python">
          <span className="stat-icon">⚡</span>
          <div className="stat-text-col">
            <span className="stat-label">Lv.{game.level} {game.level_title}</span>
            <div className="xp-progress-track" title={`${game.focus_xp} / ${currentLvlTarget.max} Focus XP`}>
              <div className="xp-progress-fill" style={{ width: `${progressPercent}%` }} />
            </div>
          </div>
        </div>

        {/* Focus XP Counter */}
        <div className="game-stat-item xp-item" title="Poin Pengalaman Fokus Belajar (Didapat dari 25m Pomodoro & Quest AST)">
          <span className="stat-icon">🎯</span>
          <span className="stat-value">{game.focus_xp.toLocaleString()} <small>XP</small></span>
        </div>

        {/* Python Coins Counter */}
        <div className="game-stat-item coins-item" title="Koin Reward Latihan Mandiri Tanpa Distraksi">
          <span className="stat-icon">🪙</span>
          <span className="stat-value">{game.python_coins}</span>
        </div>

        {/* Daily Streak Counter */}
        <div className="game-stat-item streak-item" title="Kedisiplinan Belajar Harian Berturut-turut">
          <span className="stat-icon">🔥</span>
          <span className="stat-value">{game.daily_streak} <small>Hari</small></span>
        </div>

        {/* Tombol Interaktif Leaderboard & Badges */}
        <div className="game-actions">
          <button
            type="button"
            className="btn-mda-action leaderboard"
            onClick={() => setIsLeaderboardOpen(true)}
            title="Buka Papan Peringkat Mahasiswa TI (Leaderboard)"
          >
            🏆 Leaderboard
          </button>
          <button
            type="button"
            className="btn-mda-action badges"
            onClick={() => setIsBadgesOpen(true)}
            title="Buka Lencana Prestasi Belajar (Badges)"
          >
            🎖️ ({game.badges_unlocked.length})
          </button>
        </div>
      </div>

      {/* Modals */}
      <LeaderboardModal
        isOpen={isLeaderboardOpen}
        onClose={() => setIsLeaderboardOpen(false)}
        currentUserNim={profile?.nim || "2313020011"}
      />
      <BadgesModal
        isOpen={isBadgesOpen}
        onClose={() => setIsBadgesOpen(false)}
        unlockedBadges={game.badges_unlocked}
      />
    </>
  );
}

