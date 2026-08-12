"""
tests/test_metrics.py
---------------------
Basic sanity checks for the evaluation metrics.
"""

from src.evaluation.metrics import (
    exact_match,
    edit_similarity,
    identifier_accuracy,
    precision_at_k,
    recall_at_k,
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


# allow running without pytest installed
try:
    from pytest import approx as pytest_approx
except ImportError:
    pytest_approx = lambda x: x

