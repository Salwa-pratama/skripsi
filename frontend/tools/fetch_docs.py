#!/usr/bin/env python3
"""Build the PyJourney learning content from the official CPython documentation.

The pipeline intentionally mirrors the brief:

    cpython/Doc  ->  Sphinx JSON Builder  ->  structured JSON  ->  Next.js

It downloads a pinned CPython source tarball, builds a selected subset of the
official reStructuredText docs with Sphinx's JSON builder, parses the resulting
``.fjson`` files and ``objects.inv`` inventory, and emits the data consumed by
the Next.js app.

Run from the project root:

    python3 tools/fetch_docs.py
    python3 tools/fetch_docs.py --skip-sphinx   # reuse the cached JSON build
    python3 tools/fetch_docs.py --force         # re-download and rebuild
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import html
import json
import os
import posixpath
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from bs4 import BeautifulSoup, NavigableString, Tag

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = ROOT / "content"
GENERATED_DIR = CONTENT_DIR / "generated"
PUBLIC_DATA_DIR = ROOT / "public" / "data"
CACHE_DIR = ROOT / ".cache"

PYTHON_VERSION = "3.13.7"
DOC_VERSION = "3.13"
TARBALL_NAME = f"Python-{PYTHON_VERSION}.tar.xz"
TARBALL_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/{TARBALL_NAME}"
CPYTHON_REPO = f"https://github.com/python/cpython/tree/v{PYTHON_VERSION}/Doc"
DOCS_BASE = f"https://docs.python.org/{DOC_VERSION}"

# Extra docs are built for their inventory entries (built-in functions,
# exceptions, data model, etc.) even when they are not rendered as chapters.
INVENTORY_DOCS = [
    "library/functions",
    "library/exceptions",
    "reference/datamodel",
    "reference/expressions",
    "glossary",
]

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
INLINE_ALLOWED = {
    "a",
    "abbr",
    "br",
    "cite",
    "code",
    "em",
    "img",
    "kbd",
    "samp",
    "strong",
    "sub",
    "sup",
    "var",
}
LANGUAGE_ALIASES = {
    "python3": "python",
    "pycon": "python",
    "default": "text",
    "none": "text",
    "text": "text",
}


# ---------------------------------------------------------------------------
# Small utilities
# ---------------------------------------------------------------------------


def log(message: str) -> None:
    print(f"[pyjourney] {message}", flush=True)


def fail(message: str) -> None:
    print(f"[pyjourney] ERROR: {message}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slugify(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "-", text).strip("-") or "bagian"


def html_to_text(value: str) -> str:
    if not value:
        return ""
    soup = BeautifulSoup(value, "lxml")
    return re.sub(r"\s+", " ", soup.get_text(" ", strip=True)).strip()


def load_curriculum() -> dict[str, Any]:
    path = CONTENT_DIR / "curriculum.json"
    if not path.exists():
        fail(f"Curriculum tidak ditemukan: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    chapters = data.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        fail("content/curriculum.json harus punya array 'chapters' yang tidak kosong.")

    seen: set[str] = set()
    for chapter in chapters:
        slug = chapter.get("slug")
        if not slug or slug in seen:
            fail(f"Slug bab tidak valid atau duplikat: {slug!r}")
        seen.add(slug)
        if not chapter.get("sources"):
            fail(f"Bab {slug} tidak punya sources.")
        for source in chapter["sources"]:
            if not source.get("doc") or not source.get("sections"):
                fail(f"Source pada bab {slug} harus punya 'doc' dan 'sections'.")
    return data


# ---------------------------------------------------------------------------
# Download / extract / Sphinx build
# ---------------------------------------------------------------------------


def download_tarball(force: bool, offline: bool) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tarball = CACHE_DIR / TARBALL_NAME
    if tarball.exists() and not force:
        log(f"Memakai tarball cache: {tarball.relative_to(ROOT)}")
        return tarball
    if offline:
        fail(
            f"Mode offline, tetapi tarball belum ada di {tarball}. "
            "Jalankan tanpa --offline atau sediakan cache tersebut."
        )
    log(f"Mengunduh dokumentasi resmi CPython {PYTHON_VERSION} ...")
    tmp = tarball.with_suffix(".part")
    try:
        with urllib.request.urlopen(TARBALL_URL, timeout=120) as response:
            with tmp.open("wb") as handle:
                shutil.copyfileobj(response, handle)
    except Exception as exc:  # noqa: BLE001 - surface a useful message
        tmp.unlink(missing_ok=True)
        fail(f"Gagal mengunduh {TARBALL_URL}: {exc}")
    tmp.replace(tarball)
    log(f"Selesai: {tarball.name} ({tarball.stat().st_size / 1_000_000:.1f} MB)")
    return tarball


def extract_source(tarball: Path, force: bool) -> Path:
    source_root = CACHE_DIR / f"Python-{PYTHON_VERSION}"
    doc_dir = source_root / "Doc"
    if doc_dir.exists() and (source_root / "Include" / "patchlevel.h").exists() and not force:
        log(f"Memakai source cache: {source_root.relative_to(ROOT)}")
        return source_root

    log("Mengekstrak Doc/, Include/patchlevel.h, dan LICENSE ...")
    shutil.rmtree(source_root, ignore_errors=True)
    wanted = (
        f"Python-{PYTHON_VERSION}/Doc/",
        f"Python-{PYTHON_VERSION}/Include/patchlevel.h",
        f"Python-{PYTHON_VERSION}/LICENSE",
    )
    with tarfile.open(tarball, "r:xz") as archive:
        members = [member for member in archive.getmembers() if member.name.startswith(wanted)]
        if not members:
            fail("Tarball tidak berisi Doc/ yang diharapkan.")
        archive.extractall(CACHE_DIR, members=members)
    if not doc_dir.exists():
        fail(f"Ekstraksi gagal, {doc_dir} tidak ada.")
    return source_root


def build_doc_list(curriculum: dict[str, Any]) -> list[str]:
    docs: list[str] = []
    for chapter in curriculum["chapters"]:
        for source in chapter["sources"]:
            docs.append(source["doc"])
    docs.extend(INVENTORY_DOCS)
    return sorted(dict.fromkeys(docs))


def prepare_build_dir(source_root: Path, docs: list[str], force: bool) -> Path:
    build_dir = CACHE_DIR / "doc-build"
    if force:
        shutil.rmtree(build_dir, ignore_errors=True)
    if not (build_dir / "conf.py").exists():
        log("Menyiapkan salinan Doc/ untuk build ...")
        shutil.rmtree(build_dir, ignore_errors=True)
        shutil.copytree(source_root / "Doc", build_dir)

    conf_path = build_dir / "conf.py"
    original = conf_path.read_text(encoding="utf-8")
    marker = "# --- PyJourney overrides"
    if marker in original:
        original = original[: original.index(marker)].rstrip() + "\n"

    patterns = [f"{doc}.rst" for doc in docs]
    patterns.append("contents.rst")
    overrides = f"""

{marker} ---
# Generated by tools/fetch_docs.py. Do not edit by hand.
version, release = {DOC_VERSION!r}, {PYTHON_VERSION!r}
include_patterns = {patterns!r}
intersphinx_mapping = {{}}
# The JSON builder only needs a theme object; avoid optional HTML extensions
# that assume a full HTML page context.
extensions = [
    ext for ext in extensions
    if ext not in ("notfound.extension", "sphinxext.opengraph")
]
"""
    conf_path.write_text(original + overrides, encoding="utf-8")
    return build_dir


def run_sphinx(build_dir: Path, force: bool) -> Path:
    try:
        import sphinx  # noqa: F401
    except ImportError:
        fail(
            "Sphinx belum terpasang. Jalankan:\n"
            "  python3 -m venv .venv\n"
            "  .venv/bin/pip install -r tools/requirements.txt\n"
            "lalu ulangi perintah ini."
        )

    json_out = CACHE_DIR / "sphinx-json"
    doctrees = CACHE_DIR / "doctrees"
    if force:
        shutil.rmtree(json_out, ignore_errors=True)
        shutil.rmtree(doctrees, ignore_errors=True)
    json_out.mkdir(parents=True, exist_ok=True)
    doctrees.mkdir(parents=True, exist_ok=True)

    log("Menjalankan Sphinx JSON Builder (-b json) ...")
    log_path = CACHE_DIR / "sphinx-build.log"
    command = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        "json",
        "-j",
        "auto",
        "-q",
        "-d",
        str(doctrees),
        str(build_dir),
        str(json_out),
    ]
    with log_path.open("w", encoding="utf-8") as log_handle:
        result = subprocess.run(
            command,
            cwd=ROOT,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if result.returncode != 0:
        tail = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-40:]
        print("\n".join(tail), file=sys.stderr)
        fail(f"Sphinx gagal. Log lengkap: {log_path}")
    fjson_count = len(list(json_out.glob("**/*.fjson")))
    log(f"Sphinx selesai: {fjson_count} file .fjson, log di {log_path.relative_to(ROOT)}")
    return json_out


# ---------------------------------------------------------------------------
# HTML -> block JSON
# ---------------------------------------------------------------------------


class DocParser:
    def __init__(self, doc: str):
        self.doc = doc
        self.used_ids: set[str] = set()

    def unique_id(self, value: str | None, fallback: str = "bagian") -> str | None:
        if not value:
            return None
        candidate = value
        counter = 2
        while candidate in self.used_ids:
            candidate = f"{value}-{counter}"
            counter += 1
        self.used_ids.add(candidate)
        return candidate

    def rewrite_href(self, href: str) -> str:
        if not href:
            return "#"
        if href.startswith(("#", "http://", "https://", "mailto:", "tel:", "data:")):
            return href
        path, _, fragment = href.partition("#")
        path = path.split("?", 1)[0]
        if path.endswith("/"):
            path = path[:-1]
        if path.endswith(".html"):
            path = path[:-5]
        if not path:
            return f"#{fragment}" if fragment else "#"
        target = posixpath.normpath(posixpath.join(self.doc, path))
        if target.startswith(".."):
            return href
        if target == self.doc:
            return f"#{fragment}" if fragment else "#"
        url = f"{DOCS_BASE}/{target}.html"
        return f"{url}#{fragment}" if fragment else url

    def rewrite_asset(self, src: str) -> str:
        if not src or src.startswith(("http://", "https://", "data:")):
            return src
        path = posixpath.normpath(posixpath.join(self.doc, src))
        return f"{DOCS_BASE}/{path}"

    def inline_html(self, node: Tag) -> str:
        clone = copy.deepcopy(node)

        for link in clone.find_all("a"):
            classes = link.get("class") or []
            if "headerlink" in classes:
                link.decompose()
                continue
            title = link.get("title")
            href = self.rewrite_href(link.get("href", ""))
            link.attrs = {"href": href}
            if title:
                link["title"] = title
            if href.startswith(("http://", "https://")):
                link["target"] = "_blank"
                link["rel"] = "noopener noreferrer"

        for code in clone.find_all("code"):
            text = code.get_text()
            code.clear()
            code.append(text)
            code.attrs = {}

        for span in clone.find_all("span"):
            span.unwrap()

        for image in clone.find_all("img"):
            image.attrs = {
                "src": self.rewrite_asset(image.get("src", "")),
                "alt": image.get("alt", ""),
                "loading": "lazy",
            }

        for tag in clone.find_all(True):
            if tag.name not in INLINE_ALLOWED:
                tag.unwrap()

        for tag in clone.find_all(True):
            if tag.name == "a":
                tag.attrs = {
                    key: value
                    for key, value in tag.attrs.items()
                    if key in {"href", "title", "target", "rel"}
                }
            elif tag.name == "img":
                tag.attrs = {
                    key: value
                    for key, value in tag.attrs.items()
                    if key in {"src", "alt", "loading"}
                }
            else:
                tag.attrs = {}

        return clone.decode_contents().strip()

    def heading_block(self, heading: Tag, section_id: str | None, shift: int) -> dict[str, Any]:
        level = int(heading.name[1])
        level = max(2, min(6, level + shift))
        heading_html = self.inline_html(heading)
        text = html_to_text(heading_html)
        identifier = self.unique_id(section_id or heading.get("id") or slugify(text))
        return {
            "type": "heading",
            "level": level,
            "id": identifier,
            "html": heading_html,
            "text": text,
        }

    def parse_section(self, section: Tag, shift: int, exclude: set[str]) -> list[dict[str, Any]]:
        section_id = section.get("id")
        if section_id and section_id in exclude:
            return []

        blocks: list[dict[str, Any]] = []
        heading = None
        for child in section.children:
            if isinstance(child, Tag) and child.name in HEADING_TAGS:
                heading = child
                break
        if heading is not None:
            blocks.append(self.heading_block(heading, section_id, shift))

        for child in section.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    blocks.append({"type": "paragraph", "html": html.escape(text)})
                continue
            if not isinstance(child, Tag) or child.name == "section":
                continue
            if child.name in HEADING_TAGS:
                continue
            blocks.extend(self.parse_node(child, shift, exclude))

        for child in section.find_all("section", recursive=False):
            blocks.extend(self.parse_section(child, shift, exclude))
        return blocks

    def parse_children(self, node: Tag, shift: int, exclude: set[str]) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        for child in node.children:
            if isinstance(child, NavigableString):
                text = str(child).strip()
                if text:
                    blocks.append({"type": "paragraph", "html": html.escape(text)})
            elif isinstance(child, Tag):
                blocks.extend(self.parse_node(child, shift, exclude))
        return blocks

    def parse_code(self, node: Tag) -> list[dict[str, Any]]:
        pre = node.find("pre")
        if pre is None:
            return self.parse_children(node, 0, set())
        classes = node.get("class") or []
        language = "text"
        for name in classes:
            if name.startswith("highlight-"):
                language = name.removeprefix("highlight-")
                break
        language = LANGUAGE_ALIASES.get(language, language)
        text = pre.get_text()
        return [
            {
                "type": "code",
                "language": language,
                "html": pre.decode_contents().strip(),
                "text": text.rstrip("\n"),
            }
        ]

    def parse_list(self, node: Tag, shift: int, exclude: set[str]) -> dict[str, Any]:
        items: list[list[dict[str, Any]]] = []
        for item in node.find_all("li", recursive=False):
            blocks = self.parse_children(item, shift, exclude)
            if not blocks:
                text = item.get_text(" ", strip=True)
                if text:
                    blocks = [{"type": "paragraph", "html": html.escape(text)}]
            items.append(blocks)
        start = node.get("start")
        return {
            "type": "list",
            "ordered": node.name == "ol",
            "start": int(start) if start and str(start).isdigit() else None,
            "items": items,
        }

    def parse_definition_list(self, node: Tag, shift: int, exclude: set[str]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None
        for child in node.children:
            if not isinstance(child, Tag):
                continue
            if child.name == "dt":
                if current is not None:
                    items.append(current)
                current = {
                    "id": self.unique_id(child.get("id")),
                    "termHtml": self.inline_html(child),
                    "blocks": [],
                }
            elif child.name == "dd" and current is not None:
                current["blocks"].extend(self.parse_children(child, shift, exclude))
        if current is not None:
            items.append(current)
        items = [item for item in items if item["termHtml"] or item["blocks"]]
        return [{"type": "definition", "items": items}] if items else []

    def parse_admonition(self, node: Tag, shift: int, exclude: set[str]) -> dict[str, Any]:
        clone = copy.deepcopy(node)
        title_tag = clone.find(class_="admonition-title")
        title_html = self.inline_html(title_tag) if title_tag is not None else None
        if title_tag is not None:
            title_tag.decompose()
        classes = [name for name in (node.get("class") or []) if name != "admonition"]
        return {
            "type": "admonition",
            "kind": classes[0] if classes else "note",
            "titleHtml": title_html,
            "blocks": self.parse_children(clone, shift, exclude),
        }

    def parse_topic(self, node: Tag, shift: int, exclude: set[str]) -> dict[str, Any]:
        clone = copy.deepcopy(node)
        title_tag = clone.find(class_="topic-title")
        title_html = self.inline_html(title_tag) if title_tag is not None else None
        if title_tag is not None:
            title_tag.decompose()
        return {
            "type": "admonition",
            "kind": "topic",
            "titleHtml": title_html,
            "blocks": self.parse_children(clone, shift, exclude),
        }

    def parse_table(self, node: Tag) -> dict[str, Any]:
        if "highlighttable" in (node.get("class") or []):
            return self.parse_code(node)[0]
        caption = node.find("caption")
        rows: list[str] = []
        for row in node.find_all("tr"):
            cells: list[str] = []
            for cell in row.find_all(["th", "td"], recursive=False):
                attrs: list[str] = []
                for attribute in ("colspan", "rowspan"):
                    value = cell.get(attribute)
                    if value:
                        attrs.append(f'{attribute}="{html.escape(str(value))}"')
                attr_text = f" {' '.join(attrs)}" if attrs else ""
                cells.append(
                    f"<{cell.name}{attr_text}>{self.inline_html(cell)}</{cell.name}>"
                )
            if cells:
                rows.append(f"<tr>{''.join(cells)}</tr>")
        caption_html = (
            f"<caption>{self.inline_html(caption)}</caption>" if caption is not None else ""
        )
        return {
            "type": "table",
            "html": f"<table>{caption_html}{''.join(rows)}</table>",
        }

    def parse_version(self, node: Tag) -> dict[str, Any]:
        classes = node.get("class") or []
        kind = next(
            (
                name
                for name in classes
                if name in {"versionadded", "versionchanged", "deprecated", "versionremoved"}
            ),
            "versionchanged",
        )
        return {"type": "note", "kind": kind, "html": self.inline_html(node)}

    def parse_node(self, node: Tag, shift: int, exclude: set[str]) -> list[dict[str, Any]]:
        if isinstance(node, NavigableString):
            text = str(node).strip()
            return [{"type": "paragraph", "html": html.escape(text)}] if text else []
        if not isinstance(node, Tag):
            return []
        name = node.name
        classes = node.get("class") or []

        if name == "p":
            content = self.inline_html(node)
            return [{"type": "paragraph", "html": content}] if content else []
        if name in {"ul", "ol"}:
            return [self.parse_list(node, shift, exclude)]
        if name == "dl":
            return self.parse_definition_list(node, shift, exclude)
        if name == "table":
            return [self.parse_table(node)]
        if name == "pre":
            return [
                {
                    "type": "code",
                    "language": "text",
                    "html": node.decode_contents().strip(),
                    "text": node.get_text().rstrip("\n"),
                }
            ]
        if name == "blockquote":
            return [{"type": "quote", "blocks": self.parse_children(node, shift, exclude)}]
        if name == "hr":
            return [{"type": "separator"}]
        if name in HEADING_TAGS:
            return [self.heading_block(node, node.get("id"), shift)]
        if name == "section":
            return self.parse_section(node, shift, exclude)
        if name == "div":
            if "highlight" in classes or "doctest" in classes or "literal-block" in classes:
                return self.parse_code(node)
            if "admonition" in classes:
                return [self.parse_admonition(node, shift, exclude)]
            if "topic" in classes:
                return [self.parse_topic(node, shift, exclude)]
            if any(
                key in classes
                for key in {"versionadded", "versionchanged", "deprecated", "versionremoved"}
            ):
                return [self.parse_version(node)]
            if "code-block-caption" in classes:
                return []
            if "clearer" in classes:
                return []
            return self.parse_children(node, shift, exclude)
        if name == "img":
            return [{"type": "paragraph", "html": self.inline_html(node)}]
        if name == "br":
            return []
        return self.parse_children(node, shift, exclude)


# ---------------------------------------------------------------------------
# Chapter assembly
# ---------------------------------------------------------------------------


def collect_block_ids(blocks: list[dict[str, Any]]) -> set[str]:
    ids: set[str] = set()
    for block in blocks:
        if block.get("id"):
            ids.add(block["id"])
        block_type = block.get("type")
        if block_type == "list":
            for item in block.get("items", []):
                ids |= collect_block_ids(item)
        elif block_type == "definition":
            for item in block.get("items", []):
                if item.get("id"):
                    ids.add(item["id"])
                ids |= collect_block_ids(item.get("blocks", []))
        elif block_type in {"admonition", "quote"}:
            ids |= collect_block_ids(block.get("blocks", []))
    return ids


def rewrite_local_anchors(blocks: list[dict[str, Any]], doc: str, valid_ids: set[str]) -> None:
    """Point same-page anchors that were not extracted back to docs.python.org."""
    for block in blocks:
        for key in ("html", "termHtml"):
            value = block.get(key)
            if not isinstance(value, str) or 'href="#' not in value:
                continue
            soup = BeautifulSoup(value, "html.parser")
            changed = False
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if not href.startswith("#") or href == "#":
                    continue
                fragment = href[1:]
                if fragment and fragment not in valid_ids:
                    link["href"] = f"{DOCS_BASE}/{doc}.html#{fragment}"
                    link["target"] = "_blank"
                    link["rel"] = "noopener noreferrer"
                    changed = True
            if changed:
                block[key] = str(soup)

        block_type = block.get("type")
        if block_type == "list":
            for item in block.get("items", []):
                rewrite_local_anchors(item, doc, valid_ids)
        elif block_type == "definition":
            for item in block.get("items", []):
                rewrite_local_anchors(item.get("blocks", []), doc, valid_ids)
        elif block_type in {"admonition", "quote"}:
            rewrite_local_anchors(block.get("blocks", []), doc, valid_ids)


def find_section(root: Tag, section_id: str, doc: str) -> Tag:
    section = root.find("section", id=section_id)
    if section is None:
        top = [
            item.get("id")
            for item in root.find_all("section", recursive=False)
            if item.get("id")
        ]
        fail(
            f"Section '{section_id}' tidak ditemukan di {doc}. "
            f"Section level atas yang tersedia: {', '.join(top) or '(tidak ada)'}"
        )
    return section


def parse_chapter(chapter: dict[str, Any], fjson_dir: Path) -> dict[str, Any]:
    groups: list[dict[str, Any]] = []
    block_count = 0
    word_count = 0

    for source in chapter["sources"]:
        doc = source["doc"]
        fjson_path = fjson_dir / f"{doc}.fjson"
        if not fjson_path.exists():
            fail(
                f"Output Sphinx untuk '{doc}' tidak ditemukan di {fjson_path}. "
                "Jalankan ulang tanpa --skip-sphinx."
            )
        data = json.loads(fjson_path.read_text(encoding="utf-8"))
        soup = BeautifulSoup(data["body"], "lxml")
        root = soup.find("section")
        if root is None:
            fail(f"Body {doc} tidak punya <section>.")

        parser = DocParser(doc)
        exclude = set(source.get("exclude") or [])
        order = {id(section): index for index, section in enumerate(root.find_all("section"))}
        selected = [find_section(root, section_id, doc) for section_id in source["sections"]]
        selected.sort(key=lambda item: order.get(id(item), 0))

        blocks: list[dict[str, Any]] = []
        emitted: set[str] = set()
        for section in selected:
            section_id = section.get("id")
            if not section_id or section_id in emitted:
                continue
            ancestor_ids = {
                parent.get("id")
                for parent in section.parents
                if isinstance(parent, Tag) and parent.name == "section" and parent.get("id")
            }
            if ancestor_ids & emitted:
                continue
            heading = None
            for child in section.children:
                if isinstance(child, Tag) and child.name in HEADING_TAGS:
                    heading = child
                    break
            shift = 2 - int(heading.name[1]) if heading is not None else 0
            blocks.extend(parser.parse_section(section, shift, exclude))
            emitted.add(section_id)

        rewrite_local_anchors(blocks, doc, collect_block_ids(blocks))

        for block in blocks:
            block_count += 1
            word_count += len(block_plain_text(block).split())

        groups.append(
            {
                "source": {
                    "doc": doc,
                    "title": data.get("title", doc),
                    "label": source.get("label") or data.get("title", doc),
                    "url": f"{DOCS_BASE}/{doc}.html",
                },
                "blocks": blocks,
            }
        )

    return {
        "slug": chapter["slug"],
        "docVersion": DOC_VERSION,
        "generatedAt": utc_now(),
        "groups": groups,
        "blockCount": block_count,
        "wordCount": word_count,
    }


# ---------------------------------------------------------------------------
# Inventory, search, CSS, metadata
# ---------------------------------------------------------------------------


def load_inventory(json_dir: Path) -> dict[str, dict[str, Any]]:
    try:
        from sphinx.util.inventory import InventoryFile
    except ImportError:
        fail("Sphinx diperlukan untuk membaca objects.inv.")

    inventory_path = json_dir / "objects.inv"
    if not inventory_path.exists():
        fail(f"objects.inv tidak ditemukan di {inventory_path}.")
    with inventory_path.open("rb") as handle:
        inventory = InventoryFile.load(handle, f"{DOCS_BASE}/", lambda base, uri: base + uri)

    entries: dict[str, dict[str, Any]] = {}
    role_order = [
        "py:function",
        "py:class",
        "py:method",
        "py:attribute",
        "py:data",
        "py:exception",
        "std:term",
        "std:label",
    ]
    for role in role_order:
        for name, item in inventory.get(role, {}).items():
            if name in entries:
                continue
            entries[name] = {
                "name": name,
                "role": role,
                "url": item.uri,
                "display": item.display_name if item.display_name != "-" else name,
                "doc": doc_from_url(item.uri),
            }
    return entries


def doc_from_url(url: str) -> str:
    path = urllib.parse.urlparse(url).path
    prefix = f"/{DOC_VERSION}/"
    if path.startswith(prefix):
        path = path[len(prefix) :]
    path = path.removesuffix(".html").rstrip("/")
    return path or "index"


def build_api_index(entries: dict[str, dict[str, Any]], built_docs: list[str]) -> dict[str, Any]:
    allowed = set(built_docs)
    rows = [
        entry
        for entry in entries.values()
        if entry["doc"] in allowed and entry["role"].startswith("py:")
    ]
    rows.sort(key=lambda item: (item["name"].lower(), item["role"]))
    return {
        "count": len(rows),
        "roles": sorted({row["role"] for row in rows}),
        "entries": rows,
    }


def block_plain_text(block: dict[str, Any]) -> str:
    block_type = block.get("type")
    if block_type in {"paragraph", "heading", "note"}:
        return html_to_text(block.get("html") or block.get("text") or "")
    if block_type == "code":
        return block.get("text") or ""
    if block_type == "table":
        return html_to_text(block.get("html") or "")
    if block_type == "list":
        return " ".join(
            block_plain_text(child)
            for item in block.get("items", [])
            for child in item
        )
    if block_type == "definition":
        parts: list[str] = []
        for item in block.get("items", []):
            parts.append(html_to_text(item.get("termHtml") or ""))
            parts.extend(block_plain_text(child) for child in item.get("blocks", []))
        return " ".join(parts)
    if block_type in {"admonition", "quote"}:
        parts = [html_to_text(block.get("titleHtml") or "")]
        parts.extend(block_plain_text(child) for child in block.get("blocks", []))
        return " ".join(parts)
    return ""


def build_search_index(chapters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []
    for chapter in chapters:
        current: dict[str, Any] | None = None
        for group in chapter["groups"]:
            for block in group["blocks"]:
                if block.get("type") == "heading":
                    if current and current["text"].strip():
                        index.append(current)
                    current = {
                        "chapter": chapter["slug"],
                        "chapterTitle": chapter.get("title") or chapter["slug"],
                        "title": block.get("text") or html_to_text(block.get("html") or ""),
                        "anchor": block.get("id"),
                        "text": "",
                    }
                else:
                    text = block_plain_text(block).strip()
                    if not text:
                        continue
                    if current is None:
                        current = {
                            "chapter": chapter["slug"],
                            "chapterTitle": chapter.get("title") or chapter["slug"],
                            "title": chapter.get("title") or chapter["slug"],
                            "anchor": None,
                            "text": "",
                        }
                    if len(current["text"]) < 3000:
                        current["text"] = f"{current['text']} {text}".strip()
        if current and current["text"].strip():
            index.append(current)
    for entry in index:
        entry["text"] = entry["text"][:3000]
    return index


def write_pygments_css(path: Path) -> None:
    try:
        from pygments.formatters import HtmlFormatter
    except ImportError:
        fail("Pygments diperlukan untuk membuat CSS syntax highlighting.")
    light = HtmlFormatter(style="friendly").get_style_defs(".code-block")
    dark = HtmlFormatter(style="monokai").get_style_defs('[data-theme="dark"] .code-block')

    # Pygments also emits a container rule with its own background/foreground.
    # Drop only that rule: token colours are useful, but the container colours
    # belong to app/globals.css so light/dark themes stay consistent.
    def token_rules(css: str, container: str) -> str:
        return "\n".join(
            line for line in css.splitlines() if not line.startswith(f"{container} {{")
        )

    path.write_text(
        "/* Generated by tools/fetch_docs.py. Do not edit by hand. */\n"
        + token_rules(light, ".code-block")
        + "\n"
        + token_rules(dark, '[data-theme="dark"] .code-block')
        + "\n.code-block pre { background: transparent !important; }\n",
        encoding="utf-8",
    )


def copy_license(source_root: Path) -> None:
    license_path = source_root / "LICENSE"
    target = PUBLIC_DATA_DIR / "LICENSE-PSF.txt"
    if license_path.exists():
        shutil.copyfile(license_path, target)
    else:
        target.write_text(
            "Python Software Foundation License\n"
            "https://docs.python.org/3/license.html\n",
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-sphinx",
        action="store_true",
        help="Reuse .cache/sphinx-json instead of running Sphinx again.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download the tarball and rebuild Sphinx from scratch.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Never download; require the cached tarball.",
    )
    parser.add_argument(
        "--source",
        type=Path,
        help="Use a local CPython checkout/source tree instead of the tarball.",
    )
    args = parser.parse_args()

    curriculum = load_curriculum()
    built_docs = build_doc_list(curriculum)

    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_DATA_DIR.mkdir(parents=True, exist_ok=True)

    if args.source:
        source_root = args.source.expanduser().resolve()
        if not (source_root / "Doc" / "conf.py").exists():
            fail(f"{source_root} tidak terlihat seperti source CPython (Doc/conf.py tidak ada).")
        log(f"Memakai source lokal: {source_root}")
        tarball_sha = None
    else:
        tarball = download_tarball(force=args.force, offline=args.offline)
        tarball_sha = sha256(tarball)
        source_root = extract_source(tarball, force=args.force)

    build_dir = prepare_build_dir(source_root, built_docs, force=args.force)
    if args.skip_sphinx:
        json_dir = CACHE_DIR / "sphinx-json"
        if not (json_dir / "objects.inv").exists():
            fail("--skip-sphinx dipakai, tetapi .cache/sphinx-json/objects.inv belum ada.")
        log("Melewati Sphinx, memakai output JSON yang sudah ada.")
    else:
        json_dir = run_sphinx(build_dir, force=args.force)

    log("Mengurai .fjson dan objects.inv ...")
    inventory = load_inventory(json_dir)
    api_index = build_api_index(inventory, built_docs)

    chapters_dir = GENERATED_DIR / "chapters"
    shutil.rmtree(chapters_dir, ignore_errors=True)
    chapters_dir.mkdir(parents=True, exist_ok=True)

    generated_chapters: list[dict[str, Any]] = []
    for chapter in curriculum["chapters"]:
        generated = parse_chapter(chapter, json_dir)
        generated["title"] = chapter["title"]
        generated["order"] = chapter["order"]
        generated["api"] = [
            inventory[name]
            for name in chapter.get("apiHighlights", [])
            if name in inventory
        ]
        missing = [name for name in chapter.get("apiHighlights", []) if name not in inventory]
        if missing:
            log(f"Catatan: API highlight tidak ada di inventory untuk {chapter['slug']}: {', '.join(missing)}")
        (chapters_dir / f"{chapter['slug']}.json").write_text(
            json.dumps(generated, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        generated_chapters.append(generated)

    search_index = build_search_index(generated_chapters)
    (PUBLIC_DATA_DIR / "search-index.json").write_text(
        json.dumps(search_index, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    (PUBLIC_DATA_DIR / "api-index.json").write_text(
        json.dumps(api_index, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    write_pygments_css(GENERATED_DIR / "pygments.css")
    copy_license(source_root)

    import sphinx

    generated_at = utc_now()
    manifest = {
        "pythonVersion": PYTHON_VERSION,
        "docVersion": DOC_VERSION,
        "docUrl": DOCS_BASE,
        "cpythonRepo": CPYTHON_REPO,
        "tarballUrl": TARBALL_URL,
        "tarballSha256": tarball_sha,
        "sphinxVersion": sphinx.__version__,
        "builder": "sphinx-build -b json",
        "generatedAt": generated_at,
        "sourceDocs": built_docs,
        "inventoryCount": len(inventory),
        "apiIndexCount": api_index["count"],
        "searchEntryCount": len(search_index),
        "chapters": [
            {
                "slug": chapter["slug"],
                "title": chapter["title"],
                "order": chapter["order"],
                "blockCount": chapter["blockCount"],
                "wordCount": chapter["wordCount"],
            }
            for chapter in generated_chapters
        ],
    }
    (GENERATED_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    total_words = sum(chapter["wordCount"] for chapter in generated_chapters)
    log(
        f"Beres: {len(generated_chapters)} bab, {total_words:,} kata materi, "
        f"{len(search_index)} entri pencarian, {len(inventory)} objek inventory."
    )
    log(f"Output: {GENERATED_DIR.relative_to(ROOT)}/ dan {PUBLIC_DATA_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
