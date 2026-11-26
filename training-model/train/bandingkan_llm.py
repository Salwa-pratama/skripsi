#!/usr/bin/env python3
"""
bandingkan_llm.py — Bandingkan kualitas narasi beberapa LLM lokal
untuk pipeline SBERT (top-3 passage) -> SLM -> teks TTS.

Tahap 1 (sekali):
    python bandingkan_llm.py siapkan

Tahap 2 (per model, server harus sudah jalan di port tertentu):
    python bandingkan_llm.py jalankan --port 8080 --model qwen-0.5b --out hasil_qwen05.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import requests

from pemandu_ucapan import bersihkan_judul, estimasi_durasi, rapikan_untuk_tts

BASE = Path(__file__).resolve().parent
ART = BASE / "output_artifacts"
TMP = Path("/tmp/opencode")
KONTEKS = TMP / "uji_konteks.json"

QUERIES = [
    "what is meant by a loop?",
    "bedanya list dan tuple apa?",
    "cara menghitung sisa bagi modulo",
    "kenapa kode saya error index out of range",
]

SISTEM = (
    "Kamu kakak pembimbing belajar Python untuk pelajar Indonesia. "
    "Jawab hanya dalam bahasa Indonesia. "
    "Tulis dua sampai tiga kalimat pendek yang enak didengar saat dibacakan mesin suara. "
    "Tanpa emoji, tanpa markdown, tanpa daftar, tanpa tanda kurung, tanpa kode. "
    "Akhiri dengan satu pertanyaan atau ajakan singkat supaya pelajar mencoba sendiri. "
    "Jangan pernah menyebut kata konteks, passage, atau peringkat."
)


def prompt_user(query: str, docs: list[dict]) -> str:
    baris = []
    for i, d in enumerate(docs, 1):
        baris.append(
            f"{i}. Bab {bersihkan_judul(d['chapter_title'])} | "
            f"Bagian {bersihkan_judul(d['episode_title'])} | "
            f"Konsep: {d['concept']}"
        )
    materi = "\n".join(baris)
    return (
        f"Pertanyaan pelajar: {query}\n\n"
        f"Materi yang paling relevan:\n{materi}\n\n"
        "Tulis respons lisannya sekarang."
    )


# --------------------------------------------------------------------------- #
def siapkan() -> None:
    import numpy as np
    import pandas as pd
    import torch
    from sentence_transformers import SentenceTransformer, util

    TMP.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(str(ART / "finetuned_sbert"), device="cpu")
    df = pd.DataFrame(json.load(open(ART / "corpus_metadata.json")))
    emb = torch.tensor(np.load(ART / "corpus_embeddings_finetuned.npy"))

    hasil = []
    for q in QUERIES:
        qe = model.encode(q, convert_to_tensor=True)
        skor = util.cos_sim(qe, emb)[0]
        top = torch.topk(skor, k=3)
        docs = []
        for s, idx in zip(top.values, top.indices):
            d = df.iloc[int(idx)]
            docs.append(
                {
                    "skor": round(float(s), 4),
                    "chapter_title": d["chapter_title"],
                    "episode_title": d["episode_title"],
                    "concept": d["concept"],
                    "passage_text": d["passage_text"],
                }
            )
        hasil.append({"query": q, "docs": docs})

    json.dump(hasil, open(KONTEKS, "w"), ensure_ascii=False, indent=2)
    print(f"[OK] {len(hasil)} pertanyaan x 3 passage -> {KONTEKS}")


# --------------------------------------------------------------------------- #
def jalankan(port: int, model: str, out: str, suhu: float, maks: int) -> None:
    konteks = json.load(open(KONTEKS))
    url = f"http://127.0.0.1:{port}/v1/chat/completions"
    hasil = []

    for item in konteks:
        q = item["query"]
        body = {
            "messages": [
                {"role": "system", "content": SISTEM},
                {"role": "user", "content": prompt_user(q, item["docs"])},
            ],
            "max_tokens": maks,
            "temperature": suhu,
            "top_p": 0.9,
        }
        t0 = time.time()
        r = requests.post(url, json=body, timeout=180)
        r.raise_for_status()
        data = r.json()
        mentah = data["choices"][0]["message"]["content"]
        detik = time.time() - t0
        bersih = rapikan_untuk_tts(mentah)

        hasil.append(
            {
                "query": q,
                "mentah": mentah,
                "speech": bersih,
                "kata": len(re.findall(r"\w+", bersih)),
                "kalimat": len(re.findall(r"[.?!]", bersih)),
                "diakhiri_tanya": bersih.rstrip().endswith("?"),
                "detik_generate": round(detik, 1),
                "estimasi_audio": estimasi_durasi(bersih),
                "tokens": data.get("usage", {}).get("completion_tokens"),
            }
        )
        print(f"  [{q[:40]}] {detik:.1f}s -> {bersih[:80]}...")

    Path(out).write_text(json.dumps(hasil, ensure_ascii=False, indent=2))
    print(f"[OK] {len(hasil)} jawaban -> {out}")


# --------------------------------------------------------------------------- #
def bandingkan(files: list[str]) -> None:
    semua = [(f, json.loads(Path(f).read_text())) for f in files]
    for i, item in enumerate(semua[0][1]):
        print("\n" + "=" * 78)
        print(f'PERTANYAAN: "{item["query"]}"')
        print("=" * 78)
        for nama, data in semua:
            d = data[i]
            tanda = "✓" if d["diakhiri_tanya"] else "✗"
            print(f"\n[{nama}]  {d['kata']} kata | {d['kalimat']} kalimat | "
                  f"akhiri-tanya {tanda} | {d['detik_generate']}s | audio ~{d['estimasi_audio']}s")
            print(f'  "{d["speech"]}"')
    print()


# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("siapkan")

    j = sub.add_parser("jalankan")
    j.add_argument("--port", type=int, default=8080)
    j.add_argument("--model", required=True)
    j.add_argument("--out", required=True)
    j.add_argument("--suhu", type=float, default=0.7)
    j.add_argument("--maks", type=int, default=120)

    b = sub.add_parser("bandingkan")
    b.add_argument("files", nargs="+")

    a = ap.parse_args()
    if a.cmd == "siapkan":
        siapkan()
    elif a.cmd == "jalankan":
        jalankan(a.port, a.model, a.out, a.suhu, a.maks)
    else:
        bandingkan(a.files)
