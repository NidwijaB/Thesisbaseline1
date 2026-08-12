"""
src/evaluation/metrics.py
--------------------------
Evaluation metrics for the comparative study:

  Code Completion Quality
  -----------------------
  - Exact Match (EM)
  - Edit Similarity  (Levenshtein)
  - Identifier Accuracy
  - CodeBLEU          (requires `evaluate` library)

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
    CodeBLEU via the HuggingFace `evaluate` library.
    Falls back to 0.0 if the metric is unavailable.
    """
    try:
        import evaluate as hf_evaluate
        metric = hf_evaluate.load("code_bleu", lang="python")
        result = metric.compute(predictions=predictions, references=[[r] for r in references])
        return float(result["code_bleu"])
    except Exception:
        # Graceful fallback — install `evaluate` and `sacrebleu` for full support
        return 0.0


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

def evaluate_completion(predictions: List[str], references: List[str]) -> dict:
    """
    Returns all code-quality metrics for a list of prediction/reference pairs.
    Used to compare RAG-only, Fine-Tuning-only, and Hybrid systems.
    """
    em_scores, es_scores, ia_scores = [], [], []
    for pred, ref in zip(predictions, references):
        em_scores.append(exact_match(pred, ref))
        es_scores.append(edit_similarity(pred, ref))
        ia_scores.append(identifier_accuracy(pred, ref))

    cb_score = code_bleu(predictions, references)

    return {
        "exact_match":         round(sum(em_scores) / len(em_scores), 4),
        "edit_similarity":     round(sum(es_scores) / len(es_scores), 4),
        "identifier_accuracy": round(sum(ia_scores) / len(ia_scores), 4),
        "code_bleu":           round(cb_score, 4),
        "n_samples":           len(predictions),
    }
