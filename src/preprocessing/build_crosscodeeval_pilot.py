"""
src/preprocessing/build_crosscodeeval_pilot.py
-----------------------------------------------
Seeded selection of the pilot examples (plan Section 9, step 5).

Candidates are TEST examples with >= 1 relevant file in the main pool (BASE), using
the A3 rule from Entry 4: distinct filenames in crossfile_context_retrieval that are
in the BASE pool and are not the target file. Restricting to these means retrieval
metrics are defined for every pilot example. N_PILOT are drawn with a fixed seed.

Output: data/processed/crosscodeeval/pilot_ids.json (task_ids, sorted).

Run from the project root:
    python -m src.preprocessing.build_crosscodeeval_pilot
"""

from __future__ import annotations
import json
import random
from pathlib import Path

from datasets import load_from_disk

from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/crosscodeeval")
DATASET_DIR = Path("data/crosscodeeval/python")
SEED = 42
N_PILOT = 50


def main():
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    test_ids = {e["task_id"] for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))
                if e["split"] == "test"}
    repos_with_new = {r for (r, _), s in manifest.items() if s == "new"}

    candidates = []
    for ex in load_from_disk(str(DATASET_DIR))["train"]:
        meta = ex["metadata"]
        if meta["task_id"] not in test_ids:
            continue
        repo, target = meta["repository"], meta["file"]
        files = {s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {target}
        if any(manifest.get((repo, f)) == "base" for f in files):
            candidates.append((meta["task_id"], repo))

    assert len(candidates) == 292, f"expected 292 candidates (Entry 7), got {len(candidates)}"
    candidates.sort()
    pilot = sorted(random.Random(SEED).sample(candidates, N_PILOT))

    out = SPLIT_DIR / "pilot_ids.json"
    out.write_text(json.dumps([t for t, _ in pilot], indent=0), encoding="utf-8")
    logger.info(f"candidates: {len(candidates)}; pilot: {len(pilot)} -> {out}")
    logger.info(f"pilot repos: {len({r for _, r in pilot})}; "
                f"in repos with NEW files: {sum(r in repos_with_new for _, r in pilot)}")


if __name__ == "__main__":
    main()