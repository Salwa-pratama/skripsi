"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { Blocks } from "@/components/Blocks";
import { ChapterProgressButton } from "@/components/ChapterProgressButton";
import { Notes } from "@/components/Notes";
import { Quiz } from "@/components/Quiz";
import { AsistenCompanionWidget } from "@/components/AsistenCompanionWidget";
import { GamificationBar } from "@/components/GamificationBar";
import {
  ArrowLeftIcon,
  ArrowRightIcon,
  BookIcon,
  CheckIcon,
  ClockIcon,
  ExternalLinkIcon,
  GraduationIcon,
  InfoIcon,
  LightbulbIcon,
  ListChecksIcon,
  SparklesIcon,
  WarningIcon,
} from "@/components/icons";
import type { QuestRequirement } from "@/lib/quests";
import type { ChapterContent, ChapterMeta, QuizQuestion } from "@/lib/types";

type Props = {
  chapter: ChapterMeta;
  content: ChapterContent;
  quiz: QuizQuestion[];
  quest?: QuestRequirement;
  headings: { id: string; text: string; level: number }[];
  previous: ChapterMeta | null;
  next: ChapterMeta | null;
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

function highlightPython(code: string): string {
  const escapeHtml = (str: string) =>
    str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  const tokenRegex =
    /(#[^\n]*)|("""[\s\S]*?"""|'''[\s\S]*?'''|f?"(?:[^"\\]|\\.)*"|f?'(?:[^'\\]|\\.)*')|(\b(?:def|class|if|elif|else|for|while|return|import|from|as|pass|break|continue|in|is|not|and|or|lambda|with|try|except|finally|raise|yield)\b)|(\b(?:True|False|None)\b)|(\b(?:print|type|len|range|int|float|str|bool|list|dict|set|tuple|abs|round|enumerate|zip|sum|min|max|super|input)\b(?=\s*\())|(\b[a-zA-Z_]\w*\b(?=\s*\())|(\b\d+(?:\.\d+)?\b)|(\+|\-|\*|\/|\/\/|\%|\*\*|\=|\=\=|\!\=|\<|\>|\<\=|\>\=)|([a-zA-Z_]\w*)|([^\s\w]+|\s+)/g;

  return code.replace(
    tokenRegex,
    (
      match,
      comment,
      string,
      keyword,
      constant,
      builtin,
      func,
      num,
      op,
      ident,
      _other,
    ) => {
      if (comment) return `<span class="tok-comment">${escapeHtml(comment)}</span>`;
      if (string) return `<span class="tok-string">${escapeHtml(string)}</span>`;
      if (keyword) return `<span class="tok-keyword">${escapeHtml(keyword)}</span>`;
      if (constant) return `<span class="tok-constant">${escapeHtml(constant)}</span>`;
      if (builtin) return `<span class="tok-builtin">${escapeHtml(builtin)}</span>`;
      if (func) return `<span class="tok-function">${escapeHtml(func)}</span>`;
      if (num) return `<span class="tok-number">${escapeHtml(num)}</span>`;
      if (op) return `<span class="tok-operator">${escapeHtml(op)}</span>`;
      if (ident) return `<span class="tok-ident">${escapeHtml(ident)}</span>`;
      return escapeHtml(match);
    },
  );
}

export function WorkspaceIDE({
  chapter,
  content,
  quiz,
  quest,
  headings,
  previous,
  next,
}: Props) {
  // State untuk Editor & Runner
  const [code, setCode] = useState(quest?.starterCode ?? "");
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<RunResult | null>(null);
  const [activeBottomTab, setActiveBottomTab] = useState<"terminal" | "ast" | "hints">("terminal");
  const [pasteAttempts, setPasteAttempts] = useState(0);
  const [pasteWarning, setPasteWarning] = useState(false);
  const [cursorLine, setCursorLine] = useState(1);
  const [cursorCol, setCursorCol] = useState(1);

  // State untuk drawer samping (Kurikulum & TOC)
  const [isTocOpen, setIsTocOpen] = useState(false);

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const preRef = useRef<HTMLPreElement>(null);
  const warningTimeoutRef = useRef<number | null>(null);
  const leftPaneRef = useRef<HTMLDivElement>(null);

  const highlightedCode = useMemo(() => highlightPython(code), [code]);

  function handleScroll() {
    if (textareaRef.current && preRef.current) {
      preRef.current.scrollTop = textareaRef.current.scrollTop;
      preRef.current.scrollLeft = textareaRef.current.scrollLeft;
    }
  }

  const lines = code.split("\n");
  const lineCount = Math.max(lines.length, 16);

  // Intervensi Anti Copy-Paste
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

  function handlePaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    e.preventDefault();
    triggerPasteIntervention();
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // 1. Blokir shortcut paste keyboard
    const isPasteCombo =
      ((e.ctrlKey || e.metaKey) && (e.key === "v" || e.key === "V")) ||
      (e.shiftKey && e.key === "Insert");

    if (isPasteCombo) {
      e.preventDefault();
      triggerPasteIntervention();
      return;
    }

    // 2. Tab 4 Spasi standar Python PEP 8
    if (e.key === "Tab") {
      e.preventDefault();
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const end = textarea.selectionEnd;
      const spaces = "    ";

      const newCode = code.substring(0, start) + spaces + code.substring(end);
      setCode(newCode);

      window.requestAnimationFrame(() => {
        textarea.selectionStart = textarea.selectionEnd = start + spaces.length;
      });
      return;
    }

    // 3. Enter auto-indent
    if (e.key === "Enter") {
      const textarea = textareaRef.current;
      if (!textarea) return;

      const start = textarea.selectionStart;
      const lineStart = code.lastIndexOf("\n", start - 1) + 1;
      const currentLine = code.substring(lineStart, start);
      const match = currentLine.match(/^(\s+)/);
      const indentation = match ? match[1] : "";

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

  function updateCursorPos() {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const textUpToCursor = textarea.value.substring(0, textarea.selectionStart);
    const lineArray = textUpToCursor.split("\n");
    setCursorLine(lineArray.length);
    setCursorCol(lineArray[lineArray.length - 1].length + 1);
  }

  async function handleRunCode() {
    if (!quest) return;
    setIsRunning(true);
    setPasteWarning(false);

    try {
      const res = await fetch("/api/run-code", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          code,
          chapterSlug: chapter.slug,
        }),
      });

      const data = (await res.json()) as RunResult;
      setResult(data);

      if (data.passed) {
        // Beritahu backend Python untuk memicu ekspresi selebrasi (HAPPY) di robot OLED
        fetch("http://localhost:5000/api/pomodoro/quest_passed", {
          method: "POST",
        }).catch(() => {});
      }

      if (data.ast && (!data.ast.syntaxValid || !data.ast.hasAllRequiredNodes)) {
        setActiveBottomTab("ast");
      } else {
        setActiveBottomTab("terminal");
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
      setActiveBottomTab("terminal");
    } finally {
      setIsRunning(false);
    }
  }

  function handleReset() {
    if (quest && window.confirm("Kembalikan kode ke template awal? Perubahan Anda akan hilang.")) {
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
    <div className="ide-fullscreen-workspace">
      {/* -------------------------------- TOP NAVBAR (IDE HEADER) -------------------------------- */}
      <header className="ide-topbar">
        <div className="ide-topbar-left">
          <Link href="/materi" className="ide-btn-back" title="Kembali ke Daftar Kurikulum">
            <ArrowLeftIcon size={16} />
            <span>Kurikulum</span>
          </Link>
          <span className="ide-separator">/</span>
          <div className="ide-chapter-badge">
            Bab {String(chapter.order).padStart(2, "0")}
          </div>
          <h1 className="ide-chapter-title">{chapter.title}</h1>
        </div>

        <div className="ide-topbar-center">
          <GamificationBar />
          <AsistenCompanionWidget />
          <div className="ide-anti-paste-pill" title="Sistem menonaktifkan fitur copy-paste guna melatih muscle memory dan algoritma mandiri">
            <span className="ide-shield-icon">🛡️</span>
            <span>Anti Copy-Paste: <strong>Aktif</strong></span>
          </div>
        </div>

        <div className="ide-topbar-right">
          <button
            type="button"
            className="ide-btn-outline"
            onClick={() => setIsTocOpen(!isTocOpen)}
            title="Daftar Isi Halaman"
          >
            <ListChecksIcon size={15} />
            <span>{isTocOpen ? "Tutup Indeks" : "Daftar Isi"}</span>
          </button>

          <button
            type="button"
            className="ide-btn-run-primary"
            onClick={handleRunCode}
            disabled={isRunning}
            title="Eksekusi kode dan validasi simpul AST (Ctrl+Enter)"
          >
            {isRunning ? (
              <>
                <span className="spinner" aria-hidden="true" />
                <span>Memvalidasi AST...</span>
              </>
            ) : (
              <>
                <span>▶</span>
                <span>Jalankan & Validasi AST</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* -------------------------------- MAIN DUAL-PANE BODY -------------------------------- */}
      <div className="ide-main-split">
        {/* =========================================================================
            PANEL KIRI (50%): Dokumentasi Resmi PSF, Teori, dan Instruksi Misi
           ========================================================================= */}
        <section className="ide-left-pane" ref={leftPaneRef}>
          <div className="ide-left-content">
            {/* Header Dokumentasi */}
            <header className="chapter-header">
              <div className="chapter-chips">
                <span className="chip chip-accent">Bab {String(chapter.order).padStart(2, "0")}</span>
                <span className="chip">
                  <GraduationIcon size={14} />
                  {chapter.level}
                </span>
                <span className="chip">
                  <ClockIcon size={14} />
                  {chapter.minutes} menit
                </span>
                <span className="chip">
                  <BookIcon size={14} />
                  Sumber resmi PSF ID
                </span>
              </div>
              <h2 className="chapter-page-title">{chapter.title}</h2>
              <p className="chapter-subtitle">{chapter.subtitle}</p>
              <p className="chapter-description">{chapter.description}</p>
              <p className="chapter-source-line">
                Teks materi: dokumentasi CPython {content.docVersion} · Berlisensi PSF License.
                Diselaraskan dengan repositori resmi Python Software Foundation Bahasa Indonesia.
              </p>
            </header>

            {/* Misi Koding (Quest Box Utama) */}
            {quest && (
              <div className="ide-quest-card">
                <div className="ide-quest-head">
                  <div className="ide-quest-tag">
                    <SparklesIcon size={14} />
                    Misi Latihan Mandiri (25 Menit)
                  </div>
                  <h3 className="ide-quest-title">{quest.title}</h3>
                </div>
                <p className="ide-quest-summary">{quest.summary}</p>

                <div className="ide-quest-steps">
                  <strong>Instruksi Langkah Pengerjaan:</strong>
                  <ol className="ide-quest-ol">
                    {quest.instructions.map((step, idx) => (
                      <li key={idx}>{step}</li>
                    ))}
                  </ol>
                </div>

                <div className="ide-quest-hints-row">
                  <button
                    type="button"
                    className="ide-btn-hint-inline"
                    onClick={() => setActiveBottomTab("hints")}
                  >
                    <LightbulbIcon size={14} />
                    <span>Lihat Petunjuk di Panel Bawah ({quest.hints.length})</span>
                  </button>
                  <span className="ide-quest-nodes-preview">
                    Wajib mengandung:{" "}
                    {quest.requiredNodes.map((n) => (
                      <code key={n}>ast.{n}</code>
                    ))}
                  </span>
                </div>
              </div>
            )}

            {/* Tujuan Pembelajaran */}
            <section className="learning-objectives" aria-labelledby="objectives-title">
              <div className="card-heading">
                <p className="section-kicker">
                  <ListChecksIcon size={15} />
                  Setelah bab ini
                </p>
                <h3 id="objectives-title">Tujuan pembelajaran</h3>
              </div>
              <ul className="objective-list">
                {chapter.objectives.map((objective) => (
                  <li key={objective}>
                    <span className="objective-check">
                      <CheckIcon size={14} />
                    </span>
                    <span>{objective}</span>
                  </li>
                ))}
              </ul>
            </section>

            {/* Poin Kunci */}
            <section className="key-points" aria-labelledby="key-points-title">
              <div className="card-heading">
                <p className="section-kicker">Ringkasan cepat</p>
                <h3 id="key-points-title">Poin kunci</h3>
              </div>
              <div className="key-point-grid">
                {chapter.keyPoints.map((point, index) => (
                  <div className="key-point" key={point}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <p>{point}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* API Highlights */}
            {content.api.length > 0 && (
              <section className="api-highlights" aria-labelledby="api-title">
                <div className="card-heading">
                  <p className="section-kicker">Referensi cepat</p>
                  <h3 id="api-title">Objek Python di bab ini</h3>
                </div>
                <div className="api-chip-row">
                  {content.api.map((entry) => (
                    <a
                      className="api-chip"
                      href={entry.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      key={`${entry.role}-${entry.name}`}
                      title={`${entry.role.replace("py:", "")} · ${entry.doc}`}
                    >
                      <code>{entry.name}</code>
                      <ExternalLinkIcon size={13} />
                    </a>
                  ))}
                </div>
              </section>
            )}

            {/* Banner Sumber PSF Indonesia */}
            <div className="official-intro">
              <span className="psf-badge">PSF ID</span>
              <p>
                Materi di bawah disadur dari dokumentasi resmi{" "}
                <strong>{chapter.sources[0]?.label ?? "CPython PSF"}</strong> yang telah
                diselaraskan ke Bahasa Indonesia (PEP 545). Ketiklah kode contoh secara manual
                di panel editor kanan!
              </p>
            </div>

            {/* Blok Konten Dokumentasi Resmi */}
            {content.groups.map((group, index) => (
              <section className="source-group" key={`${group.source.doc}-${index}`}>
                <div className="source-banner">
                  <div className="source-banner-main">
                    <span className="source-badge">Materi resmi</span>
                    <div>
                      <p>{group.source.label}</p>
                      <span>{group.source.url.replace("https://", "")}</span>
                    </div>
                  </div>
                  <a
                    href={group.source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="source-link"
                  >
                    Halaman asli
                    <ExternalLinkIcon size={14} />
                  </a>
                </div>
                <div className="prose">
                  <Blocks blocks={group.blocks} />
                </div>
              </section>
            ))}

            {/* Kuis Evaluasi Pasca-Sesi & Catatan */}
            <div id="kuis-evaluasi" className="ide-quiz-container">
              <Quiz questions={quiz} />
            </div>

            <Notes slug={chapter.slug} />
            <ChapterProgressButton slug={chapter.slug} />

            {/* Navigasi Pager Bab */}
            <nav className="chapter-pager" aria-label="Navigasi antar bab">
              {previous ? (
                <Link className="pager-card pager-prev" href={`/materi/${previous.slug}`}>
                  <span>
                    <ArrowLeftIcon size={15} />
                    Sebelumnya
                  </span>
                  <strong>{previous.title}</strong>
                </Link>
              ) : (
                <Link className="pager-card pager-prev" href="/materi">
                  <span>
                    <ArrowLeftIcon size={15} />
                    Kembali
                  </span>
                  <strong>Kurikulum</strong>
                </Link>
              )}
              {next ? (
                <Link className="pager-card pager-next" href={`/materi/${next.slug}`}>
                  <span>
                    Selanjutnya
                    <ArrowRightIcon size={15} />
                  </span>
                  <strong>{next.title}</strong>
                </Link>
              ) : (
                <Link className="pager-card pager-next" href="/indeks">
                  <span>
                    Selesai
                    <ArrowRightIcon size={15} />
                  </span>
                  <strong>Jelajahi indeks API</strong>
                </Link>
              )}
            </nav>
          </div>

          {/* Drawer TOC (Daftar Isi Halaman) */}
          {isTocOpen && (
            <aside className="ide-toc-drawer">
              <div className="ide-toc-header">
                <strong>Daftar Isi Materi</strong>
                <button
                  type="button"
                  className="ide-toc-close"
                  onClick={() => setIsTocOpen(false)}
                >
                  ✕
                </button>
              </div>
              <nav className="ide-toc-nav">
                {headings.map((h) => (
                  <a
                    key={h.id}
                    href={`#${h.id}`}
                    className={`ide-toc-item level-${h.level}`}
                    onClick={() => setIsTocOpen(false)}
                  >
                    {h.text}
                  </a>
                ))}
              </nav>
            </aside>
          )}
        </section>

        {/* =========================================================================
            PANEL KANAN (50%): Visual Studio Code Style (Editor Canvas + Bottom Console)
           ========================================================================= */}
        <section className="ide-right-pane">
          {/* BANNER INTERVENSI ANTI COPY-PASTE */}
          {pasteWarning && (
            <div className="ide-anti-paste-banner" role="alert">
              <div className="ide-paste-icon">
                <WarningIcon size={20} />
              </div>
              <div className="ide-paste-text">
                <strong>Aksi Tempel (Paste) Diblokir!</strong>
                <p>
                  Sesuai batasan sistem skripsi, fitur <em>copy-paste</em> dinonaktifkan.
                  Anda diwajibkan <strong>mengetik setiap baris kode secara manual</strong> untuk
                  melatih <em>muscle memory</em> dan alur berpikir komputasional.
                </p>
                <span className="ide-paste-count">
                  Upaya tempel diblokir: <strong>{pasteAttempts}x</strong>
                </span>
              </div>
            </div>
          )}

          {/* 1. BAGIAN ATAS: Editor Code Canvas ala VS Code */}
          <div className="ide-editor-container">
            {/* Tab Bar Editor */}
            <div className="ide-editor-tabbar">
              <div className="ide-tab active">
                <span className="ide-python-icon">🐍</span>
                <span className="ide-tab-filename">main.py</span>
              </div>
              <div className="ide-editor-meta">
                <span className="ide-cursor-pos">
                  Ln {cursorLine}, Col {cursorCol}
                </span>
                <button
                  type="button"
                  className="ide-btn-reset-editor"
                  onClick={handleReset}
                  title="Kembalikan template awal"
                >
                  Reset Template
                </button>
              </div>
            </div>

            {/* Area Teks & Nomor Baris dengan Syntax Highlighting One Dark Pro */}
            <div className="ide-editor-body">
              <div className="ide-line-numbers" aria-hidden="true">
                {Array.from({ length: lineCount }, (_, i) => (
                  <span
                    key={i + 1}
                    className={i + 1 === cursorLine ? "ide-ln active" : "ide-ln"}
                  >
                    {i + 1}
                  </span>
                ))}
              </div>

              <div className="ide-code-layer-wrap">
                <pre
                  ref={preRef}
                  className="ide-highlight-overlay"
                  aria-hidden="true"
                  dangerouslySetInnerHTML={{ __html: highlightedCode + "\n" }}
                />

                <textarea
                  ref={textareaRef}
                  className="ide-code-textarea"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  onScroll={handleScroll}
                  onPaste={handlePaste}
                  onKeyDown={handleKeyDown}
                  onKeyUp={updateCursorPos}
                  onClick={updateCursorPos}
                  onContextMenu={(e) => {
                    e.preventDefault();
                    triggerPasteIntervention();
                  }}
                  spellCheck={false}
                  autoCapitalize="off"
                  autoComplete="off"
                  autoCorrect="off"
                  placeholder="# Ketikkan baris kode Python Anda secara manual di sini..."
                />
              </div>
            </div>
          </div>

          {/* 2. BAGIAN BAWAH: Integrated Terminal & AST Panel ala VS Code */}
          <div className="ide-terminal-container">
            {/* Terminal Tab Bar */}
            <div className="ide-terminal-tabs">
              <button
                type="button"
                className={`ide-term-tab ${activeBottomTab === "terminal" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("terminal")}
              >
                <span>TERMINAL OUTPUT</span>
                {result && (
                  <span className={`ide-tab-dot ${result.success ? "success" : "error"}`} />
                )}
              </button>

              <button
                type="button"
                className={`ide-term-tab ${activeBottomTab === "ast" ? "active" : ""}`}
                onClick={() => setActiveBottomTab("ast")}
              >
                <span>VALIDASI POHON AST</span>
                {result && (
                  <span
                    className={`ide-tab-dot ${
                      result.ast.hasAllRequiredNodes && result.ast.syntaxValid
                        ? "success"
                        : "warning"
                    }`}
                  />
                )}
              </button>

              {quest && (
                <button
                  type="button"
                  className={`ide-term-tab ${activeBottomTab === "hints" ? "active" : ""}`}
                  onClick={() => setActiveBottomTab("hints")}
                >
                  <span>PETUNJUK (DOCSTRING)</span>
                </button>
              )}

              {/* Status Hasil Singkat di Kanan Header Terminal */}
              {result && (
                <div className="ide-terminal-status-badge">
                  {result.passed ? (
                    <span className="status-badge-passed">✅ Lolos Uji AST & Luaran</span>
                  ) : (
                    <span className="status-badge-failed">⚠️ Butuh Perbaikan</span>
                  )}
                </div>
              )}
            </div>

            {/* Isi Konten Terminal / AST */}
            <div className="ide-terminal-content">
              {/* TAB 1: Terminal Konsol */}
              {activeBottomTab === "terminal" && (
                <div className="ide-console-view">
                  {result?.stdout && (
                    <pre className="ide-stdout">{result.stdout}</pre>
                  )}
                  {result?.stderr && (
                    <pre className="ide-stderr">{result.stderr}</pre>
                  )}
                  {!result && (
                    <div className="ide-console-idle">
                      Tekan tombol <strong>"▶ Jalankan & Validasi AST"</strong> di pojok kanan atas untuk mengeksekusi kode.
                    </div>
                  )}
                  {result && !result.stdout && !result.stderr && (
                    <div className="ide-console-idle">
                      Program selesai dieksekusi tanpa luaran teks (stdout).
                    </div>
                  )}
                  {result?.timedOut && (
                    <div className="ide-console-timeout">
                      ⚠️ Waktu eksekusi melebihi 4 detik! Kemungkinan terjadi infinite loop pada perulangan Anda.
                    </div>
                  )}
                </div>
              )}

              {/* TAB 2: Validasi AST */}
              {activeBottomTab === "ast" && (
                <div className="ide-ast-view">
                  {!result ? (
                    <div className="ide-console-idle">
                      Pohon sintaks (AST) akan otomatis dianalisis dan dibedah setelah Anda menjalankan kode.
                    </div>
                  ) : (
                    <div className="ide-ast-results">
                      {/* Status Header AST */}
                      <div className="ide-ast-status-bar">
                        <span>Status Sintaksis: </span>
                        {result.ast.syntaxValid ? (
                          <strong className="ast-text-ok">Valid (Lolos ast.parse)</strong>
                        ) : (
                          <strong className="ast-text-err">SyntaxError Ditemukan</strong>
                        )}
                      </div>

                      {/* Grid Simpul Wajib */}
                      {quest && (
                        <div className="ide-ast-node-cards">
                          <div className="ide-ast-grid-title">Pemeriksaan Simpul yang Diwajibkan:</div>
                          <div className="ide-node-grid">
                            {quest.requiredNodes.map((nodeName) => {
                              const isPresent = result.ast.nodesFound.includes(nodeName);
                              return (
                                <div
                                  key={nodeName}
                                  className={`ide-node-box ${isPresent ? "fulfilled" : "missing"}`}
                                >
                                  <div className="ide-node-box-header">
                                    <code>ast.{nodeName}</code>
                                    <span className="ide-node-state">
                                      {isPresent ? "✓ Terpenuhi" : "✗ Belum Ada"}
                                    </span>
                                  </div>
                                  <span className="ide-node-note">
                                    {quest.nodeExplanations[nodeName] || "Konstruksi sintaks"}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Tree View ast.dump */}
                      {result.ast.astTree && (
                        <details className="ide-ast-tree-details">
                          <summary>Lihat Hierarki Pohon Sintaks Lengkap (ast.dump)</summary>
                          <pre className="ide-tree-code">{result.ast.astTree}</pre>
                        </details>
                      )}
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Petunjuk Resmi */}
              {activeBottomTab === "hints" && quest && (
                <div className="ide-hints-view">
                  <div className="ide-hints-title">Petunjuk Berdasarkan Dokumentasi Resmi:</div>
                  <ul className="ide-hints-ul">
                    {quest.hints.map((hint, i) => (
                      <li key={i}>
                        <InfoIcon size={14} />
                        <span>{hint}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Bar Hasil Evaluasi di Footer Terminal */}
            {result && (
              <div className={`ide-terminal-footer ${result.passed ? "passed" : "incomplete"}`}>
                <div className="ide-feedback-text">{result.feedback}</div>
                {result.passed && (
                  <button
                    type="button"
                    className="ide-btn-to-quiz"
                    onClick={scrollToQuiz}
                  >
                    <span>Lanjut ke Kuis Pasca-Sesi ➔</span>
                  </button>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

