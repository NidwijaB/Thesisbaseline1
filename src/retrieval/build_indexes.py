"""
src/retrieval/build_indexes.py
-------------------------------
Builds one FAISS index per repo for the CrossCodeEval pool (plan Section 5,
System A; Section 1, A6).

Per repo, chunks come from pool files only (BASE and NEW). TEST files are never
read into an index. Two views are saved from one set of embeddings:
  main       BASE chunks only            (headline comparison)
  staleness  BASE + NEW chunks           (NEW files added to the index only)

Layout (data/embeddings is gitignored):
  data/embeddings/crosscodeeval/<repo>/main/{index.faiss,chunks.pkl}
  data/embeddings/crosscodeeval/<repo>/staleness/{index.faiss,chunks.pkl}

Run from the project root (after build_crosscodeeval_split):
    python -m src.retrieval.build_indexes [--repos REPO ...]
"""

from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

from src.preprocessing.chunker import chunk_text
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/crosscodeeval")
OUTPUT_DIR = Path("data/embeddings/crosscodeeval")
VIEWS = {"main": {"base"}, "staleness": {"base", "new"}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repos", nargs="+", default=None, help="Only build these repos")
    parser.add_argument("--config", default="configs/config.yaml")
    args = parser.parse_args()

    cfg = load_config(args.config)
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl"))}
    test_keys = {k for k, s in manifest.items() if s == "test"}

    chunks_by_repo = defaultdict(list)
    for row in map(json.loads, open(SPLIT_DIR / "files.jsonl", encoding="utf-8")):
        if row["split"] == "test":
            continue                      # TEST text is never chunked or embedded
        if args.repos and row["repo"] not in args.repos:
            continue
        chunks_by_repo[row["repo"]].extend(chunk_text(
            row["text"], repo_id=row["repo"], file_path=row["path"],
            chunk_size=cfg.retrieval.chunk_size, chunk_overlap=cfg.retrieval.chunk_overlap,
            metadata={"split": row["split"]}))

    embedder = CodeEmbedder(model_name=cfg.retrieval.embedding_model)
    sizes = defaultdict(int)
    for n, (repo, chunks) in enumerate(sorted(chunks_by_repo.items()), 1):
        embeddings = embedder.embed([c.content for c in chunks])
        for view, splits in VIEWS.items():
            keep = [i for i, c in enumerate(chunks) if c.metadata["split"] in splits]
            store = FAISSVectorStore(dim=embeddings.shape[1])
            store.add(embeddings[keep], [chunks[i] for i in keep])
            # A6 assertions: only pool files, never a TEST file, scoped to this repo
            for c in store._chunks:
                assert (c.repo_id, c.file_path) not in test_keys, "TEST file in index"
                assert c.repo_id == repo
                assert manifest[(c.repo_id, c.file_path)] in splits
            store.save(str(OUTPUT_DIR / repo / view))
            sizes[view] += len(keep)
        logger.info(f"[{n}/{len(chunks_by_repo)}] {repo}: {len(chunks)} chunks")

    logger.info(f"Indexed {len(chunks_by_repo)} repos; chunks per view: {dict(sizes)}")
    logger.info("Index assertions passed (no TEST file, one repo per index)")


if __name__ == "__main__":
    main()
