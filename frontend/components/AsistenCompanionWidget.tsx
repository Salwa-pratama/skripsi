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
  live_flags?: {
    is_phone: boolean;
    is_head_down: boolean;
  };
  absence_tracking?: {
    is_user_present: boolean;
    tolerance_exceeded: boolean;
  };
};

type SystemStatus = {
  camera: {
    connected: boolean;
    fps: number;
    source: string;
  };
  pomodoro: PomodoroStatus;
  ai: {
    distraction_enabled: boolean;
    detected_emotion: string;
  };
};

const FASTAPI_URL = "http://localhost:5000";

export function AsistenCompanionWidget() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [showCameraModal, setShowCameraModal] = useState<boolean>(false);
  const [streamKey, setStreamKey] = useState<number>(Date.now());
  const [isActionLoading, setIsActionLoading] = useState<boolean>(false);

  const openCameraModal = () => {
    setStreamKey(Date.now());
    setShowCameraModal(true);
  };

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
  const isPhone = status?.pomodoro?.live_flags?.is_phone;
  const isAbsent = status?.pomodoro?.absence_tracking?.is_user_present === false;

  return (
    <div className="asisten-companion-container">
      {/* Tombol Utama Companion di Topbar */}
      <div className="asisten-topbar-pill">
        <div className="asisten-robot-avatar" title={`Status Emosi Robot: ${emotion}`}>
          {emotion === "ANGRY" || isPhone ? (
            <span className="emotion-icon angry">😾</span>
          ) : emotion === "SURPRISED" || isAbsent ? (
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
                ? isPhone
                  ? "HP TERDETEKSI!"
                  : isAbsent
                  ? "PENGGUNA ABSEN!"
                  : emotion === "HAPPY"
                  ? "SELEBRASI QUEST!"
                  : isRunning
                  ? "SESI FOKUS 25M"
                  : "ROBOT MOCHI SIAP"
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

            <button
              type="button"
              className="btn-pomo-icon camera-btn"
              onClick={openCameraModal}
              title="Pratinjau Sudut Pandang Kamera Robot ESP32-S3"
            >
              📷
            </button>
          </div>
        )}
      </div>

      {/* Alert Banner Peringatan Distraksi Visual di Atas IDE jika Terdeteksi HP / Absen */}
      {isConnected && isRunning && (isPhone || isAbsent) && (
        <div className={`asisten-live-alert ${isPhone ? "alert-phone" : "alert-absent"}`}>
          <div className="alert-content">
            <span className="alert-emoji">{isPhone ? "⚠️📱" : "⚠️👤"}</span>
            <span className="alert-text">
              {isPhone
                ? "Robot mendeteksi keberadaan Handphone di meja belajar! Singkirkan ponsel untuk menjaga Focus XP dan ekspresi Mochi."
                : "Robot mendeteksi meja kosong! Kembali ke tempat belajar agar Daily Streak tidak terpotong."}
            </span>
          </div>
        </div>
      )}

      {/* Modal Pratinjau Kamera OV5640 */}
      {showCameraModal && (
        <div className="asisten-modal-backdrop" onClick={() => setShowCameraModal(false)}>
          <div className="asisten-modal-box" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>📷 Sudut Pandang Asisten Belajar (OV5640)</h3>
              <button
                type="button"
                className="modal-close-btn"
                onClick={() => setShowCameraModal(false)}
              >
                ✕
              </button>
            </div>
            <div className="modal-body">
              <p className="modal-desc">
                Stream real-time dari kamera ESP32-S3 dengan deteksi objek (HP &amp; Keberadaan
                Pengguna). • <strong>Status:</strong>{" "}
                <span style={{ color: status?.camera?.connected ? "#10b981" : "#ef4444" }}>
                  {status?.camera?.connected
                    ? `Terhubung (${status.camera.fps ?? 0} FPS)`
                    : "Menghubungkan..."}
                </span>
              </p>
              <div className="camera-stream-wrapper">
                {/* Direct High-Performance MJPEG Feed dari FastAPI */}
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  key={streamKey}
                  src={`${FASTAPI_URL}/video_feed?t=${streamKey}`}
                  alt="Live Camera Feed dari ESP32"
                  className="camera-stream-img"
                  onError={(e) => {
                    const target = e.currentTarget;
                    target.style.display = "none";
                    const errEl = document.getElementById("camera-stream-error");
                    if (errEl) errEl.style.display = "block";
                  }}
                />
                <div id="camera-stream-error" style={{ display: "none" }} className="stream-error-box">
                  <p>Stream kamera ESP32 belum terhubung atau port 5000 offline.</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

