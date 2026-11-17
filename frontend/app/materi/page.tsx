import type { Metadata } from "next";
import Link from "next/link";
import { ChapterCard } from "@/components/ChapterCard";
import { OverallProgress } from "@/components/OverallProgress";
import { ArrowRightIcon, ClockIcon, ListChecksIcon } from "@/components/icons";
import { chapters, curriculum, phases, totalMinutes } from "@/lib/curriculum";

export const metadata: Metadata = {
  title: "Kurikulum",
  description:
    "Tujuh bab Python 3 dari dokumentasi resmi CPython: variabel, percabangan, perulangan, fungsi, list & dictionary, OOP dasar, dan OOP lanjutan.",
};

export default function MateriPage() {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  return (
    <>
      <section className="page-hero">
        <div className="container page-hero-grid">
          <div>
            <p className="eyebrow">Kurikulum</p>
            <h1>Tujuh bab, satu alur yang jelas.</h1>
            <p className="page-lede">
              Mulai dari cara Python menyimpan nilai, lalu naik ke kontrol alur,
              fungsi, struktur data, dan akhirnya object-oriented programming.
              Semua teks materi bersumber dari dokumentasi resmi CPython{" "}
              {curriculum.pythonVersion}.
            </p>
            <div className="page-meta-row">
              <span>
                <ListChecksIcon size={16} />
                {chapters.length} bab
              </span>
              <span>
                <ClockIcon size={16} />
                ±{hours} jam {minutes} menit
              </span>
              <span>Pemula → Lanjutan</span>
            </div>
          </div>
          <OverallProgress />
        </div>
      </section>

      <section className="section section-tight">
        <div className="container">
          {phases.map((phase) => {
            const phaseChapters = chapters.filter((chapter) => chapter.phase === phase);
            return (
              <div className="phase-block" key={phase}>
                <div className="phase-heading">
                  <p className="eyebrow">{phase}</p>
                  <span>{phaseChapters.length} bab</span>
                </div>
                <div className="chapter-grid">
                  {phaseChapters.map((chapter) => (
                    <ChapterCard chapter={chapter} key={chapter.slug} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      <section className="section section-tight">
        <div className="container start-note">
          <div>
            <p className="eyebrow">Bingung mulai dari mana?</p>
            <h2>Ikuti urutannya, atau lompat ke yang kamu butuhkan.</h2>
            <p>
              Kalau baru pertama kali belajar Python, mulai dari Bab 1. Kalau
              sudah familiar dengan sintaks dasar, kamu bisa langsung ke Bab 5
              untuk list & dictionary atau Bab 6 untuk OOP.
            </p>
          </div>
          <div className="start-note-actions">
            <Link className="button button-primary" href={`/materi/${chapters[0].slug}`}>
              Mulai Bab 1
              <ArrowRightIcon size={17} />
            </Link>
            <Link className="button button-ghost" href="/indeks">
              Cari di indeks API
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
