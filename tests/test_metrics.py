"""
tests/test_metrics.py
---------------------
Basic sanity checks for the evaluation metrics.
"""

# allow running without pytest installed
try:
    from pytest import approx as pytest_approx
except ImportError:
    pytest_approx = lambda x: x

from src.evaluation.metrics import (
    exact_match,
    edit_similarity,
    identifier_accuracy,
    precision_at_k,
    recall_at_k,
    mean_reciprocal_rank,
    evaluate_retrieval,
)


def test_exact_match_positive():
    assert exact_match("return x", "return x") == 1.0


def test_exact_match_negative():
    assert exact_match("return x", "return y") == 0.0


def test_edit_similarity_identical():
    assert edit_similarity("hello", "hello") == 1.0


def test_edit_similarity_partial():
    score = edit_similarity("return x", "return y")
    assert 0.0 < score < 1.0


def test_identifier_accuracy_full():
    assert identifier_accuracy("user = UserFactory()", "user = UserFactory()") == 1.0


def test_precision_at_k():
    retrieved = ["a.py", "b.py", "c.py"]
    relevant = ["a.py", "c.py"]
    assert precision_at_k(retrieved, relevant, k=3) == pytest_approx(2 / 3)


def test_recall_at_k():
    retrieved = ["a.py", "b.py"]
    relevant = ["a.py", "c.py"]
    assert recall_at_k(retrieved, relevant, k=2) == 0.5


def test_mrr_first_hit():
    assert mean_reciprocal_rank(["a.py", "b.py", "c.py"], ["a.py"]) == 1.0


def test_mrr_second_hit():
    assert mean_reciprocal_rank(["b.py", "a.py", "c.py"], ["a.py"]) == pytest_approx(0.5)


def test_mrr_no_hit():
    assert mean_reciprocal_rank(["b.py", "c.py"], ["a.py"]) == 0.0


def test_evaluate_retrieval_aggregate():
    retrieved_list = [["a.py", "b.py", "c.py"], ["x.py", "y.py"]]
    relevant_list  = [["a.py", "c.py"],          ["x.py"]]
    result = evaluate_retrieval(retrieved_list, relevant_list, k=3, k_values=[1, 3])
    assert "mrr" in result
    assert "precision@3" in result
    assert "recall@3" in result
    assert result["n_queries"] == 2

