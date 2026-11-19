"""
src/evaluation/metrics.py
--------------------------
Evaluation metrics for the comparative study:

  Code Completion Quality
  -----------------------
  - Exact Match (EM)
  - Edit Similarity  (Levenshtein)
  - Identifier Accuracy
  - CodeBLEU          (requires the `codebleu` package; raises if missing)

  Retrieval Quality
  -----------------
  - Precision@K
  - Recall@K

  Efficiency
  ----------
  See src/evaluation/latency.py
"""

from __future__ import annotations
from typing import List, Set
import re

try:
    from Levenshtein import ratio as lev_ratio
except ImportError:
    from difflib import SequenceMatcher
    def lev_ratio(a, b):
        return SequenceMatcher(None, a, b).ratio()


# ── Code Completion Metrics ───────────────────────────────────────────────────

def exact_match(prediction: str, reference: str) -> float:
    return float(prediction.strip() == reference.strip())


def edit_similarity(prediction: str, reference: str) -> float:
    return lev_ratio(prediction.strip(), reference.strip())


def _extract_identifiers(code: str) -> Set[str]:
    """Simple regex-based identifier extractor (no AST required)."""
    tokens = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", code)
    keywords = {
        "def", "class", "return", "import", "from", "if", "else",
        "for", "while", "in", "not", "and", "or", "True", "False", "None",
        "try", "except", "with", "as", "pass", "raise", "lambda",
    }
    return set(tokens) - keywords


def identifier_accuracy(prediction: str, reference: str) -> float:
    pred_ids = _extract_identifiers(prediction)
    ref_ids = _extract_identifiers(reference)
    if not ref_ids:
        return 1.0
    return len(pred_ids & ref_ids) / len(ref_ids)


def code_bleu(predictions: List[str], references: List[str]) -> float:
    """
    CodeBLEU (corpus level) from the `codebleu` package (pip install codebleu tree-sitter-python).
    Raises if the package is missing or fails: a missing metric must never show up as 0.0.
    Note: the metric needs parseable code, so one-line fragments can score low on its
    syntax and data-flow parts; report that when quoting it.
    """
    try:
        from codebleu import calc_codebleu
    except ImportError as exc:
        raise ImportError(
            "CodeBLEU needs the 'codebleu' package: pip install codebleu tree-sitter-python "
            "(or run with --skip-codebleu to leave it out of the results)."
        ) from exc
    result = calc_codebleu(references=list(references), predictions=list(predictions), lang="python")
    return float(result["codebleu"])


def bootstrap_ci(values, n_resamples: int = 1000, seed: int = 42, level: float = 0.95) -> tuple:
    """Percentile bootstrap confidence interval for the mean of per-example scores."""
    import numpy as np
    values = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(values), size=(n_resamples, len(values)))
    means = values[idx].mean(axis=1)
    tail = (1 - level) / 2 * 100
    return float(np.percentile(means, tail)), float(np.percentile(means, 100 - tail))


# ── Retrieval Quality Metrics ─────────────────────────────────────────────────

def precision_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    retrieved_k = retrieved[:k]
    if not retrieved_k:
        return 0.0
    return len(set(retrieved_k) & set(relevant)) / k


def recall_at_k(retrieved: List[str], relevant: List[str], k: int) -> float:
    if not relevant:
        return 0.0
    retrieved_k = retrieved[:k]
    return len(set(retrieved_k) & set(relevant)) / len(relevant)


def mean_reciprocal_rank(retrieved: List[str], relevant: List[str]) -> float:
    """
    MRR — Mean Reciprocal Rank.
    Returns the reciprocal of the rank of the first relevant result.
    A score of 1.0 means the first retrieved item was relevant.
    A score of 0.0 means nothing relevant was retrieved.
    """
    relevant_set = set(relevant)
    for rank, item in enumerate(retrieved, start=1):
        if item in relevant_set:
            return 1.0 / rank
    return 0.0


def evaluate_retrieval(
    retrieved_list: List[List[str]],
    relevant_list: List[List[str]],
    k: int = 5,
    k_values: List[int] = None,
) -> dict:
    """
    Aggregate retrieval metrics over a list of queries.

    Parameters
    ----------
    retrieved_list : list of retrieved file/chunk IDs per query
    relevant_list  : list of ground-truth relevant file/chunk IDs per query
    k              : primary K for Precision@K and Recall@K
    k_values       : optional list of K values for ablation sweep (e.g. [1,3,5,10])
    """
    if k_values is None:
        k_values = [k]

    prec_scores = {kv: [] for kv in k_values}
    rec_scores  = {kv: [] for kv in k_values}
    mrr_scores  = []

    for retrieved, relevant in zip(retrieved_list, relevant_list):
        for kv in k_values:
            prec_scores[kv].append(precision_at_k(retrieved, relevant, kv))
            rec_scores[kv].append(recall_at_k(retrieved, relevant, kv))
        mrr_scores.append(mean_reciprocal_rank(retrieved, relevant))

    result = {"mrr": round(sum(mrr_scores) / len(mrr_scores), 4)}
    for kv in k_values:
        result[f"precision@{kv}"] = round(sum(prec_scores[kv]) / len(prec_scores[kv]), 4)
        result[f"recall@{kv}"]    = round(sum(rec_scores[kv])  / len(rec_scores[kv]),  4)

    result["n_queries"] = len(retrieved_list)
    return result


# ── Aggregate Completion Evaluation ──────────────────────────────────────────

def evaluate_completion(predictions: List[str], references: List[str],
                        include_codebleu: bool = True) -> dict:
    """
    Returns all code-quality metrics for a list of prediction/reference pairs.
    Used to compare RAG-only, Fine-Tuning-only, and Hybrid systems.
    With include_codebleu=False the CodeBLEU entry is None (not 0.0).
    """
    em_scores, es_scores, ia_scores = [], [], []
    for pred, ref in zip(predictions, references):
        em_scores.append(exact_match(pred, ref))
        es_scores.append(edit_similarity(pred, ref))
        ia_scores.append(identifier_accuracy(pred, ref))

    cb_score = code_bleu(predictions, references) if include_codebleu else None

    return {
        "exact_match":         round(sum(em_scores) / len(em_scores), 4),
        "edit_similarity":     round(sum(es_scores) / len(es_scores), 4),
        "identifier_accuracy": round(sum(ia_scores) / len(ia_scores), 4),
        "code_bleu":           None if cb_score is None else round(cb_score, 4),
        "exact_match_ci95":    [round(v, 4) for v in bootstrap_ci(em_scores)],
        "edit_similarity_ci95": [round(v, 4) for v in bootstrap_ci(es_scores)],
        "n_samples":           len(predictions),
    }
