"""
src/preprocessing/build_crosscodeeval_finetune.py
---------------------------------------------------
Builds the fine-tuning corpus for System B / the fine-tuned part of System C
(plan Sections 3, 4, 5) from BASE files only.

Each example cuts a BASE file inside a line: input = file prefix up to the cut,
output = rest of that line. CrossCodeEval prompts always end right after a '.'
(a member access), so cuts are placed after a '.' to match the test format.

Validation examples are different lines from the same BASE files (never TEST).

Outputs (data/processed/crosscodeeval/finetune/):
  train.jsonl / val.jsonl             {"input", "output"}  (what src/finetuning/dataset.py reads)
  train_meta.jsonl / val_meta.jsonl   repo, path, split, line_no  (line-aligned provenance)

Run from the project root (after build_crosscodeeval_split):
    python -m src.preprocessing.build_crosscodeeval_finetune
"""

from __future__ import annotations
import json
import random
import re
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/crosscodeeval")
OUTPUT_DIR = SPLIT_DIR / "finetune"

SEED = 42
EXAMPLES_PER_FILE = 20   # cut points sampled per BASE file (before the train/val split)
VAL_FRAC = 0.1           # share of sampled lines held out for validation
MAX_PREFIX_CHARS = 1500  # keep the prompt near the 512-token training limit
MIN_LONG_GT = 20         # test groundtruths this long are also checked inside inputs

CUT_RE = re.compile(r"(?<=[A-Za-z_\)\]])\.(?=[A-Za-z_])")


def _candidates(lines: list) -> list:
    """(line_no, cut_col) pairs: after a '.', with a non-empty rest of line."""
    out = []
    for i, line in enumerate(lines):
        s = line.lstrip()
        if not s or s.startswith(("#", "import ", "from ")):
            continue
        for m in CUT_RE.finditer(line):
            out.append((i, m.end()))
    return out


def _make_example(lines: list, line_no: int, col: int) -> dict:
    prefix = "\n".join(lines[:line_no]) + ("\n" if line_no else "") + lines[line_no][:col]
    if len(prefix) > MAX_PREFIX_CHARS:
        prefix = prefix[-MAX_PREFIX_CHARS:]
        prefix = prefix[prefix.find("\n") + 1:] if "\n" in prefix else prefix
    return {"input": prefix, "output": lines[line_no][col:]}


def _load_test_groundtruths(test_keys: set) -> set:
    from datasets import load_from_disk

    dataset = load_from_disk("data/crosscodeeval/python")["train"]
    return {row["groundtruth"] for row in dataset
            if (row["metadata"]["repository"], row["metadata"]["file"]) in test_keys}


def main():
    files = [json.loads(l) for l in open(SPLIT_DIR / "files.jsonl", encoding="utf-8")]
    split_of = {(f["repo"], f["path"]): f["split"] for f in files}
    test_keys = {k for k, s in split_of.items() if s == "test"}
    new_keys = {k for k, s in split_of.items() if s == "new"}

    test_gts = _load_test_groundtruths(test_keys)
    long_gts = [g for g in test_gts if len(g) >= MIN_LONG_GT]

    train, val, train_meta, val_meta = [], [], [], []
    dropped = 0
    for f in files:
        if f["split"] != "base":
            continue
        lines = f["text"].split("\n")
        cands = _candidates(lines)
        rng = random.Random(f"{SEED}:{f['repo']}:{f['path']}:ft")
        rng.shuffle(cands)
        # one cut per line, so train and val never share a target line
        seen, picked = set(), []
        for line_no, col in cands:
            if line_no in seen:
                continue
            seen.add(line_no)
            picked.append((line_no, col))
            if len(picked) == EXAMPLES_PER_FILE:
                break
        n_val = round(VAL_FRAC * len(picked)) if len(picked) >= 2 else 0
        for idx, (line_no, col) in enumerate(picked):
            ex = _make_example(lines, line_no, col)
            # drop anything that would put a TEST groundtruth into the corpus
            if ex["output"] in test_gts or any(g in ex["input"] for g in long_gts):
                dropped += 1
                continue
            meta = {"repo": f["repo"], "path": f["path"], "split": "base", "line_no": line_no}
            target, target_meta = (val, val_meta) if idx < n_val else (train, train_meta)
            target.append(ex)
            target_meta.append(meta)

    # Section 4 assertions
    for meta in train_meta + val_meta:
        key = (meta["repo"], meta["path"])
        assert meta["split"] == "base" and split_of[key] == "base", "non-BASE file in corpus"
        assert key not in test_keys, "TEST file in fine-tuning corpus"
        assert key not in new_keys, "NEW file in fine-tuning corpus"
    for ex in train + val:
        assert ex["output"] not in test_gts, "test groundtruth in corpus output"
        assert not any(g in ex["input"] for g in long_gts), "test groundtruth in corpus input"
    assert {(m["repo"], m["path"], m["line_no"]) for m in train_meta}.isdisjoint(
        {(m["repo"], m["path"], m["line_no"]) for m in val_meta}), "train/val share a target line"
    logger.info("Leakage assertions passed")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in [("train", train), ("val", val),
                       ("train_meta", train_meta), ("val_meta", val_meta)]:
        with open(OUTPUT_DIR / f"{name}.jsonl", "w", encoding="utf-8") as fh:
            for r in rows:
                fh.write(json.dumps(r, ensure_ascii=False) + "\n")

    n_base = sum(1 for f in files if f["split"] == "base")
    logger.info(f"BASE files: {n_base}; train={len(train)}, val={len(val)}; "
                f"dropped for groundtruth overlap={dropped}")
    logger.info(f"Wrote outputs to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()