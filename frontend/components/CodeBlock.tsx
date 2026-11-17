"use client";

import { useState } from "react";
import { WarningIcon } from "./icons";

const LANGUAGE_LABELS: Record<string, string> = {
  python: "Python 3",
  console: "Konsol Interaktif",
  text: "Teks",
  bash: "Terminal",
  sh: "Shell",
  json: "JSON",
  none: "Teks",
};

type Props = {
  html: string;
  text: string;
  language: string;
};

export function CodeBlock({ html, text, language }: Props) {
  const [showWarning, setShowWarning] = useState(false);

  function handleAttemptCopy(e: React.SyntheticEvent) {
    e.preventDefault();
    setShowWarning(true);
    window.setTimeout(() => setShowWarning(false), 3000);
  }

  return (
    <div className="code-block" onCopy={handleAttemptCopy}>
      <div className="code-toolbar">
        <span className="code-language">
          <span className="code-dot" aria-hidden="true" />
          {LANGUAGE_LABELS[language] ?? language}
        </span>
        <button
          type="button"
          className="code-manual-badge"
          onClick={handleAttemptCopy}
          title="Salin-tempel dinonaktifkan untuk melatih muscle memory"
          aria-label="Ketik Manual (Anti Copy-Paste)"
        >
          ✍️ Ketik Manual
        </button>
      </div>

      {showWarning && (
        <div className="code-copy-warning" role="alert">
          <WarningIcon size={14} />
          <span>
            <strong>Anti Copy-Paste:</strong> Demi melatih memori otot (<em>muscle memory</em>) dan
            algoritma dasar, ketik kode contoh ini secara manual di editor.
          </span>
        </div>
      )}

      <pre>
        <code dangerouslySetInnerHTML={{ __html: html || text }} />
      </pre>
    </div>
  );
}
