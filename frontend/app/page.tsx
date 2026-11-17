import Link from "next/link";
import manifest from "@/content/generated/manifest.json";
import { ChapterCard } from "@/components/ChapterCard";
import { OverallProgress } from "@/components/OverallProgress";
import {
  ArrowRightIcon,
  BookIcon,
  CheckIcon,
  ExternalLinkIcon,
  FileTextIcon,
  LayersIcon,
  SparklesIcon,
  TerminalIcon,
} from "@/components/icons";
import { chapters, curriculum, totalMinutes } from "@/lib/curriculum";

const heroCode = `<span class="k">class</span> <span class="nc">Petualang</span><span class="p">:</span>
    <span class="k">def</span> <span class="fm">__init__</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">nama</span><span class="p">):</span>
        <span class="bp">self</span><span class="p">.</span><span class="n">nama</span> <span class="o">=</span> <span class="n">nama</span>
        <span class="bp">self</span><span class="p">.</span><span class="n">xp</span> <span class="o">=</span> <span class="mi">0</span>

    <span class="k">def</span> <span class="nf">selesai</span><span class="p">(</span><span class="bp">self</span><span class="p">,</span> <span class="n">bab</span><span class="p">):</span>
        <span class="bp">self</span><span class="p">.</span><span class="n">xp</span> <span class="o">+=</span> <span class="mi">100</span>
        <span class="k">return</span> <span class="sa">f</span><span class="s2">&quot;{self.nama} selesai {bab}!&quot;</span>`;

const hours = Math.floor(totalMinutes / 60);
const minutes = totalMinutes % 60;

const sourceChips = [
  "The Python Tutorial",
  "Python Language Reference",
  "The Python Standard Library",
  "objects.inv",
  "PSF License",
];

export default function HomePage() {
  const firstChapter = chapters[0];

  return (
    <>
      <section className="hero">
        <div className="hero-grid container">
          <div className="hero-copy">
            <span className="eyebrow">
              <span className="pulse-dot" />
              Python {curriculum.pythonVersion} · Dokumentasi resmi PSF
            </span>
            <h1>
              Belajar Python dari <span className="marker">sumbernya.</span>
            </h1>
            <p className="hero-lede">
              Jalur terstruktur dari variabel sampai OOP, diambil langsung dari
              dokumentasi resmi CPython lewat Sphinx JSON Builder. Tanpa materi
              acak, tanpa setup yang bikin laptop penuh.
            </p>
            <div className="hero-actions">
              <Link className="button button-primary" href={`/materi/${firstChapter.slug}`}>
                Mulai dari Bab 1
                <ArrowRightIcon size={18} />
              </Link>
              <Link className="button button-ghost" href="/materi">
                Lihat kurikulum
              </Link>
            </div>
            <div className="hero-proof">
              <span>
                <CheckIcon size={15} /> 7 bab terurut
              </span>
              <span>
                <CheckIcon size={15} /> ±{hours}j {minutes}m materi
              </span>
              <span>
                <CheckIcon size={15} /> 100% sumber resmi
              </span>
            </div>
          </div>

          <div className="hero-visual" aria-label="Contoh kode Python">
            <div className="hero-glow" aria-hidden="true" />
            <div className="terminal-card">
              <div className="terminal-bar">
                <span className="terminal-dots" aria-hidden="true">
                  <i />
                  <i />
                  <i />
                </span>
                <span className="terminal-file">petualang.py</span>
                <span className="terminal-tag">OOP</span>
              </div>
              <div className="code-block hero-code-block">
                <pre>
                  <code dangerouslySetInnerHTML={{ __html: heroCode }} />
                </pre>
              </div>
              <div className="terminal-output">
                <span className="terminal-prompt">›</span>
                <span>
                  p = Petualang(&quot;Kamu&quot;)
                  <br />
                  p.selesai(&quot;OOP Dasar&quot;)
                </span>
                <span className="terminal-result">&quot;Kamu selesai OOP Dasar!&quot;</span>
              </div>
            </div>

            <div className="float-card float-card-a">
              <span className="float-icon">
                <LayersIcon size={17} />
              </span>
              <span>
                <strong>7 bab</strong>
                <small>dari variabel ke OOP</small>
              </span>
            </div>
            <div className="float-card float-card-b">
              <span className="float-icon float-icon-yellow">
                <FileTextIcon size={17} />
              </span>
              <span>
                <strong>objects.inv</strong>
                <small>{manifest.inventoryCount.toLocaleString("id-ID")} objek terpetakan</small>
              </span>
            </div>
          </div>
        </div>
      </section>

      <div className="source-strip">
        <div className="container source-strip-inner">
          <span className="source-strip-label">Disusun dari</span>
          {sourceChips.map((chip) => (
            <span className="source-chip" key={chip}>
              {chip}
            </span>
          ))}
        </div>
      </div>

      <section className="section curriculum-section" id="kurikulum">
        <div className="container">
          <div className="section-heading">
            <div>
              <p className="eyebrow">Kurikulum</p>
              <h2>Satu jalur, tujuh bab.</h2>
              <p className="section-lede">
                Urutannya sengaja dibuat naik bertahap. Setiap bab memakai teks
                resmi dari CPython, lalu dilengkapi tujuan belajar dan latihan
                singkat.
              </p>
            </div>
            <OverallProgress />
          </div>

          <div className="chapter-grid">
            {chapters.map((chapter) => (
              <ChapterCard chapter={chapter} key={chapter.slug} />
            ))}
          </div>
        </div>
      </section>

      <section className="section why-section">
        <div className="container">
          <div className="section-heading section-heading-compact">
            <div>
              <p className="eyebrow">Kenapa PyJourney</p>
              <h2>Bukan rangkuman asal-asalan.</h2>
            </div>
          </div>
          <div className="feature-grid">
            <article className="feature-card">
              <span className="feature-icon">
                <BookIcon size={21} />
              </span>
              <h3>Langsung dari sumbernya</h3>
              <p>
                Teks materi berasal dari <code>cpython/Doc</code> versi{" "}
                {manifest.pythonVersion}, dibangun dengan Sphinx JSON Builder —
                bukan salinan blog atau ringkasan pihak ketiga.
              </p>
              <a
                className="feature-link"
                href={manifest.cpythonRepo}
                target="_blank"
                rel="noopener noreferrer"
              >
                Lihat repositori sumber <ExternalLinkIcon size={14} />
              </a>
            </article>
            <article className="feature-card">
              <span className="feature-icon feature-icon-yellow">
                <SparklesIcon size={21} />
              </span>
              <h3>Dibingkai untuk belajar</h3>
              <p>
                Setiap bab punya tujuan, poin kunci, latihan, catatan pribadi,
                dan progres. Teks resmi tetap utuh; lapisan belajarnya yang
                membuatnya mudah diikuti.
              </p>
              <Link className="feature-link" href="/materi">
                Jelajahi kurikulum <ArrowRightIcon size={14} />
              </Link>
            </article>
            <article className="feature-card">
              <span className="feature-icon feature-icon-green">
                <TerminalIcon size={21} />
              </span>
              <h3>Bisa dijalankan di container</h3>
              <p>
                Devcontainer Podman sudah disiapkan. Buka di VS Code, pilih
                “Reopen in Container”, dan semua dependensi Python, Node, dan
                Sphinx terisolasi dari laptop.
              </p>
              <Link className="feature-link" href="/sumber">
                Lihat cara build <ArrowRightIcon size={14} />
              </Link>
            </article>
          </div>
        </div>
      </section>

      <section className="section pipeline-section">
        <div className="container pipeline-grid">
          <div className="pipeline-copy">
            <p className="eyebrow">Metodologi</p>
            <h2>Dari reStructuredText ke layar.</h2>
            <p>
              Pipeline-nya sengaja transparan dan bisa kamu jalankan ulang.
              Tidak ada scraping HTML sembarangan: dokumentasi dibangun dengan
              builder resmi Sphinx, lalu inventory <code>objects.inv</code>{" "}
              dipakai untuk memetakan objek API.
            </p>
            <Link className="button button-ghost" href="/sumber">
              Baca detail metodologi
              <ArrowRightIcon size={17} />
            </Link>
          </div>
          <div className="pipeline-steps">
            <div className="pipeline-step">
              <span className="pipeline-number">01</span>
              <div>
                <h3>Ambil source resmi</h3>
                <p>
                  Tarball CPython {manifest.pythonVersion} dari python.org,
                  berisi <code>Doc/</code> dan <code>Include/patchlevel.h</code>.
                </p>
              </div>
            </div>
            <div className="pipeline-step">
              <span className="pipeline-number">02</span>
              <div>
                <h3>Build dengan Sphinx</h3>
                <p>
                  <code>sphinx-build -b json</code> menghasilkan{" "}
                  <code>.fjson</code> untuk setiap halaman yang dipilih.
                </p>
              </div>
            </div>
            <div className="pipeline-step">
              <span className="pipeline-number">03</span>
              <div>
                <h3>Petakan & render</h3>
                <p>
                  Parser mengambil section, kode, tabel, dan tautan;{" "}
                  <code>objects.inv</code> mengisi indeks API. Next.js merender
                  semuanya.
                </p>
              </div>
            </div>
            <pre className="pipeline-code">
              <code>{`$ npm run content:build
→ sphinx-build -b json Doc/ .cache/sphinx-json
→ content/generated/chapters/*.json
→ public/data/search-index.json`}</code>
            </pre>
          </div>
        </div>
      </section>

      <section className="cta-band">
        <div className="container cta-inner">
          <div>
            <p className="eyebrow">Siap mulai?</p>
            <h2>Bab pertama cuma butuh satu klik.</h2>
            <p>
              Mulai dari variabel dan tipe data, lalu naik pelan-pelan sampai
              kamu bisa merancang class dan inheritance sendiri.
            </p>
          </div>
          <div className="cta-actions">
            <Link className="button button-primary" href={`/materi/${firstChapter.slug}`}>
              Mulai belajar
              <ArrowRightIcon size={18} />
            </Link>
            <Link className="button button-ghost" href="/indeks">
              Lihat indeks API
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
