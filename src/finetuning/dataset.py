"""
src/finetuning/dataset.py
--------------------------
Converts processed completion examples into a HuggingFace Dataset
ready for causal-language-model fine-tuning.

Expected JSONL format per line:
    {"input": "<partial code>", "output": "<completion>"}
"""

from __future__ import annotations
from pathlib import Path
from typing import Optional

from datasets import Dataset, DatasetDict
from transformers import PreTrainedTokenizer

PROMPT_TEMPLATE = """\
### Instruction:
Complete the following code.

### Input:
{input}

### Response:
{output}"""


def load_jsonl(path: str) -> list:
    import json
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


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
        def tokenize(example):
            text = PROMPT_TEMPLATE.format(**example)
            tokens = tokenizer(
                text,
                truncation=True,
                max_length=max_length,
                padding="max_length",
            )
            tokens["labels"] = tokens["input_ids"].copy()
            return tokens

        splits = {k: v.map(tokenize, remove_columns=["input", "output"])
                  for k, v in splits.items()}

    return DatasetDict(splits)

