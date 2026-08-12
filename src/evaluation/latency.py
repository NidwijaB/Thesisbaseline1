"""
src/evaluation/latency.py
--------------------------
Efficiency measurement utilities for the comparative study.

Measures per-system:
  - Retrieval latency (ms)          — RAG-only / Hybrid only
  - Inference latency (ms)
  - End-to-end latency (ms)
  - Peak GPU memory (MB)            — if CUDA available
"""

from __future__ import annotations
import time
import contextlib
from dataclasses import dataclass
from typing import Optional

try:
    import torch
    _TORCH_AVAILABLE = True
except ImportError:
    torch = None  # type: ignore[assignment]
    _TORCH_AVAILABLE = False

try:
    import psutil
    _PSUTIL_AVAILABLE = True
except ImportError:
    psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False


@dataclass
class LatencyRecord:
    system: str
    retrieval_ms: float = 0.0
    inference_ms: float = 0.0
    total_ms: float = 0.0
    peak_gpu_mb: float = 0.0
    peak_cpu_ram_mb: float = 0.0
    n_samples: int = 0

    def to_dict(self) -> dict:
        return {
            "system": self.system,
            "retrieval_latency_ms":  round(self.retrieval_ms, 2),
            "inference_latency_ms":  round(self.inference_ms, 2),
            "total_latency_ms":      round(self.total_ms, 2),
            "avg_total_ms":          round(self.total_ms / max(self.n_samples, 1), 2),
            "peak_gpu_mb":           round(self.peak_gpu_mb, 2),
            "peak_cpu_ram_mb":       round(self.peak_cpu_ram_mb, 2),
        }


@contextlib.contextmanager
def timer():
    """Context manager that yields elapsed milliseconds."""
    start = time.perf_counter()
    result = {"ms": 0.0}
    yield result
    result["ms"] = (time.perf_counter() - start) * 1000


def reset_gpu_memory_stats():
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def peak_gpu_memory_mb() -> float:
    if _TORCH_AVAILABLE and torch.cuda.is_available():
        return torch.cuda.max_memory_allocated() / 1024 ** 2
    return 0.0


def current_cpu_ram_mb() -> float:
    """Returns current process RSS memory in MB."""
    if _PSUTIL_AVAILABLE:
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 ** 2
    return 0.0


def measure_system(
    system_name: str,
    examples: list,
    generate_fn,               # callable(input_text, context) -> str
    retrieve_fn=None,          # callable(input_text) -> context str (RAG / Hybrid only)
) -> LatencyRecord:
    """
    Runs all examples through the given system, recording latency and memory at each step.

    Parameters
    ----------
    system_name : str
    examples    : list of dicts with at least {"input": str}
    generate_fn : callable(input_text: str, context: str | None) -> str
    retrieve_fn : optional callable(input_text: str) -> str
    """
    record = LatencyRecord(system=system_name, n_samples=len(examples))
    reset_gpu_memory_stats()
    peak_ram = 0.0

    for ex in examples:
        context: Optional[str] = None

        if retrieve_fn is not None:
            with timer() as t:
                context = retrieve_fn(ex["input"])
            record.retrieval_ms += t["ms"]

        with timer() as t:
            generate_fn(ex["input"], context)
        record.inference_ms += t["ms"]

        # track peak CPU RAM across all samples
        current_ram = current_cpu_ram_mb()
        if current_ram > peak_ram:
            peak_ram = current_ram

    record.total_ms = record.retrieval_ms + record.inference_ms
    record.peak_gpu_mb = peak_gpu_memory_mb()
    record.peak_cpu_ram_mb = peak_ram
    return record

