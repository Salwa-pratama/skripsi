"use client";

import { useProgress } from "@/lib/progress";
import { CheckIcon, CircleCheckIcon } from "./icons";

export function ChapterProgressButton({ slug }: { slug: string }) {
  const { isComplete, toggle, ready } = useProgress();
  const complete = ready && isComplete(slug);

  return (
    <div className="chapter-complete">
      <button
        type="button"
        className={`complete-button ${complete ? "is-complete" : ""}`}
        onClick={() => toggle(slug)}
        disabled={!ready}
        aria-pressed={complete}
      >
        {complete ? <CheckIcon size={19} /> : <CircleCheckIcon size={19} />}
        {complete ? "Bab ini sudah selesai" : "Tandai bab ini selesai"}
      </button>
      <p>Progres disimpan otomatis di browser ini. Tidak ada akun, tidak ada server.</p>
    </div>
  );
}
