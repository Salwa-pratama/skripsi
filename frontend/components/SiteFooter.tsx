import Link from "next/link";
import manifest from "@/content/generated/manifest.json";
import { curriculum } from "@/lib/curriculum";
import { ExternalLinkIcon } from "./icons";
import { Logo } from "./Logo";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-brand">
          <Logo />
          <p>
            Jalur belajar Python 3 yang disusun dari dokumentasi resmi CPython.
            Dibaca, dicari, dan dilacak kemajuannya dalam satu tempat.
          </p>
          <p className="footer-version">
            Python {manifest.pythonVersion} · Sphinx {manifest.sphinxVersion} ·{" "}
            {manifest.inventoryCount.toLocaleString("id-ID")} objek inventory
          </p>
        </div>

        <div className="footer-column">
          <h2>Belajar</h2>
          <Link href="/materi">Kurikulum</Link>
          <Link href={`/materi/${curriculum.chapters[0]?.slug ?? ""}`}>Mulai dari awal</Link>
          <Link href="/indeks">Indeks API</Link>
        </div>

        <div className="footer-column">
          <h2>Sumber</h2>
          <a href={manifest.docUrl} target="_blank" rel="noopener noreferrer">
            Dokumentasi Python 3.13 <ExternalLinkIcon size={14} />
          </a>
          <a href={manifest.cpythonRepo} target="_blank" rel="noopener noreferrer">
            Repositori cpython/Doc <ExternalLinkIcon size={14} />
          </a>
          <Link href="/sumber">Metodologi & lisensi</Link>
        </div>

        <div className="footer-column">
          <h2>Lisensi</h2>
          <a href="/data/LICENSE-PSF.txt" target="_blank" rel="noopener noreferrer">
            PSF License <ExternalLinkIcon size={14} />
          </a>
          <p className="footer-fine">
            Materi asli © Python Software Foundation. PyJourney tidak berafiliasi
            secara resmi dengan PSF.
          </p>
        </div>
      </div>

      <div className="container footer-bottom">
        <p>
          Dibangun dengan Next.js, Sphinx JSON Builder, dan objects.inv. Materi
          resmi tetap dalam bahasa Inggris; ringkasan dan latihan ditulis dalam
          bahasa Indonesia.
        </p>
        <p>Untuk belajar, bukan menggantikan dokumentasi resmi.</p>
      </div>
    </footer>
  );
}
