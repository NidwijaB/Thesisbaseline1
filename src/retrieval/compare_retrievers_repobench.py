"""
src/retrieval/compare_retrievers_repobench.py
----------------------------------------------
Retrieval-only comparison on the RepoBench evaluation sample (plan Section 5, System A; Section 6
retrieval metrics). No model and no GPU: it only reads the per-repo indexes built by
build_repobench_indexes.py. RepoBench counterpart of compare_retrievers.py (CrossCodeEval); the
retrievers, metrics and bootstrap are the same code.

Sample: the seeded examples in data/processed/repobench/sample_ids.json (300 per setting,
cross_file_first and cross_file_random; build_repobench_sample.py). Settings are reported
separately, never pooled (plan Section 2).

Retrievers rank the SAME fragments of the example's own repository:
  dense   UniXcoder embeddings from the saved FAISS index
  bm25    BM25 (rank_bm25, BM25Okapi) over the same fragment text
  random  seeded random order of the pool's files (a floor; pools are small)
Query = last QUERY_LINES lines of the example's cropped_code (the code before the line to predict).
Fragment rankings are collapsed to a ranked list of distinct files (first occurrence wins).
Relevant file = the file of the gold snippet (context[gold_snippet_index].path), a single file.

Views: main (pool = BASE) and staleness (pool = BASE + NEW). Because the sample was drawn from examples
whose gold file is in BASE (Entry 24), the gold file is in both pools; the staleness view therefore
shows what NEW files do as extra distractors. It does NOT contain examples whose gold file is in NEW.
Those would need a separate sample (not built).

Metrics: hit@k, precision@k, recall@k (k = 1, 3, 5, 10) and MRR with 95% bootstrap CIs over examples,
plus paired dense-minus-BM25 differences, and the size of the pools (distinct files), because with
small pools even random guessing scores high at large k. Precision@k divides by k even when the pool
has fewer than k files.

Leakage checks: the sampled example must be a TEST example matching examples.jsonl (same repo and
path); a retrieved fragment from a TEST file aborts the run.

Run from the project root (after build_repobench_indexes --sample-repos):
    python -m src.retrieval.compare_retrievers_repobench [--limit N] [--output results/repobench_retrieval_comparison.json]
"""

from __future__ import annotations
import argparse
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
from datasets import load_from_disk
from rank_bm25 import BM25Okapi

from src.evaluation.metrics import bootstrap_ci
from src.retrieval.build_repobench_indexes import repo_dir
from src.retrieval.compare_retrievers import (KS, N_BOOTSTRAP, QUERY_LINES, SEED, SYSTEMS,
                                              distinct_files, score_example, summarise, tokenize)
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/repobench")
DATASET_DIR = Path("data/repobench")
VIEWS = ("main", "staleness")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only the first N sampled examples per setting (testing)")
    parser.add_argument("--output", default="results/repobench_retrieval_comparison.json")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    examples = {(e["setting"], e["row"]): e
                for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))}
    sample = json.loads((SPLIT_DIR / "sample_ids.json").read_text(encoding="utf-8"))

    embedder = CodeEmbedder(model_name=cfg.retrieval.embedding_model)
    stores, bm25s = {}, {}
    # rows[setting][view][system] -> list of per-example metric dicts
    rows = {s: {v: defaultdict(list) for v in VIEWS} for s in sample}
    pool_sizes = {s: {v: [] for v in VIEWS} for s in sample}
    leaked = total = 0

    for setting, row_ids in sample.items():
        data = load_from_disk(str(DATASET_DIR / setting))
        for row_id in row_ids[:args.limit] if args.limit else row_ids:
            ex, info = data[row_id], examples[(setting, row_id)]
            assert info["split"] == "test" and info["repo"] == ex["repo_name"] \
                and info["path"] == ex["file_path"], f"sample row {setting}/{row_id} does not match the split file"
            repo, gold = info["repo"], info["gold_path"]
            assert gold and gold != info["path"], "sample must have a valid gold file"
            total += 1
            query = "\n".join(ex["cropped_code"].split("\n")[-QUERY_LINES:])
            q = embedder.embed([query])[0]

            for view in VIEWS:
                if (repo, view) not in stores:
                    store = FAISSVectorStore.load(str(repo_dir(repo) / view))
                    stores[(repo, view)] = store
                    bm25s[(repo, view)] = BM25Okapi([tokenize(c.content) for c in store._chunks])
                store, bm25 = stores[(repo, view)], bm25s[(repo, view)]
                chunks = store._chunks
                pool_files = sorted({c.file_path for c in chunks})
                assert gold in pool_files, f"gold file missing from the {view} pool of {repo}"
                pool_sizes[setting][view].append(len(pool_files))

                dense_files = [h.file_path for h in store.search(q, top_k=store.index.ntotal)]
                bm25_order = np.argsort(-bm25.get_scores(tokenize(query)), kind="stable")
                shuffled = list(pool_files)
                random.Random(f"{SEED}-{setting}-{row_id}-{view}").shuffle(shuffled)
                rankings = {"dense": list(dict.fromkeys(dense_files)),
                            "bm25": distinct_files(bm25_order, chunks), "random": shuffled}
                for files in rankings.values():
                    leaked += sum(manifest[(repo, f)] == "test" for f in files)
                for system, ranked in rankings.items():
                    rows[setting][view][system].append(score_example(ranked, [gold]))

    assert leaked == 0, "a TEST file was retrieved"
    logger.info(f"Sampled TEST examples queried: {total}; TEST files retrieved (must be 0): {leaked}")

    result = {"config": {"query_lines": QUERY_LINES, "ks": list(KS), "seed": SEED, "n_bootstrap": N_BOOTSTRAP,
                         "bm25": "rank_bm25.BM25Okapi, identifier tokens lowercased",
                         "dense": cfg.retrieval.embedding_model, "limit": args.limit,
                         "query": f"last {QUERY_LINES} lines of cropped_code", "relevant": "gold snippet file"},
              "n": {}, "pool_distinct_files": {}, "metrics": {}, "paired_dense_minus_bm25": {}}
    for setting in sample:
        for key in ("n", "pool_distinct_files", "metrics", "paired_dense_minus_bm25"):
            result[key][setting] = {}
        for view in VIEWS:
            by_system = rows[setting][view]
            n = len(by_system["dense"])
            sizes = np.array(pool_sizes[setting][view])
            result["n"][setting][view] = n
            result["pool_distinct_files"][setting][view] = {
                "median": float(np.median(sizes)), "mean": round(float(sizes.mean()), 2), "max": int(sizes.max())}
            result["metrics"][setting][view] = {s: summarise(by_system[s]) for s in SYSTEMS}
            paired = {}
            for metric in ("hit@1", "hit@3", "mrr"):
                d = np.array([a[metric] - b[metric] for a, b in zip(by_system["dense"], by_system["bm25"])])
                low, high = bootstrap_ci(d, N_BOOTSTRAP, SEED)
                paired[metric] = {"mean": round(float(d.mean()), 4), "ci95": [round(low, 4), round(high, 4)]}
            result["paired_dense_minus_bm25"][setting][view] = paired
            line = {s: {m: result["metrics"][setting][view][s][m]["mean"] for m in ("hit@1", "hit@3", "mrr")}
                    for s in SYSTEMS}
            logger.info(f"{setting}/{view} (n={n}, median pool files {np.median(sizes):.0f}): {line}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info(f"Saved {out}")


if __name__ == "__main__":
    main()
