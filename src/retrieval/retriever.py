"""
src/retrieval/retriever.py
---------------------------
High-level retriever: embed a query → search vector store → return context string.
"""

from __future__ import annotations
from typing import List

from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore, RetrievedChunk
from src.utils.logger import get_logger

logger = get_logger(__name__)


class Retriever:
    def __init__(self, embedder: CodeEmbedder, store: FAISSVectorStore, top_k: int = 5):
        self.embedder = embedder
        self.store = store
        self.top_k = top_k

    def retrieve(self, query: str) -> List[RetrievedChunk]:
        embedding = self.embedder.embed([query])[0]
        return self.store.search(embedding, top_k=self.top_k)

    def build_context_string(self, query: str) -> str:
        """Return a formatted context block ready to inject into a prompt."""
        chunks = self.retrieve(query)
        parts = []
        for chunk in chunks:
            parts.append(f"# File: {chunk.file_path}\n{chunk.content}")
        return "\n\n".join(parts)

