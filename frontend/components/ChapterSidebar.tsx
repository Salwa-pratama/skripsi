import Link from "next/link";
import { chapters, phases } from "@/lib/curriculum";
import { ProgressSummary } from "./ProgressSummary";
import { ChevronDownIcon } from "./icons";

function ChapterNavList({ currentSlug }: { currentSlug: string }) {
  return (
    <div className="sidebar-phases">
      {phases.map((phase) => (
        <div className="sidebar-phase" key={phase}>
          <p className="sidebar-phase-label">{phase}</p>
          <ol className="sidebar-chapter-list">
            {chapters
              .filter((chapter) => chapter.phase === phase)
              .map((chapter) => (
                <li key={chapter.slug}>
                  <Link
                    href={`/materi/${chapter.slug}`}
                    className={chapter.slug === currentSlug ? "is-active" : undefined}
                    aria-current={chapter.slug === currentSlug ? "page" : undefined}
                  >
                    <span className="sidebar-number">
                      {String(chapter.order).padStart(2, "0")}
                    </span>
                    <span>{chapter.title}</span>
                  </Link>
                </li>
              ))}
          </ol>
        </div>
      ))}
    </div>
  );
}

export function ChapterSidebar({ currentSlug }: { currentSlug: string }) {
  return (
    <aside className="chapter-sidebar">
      <ProgressSummary />
      <nav aria-label="Daftar bab">
        <p className="sidebar-label">Kurikulum</p>
        <ChapterNavList currentSlug={currentSlug} />
      </nav>
      <Link href="/materi" className="sidebar-all-link">
        Lihat semua bab
      </Link>
    </aside>
  );
}

export function MobileChapterNav({ currentSlug }: { currentSlug: string }) {
  const current = chapters.find((chapter) => chapter.slug === currentSlug);
  return (
    <details className="mobile-chapter-nav">
      <summary>
        <span>
          <span className="mobile-nav-kicker">Daftar bab</span>
          <strong>{current ? `Bab ${current.order} · ${current.title}` : "Kurikulum"}</strong>
        </span>
        <ChevronDownIcon size={19} />
      </summary>
      <div className="mobile-nav-body">
        <ChapterNavList currentSlug={currentSlug} />
      </div>
    </details>
  );
}
