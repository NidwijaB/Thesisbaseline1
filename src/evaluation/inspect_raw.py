"""
src/evaluation/inspect_raw.py
------------------------------
Reads a predictions.jsonl written with `run_comparison --save-raw` and prints, per system, why generation
stopped (eos / newline / max_tokens) and the examples whose first line is empty or very short, with the raw
completion (special tokens shown). Used to find out why RAG answers are sometimes empty or cut off
(progress log Entry 41). No GPU needed.

    python -m src.evaluation.inspect_raw results/pilot_main_plainbase_raw/predictions.jsonl
"""

from __future__ import annotations
import argparse
import json
from collections import Counter

SYSTEMS = ("base", "rag_only", "finetuning_only", "hybrid")


def summarize(rows: list[dict], short_chars: int = 5) -> dict:
    out = {}
    for system in SYSTEMS:
        have = [r[system] for r in rows if system in r and "stop_reason" in r[system]]
        if not have:
            continue
        short = [(r["task_id"], r["reference"], r[system]) for r in rows
                 if system in r and "stop_reason" in r[system] and len(r[system]["prediction"].strip()) < short_chars]
        out[system] = {"n": len(have), "stop_reasons": dict(Counter(x["stop_reason"] for x in have)),
                       "empty_or_short": len(short), "short_examples": short,
                       "median_new_tokens": sorted(x["n_new_tokens"] for x in have)[len(have) // 2]}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("predictions")
    ap.add_argument("--show", type=int, default=6, help="how many short examples to print per system")
    args = ap.parse_args()
    rows = [json.loads(line) for line in open(args.predictions, encoding="utf-8")]
    summary = summarize(rows)
    if not summary:
        raise SystemExit("no raw diagnostics found: run run_comparison with --save-raw")
    for system, s in summary.items():
        print(f"\n{system}: {s['n']} answers, stop reasons {s['stop_reasons']}, median new tokens "
              f"{s['median_new_tokens']}, empty or under 5 characters: {s['empty_or_short']}")
        for task_id, reference, r in s["short_examples"][:args.show]:
            print(f"   {task_id} | REF {reference!r:.50} | first line {r['prediction']!r} | "
                  f"stop {r['stop_reason']}, {r['n_new_tokens']} tokens | raw {r['raw']!r:.120}")


if __name__ == "__main__":
    main()
