import curriculumData from "@/content/curriculum.json";
import type { ChapterMeta, Curriculum } from "./types";

export const curriculum = curriculumData as unknown as Curriculum;

export const chapters: ChapterMeta[] = [...curriculum.chapters].sort(
  (a, b) => a.order - b.order,
);

export const chapterBySlug = new Map(chapters.map((chapter) => [chapter.slug, chapter]));

export const phases = Array.from(new Set(chapters.map((chapter) => chapter.phase)));

export function getChapter(slug: string): ChapterMeta | undefined {
  return chapterBySlug.get(slug);
}

export function getAdjacentChapters(slug: string): {
  previous: ChapterMeta | null;
  next: ChapterMeta | null;
} {
  const index = chapters.findIndex((chapter) => chapter.slug === slug);
  return {
    previous: index > 0 ? chapters[index - 1] : null,
    next: index >= 0 && index < chapters.length - 1 ? chapters[index + 1] : null,
  };
}

export function chapterHref(slug: string): string {
  return `/materi/${slug}`;
}

export const totalMinutes = chapters.reduce((total, chapter) => total + chapter.minutes, 0);
