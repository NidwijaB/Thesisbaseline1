"""
src/preprocessing/prepare_datasets.py
---------------------------------------
Converts the raw RepoBench / CrossCodeEval examples (downloaded via
data/repobench/download.py and data/crosscodeeval/download.py) into the
single unified format every other script in this repo expects:

    {"input": "<partial code>", "output": "<ground-truth completion>",
     "relevant_files": ["path/a.py", "path/b.py", ...]}

- "input"          -> what the model sees (partial code / prompt)
- "output"         -> what the model should generate (ground truth)
- "relevant_files" -> ground-truth list of files that genuinely help
                      complete this example. This is ONLY used for scoring
                      retrieval quality (Precision@K, Recall@K, MRR) — the
                      fine-tuning-only baseline ignores this field entirely.

Output files (one JSON object per line):
    data/processed/train.jsonl
    data/processed/val.jsonl
    data/processed/test.jsonl

Run once, after both datasets are downloaded:
    python src/preprocessing/prepare_datasets.py

Field mapping reference (verified against the HuggingFace dataset cards):

  RepoBench (tianyang/repobench_python_v1.1):
      input          = import_statement + "\\n" + cropped_code
      output         = next_line
      relevant_files = distinct paths inside the "context" list

  CrossCodeEval (community mirror: ZHENGRAN/cross_code_eval_python):
      input          = prompt
      output         = groundtruth
      relevant_files = distinct filenames inside "crossfile_context_retrieval"

  NOTE: if you swap in the *official* amazon-science/cceval release instead
  of the community mirror (see data/crosscodeeval/download.py), the field
  names will be different ("prompt" / "groundtruth" / "crossfile_context" —
  close but not identical record structure). Re-check with a quick
  `print(dataset[0])` before trusting this script on that data.
"""

from __future__ import annotations
import json
import random
from pathlib import Path
from typing import Iterable

from src.utils.logger import get_logger

logger = get_logger(__name__)

REPOBENCH_DIR = Path("data/repobench")
CROSSCODEEVAL_DIR = Path("data/crosscodeeval")
OUTPUT_DIR = Path("data/processed")

# 80/10/10 split. Kept simple and deterministic (seeded shuffle) since
# RepoBench/CrossCodeEval are normally *evaluation* benchmarks, not training
# corpora — we're carving out a slice for fine-tuning + validation and
# holding out a test slice for the final 3-way comparison.
SPLIT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}
SEED = 42


# ── Helpers ───────────────────────────────────────────────────────────────────

def _iter_struct_list(value) -> Iterable[dict]:
    """
    HuggingFace `datasets` sometimes represents a list-of-structs field as a
    list of dicts, and sometimes (depending on how it was saved/loaded) as a
    dict of parallel lists, e.g. {"filename": [...], "retrieved_chunk": [...]}.
    This normalises either shape into an iterator of plain dicts so the rest
    of the code doesn't need to care which one it got.
    """
    if value is None:
        return
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item
    elif isinstance(value, dict):
        keys = list(value.keys())
        if not keys:
            return
        length = len(value[keys[0]])
        for i in range(length):
            yield {k: value[k][i] for k in keys}


def _write_jsonl(path: Path, examples: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for ex in examples:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    logger.info(f"Wrote {len(examples)} examples -> {path}")


def _split_by_group(examples: list, group_key: str) -> dict:
    """
    Splits examples 80/10/10 into train/val/test, keeping every example from
    the same repository/group together in the same split. This avoids
    leakage (the fine-tuned model must not train on the same repo it is
    later tested on).
    """
    groups: dict = {}
    for ex in examples:
        groups.setdefault(ex.get(group_key, "unknown"), []).append(ex)

    group_keys = list(groups.keys())
    random.Random(SEED).shuffle(group_keys)

    n = len(group_keys)
    n_train = int(n * SPLIT_RATIOS["train"])
    n_val = int(n * SPLIT_RATIOS["val"])

    train_keys = set(group_keys[:n_train])
    val_keys = set(group_keys[n_train:n_train + n_val])
    test_keys = set(group_keys[n_train + n_val:])

    out = {"train": [], "val": [], "test": []}
    for key, items in groups.items():
        if key in train_keys:
            out["train"].extend(items)
        elif key in val_keys:
            out["val"].extend(items)
        else:
            out["test"].extend(items)
    return out


# ── RepoBench ─────────────────────────────────────────────────────────────────

def convert_repobench(configs=("cross_file_first", "cross_file_random", "in_file")) -> list:
    """Reads every downloaded RepoBench config and maps it to the unified format."""
    from datasets import load_from_disk

    examples = []
    for config_name in configs:
        config_dir = REPOBENCH_DIR / config_name
        if not config_dir.exists():
            logger.warning(f"Skipping missing RepoBench config: {config_dir}")
            continue

        dataset = load_from_disk(str(config_dir))
        split_names = dataset.keys() if hasattr(dataset, "keys") else ["train"]

        for split_name in split_names:
            rows = dataset[split_name] if hasattr(dataset, "keys") else dataset
            for row in rows:
                relevant_files = sorted({
                    snippet.get("path") for snippet in _iter_struct_list(row.get("context"))
                    if snippet.get("path")
                })
                examples.append({
                    "input": f"{row.get('import_statement', '')}\n{row.get('cropped_code', '')}".strip(),
                    "output": row.get("next_line", "").strip(),
                    "relevant_files": relevant_files,
                    "source": "repobench",
                    "repo_group": row.get("repo_name", "unknown"),
                })

    logger.info(f"RepoBench: converted {len(examples)} examples")
    return examples


# ── CrossCodeEval ─────────────────────────────────────────────────────────────

def convert_crosscodeeval() -> list:
    """Reads the downloaded CrossCodeEval (community mirror) and maps it to the unified format."""
    from datasets import load_from_disk

    dataset_dir = CROSSCODEEVAL_DIR / "python"
    if not dataset_dir.exists():
        logger.warning(f"Skipping missing CrossCodeEval dataset: {dataset_dir}")
        return []

    dataset = load_from_disk(str(dataset_dir))
    split_names = dataset.keys() if hasattr(dataset, "keys") else ["train"]

    examples = []
    for split_name in split_names:
        rows = dataset[split_name] if hasattr(dataset, "keys") else dataset
        for row in rows:
            relevant_files = sorted({
                chunk.get("filename") for chunk in _iter_struct_list(row.get("crossfile_context_retrieval"))
                if chunk.get("filename")
            })
            metadata = row.get("metadata", {}) or {}
            examples.append({
                "input": (row.get("prompt", "") or "").strip(),
                "output": (row.get("groundtruth", "") or "").strip(),
                "relevant_files": relevant_files,
                "source": "crosscodeeval",
                "repo_group": metadata.get("repository", "unknown"),
            })

    logger.info(f"CrossCodeEval: converted {len(examples)} examples")
    return examples


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_examples = convert_repobench() + convert_crosscodeeval()

    if not all_examples:
        logger.error(
            "No examples produced. Did you run data/repobench/download.py "
            "and data/crosscodeeval/download.py first?"
        )
        return

    # Drop the helper "repo_group" field after splitting — downstream code
    # only expects input/output/relevant_files/source.
    splits = _split_by_group(all_examples, group_key="repo_group")
    for split_name, examples in splits.items():
        for ex in examples:
            ex.pop("repo_group", None)
        _write_jsonl(OUTPUT_DIR / f"{split_name}.jsonl", examples)

    logger.info(
        f"Done. train={len(splits['train'])}, val={len(splits['val'])}, "
        f"test={len(splits['test'])}. Files are in {OUTPUT_DIR}/"
    )


if __name__ == "__main__":
    main()