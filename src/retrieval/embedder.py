"""
src/retrieval/embedder.py
--------------------------
Wraps a HuggingFace sentence-transformers model to produce code embeddings.
"""

from __future__ import annotations
from typing import List
import numpy as np
from sentence_transformers import SentenceTransformer

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CodeEmbedder:
    def __init__(self, model_name: str = "microsoft/unixcoder-base"):
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Return L2-normalised embeddings as a float32 numpy array."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        return embeddings.astype("float32")

