"use client";

import { useProgress } from "@/lib/progress";

export function ProgressSummary() {
  const { count, total, ready } = useProgress();
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

  return (
    <div className="progress-summary">
      <div className="progress-summary-head">
        <span>Progres belajar</span>
        <strong>
          {ready ? count : 0}/{total}
        </strong>
      </div>
      <div
        className="progress-bar"
        role="progressbar"
        aria-valuemin={0}
        aria-valuemax={total}
        aria-valuenow={ready ? count : 0}
        aria-label="Progres belajar"
      >
        <span style={{ width: `${ready ? percentage : 0}%` }} />
      </div>
      <p>{percentage === 100 ? "Semua bab selesai. Mantap!" : "Tandai bab yang sudah kamu tuntaskan."}</p>
    </div>
  );
}
