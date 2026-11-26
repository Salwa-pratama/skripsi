#!/usr/bin/env python3
"""
pemandu_ucapan.py — Generator kalimat pemandu belajar (Sokratik) yang enak didengar TTS.

Dua backend:
  1. "template" (default, 0 MB): kalimat dirakit dari beberapa pola + variasi acak
     berbasis hash pertanyaan, jadi tidak kaku, tetap konsisten, dan instan.
  2. "qwen" (opsional, ~400 MB): Qwen2.5-0.5B-Instruct GGUF Q4_K_M via llama.cpp
     untuk kalimat yang benar-benar dinamis. Kalau gagal/lambat -> otomatis balik ke template.

Aturan output (ramah ESP32 TTS):
  - tanpa emoji, markdown, bullet, atau singkatan aneh
  - 2-4 kalimat pendek, <= ~45 kata (sekitar 12-18 detik audio)
  - selalu diakhiri pertanyaan/ajakan supaya pelajar berpikir atau mencoba kode

Pemakaian cepat:
    from pemandu_ucapan import PemanduUcapan
    pemandu = PemanduUcapan()                      # template saja
    hasil = pemandu.buat_ucapan(query, top_doc, skor=0.72)
    print(hasil["speech"])

Uji dari terminal:
    python pemandu_ucapan.py "what is meant by a loop?"
    python pemandu_ucapan.py --backend qwen "apa itu modulo?"
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import zlib
from pathlib import Path
from typing import Any, Mapping, Optional

# --------------------------------------------------------------------------- #
# 1. PEMBERSIH TEKS (supaya aman dibacakan mesin TTS)
# --------------------------------------------------------------------------- #

_EMOJI_RE = re.compile(
    "[\U0001F000-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF"
    "\u2B00-\u2BFF\uFE0F\u200D]"
)
_MARKDOWN_RE = re.compile(r"[*_`#>\[\]|]")
_BULLET_RE = re.compile(r"^\s*[-•]\s+", re.MULTILINE)


def bersihkan_judul(judul: str) -> str:
    """'Episode 1: Mendefinisikan Fungsi (def) & Docstring' -> 'Mendefinisikan Fungsi def dan Docstring'."""
    if not judul:
        return ""
    t = str(judul)
    t = re.sub(r"^\s*episode\s*\d+\s*[:.\-]\s*", "", t, flags=re.IGNORECASE)
    t = re.sub(r"\(([^()]*)\)", r"\1", t)          # buang tanda kurung, isi tetap
    t = re.sub(r"\s*&\s*", " dan ", t)
    t = re.sub(r"\s*/\s*", " atau ", t)
    t = re.sub(r"\s*[:;]\s*", ", ", t)
    t = re.sub(r"\s+", " ", t).strip(" ,.-")
    return t


def rapikan_untuk_tts(teks: str, max_chars: int = 330) -> str:
    """Buang semua yang bikin TTS terbaca aneh, lalu batasi panjangnya."""
    if not teks:
        return ""
    t = _EMOJI_RE.sub(" ", str(teks))

    # --- operator & simbol: harus SEBELUM tanda markdown dibuang ---
    t = t.replace("```", " ")
    t = re.sub(r"\s*(->|=>|→|⇒)\s*", " menjadi ", t)
    t = re.sub(r"\s*!=\s*", " tidak sama dengan ", t)
    t = re.sub(r"\s*==\s*", " sama dengan ", t)
    t = re.sub(r"\s*>=\s*", " lebih besar atau sama dengan ", t)
    t = re.sub(r"\s*<=\s*", " lebih kecil atau sama dengan ", t)
    t = re.sub(r"\s*=\s*", " sama dengan ", t)
    t = re.sub(r"\s*&\s*", " dan ", t)
    t = re.sub(r"\s*%\s*", " persen ", t)
    t = re.sub(r"\s*\+\s*", " plus ", t)

    # --- sisa penanda markdown ---
    t = _MARKDOWN_RE.sub(" ", t)
    t = _BULLET_RE.sub("", t)
    t = t.replace("•", " ").replace("–", "-").replace("—", ",").replace("\u2019", "'")
    t = re.sub(r"\.{3,}", ", ", t)
    t = re.sub(r"\(([^()]*)\)", r" \1 ", t)
    t = re.sub(r"[\"“”]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    t = re.sub(r"\s+([.,;:!?])", r"\1", t)        # "break ." -> "break."
    t = re.sub(r",\s*([.?!])", r"\1", t)          # "ya,." -> "ya."
    t = re.sub(r"[,\s]+$", "", t)                 # buang koma menggantung

    if len(t) > max_chars:
        potong = t[:max_chars]
        batas = max(potong.rfind(". "), potong.rfind("? "), potong.rfind("! "))
        if batas > 60:
            t = potong[: batas + 1]
        else:
            t = potong.rsplit(" ", 1)[0].rstrip(" ,;:") + "."

    if t and t[-1] not in ".?!":
        t += "."
    return t


def estimasi_durasi(teks: str) -> float:
    """Perkiraan durasi audio (detik). Bahasa Indonesia santai ~2.5 kata/detik."""
    kata = len(re.findall(r"\w+", teks))
    return round(kata / 2.5, 1)


# --------------------------------------------------------------------------- #
# 2. TEMPLATE NARASI SOKRATIK
# --------------------------------------------------------------------------- #

_OPENER_PASTI = [
    "Wah, pertanyaan bagus!",
    "Nah, ini pertanyaan yang sering banget muncul.",
    "Oke, aku bantu arahkan ya.",
    "Sip, kita bedah pelan-pelan ya.",
    "Hmm, menarik nih.",
]

_OPENER_RAGU = [
    "Hmm, aku belum yakin.",
    "Jujur, aku agak ragu.",
    "Aku belum yakin nih.",
]

_PENGHUBUNG = [
    "Ini nyambung sama bab {bab}, tepatnya di bagian {episode}.",
    "Kalau dilihat dari materinya, ini masuk bab {bab}, di bagian {episode}.",
    "Materi yang paling dekat ada di bab {bab}, bagian {episode}.",
]

_KONSEP = [
    "Intinya di situ kamu belajar {konsep}.",
    "Konsep kuncinya, {konsep}.",
    "Yang perlu kamu pegang, {konsep}.",
]

_PENUTUP = [
    "Coba tebak dulu apa yang bakal terjadi, baru jalankan kodenya. Berani?",
    "Sekarang coba tulis versi kecilnya di editor, lalu ubah satu bagian. Apa yang berubah menurutmu?",
    "Sebelum lihat jawaban, coba jelaskan pakai bahasamu sendiri. Sudah kebayang?",
    "Coba praktikkan satu baris dulu di editor tanpa contekan. Kamu pasti bisa, kan?",
    "Menurutmu, kalau bagian itu dihapus, programnya masih jalan? Berani buktikan?",
]

_PENUTUP_RAGU = [
    "Coba cek dulu materinya, lalu ceritakan ulang pakai bahasamu sendiri. Bisa?",
    "Kalau masih ragu, tulis pertanyaanmu lebih spesifik, nanti aku bantu lagi.",
]

# Kata yang huruf depannya jangan diubah jadi huruf kecil.
_KATA_KHUSUS = {
    "python", "numpy", "pandas", "json", "html", "css", "sql", "api", "oop",
    "django", "flask", "git", "linux", "esp32", "true", "false", "none",
    "print", "input", "def", "for", "while", "if", "else", "elif", "list",
    "tuple", "dict", "set", "string", "integer", "float", "boolean",
}


def _kecilkan_awal(teks: str) -> str:
    """'Eksekusi blok berulang' -> 'eksekusi blok berulang' (kecuali nama khusus)."""
    if not teks:
        return teks
    kata_pertama = re.split(r"\s+", teks, maxsplit=1)[0]
    bersih = kata_pertama.strip(".,;:()'\"")
    if bersih.lower() in _KATA_KHUSUS or bersih.isupper() or any(c.isdigit() for c in bersih):
        return teks
    return teks[0].lower() + teks[1:]


def _pendekkan(teks: str, maks: int = 75) -> str:
    """Ambil klausa pertama yang muat, tanpa elipsis (biar TTS tidak baca aneh)."""
    teks = teks.strip().rstrip(".")
    if len(teks) <= maks:
        return teks
    potong = teks[:maks]
    for pemisah in (", ", "; ", " dan ", " atau "):
        pos = potong.rfind(pemisah)
        if pos > 25:
            return potong[:pos].rstrip(" ,;")
    return potong.rsplit(" ", 1)[0].rstrip(" ,;")


def _tutup_kalimat(teks: str) -> str:
    teks = teks.strip().rstrip(" ,;:")
    return teks if teks.endswith((".", "?", "!")) else teks + "."


def _susun(pembuka: str, penghubung: str, konsep: str, penutup: str,
           bab: str, maks: int = 300) -> str:
    """
    Rakit kalimat dengan prioritas: penutup Sokratik HARUS selamat.
    Kalau kepanjangan, buang pembuka -> pendekkan konsep -> pendekkan penghubung.
    """
    penuh = f"{pembuka} {penghubung} {konsep} {penutup}"
    if len(penuh) <= maks:
        return penuh

    tanpa_buka = f"{penghubung} {konsep} {penutup}"
    if len(tanpa_buka) <= maks:
        return tanpa_buka

    konsep_pendek = _tutup_kalimat(_pendekkan(konsep, 70))
    versi = f"{penghubung} {konsep_pendek} {penutup}"
    if len(versi) <= maks:
        return versi

    hubung_pendek = f"Ini nyambung sama bab {bab}."
    versi = f"{hubung_pendek} {konsep_pendek} {penutup}"
    if len(versi) <= maks:
        return versi

    return (
        f"{hubung_pendek} {_tutup_kalimat(_pendekkan(konsep, 45))} "
        f"{_tutup_kalimat(_pendekkan(penutup, 90))}"
    )


# --------------------------------------------------------------------------- #
# 3. BACKEND OPSIONAL: Qwen2.5-0.5B-Instruct (GGUF)
# --------------------------------------------------------------------------- #

DEFAULT_GGUF = Path.home() / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"
HF_REPO = "Qwen/Qwen2.5-0.5B-Instruct-GGUF"
HF_FILE = "qwen2.5-0.5b-instruct-q4_k_m.gguf"

_SISTEM_QWEN = (
    "Kamu pemandu belajar Python untuk pelajar Indonesia. "
    "Tulis SATU respons lisan maksimal tiga kalimat pendek, maksimal empat puluh lima kata. "
    "Gaya santai, hangat, seperti kakak yang menemani belajar. "
    "Tanpa emoji, tanpa markdown, tanpa daftar, tanpa tanda kurung, tanpa menyebut kata konteks atau passage. "
    "Akhiri dengan satu pertanyaan atau ajakan singkat supaya pelajar mencoba kodenya sendiri."
)


def unduh_model_gguf(tujuan: Optional[Path] = None) -> Path:
    """Unduh GGUF Q4_K_M (~397 MB) ke folder model lokal."""
    from huggingface_hub import hf_hub_download

    tujuan = Path(tujuan or DEFAULT_GGUF)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    if tujuan.exists():
        print(f"[INFO] Model sudah ada: {tujuan}")
        return tujuan
    print(f"[UNDUH] {HF_REPO}/{HF_FILE} -> {tujuan.parent} (~397 MB, sekali saja)")
    path = hf_hub_download(repo_id=HF_REPO, filename=HF_FILE, local_dir=str(tujuan.parent))
    hasil = Path(path)
    if hasil != tujuan and hasil.exists():
        hasil.replace(tujuan)
    print(f"[OK] Tersimpan di {tujuan}")
    return tujuan


class BackendQwen:
    """Pembungkus tipis llama.cpp. Import-nya lambat, jadi dibuat lazy."""

    def __init__(self, model_path: Optional[Path] = None, n_threads: Optional[int] = None,
                 n_ctx: int = 1024, verbose: bool = False):
        from llama_cpp import Llama  # noqa: F401  (gagal -> ImportError, ditangani pemanggil)

        self.model_path = Path(model_path or os.environ.get("PEMANDU_GGUF") or DEFAULT_GGUF)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model GGUF tidak ditemukan: {self.model_path}\n"
                f"Unduh dengan: python pemandu_ucapan.py --download"
            )
        self.llm = Llama(
            model_path=str(self.model_path),
            n_ctx=n_ctx,
            n_threads=n_threads or min(4, os.cpu_count() or 4),
            verbose=verbose,
        )

    def tulis(self, query: str, bab: str, episode: str, konsep: str) -> str:
        pesan = [
            {"role": "system", "content": _SISTEM_QWEN},
            {
                "role": "user",
                "content": (
                    f"Materi: bab {bab}, bagian {episode}. Konsep: {konsep}.\n"
                    f"Pertanyaan pelajar: {query}\n"
                    "Tulis respons lisannya sekarang."
                ),
            },
        ]
        out = self.llm.create_chat_completion(
            messages=pesan,
            max_tokens=110,
            temperature=0.75,
            top_p=0.9,
            repeat_penalty=1.1,
            stop=["\n\n", "Pelajar:", "Materi:"],
        )
        return (out["choices"][0]["message"]["content"] or "").strip()


def _layak_dipakai(teks: str) -> bool:
    if not teks:
        return False
    kata = len(re.findall(r"\w+", teks))
    kalimat = len(re.findall(r"[.?!]", teks))
    return 8 <= kata <= 55 and kalimat <= 4 and "```" not in teks


# --------------------------------------------------------------------------- #
# 4. KELAS UTAMA
# --------------------------------------------------------------------------- #

class PemanduUcapan:
    def __init__(self, backend: str = "auto", model_path: Optional[Path] = None,
                 n_threads: Optional[int] = None, verbose: bool = False):
        self.backend = backend
        self._qwen: Optional[BackendQwen] = None
        self._qwen_gagal = False
        self._model_path = model_path
        self._n_threads = n_threads
        self._verbose = verbose
        self._terakhir: dict[str, int] = {}

        if backend == "qwen":
            self._qwen = self._muat_qwen()

    # -- util -----------------------------------------------------------------
    def _muat_qwen(self) -> Optional[BackendQwen]:
        try:
            b = BackendQwen(self._model_path, self._n_threads, verbose=self._verbose)
            if self._verbose:
                print(f"[QWEN] siap: {b.model_path}")
            return b
        except Exception as exc:  # ImportError, FileNotFoundError, dll.
            self._qwen_gagal = True
            if self._verbose:
                print(f"[QWEN] dilewati ({type(exc).__name__}: {exc}). Pakai template.")
            return None

    def _pilih(self, pool: list[str], kunci: str) -> str:
        """Pilih varian berbasis hash (stabil) tapi tidak mengulang yang barusan dipakai."""
        idx = zlib.crc32(kunci.encode("utf-8")) % len(pool)
        if self._terakhir.get(id(pool)) == idx and len(pool) > 1:
            idx = (idx + 1) % len(pool)
        self._terakhir[id(pool)] = idx
        return pool[idx]

    # -- inti -----------------------------------------------------------------
    def buat_ucapan(self, query: str, doc: Mapping[str, Any],
                    skor: Optional[float] = None, backend: Optional[str] = None) -> dict:
        bab = bersihkan_judul(doc.get("chapter_title", "")) or "materi ini"
        episode = bersihkan_judul(doc.get("episode_title", "")) or "bagian ini"
        konsep = (str(doc.get("concept") or "").strip().rstrip(".")) or "konsep dasarnya"

        yakin = skor is None or float(skor) >= 0.45
        kunci = f"{query}|{doc.get('episode_id', episode)}"

        # --- jalur LLM (opsional) ---
        mode = backend or self.backend
        if mode in ("auto", "qwen") and not self._qwen_gagal:
            if self._qwen is None:
                self._qwen = self._muat_qwen()
            if self._qwen is not None:
                try:
                    kandidat = rapikan_untuk_tts(
                        self._qwen.tulis(query, bab, episode, konsep), max_chars=330
                    )
                    if _layak_dipakai(kandidat):
                        return self._bungkus(kandidat, query, doc, skor, "qwen")
                except Exception:
                    pass  # apa pun yang gagal -> template

        # --- jalur template ---
        pembuka = self._pilih(_OPENER_PASTI if yakin else _OPENER_RAGU, kunci + "|buka")
        penghubung = self._pilih(_PENGHUBUNG, kunci + "|hubung").format(bab=bab, episode=episode)
        if not yakin:
            # jaga kerendahan hati tetap terbaca walau kalimat pembuka dipangkas
            penghubung = "Sepertinya " + _kecilkan_awal(penghubung)
        kalimat_konsep = self._pilih(_KONSEP, kunci + "|konsep").format(konsep=_kecilkan_awal(konsep))
        penutup = self._pilih(_PENUTUP if yakin else _PENUTUP_RAGU, kunci + "|tutup")

        ucapan = _susun(pembuka, penghubung, kalimat_konsep, penutup, bab=bab)

        return self._bungkus(rapikan_untuk_tts(ucapan), query, doc, skor, "template")

    @staticmethod
    def _bungkus(ucapan: str, query: str, doc: Mapping[str, Any],
                 skor: Optional[float], sumber: str) -> dict:
        return {
            "query": query,
            "speech": ucapan,
            "speech_esp32": ucapan,          # kompatibel dengan cell playground lama
            "sumber": sumber,                # "template" atau "qwen"
            "estimasi_detik": estimasi_durasi(ucapan),
            "top_chapter": doc.get("chapter_title"),
            "top_episode": doc.get("episode_title"),
            "top_concept": doc.get("concept"),
            "confidence_score": None if skor is None else float(skor),
        }


# --------------------------------------------------------------------------- #
# 5. CLI
# --------------------------------------------------------------------------- #

def _main() -> int:
    ap = argparse.ArgumentParser(description="Uji generator ucapan pemandu belajar.")
    ap.add_argument("query", nargs="*", help="pertanyaan pelajar")
    ap.add_argument("--backend", default="template", choices=["template", "qwen", "auto"])
    ap.add_argument("--download", action="store_true", help="unduh GGUF Qwen 0.5B Q4_K_M")
    ap.add_argument("--n", type=int, default=3, help="jumlah variasi yang ditampilkan")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    if args.download:
        unduh_model_gguf()
        return 0

    q = " ".join(args.query) or "what is meant by a loop?"
    doc = {
        "chapter_title": "Perulangan",
        "episode_title": "Episode 2: While dan For",
        "concept": "mengulang blok kode selama kondisi bernilai benar",
        "episode_id": "demo",
    }
    pemandu = PemanduUcapan(backend=args.backend, verbose=args.verbose)
    for i in range(args.n):
        hasil = pemandu.buat_ucapan(f"{q} #{i}" if args.n > 1 else q, doc, skor=0.72)
        print(f"[{hasil['sumber']} | ~{hasil['estimasi_detik']}s] {hasil['speech']}")
    return 0


if __name__ == "__main__":
    sys.exit(_main())
