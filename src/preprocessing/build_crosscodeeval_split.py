"""
src/preprocessing/build_crosscodeeval_split.py
-----------------------------------------------
Builds the CrossCodeEval knowledge pool and the per-repo BASE / NEW / TEST
file split (plan Section 3), and checks the leakage assertions that apply at
this stage (plan Section 4).

Steps:
  1. file_text = prompt + groundtruth + right_context
  2. Deduplicate by (repo, file path)
  3. Keep repos with >= 3 distinct files
  4. Split each repo's files by FILE (never by example), seeded:
       >= 5 files : BASE / NEW / TEST
       3-4 files  : BASE / TEST only (no NEW)
     with at least 2 BASE and 1 TEST file per repo
  5. Assert no overlap between splits, then write the outputs

Outputs (data/processed/crosscodeeval/):
  files.jsonl      repo, path, split, text            (the pool + test targets)
  manifest.jsonl   repo, path, split                  (split manifest)
  examples.jsonl   task_id, repo, path, split         (which split each example belongs to)

Run from the project root:
    python -m src.preprocessing.build_crosscodeeval_split
"""

from __future__ import annotations
import json
import random
from collections import defaultdict
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

DATASET_DIR = Path("data/crosscodeeval/python")
OUTPUT_DIR = Path("data/processed/crosscodeeval")

SEED = 42
MIN_FILES = 3          # repos below this are dropped
MIN_FILES_FOR_NEW = 5  # NEW files only exist for repos at or above this
NEW_FRAC = 0.175       # target 15-20%
TEST_FRAC = 0.275      # target 25-30%


def _split_counts(n: int) -> tuple:
    """Returns (n_base, n_new, n_test) for a repo with n distinct files."""
    n_test = max(1, round(TEST_FRAC * n))
    n_new = max(1, round(NEW_FRAC * n)) if n >= MIN_FILES_FOR_NEW else 0
    n_base = n - n_new - n_test
    assert n_base >= 2, f"repo with {n} files would get {n_base} BASE files"
    return n_base, n_new, n_test


def _split_repo(repo: str, paths: list) -> dict:
    """Seeded file-level split. Sorted input + per-repo seed keeps it reproducible."""
    paths = sorted(paths)
    random.Random(f"{SEED}:{repo}").shuffle(paths)
    n_base, n_new, n_test = _split_counts(len(paths))
    out = {}
    for p in paths[:n_base]:
        out[p] = "base"
    for p in paths[n_base:n_base + n_new]:
        out[p] = "new"
    for p in paths[n_base + n_new:]:
        out[p] = "test"
    return out


def load_pool() -> tuple:
    """Steps 1-2: rebuild file text and deduplicate by (repo, path)."""
    from datasets import load_from_disk

    dataset = load_from_disk(str(DATASET_DIR))["train"]  # "train" is only the key name
    texts: dict = {}
    examples = []
    conflicts = 0
    for row in dataset:
        meta = row["metadata"]
        repo, path = meta["repository"], meta["file"]
        # Check the reconstruction assumption from plan Section 2.
        assert meta["context_start_lineno"] == 0
        assert row["prompt"].count("\n") == meta["groundtruth_start_lineno"], (
            f"line-number mismatch for {meta['task_id']}")
        text = row["prompt"] + row["groundtruth"] + row["right_context"]
        if (repo, path) in texts:
            conflicts += texts[(repo, path)] != text
        else:
            texts[(repo, path)] = text
        examples.append({"task_id": meta["task_id"], "repo": repo, "path": path})
    logger.info(f"{len(examples)} examples -> {len(texts)} distinct (repo, path) files; "
                f"{conflicts} duplicate keys had different reconstructed text (first copy kept)")
    return texts, examples, conflicts


def check_assertions(split_of: dict, examples: list, files_by_repo: dict) -> None:
    """Leakage / design assertions from plan Sections 3 and 4 that apply to the split."""
    base = {k for k, s in split_of.items() if s == "base"}
    new = {k for k, s in split_of.items() if s == "new"}
    test = {k for k, s in split_of.items() if s == "test"}

    # No TEST file in the pool (BASE) or in the retrieval-only extension (NEW).
    assert not (test & base) and not (test & new) and not (base & new), "split overlap"
    # Every kept example's target file is in TEST, BASE or NEW exactly once.
    for ex in examples:
        assert (ex["repo"], ex["path"]) in split_of
    # Per-repo size rules.
    for repo, paths in files_by_repo.items():
        counts = defaultdict(int)
        for p in paths:
            counts[split_of[(repo, p)]] += 1
        assert counts["base"] >= 2 and counts["test"] >= 1, f"{repo}: {dict(counts)}"
        assert counts["new"] == 0 or len(paths) >= MIN_FILES_FOR_NEW, f"{repo}: NEW too early"
    logger.info("Leakage/design assertions passed")


def main():
    texts, examples, _ = load_pool()

    files_by_repo = defaultdict(list)
    for repo, path in texts:
        files_by_repo[repo].append(path)
    files_by_repo = {r: p for r, p in files_by_repo.items() if len(p) >= MIN_FILES}
    logger.info(f"Repos kept (>= {MIN_FILES} files): {len(files_by_repo)} of "
                f"{len({r for r, _ in texts})}")

    split_of = {}
    for repo, paths in files_by_repo.items():
        for path, split in _split_repo(repo, paths).items():
            split_of[(repo, path)] = split

    kept_examples = [ex for ex in examples if ex["repo"] in files_by_repo]
    for ex in kept_examples:
        ex["split"] = split_of[(ex["repo"], ex["path"])]

    check_assertions(split_of, kept_examples, files_by_repo)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "files.jsonl", "w", encoding="utf-8") as f_files, \
         open(OUTPUT_DIR / "manifest.jsonl", "w", encoding="utf-8") as f_man:
        for (repo, path), split in sorted(split_of.items()):
            f_man.write(json.dumps({"repo": repo, "path": path, "split": split}) + "\n")
            f_files.write(json.dumps({"repo": repo, "path": path, "split": split,
                                      "text": texts[(repo, path)]}, ensure_ascii=False) + "\n")
    with open(OUTPUT_DIR / "examples.jsonl", "w", encoding="utf-8") as f_ex:
        for ex in kept_examples:
            f_ex.write(json.dumps(ex) + "\n")

    n_files = defaultdict(int)
    for s in split_of.values():
        n_files[s] += 1
    n_ex = defaultdict(int)
    for ex in kept_examples:
        n_ex[ex["split"]] += 1
    logger.info(f"Files per split: {dict(n_files)}")
    logger.info(f"Examples per split (by target file): {dict(n_ex)}")
    logger.info(f"Wrote outputs to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()