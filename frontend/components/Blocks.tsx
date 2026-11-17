import { createElement } from "react";
import type { Block } from "@/lib/types";
import { CodeBlock } from "./CodeBlock";
import {
  BookIcon,
  InfoIcon,
  LightbulbIcon,
  ListChecksIcon,
  SparklesIcon,
  WarningIcon,
} from "./icons";

const ADMONITION_LABELS: Record<string, string> = {
  note: "Catatan",
  tip: "Tips",
  hint: "Saran",
  important: "Penting",
  warning: "Peringatan",
  caution: "Hati-hati",
  danger: "Bahaya",
  attention: "Perhatian",
  error: "Error",
  seealso: "Lihat juga",
  topic: "Topik",
  admonition: "Catatan",
};

const NOTE_LABELS: Record<string, string> = {
  versionadded: "Ditambahkan",
  versionchanged: "Diubah",
  deprecated: "Deprecated",
  versionremoved: "Dihapus",
};

function AdmonitionIcon({ kind }: { kind: string }) {
  if (kind === "warning" || kind === "caution" || kind === "danger" || kind === "attention" || kind === "error") {
    return <WarningIcon size={18} />;
  }
  if (kind === "tip" || kind === "hint") return <LightbulbIcon size={18} />;
  if (kind === "important") return <SparklesIcon size={18} />;
  if (kind === "seealso" || kind === "topic") return <BookIcon size={18} />;
  return <InfoIcon size={18} />;
}

function BlockView({ block }: { block: Block }) {
  switch (block.type) {
    case "heading": {
      const level = Math.min(Math.max(block.level, 2), 6);
      return createElement(
        `h${level}`,
        {
          id: block.id ?? undefined,
          className: "content-heading",
        },
        <>
          <span dangerouslySetInnerHTML={{ __html: block.html }} />
          {block.id && (
            <a
              href={`#${block.id}`}
              className="heading-anchor"
              aria-label="Tautan langsung ke bagian ini"
            >
              #
            </a>
          )}
        </>,
      );
    }
    case "paragraph":
      return <p dangerouslySetInnerHTML={{ __html: block.html }} />;
    case "code":
      return <CodeBlock html={block.html} text={block.text} language={block.language} />;
    case "list": {
      const ListTag = block.ordered ? "ol" : "ul";
      return (
        <ListTag start={block.ordered ? block.start ?? undefined : undefined}>
          {block.items.map((item, index) => (
            <li key={index}>
              <Blocks blocks={item} />
            </li>
          ))}
        </ListTag>
      );
    }
    case "definition":
      return (
        <div className="definition-list">
          {block.items.map((item, index) => (
            <div className="definition-item" id={item.id ?? undefined} key={item.id ?? index}>
              <div
                className="definition-term"
                dangerouslySetInnerHTML={{ __html: item.termHtml }}
              />
              <div className="definition-body">
                <Blocks blocks={item.blocks} />
              </div>
            </div>
          ))}
        </div>
      );
    case "table":
      return (
        <div
          className="table-wrap"
          dangerouslySetInnerHTML={{ __html: block.html }}
        />
      );
    case "admonition": {
      const label = ADMONITION_LABELS[block.kind] ?? "Catatan";
      return (
        <aside className={`admonition admonition-${block.kind}`}>
          <div className="admonition-title">
            <AdmonitionIcon kind={block.kind} />
            {block.titleHtml ? (
              <span dangerouslySetInnerHTML={{ __html: block.titleHtml }} />
            ) : (
              <span>{label}</span>
            )}
          </div>
          <div className="admonition-body">
            <Blocks blocks={block.blocks} />
          </div>
        </aside>
      );
    }
    case "note":
      return (
        <div className={`version-note version-note-${block.kind}`}>
          <span className="version-badge">{NOTE_LABELS[block.kind] ?? "Catatan"}</span>
          <span dangerouslySetInnerHTML={{ __html: block.html }} />
        </div>
      );
    case "quote":
      return (
        <blockquote>
          <Blocks blocks={block.blocks} />
        </blockquote>
      );
    case "separator":
      return <hr />;
    default:
      return null;
  }
}

export function Blocks({ blocks }: { blocks: Block[] }) {
  return (
    <>
      {blocks.map((block, index) => (
        <BlockView block={block} key={index} />
      ))}
    </>
  );
}
