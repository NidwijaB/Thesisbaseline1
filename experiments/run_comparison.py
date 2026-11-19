"""
experiments/run_comparison.py
------------------------------
End-to-end comparison of the systems on CrossCodeEval TEST examples (plan Section 9, step 5 for
the pilot; step 7 for the full TEST set):

  base    frozen model, no retrieval, no adapter          (reference row, not one of the three)
  rag     System A: frozen model + retrieved chunks
  ft      System B: LoRA adapter, no retrieval
  hybrid  System C: LoRA adapter + retrieved chunks

One model is loaded once; base and rag run with the adapter switched off. All four use the shared
prompt (src/prompting.py) and the same greedy one-line generation (src/generation.py). Predictions
are cut to the first line before scoring.

Examples: --subset pilot (the 50 ids in data/processed/crosscodeeval/pilot_ids.json) or
--subset test (all TEST examples). Retrieval metrics use the A3 relevance rule for the chosen
--view (main = BASE pool, staleness = BASE + NEW pool); examples without a relevant file there
are left out of the retrieval metrics but still scored on completion.

Outputs in --output-dir (default results/<subset>_<view>):
  <system>_metrics.json, comparison_summary.{json,md}, predictions.jsonl (one row per example,
  all systems, retrieved files, hit flag) for hit-vs-miss analysis and bootstrap tests.
Memory note: all four systems share one process and the adapter stays loaded, so peak GPU memory
is not an independent per-system measurement; report it as such or run systems separately.

Run from the project root, for example:
    python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
"""

from __future__ import annotations
import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

from datasets import load_from_disk

from src.evaluation.evaluator import compare_systems, run_evaluation
from src.evaluation.latency import (LatencyRecord, current_cpu_ram_mb, peak_gpu_memory_mb,
                                    reset_gpu_memory_stats)
from src.evaluation.metrics import edit_similarity, exact_match, mean_reciprocal_rank
from src.generation import complete, load_model
from src.prompting import build_prompt, retrieval_query
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("run_comparison")

SPLIT_DIR = Path("data/processed/crosscodeeval")
INDEX_DIR = Path("data/embeddings/crosscodeeval")
DATASET_DIR = Path("data/crosscodeeval/python")
VIEWS = {"main": {"base"}, "staleness": {"base", "new"}}
# system name used in results files -> (uses adapter, uses retrieval)
SYSTEMS = {"base": (False, False), "rag_only": (False, True),
           "finetuning_only": (True, False), "hybrid": (True, True)}


def load_examples(subset: str, limit: int | None):
    """Raw CrossCodeEval rows for the chosen TEST examples, in a fixed order."""
    split = {e["task_id"]: e["split"]
             for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))}
    if subset == "pilot":
        wanted = set(json.loads((SPLIT_DIR / "pilot_ids.json").read_text(encoding="utf-8")))
    else:
        wanted = {t for t, s in split.items() if s == "test"}
    rows = [ex for ex in load_from_disk(str(DATASET_DIR))["train"] if ex["metadata"]["task_id"] in wanted]
    assert all(split[ex["metadata"]["task_id"]] == "test" for ex in rows), "non-TEST example selected"
    rows.sort(key=lambda ex: ex["metadata"]["task_id"])
    if limit:
        rows = rows[:limit]
    return rows


def distinct_files(chunks) -> list[str]:
    return list(dict.fromkeys(c.file_path for c in chunks))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", help="LoRA adapter folder (needed for finetuning_only and hybrid)")
    ap.add_argument("--subset", choices=["pilot", "test"], default="pilot")
    ap.add_argument("--view", choices=list(VIEWS), default="main")
    ap.add_argument("--systems", nargs="+", choices=list(SYSTEMS), default=list(SYSTEMS))
    ap.add_argument("--top-k", type=int, default=None, help="chunks in the prompt (default: config retrieval.top_k)")
    ap.add_argument("--limit", type=int, default=None, help="first N examples only (quick test)")
    ap.add_argument("--4bit", dest="use_4bit", action="store_true", help="4-bit weights (needs GPU + bitsandbytes)")
    ap.add_argument("--skip-codebleu", action="store_true", help="leave CodeBLEU out (recorded as null)")
    ap.add_argument("--output-dir", default=None)
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()

    needs_adapter = [s for s in args.systems if SYSTEMS[s][0]]
    if needs_adapter and not args.adapter:
        ap.error(f"--adapter is required for: {', '.join(needs_adapter)}")
    if args.adapter and not (Path(args.adapter) / "adapter_config.json").exists():
        ap.error(f"no adapter_config.json in {args.adapter}")

    cfg = load_config(args.config)
    top_k = args.top_k or cfg.retrieval.top_k
    k_values = list(cfg.retrieval.top_k_values)
    out_dir = Path(args.output_dir or f"results/{args.subset}_{args.view}")

    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    examples = load_examples(args.subset, args.limit)
    logger.info(f"{args.subset}: {len(examples)} examples, view={args.view}, top_k={top_k}")

    embedder = CodeEmbedder(cfg.retrieval.embedding_model)
    stores: dict[str, FAISSVectorStore] = {}
    tokenizer, model = load_model(cfg.llm.model, args.adapter, args.use_4bit)
    max_new_tokens = cfg.generation.max_new_tokens

    # Retrieval is identical for rag_only and hybrid, so do it once per example.
    records = []
    retrieval_ms = defaultdict(float)
    for ex in examples:
        meta = ex["metadata"]
        repo, target = meta["repository"], meta["file"]
        if repo not in stores:
            stores[repo] = FAISSVectorStore.load(str(INDEX_DIR / repo / args.view))
        code = ex["prompt"]
        start = time.perf_counter()
        ranked_chunks = stores[repo].search(embedder.embed([retrieval_query(code)])[0],
                                            top_k=max(top_k, stores[repo].index.ntotal))
        elapsed = (time.perf_counter() - start) * 1000
        chunks = ranked_chunks[:top_k]
        files = distinct_files(ranked_chunks)
        assert all(manifest[(repo, f)] != "test" for f in files), "TEST file retrieved"
        relevant = sorted({s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {target})
        relevant = [f for f in relevant if manifest.get((repo, f)) in VIEWS[args.view]]
        records.append({"task_id": meta["task_id"], "repo": repo, "code": code,
                        "reference": ex["groundtruth"].split("\n")[0], "chunks": chunks,
                        "retrieved_files": files, "relevant_files": relevant, "retrieval_ms": elapsed})
        retrieval_ms["total"] += elapsed

    results, predictions = {}, defaultdict(list)
    for system in args.systems:
        uses_adapter, uses_retrieval = SYSTEMS[system]
        logger.info(f"=== {system} ===")
        latency = LatencyRecord(system=system, n_samples=len(records))
        reset_gpu_memory_stats()
        peak_ram = 0.0
        for rec in records:
            prompt = build_prompt(rec["code"], rec["chunks"] if uses_retrieval else None)
            start = time.perf_counter()
            if uses_adapter or not args.adapter:
                pred = complete(tokenizer, model, prompt, max_new_tokens)
            else:
                with model.disable_adapter():
                    pred = complete(tokenizer, model, prompt, max_new_tokens)
            latency.inference_ms += (time.perf_counter() - start) * 1000
            if uses_retrieval:
                latency.retrieval_ms += rec["retrieval_ms"]
            predictions[system].append(pred)
            peak_ram = max(peak_ram, current_cpu_ram_mb())
        latency.total_ms = latency.retrieval_ms + latency.inference_ms
        latency.peak_gpu_mb = peak_gpu_memory_mb()
        latency.peak_cpu_ram_mb = peak_ram

        retrieved_list = relevant_list = None
        if uses_retrieval:
            keep = [r for r in records if r["relevant_files"]]
            retrieved_list = [r["retrieved_files"] for r in keep]
            relevant_list = [r["relevant_files"] for r in keep]
        results[system] = run_evaluation(
            system, predictions[system], [r["reference"] for r in records],
            latency=latency, output_dir=str(out_dir),
            retrieved_list=retrieved_list, relevant_list=relevant_list, k_values=k_values,
            include_codebleu=not args.skip_codebleu,
            extra={"n_examples": len(records),
                   "n_with_relevant_file": sum(bool(r["relevant_files"]) for r in records),
                   "subset": args.subset, "view": args.view, "top_k": top_k,
                   "adapter": args.adapter},
        )

    compare_systems(results, output_dir=str(out_dir))
    with open(out_dir / "predictions.jsonl", "w", encoding="utf-8") as f:
        for i, rec in enumerate(records):
            row = {"task_id": rec["task_id"], "repo": rec["repo"], "reference": rec["reference"],
                   "retrieved_files": rec["retrieved_files"], "relevant_files": rec["relevant_files"],
                   "relevant_in_top_k": bool(set(rec["relevant_files"]) & {c.file_path for c in rec["chunks"]}),
                   "mrr": mean_reciprocal_rank(rec["retrieved_files"], rec["relevant_files"]) if rec["relevant_files"] else None}
            for system, preds in predictions.items():
                row[system] = {"prediction": preds[i],
                               "exact_match": exact_match(preds[i], rec["reference"]),
                               "edit_similarity": round(edit_similarity(preds[i], rec["reference"]), 4)}
            f.write(json.dumps(row) + "\n")
    logger.info(f"Done. See {out_dir}/comparison_summary.md and predictions.jsonl")


if __name__ == "__main__":
    main()
