export type Block =
  | {
      type: "heading";
      level: number;
      id: string | null;
      html: string;
      text: string;
    }
  | { type: "paragraph"; html: string }
  | { type: "code"; language: string; html: string; text: string }
  | {
      type: "list";
      ordered: boolean;
      start: number | null;
      items: Block[][];
    }
  | {
      type: "definition";
      items: {
        id: string | null;
        termHtml: string;
        blocks: Block[];
      }[];
    }
  | { type: "table"; html: string }
  | {
      type: "admonition";
      kind: string;
      titleHtml: string | null;
      blocks: Block[];
    }
  | { type: "note"; kind: string; html: string }
  | { type: "quote"; blocks: Block[] }
  | { type: "separator" };

export type SourceRef = {
  doc: string;
  title: string;
  label: string;
  url: string;
};

export type SourceConfig = {
  doc: string;
  label?: string;
  sections: string[];
  exclude?: string[];
};

export type ApiHighlight = {
  name: string;
  role: string;
  url: string;
  display: string;
  doc: string;
};

export type EpisodeMeta = {
  id: string;
  title: string;
  concept: string;
  targetSection?: string;
};

export type ChapterMeta = {
  order: number;
  slug: string;
  phase: string;
  title: string;
  subtitle: string;
  level: string;
  minutes: number;
  description: string;
  objectives: string[];
  keyPoints: string[];
  apiHighlights: string[];
  sources: SourceConfig[];
  episodes?: EpisodeMeta[];
};

export type Curriculum = {
  pythonVersion: string;
  docVersion: string;
  docUrl: string;
  cpythonRepo: string;
  title: string;
  description: string;
  chapters: ChapterMeta[];
};

export type ChapterContent = {
  slug: string;
  title: string;
  order: number;
  docVersion: string;
  generatedAt: string;
  blockCount: number;
  wordCount: number;
  api: ApiHighlight[];
  groups: {
    source: SourceRef;
    blocks: Block[];
  }[];
};

export type Manifest = {
  pythonVersion: string;
  docVersion: string;
  docUrl: string;
  cpythonRepo: string;
  tarballUrl: string;
  tarballSha256: string | null;
  sphinxVersion: string;
  builder: string;
  generatedAt: string;
  sourceDocs: string[];
  inventoryCount: number;
  apiIndexCount: number;
  searchEntryCount: number;
  chapters: {
    slug: string;
    title: string;
    order: number;
    blockCount: number;
    wordCount: number;
  }[];
};

export type SearchEntry = {
  chapter: string;
  chapterTitle: string;
  title: string;
  anchor: string | null;
  text: string;
};

export type ApiEntry = {
  name: string;
  role: string;
  url: string;
  display: string;
  doc: string;
};

export type ApiIndex = {
  count: number;
  roles: string[];
  entries: ApiEntry[];
};

export type QuizQuestion = {
  question: string;
  options: string[];
  answer: number;
  explanation: string;
};
