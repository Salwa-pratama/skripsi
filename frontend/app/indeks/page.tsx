import type { Metadata } from "next";
import Link from "next/link";
import { ApiExplorer } from "@/components/ApiExplorer";
import { BookIcon, ExternalLinkIcon, FileTextIcon, LayersIcon } from "@/components/icons";
import { getApiIndex } from "@/lib/content";
import manifest from "@/content/generated/manifest.json";

export const metadata: Metadata = {
  title: "Indeks API",
  description:
    "Indeks objek Python yang dipetakan dari objects.inv hasil build Sphinx dokumentasi resmi CPython 3.13.",
};

export default function IndeksPage() {
  const api = getApiIndex();

  return (
    <>
      <section className="page-hero">
        <div className="container">
          <p className="eyebrow">Indeks API</p>
          <h1>Semua objek, satu indeks.</h1>
          <p className="page-lede">
            Daftar fungsi, class, method, atribut, dan exception yang muncul di
            dokumentasi resmi. Datanya dibaca langsung dari{" "}
            <code>objects.inv</code> hasil Sphinx JSON Builder — bukan daftar
            manual.
          </p>
          <div className="page-meta-row">
            <span>
              <LayersIcon size={16} />
              {api.count.toLocaleString("id-ID")} objek
            </span>
            <span>
              <FileTextIcon size={16} />
              {manifest.inventoryCount.toLocaleString("id-ID")} entri inventory
            </span>
            <span>
              <BookIcon size={16} />
              Python {manifest.pythonVersion}
            </span>
          </div>
        </div>
      </section>

      <section className="section section-tight">
        <div className="container">
          <div className="index-note">
            <div>
              <strong>Objek apa yang masuk ke sini?</strong>
              <p>
                Hanya objek dari dokumen yang ikut dibangun: tutorial, built-in
                types, language reference, built-in functions, exceptions, dan
                data model. Klik nama objek untuk membuka halaman resminya.
              </p>
            </div>
            <Link className="text-button" href="/sumber">
              Cara indeks dibuat
              <ExternalLinkIcon size={14} />
            </Link>
          </div>

          <ApiExplorer entries={api.entries} />
        </div>
      </section>
    </>
  );
}
