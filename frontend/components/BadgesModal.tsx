"use client";

type BadgeItem = {
  id: string;
  name: string;
  icon: string;
  description: string;
  criteria: string;
};

const ALL_BADGES: BadgeItem[] = [
  {
    id: "zero_ai",
    name: "Zero AI Dependency",
    icon: "🛡️",
    description: "Menolak jalan pintas copy-paste GenAI dan mengetik kode secara manual.",
    criteria: "Selesaikan quest tanpa menyalin kode",
  },
  {
    id: "zen_focus",
    name: "Zen Focus Master",
    icon: "🧘",
    description: "Menuntaskan 25 menit sesi Pomodoro tanpa terdeteksi smartphone di meja.",
    criteria: "Sesi Pomodoro 100% fokus tanpa insiden HP",
  },
  {
    id: "ast_architect",
    name: "AST Architect",
    icon: "⚡",
    description: "Berhasil menyusun pohon sintaksis kode abstrak yang valid dan terstruktur.",
    criteria: "Lolos seluruh pemeriksaan simpul ast.If / ast.For",
  },
  {
    id: "streak_builder",
    name: "Streak Warrior",
    icon: "🔥",
    description: "Membangun konsistensi dan disiplin belajar berturut-turut tanpa jeda.",
    criteria: "Pertahankan daily streak minimal 3 hari",
  },
  {
    id: "robot_sync",
    name: "Mochi Synchronizer",
    icon: "🤖",
    description: "Menghubungkan asisten fisik IoT ESP32-S3 dengan web pembelajaran.",
    criteria: "Terhubung ke stream kamera & endpoint OLED",
  },
];

type Props = {
  isOpen: boolean;
  onClose: () => void;
  unlockedBadges: string[];
};

export function BadgesModal({ isOpen, onClose, unlockedBadges }: Props) {
  if (!isOpen) return null;

  return (
    <div className="asisten-modal-backdrop" onClick={onClose}>
      <div className="mda-badges-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="header-title-row">
            <span className="trophy-icon">🎖️</span>
            <div>
              <h3>Lencana Prestasi Digital (MDA Achievements)</h3>
              <p className="modal-desc">
                Penghargaan atas kedisiplinan fokus belajar dan penguasaan fondasi sintaks Python.
              </p>
            </div>
          </div>
          <button type="button" className="modal-close-btn" onClick={onClose}>
            ✕
          </button>
        </div>

        <div className="modal-body">
          <div className="badges-grid">
            {ALL_BADGES.map((badge) => {
              const isUnlocked = unlockedBadges.includes(badge.id);
              return (
                <div key={badge.id} className={`badge-card ${isUnlocked ? "unlocked" : "locked"}`}>
                  <div className="badge-icon-box">
                    <span className="badge-emoji">{badge.icon}</span>
                    {!isUnlocked && <span className="lock-tag">🔒 Terkunci</span>}
                  </div>
                  <div className="badge-info">
                    <h4 className="badge-name">{badge.name}</h4>
                    <p className="badge-desc">{badge.description}</p>
                    <span className="badge-criteria">Syarat: {badge.criteria}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="modal-footer-mda">
          <span>Terkumpul: <strong>{unlockedBadges.length}</strong> dari <strong>{ALL_BADGES.length}</strong> lencana prestasi.</span>
        </div>
      </div>
    </div>
  );
}

