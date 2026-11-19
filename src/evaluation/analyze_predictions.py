"""
src/evaluation/analyze_predictions.py
--------------------------------------
Analyses of one run's predictions.jsonl (written by experiments/run_comparison.py), plan Section 6:

  1. Hit vs miss: for the systems that retrieve (rag_only, hybrid), exact match and edit similarity
     when a relevant file was inside the top-k chunks (hit) and when it was not (miss), with the
     sample sizes and a bootstrap 95% CI of the hit-minus-miss difference.
  2. Paired system differences over all examples (same examples, so the bootstrap resamples whole
     examples): rag_only - base, finetuning_only - base, hybrid - rag_only, hybrid - finetuning_only,
     rag_only - finetuning_only. Each with a 95% CI; an interval that excludes 0 is the evidence.

Samples are small (pilot n=50): report the numbers as a pipeline check. A miss group of a handful of
examples has a very wide interval; the output prints n so that this is visible.

Run from the project root:
    python -m src.evaluation.analyze_predictions results/pilot_main/predictions.jsonl
Writes <same folder>/analysis.json and prints a table.
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import numpy as np

METRICS = ("exact_match", "edit_similarity")
PAIRS = [("rag_only", "base"), ("finetuning_only", "base"), ("hybrid", "rag_only"),
         ("hybrid", "finetuning_only"), ("rag_only", "finetuning_only")]
RETRIEVING = ("rag_only", "hybrid")


def load_rows(path: str) -> list[dict]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def _ci(samples: np.ndarray, level: float = 0.95) -> list[float]:
    tail = (1 - level) / 2 * 100
    return [round(float(np.percentile(samples, tail)), 4), round(float(np.percentile(samples, 100 - tail)), 4)]


def boot_mean(values, n=2000, seed=42) -> dict:
    v = np.asarray(values, dtype=float)
    if len(v) == 0:
        return {"n": 0, "mean": None, "ci95": None}
    idx = np.random.default_rng(seed).integers(0, len(v), size=(n, len(v)))
    return {"n": len(v), "mean": round(float(v.mean()), 4), "ci95": _ci(v[idx].mean(axis=1))}


def boot_diff_groups(a, b, n=2000, seed=42) -> dict:
    """Difference of means of two independent groups (a minus b), bootstrap over each group."""
    a, b = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if len(a) == 0 or len(b) == 0:
        return {"mean": None, "ci95": None}
    rng = np.random.default_rng(seed)
    da = a[rng.integers(0, len(a), size=(n, len(a)))].mean(axis=1)
    db = b[rng.integers(0, len(b), size=(n, len(b)))].mean(axis=1)
    return {"mean": round(float(a.mean() - b.mean()), 4), "ci95": _ci(da - db)}


def boot_diff_paired(a, b, n=2000, seed=42) -> dict:
    d = np.asarray(a, dtype=float) - np.asarray(b, dtype=float)
    res = boot_mean(d, n=n, seed=seed)
    return {"mean": res["mean"], "ci95": res["ci95"]}


def analyse(rows: list[dict]) -> dict:
    systems = [s for s in ("base", "rag_only", "finetuning_only", "hybrid") if s in rows[0]]
    out = {"n_examples": len(rows), "systems": systems, "hit_vs_miss": {}, "paired_differences": {}}

    scored = [r for r in rows if r["relevant_files"]]            # hit/miss is defined only for these
    out["n_with_relevant_file"] = len(scored)
    for system in (s for s in RETRIEVING if s in systems):
        out["hit_vs_miss"][system] = {}
        for metric in METRICS:
            hit = [r[system][metric] for r in scored if r["relevant_in_top_k"]]
            miss = [r[system][metric] for r in scored if not r["relevant_in_top_k"]]
            out["hit_vs_miss"][system][metric] = {"hit": boot_mean(hit), "miss": boot_mean(miss),
                                                  "hit_minus_miss": boot_diff_groups(hit, miss)}

    for a, b in PAIRS:
        if a in systems and b in systems:
            out["paired_differences"][f"{a} - {b}"] = {
                m: boot_diff_paired([r[a][m] for r in rows], [r[b][m] for r in rows]) for m in METRICS}
    return out


def print_report(res: dict) -> None:
    print(f"examples: {res['n_examples']} (with a relevant file: {res['n_with_relevant_file']})")
    print("\nHit vs miss (relevant file inside / outside the top-k chunks)")
    for system, by_metric in res["hit_vs_miss"].items():
        for metric, g in by_metric.items():
            print(f"  {system:16s} {metric:16s} hit n={g['hit']['n']:3d} mean={g['hit']['mean']}   "
                  f"miss n={g['miss']['n']:3d} mean={g['miss']['mean']}   "
                  f"hit-miss={g['hit_minus_miss']['mean']} CI={g['hit_minus_miss']['ci95']}")
    print("\nPaired differences over all examples (95% bootstrap CI)")
    for pair, by_metric in res["paired_differences"].items():
        for metric, d in by_metric.items():
            flag = "" if d["ci95"] is None or d["ci95"][0] <= 0 <= d["ci95"][1] else "  <- excludes 0"
            print(f"  {pair:32s} {metric:16s} {d['mean']:+.4f} {d['ci95']}{flag}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("predictions", help="predictions.jsonl from experiments/run_comparison.py")
    args = ap.parse_args()
    res = analyse(load_rows(args.predictions))
    print_report(res)
    out = Path(args.predictions).parent / "analysis.json"
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
