import type { Metadata } from "next";
import Link from "next/link";
import manifest from "@/content/generated/manifest.json";
import {
  BookIcon,
  ExternalLinkIcon,
  FileTextIcon,
  LayersIcon,
  TerminalIcon,
} from "@/components/icons";
import { chapters, curriculum } from "@/lib/curriculum";

export const metadata: Metadata = {
  title: "Sumber & Metodologi",
  description:
    "Cara PyJourney mengambil materi dari cpython/Doc, membangunnya dengan Sphinx JSON Builder, dan memetakan objects.inv. Lengkap dengan lisensi PSF.",
};

export default function SumberPage() {
  const chapterDocs = Array.from(
    new Set(chapters.flatMap((chapter) => chapter.sources.map((source) => source.doc))),
  );
  const extraDocs = manifest.sourceDocs.filter((doc) => !chapterDocs.includes(doc));
  const allDocs = [...chapterDocs, ...extraDocs];

  return (
    <>
      <section className="page-hero">
        <div className="container">
          <p className="eyebrow">Sumber & metodologi</p>
          <h1>Terbuka dari hulu ke hilir.</h1>
          <p className="page-lede">
            PyJourney tidak menyalin materi dari blog atau forum. Semua teks
            pembelajaran diambil dari repositori dokumentasi resmi CPython,
            dibangun dengan Sphinx, lalu diolah menjadi data yang bisa dibaca
            Next.js.
          </p>
          <div className="page-meta-row">
            <span>
              <BookIcon size={16} />
              Python {manifest.pythonVersion}
            </span>
            <span>
              <TerminalIcon size={16} />
              Sphinx {manifest.sphinxVersion}
            </span>
            <span>
              <LayersIcon size={16} />
              {manifest.inventoryCount.toLocaleString("id-ID")} objek inventory
            </span>
          </div>
        </div>
      </section>

      <section className="section section-tight">
        <div className="container source-page-grid">
          <div className="source-prose">
            <p className="eyebrow">Dari mana?</p>
            <h2>cpython/Doc, bukan dokumentasi pihak ketiga.</h2>
            <p>
              Pipeline mengambil tarball resmi{" "}
              <a href={manifest.tarballUrl} target="_blank" rel="noopener noreferrer">
                Python {manifest.pythonVersion} dari python.org
                <ExternalLinkIcon size={14} />
              </a>
              . Dari dalamnya, folder <code>Doc/</code> berisi sumber
              reStructuredText untuk seluruh dokumentasi Python, termasuk
              tutorial, language reference, dan standard library.
            </p>
            <p>
              Build dibatasi pada dokumen yang relevan dengan kurikulum. Sphinx
              JSON Builder menghasilkan satu file <code>.fjson</code> per
              halaman; parser PyJourney mengubah HTML semantik dari builder
              tersebut menjadi blok terstruktur: heading, paragraf, kode, tabel,
              definition list, dan admonition.
            </p>
            <p>
              Setelah build, <code>objects.inv</code> dibaca dengan{" "}
              <code>sphinx.util.inventory</code>. Inventory inilah yang menjadi
              sumber indeks API dan chip referensi di setiap bab.
            </p>
            <div className="source-links">
              <a href={manifest.cpythonRepo} target="_blank" rel="noopener noreferrer">
                cpython/Doc di GitHub <ExternalLinkIcon size={14} />
              </a>
              <a href={manifest.docUrl} target="_blank" rel="noopener noreferrer">
                Dokumentasi Python {manifest.docVersion} <ExternalLinkIcon size={14} />
              </a>
              <a href={manifest.tarballUrl} target="_blank" rel="noopener noreferrer">
                Tarball sumber <ExternalLinkIcon size={14} />
              </a>
            </div>
          </div>

          <aside className="build-card">
            <p className="section-kicker">Build yang bisa diulang</p>
            <h2>Jalankan sendiri</h2>
            <pre className="pipeline-code">
              <code>{`# di dalam devcontainer
npm run content:build

# hanya parse ulang cache Sphinx
npm run content:build:fast`}</code>
            </pre>
            <p>
              Butuh Python 3.12+, Sphinx {manifest.sphinxVersion}, BeautifulSoup,
              dan lxml. Semuanya sudah dipasang oleh devcontainer.
            </p>
            <dl className="build-meta">
              <div>
                <dt>Builder</dt>
                <dd>{manifest.builder}</dd>
              </div>
              <div>
                <dt>Dokumen dibangun</dt>
                <dd>{manifest.sourceDocs.length} halaman</dd>
              </div>
              <div>
                <dt>Entri pencarian</dt>
                <dd>{manifest.searchEntryCount} bagian</dd>
              </div>
              <div>
                <dt>Build terakhir</dt>
                <dd>
                  {new Intl.DateTimeFormat("id-ID", {
                    dateStyle: "medium",
                    timeStyle: "short",
                    timeZone: "Asia/Jakarta",
                  }).format(new Date(manifest.generatedAt))}{" "}
                  WIB
                </dd>
              </div>
            </dl>
          </aside>
        </div>
      </section>

      <section className="section section-tight">
        <div className="container">
          <div className="section-heading section-heading-compact">
            <div>
              <p className="eyebrow">Dokumen sumber</p>
              <h2>Halaman resmi yang ikut dibangun.</h2>
            </div>
          </div>
          <div className="doc-table">
            <div className="doc-table-head">
              <span>Dokumen</span>
              <span>Dipakai di</span>
              <span>Section</span>
              <span />
            </div>
            {allDocs.map((doc) => {
              const usedBy = chapters.filter((chapter) =>
                chapter.sources.some((source) => source.doc === doc),
              );
              const sectionCount = chapters.reduce(
                (total, chapter) =>
                  total +
                  chapter.sources
                    .filter((source) => source.doc === doc)
                    .reduce((sum, source) => sum + source.sections.length, 0),
                0,
              );
              return (
                <a
                  className="doc-row"
                  key={doc}
                  href={`${manifest.docUrl}${doc}.html`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  <span className="doc-name">
                    <FileTextIcon size={16} />
                    {doc}
                  </span>
                  <span>
                    {usedBy.length
                      ? usedBy.map((chapter) => `Bab ${chapter.order}`).join(", ")
                      : "Inventory API"}
                  </span>
                  <span>{sectionCount || "—"}</span>
                  <span>
                    <ExternalLinkIcon size={15} />
                  </span>
                </a>
              );
            })}
          </div>
        </div>
      </section>

      <section className="section section-tight">
        <div className="container license-grid">
          <div className="license-card">
            <p className="section-kicker">Lisensi</p>
            <h2>Materi tetap milik PSF.</h2>
            <p>
              Teks dokumentasi Python dilisensikan di bawah Python Software
              Foundation License Version 2. PyJourney mempertahankan atribusi
              dan menyediakan salinan lisensi. Antarmuka, ringkasan bahasa
              Indonesia, soal latihan, dan fitur progres adalah tambahan
              PyJourney dan bukan bagian dari dokumentasi resmi.
            </p>
            <div className="license-actions">
              <a
                className="button button-ghost button-small"
                href="/data/LICENSE-PSF.txt"
                target="_blank"
                rel="noopener noreferrer"
              >
                Baca PSF License
                <ExternalLinkIcon size={15} />
              </a>
              <Link className="text-button" href="/materi">
                Kembali ke kurikulum
              </Link>
            </div>
          </div>
          <div className="honesty-card">
            <p className="section-kicker">Catatan jujur</p>
            <h2>Apa yang bukan materi resmi?</h2>
            <ul>
              <li>Judul bab, tujuan belajar, dan poin kunci dalam bahasa Indonesia.</li>
              <li>Soal latihan beserta pembahasannya.</li>
              <li>Fitur progres, catatan pribadi, pencarian, dan indeks API.</li>
              <li>Desain antarmuka dan alur kurikulum.</li>
            </ul>
            <p>
              Teks materi resmi sengaja dibiarkan dalam bahasa Inggris agar
              istilah teknis tidak bergeser. Gunakan halaman asli di
              docs.python.org sebagai rujukan utama.
            </p>
          </div>
        </div>
      </section>

      <section className="section section-tight">
        <div className="container build-details">
          <details>
            <summary>Detail teknis build</summary>
            <div>
              <p>
                <strong>Versi Python:</strong> {manifest.pythonVersion}
                <br />
                <strong>Versi dokumentasi:</strong> {manifest.docVersion}
                <br />
                <strong>Sphinx:</strong> {manifest.sphinxVersion}
                <br />
                <strong>Builder:</strong> {manifest.builder}
                <br />
                <strong>Jumlah objek inventory:</strong>{" "}
                {manifest.inventoryCount.toLocaleString("id-ID")}
                <br />
                <strong>SHA-256 tarball:</strong>{" "}
                <code>{manifest.tarballSha256 ?? "menggunakan source lokal"}</code>
              </p>
              <p>
                Source dokumentasi diambil dari{" "}
                <a href={manifest.cpythonRepo} target="_blank" rel="noopener noreferrer">
                  cpython/Doc
                </a>{" "}
                pada tag v{manifest.pythonVersion}. Build hanya menyertakan
                halaman yang dipakai kurikulum plus beberapa halaman referensi
                untuk inventory.
              </p>
            </div>
          </details>
        </div>
      </section>
    </>
  );
}
