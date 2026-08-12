"""
src/retrieval/vector_store.py
------------------------------
FAISS-backed vector store for code chunk retrieval.
Swap `backend="chromadb"` for the ChromaDB path (stub included).
"""

from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple
import numpy as np
import faiss
import pickle

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RetrievedChunk:
    content: str
    file_path: str
    score: float
    metadata: dict


class FAISSVectorStore:
    def __init__(self, dim: int):
        self.dim = dim
        self.index = faiss.IndexFlatIP(dim)   # inner-product = cosine on normalised vecs
        self._chunks: list = []               # parallel list of CodeChunk objects

    # ── Build / Persist ──────────────────────────────────────────────────────

    def add(self, embeddings: np.ndarray, chunks: list) -> None:
        assert embeddings.shape[0] == len(chunks)
        self.index.add(embeddings)
        self._chunks.extend(chunks)
        logger.info(f"Vector store now contains {self.index.ntotal} vectors.")

    def save(self, path: str) -> None:
        p = Path(path)
        p.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(p / "index.faiss"))
        with open(p / "chunks.pkl", "wb") as f:
            pickle.dump(self._chunks, f)
        logger.info(f"Vector store saved to {path}")

    @classmethod
    def load(cls, path: str) -> "FAISSVectorStore":
        p = Path(path)
        index = faiss.read_index(str(p / "index.faiss"))
        with open(p / "chunks.pkl", "rb") as f:
            chunks = pickle.load(f)
        store = cls(dim=index.d)
        store.index = index
        store._chunks = chunks
        logger.info(f"Vector store loaded from {path} ({index.ntotal} vectors)")
        return store

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[RetrievedChunk]:
        if query_embedding.ndim == 1:
            query_embedding = query_embedding[np.newaxis, :]
        scores, indices = self.index.search(query_embedding, top_k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                continue
            chunk = self._chunks[idx]
            results.append(
                RetrievedChunk(
                    content=chunk.content,
                    file_path=chunk.file_path,
                    score=float(score),
                    metadata=chunk.metadata,
                )
            )
        return results

