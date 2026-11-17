"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import type { SearchEntry } from "@/lib/types";
import { ArrowRightIcon, CloseIcon, SearchIcon } from "./icons";

type Props = {
  open: boolean;
  onClose: () => void;
};

type Result = SearchEntry & { snippet: string; score: number };

function makeSnippet(text: string, query: string): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (!query) return clean.slice(0, 170);
  const index = clean.toLowerCase().indexOf(query.toLowerCase());
  if (index < 0) return clean.slice(0, 170);
  const start = Math.max(0, index - 55);
  const end = Math.min(clean.length, start + 220);
  return `${start > 0 ? "…" : ""}${clean.slice(start, end)}${end < clean.length ? "…" : ""}`;
}

export function SearchDialog({ open, onClose }: Props) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [entries, setEntries] = useState<SearchEntry[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setActiveIndex(0);
    const timer = window.setTimeout(() => inputRef.current?.focus(), 30);
    return () => window.clearTimeout(timer);
  }, [open]);

  useEffect(() => {
    if (!open || loaded || loading) return;
    setLoading(true);
    fetch("/data/search-index.json")
      .then((response) => {
        if (!response.ok) throw new Error("Gagal memuat indeks");
        return response.json() as Promise<SearchEntry[]>;
      })
      .then((data) => {
        setEntries(data);
        setLoaded(true);
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false));
  }, [open, loaded, loading]);

  useEffect(() => {
    if (!open) return;
    const previous = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previous;
    };
  }, [open]);

  const results = useMemo<Result[]>(() => {
    const normalized = query.trim().toLowerCase();
    const terms = normalized.split(/\s+/).filter(Boolean);
    return entries
      .map((entry) => {
        const haystack =
          `${entry.chapterTitle} ${entry.title} ${entry.text}`.toLowerCase();
        if (terms.length && !terms.every((term) => haystack.includes(term))) {
          return null;
        }
        let score = 0;
        if (normalized) {
          if (entry.title.toLowerCase().includes(normalized)) score += 40;
          if (entry.chapterTitle.toLowerCase().includes(normalized)) score += 15;
          if (haystack.includes(normalized)) score += 10;
          for (const term of terms) {
            const occurrences = haystack.split(term).length - 1;
            score += Math.min(occurrences, 8);
          }
        }
        return {
          ...entry,
          snippet: makeSnippet(entry.text, query.trim()),
          score,
        };
      })
      .filter((entry): entry is Result => entry !== null)
      .sort((a, b) => b.score - a.score || a.chapterTitle.localeCompare(b.chapterTitle))
      .slice(0, 12);
  }, [entries, query]);

  useEffect(() => {
    setActiveIndex(0);
  }, [query]);

  useEffect(() => {
    if (!open) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((index) => Math.min(index + 1, Math.max(results.length - 1, 0)));
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((index) => Math.max(index - 1, 0));
      } else if (event.key === "Enter" && results[activeIndex]) {
        event.preventDefault();
        const result = results[activeIndex];
        router.push(
          `/materi/${result.chapter}${result.anchor ? `#${result.anchor}` : ""}`,
        );
        onClose();
      }
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [activeIndex, onClose, open, results, router]);

  if (!open) return null;

  return (
    <div
      className="search-overlay"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div
        className="search-panel"
        role="dialog"
        aria-modal="true"
        aria-label="Cari materi"
      >
        <div className="search-input-row">
          <SearchIcon size={20} className="search-input-icon" />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Cari topik, istilah, atau potongan kode..."
            aria-label="Kata kunci pencarian"
            autoComplete="off"
            spellCheck={false}
          />
          <button type="button" className="icon-button" onClick={onClose} aria-label="Tutup pencarian">
            <CloseIcon size={18} />
          </button>
        </div>

        <div className="search-results" role="listbox" aria-label="Hasil pencarian">
          {loading && <p className="search-state">Memuat indeks materi…</p>}
          {error && (
            <p className="search-state">
              Indeks pencarian belum tersedia. Jalankan <code>npm run content:build</code>.
            </p>
          )}
          {!loading && !error && results.length === 0 && (
            <p className="search-state">
              Tidak ada hasil untuk <strong>{query}</strong>. Coba kata kunci yang lebih umum.
            </p>
          )}
          {results.map((result, index) => (
            <button
              key={`${result.chapter}-${result.anchor ?? result.title}-${index}`}
              type="button"
              role="option"
              aria-selected={index === activeIndex}
              className={`search-result ${index === activeIndex ? "is-active" : ""}`}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => {
                router.push(
                  `/materi/${result.chapter}${result.anchor ? `#${result.anchor}` : ""}`,
                );
                onClose();
              }}
            >
              <span className="search-result-main">
                <span className="search-result-chapter">{result.chapterTitle}</span>
                <span className="search-result-title">{result.title}</span>
                <span className="search-result-snippet">{result.snippet}</span>
              </span>
              <ArrowRightIcon size={17} className="search-result-arrow" />
            </button>
          ))}
        </div>

        <div className="search-footer">
          <span>
            <kbd>↑</kbd> <kbd>↓</kbd> navigasi
          </span>
          <span>
            <kbd>Enter</kbd> buka
          </span>
          <span>
            <kbd>Esc</kbd> tutup
          </span>
          <span className="search-footer-count">
            {loaded ? `${entries.length} bagian terindeks` : "indeks resmi"}
          </span>
        </div>
      </div>
    </div>
  );
}
