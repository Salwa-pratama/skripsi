"use client";

import { useEffect, useState } from "react";

type LeaderboardEntry = {
  rank: number;
  nim: string;
  name: string;
  avatar: string;
  focus_xp: number;
  python_coins: number;
  level: number;
  level_title: string;
  daily_streak: number;
  badges_count: number;
};

type Props = {
  isOpen: boolean;
  onClose: () => void;
  currentUserNim?: string;
};

const FASTAPI_URL = "http://localhost:5000";

export function LeaderboardModal({ isOpen, onClose, currentUserNim = "2313020011" }: Props) {
  const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isOpen) return;

    let isMounted = true;
    async function fetchLeaderboard() {
      try {
        const res = await fetch(`${FASTAPI_URL}/api/leaderboard`, { cache: "no-store" });
        if (res.ok) {
          const data = await res.json();
          if (isMounted) {
            setLeaderboard(data.leaderboard || []);
          }
        }
      } catch (err) {
        console.error("Gagal mengambil leaderboard:", err);
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    fetchLeaderboard();
    return () => {
      isMounted = false;
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="asisten-modal-backdrop" onClick={onClose}>
      <div className="mda-leaderboard-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title-row">
            <span className="trophy-icon">🏆</span>
            <div>
              <h3>Papan Peringkat Kompetitif (MDA Leaderboard)</h3>
              <p className="modal-desc">
                Peringkat mahasiswa Prodi Teknik Informatika UNP Kediri berdasarkan akumulasi Focus XP &amp; Streak.
              </p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          {loading ? (
            <div className="leaderboard-loading">Memuat peringkat dari basis data MySQL...</div>
          ) : (
            <div className="leaderboard-table-wrapper">
              <table className="leaderboard-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Mahasiswa</th>
                    <th>Level &amp; Gelar</th>
                    <th>Focus XP</th>
                    <th>Streak</th>
                    <th>Koin</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((item) => {
                    const isMe = item.nim === currentUserNim;
                    return (
                      <tr key={item.nim} className={isMe ? "row-current-user" : undefined}>
                        <td className="rank-cell">
                          {item.rank === 1 ? (
                            <span className="medal gold">🥇 1</span>
                          ) : item.rank === 2 ? (
                            <span className="medal silver">🥈 2</span>
                          ) : item.rank === 3 ? (
                            <span className="medal bronze">🥉 3</span>
                          ) : (
                            <span className="rank-num">#{item.rank}</span>
                          )}
                        </td>
                        <td className="user-cell">
                          <span className="user-avatar">{item.avatar}</span>
                          <div className="user-meta">
                            <span className="user-name">
                              {item.name} {isMe && <span className="you-badge">(Kamu)</span>}
                            </span>
                            <span className="user-nim">NIM: {item.nim}</span>
                          </div>
                        </td>
                        <td>
                          <div className="level-badge-col">
                            <span className="lvl-num">Lv.{item.level}</span>
                            <span className="lvl-title">{item.level_title}</span>
                          </div>
                        </td>
                        <td className="xp-cell">
                          <strong>{item.focus_xp.toLocaleString()}</strong> XP
                        </td>
                        <td className="streak-cell">🔥 {item.daily_streak} Hari</td>
                        <td className="coins-cell">🪙 {item.python_coins}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="modal-footer-mda">
          <span>💡 <em>Dynamics MDA:</em> Selesaikan 25 menit Pomodoro (+100 XP) atau tantangan kode AST (+50 XP) untuk mendongkrak peringkatmu!</span>
        </div>
      </div>
    </div>
  );
}

