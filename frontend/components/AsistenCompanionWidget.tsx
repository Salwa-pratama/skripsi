"use client";

import { useEffect, useState } from "react";

type PomodoroStatus = {
  status: "stopped" | "running" | "paused" | "completed";
  mode: "work" | "short_break" | "long_break";
  formatted_time: string;
  time_left: number;
  current_cycle: number;
  target_cycles: number;
  focus_score: number;
  emotion?: string;
};

type SystemStatus = {
  pomodoro: PomodoroStatus;
  ai: {
    detected_emotion: string;
    retrieval_ready?: boolean;
    voice_gender?: string;
    voice_model?: string;
  };
};

const FASTAPI_URL = "http://localhost:5000";

export function AsistenCompanionWidget() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;

    async function fetchStatus() {
      try {
        const res = await fetch(`${FASTAPI_URL}/api/status`, {
          cache: "no-store",
        });
        if (res.ok) {
          const data = (await res.json()) as SystemStatus;
          if (isMounted) {
            setStatus(data);
            setIsConnected(true);
          }
        } else {
          if (isMounted) setIsConnected(false);
        }
      } catch {
        if (isMounted) setIsConnected(false);
      }
    }

    fetchStatus();
    const interval = setInterval(fetchStatus, 1000);
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  async function handlePomodoroAction(action: "start" | "pause" | "reset") {
    setIsActionLoading(true);
    try {
      await fetch(`${FASTAPI_URL}/api/pomodoro/${action}`, {
        method: "POST",
      });
      // Segera refresh status
      const res = await fetch(`${FASTAPI_URL}/api/status`);
      if (res.ok) {
        setStatus(await res.json());
      }
    } catch (err) {
      console.error("Gagal mengirim aksi pomodoro:", err);
    } finally {
      setIsActionLoading(false);
    }
  }

  // Tentukan badge emosi robot
  const emotion = status?.pomodoro?.emotion || status?.ai?.detected_emotion || "NORMAL";
  const isRunning = status?.pomodoro?.status === "running";

  return (
    <div className="asisten-companion-container">
      {/* Tombol Utama Companion di Topbar */}
      <div className="asisten-topbar-pill">
        <div className="asisten-robot-avatar" title={`Status Emosi Robot: ${emotion}`}>
          {emotion === "ANGRY" ? (
            <span className="emotion-icon angry">😾</span>
          ) : emotion === "SURPRISED" ? (
            <span className="emotion-icon surprised">🙀</span>
          ) : emotion === "HAPPY" ? (
            <span className="emotion-icon happy">😸</span>
          ) : emotion === "SLEEP" ? (
            <span className="emotion-icon sleep">😴</span>
          ) : isRunning ? (
            <span className="emotion-icon focus">🤖</span>
          ) : (
            <span className="emotion-icon normal">🤖</span>
          )}
        </div>

        <div className="asisten-info-col">
          <div className="asisten-status-line">
            <span className={`status-dot ${isConnected ? "online" : "offline"}`} />
            <span className="asisten-label">
              {isConnected
                ? emotion === "HAPPY"
                  ? "SELEBRASI QUEST!"
                  : isRunning
                  ? "SESI FOKUS 25M"
                  : "ASISTEN BELAJAR SIAP"
                : "ROBOT OFFLINE"}
            </span>
          </div>

          {isConnected && status?.pomodoro && (
            <div className="asisten-timer-line">
              <span className="timer-digits">{status.pomodoro.formatted_time}</span>
              <span className="cycle-badge">
                [{status.pomodoro.current_cycle}/{status.pomodoro.target_cycles}]
              </span>
              <span className="focus-badge">F:{status.pomodoro.focus_score}%</span>
            </div>
          )}
        </div>

        {/* Action Controls */}
        {isConnected && (
          <div className="asisten-controls">
            {!isRunning ? (
              <button
                type="button"
                className="btn-pomo-action start"
                onClick={() => handlePomodoroAction("start")}
                disabled={isActionLoading}
                title="Mulai Sesi Fokus Pomodoro (25 Menit)"
              >
                ▶ Mulai Fokus
              </button>
            ) : (
              <button
                type="button"
                className="btn-pomo-action pause"
                onClick={() => handlePomodoroAction("pause")}
                disabled={isActionLoading}
                title="Jeda Sesi"
              >
                ⏸ Jeda
              </button>
            )}

            <button
              type="button"
              className="btn-pomo-icon"
              onClick={() => handlePomodoroAction("reset")}
              title="Reset Timer"
            >
              🔄
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

