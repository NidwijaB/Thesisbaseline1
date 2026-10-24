"""
src/retrieval/sanity_check_indexes.py
--------------------------------------
Sanity retrieval over the per-repo CrossCodeEval indexes (plan Section 9, step 5 prep).

For every TEST example, the query is the last QUERY_LINES lines of the prompt and the
index is the repo's own. It reports:
  - leakage: a retrieved chunk from a TEST file (must be 0)
  - hit@k against the A3 relevance rule (distinct filenames in
    crossfile_context_retrieval that are in the pool and are not the target file)
    for the main and staleness views, restricted to examples with >= 1 relevant file.
This is a smoke test of the indexes, not the P@k / R@k / MRR evaluation.

Run from the project root (after build_indexes):
    python -m src.retrieval.sanity_check_indexes
"""

from __future__ import annotations
import json
from pathlib import Path

from datasets import load_from_disk

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


def main():
    cfg = load_config("configs/config.yaml")
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    test_ids = {e["task_id"] for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))
                if e["split"] == "test"}

    embedder = CodeEmbedder(model_name=cfg.retrieval.embedding_model)
    stores = {}
    hits = {v: {k: 0 for k in KS} for v in ("main", "staleness")}
    counted = {"main": 0, "staleness": 0}
    leaked = 0
    total = 0

    for ex in load_from_disk(str(DATASET_DIR))["train"]:
        meta = ex["metadata"]
        if meta["task_id"] not in test_ids:
            continue
        total += 1
        repo, target = meta["repository"], meta["file"]
        query = "\n".join(ex["prompt"].split("\n")[-QUERY_LINES:])
        q = embedder.embed([query])[0]
        snippet_files = {s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {target}
        for view, splits in (("main", {"base"}), ("staleness", {"base", "new"})):
            if (repo, view) not in stores:
                stores[(repo, view)] = FAISSVectorStore.load(str(INDEX_DIR / repo / view))
            results = stores[(repo, view)].search(q, top_k=max(KS))
            leaked += sum(manifest[(repo, r.file_path)] == "test" for r in results)
            relevant = {f for f in snippet_files if manifest.get((repo, f)) in splits}
            if not relevant:
                continue
            counted[view] += 1
            ranked = [r.file_path for r in results]
            for k in KS:
                hits[view][k] += bool(relevant & set(ranked[:k]))

    logger.info(f"TEST examples queried: {total}; TEST chunks retrieved (must be 0): {leaked}")
    for view in hits:
        rates = {f"hit@{k}": round(hits[view][k] / counted[view], 3) for k in KS}
        logger.info(f"{view}: {counted[view]} examples with a relevant file; {rates}")
    assert leaked == 0, "TEST file retrieved"


if __name__ == "__main__":
    main()