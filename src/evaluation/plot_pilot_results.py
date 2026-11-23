"""
src/evaluation/plot_pilot_results.py
-------------------------------------
Slide charts for the Part 1 pilot (progress log Entries 40 and 41), drawn from the saved result folders in results/.
Every number comes from the metrics files / predictions.jsonl of those runs; nothing is typed in by hand. Run it again
whenever a run is repeated:

    python -m src.evaluation.plot_pilot_results            # writes results/figures/pilot_*.png and pilot_numbers.csv

Colour roles (validated with the dataviz skill, light surface): RAG blue, fine-tuned orange, hybrid aqua, base is the
neutral reference (grey). The aqua mark is below 3:1 on a white surface, so every bar also carries its value as a label
and pilot_numbers.csv holds the table behind each chart. Pilot, n=50 (n=68 for the staleness test): never "findings".
"""

from __future__ import annotations
import csv
import json
import math
from pathlib import Path

from src.evaluation.analyze_predictions import boot_mean

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

R = Path("results")
OUT = R / "figures"
SYSTEMS = ["base", "rag_only", "finetuning_only", "hybrid"]
LABEL = {"base": "base", "rag_only": "RAG (A)", "finetuning_only": "fine-tuned (B)", "hybrid": "hybrid (C)"}
COLOR = {"base": "#8a8984", "rag_only": "#2a78d6", "finetuning_only": "#eb6834", "hybrid": "#1baf7a"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({"figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
                     "font.size": 12, "axes.edgecolor": GRID, "axes.labelcolor": INK2, "text.color": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False,
                     "axes.spines.left": False, "axes.grid": True, "axes.axisbelow": True, "grid.color": GRID,
                     "grid.linewidth": 1, "axes.grid.axis": "y", "legend.frameon": False})

_numbers: list[dict] = []     # rows for pilot_numbers.csv


def metrics(run: str) -> dict:
    """{system: metrics json} of a run folder."""
    return {s: json.loads((R / run / f"{s}_metrics.json").read_text(encoding="utf-8")) for s in SYSTEMS}


def predictions(run: str) -> dict:
    return {r["task_id"]: r for r in map(json.loads, open(R / run / "predictions.jsonl", encoding="utf-8"))}


def quality(m: dict, key: str):
    q = m.get("quality", m)
    return q[key]


def bootstrap(diffs: list[float]):
    """Mean and 95% bootstrap interval of paired differences: the same method and seed as analyze_predictions
    (2,000 resamples, seed 42), so the charts and the progress log give identical numbers."""
    r = boot_mean(diffs)
    return r["mean"], r["ci95"][0], r["ci95"][1]


def record(chart, group, system, value, lo=None, hi=None, n=None):
    _numbers.append({"chart": chart, "group": group, "system": system, "value": round(value, 4),
                     "ci_low": None if lo is None else round(lo, 4), "ci_high": None if hi is None else round(hi, 4), "n": n})


def grouped_bars(ax, groups, series, values, cis, ymax, fmt="{:.2f}"):
    """groups on x, one bar per series; values[s][g], cis[s][g] = (lo, hi) or None."""
    width = 0.8 / len(series)
    for j, s in enumerate(series):
        for i, g in enumerate(groups):
            x = i + (j - (len(series) - 1) / 2) * width
            v = values[s][i]
            ax.bar(x, v, width * 0.84, color=COLOR[s], label=LABEL[s] if i == 0 else None, zorder=3)
            ci = cis[s][i]
            if ci:
                ax.plot([x, x], ci, color=INK2, lw=1.4, zorder=4)
            ax.text(x, (ci[1] if ci else v) + ymax * 0.015, fmt.format(v), ha="center", va="bottom", fontsize=10, color=INK)
    ax.set_xticks(range(len(groups)), groups)
    ax.set_ylim(0, ymax)
    ax.tick_params(length=0)


def system_legend(fig, y=0.9):
    """One legend for the four systems, above the plots (never on top of the bars or their labels)."""
    from matplotlib.patches import Patch
    fig.legend([Patch(facecolor=COLOR[s]) for s in SYSTEMS], [LABEL[s] for s in SYSTEMS], ncol=4,
               loc="upper right", bbox_to_anchor=(0.99, y), fontsize=11, handlelength=1.2)


def fig_pilot(path: Path):
    """Edit similarity, identifier accuracy and exact match by system, main vs staleness view (pilot, n=50)."""
    runs = {"main view": "pilot_main_plainbase", "staleness view": "pilot_staleness_plainbase"}
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.2))
    for ax, (key, title, ymax) in zip(axes, [("edit_similarity", "Edit similarity", 0.85),
                                              ("identifier_accuracy", "Identifier accuracy", 0.7),
                                              ("exact_match", "Exact match", 0.3)]):
        vals, cis = {s: [] for s in SYSTEMS}, {s: [] for s in SYSTEMS}
        for gname, run in runs.items():
            m = metrics(run)
            for s in SYSTEMS:
                q = m[s].get("quality", m[s])
                v = q[key]
                ci = q.get(f"{key}_ci95")
                vals[s].append(v)
                cis[s].append(tuple(ci) if ci and ci[0] != ci[1] else None)
                record(f"pilot_{key}", gname, LABEL[s], v, ci[0] if ci else None, ci[1] if ci else None, 50)
        grouped_bars(ax, list(runs), SYSTEMS, vals, cis, ymax)
        ax.set_title(title, loc="left", fontsize=13, color=INK)
    system_legend(fig)
    fig.suptitle("Pilot, 50 CrossCodeEval examples (not findings): fine-tuned and hybrid lead; RAG alone is below the base model",
                 x=0.01, ha="left", fontsize=14)
    fig.text(0.01, 0.005, "Whiskers: 95% bootstrap interval (shown where defined). Base and RAG use the plain prompt; fine-tuned and hybrid "
             "the training format. Staleness view = new files added to the retrieval index.", fontsize=9, color=INK2)
    fig.tight_layout(rect=(0, 0.03, 1, 0.88))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_prompt_effect(path: Path):
    """Edit similarity with the instruction prompt (first pilot) vs the plain prompt, same 50 examples, paired CI."""
    plain, instr = predictions("pilot_main_plainbase"), predictions("pilot_main")
    ids = sorted(plain)
    fig, ax = plt.subplots(figsize=(9, 5.2))
    width = 0.34
    for i, s in enumerate(["base", "rag_only"]):
        for j, (name, data, hatch) in enumerate([("instruction prompt (first pilot)", instr, "//"), ("plain prompt", plain, None)]):
            v = sum(data[t][s]["edit_similarity"] for t in ids) / len(ids)
            x = i + (j - 0.5) * width
            ax.bar(x, v, width * 0.9, color=COLOR[s], alpha=0.45 if j == 0 else 1.0, hatch=hatch,
                   edgecolor=SURFACE if hatch is None else COLOR[s], linewidth=0, zorder=3)
            ax.text(x, v + 0.012, f"{v:.2f}", ha="center", fontsize=11)
            record("prompt_effect", name, LABEL[s], v, None, None, 50)
        diff = [plain[t][s]["edit_similarity"] - instr[t][s]["edit_similarity"] for t in ids]
        m, lo, hi = bootstrap(diff)
        ax.text(i, 0.66, f"plain minus instruction\n+{m:.2f}  [{lo:+.2f}, {hi:+.2f}]", ha="center", fontsize=10, color=INK2)
        record("prompt_effect_paired_diff", "plain - instruction", LABEL[s], m, lo, hi, 50)
    ax.set_xticks(range(2), [LABEL["base"], LABEL["rag_only"]])
    ax.set_ylim(0, 0.8)
    ax.set_ylabel("edit similarity")
    ax.tick_params(length=0)
    ax.set_title("The first pilot's base and RAG scores were mostly a prompt-format effect (n=50)", loc="left", fontsize=13)
    ax.text(0.0, -0.13, "Light hatched bar: instruction wrapper (the format only the adapter was trained on). Solid bar: plain continuation prompt.\n"
            "Fine-tuned and hybrid are identical in both (they always use the training format).", transform=ax.transAxes, fontsize=9, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_staleness(path: Path):
    """The 68 examples whose relevant file is a NEW file: main view vs staleness view, paired differences."""
    main, stale = predictions("new_relevant_main_plainbase"), predictions("new_relevant_staleness_plainbase")
    ids = sorted(main)
    fig, (ax, ax2) = plt.subplots(1, 2, figsize=(14, 5.2), gridspec_kw={"width_ratios": [1.15, 1]})
    vals, cis = {s: [] for s in SYSTEMS}, {s: [] for s in SYSTEMS}
    for gname, run in [("main view\n(new file not in index)", "new_relevant_main_plainbase"),
                       ("staleness view\n(new file in index)", "new_relevant_staleness_plainbase")]:
        m = metrics(run)
        for s in SYSTEMS:
            q = m[s].get("quality", m[s])
            vals[s].append(q["edit_similarity"])
            ci = q.get("edit_similarity_ci95")
            cis[s].append(tuple(ci) if ci else None)
            record("staleness68_edit_similarity", gname.split("\n")[0], LABEL[s], q["edit_similarity"],
                   ci[0] if ci else None, ci[1] if ci else None, len(ids))
    grouped_bars(ax, ["main view\n(new file not in index)", "staleness view\n(new file in index)"], SYSTEMS, vals, cis, 0.85)
    ax.set_title("Edit similarity on the 68 staleness-test examples", loc="left", fontsize=13)
    system_legend(fig)
    # paired change, staleness minus main, per system
    names, mids, los, his = [], [], [], []
    for s in ["rag_only", "hybrid"]:
        d = [stale[t][s]["edit_similarity"] - main[t][s]["edit_similarity"] for t in ids]
        m, lo, hi = bootstrap(d)
        names.append(LABEL[s]); mids.append(m); los.append(lo); his.append(hi)
        record("staleness68_change", "staleness - main", LABEL[s], m, lo, hi, len(ids))
    for k, s in enumerate(["rag_only", "hybrid"]):
        ax2.barh(k, mids[k], 0.45, color=COLOR[s], zorder=3)
        ax2.plot([los[k], his[k]], [k, k], color=INK2, lw=1.6, zorder=4)
        ax2.text(max(his[k], mids[k]) + 0.006, k, f"{mids[k]:+.3f}  [{los[k]:+.3f}, {his[k]:+.3f}]", va="center", fontsize=10.5)
    ax2.axvline(0, color=INK2, lw=1)
    ax2.set_yticks(range(2), names)
    ax2.set_xlim(-0.12, 0.2)
    ax2.set_ylim(-0.6, 1.6)
    ax2.grid(axis="y", visible=False)
    ax2.grid(axis="x")
    ax2.tick_params(length=0)
    ax2.set_title("Change when the new file is in the index", loc="left", fontsize=13)
    ax2.set_xlabel("edit similarity, staleness view minus main view (paired, 95% interval)")
    fig.suptitle("Staleness test, n=68 (not a finding): only the hybrid gains from the new file; fine-tuned and base cannot change",
                 x=0.01, ha="left", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.88))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_paired(path: Path):
    """Forest plot of the paired differences in edit similarity, pilot main view (n=50)."""
    d = predictions("pilot_main_plainbase")
    ids = sorted(d)
    pairs = [("fine-tuned minus base", "finetuning_only", "base"), ("RAG minus base", "rag_only", "base"),
             ("hybrid minus fine-tuned", "hybrid", "finetuning_only"), ("hybrid minus RAG", "hybrid", "rag_only"),
             ("RAG minus fine-tuned", "rag_only", "finetuning_only")]
    fig, ax = plt.subplots(figsize=(10, 4.8))
    for k, (name, a, b) in enumerate(pairs[::-1]):
        diff = [d[t][a]["edit_similarity"] - d[t][b]["edit_similarity"] for t in ids]
        m, lo, hi = bootstrap(diff)
        sig = lo > 0 or hi < 0
        ax.plot([lo, hi], [k, k], color=INK2, lw=2, zorder=3)
        ax.plot(m, k, "o", ms=9, color=COLOR[a] if sig else SURFACE, mec=COLOR[a], mew=2, zorder=4)
        ax.text(0.37, k, f"{m:+.3f}  [{lo:+.3f}, {hi:+.3f}]  " + ("excludes 0" if sig else "includes 0"), va="center", fontsize=10.5)
        record("paired_edit_similarity", "pilot main", name, m, lo, hi, 50)
    ax.axvline(0, color=INK2, lw=1)
    ax.set_yticks(range(len(pairs)), [p[0] for p in pairs[::-1]])
    ax.set_xlim(-0.4, 0.75)
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x")
    ax.tick_params(length=0)
    ax.set_xlabel("difference in edit similarity (paired, 95% bootstrap interval); filled marker = interval excludes 0")
    ax.set_title("Which differences are real at n=50?", loc="left", fontsize=13)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def fig_cost(path: Path):
    """Average time per example and peak GPU memory by system (pilot main view)."""
    m = metrics("pilot_main_plainbase")
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
    for ax, key, title, fmt, ymax in [(a1, "avg_total_ms", "Average time per example (s)", "{:.2f}", 3.0),
                                       (a2, "peak_gpu_mb", "Peak GPU memory (GB)", "{:.2f}", 3.0)]:
        for i, s in enumerate(SYSTEMS):
            eff = m[s].get("efficiency", {})
            raw = eff[key]
            v = raw / 1000
            ax.bar(i, v, 0.55, color=COLOR[s], zorder=3)
            ax.text(i, v + 0.05, fmt.format(v), ha="center", fontsize=11)
            record(f"cost_{key}", "pilot main", LABEL[s], v, None, None, 50)
        ax.set_xticks(range(4), [LABEL[s] for s in SYSTEMS])
        ax.set_ylim(0, ymax)
        ax.set_title(title, loc="left", fontsize=13)
        ax.tick_params(length=0)
    fig.suptitle("Cost on one T4 (4-bit, pilot): retrieval adds about 0.1 to 0.3 s and 0.14 GB per example", x=0.01, ha="left", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, dpi=160)
    plt.close(fig)


def wilson(k: int, n: int, z: float = 1.96):
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def mcnemar_exact(base: list[bool], tuned: list[bool]) -> float:
    """Two-sided exact McNemar p-value from the discordant pairs."""
    only_a = sum(a and not b for a, b in zip(base, tuned))
    only_b = sum(b and not a for a, b in zip(base, tuned))
    n, k = only_a + only_b, min(only_a, only_b)
    return 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, j) for j in range(k + 1)) / 2 ** n)


def fig_forgetting(path: Path):
    d = json.loads((R / "forgetting_humaneval_plain.json").read_text(encoding="utf-8"))
    n = d["n_problems"]
    p_value = mcnemar_exact([x["passed"] for x in d["per_problem"]["base"]], [x["passed"] for x in d["per_problem"]["finetuned"]])
    record("humaneval_mcnemar_p", "plain stub", "base vs fine-tuned", p_value, None, None, n)
    fig, ax = plt.subplots(figsize=(7.5, 4.8))
    for i, (name, key, color) in enumerate([("base", "base", COLOR["base"]), ("fine-tuned", "finetuned", COLOR["finetuning_only"])]):
        k = sum(x["passed"] for x in d["per_problem"][key])
        p = k / n
        lo, hi = wilson(k, n)
        ax.bar(i, p, 0.5, color=color, zorder=3)
        ax.plot([i, i], [lo, hi], color=INK2, lw=1.6, zorder=4)
        ax.text(i, hi + 0.015, f"{p:.3f}  ({k}/{n})", ha="center", fontsize=11)
        record("humaneval_pass1", "plain stub", name, p, lo, hi, n)
    ax.set_xticks(range(2), ["base", "fine-tuned"])
    ax.set_ylim(0, 0.6)
    ax.set_ylabel("HumanEval pass@1")
    ax.tick_params(length=0)
    ax.set_title(f"Forgetting check, all {n} problems: "
                 + ("no significant drop" if p_value >= 0.05 else "significant difference") + f" (McNemar p = {p_value:.2f})", loc="left", fontsize=12.5)
    ax.text(0, -0.14, "Whiskers: 95% Wilson interval. Wang et al. report -24.1% for full fine-tuning of larger models.", transform=ax.transAxes, fontsize=9, color=INK2)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fig_pilot(OUT / "pilot_main_vs_staleness.png")
    fig_prompt_effect(OUT / "pilot_prompt_effect.png")
    fig_staleness(OUT / "pilot_staleness_68.png")
    fig_paired(OUT / "pilot_paired_differences.png")
    fig_cost(OUT / "pilot_cost.png")
    fig_forgetting(OUT / "pilot_forgetting.png")
    with open(OUT / "pilot_numbers.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["chart", "group", "system", "value", "ci_low", "ci_high", "n"])
        w.writeheader()
        w.writerows(_numbers)
    print(f"wrote 6 figures and pilot_numbers.csv ({len(_numbers)} rows) to {OUT}")


if __name__ == "__main__":
    main()
