"""
src/hybrid/pipeline.py
-----------------------
The Hybrid RAG + Fine-Tuning inference pipeline.

Given a partial code snippet it:
1. Retrieves relevant repository context via the Retriever.
2. Builds an augmented prompt.
3. Generates a completion with the fine-tuned model.
"""

from __future__ import annotations
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from src.retrieval.retriever import Retriever
from src.utils.logger import get_logger

logger = get_logger(__name__)

PROMPT_TEMPLATE = """\
### Retrieved Context:
{context}

### Current File:
{query}

### Response:
"""


class HybridPipeline:
    def __init__(
        self,
        model_path: str,
        retriever: Retriever,
        max_new_tokens: int = 128,
        temperature: float = 0.2,
        device: str = "cuda",
    ):
        self.retriever = retriever
        self.device = device
        self.max_new_tokens = max_new_tokens
        self.temperature = temperature

        logger.info(f"Loading fine-tuned model from {model_path}")
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            device_map="auto",
        )
        self.model.eval()

    def complete(self, partial_code: str) -> str:
        context = self.retriever.build_context_string(partial_code)
        prompt = PROMPT_TEMPLATE.format(context=context, query=partial_code)

        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output_ids = self.model.generate(
                **inputs,
                max_new_tokens=self.max_new_tokens,
                temperature=self.temperature,
                do_sample=self.temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id,
            )
        generated = output_ids[0][inputs["input_ids"].shape[1]:]
        return self.tokenizer.decode(generated, skip_special_tokens=True)

