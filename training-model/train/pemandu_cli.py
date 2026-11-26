#!/usr/bin/env python3
"""
pemandu_cli.py — Pemandu belajar Sokratik (CLI).

Alur:
  1. Pertanyaan pelajar -> SBERT fine-tuned -> ambil passage paling relevan
  2. Passage + pertanyaan -> Gemma-3-1B (llama-server) -> kalimat Sokratik
  3. Teks dibersihkan untuk TTS (tanpa emoji/markdown) + dijaga strukturnya
  4. Ditampilkan bersama metrik naturalitas heuristik

Pemakaian:
    python pemandu_cli.py                          # mode interaktif
    python pemandu_cli.py "what is meant by a loop?"
    python pemandu_cli.py --uji                    # 5 pertanyaan uji + ringkasan
    python pemandu_cli.py --banding "apa itu list?"  # Gemma vs template

Opsi berguna:
    --url http://127.0.0.1:8081   alamat llama-server
    --topk 3                      jumlah passage yang dikirim ke model
    --suhu 0.7 --maks 150         sampling
    --tanpa-server                paksa pakai template saja
"""

from __future__ import annotations

import argparse
import json
import re
import zlib
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
import torch
from sentence_transformers import SentenceTransformer, util

from pemandu_ucapan import PemanduUcapan, bersihkan_judul, estimasi_durasi, rapikan_untuk_tts

BASE = Path(__file__).resolve().parent
ART = BASE / "output_artifacts"
if not ART.exists():
    ART = BASE / "train" / "output_artifacts"

MODEL_SBERT = ART / "finetuned_sbert"
FILE_META = ART / "corpus_metadata.json"
FILE_EMB = ART / "corpus_embeddings_finetuned.npy"

DEFAULT_URL = "http://127.0.0.1:8081"
DEFAULT_MODEL = "gemma-3-1b"

# --------------------------------------------------------------------------- #
# Tampilan terminal
# --------------------------------------------------------------------------- #
DIM = "\033[2m"
TEBAL = "\033[1m"
SIAN = "\033[36m"
HIJAU = "\033[32m"
KUNING = "\033[33m"
MERAH = "\033[31m"
RESET = "\033[0m"
GARIS = "─" * 78


# --------------------------------------------------------------------------- #
# 1. PROMPT
# --------------------------------------------------------------------------- #
SISTEM_DASAR = (
    "Kamu kakak pembimbing belajar Python untuk pelajar Indonesia. "
    "Gaya bicara hangat dan tidak menghakimi. "
    "Aturan wajib: "
    "jawab hanya dalam bahasa Indonesia; "
    "tulis dua sampai tiga kalimat pendek; "
    "jangan beri jawaban lengkap, beri pancingan supaya pelajar berpikir sendiri; "
    "akhiri dengan satu pertanyaan; "
    "tanpa emoji, tanpa markdown, tanpa daftar, tanpa kode; "
    "jangan pernah menyebut kata konteks, passage, peringkat, atau sistem."
)

# Tiga preset gaya — supaya kamu bisa membandingkan mana yang paling enak didengar.
GAYA = {
    "ketat": SISTEM_DASAR
    + " Gunakan bahasa Indonesia baku namun tetap hangat. "
      "Hindari kata gaul, kata asing, dan singkatan. "
      "Jangan mengarang perumpamaan; sebut langsung istilah dari materi.",
    "santai": SISTEM_DASAR
    + " Pakai bahasa sehari-hari yang akrab, boleh memakai kata kamu, "
      "tetapi jangan berlebihan sampai terdengar seperti teman nongkrong. "
      "Hindari kata asing seperti basically atau skipping.",
    "naratif": SISTEM_DASAR
    + " Boleh memakai satu perumpamaan singkat, tetapi perumpamaannya harus "
      "berhubungan dengan hal yang sudah dikenal pelajar pemula, bukan hal acak. "
      "Sesudah perumpamaan, sebut istilah teknis yang benar dari materi.",
}


def sistem_prompt(gaya: str) -> str:
    return GAYA.get(gaya, GAYA["ketat"])

CONTOH = (
    "Contoh gaya yang benar:\n"
    "Pertanyaan: apa itu variabel?\n"
    "Jawaban: Variabel itu seperti kotak berlabel yang menyimpan nilai. "
    "Coba bayangkan kamu punya dua kotak berisi angka dan teks, menurutmu Python "
    "membedakannya dari mana?\n\n"
    "Pertanyaan: kenapa kode saya error?\n"
    "Jawaban: Error itu petunjuk, bukan hukuman. "
    "Coba baca baris terakhir pesan errornya, bagian mana yang disebut di situ?\n"
)


def prompt_pengguna(query: str, doc: dict) -> str:
    bab = bersihkan_judul(doc.get("chapter_title", ""))
    episode = bersihkan_judul(doc.get("episode_title", ""))
    konsep = str(doc.get("concept") or "").strip().rstrip(".")
    inti = str(doc.get("passage_text") or "").strip()
    if len(inti) > 280:
        inti = inti[:280].rsplit(" ", 1)[0] + "."
    return (
        f"{CONTOH}\n"
        f"Sekarang jawab yang ini, jangan menyalin contoh di atas.\n"
        f"Pertanyaan pelajar: {query}\n"
        f"Materi terdekat: bab {bab}, bagian {episode}. Konsep: {konsep}.\n"
        f"Inti materi: {inti}\n"
        f"Jawaban:"
    )


# --------------------------------------------------------------------------- #
# 2. RETRIEVER (SBERT fine-tuned)
# --------------------------------------------------------------------------- #
class Materi:
    def __init__(self) -> None:
        for p in (MODEL_SBERT, FILE_META, FILE_EMB):
            if not p.exists():
                raise FileNotFoundError(f"Artefak tidak ditemukan: {p}")
        self.model = SentenceTransformer(str(MODEL_SBERT), device="cpu")
        self.df = pd.DataFrame(json.load(open(FILE_META, encoding="utf-8")))
        self.emb = torch.tensor(np.load(FILE_EMB))

    def cari(self, query: str, topk: int = 3) -> list[dict]:
        q = self.model.encode(query, convert_to_tensor=True)
        skor = util.cos_sim(q, self.emb)[0]
        top = torch.topk(skor, k=min(topk, len(self.df)))
        hasil = []
        for s, idx in zip(top.values, top.indices):
            d = self.df.iloc[int(idx)]
            hasil.append(
                {
                    "skor": round(float(s), 4),
                    "chapter_title": d["chapter_title"],
                    "episode_title": d["episode_title"],
                    "concept": d["concept"],
                    "passage_text": d["passage_text"],
                }
            )
        return hasil


# --------------------------------------------------------------------------- #
# 3. NARATOR (Gemma via llama-server)
# --------------------------------------------------------------------------- #
class Narator:
    def __init__(self, url: str = DEFAULT_URL, model: str = DEFAULT_MODEL, verbose: bool = True):
        self.url = url.rstrip("/")
        self.model = model
        self.verbose = verbose
        self.aktif = self._cek()

    def _cek(self) -> bool:
        try:
            r = requests.get(f"{self.url}/v1/models", timeout=2)
            return r.ok
        except Exception:
            return False

    def tulis(self, messages: list[dict], suhu: float, maks: int):
        """Generator: mengalirkan potongan teks sambil mencatat waktu & token."""
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": maks,
            "temperature": suhu,
            "top_p": 0.9,
            "stream": True,
        }
        self.mulai = time.time()
        self.ttft = None
        self.token = 0
        potongan: list[str] = []
        with requests.post(
            f"{self.url}/v1/chat/completions", json=body, stream=True, timeout=(10, 300)
        ) as r:
            r.raise_for_status()
            for line in r.iter_lines(decode_unicode=True):
                if not line or not line.startswith("data: "):
                    continue
                data = line[6:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = obj.get("choices", [{}])[0].get("delta", {})
                teks = delta.get("content")
                if teks:
                    if self.ttft is None:
                        self.ttft = time.time() - self.mulai
                    self.token += 1
                    potongan.append(teks)
                    yield teks
        self.total = time.time() - self.mulai
        self.teks = "".join(potongan).strip()


# --------------------------------------------------------------------------- #
# 4. PENJAGA TEKS (biar tetap ramah TTS & tetap Sokratik)
# --------------------------------------------------------------------------- #
_AJAKAN = ("coba", "bayangkan", "tebak", "menurutmu", "gimana", "bagaimana",
           "perhatikan", "pikirkan", "jelaskan", "tulis", "praktikkan")

_TANYA_CADANGAN = (
    "Menurutmu, bagian mana yang paling ingin kamu coba dulu?",
    "Coba tebak apa yang terjadi kalau bagian itu kamu ubah, berani?",
    "Sudah kebayang alurnya, atau masih ada yang mengganjal?",
    "Kalau kamu tulis versi kecilnya sendiri, langkah pertamanya apa?",
)

_GAUL = ("banget", "gimana", "kayak", "soalnya", "nggak", "gak ", "udah",
         "nih", "deh", "sih", "dong", "basically", "skipping", "restart",
         "ngelakuin", "nge-", "oke, siap", "siap!")


def deteksi_register(teks: str) -> list[str]:
    """Kata yang bikin kalimat terdengar gaul/asing untuk TTS pemandu belajar."""
    rendah = teks.lower()
    return [k.strip() for k in _GAUL if k in rendah]


def jaga_struktur(teks: str, penutup_cadangan: str = "") -> tuple[str, list[str]]:
    """Bersihkan untuk TTS, batasi 4 kalimat, pastikan ditutup pertanyaan."""
    catatan: list[str] = []
    # max_chars besar: jangan potong di sini, biar pertanyaan penutup model tidak hilang
    t = rapikan_untuk_tts(teks, max_chars=1500)
    # buang label yang kadang bocor dari model ("Jawaban:", "Pertanyaan:")
    t = re.sub(r"\b(Jawaban|Pertanyaan)\s*:", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    if re.search(r"pertanyaan pelajar|materi terdekat|inti materi|contoh gaya", t, re.I):
        catatan.append("model menyalin prompt")

    kalimat = [k.strip() for k in re.split(r"(?<=[.!?])\s+", t) if k.strip()]
    if len(kalimat) > 4:
        # pertahankan pertanyaan milik model kalau ada, buang kalimat penjelas paling akhir
        tanya = [k for k in kalimat if k.rstrip().endswith("?")]
        inti = [k for k in kalimat if not k.rstrip().endswith("?")]
        kalimat = (inti[:3] + [tanya[-1]]) if tanya else kalimat[:4]
        catatan.append("dipotong jadi 4 kalimat")

    t = " ".join(kalimat)
    if not t.rstrip().endswith("?"):
        cadangan = penutup_cadangan if penutup_cadangan.rstrip().endswith("?") else \
            _TANYA_CADANGAN[zlib.crc32(t.encode("utf-8")) % len(_TANYA_CADANGAN)]
        t = t.rstrip(" .") + ". " + cadangan
        catatan.append("pertanyaan penutup ditambahkan")

    t = t.strip()
    if t and t[0].islower():
        t = t[0].upper() + t[1:]
    return t, catatan


def skor_natural(teks: str) -> tuple[int, dict]:
    """Skor heuristik 0-100 — HANYA mengukur bentuk, bukan kebenaran isi."""
    kata = len(re.findall(r"\w+", teks))
    kalimat = len(re.findall(r"[.?!]", teks))
    akhir_tanya = teks.rstrip().endswith("?")
    ada_ajakan = any(k in teks.lower() for k in _AJAKAN)
    jumlah_tanya = teks.count("?")
    gaul = deteksi_register(teks)

    rincian = {
        "kata": kata,
        "kalimat": kalimat,
        "akhir_tanya": akhir_tanya,
        "ada_ajakan": ada_ajakan,
        "jumlah_tanya": jumlah_tanya,
        "gaul": gaul,
    }
    skor = 0
    skor += 40 if akhir_tanya else 0
    skor += 20 if 2 <= kalimat <= 4 else 0
    skor += 15 if 18 <= kata <= 70 else 0
    skor += 15 if ada_ajakan else 0
    skor += 10 if jumlah_tanya == 1 else 0
    skor -= 10 if len(gaul) >= 3 else 0
    return max(0, skor), rincian


# --------------------------------------------------------------------------- #
# 5. SATU PUTARAN
# --------------------------------------------------------------------------- #
def satu_putaran(
    query: str,
    materi: Materi,
    narator: Narator,
    pemandu: PemanduUcapan,
    topk: int,
    suhu: float,
    maks: int,
    banding: bool,
    tampil_materi: bool,
    gaya: str = "ketat",
) -> dict:
    hasil_materi = materi.cari(query, topk=topk)
    teratas = hasil_materi[0]
    penutup = pemandu.buat_ucapan(query, teratas, skor=teratas["skor"])["speech"]

    # server mungkin baru dinyalakan setelah CLI berjalan
    if not narator.aktif:
        narator.aktif = narator._cek()

    print(f"\n{GARIS}")
    print(f"{TEBAL}PERTANYAAN:{RESET} {query}")
    print(GARIS)
    print(f"{DIM}Materi terpilih:{RESET}")
    for i, d in enumerate(hasil_materi, 1):
        print(
            f"  {i}. {d['skor']:.3f}  {bersihkan_judul(d['chapter_title'])}"
            f" {DIM}›{RESET} {bersihkan_judul(d['episode_title'])}"
        )
        if tampil_materi:
            print(f"     {DIM}{d['concept']}{RESET}")
            print(f"     {DIM}\"{d['passage_text'][:110]}...\"{RESET}")

    if teratas["skor"] < 0.60:
        print(
            f"{KUNING}[peringatan]{RESET} skor kemiripan teratas cuma "
            f"{teratas['skor']:.2f} — materi mungkin kurang cocok, jawaban bisa melenceng."
        )

    mentah = ""
    detik = 0.0
    ttft = None
    if narator.aktif:
        print(f"\n{SIAN}[Gemma-3-1B · gaya {gaya}]{RESET} menulis:\n")
        try:
            for potong in narator.tulis(
                [
                    {"role": "system", "content": sistem_prompt(gaya)},
                    {"role": "user", "content": prompt_pengguna(query, teratas)},
                ],
                suhu=suhu,
                maks=maks,
            ):
                mentah += potong
                print(potong, end="", flush=True)
            print()
            detik = getattr(narator, "total", 0.0)
            ttft = getattr(narator, "ttft", None)
        except Exception as exc:
            print(f"\n{MERAH}[gagal]{RESET} {type(exc).__name__}: {exc}")
            narator.aktif = False
    else:
        print(f"{KUNING}[server tidak aktif]{RESET} memakai template saja.")

    if not mentah.strip():
        bersih, catatan = penutup, ["dari template"]
        sumber = "template"
    else:
        bersih, catatan = jaga_struktur(mentah)
        sumber = "gemma"

    skor, rincian = skor_natural(bersih)

    print(f"\n{TEBAL}Kalimat siap TTS{RESET} {DIM}({sumber}){RESET}:")
    print(f'  "{bersih}"')
    if catatan:
        print(f"  {DIM}catatan: {', '.join(catatan)}{RESET}")
    if rincian["gaul"]:
        print(f"  {KUNING}register gaul/asing: {', '.join(rincian['gaul'])}{RESET}")

    kecepatan = (narator.token / detik) if detik and sumber == "gemma" else 0
    print(
        f"\n  {DIM}{rincian['kata']} kata · {rincian['kalimat']} kalimat · "
        f"akhiri-tanya {'✓' if rincian['akhir_tanya'] else '✗'} · "
        f"ajakan {'✓' if rincian['ada_ajakan'] else '✗'} · "
        f"{detik:.1f} dtk · {kecepatan:.1f} tok/s · "
        f"audio ~{estimasi_durasi(bersih)} dtk{RESET}"
    )
    warna = HIJAU if skor >= 80 else (KUNING if skor >= 50 else MERAH)
    print(f"  {warna}{TEBAL}skor naturalitas: {skor}/100{RESET}")
    print(f"  {DIM}(skor ini hanya mengukur bentuk kalimat, bukan kebenaran isi — "
          f"baca sendiri hasilnya){RESET}")

    if banding:
        print(f"\n{TEBAL}Versi template{RESET} {DIM}(pembanding){RESET}:")
        print(f'  "{penutup}"')
        s2, r2 = skor_natural(penutup)
        print(f"  {DIM}{r2['kata']} kata · {r2['kalimat']} kalimat · skor {s2}/100{RESET}")

    return {
        "waktu": datetime.now().isoformat(timespec="seconds"),
        "query": query,
        "gaya": gaya,
        "materi": hasil_materi,
        "gemma_mentah": mentah,
        "speech": bersih,
        "sumber": sumber,
        "catatan": catatan,
        "skor": skor,
        "rincian": rincian,
        "detik": round(detik, 2),
        "ttft": round(ttft, 2) if ttft else None,
        "template": penutup,
        "skor_template": skor_natural(penutup)[0],
    }


# --------------------------------------------------------------------------- #
# 6. CLI
# --------------------------------------------------------------------------- #
UJI = [
    "what is meant by a loop?",
    "bedanya list dan tuple apa?",
    "cara menghitung sisa bagi modulo",
    "kenapa kode saya error index out of range",
    "gimana cara bikin fungsi dengan parameter",
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Pemandu belajar Sokratik (SBERT + Gemma).")
    ap.add_argument("query", nargs="*", help="pertanyaan; kosong = mode interaktif")
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--topk", type=int, default=3)
    ap.add_argument("--suhu", type=float, default=0.7)
    ap.add_argument("--maks", type=int, default=150)
    ap.add_argument("--banding", action="store_true", help="tampilkan versi template")
    ap.add_argument("--gaya", default="ketat", choices=list(GAYA),
                    help="preset gaya bahasa (default: ketat)")
    ap.add_argument("--materi", action="store_true", help="tampilkan konsep tiap passage")
    ap.add_argument("--tanpa-server", action="store_true", help="paksa mode template")
    ap.add_argument("--uji", action="store_true", help="jalankan 5 pertanyaan uji + ringkasan")
    ap.add_argument("--simpan", metavar="FILE", help="simpan hasil ke JSONL")
    args = ap.parse_args()

    print(f"{TEBAL}Memuat SBERT fine-tuned...{RESET}")
    t0 = time.time()
    materi = Materi()
    pemandu = PemanduUcapan(backend="template")
    print(f"{DIM}siap dalam {time.time()-t0:.1f} dtk · {len(materi.df)} passage{RESET}")

    narator = Narator(args.url, args.model)
    if args.tanpa_server:
        narator.aktif = False
    if narator.aktif:
        print(f"{HIJAU}[server]{RESET} {args.url} — model {args.model}")
    else:
        print(f"{KUNING}[server tidak aktif]{RESET} {args.url} — jalan dengan template")

    def proses(q: str) -> dict:
        return satu_putaran(
            q, materi, narator, pemandu, args.topk, args.suhu,
            args.maks, args.banding, args.materi, args.gaya,
        )

    rekaman: list[dict] = []

    if args.uji:
        print(f"\n{TEBAL}MODE UJI — {len(UJI)} pertanyaan{RESET}")
        for q in UJI:
            rekaman.append(proses(q))
        if rekaman:
            rata = sum(r["skor"] for r in rekaman) / len(rekaman)
            rata_t = sum(r["skor_template"] for r in rekaman) / len(rekaman)
            total_dtk = sum(r["detik"] for r in rekaman)
            print(f"\n{GARIS}\n{TEBAL}RINGKASAN{RESET}")
            print(f"  skor Gemma    : {rata:.1f}/100")
            print(f"  skor template : {rata_t:.1f}/100")
            print(f"  total waktu   : {total_dtk:.1f} dtk ({total_dtk/len(rekaman):.1f} dtk/pertanyaan)")
            patuh = sum(1 for r in rekaman if r["rincian"]["akhir_tanya"])
            print(f"  akhiri tanya  : {patuh}/{len(rekaman)}")
            print(f"  menyalin prompt: {sum(1 for r in rekaman if 'model menyalin prompt' in r['catatan'])}/{len(rekaman)}")
    elif args.query:
        rekaman.append(proses(" ".join(args.query)))
    else:
        print(f"\n{DIM}Ketik pertanyaan. Perintah: /g gaya · /m materi · /b banding · "
              f"/s simpan · /k keluar{RESET}")
        print(f"{DIM}gaya aktif: {args.gaya} (ketat / santai / naratif){RESET}")
        while True:
            try:
                q = input(f"\n{TEBAL}>{RESET} ").strip()
            except (KeyboardInterrupt, EOFError):
                break
            if not q:
                continue
            if q.lower() in ("/k", "/keluar", "exit", "quit"):
                break
            if q == "/g":
                daftar = list(GAYA)
                args.gaya = daftar[(daftar.index(args.gaya) + 1) % len(daftar)]
                print(f"  gaya sekarang: {args.gaya}")
                continue
            if q == "/m":
                args.materi = not args.materi
                print(f"  tampil materi: {'ya' if args.materi else 'tidak'}")
                continue
            if q == "/b":
                args.banding = not args.banding
                print(f"  banding template: {'ya' if args.banding else 'tidak'}")
                continue
            if q == "/s":
                if not rekaman:
                    print("  belum ada hasil")
                    continue
                tujuan = args.simpan or str(
                    ART / f"uji_naturalitas_{datetime.now():%Y%m%d_%H%M%S}.jsonl"
                )
                with open(tujuan, "w", encoding="utf-8") as f:
                    for r in rekaman:
                        f.write(json.dumps(r, ensure_ascii=False) + "\n")
                print(f"  tersimpan: {tujuan}")
                continue
            rekaman.append(proses(q))

    if args.simpan and rekaman:
        with open(args.simpan, "w", encoding="utf-8") as f:
            for r in rekaman:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\n{DIM}tersimpan: {args.simpan}{RESET}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
