"use client";

import { useEffect, useRef, useState } from "react";
import type { QuestRequirement } from "@/lib/quests";
import {
  CheckIcon,
  ClockIcon,
  InfoIcon,
  LightbulbIcon,
  SparklesIcon,
  WarningIcon,
} from "./icons";

type Props = {
  quest: QuestRequirement;
  chapterOrder: number;
  chapterSlug: string;
};

type AstAnalysis = {
  syntaxValid: boolean;
  syntaxError: {
    message: string;
    line: number;
    offset?: number;
    text?: string;
  } | null;
  nodesFound: string[];
  nodeDetails?: string[];
  requiredNodes: string[];
  missingNodes: string[];
  hasAllRequiredNodes: boolean;
  astTree: string;
  summary: string;
};

type RunResult = {
  success: boolean;
  stdout: string;
  stderr: string;
  timedOut?: boolean;
  ast: AstAnalysis;
  outputMatches?: boolean;
  passed: boolean;
  feedback: string;
};

export function CodeSandbox({ quest, chapterOrder, chapterSlug }: Props) {
  const [code, setCode] = useState(quest.starterCode);
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [activeTab, setActiveTab] = useState<"terminal" | "ast">("terminal");
  const [showHints, setShowHints] = useState(false);
  const [pasteAttempts, setPasteAttempts] = useState(0);
  const [pasteWarning, setPasteWarning] = useState(false);
  const [cursorLine, setCursorLine] = useState(1);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const warningTimeoutRef = useRef<number | null>(null);

  // Hitung jumlah baris kode
  const lines = code.split("\n");
  const lineCount = Math.max(lines.length, 12);

  // Trigger peringatan anti copy-paste
  function triggerPasteIntervention() {
    setPasteAttempts((prev) => prev + 1);
    setPasteWarning(true);

    if (warningTimeoutRef.current) {
      window.clearTimeout(warningTimeoutRef.current);
    }
    warningTimeoutRef.current = window.setTimeout(() => {
      setPasteWarning(false);
    }, 4500);
  }

  // Intersep aksi Paste
  function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    e.preventDefault();
    triggerPasteIntervention();
  }

  // Intersep shortcut keyboard paste (Ctrl+V, Cmd+V, Shift+Insert) dan tangani indentasi Tab
  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // 1. Cek upaya paste keyboard
    const isPasteCombo =
      ((e.ctrlKey || e.metaKey) && (e.key === "v" || e.key === "V")) ||
      (e.shiftKey && e.key === "Insert");

    if (isPasteCombo) {
      e.preventDefault();
      triggerPasteIntervention();
      return;
    }

    // 2. Dukungan Tab 4 spasi khas Python (PEP 8)
    if (e.key === "Tab") {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const spaces = "    ";

      const newCode = code.substring(0, start) + spaces + code.substring(end);
      setCode(newCode);

      // Kembalikan posisi kursor setelah 4 spasi
      window.requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + spaces.length;
      });
      return;
    }

    // 3. Dukungan Enter yang mempertahankan indentasi baris sebelumnya
    if (e.key === "Enter") {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const lineStart = code.lastIndexOf("\n", start - 1) + 1;
      const currentLine = code.substring(lineStart, start);
      const match = currentLine.match(/^(\s+)/);
      const indentation = match ? match[1] : "";

      // Bila baris berakhiran dengan ':', tambahkan 4 spasi ekstra
      const extraIndent = currentLine.trim().endsWith(":") ? "    " : "";
      const totalIndent = indentation + extraIndent;

      if (totalIndent.length > 0) {
        e.preventDefault();
        const newCode =
          code.substring(0, start) + "\n" + totalIndent + code.substring(start);
        setCode(newCode);

        window.requestAnimationFrame(() => {
          textarea.selectionStart = textarea.selectionEnd =
            start + 1 + totalIndent.length;
        });
      }
    }
  }

  // Pemantauan posisi baris kursor
  function updateCursorLine() {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const textUpToCursor = textarea.value.substring(0, textarea.selectionStart);
    const lineIndex = textUpToCursor.split("\n").length;
    setCursorLine(lineIndex);
  }

  // Menjalankan kode dan memvalidasi AST melalui API
  async function handleRunCode() {
    setIsRunning(true);
    setPasteWarning(false);

    try {
      const res = await fetch("/api/run-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code,
          chapterSlug,
        }),
      });

      const data = (await res.json()) as RunResult;
      setResult(data);

      if (data.ast && (!data.ast.syntaxValid || !data.ast.hasAllRequiredNodes)) {
        setActiveTab("ast");
      } else {
        setActiveTab("terminal");
      }
    } catch (err: any) {
      setResult({
        success: false,
        stdout: "",
        stderr: err?.message || "Koneksi ke backend runner Python gagal.",
        ast: {
          syntaxValid: false,
          syntaxError: null,
          nodesFound: [],
          requiredNodes: quest.requiredNodes,
          missingNodes: quest.requiredNodes,
          hasAllRequiredNodes: false,
          astTree: "",
          summary: "Gagal menghubungkan ke server validasi.",
        },
        passed: false,
        feedback: "Terjadi kesalahan jaringan atau server saat mengeksekusi kode.",
      });
    } finally {
      setIsRunning(false);
    }
  }

  function handleReset() {
    if (window.confirm("Kembalikan kode ke template awal? Perubahan Anda akan hilang.")) {
      setCode(quest.starterCode);
      setResult(null);
    }
  }

  function scrollToQuiz() {
    const quizEl = document.getElementById("kuis-evaluasi");
    if (quizEl) {
      quizEl.scrollIntoView({ behavior: "smooth" });
    }
  }

  useEffect(() => {
    return () => {
      if (warningTimeoutRef.current) {
        window.clearTimeout(warningTimeoutRef.current);
      }
    };
  }, []);

  return (
    <aside className="sandbox-panel" aria-label="Web Code Sandbox Anti Copy-Paste">
      {/* Header Sandbox */}
      <div className="sandbox-header">
        <div className="sandbox-title-wrap">
          <div className="sandbox-badge-row">
            <span className="sandbox-badge">
              <SparklesIcon size={13} />
              Misi Koding Bab {chapterOrder}
            </span>
            <span className="sandbox-shield-badge" title="Fitur tempel diblokir untuk melatih muscle memory">
              🛡️ Anti Copy-Paste
            </span>
          </div>
          <h2 className="sandbox-title">{quest.title}</h2>
        </div>
      </div>

      {/* Instruksi Misi */}
      <div className="sandbox-instructions">
        <p className="sandbox-summary">{quest.summary}</p>
        <div className="sandbox-steps">
          <div className="sandbox-steps-label">
            <strong>Instruksi Langkah Pengerjaan:</strong>
          </div>
          <ol className="sandbox-instruction-list">
            {quest.instructions.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ol>
        </div>

        {/* Tombol Bantuan / Hints */}
        <div className="sandbox-hints-toggle">
          <button
            type="button"
            className="sandbox-hint-btn"
            onClick={() => setShowHints(!showHints)}
          >
            <LightbulbIcon size={14} />
            {showHints ? "Sembunyikan Petunjuk" : "Buka Petunjuk (Docstring Resmi)"}
          </button>
          {showHints && (
            <div className="sandbox-hints-box">
              {quest.hints.map((hint, i) => (
                <div key={i} className="sandbox-hint-item">
                  <InfoIcon size={14} />
                  <span>{hint}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Banner Intervensi Anti Copy-Paste */}
      {pasteWarning && (
        <div className="anti-paste-banner" role="alert">
          <div className="anti-paste-banner-icon">
            <WarningIcon size={20} />
          </div>
          <div className="anti-paste-banner-content">
            <strong className="anti-paste-title">Aksi Tempel (Paste) Diblokir!</strong>
            <p className="anti-paste-desc">
              Sesuai kaidah latihan pemrograman mandiri, fitur <em>copy-paste</em> dinonaktifkan.
              Silakan ketik setiap baris kode secara manual untuk membentuk <strong>muscle memory</strong>{" "}
              dan memahami konstruksi algoritma.
            </p>
            <div className="anti-paste-counter">
              Percobaan paste terdeteksi: <strong>{pasteAttempts}x</strong>
            </div>
          </div>
        </div>
      )}

      {/* Editor Pengetikan Kode */}
      <div className="sandbox-editor-wrapper">
        <div className="sandbox-editor-toolbar">
          <span className="sandbox-editor-filename">
            main.py <span className="sandbox-cursor-indicator">(Baris {cursorLine})</span>
          </span>
          <div className="sandbox-toolbar-actions">
            <button
              type="button"
              className="sandbox-btn-reset"
              onClick={handleReset}
              title="Reset ke template awal"
            >
              Reset
            </button>
          </div>
        </div>

        <div className="sandbox-editor-container">
          {/* Nomor Baris */}
          <div className="sandbox-line-numbers" aria-hidden="true">
            {Array.from({ length: lineCount }, (_, i) => (
              <span
                key={i + 1}
                className={i + 1 === cursorLine ? "line-number active" : "line-number"}
              >
                {i + 1}
              </span>
            ))}
          </div>

          {/* Area Textarea dengan Proteksi Anti-Paste */}
          <textarea
            ref={textareaRef}
            className="sandbox-textarea"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onPaste={handlePaste}
            onKeyDown={handleKeyDown}
            onKeyUp={updateCursorLine}
            onClick={updateCursorLine}
            onContextMenu={(e) => {
              // Blokir menu klik kanan paste pada textarea
              e.preventDefault();
              triggerPasteIntervention();
            }}
            spellCheck={false}
            autoCapitalize="off"
            autoComplete="off"
            autoCorrect="off"
            placeholder="Ketik baris kode Python Anda secara manual di sini..."
          />
        </div>
      </div>

      {/* Tombol Aksi Eksekusi & Validasi */}
      <div className="sandbox-action-bar">
        <button
          type="button"
          className="sandbox-btn-run"
          onClick={handleRunCode}
          disabled={isRunning}
        >
          {isRunning ? (
            <>
              <span className="spinner" aria-hidden="true" />
              <span>Memeriksa Sintaks & AST...</span>
            </>
          ) : (
            <>
              <span>▶</span>
              <span>Jalankan Kode & Validasi AST</span>
            </>
          )}
        </button>
      </div>

      {/* Panel Hasil (Terminal & AST) */}
      {result && (
        <div className="sandbox-result-box">
          <div className="sandbox-result-tabs">
            <button
              type="button"
              className={`sandbox-tab ${activeTab === "terminal" ? "active" : ""}`}
              onClick={() => setActiveTab("terminal")}
            >
              Output Konsol {result.success ? "✅" : "❌"}
            </button>
            <button
              type="button"
              className={`sandbox-tab ${activeTab === "ast" ? "active" : ""}`}
              onClick={() => setActiveTab("ast")}
            >
              Validasi AST {result.ast.hasAllRequiredNodes && result.ast.syntaxValid ? "✅" : "⚠️"}
            </button>
          </div>

          {/* Tab 1: Terminal Konsol */}
          {activeTab === "terminal" && (
            <div className="sandbox-terminal">
              {result.stdout && (
                <pre className="terminal-stdout">{result.stdout}</pre>
              )}
              {result.stderr && (
                <pre className="terminal-stderr">{result.stderr}</pre>
              )}
              {!result.stdout && !result.stderr && (
                <div className="terminal-empty">Program berjalan tanpa luaran teks (stdout).</div>
              )}
              {result.timedOut && (
                <div className="terminal-timeout">
                  ⚠️ Eksekusi dihentikan paksa karena melebihi batas waktu 4 detik.
                </div>
              )}
            </div>
          )}

          {/* Tab 2: Validasi AST */}
          {activeTab === "ast" && (
            <div className="sandbox-ast-panel">
              <div className="ast-status-card">
                <strong>Status Sintaksis: </strong>
                {result.ast.syntaxValid ? (
                  <span className="ast-tag-valid">Sintaks Valid (Lolos ast.parse)</span>
                ) : (
                  <span className="ast-tag-invalid">SyntaxError Terdeteksi</span>
                )}
              </div>

              {/* Pemeriksaan Konstruksi Node yang Diwajibkan */}
              <div className="ast-requirements-list">
                <div className="ast-subheading">Kebutuhan Konstruksi Algoritma (AST):</div>
                <div className="ast-nodes-grid">
                  {quest.requiredNodes.map((nodeName) => {
                    const isPresent = result.ast.nodesFound.includes(nodeName);
                    return (
                      <div
                        key={nodeName}
                        className={`ast-node-card ${isPresent ? "fulfilled" : "unfulfilled"}`}
                      >
                        <div className="ast-node-header">
                          <span className="ast-node-name">ast.{nodeName}</span>
                          <span className="ast-node-badge">
                            {isPresent ? "Terpenuhi" : "Belum Ada"}
                          </span>
                        </div>
                        <div className="ast-node-desc">
                          {quest.nodeExplanations[nodeName] || "Simpul sintaksis"}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Pohon Sintaks Lengkap (Expandable) */}
              {result.ast.astTree && (
                <details className="ast-details">
                  <summary className="ast-details-summary">
                    Lihat Struktur Lengkap Pohon Sintaks (ast.dump)
                  </summary>
                  <pre className="ast-tree-pre">{result.ast.astTree}</pre>
                </details>
              )}
            </div>
          )}

          {/* Umpan Balik Status Evaluasi */}
          <div className={`sandbox-feedback-card ${result.passed ? "passed" : "needs-work"}`}>
            <div className="feedback-message">{result.feedback}</div>
            {result.passed && (
              <div className="feedback-next-action">
                <button
                  type="button"
                  className="btn-continue-quiz"
                  onClick={scrollToQuiz}
                >
                  <CheckIcon size={16} />
                  <span>Lolos Validasi! Lanjut ke Kuis Pasca-Sesi ➔</span>
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </aside>
  );
}
