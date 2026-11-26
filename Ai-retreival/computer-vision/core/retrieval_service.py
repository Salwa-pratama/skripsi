"""Retrieval Service - Fine-Tuned Sentence-Transformer.

Memuat artefak hasil `chatbot_finetuned.ipynb`:
    model/output_artifacts/finetuned_sbert/
    model/output_artifacts/corpus_metadata.json
    model/output_artifacts/corpus_embeddings_finetuned.npy

Model ini bersifat *retrieval* (bukan generator): pertanyaan user diubah
menjadi vektor, lalu dicari passage materi paling mirip dengan cosine
similarity. Jawaban disusun dari chapter/episode/concept/passage teratas.
"""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

from config import Config


class RetrievalService:
    def __init__(self) -> None:
        self.model = None
        self.records: List[Dict[str, Any]] = []
        self.embeddings = None
        self._lock = threading.Lock()
        self._loaded = False
        self._load_error: Optional[str] = None

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------
    def _validate_paths(self) -> None:
        missing = [
            str(p)
            for p in (
                Config.FINETUNED_MODEL_DIR,
                Config.CORPUS_METADATA_FILE,
                Config.CORPUS_EMBEDDINGS_FILE,
            )
            if not Path(p).exists()
        ]
        if missing:
            raise FileNotFoundError(
                "Artefak model fine-tuned tidak lengkap. File/folder berikut tidak ditemukan:\n- "
                + "\n- ".join(missing)
            )

    def load(self) -> None:
        """Muat model, metadata, dan embedding sekali saja (thread-safe)."""
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            try:
                # Import di dalam method agar pesan error dependency lebih jelas
                # dan server tetap bisa menampilkan /docs saat model belum siap.
                import torch
                from sentence_transformers import SentenceTransformer

                self._validate_paths()
                print(f"[SBERT] Memuat model fine-tuned: {Config.FINETUNED_MODEL_DIR}", flush=True)
                self.model = SentenceTransformer(
                    str(Config.FINETUNED_MODEL_DIR), device="cpu"
                )

                print(
                    f"[SBERT] Memuat metadata korpus: {Config.CORPUS_METADATA_FILE.name}",
                    flush=True,
                )
                with open(Config.CORPUS_METADATA_FILE, "r", encoding="utf-8") as f:
                    self.records = json.load(f)

                print(
                    f"[SBERT] Memuat embedding: {Config.CORPUS_EMBEDDINGS_FILE.name}",
                    flush=True,
                )
                self.embeddings = torch.tensor(
                    np.load(Config.CORPUS_EMBEDDINGS_FILE), dtype=torch.float32
                )

                if len(self.records) != int(self.embeddings.shape[0]):
                    raise ValueError(
                        "Jumlah metadata ("
                        f"{len(self.records)}) tidak sama dengan jumlah embedding "
                        f"({self.embeddings.shape[0]})."
                    )

                self._loaded = True
                self._load_error = None
                print(
                    f"[SBERT] SIAP: {len(self.records)} passage materi | "
                    f"dimensi {tuple(self.embeddings.shape)}",
                    flush=True,
                )
            except Exception as exc:  # noqa: BLE001
                self._load_error = str(exc)
                print(f"[SBERT ERROR] Gagal memuat model: {exc}", flush=True)
                raise

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    # ------------------------------------------------------------------
    # Search & answer composition
    # ------------------------------------------------------------------
    def search(self, query: str, top_k: Optional[int] = None) -> Dict[str, Any]:
        """Cari passage paling relevan untuk query user."""
        self._ensure_loaded()
        assert self.model is not None and self.embeddings is not None

        import torch
        from sentence_transformers import util

        top_k = top_k or Config.RETRIEVAL_TOP_K
        top_k = max(1, min(top_k, len(self.records)))

        query = (query or "").strip()
        if not query:
            raise ValueError("Pertanyaan tidak boleh kosong.")

        query_embedding = self.model.encode(query, convert_to_tensor=True)
        cosine_scores = util.cos_sim(query_embedding, self.embeddings)[0]
        top_results = torch.topk(cosine_scores, k=top_k)

        results: List[Dict[str, Any]] = []
        for score, index in zip(top_results.values, top_results.indices):
            record = dict(self.records[int(index)])
            record["confidence"] = float(score)
            results.append(record)

        return {
            "query": query,
            "top": results[0],
            "results": results,
        }

    @staticmethod
    def _shorten(text: str, max_chars: int) -> str:
        text = " ".join((text or "").split())
        if len(text) <= max_chars:
            return text
        cut = text[:max_chars]
        last_space = cut.rfind(" ")
        if last_space > max_chars * 0.6:
            cut = cut[:last_space]
        return cut.rstrip(" ,;:-") + "."

    def compose_answer(self, top: Dict[str, Any]) -> Dict[str, Any]:
        """Susun jawaban suara + teks OLED dari passage teratas."""
        chapter = top.get("chapter_title", "materi Python")
        episode = top.get("episode_title", "")
        concept = top.get("concept", "")
        passage = self._shorten(top.get("passage_text", ""), 160)

        sentence_parts = [
            f"Pertanyaanmu berkaitan dengan {chapter}",
        ]
        if episode:
            sentence_parts.append(f"khususnya pada {episode}")
        answer = ", ".join(sentence_parts) + ". "
        if concept:
            answer += f"Konsep kuncinya: {concept}. "
        if passage:
            answer += f"Contoh dari materi: {passage} "
        answer += "Coba praktikkan kembali di editor kode ya."

        display_text = self._shorten(
            f"{chapter}. {episode}. Konsep: {concept}." if episode else
            f"{chapter}. Konsep: {concept}.",
            220,
        )
        return {
            "answer": answer.strip(),
            "display_text": display_text,
        }

    def answer(self, query: str) -> Dict[str, Any]:
        """Endpoint-level helper: retrieval + threshold + komposisi jawaban."""
        search_result = self.search(query)
        top = search_result["top"]
        confidence = float(top.get("confidence", 0.0))

        matched = confidence >= Config.RETRIEVAL_MIN_SCORE
        if matched:
            composed = self.compose_answer(top)
            answer = composed["answer"]
            display_text = composed["display_text"]
            emotion = "speaking"
        else:
            answer = (
                "Maaf, pertanyaanmu belum ada di materi kurikulum yang aku pelajari. "
                "Coba tanyakan topik Python lain, seperti variabel, percabangan, "
                "perulangan, fungsi, list, atau dictionary ya."
            )
            display_text = "Materi belum ada di kurikulum. Coba topik Python lain ya."
            emotion = "confused"

        return {
            "query": query,
            "matched": matched,
            "confidence": round(confidence, 4),
            "answer": answer,
            "display_text": display_text,
            "emotion": emotion,
            "chapter": top.get("chapter_title"),
            "chapter_slug": top.get("chapter_slug"),
            "episode": top.get("episode_title"),
            "episode_id": top.get("episode_id"),
            "concept": top.get("concept"),
            "passage": top.get("passage_text"),
            "alternatives": [
                {
                    "chapter": item.get("chapter_title"),
                    "episode": item.get("episode_title"),
                    "confidence": round(float(item.get("confidence", 0.0)), 4),
                }
                for item in search_result["results"][1:]
            ],
        }


# Singleton
retrieval_service = RetrievalService()
