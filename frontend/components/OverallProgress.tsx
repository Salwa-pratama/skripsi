"use client";

import { useProgress } from "@/lib/progress";

export function OverallProgress() {
  const { count, total, ready } = useProgress();
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

  return (
    <div className="overall-progress" aria-label={`Progres belajar ${count} dari ${total} bab`}>
      <div className="progress-ring" aria-hidden="true">
        <svg viewBox="0 0 36 36">
          <circle className="ring-track" cx="18" cy="18" r="15.9155" />
          <circle
            className="ring-value"
            cx="18"
            cy="18"
            r="15.9155"
            pathLength={100}
            strokeDasharray={`${ready ? percentage : 0} 100`}
          />
        </svg>
        <span className="ring-label">
          <strong>{ready ? count : 0}</strong>
          <span>/{total}</span>
        </span>
      </div>
      <div className="overall-progress-copy">
        <span className="overall-progress-kicker">Progres kamu</span>
        <strong>
          {ready ? `${count} dari ${total} bab` : `${total} bab menanti`}
        </strong>
        <span>{percentage}% selesai</span>
      </div>
    </div>
  );
}
