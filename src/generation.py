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


def complete(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    """Greedy decoding, stopped at the first newline, returned as the first line."""
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                             stop_strings=["\n"], tokenizer=tokenizer,
                             pad_token_id=tokenizer.eos_token_id)
    text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return first_line(text)
