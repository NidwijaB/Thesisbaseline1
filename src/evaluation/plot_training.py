"""
src/evaluation/plot_training.py
--------------------------------
Plots the training and validation loss from a finished or interrupted run.

The Hugging Face Trainer writes trainer_state.json into every checkpoint folder
(and the latest one lives next to the adapter on Drive). Give this script either that
file or a folder that contains checkpoint-* folders; it picks the latest checkpoint.

    python -m src.evaluation.plot_training --run experiments/finetuned_model/crosscodeeval
    python -m src.evaluation.plot_training --run <path>/trainer_state.json --output results/figures/loss.png

Validation loss here is NOT file-held-out (progress log Entries 8 and 11), so it is
optimistic: use it to see that training behaves, not as a measure of generalisation.
"""

from __future__ import annotations
import argparse
import json
import re
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def find_state(run: Path) -> Path:
    if run.is_file():
        return run
    checkpoints = sorted((p for p in run.glob("checkpoint-*") if p.is_dir()),
                         key=lambda p: int(re.search(r"(\d+)$", p.name).group(1)))
    for folder in reversed(checkpoints):
        state = folder / "trainer_state.json"
        if state.exists():
            return state
    direct = run / "trainer_state.json"
    if direct.exists():
        return direct
    raise SystemExit(f"no trainer_state.json found under {run}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="trainer_state.json or a run folder with checkpoint-*")
    parser.add_argument("--output", default="results/figures/training_loss.png")
    args = parser.parse_args()

    state_path = find_state(Path(args.run))
    state = json.loads(state_path.read_text(encoding="utf-8"))
    log = state.get("log_history", [])
    train = [(e["step"], e["loss"]) for e in log if "loss" in e and "eval_loss" not in e]
    evals = [(e["step"], e["eval_loss"]) for e in log if "eval_loss" in e]
    if not train:
        raise SystemExit("no training loss entries in the log yet")

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    ax.plot(*zip(*train), color="#1f6fb4", label="training loss")
    if evals:
        ax.plot(*zip(*evals), color="#e08a1e", marker="o", label="validation loss (not file-held-out)")
    ax.set_xlabel("optimizer step")
    ax.set_ylabel("loss")
    ax.set_title(f"Fine-tuning loss ({state_path.parent.name}, {state.get('global_step', '?')} steps)")
    ax.legend()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out, dpi=200)
    print(f"Saved {out} ({len(train)} training points, {len(evals)} validation points)")


if __name__ == "__main__":
    main()
