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
prompts (src/prompting.py) and the same greedy one-line generation (src/generation.py). Predictions
are cut to the first line before scoring.

Prompts: the adapter systems (ft, hybrid) always get the instruction format they were trained on.
--base-prompt chooses what base and rag get: "instruction" (default, the format of the first pilot,
which the frozen model does not follow, progress log Entry 36) or "plain" (retrieved chunks as comments
+ the code, no wrapper; the model just continues the line; the recommended setting).

Examples: --subset pilot (the 50 ids in data/processed/crosscodeeval/pilot_ids.json),
--subset test (all TEST examples) or --subset new_relevant (the TEST examples whose relevant file,
by the A3 rule, is a NEW file: the staleness test; run it with --view main and --view staleness). Retrieval metrics use the A3 relevance rule for the chosen
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

import random
import re

import numpy as np
from datasets import load_from_disk
from rank_bm25 import BM25Okapi

from src.evaluation.evaluator import compare_systems, run_evaluation
from src.evaluation.latency import (LatencyRecord, current_cpu_ram_mb, peak_gpu_memory_mb,
                                    reset_gpu_memory_stats)
from src.evaluation.metrics import edit_similarity, exact_match, mean_reciprocal_rank
from src.generation import code_marker_ids, complete, complete_detailed, load_model
from src.prompting import BASE_PROMPTS, RAG_FORMATS, build_system_prompt, retrieval_query, truncate_code_left
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore, RetrievedChunk
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


def new_relevant_ids(rows, manifest: dict, split: dict) -> set[str]:
    """TEST examples with at least one relevant file (A3 rule: distinct files named in the example's
    cross-file snippets, minus the example's own file) that is a NEW file. These are the examples on
    which fine-tuning cannot know the relevant file and retrieval can (staleness test)."""
    ids = set()
    for ex in rows:
        meta = ex["metadata"]
        if split.get(meta["task_id"]) != "test":
            continue
        files = {s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {meta["file"]}
        if any(manifest.get((meta["repository"], f)) == "new" for f in files):
            ids.add(meta["task_id"])
    return ids


def load_examples(subset: str, limit: int | None):
    """Raw CrossCodeEval rows for the chosen TEST examples, in a fixed order."""
    split = {e["task_id"]: e["split"]
             for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))}
    all_rows = load_from_disk(str(DATASET_DIR))["train"]
    if subset == "pilot":
        wanted = set(json.loads((SPLIT_DIR / "pilot_ids.json").read_text(encoding="utf-8")))
    elif subset == "new_relevant":
        manifest = {(m["repo"], m["path"]): m["split"]
                    for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
        wanted = new_relevant_ids(all_rows, manifest, split)
        logger.info(f"new_relevant subset: {len(wanted)} TEST examples with a relevant NEW file (expected 68)")
    else:
        wanted = {t for t, s in split.items() if s == "test"}
    rows = [ex for ex in all_rows if ex["metadata"]["task_id"] in wanted]
    assert all(split[ex["metadata"]["task_id"]] == "test" for ex in rows), "non-TEST example selected"
    rows.sort(key=lambda ex: ex["metadata"]["task_id"])
    if limit:
        rows = rows[:limit]
    return rows


TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def bm25_tokens(text: str) -> list[str]:
    """Same tokeniser as src/retrieval/compare_retrievers.py (identifier tokens, lowercased)."""
    return [t.lower() for t in TOKEN_RE.findall(text)]


def bm25_search(store: FAISSVectorStore, bm25: BM25Okapi, query: str) -> list[RetrievedChunk]:
    """All chunks of the repo's pool ranked by BM25 (stable sort, ties keep chunk order)."""
    scores = bm25.get_scores(bm25_tokens(query))
    order = np.argsort(-scores, kind="stable")
    return [RetrievedChunk(content=store._chunks[i].content, file_path=store._chunks[i].file_path,
                           score=float(scores[i]), metadata=store._chunks[i].metadata) for i in order]


def add_noise(chunks: list, n_noise: int, repo: str, task_id: str, repos: list[str], view: str,
              stores: dict, seed: int = 42) -> list:
    """Noisy-context test (plan Section 6, extra 2): put n_noise chunks from OTHER repositories
    (never the example's own) among the real chunks, at seeded random positions. They are
    irrelevant by construction. Same noise for rag_only and hybrid."""
    rng = random.Random(f"{seed}:{task_id}")
    noise = []
    while len(noise) < n_noise:
        other = rng.choice(repos)
        if other == repo:
            continue
        key = f"{other}/{view}"
        if key not in stores:
            stores[key] = FAISSVectorStore.load(str(INDEX_DIR / other / view))
        pool = stores[key]._chunks
        c = rng.choice(pool)
        noise.append(RetrievedChunk(content=c.content, file_path=f"[noise from {other}] {c.file_path}",
                                    score=0.0, metadata=c.metadata))
    mixed = list(chunks) + noise
    rng.shuffle(mixed)
    return mixed


def distinct_files(chunks) -> list[str]:
    return list(dict.fromkeys(c.file_path for c in chunks))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", help="LoRA adapter folder (needed for finetuning_only and hybrid)")
    ap.add_argument("--subset", choices=["pilot", "test", "new_relevant"], default="pilot")
    ap.add_argument("--base-prompt", choices=list(BASE_PROMPTS), default="instruction",
                    help="prompt for base and rag_only (the adapter systems always use the instruction format): "
                         "instruction = first-pilot format (default); plain = chunks as comments + code, no wrapper")
    ap.add_argument("--view", choices=list(VIEWS), default="main")
    ap.add_argument("--systems", nargs="+", choices=list(SYSTEMS), default=list(SYSTEMS))
    ap.add_argument("--top-k", type=int, default=None, help="chunks in the prompt (default: config retrieval.top_k)")
    ap.add_argument("--retriever", choices=["dense", "bm25"], default="dense",
                    help="how rag_only and hybrid find chunks (same chunks and index views either way)")
    ap.add_argument("--max-code-tokens", type=int, default=None,
                    help="keep only the last N tokens of the code in every prompt (training cut inputs to "
                         "512 tokens in total; about 480 matches it). Default: no cut. Chunks are not cut.")
    ap.add_argument("--noise-chunks", type=int, default=0,
                    help="noisy-context test: add N irrelevant chunks from other repositories to the "
                         "prompts of rag_only and hybrid (seeded). Retrieval metrics are not affected.")
    ap.add_argument("--limit", type=int, default=None, help="first N examples only (quick test)")
    ap.add_argument("--rag-format", choices=list(RAG_FORMATS), default="comments",
                    help="how the frozen RAG system sees the retrieved chunks (only with --base-prompt plain): comments = "
                         "chunks as # comment lines (default, first runs); qwen_repo = Qwen2.5-Coder's repository-level "
                         "format with <|file_sep|> markers. Output folder gets the suffix _qwenrepo.")
    ap.add_argument("--suppress-fim", action="store_true",
                    help="forbid Qwen's fill-in-the-middle and file-separator tokens during generation, for every system "
                         "(the frozen RAG system sometimes wrote <|fim_suffix|> as its answer). Folder suffix _nofim.")
    ap.add_argument("--save-raw", action="store_true",
                    help="diagnostic: also save each system's raw completion, number of generated tokens and the "
                         "reason generation stopped (eos / newline / max_tokens) in predictions.jsonl. Same decoding, "
                         "so the predictions are unchanged. Output folder gets the suffix _raw.")
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
    suffix = "" if args.retriever == "dense" else f"_{args.retriever}"
    suffix += f"_code{args.max_code_tokens}" if args.max_code_tokens else ""
    suffix += f"_noise{args.noise_chunks}" if args.noise_chunks else ""
    suffix += "_plainbase" if args.base_prompt == "plain" else ""
    suffix += "_qwenrepo" if args.rag_format == "qwen_repo" else ""
    suffix += "_nofim" if args.suppress_fim else ""
    suffix += "_raw" if args.save_raw else ""
    out_dir = Path(args.output_dir or f"results/{args.subset}_{args.view}{suffix}")

    all_repos = sorted(p.name for p in INDEX_DIR.iterdir() if p.is_dir())
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    examples = load_examples(args.subset, args.limit)
    logger.info(f"{args.subset}: {len(examples)} examples, view={args.view}, top_k={top_k}")

    embedder = CodeEmbedder(cfg.retrieval.embedding_model) if args.retriever == "dense" else None
    stores: dict[str, FAISSVectorStore] = {}
    bm25s: dict[str, BM25Okapi] = {}
    noise_stores: dict[str, FAISSVectorStore] = {}
    tokenizer, model = load_model(cfg.llm.model, args.adapter, args.use_4bit)
    max_new_tokens = cfg.generation.max_new_tokens
    bad_words = code_marker_ids(tokenizer) if args.suppress_fim else None

    # Retrieval is identical for rag_only and hybrid, so do it once per example.
    records = []
    retrieval_ms = defaultdict(float)
    for ex in examples:
        meta = ex["metadata"]
        repo, target = meta["repository"], meta["file"]
        if repo not in stores:
            stores[repo] = FAISSVectorStore.load(str(INDEX_DIR / repo / args.view))
        full_code = ex["prompt"]
        start = time.perf_counter()
        if args.retriever == "dense":
            ranked_chunks = stores[repo].search(embedder.embed([retrieval_query(full_code)])[0],
                                                top_k=max(top_k, stores[repo].index.ntotal))
        else:
            if repo not in bm25s:
                bm25s[repo] = BM25Okapi([bm25_tokens(c.content) for c in stores[repo]._chunks])
            ranked_chunks = bm25_search(stores[repo], bm25s[repo], retrieval_query(full_code))
        code = truncate_code_left(full_code, tokenizer, args.max_code_tokens)   # after retrieval: query unchanged
        elapsed = (time.perf_counter() - start) * 1000
        chunks = ranked_chunks[:top_k]
        prompt_chunks = (add_noise(chunks, args.noise_chunks, repo, meta["task_id"], all_repos,
                                   args.view, noise_stores) if args.noise_chunks else chunks)
        files = distinct_files(ranked_chunks)
        assert all(manifest[(repo, f)] != "test" for f in files), "TEST file retrieved"
        relevant = sorted({s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {target})
        relevant = [f for f in relevant if manifest.get((repo, f)) in VIEWS[args.view]]
        records.append({"task_id": meta["task_id"], "repo": repo, "target": target, "code": code,
                        "reference": ex["groundtruth"].split("\n")[0], "chunks": chunks, "prompt_chunks": prompt_chunks,
                        "retrieved_files": files, "relevant_files": relevant, "retrieval_ms": elapsed})
        retrieval_ms["total"] += elapsed

    results, predictions = {}, defaultdict(list)
    diagnostics = defaultdict(list)    # --save-raw only
    for system in args.systems:
        uses_adapter, uses_retrieval = SYSTEMS[system]
        logger.info(f"=== {system} ===")
        latency = LatencyRecord(system=system, n_samples=len(records))
        reset_gpu_memory_stats()
        peak_ram = 0.0
        for rec in records:
            prompt = build_system_prompt(rec["code"], rec["prompt_chunks"] if uses_retrieval else None,
                                         uses_adapter, args.base_prompt, args.rag_format, rec["repo"], rec["target"])
            start = time.perf_counter()
            generate = complete_detailed if args.save_raw else complete
            if uses_adapter or not args.adapter:
                pred = generate(tokenizer, model, prompt, max_new_tokens, bad_words)
            else:
                with model.disable_adapter():
                    pred = generate(tokenizer, model, prompt, max_new_tokens, bad_words)
            if args.save_raw:
                diagnostics[system].append({k: pred[k] for k in ("raw", "n_new_tokens", "stop_reason")})
                pred = pred["prediction"]
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
                   "adapter": args.adapter, "retriever": args.retriever,
                          "max_code_tokens": args.max_code_tokens,
                          "noise_chunks": args.noise_chunks,
                          "base_prompt": args.base_prompt, "rag_format": args.rag_format,
                          "suppress_fim": args.suppress_fim},
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
                if args.save_raw:
                    row[system].update(diagnostics[system][i])
            f.write(json.dumps(row) + "\n")
    if args.save_raw:
        for system, rows in diagnostics.items():
            counts = {r: sum(x["stop_reason"] == r for x in rows) for r in ("eos", "newline", "max_tokens")}
            empty = sum(not p.strip() for p in predictions[system])
            logger.info(f"[{system}] stop reasons {counts}; empty first lines {empty}")
    logger.info(f"Done. See {out_dir}/comparison_summary.md and predictions.jsonl")


if __name__ == "__main__":
    main()
