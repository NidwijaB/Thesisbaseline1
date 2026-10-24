"""
src/preprocessing/build_repobench_split.py
--------------------------------------------
Builds the RepoBench knowledge pool and the per-repo BASE / NEW / TEST file
split (plan Section 3), with the leakage assertions that apply at this stage
(plan Section 4).

Both cross-file settings (cross_file_first, cross_file_random) share ONE split.
They overlap heavily (same repos, same target files), so splitting each setting
separately would let a file be TEST in one and BASE in the other.

Per repo, the file universe is the union of target files (`file_path`) and
snippet source files (`context[*].path`). Only target files can be TEST, since
only they have a next line to predict.

Pool entries are fragments, not full files (plan Section 3):
  kind "prefix"  : longest `all_code` seen for a target file (file text up to the
                   last target line seen)
  kind "snippet" : a distinct context snippet for a file path
Deduplicated by (repo, path, text). TEST files never enter the pool, filtered by
path AND by content (a fragment contained in a TEST file's text is dropped).

Outputs (data/processed/repobench/):
  manifest.jsonl   repo, path, split, is_target
  pool.jsonl       repo, path, split (base|new), kind, identifier, text
  examples.jsonl   setting, row, repo, path, split, level, gold_path
                   (row = index into data/repobench/<setting>; gold_path is null
                   when gold_snippet_index is out of range)

Run from the project root:
    python -m src.preprocessing.build_repobench_split
"""

from __future__ import annotations
import json
import random
from collections import defaultdict
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)

SETTINGS = ("cross_file_first", "cross_file_random")
DATA_DIR = Path("data/repobench")
OUTPUT_DIR = Path("data/processed/repobench")

SEED = 42
MIN_FILES = 3
MIN_FILES_FOR_NEW = 5
NEW_FRAC = 0.175
TEST_FRAC = 0.275

COLUMNS = ["repo_name", "file_path", "context", "all_code", "gold_snippet_index", "level"]


def load_universe() -> tuple:
    """Reads both settings once; returns targets, snippets, and light example records."""
    from datasets import load_from_disk

    prefix_of: dict = {}                       # (repo, path) -> longest all_code
    snippets: dict = defaultdict(dict)         # (repo, path) -> {text: identifier}
    examples = []
    for setting in SETTINGS:
        ds = load_from_disk(str(DATA_DIR / setting)).select_columns(COLUMNS)
        for i, row in enumerate(ds):
            key = (row["repo_name"], row["file_path"])
            if len(row["all_code"]) > len(prefix_of.get(key, "")):
                prefix_of[key] = row["all_code"]
            for c in row["context"]:
                snippets[(row["repo_name"], c["path"])].setdefault(c["snippet"], c["identifier"])
            g = row["gold_snippet_index"]
            gold_path = row["context"][g]["path"] if 0 <= g < len(row["context"]) else None
            examples.append({"setting": setting, "row": i, "repo": row["repo_name"],
                             "path": row["file_path"], "level": row["level"],
                             "gold_path": gold_path})
        logger.info(f"{setting}: {len(ds)} examples read")
    return prefix_of, snippets, examples


def _split_repo(repo: str, paths: list, target_paths: set) -> dict:
    n = len(paths)
    n_test = min(max(1, round(TEST_FRAC * n)), len(target_paths))
    n_new = max(1, round(NEW_FRAC * n)) if n >= MIN_FILES_FOR_NEW else 0
    rng = random.Random(f"{SEED}:{repo}")

    targets = sorted(target_paths)
    rng.shuffle(targets)
    test = set(targets[:n_test])
    rest = sorted(set(paths) - test)
    rng.shuffle(rest)
    out = {p: "test" for p in test}
    for p in rest[:n_new]:
        out[p] = "new"
    for p in rest[n_new:]:
        out[p] = "base"
    return out


def main():
    prefix_of, snippets, examples = load_universe()
    targets_by_repo = defaultdict(set)
    files_by_repo = defaultdict(set)
    for repo, path in prefix_of:
        targets_by_repo[repo].add(path)
        files_by_repo[repo].add(path)
    for repo, path in snippets:
        files_by_repo[repo].add(path)

    kept = {r for r, p in files_by_repo.items() if len(p) >= MIN_FILES}
    logger.info(f"Repos kept (>= {MIN_FILES} files): {len(kept)} of {len(files_by_repo)}")

    split_of = {}
    for repo in sorted(kept):
        for path, split in _split_repo(repo, sorted(files_by_repo[repo]), targets_by_repo[repo]).items():
            split_of[(repo, path)] = split

    # Pool: BASE and NEW files only, filtered by path and by content against TEST text.
    test_texts = defaultdict(list)
    for (repo, path), split in split_of.items():
        if split == "test":
            test_texts[repo].append(prefix_of[(repo, path)])
    pool, seen, content_dropped = [], set(), 0
    for (repo, path), split in sorted(split_of.items()):
        if split == "test":
            continue
        entries = []
        if (repo, path) in prefix_of:
            entries.append(("prefix", "", prefix_of[(repo, path)]))
        for text, ident in snippets.get((repo, path), {}).items():
            entries.append(("snippet", ident, text))
        for kind, ident, text in entries:
            if (repo, path, text) in seen:
                continue
            seen.add((repo, path, text))
            if any(text in t for t in test_texts[repo]):
                content_dropped += 1
                continue
            pool.append({"repo": repo, "path": path, "split": split, "kind": kind,
                         "identifier": ident, "text": text})

    kept_examples = [ex for ex in examples if ex["repo"] in kept]
    for ex in kept_examples:
        ex["split"] = split_of[(ex["repo"], ex["path"])]

    # Section 3 / 4 assertions
    test_keys = {k for k, s in split_of.items() if s == "test"}
    for k in test_keys:
        assert k in prefix_of, "TEST file that is not a target file"
    for e in pool:
        assert (e["repo"], e["path"]) not in test_keys, "TEST path in pool"
        assert e["split"] in ("base", "new")
        assert not any(e["text"] in t for t in test_texts[e["repo"]]), "TEST content in pool"
    for ex in kept_examples:
        assert (ex["repo"], ex["path"]) in split_of
    for repo in kept:
        counts = defaultdict(int)
        for p in files_by_repo[repo]:
            counts[split_of[(repo, p)]] += 1
        assert counts["base"] >= 2 and counts["test"] >= 1, f"{repo}: {dict(counts)}"
        assert counts["new"] == 0 or len(files_by_repo[repo]) >= MIN_FILES_FOR_NEW
    logger.info("Leakage/design assertions passed")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_DIR / "manifest.jsonl", "w", encoding="utf-8") as f:
        for (repo, path), split in sorted(split_of.items()):
            f.write(json.dumps({"repo": repo, "path": path, "split": split,
                                "is_target": (repo, path) in prefix_of}) + "\n")
    with open(OUTPUT_DIR / "pool.jsonl", "w", encoding="utf-8") as f:
        for e in pool:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    with open(OUTPUT_DIR / "examples.jsonl", "w", encoding="utf-8") as f:
        for ex in kept_examples:
            f.write(json.dumps(ex) + "\n")

    n_files = defaultdict(int)
    for s in split_of.values():
        n_files[s] += 1
    logger.info(f"Files per split: {dict(n_files)}")
    for setting in SETTINGS:
        by = defaultdict(int)
        for ex in kept_examples:
            if ex["setting"] == setting:
                by[ex["split"]] += 1
        logger.info(f"{setting} examples per split: {dict(by)}")
    logger.info(f"Pool fragments: {len(pool)} (dropped by content filter: {content_dropped})")
    logger.info(f"Wrote outputs to {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()
