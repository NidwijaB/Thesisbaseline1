"""
src/retrieval/compare_retrievers.py
------------------------------------
Retrieval-only comparison on the CrossCodeEval TEST examples (plan Section 5, System A;
Section 6 retrieval metrics). No model and no GPU: it only reads the per-repo indexes.

Three retrievers rank the SAME chunks of the example's own repository:
  dense   UniXcoder embeddings from the saved FAISS index (cosine similarity)
  bm25    BM25 (rank_bm25, BM25Okapi) over the same chunk text
  random  seeded random order of the pool's files (a floor: pools are tiny, so hit@k
          is high even for random guessing; the other two must be read against this)

Query = last QUERY_LINES lines of the example's prompt (same as sanity_check_indexes.py).
Chunk rankings are collapsed to a ranked list of distinct files (first occurrence wins),
and scored against the A3 relevance rule (Entry 4): distinct files named in
crossfile_context_retrieval that are in the pool for the view and are not the target file.
Examples with no relevant file in a view's pool are excluded from that view.

Views: main (pool = BASE) and staleness (pool = BASE + NEW). Subsets reported:
  all           every example with >= 1 relevant file in the view
  new_relevant  (staleness only) examples with a relevant file in NEW: the staleness sample
Metrics: hit@k, precision@k, recall@k (k = 1, 3, 5, 10) and MRR, each with a 95% bootstrap
confidence interval over examples, plus paired dense-minus-BM25 differences.
Precision@k divides by k even when a pool has fewer than k files (src/evaluation/metrics.py).

Leakage check: a retrieved chunk from a TEST file aborts the run.

Run from the project root (after build_indexes):
    python -m src.retrieval.compare_retrievers [--limit N] [--output results/retrieval_comparison.json]
"""

from __future__ import annotations
import argparse
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from datasets import load_from_disk
from rank_bm25 import BM25Okapi

from src.evaluation.metrics import bootstrap_ci, mean_reciprocal_rank, precision_at_k, recall_at_k
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/crosscodeeval")
INDEX_DIR = Path("data/embeddings/crosscodeeval")
DATASET_DIR = Path("data/crosscodeeval/python")
QUERY_LINES = 20
KS = (1, 3, 5, 10)
SEED = 42
N_BOOTSTRAP = 1000
VIEWS = {"main": {"base"}, "staleness": {"base", "new"}}
SYSTEMS = ("dense", "bm25", "random")
TOKEN_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
EXPECTED_EXAMPLES = {"main": 292, "staleness": 327}   # Entry 7 / Entry 12


def tokenize(text: str) -> list[str]:
    """Identifier-like tokens, lowercased. Simple on purpose; stated in the thesis."""
    return [t.lower() for t in TOKEN_RE.findall(text)]


def distinct_files(chunk_order, chunks) -> list[str]:
    files, seen = [], set()
    for i in chunk_order:
        path = chunks[i].file_path
        if path not in seen:
            seen.add(path)
            files.append(path)
    return files


def score_example(ranked: list[str], relevant: list[str]) -> dict:
    row = {"mrr": mean_reciprocal_rank(ranked, relevant)}
    for k in KS:
        row[f"hit@{k}"] = float(bool(set(ranked[:k]) & set(relevant)))
        row[f"precision@{k}"] = precision_at_k(ranked, relevant, k)
        row[f"recall@{k}"] = recall_at_k(ranked, relevant, k)
    return row


def summarise(rows: list[dict]) -> dict:
    out = {}
    for metric in rows[0]:
        values = np.array([r[metric] for r in rows], dtype=float)
        low, high = bootstrap_ci(values, N_BOOTSTRAP, SEED)
        out[metric] = {"mean": round(float(values.mean()), 4),
                       "ci95": [round(low, 4), round(high, 4)]}
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None, help="Only the first N TEST examples (testing)")
    parser.add_argument("--output", default="results/retrieval_comparison.json")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    test_ids = {e["task_id"] for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))
                if e["split"] == "test"}

    embedder = CodeEmbedder(model_name=cfg.retrieval.embedding_model)
    stores, bm25s = {}, {}
    # rows[view][subset][system] -> list of per-example metric dicts
    rows = {v: defaultdict(lambda: defaultdict(list)) for v in VIEWS}
    leaked = total = 0

    for ex in load_from_disk(str(DATASET_DIR))["train"]:
        meta = ex["metadata"]
        if meta["task_id"] not in test_ids:
            continue
        if args.limit and total >= args.limit:
            break
        total += 1
        repo, target = meta["repository"], meta["file"]
        query = "\n".join(ex["prompt"].split("\n")[-QUERY_LINES:])
        q = embedder.embed([query])[0]
        snippet_files = {s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {target}

        for view, splits in VIEWS.items():
            relevant = sorted(f for f in snippet_files if manifest.get((repo, f)) in splits)
            if not relevant:
                continue
            if (repo, view) not in stores:
                store = FAISSVectorStore.load(str(INDEX_DIR / repo / view))
                stores[(repo, view)] = store
                bm25s[(repo, view)] = BM25Okapi([tokenize(c.content) for c in store._chunks])
            store, bm25 = stores[(repo, view)], bm25s[(repo, view)]
            chunks = store._chunks

            # dense: all chunks in similarity order (pools are small, so rank them all)
            dense_hits = store.search(q, top_k=store.index.ntotal)
            dense_files = [h.file_path for h in dense_hits]
            # bm25: stable sort so ties keep chunk order
            bm25_order = np.argsort(-bm25.get_scores(tokenize(query)), kind="stable")
            bm25_files = distinct_files(bm25_order, chunks)
            # random: shuffle the pool's distinct files, seeded per example and view
            pool_files = sorted({c.file_path for c in chunks})
            random.Random(f"{SEED}-{meta['task_id']}-{view}").shuffle(pool_files)

            rankings = {"dense": list(dict.fromkeys(dense_files)), "bm25": bm25_files, "random": pool_files}
            for files in rankings.values():
                leaked += sum(manifest[(repo, f)] == "test" for f in files)

            in_new = any(manifest[(repo, f)] == "new" for f in relevant)
            for system, ranked in rankings.items():
                scored = score_example(ranked, relevant)
                rows[view]["all"][system].append(scored)
                if view == "staleness" and in_new:
                    rows[view]["new_relevant"][system].append(scored)

    assert leaked == 0, "a TEST file was retrieved"
    logger.info(f"TEST examples queried: {total}; TEST files retrieved (must be 0): {leaked}")

    result = {
        "config": {"query_lines": QUERY_LINES, "ks": list(KS), "seed": SEED, "n_bootstrap": N_BOOTSTRAP,
                   "bm25": "rank_bm25.BM25Okapi, identifier tokens lowercased",
                   "dense": cfg.retrieval.embedding_model, "chunk_size": cfg.retrieval.chunk_size,
                   "chunk_overlap": cfg.retrieval.chunk_overlap, "limit": args.limit},
        "n": {}, "metrics": {}, "paired_dense_minus_bm25": {},
    }
    for view in VIEWS:
        result["metrics"][view], result["n"][view], result["paired_dense_minus_bm25"][view] = {}, {}, {}
        for subset, by_system in rows[view].items():
            n = len(by_system["dense"])
            result["n"][view][subset] = n
            result["metrics"][view][subset] = {s: summarise(by_system[s]) for s in SYSTEMS}
            paired = {}
            for metric in ("hit@1", "hit@3", "mrr"):
                d = np.array([a[metric] - b[metric] for a, b in zip(by_system["dense"], by_system["bm25"])])
                low, high = bootstrap_ci(d, N_BOOTSTRAP, SEED)
                paired[metric] = {"mean": round(float(d.mean()), 4), "ci95": [round(low, 4), round(high, 4)]}
            result["paired_dense_minus_bm25"][view][subset] = paired
        expected = EXPECTED_EXAMPLES[view]
        got = result["n"][view].get("all", 0)
        if not args.limit and got != expected:
            logger.warning(f"{view}: {got} examples, the log says {expected}")
        for subset, n in result["n"][view].items():
            line = {s: {m: result["metrics"][view][subset][s][m]["mean"] for m in ("hit@1", "hit@3", "mrr")}
                    for s in SYSTEMS}
            logger.info(f"{view}/{subset} (n={n}): {line}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    logger.info(f"Saved {out}")


if __name__ == "__main__":
    main()
