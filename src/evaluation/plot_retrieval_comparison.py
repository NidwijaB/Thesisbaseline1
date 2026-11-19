"""
src/evaluation/plot_retrieval_comparison.py
--------------------------------------------
Plots for results/retrieval_comparison.json (written by src.retrieval.compare_retrievers).
Writes PNGs to results/figures/. Error bars are 95% bootstrap confidence intervals.

    python -m src.evaluation.plot_retrieval_comparison [--input results/retrieval_comparison.json]
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

SYSTEMS = ["random", "bm25", "dense"]
LABELS = {"random": "Random (floor)", "bm25": "BM25", "dense": "Dense (UniXcoder)"}
COLORS = {"random": "#9aa0a6", "bm25": "#e08a1e", "dense": "#1f6fb4"}
KS = (1, 3, 5, 10)


def errorbars(entries):
    lows = [e["mean"] - e["ci95"][0] for e in entries]
    highs = [e["ci95"][1] - e["mean"] for e in entries]
    return [lows, highs]


def grouped_bars(data, view, subset, out_path):
    """hit@1, hit@3 and MRR for the three retrievers in one view/subset."""
    metrics = [("hit@1", "hit@1"), ("hit@3", "hit@3"), ("mrr", "MRR")]
    n = data["n"][view][subset]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    width = 0.26
    for i, system in enumerate(SYSTEMS):
        entries = [data["metrics"][view][subset][system][m] for m, _ in metrics]
        xs = [j + (i - 1) * width for j in range(len(metrics))]
        ax.bar(xs, [e["mean"] for e in entries], width, yerr=errorbars(entries), capsize=3,
               color=COLORS[system], label=LABELS[system])
    ax.set_xticks(range(len(metrics)), [name for _, name in metrics])
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("score (higher is better)")
    ax.set_title(f"File retrieval, {view} pool, {subset.replace('_', ' ')} (n={n})")
    ax.legend(loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def hit_at_k_lines(data, view, out_path):
    """hit@k against k, showing how quickly small pools saturate."""
    n = data["n"][view]["all"]
    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    for system in SYSTEMS:
        entries = [data["metrics"][view]["all"][system][f"hit@{k}"] for k in KS]
        ax.errorbar(KS, [e["mean"] for e in entries], yerr=errorbars(entries), marker="o", capsize=3,
                    color=COLORS[system], label=LABELS[system])
    ax.set_xticks(KS)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("k (files)")
    ax.set_ylabel("hit@k")
    ax.set_title(f"hit@k by retriever, {view} pool (n={n})\nsmall pools: high k covers nearly every file")
    ax.legend(loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/retrieval_comparison.json")
    parser.add_argument("--output-dir", default="results/figures")
    args = parser.parse_args()

    data = json.loads(Path(args.input).read_text(encoding="utf-8"))
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    grouped_bars(data, "main", "all", out / "retrieval_main.png")
    grouped_bars(data, "staleness", "all", out / "retrieval_staleness.png")
    if "new_relevant" in data["metrics"].get("staleness", {}):
        grouped_bars(data, "staleness", "new_relevant", out / "retrieval_staleness_new_files.png")
    hit_at_k_lines(data, "main", out / "hit_at_k_main.png")
    print(f"Figures written to {out}")


if __name__ == "__main__":
    main()
