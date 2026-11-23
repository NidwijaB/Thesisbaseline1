"""
src/generation.py
------------------
Model loading and greedy one-line generation, shared by the demo, the hybrid pipeline and
the evaluation, so every system generates in exactly the same way.
"""

from __future__ import annotations

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from src.prompting import first_line


def load_model(base_name: str, adapter: str | None, use_4bit: bool):
    """Base model, optionally 4-bit (needs a GPU and bitsandbytes), optionally with a LoRA adapter.
    With an adapter, `with model.disable_adapter():` gives the base model back."""
    tokenizer = AutoTokenizer.from_pretrained(base_name, trust_remote_code=True)
    on_gpu = torch.cuda.is_available()
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16,
                             bnb_4bit_use_double_quant=True) if use_4bit else None
    model = AutoModelForCausalLM.from_pretrained(
        base_name, trust_remote_code=True, quantization_config=bnb,
        dtype=torch.float16 if on_gpu else torch.float32,
        device_map="auto" if on_gpu else None)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tokenizer, model


def classify_stop(new_ids: list[int], eos_id: int | None, max_new_tokens: int, text: str) -> str:
    """Why generation ended: "eos" (the model wrote the end-of-text token), "max_tokens" (hit the limit) or
    "newline" (the stop string was reached). An "eos" with an empty or very short first line is the early
    stop seen with the retrieval prompts (progress log Entry 41)."""
    if new_ids and eos_id is not None and new_ids[-1] == eos_id:
        return "eos"
    if len(new_ids) >= max_new_tokens and "\n" not in text:
        return "max_tokens"
    return "newline"


CODE_MARKER_TOKENS = ["<|fim_prefix|>", "<|fim_middle|>", "<|fim_suffix|>", "<|fim_pad|>", "<|repo_name|>",
                      "<|file_sep|>"]


def code_marker_ids(tokenizer) -> list[list[int]]:
    """Ids of Qwen2.5-Coder's fill-in-the-middle and file-separator tokens, as `bad_words_ids` (they are never a valid
    first line of a completion; the frozen model with the comment-wrapped chunks sometimes wrote `<|fim_suffix|>` as its
    whole answer, progress log Entry 42). Tokens the tokenizer does not know are skipped."""
    ids = [tokenizer.convert_tokens_to_ids(t) for t in CODE_MARKER_TOKENS]
    unk = tokenizer.unk_token_id
    return [[i] for i in ids if i is not None and i != unk]


def _generate(tokenizer, model, prompt: str, max_new_tokens: int, bad_words_ids=None):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    extra = {"bad_words_ids": bad_words_ids} if bad_words_ids else {}
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                             stop_strings=["\n"], tokenizer=tokenizer,
                             pad_token_id=tokenizer.eos_token_id, **extra)
    return out[0][inputs["input_ids"].shape[1]:]


def complete(tokenizer, model, prompt: str, max_new_tokens: int, bad_words_ids=None) -> str:
    """Greedy decoding, stopped at the first newline, returned as the first line."""
    new_ids = _generate(tokenizer, model, prompt, max_new_tokens, bad_words_ids)
    return first_line(tokenizer.decode(new_ids, skip_special_tokens=True))


def complete_detailed(tokenizer, model, prompt: str, max_new_tokens: int, bad_words_ids=None) -> dict:
    """Same decoding as `complete` (so the prediction is identical), plus diagnostics for the
    --save-raw option of run_comparison: the raw text with special tokens shown, the number of
    generated tokens, and why generation stopped."""
    new_ids = _generate(tokenizer, model, prompt, max_new_tokens, bad_words_ids)
    text = tokenizer.decode(new_ids, skip_special_tokens=True)
    ids = new_ids.tolist()
    return {"prediction": first_line(text),
            "raw": tokenizer.decode(new_ids, skip_special_tokens=False),
            "n_new_tokens": len(ids),
            "stop_reason": classify_stop(ids, tokenizer.eos_token_id, max_new_tokens, text)}
