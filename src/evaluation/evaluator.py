"""
src/evaluation/evaluator.py
----------------------------
Comparative evaluator — runs all three systems (RAG-only, Fine-Tuning-only,
Hybrid) on the same benchmark and writes side-by-side metric results to results/.

This is the core of the comparative study:
  "Comparative Study of Fine-Tuning, RAG, and Hybrid Models
   for Code Completion in Enterprise Repositories"
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import List, Dict

from src.evaluation.metrics import evaluate_completion
from src.evaluation.latency import LatencyRecord
from src.utils.logger import get_logger

logger = get_logger(__name__)

SYSTEM_NAMES = ("rag_only", "finetuning_only", "hybrid")


def run_evaluation(
    system_name: str,
    predictions: List[str],
    references: List[str],
    latency: LatencyRecord | None = None,
    output_dir: str = "results",
) -> Dict:
    """Evaluate one system and persist results."""
    assert system_name in SYSTEM_NAMES, f"system_name must be one of {SYSTEM_NAMES}"

    metrics = evaluate_completion(predictions, references)

    result = {
        "system": system_name,
        **metrics,
    }
    if latency is not None:
        result["efficiency"] = latency.to_dict()

    logger.info(f"[{system_name}] quality metrics: { {k: v for k, v in metrics.items()} }")
    if latency:
        logger.info(f"[{system_name}] efficiency: {latency.to_dict()}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    result_path = out / f"{system_name}_metrics.json"
    result_path.write_text(json.dumps(result, indent=2))
    logger.info(f"Results saved → {result_path}")
    return result


def compare_systems(results: Dict[str, Dict], output_dir: str = "results") -> None:
    """
    Write a combined comparison table (JSON + Markdown) across all evaluated systems.
    Call this after run_evaluation() for each system.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # ── JSON summary ──────────────────────────────────────────────────────────
    combined_path = out / "comparison_summary.json"
    combined_path.write_text(json.dumps(results, indent=2))
    logger.info(f"Combined results → {combined_path}")

    # ── Markdown table ────────────────────────────────────────────────────────
    cols = ["exact_match", "edit_similarity", "identifier_accuracy", "code_bleu"]
    eff_cols = ["retrieval_latency_ms", "inference_latency_ms", "total_latency_ms", "peak_gpu_mb"]

    lines = [
        "# Comparative Study Results\n",
        "## Code Completion Quality\n",
        "| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |",
        "|--------|------------|----------|----------------|----------|",
    ]
    for sys, res in results.items():
        row = [sys] + [str(res.get(c, "-")) for c in cols]
        lines.append("| " + " | ".join(row) + " |")

    lines += [
        "\n## Efficiency\n",
        "| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) |",
        "|--------|---------------|----------------|------------|--------------|",
    ]
    for sys, res in results.items():
        eff = res.get("efficiency", {})
        row = [sys] + [str(eff.get(c, "-")) for c in eff_cols]
        lines.append("| " + " | ".join(row) + " |")

    md_path = out / "comparison_summary.md"
    md_path.write_text("\n".join(lines) + "\n")
    logger.info(f"Markdown comparison → {md_path}")
