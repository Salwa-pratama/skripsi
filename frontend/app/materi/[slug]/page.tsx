import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { WorkspaceIDE } from "@/components/WorkspaceIDE";
import { getChapterContent } from "@/lib/content";
import { chapters, getAdjacentChapters, getChapter } from "@/lib/curriculum";
import { getQuest } from "@/lib/quests";
import { getQuiz } from "@/lib/quizzes";
import type { Block } from "@/lib/types";

type HeadingBlock = Extract<Block, { type: "heading" }>;

type Props = {
  params: Promise<{ slug: string }>;
};

export function generateStaticParams() {
  return chapters.map((chapter) => ({ slug: chapter.slug }));
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const chapter = getChapter(slug);
  if (!chapter) return { title: "Bab tidak ditemukan" };
  return {
    title: `${chapter.title} · PyJourney`,
    description: chapter.description,
    openGraph: {
      title: `${chapter.title} · PyJourney`,
      description: chapter.description,
      type: "article",
    },
  };
}

export default async function ChapterPage({ params }: Props) {
  const { slug } = await params;
  const chapter = getChapter(slug);
  if (!chapter) notFound();

  const content = getChapterContent(slug);
  const quiz = getQuiz(slug);
  const quest = getQuest(slug);
  const { previous, next } = getAdjacentChapters(slug);

  const headings = content.groups
    .flatMap((group) => group.blocks)
    .filter(
      (block): block is HeadingBlock =>
        block.type === "heading" && block.level <= 3 && Boolean(block.id),
    )
    .map((block) => ({
      id: block.id as string,
      text: block.text,
      level: block.level,
    }));

  return (
    <WorkspaceIDE
      chapter={chapter}
      content={content}
      quiz={quiz}
      quest={quest}
      headings={headings}
      previous={previous}
      next={next}
    />
  );
}
