"""
src/finetuning/eval_loss.py
----------------------------
Validation loss of the base model and of the fine-tuned adapter on the SAME validation set, computed
the same way (loss on the answer tokens and the end token only, as in training). This answers the
question the training log cannot: did fine-tuning lower the loss compared with no fine-tuning?

Uses the same encoding as training (src/finetuning/dataset.py), the same max length, and 4-bit weights
when --4bit is given (QLoRA trained against a 4-bit base, so use --4bit on a GPU for a like-for-like
number). Loss is summed over all answer tokens and divided by the token count, so it can differ
slightly from the Trainer's eval_loss, which averages per-batch means; compare base and adapter
with THIS script, not with the Trainer's number.

Validation is not file-held-out (progress log Entries 8 and 11), so both numbers are optimistic.

Run from the project root (GPU recommended; the small default batch avoids the out-of-memory message
seen during training evaluation):
    python -m src.finetuning.eval_loss --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import torch
from datasets import Dataset
from transformers import DataCollatorForSeq2Seq

from src.finetuning.dataset import IGNORE_INDEX, encode_example, load_jsonl
from src.generation import load_model
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


@torch.no_grad()
def mean_loss(model, loader) -> tuple[float, int]:
    total, count = 0.0, 0
    for batch in loader:
        batch = {k: v.to(model.device) for k, v in batch.items()}
        logits = model(input_ids=batch["input_ids"], attention_mask=batch["attention_mask"]).logits
        shift_logits = logits[:, :-1].float()
        shift_labels = batch["labels"][:, 1:]
        loss = torch.nn.functional.cross_entropy(
            shift_logits.reshape(-1, shift_logits.size(-1)), shift_labels.reshape(-1),
            ignore_index=IGNORE_INDEX, reduction="sum")
        total += loss.item()
        count += int((shift_labels != IGNORE_INDEX).sum())
        del logits, shift_logits
    return total / count, count


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--dataset", choices=["crosscodeeval", "repobench"], default="crosscodeeval")
    ap.add_argument("--batch-size", type=int, default=2)
    ap.add_argument("--limit", type=int, default=None, help="first N validation examples (quick test)")
    ap.add_argument("--4bit", dest="use_4bit", action="store_true")
    ap.add_argument("--output", default="results/val_loss_base_vs_adapter.json")
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    rows = load_jsonl(f"data/processed/{args.dataset}/finetune/val.jsonl")
    if args.limit:
        rows = rows[:args.limit]

    tokenizer, model = load_model(cfg.finetuning.base_model, args.adapter, args.use_4bit)
    tokenizer.pad_token = tokenizer.eos_token
    max_length = cfg.finetuning.max_seq_length
    encoded = Dataset.from_list(rows).map(lambda ex: encode_example(ex, tokenizer, max_length),
                                          remove_columns=["input", "output"])
    collator = DataCollatorForSeq2Seq(tokenizer, padding=True)
    loader = torch.utils.data.DataLoader(encoded, batch_size=args.batch_size, collate_fn=collator)

    result = {"dataset": args.dataset, "n_examples": len(rows), "adapter": args.adapter,
              "four_bit": args.use_4bit, "max_length": max_length}
    result["adapter_loss"], result["answer_tokens"] = mean_loss(model, loader)
    with model.disable_adapter():
        result["base_loss"], _ = mean_loss(model, loader)
    result["difference_base_minus_adapter"] = round(result["base_loss"] - result["adapter_loss"], 4)
    for key in ("adapter_loss", "base_loss"):
        result[key] = round(result[key], 4)
    logger.info(json.dumps(result))

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info(f"Saved {out}")


if __name__ == "__main__":
    main()
