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

from src.evaluation.metrics import evaluate_completion, evaluate_retrieval
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
    retrieved_list: List[List[str]] | None = None,
    relevant_list: List[List[str]] | None = None,
    k_values: List[int] = None,
) -> Dict:
    """Evaluate one system and persist results.

    Parameters
    ----------
    retrieved_list : per-query list of retrieved chunk/file IDs (RAG & Hybrid only)
    relevant_list  : per-query list of ground-truth relevant chunk/file IDs
    k_values       : K values for Precision@K / Recall@K sweep, e.g. [1, 3, 5, 10]
    """
    assert system_name in SYSTEM_NAMES, f"system_name must be one of {SYSTEM_NAMES}"

    metrics = evaluate_completion(predictions, references)

    result = {
        "system": system_name,
        **metrics,
    }

    # Retrieval quality — only applicable for RAG-only and Hybrid
    if retrieved_list is not None and relevant_list is not None:
        ret_metrics = evaluate_retrieval(
            retrieved_list, relevant_list,
            k=5,
            k_values=k_values or [1, 3, 5, 10],
        )
        result["retrieval"] = ret_metrics
        logger.info(f"[{system_name}] retrieval metrics: {ret_metrics}")

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
    eff_cols = ["retrieval_latency_ms", "inference_latency_ms", "total_latency_ms", "peak_gpu_mb", "peak_cpu_ram_mb"]

    lines = [
        "# Comparative Study Results\n",
        "## Code Completion Quality\n",
        "| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |",
        "|--------|------------|----------|----------------|----------|",
    ]
    for sys, res in results.items():
        row = [sys] + [str(res.get(c, "-")) for c in cols]
        lines.append("| " + " | ".join(row) + " |")

    # Retrieval quality — only for systems that have retrieval data
    lines += [
        "\n## Retrieval Quality (RAG-Only & Hybrid)\n",
        "| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |",
        "|--------|-----|-----|-----|-----|------|-----|-----|-----|------|",
    ]
    for sys, res in results.items():
        ret = res.get("retrieval")
        if ret:
            row = [
                sys,
                str(ret.get("mrr", "-")),
                str(ret.get("precision@1", "-")),
                str(ret.get("precision@3", "-")),
                str(ret.get("precision@5", "-")),
                str(ret.get("precision@10", "-")),
                str(ret.get("recall@1", "-")),
                str(ret.get("recall@3", "-")),
                str(ret.get("recall@5", "-")),
                str(ret.get("recall@10", "-")),
            ]
        else:
            row = [sys] + ["N/A"] * 9  # Fine-Tuning-Only has no retrieval
        lines.append("| " + " | ".join(row) + " |")

    lines += [
        "\n## Efficiency\n",
        "| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |",
        "|--------|---------------|----------------|------------|--------------|--------------|",
    ]
    for sys, res in results.items():
        eff = res.get("efficiency", {})
        row = [sys] + [str(eff.get(c, "-")) for c in eff_cols]
        lines.append("| " + " | ".join(row) + " |")

    md_path = out / "comparison_summary.md"
    md_path.write_text("\n".join(lines) + "\n")
    logger.info(f"Markdown comparison → {md_path}")
