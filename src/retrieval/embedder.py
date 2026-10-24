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
        # RoBERTa-style position ids start at pad_token_id + 1, so a model with N
        # position embeddings accepts at most N - 2 tokens (UniXcoder reports 1026).
        pad_id = self.model[0].auto_model.config.pad_token_id or 0
        limit = self.model[0].auto_model.config.max_position_embeddings - pad_id - 1
        self.model.max_seq_length = min(self.model.max_seq_length, limit)

    def embed(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Return L2-normalised embeddings as a float32 numpy array."""
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
        )
        return embeddings.astype("float32")

