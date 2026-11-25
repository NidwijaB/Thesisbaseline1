"""
src/evaluation/supervisor_checks.py
-----------------------------------
No-GPU checks asked for in docs/review_sugesstions (part A), read-only on the data:
  A2  training examples per repository for the one global adapter (min / median / max)
  A3  how the 50 pilot examples were drawn (all in the 292 TEST examples with a relevant file in the pool?)
Writes results/additional_results/{training_examples_per_repo.csv, supervisor_checks.json}.

    python -m src.evaluation.supervisor_checks
"""
from __future__ import annotations

import csv
import json
import statistics
from collections import Counter
from pathlib import Path

from datasets import load_from_disk

SPLIT_DIR = Path("data/processed/crosscodeeval")
OUT = Path("results/additional_results")


def read_jsonl(path: Path):
    return [json.loads(line) for line in open(path, encoding="utf-8")]


def per_repo_counts(meta_path: Path, repos: list[str]) -> list[int]:
    counts = Counter(m["repo"] for m in read_jsonl(meta_path))
    return [counts.get(r, 0) for r in repos]


def summary(values: list[int]) -> dict:
    return {"min": min(values), "median": statistics.median(values), "max": max(values),
            "mean": round(statistics.mean(values), 1), "total": sum(values)}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    examples = read_jsonl(SPLIT_DIR / "examples.jsonl")
    manifest = read_jsonl(SPLIT_DIR / "manifest.jsonl")
    repos = sorted({m["repo"] for m in manifest})

    # A2: training / validation examples per repo (corpus is built from BASE files only)
    train = per_repo_counts(SPLIT_DIR / "finetune" / "train_meta.jsonl", repos)
    val = per_repo_counts(SPLIT_DIR / "finetune" / "val_meta.jsonl", repos)
    base_files = Counter(m["repo"] for m in manifest if m["split"] == "base")
    with open(OUT / "training_examples_per_repo.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["repo", "base_files", "train_examples", "val_examples"])
        for r, t, v in zip(repos, train, val):
            w.writerow([r, base_files.get(r, 0), t, v])

    # A3: pilot sampling. Candidates = TEST examples with >= 1 relevant file in the BASE pool (A3 rule).
    pilot = json.loads((SPLIT_DIR / "pilot_ids.json").read_text(encoding="utf-8"))
    split = {e["task_id"]: e["split"] for e in examples}
    base_paths = {(m["repo"], m["path"]) for m in manifest if m["split"] == "base"}
    rows = load_from_disk("data/crosscodeeval/python")["train"]
    candidates = set()
    for ex in rows:
        meta = ex["metadata"]
        if split.get(meta["task_id"]) != "test":
            continue
        files = {s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {meta["file"]}
        if any((meta["repository"], f) in base_paths for f in files):
            candidates.add(meta["task_id"])
    n_test = sum(1 for s in split.values() if s == "test")
    result = {
        "global_adapter": {
            "repos_in_corpus": len(repos),
            "repos_with_training_examples": sum(1 for t in train if t > 0),
            "train_examples_per_repo": summary(train),
            "val_examples_per_repo": summary(val),
        },
        "pilot_sampling": {
            "test_examples": n_test,
            "candidates_with_relevant_file_in_base_pool": len(candidates),
            "pilot_size": len(pilot),
            "pilot_all_in_candidates": all(p in candidates for p in pilot),
            "pilot_all_test": all(split.get(p) == "test" for p in pilot),
            "pilot_repos": len({e["repo"] for e in examples if e["task_id"] in set(pilot)}),
        },
    }
    (OUT / "supervisor_checks.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
