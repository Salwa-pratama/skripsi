# ==============================================================================
# 🧪 PLAYGROUND INTERAKTIF v2 — narasi lisan yang luwes (siap tempel ke notebook)
# ==============================================================================
# Cara pakai: ganti isi cell lama dengan isi file ini, lalu jalankan.
# Butuh file pemandu_ucapan.py di folder yang sama (atau di sys.path).
import os
import json
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

from pemandu_ucapan import PemanduUcapan

# "template" = instan & 0 MB (default) | "qwen" = Qwen2.5-0.5B GGUF | "auto"
MODE_UCAPAN = os.environ.get("PEMANDU_BACKEND", "template")

ARTIFACTS_DIR = Path.cwd() / "output_artifacts"
if not ARTIFACTS_DIR.exists():
    ARTIFACTS_DIR = Path.cwd() / "train" / "output_artifacts"

FINETUNED_MODEL_DIR = ARTIFACTS_DIR / "finetuned_sbert"
METADATA_FILE = ARTIFACTS_DIR / "corpus_metadata.json"
EMBEDDINGS_FILE = ARTIFACTS_DIR / "corpus_embeddings_finetuned.npy"

# 1. LOAD MODEL TERSIMPAN (hanya 1x per sesi notebook)
if "model_inferensi" not in globals():
    print("[AUTO-LOAD] Memuat model fine-tuned dari output_artifacts/ ...")
    model_inferensi = SentenceTransformer(str(FINETUNED_MODEL_DIR), device="cpu")
    with open(METADATA_FILE, "r", encoding="utf-8") as f:
        df_corpus_inferensi = pd.DataFrame(json.load(f))
    corpus_embeddings_inferensi = torch.tensor(np.load(EMBEDDINGS_FILE))
    pemandu = PemanduUcapan(backend=MODE_UCAPAN)
    print(f"[AUTO-LOAD] {len(df_corpus_inferensi)} korpus siap. Mode ucapan: {MODE_UCAPAN}\n")


# 2. FUNGSI INFERENSI
def uji_pertanyaan_baru(query_teks: str, top_k: int = 3) -> dict:
    q_emb = model_inferensi.encode(query_teks, convert_to_tensor=True)
    cos_scores = util.cos_sim(q_emb, corpus_embeddings_inferensi)[0]
    top_results = torch.topk(cos_scores, k=min(top_k, len(df_corpus_inferensi)))

    print("=" * 72)
    print(f'INPUT PERTANYAAN BARU: "{query_teks}"')
    print("=" * 72)

    top_doc, skor_teratas = None, 0.0
    for idx, (score, doc_idx) in enumerate(zip(top_results.values, top_results.indices)):
        doc = df_corpus_inferensi.iloc[int(doc_idx)]
        if idx == 0:
            top_doc, skor_teratas = doc, float(score)
        print(f"Peringkat #{idx+1} [Confidence: {float(score):.4f} / {float(score)*100:.1f}%]")
        print(f"  • Bab     : {doc['chapter_title']} ({doc['chapter_slug']})")
        print(f"  • Episode : {doc['episode_title']}")
        print(f"  • Konsep  : {doc['concept']}")
        print(f"  • Cuplikan: \"{doc['passage_text'][:120]}...\"")
        print("-" * 72)

    # 3. NARASI LISAN: dirakit pemandu (template instan, atau Qwen kalau diaktifkan)
    hasil = pemandu.buat_ucapan(query_teks, top_doc, skor=skor_teratas)
    print(f"🔊 RESPONS SUARA SOKRATIK ({hasil['sumber']}, ~{hasil['estimasi_detik']} detik):")
    print(f'"{hasil["speech"]}"')
    print("=" * 72 + "\n")

    return {
        "query": query_teks,
        "top_chapter": top_doc["chapter_title"],
        "top_episode": top_doc["episode_title"],
        "speech_esp32": hasil["speech"],      # <- kirim ini saja ke ESP32
        "confidence_score": skor_teratas,
        "estimasi_detik": hasil["estimasi_detik"],
    }


# ==============================================================================
# 4. KETIK PERTANYAAN DI BAWAH INI
# ==============================================================================
hasil_uji = uji_pertanyaan_baru("what is meant by a loop?", top_k=3)
