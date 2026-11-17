import Link from "next/link";
import { ArrowLeftIcon, ArrowRightIcon } from "@/components/icons";

export default function NotFound() {
  return (
    <section className="not-found container">
      <p className="eyebrow">404</p>
      <h1>Halaman ini tidak ada di kurikulum.</h1>
      <p>
        Mungkin tautannya salah, atau bab yang kamu cari sudah berubah. Kembali
        ke daftar materi dan pilih bab yang tersedia.
      </p>
      <div className="not-found-actions">
        <Link className="button button-primary" href="/materi">
          <ArrowLeftIcon size={17} />
          Lihat kurikulum
        </Link>
        <Link className="button button-ghost" href="/">
          Ke beranda
          <ArrowRightIcon size={17} />
        </Link>
      </div>
    </section>
  );
}
