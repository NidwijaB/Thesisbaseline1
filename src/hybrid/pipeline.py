"""
src/hybrid/pipeline.py
-----------------------
The Hybrid RAG + Fine-Tuning inference pipeline.

Given a partial code snippet it:
1. Retrieves relevant repository chunks via the Retriever.
2. Builds the shared prompt (src/prompting.py), the same one System A uses.
3. Generates the first line of the completion with the fine-tuned model.
"""

from __future__ import annotations
import json
from pathlib import Path

from src.generation import complete, load_model
from src.prompting import build_prompt, retrieval_query
from src.retrieval.retriever import Retriever
from src.utils.logger import get_logger

logger = get_logger(__name__)


class HybridPipeline:
    def __init__(
        self,
        model_path: str,
        retriever: Retriever,
        max_new_tokens: int = 128,
        load_in_4bit: bool = True,
    ):
        # model_path is the LoRA adapter folder written by src/finetuning/trainer.py.
        # It only holds the adapter, so the base model it was trained from (recorded in
        # adapter_config.json) is loaded first and the adapter attached to it.
        self.retriever = retriever
        self.max_new_tokens = max_new_tokens

        adapter_cfg = json.loads((Path(model_path) / "adapter_config.json").read_text(encoding="utf-8"))
        logger.info(f"Loading {adapter_cfg['base_model_name_or_path']} + adapter {model_path} "
                    f"(4-bit={load_in_4bit})")
        self.tokenizer, self.model = load_model(adapter_cfg["base_model_name_or_path"], model_path, load_in_4bit)

    def complete(self, partial_code: str) -> str:
        chunks = self.retriever.retrieve(retrieval_query(partial_code))
        prompt = build_prompt(partial_code, chunks)
        return complete(self.tokenizer, self.model, prompt, self.max_new_tokens)
