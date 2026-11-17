import fs from "node:fs";
import path from "node:path";
import manifestData from "@/content/generated/manifest.json";
import type {
  ApiIndex,
  ChapterContent,
  Manifest,
  SearchEntry,
} from "./types";

const ROOT = process.cwd();
const CONTENT_DIR = path.join(ROOT, "content", "generated");
const PUBLIC_DATA_DIR = path.join(ROOT, "public", "data");

const chapterCache = new Map<string, ChapterContent>();

export const manifest = manifestData as Manifest;

export function getChapterContent(slug: string): ChapterContent {
  const cached = chapterCache.get(slug);
  if (cached) return cached;

  const file = path.join(CONTENT_DIR, "chapters", `${slug}.json`);
  if (!fs.existsSync(file)) {
    throw new Error(
      `Konten bab "${slug}" belum dibangun. Jalankan: npm run content:build`,
    );
  }
  const content = JSON.parse(fs.readFileSync(file, "utf8")) as ChapterContent;
  chapterCache.set(slug, content);
  return content;
}

export function getApiIndex(): ApiIndex {
  const file = path.join(PUBLIC_DATA_DIR, "api-index.json");
  return JSON.parse(fs.readFileSync(file, "utf8")) as ApiIndex;
}

export function getSearchIndex(): SearchEntry[] {
  const file = path.join(PUBLIC_DATA_DIR, "search-index.json");
  return JSON.parse(fs.readFileSync(file, "utf8")) as SearchEntry[];
}

export function getPygmentsCss(): string {
  return fs.readFileSync(path.join(CONTENT_DIR, "pygments.css"), "utf8");
}
