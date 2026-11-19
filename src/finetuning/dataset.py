"""
src/finetuning/dataset.py
--------------------------
Converts processed completion examples into a HuggingFace Dataset
ready for causal-language-model fine-tuning.

Expected JSONL format per line:
    {"input": "<partial code>", "output": "<completion>"}

Each example becomes  prompt tokens + output tokens + end-of-sequence token.
Only the output tokens (and the end token) count toward the loss: prompt tokens are
labelled -100, and the padding added later by the data collator is -100 as well. If an
example is too long, the INPUT is cut from the left (the text nearest the cursor is kept)
so the output and its end token are never cut off.
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from datasets import Dataset, DatasetDict
from transformers import PreTrainedTokenizer

from src.prompting import FOOTER, HEADER, PROMPT_TEMPLATE, build_prompt  # noqa: F401  (PROMPT_TEMPLATE re-exported)

# Bump when the way examples are built changes, so checkpoints from older code are
# never resumed by mistake (see src/finetuning/trainer.py).
#   1: loss over the whole text incl. padding, no end token (first Colab smoke test)
#   2: loss on the output only, end-of-sequence token, left-truncation of the input
TRAINING_VERSION = 2

IGNORE_INDEX = -100


def load_jsonl(path: str) -> list:
    import json
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def encode_example(example: dict, tokenizer: PreTrainedTokenizer, max_length: int) -> dict:
    """Tokenise one example with the loss restricted to the output."""
    # The prompt is tokenised as ONE string, exactly as at inference time. Tokenising
    # the pieces separately would split tokens differently (for example ".\n\n").
    prompt_ids = tokenizer(build_prompt(example["input"]), add_special_tokens=False)["input_ids"]
    output_ids = tokenizer(example["output"], add_special_tokens=False)["input_ids"]
    output_ids = output_ids + [tokenizer.eos_token_id]

    # Keep at least a quarter of the window for the prompt. A truncated output gets no end token,
    # so the model never learns to stop in the middle of a line.
    max_output = max(max_length // 4 * 3, 1)
    if len(output_ids) > max_output:
        output_ids = output_ids[:max_output]

    budget = max_length - len(output_ids)
    if len(prompt_ids) > budget:
        header_len = len(tokenizer(HEADER, add_special_tokens=False)["input_ids"])
        footer_len = len(tokenizer(FOOTER, add_special_tokens=False)["input_ids"])
        tail = max(budget - header_len, footer_len)   # always keep the response marker
        prompt_ids = prompt_ids[:header_len] + prompt_ids[len(prompt_ids) - tail:]
    # Hard limit for tiny windows: the output gives way last (and then loses its end token).
    output_ids = output_ids[:max(max_length - len(prompt_ids), 1)]

    input_ids = prompt_ids + output_ids
    return {
        "input_ids": input_ids,
        "attention_mask": [1] * len(input_ids),
        "labels": [IGNORE_INDEX] * len(prompt_ids) + output_ids,
    }


def build_dataset(
    train_path: str,
    val_path: Optional[str] = None,
    tokenizer: Optional[PreTrainedTokenizer] = None,
    max_length: int = 2048,
) -> DatasetDict:
    train_data = load_jsonl(train_path)
    splits = {"train": Dataset.from_list(train_data)}
    if val_path:
        splits["validation"] = Dataset.from_list(load_jsonl(val_path))

    if tokenizer is not None:
        splits = {k: v.map(lambda ex: encode_example(ex, tokenizer, max_length),
                           remove_columns=["input", "output"])
                  for k, v in splits.items()}

    return DatasetDict(splits)
