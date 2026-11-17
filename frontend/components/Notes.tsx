"use client";

import { useEffect, useState } from "react";
import { CheckIcon, PenIcon } from "./icons";

export function Notes({ slug }: { slug: string }) {
  const storageKey = `pyjourney.notes.v1:${slug}`;
  const [value, setValue] = useState("");
  const [loaded, setLoaded] = useState(false);
  const [status, setStatus] = useState<"idle" | "saving" | "saved">("idle");

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(storageKey);
      if (saved) setValue(saved);
    } catch {
      // Ignore storage errors.
    } finally {
      setLoaded(true);
    }
  }, [storageKey]);

  useEffect(() => {
    if (!loaded) return;
    setStatus("saving");
    const timer = window.setTimeout(() => {
      try {
        if (value.trim()) {
          window.localStorage.setItem(storageKey, value);
        } else {
          window.localStorage.removeItem(storageKey);
        }
        setStatus("saved");
      } catch {
        setStatus("idle");
      }
    }, 450);
    return () => window.clearTimeout(timer);
  }, [loaded, storageKey, value]);

  function clearNote() {
    if (!value.trim()) return;
    if (!window.confirm("Hapus catatan untuk bab ini?")) return;
    setValue("");
    try {
      window.localStorage.removeItem(storageKey);
    } catch {
      // Ignore storage errors.
    }
    setStatus("idle");
  }

  return (
    <section className="notes-card" aria-labelledby="notes-title">
      <div className="notes-head">
        <div>
          <p className="section-kicker">
            <PenIcon size={15} />
            Ruang belajarmu
          </p>
          <h2 id="notes-title">Catatan pribadi</h2>
        </div>
        <span className="notes-status" aria-live="polite">
          {status === "saving" ? "Menyimpan…" : status === "saved" ? "Tersimpan" : "Lokal di browser"}
        </span>
      </div>
      <textarea
        value={value}
        onChange={(event) => setValue(event.target.value)}
        placeholder="Tulis hal yang ingin kamu ingat, pertanyaan, atau potongan kode yang ingin dicoba…"
        rows={6}
        aria-label="Catatan pribadi untuk bab ini"
      />
      <div className="notes-footer">
        <span>{value.trim() ? `${value.trim().length} karakter` : "Catatan tidak dikirim ke mana pun."}</span>
        <button type="button" className="text-button" onClick={clearNote} disabled={!value.trim()}>
          Hapus catatan
        </button>
      </div>
    </section>
  );
}
