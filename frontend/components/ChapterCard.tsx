"use client";

import Link from "next/link";
import type { ChapterMeta } from "@/lib/types";
import { useProgress } from "@/lib/progress";
import { ArrowRightIcon, CheckIcon, ClockIcon } from "./icons";

export function ChapterCard({ chapter }: { chapter: ChapterMeta }) {
  const { isComplete, ready } = useProgress();
  const complete = ready && isComplete(chapter.slug);

  return (
    <Link
      href={`/materi/${chapter.slug}`}
      className={`chapter-card ${complete ? "is-complete" : ""}`}
    >
      <div className="chapter-card-top">
        <span className="chapter-number">{String(chapter.order).padStart(2, "0")}</span>
        <span className="chapter-level">{chapter.level}</span>
      </div>
      <h3>{chapter.title}</h3>
      <p>{chapter.description}</p>
      <div className="chapter-card-meta">
        <span>
          <ClockIcon size={15} />
          {chapter.minutes} menit
        </span>
        {complete ? (
          <span className="chapter-done">
            <CheckIcon size={15} />
            Selesai
          </span>
        ) : (
          <span className="chapter-open">
            Buka bab
            <ArrowRightIcon size={15} />
          </span>
        )}
      </div>
    </Link>
  );
}
