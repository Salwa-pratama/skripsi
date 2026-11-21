#!/usr/bin/env python3
"""
Script Inferensi Mandiri (Standalone) Chatbot Pemandu Belajar Sokrates (PyJourney).
Memuat langsung model Sentence-Transformers yang telah di-fine-tune dari folder output_artifacts/
tanpa perlu melatih ulang model atau memproses dataset dari awal.

Cara Penggunaan:
1. Mode Langsung (Satu Pertanyaan):
   python uji_chatbot.py "Cara menghitung sisa bagi modulo operatornya apa ya bro?"

2. Mode Interaktif (Tanya Jawab Berkelanjutan):
   python uji_chatbot.py
"""

import sys
import json
import torch
import numpy as np
import pandas as pd
from pathlib import Path
from sentence_transformers import SentenceTransformer, util

# Direktori Artefak
CURRENT_DIR = Path(__file__).resolve().parent
ARTIFACTS_DIR = CURRENT_DIR / "output_artifacts"
FINETUNED_MODEL_DIR = ARTIFACTS_DIR / "finetuned_sbert"
METADATA_FILE = ARTIFACTS_DIR / "corpus_metadata.json"
EMBEDDINGS_FILE = ARTIFACTS_DIR / "corpus_embeddings_finetuned.npy"

# Validasi keberadaan file artefak
for p in [FINETUNED_MODEL_DIR, METADATA_FILE, EMBEDDINGS_FILE]:
    if not p.exists():
        print(f"[ERROR] File artefak tidak ditemukan: {p}")
        print("Pastikan notebook chatbot_finetuned.ipynb telah dijalankan untuk mengekspor model.")
        sys.exit(1)

print("=" * 70)
print("🤖 MEMUAT MODEL CHATBOT SOKRATIK (FINE-TUNED SBERT)...")
print("=" * 70)

# 1. Load model fine-tuned dari disk
model = SentenceTransformer(str(FINETUNED_MODEL_DIR), device="cpu")

# 2. Load metadata korpus materi
with open(METADATA_FILE, "r", encoding="utf-8") as f:
    corpus_metadata = json.load(f)
df_corpus = pd.DataFrame(corpus_metadata)

# 3. Load matriks embedding materi yang sudah terenkripsi
corpus_embeddings = torch.tensor(np.load(EMBEDDINGS_FILE))

print(f"[BERHASIL] Model tersimpan ({corpus_embeddings.shape[0]} passages) siap digunakan!")
print("=" * 70)

def tanya_chatbot(query: str, top_k: int = 3):
    if not query.strip():
        return
        
    q_emb = model.encode(query, convert_to_tensor=True)
    cos_scores = util.cos_sim(q_emb, corpus_embeddings)[0]
    top_results = torch.topk(cos_scores, k=min(top_k, len(df_corpus)))
    
    print("\n" + "=" * 70)
    print(f"🔍 PERTANYAAN: \"{query}\"")
    print("=" * 70)
    
    top_doc = None
    for idx, (score, doc_idx) in enumerate(zip(top_results.values, top_results.indices)):
        doc = df_corpus.iloc[int(doc_idx)]
        if idx == 0:
            top_doc = doc
        print(f"Peringkat #{idx+1} [Confidence Score: {float(score):.4f} / {float(score)*100:.1f}%]")
        print(f"  • Bab     : {doc['chapter_title']} ({doc['chapter_slug']})")
        print(f"  • Episode : {doc['episode_title']}")
        print(f"  • Konsep  : {doc['concept']}")
        print(f"  • Cuplikan: \"{doc['passage_text'][:120]}...\"")
        print("-" * 70)
        
    # Format narasi Sokratik untuk ESP32 Audio TTS
    speech = (
        f"Halo pembelajar! Pertanyaanmu berkaitan dengan {top_doc['chapter_title']}, "
        f"khususnya pada {top_doc['episode_title']}. "
        f"Ingat kembali konsep: {top_doc['concept']}. "
        f"Cobalah bereksperimen di editor kode tanpa melihat contekan!"
    )
    print("🔊 RESPONS SUARA SOKRATIK (UNTUK ESP32 TTS):")
    print(f"\"{speech}\"")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    # Jika ada argumen CLI (misal: python uji_chatbot.py "pertanyaan...")
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
        tanya_chatbot(user_query)
    else:
        # Mode loop interaktif di terminal
        print("\n💡 Masuk ke Mode Interaktif (Ketik 'keluar' atau 'exit' untuk selesai):")
        while True:
            try:
                q = input("Ketik pertanyaan siswa > ").strip()
                if q.lower() in ["exit", "keluar", "quit", "q"]:
                    print("Sampai jumpa!")
                    break
                if q:
                    tanya_chatbot(q)
            except (KeyboardInterrupt, EOFError):
                print("\nKeluar dari program.")
                break
