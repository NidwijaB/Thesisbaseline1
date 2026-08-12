"""
experiments/run_comparison.py
------------------------------
End-to-end orchestration script for the comparative study.

Runs all three systems on the same benchmark split and produces:
  - results/<system>_metrics.json        (per-system)
  - results/comparison_summary.json      (side-by-side JSON)
  - results/comparison_summary.md        (Markdown table for thesis)

Usage
-----
python experiments/run_comparison.py \
    --benchmark data/processed/test.jsonl \
    --config    configs/config.yaml \
    --ft-model  experiments/finetuned_model

Research Questions addressed
-----------------------------
  RQ1 — Does retrieval improve over standalone fine-tuning?
  RQ2 — Does fine-tuning improve use of retrieved context?
  RQ3 — Does the hybrid outperform both individual baselines?
  RQ4 — What retrieval strategy best supports enterprise completion?
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

from src.utils.config import load_config
from src.utils.logger import get_logger
from src.evaluation.evaluator import run_evaluation, compare_systems

logger = get_logger("run_comparison")


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_benchmark(path: str):
    return [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]


def build_retriever(cfg):
    from src.retrieval.embedder import CodeEmbedder
    from src.retrieval.vector_store import FAISSVectorStore
    from src.retrieval.retriever import Retriever

    embedder = CodeEmbedder(model_name=cfg.retrieval.embedding_model)
    store = FAISSVectorStore.load(cfg.paths.embeddings)
    return Retriever(embedder, store, top_k=cfg.retrieval.top_k)


def build_generator(model_path: str, device: str):
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch

    tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
    model = AutoModelForCausalLM.from_pretrained(
        model_path, trust_remote_code=True, device_map="auto"
    )
    model.eval()

    def generate(input_text: str, context: str | None = None, max_new_tokens: int = 128) -> str:
        prompt = input_text if context is None else f"# Context:\n{context}\n\n{input_text}"
        inputs = tokenizer(prompt, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id,
            )
        gen = out[0][inputs["input_ids"].shape[1]:]
        return tokenizer.decode(gen, skip_special_tokens=True)

    return generate


# ── Per-system runners ────────────────────────────────────────────────────────

def run_rag_only(examples, cfg, ft_model_path):
    logger.info("=== System 1/3: RAG-Only ===")
    from src.evaluation.latency import measure_system

    retriever = build_retriever(cfg)
    generate  = build_generator(cfg.llm.model, cfg.project.device)

    retrieve_fn = retriever.build_context_string
    gen_fn      = lambda inp, ctx: generate(inp, context=ctx)

    latency = measure_system("rag_only", examples, gen_fn, retrieve_fn=retrieve_fn)
    preds   = [gen_fn(ex["input"], retrieve_fn(ex["input"])) for ex in examples]
    refs    = [ex["output"] for ex in examples]

    # TODO: Populate retrieved_list and relevant_list for retrieval quality metrics.
    # retrieved_list: for each example, the list of file paths the retriever fetched.
    #   e.g. [[chunk.file_path for chunk in retriever.retrieve(ex["input"])] for ex in examples]
    # relevant_list: for each example, the ground-truth relevant file paths from the benchmark.
    #   e.g. [ex["relevant_files"] for ex in examples]  ← field name depends on your dataset
    retrieved_list = None  # TODO: replace with actual retrieved file IDs
    relevant_list  = None  # TODO: replace with ground-truth relevant file IDs from benchmark

    return run_evaluation(
        "rag_only", preds, refs,
        latency=latency,
        retrieved_list=retrieved_list,
        relevant_list=relevant_list,
        k_values=cfg.retrieval.top_k_values,
    ), latency


def run_finetuning_only(examples, cfg, ft_model_path):
    logger.info("=== System 2/3: Fine-Tuning-Only ===")
    from src.evaluation.latency import measure_system

    generate = build_generator(ft_model_path, cfg.project.device)
    gen_fn   = lambda inp, ctx: generate(inp, context=None)

    latency = measure_system("finetuning_only", examples, gen_fn, retrieve_fn=None)
    preds   = [gen_fn(ex["input"], None) for ex in examples]
    refs    = [ex["output"] for ex in examples]
    # No retrieval for Fine-Tuning-Only — retrieved_list/relevant_list intentionally None
    return run_evaluation("finetuning_only", preds, refs, latency=latency), latency


def run_hybrid(examples, cfg, ft_model_path):
    logger.info("=== System 3/3: Hybrid RAG + Fine-Tuning ===")
    from src.evaluation.latency import measure_system

    retriever = build_retriever(cfg)
    generate  = build_generator(ft_model_path, cfg.project.device)

    retrieve_fn = retriever.build_context_string
    gen_fn      = lambda inp, ctx: generate(inp, context=ctx)

    latency = measure_system("hybrid", examples, gen_fn, retrieve_fn=retrieve_fn)
    preds   = [gen_fn(ex["input"], retrieve_fn(ex["input"])) for ex in examples]
    refs    = [ex["output"] for ex in examples]

    # TODO: Populate retrieved_list and relevant_list for retrieval quality metrics.
    # retrieved_list: for each example, the list of file paths the retriever fetched.
    #   e.g. [[chunk.file_path for chunk in retriever.retrieve(ex["input"])] for ex in examples]
    # relevant_list: for each example, the ground-truth relevant file paths from the benchmark.
    #   e.g. [ex["relevant_files"] for ex in examples]  ← field name depends on your dataset
    retrieved_list = None  # TODO: replace with actual retrieved file IDs
    relevant_list  = None  # TODO: replace with ground-truth relevant file IDs from benchmark

    return run_evaluation(
        "hybrid", preds, refs,
        latency=latency,
        retrieved_list=retrieved_list,
        relevant_list=relevant_list,
        k_values=cfg.retrieval.top_k_values,
    ), latency


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Comparative Study: Fine-Tuning vs RAG vs Hybrid — Enterprise Code Completion"
    )
    parser.add_argument("--benchmark",  required=True,  help="Path to test.jsonl")
    parser.add_argument("--ft-model",   required=True,  help="Path to fine-tuned model directory")
    parser.add_argument("--config",     default="configs/config.yaml")
    parser.add_argument("--output-dir", default="results")
    parser.add_argument("--systems",    nargs="+",
                        choices=["rag_only", "finetuning_only", "hybrid"],
                        default=["rag_only", "finetuning_only", "hybrid"],
                        help="Which systems to run (default: all three)")
    args = parser.parse_args()

    cfg      = load_config(args.config)
    examples = load_benchmark(args.benchmark)
    logger.info(f"Benchmark: {args.benchmark} ({len(examples)} examples)")

    all_results = {}

    if "rag_only" in args.systems:
        result, _ = run_rag_only(examples, cfg, args.ft_model)
        all_results["rag_only"] = result

    if "finetuning_only" in args.systems:
        result, _ = run_finetuning_only(examples, cfg, args.ft_model)
        all_results["finetuning_only"] = result

    if "hybrid" in args.systems:
        result, _ = run_hybrid(examples, cfg, args.ft_model)
        all_results["hybrid"] = result

    if len(all_results) > 1:
        compare_systems(all_results, output_dir=args.output_dir)
        logger.info("Comparison complete. Check results/comparison_summary.md")


if __name__ == "__main__":
    main()

