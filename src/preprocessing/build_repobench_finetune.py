"""
src/preprocessing/build_repobench_finetune.py
-----------------------------------------------
Builds the RepoBench fine-tuning corpus (plan Sections 3, 4, 5) from BASE pool
fragments only. One adapter for the whole RepoBench dataset.

Each example cuts a BASE fragment at a line boundary: input = the lines before
the cut, output = the next line (RepoBench task: predict the next line).
Fragments are pieces of files, so this is chunk-level fine-tuning (plan Section 3).

Outputs (data/processed/repobench/finetune/):
  train.jsonl / val.jsonl             {"input", "output"}
  train_meta.jsonl / val_meta.jsonl   repo, path, split, kind, line_no

Run from the project root (after build_repobench_split):
    python -m src.preprocessing.build_repobench_finetune
"""

from __future__ import annotations
import json
import random
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/repobench")
OUTPUT_DIR = SPLIT_DIR / "finetune"

SEED = 42
CUTS_PER_PREFIX = 8      # prefixes are long; snippets are short
CUTS_PER_SNIPPET = 1
MAX_EXAMPLES = 12000     # seeded subsample, to keep training cost near the CrossCodeEval corpus
VAL_FRAC = 0.1
MAX_PREFIX_CHARS = 1500  # fit the 512-token training limit in config.yaml
MIN_LONG = 20            # TEST next lines this long are also removed if found inside an input


def _candidates(lines: list) -> list:
    """Line numbers usable as the 'next line' (needs at least 2 lines of context)."""
    out = []
    for i in range(2, len(lines)):
        s = lines[i].strip()
        if len(s) < 8 or s.startswith("#"):
            continue
        out.append(i)
    return out


def _make_example(lines: list, i: int) -> dict:
    prefix = "\n".join(lines[:i]) + "\n"
    if len(prefix) > MAX_PREFIX_CHARS:
        prefix = prefix[-MAX_PREFIX_CHARS:]
        prefix = prefix[prefix.find("\n") + 1:] if "\n" in prefix else prefix
    return {"input": prefix, "output": lines[i]}


def _load_test_next_lines(test_rows: dict) -> set:
    """next_line of every TEST example, read from the original datasets."""
    from datasets import load_from_disk

    out = set()
    for setting, rows in test_rows.items():
        ds = load_from_disk(f"data/repobench/{setting}").select_columns(["next_line"])
        wanted = set(rows)
        out |= {r["next_line"] for i, r in enumerate(ds) if i in wanted}
    return out


def main():
    pool = [json.loads(l) for l in open(SPLIT_DIR / "pool.jsonl", encoding="utf-8")]
    test_rows: dict = {}
    split_of_file = {}
    for ex in map(json.loads, open(SPLIT_DIR / "examples.jsonl")):
        split_of_file[(ex["repo"], ex["path"])] = ex["split"]
        if ex["split"] == "test":
            test_rows.setdefault(ex["setting"], set()).add(ex["row"])
    test_keys = {k for k, s in split_of_file.items() if s == "test"}
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl"))}

    test_next = _load_test_next_lines(test_rows)
    long_next = [t for t in test_next if len(t) >= MIN_LONG]

    candidates = []   # (example, meta)
    short_overlap = dropped = 0
    for frag in pool:
        if frag["split"] != "base":
            continue
        lines = frag["text"].split("\n")
        cands = _candidates(lines)
        rng = random.Random(f"{SEED}:{frag['repo']}:{frag['path']}:{frag['kind']}:{hash_text(frag['text'])}")
        rng.shuffle(cands)
        n = CUTS_PER_PREFIX if frag["kind"] == "prefix" else CUTS_PER_SNIPPET
        for i in cands[:n]:
            ex = _make_example(lines, i)
            if ex["output"] in test_next:
                dropped += 1
                short_overlap += len(ex["output"]) < MIN_LONG
                continue
            if any(t in ex["input"] for t in long_next):
                continue
            candidates.append((ex, {"repo": frag["repo"], "path": frag["path"], "split": "base",
                                    "kind": frag["kind"], "line_no": i}))

    # dedupe identical (input, output) pairs, then seeded subsample
    seen, unique = set(), []
    for ex, meta in candidates:
        k = (ex["input"], ex["output"])
        if k not in seen:
            seen.add(k)
            unique.append((ex, meta))
    random.Random(f"{SEED}:rb-subsample").shuffle(unique)
    chosen = unique[:MAX_EXAMPLES]
    n_val = round(VAL_FRAC * len(chosen))
    val, train = chosen[:n_val], chosen[n_val:]

    # Section 4 assertions
    for _, meta in train + val:
        key = (meta["repo"], meta["path"])
        assert manifest[key] == "base", "non-BASE file in corpus"
        assert key not in test_keys, "TEST file in corpus"
    for ex, _ in train + val:
        assert ex["output"] not in test_next, "test next_line in output"
        assert not any(t in ex["input"] for t in long_next), "test next_line in input"
    assert {(e["input"], e["output"]) for e, _ in train}.isdisjoint(
        {(e["input"], e["output"]) for e, _ in val}), "train/val share an example"
    logger.info("Leakage assertions passed")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, rows in [("train", train), ("val", val)]:
        with open(OUTPUT_DIR / f"{name}.jsonl", "w", encoding="utf-8") as f, \
             open(OUTPUT_DIR / f"{name}_meta.jsonl", "w", encoding="utf-8") as fm:
            for ex, meta in rows:
                f.write(json.dumps(ex, ensure_ascii=False) + "\n")
                fm.write(json.dumps(meta) + "\n")

    kinds = {}
    for _, m in chosen:
        kinds[m["kind"]] = kinds.get(m["kind"], 0) + 1
    logger.info(f"Candidates={len(candidates)}, unique={len(unique)}, used={len(chosen)} "
                f"(train={len(train)}, val={len(val)}); by fragment kind: {kinds}")
    logger.info(f"Dropped for matching a TEST next line exactly (of which short, <{MIN_LONG} chars): {dropped} ({short_overlap})")
    logger.info(f"Wrote outputs to {OUTPUT_DIR}/")


def hash_text(text: str) -> str:
    import hashlib
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:8]


if __name__ == "__main__":
    main()
