"""
src/preprocessing/build_repobench_sample.py
--------------------------------------------
Seeded evaluation sample for RepoBench (plan Section 9, step 8: "smaller sample if GPU time is
tight"). The full TEST set is about 12,000 examples, too many for generation on a free GPU, and
indexing every repository on CPU would take hours; this fixes the sampling rule.

Rule: per setting (cross_file_first, cross_file_random), candidates = TEST examples whose gold file
(the file of context[gold_snippet_index]) is in the BASE pool and is not the example's own file
(the main-condition rule from Entry 10). Draw N with random.Random(42) from the sorted candidates.
Same rule as the CrossCodeEval pilot (Entry 13): metrics are then defined for every sampled example,
and the sample is plain random, not stratified.

Output: data/processed/repobench/sample_ids.json  {setting: [row, ...]}  (row = index into
data/repobench/<setting>; gitignored) and sample_repos.json (the repos the index build has to cover).

Run from the project root:
    python -m src.preprocessing.build_repobench_sample [--n 300]
"""

from __future__ import annotations
import argparse
import json
import random
from pathlib import Path

SPLIT_DIR = Path("data/processed/repobench")
SEED = 42


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300, help="examples per setting")
    args = ap.parse_args()

    # "in the BASE pool" = at least one BASE fragment exists for the file (a BASE file whose
    # fragments were all dropped by the content filter, Entry 10, is not in the pool)
    base_pool = {(r["repo"], r["path"])
                 for r in map(json.loads, open(SPLIT_DIR / "pool.jsonl", encoding="utf-8"))
                 if r["split"] == "base"}
    cands: dict[str, list] = {}
    for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8")):
        if e["split"] != "test" or not e.get("gold_path") or e["gold_path"] == e["path"]:
            continue
        if (e["repo"], e["gold_path"]) not in base_pool:
            continue
        cands.setdefault(e["setting"], []).append((e["row"], e["repo"]))

    sample, repos = {}, set()
    for setting in sorted(cands):
        rows = sorted(cands[setting])
        picked = random.Random(SEED).sample(rows, min(args.n, len(rows)))
        sample[setting] = sorted(r for r, _ in picked)
        repos |= {repo for _, repo in picked}
        print(f"{setting}: {len(rows)} candidates, sampled {len(picked)}")
    (SPLIT_DIR / "sample_ids.json").write_text(json.dumps(sample), encoding="utf-8")
    (SPLIT_DIR / "sample_repos.json").write_text(json.dumps(sorted(repos)), encoding="utf-8")
    print(f"distinct repos to index: {len(repos)}")


if __name__ == "__main__":
    main()
