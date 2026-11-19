"""
src/retrieval/build_repobench_indexes.py
-----------------------------------------
Per-repo FAISS indexes for the RepoBench pool (plan Section 5, System A; Section 1, A6).
Mirror of build_indexes.py for CrossCodeEval. Entries are the pool fragments written by
build_repobench_split.py (BASE and NEW only; TEST files are not in pool.jsonl at all), so
one fragment = one retrievable unit; there is no further chunking.

Two views from one set of embeddings:
  main       BASE fragments only
  staleness  BASE + NEW fragments

Layout (data/embeddings is gitignored; "/" in a repo name is replaced by "__"):
  data/embeddings/repobench/<owner>__<repo>/{main,staleness}/{index.faiss,chunks.pkl}

Fragments are cut to MAX_CHARS characters before embedding and storage (a few are 240,000 characters;
prompts use at most 1,200 characters per chunk, and embedding the first 3,000 characters keeps CPU time down).

Run from the project root (after build_repobench_split):
    python -m src.retrieval.build_repobench_indexes [--sample-repos | --repos OWNER/REPO ...] [--max-repos N]
A repo whose index folder already exists is skipped, so an interrupted run can be restarted.
"""

from __future__ import annotations
import argparse
import json
from collections import defaultdict
from pathlib import Path

from src.preprocessing.chunker import CodeChunk
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

SPLIT_DIR = Path("data/processed/repobench")
OUTPUT_DIR = Path("data/embeddings/repobench")
VIEWS = {"main": {"base"}, "staleness": {"base", "new"}}
MAX_CHARS = 3000


def repo_dir(repo: str) -> Path:
    return OUTPUT_DIR / repo.replace("/", "__")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", nargs="+", default=None, help="Only these repos (owner/name)")
    ap.add_argument("--sample-repos", action="store_true",
                    help="only the repos of the evaluation sample (sample_repos.json from build_repobench_sample)")
    ap.add_argument("--max-repos", type=int, default=None, help="Stop after N repos (quick test)")
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()

    cfg = load_config(args.config)
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}
    test_keys = {k for k, s in manifest.items() if s == "test"}

    wanted = set(args.repos or [])
    if args.sample_repos:
        wanted |= set(json.loads((SPLIT_DIR / "sample_repos.json").read_text(encoding="utf-8")))
    by_repo = defaultdict(list)
    for row in map(json.loads, open(SPLIT_DIR / "pool.jsonl", encoding="utf-8")):
        assert row["split"] in ("base", "new") and (row["repo"], row["path"]) not in test_keys, "TEST in pool"
        if wanted and row["repo"] not in wanted:
            continue
        by_repo[row["repo"]].append(CodeChunk(
            repo_id=row["repo"], file_path=row["path"], language="python", content=row["text"][:MAX_CHARS],
            start_line=0, end_line=0, metadata={"split": row["split"], "kind": row["kind"]}))

    embedder = CodeEmbedder(model_name=cfg.retrieval.embedding_model)
    sizes, done = defaultdict(int), 0
    repos = sorted(by_repo)
    for n, repo in enumerate(repos, 1):
        if (repo_dir(repo) / "staleness" / "index.faiss").exists():
            continue                                   # built in an earlier run
        if args.max_repos and done >= args.max_repos:
            break
        chunks = by_repo[repo]
        embeddings = embedder.embed([c.content for c in chunks])
        for view, splits in VIEWS.items():
            keep = [i for i, c in enumerate(chunks) if c.metadata["split"] in splits]
            if not keep:
                continue
            store = FAISSVectorStore(dim=embeddings.shape[1])
            store.add(embeddings[keep], [chunks[i] for i in keep])
            for c in store._chunks:                    # A6 assertions
                assert (c.repo_id, c.file_path) not in test_keys, "TEST file in index"
                assert c.repo_id == repo and manifest[(c.repo_id, c.file_path)] in splits
            store.save(str(repo_dir(repo) / view))
            sizes[view] += len(keep)
        done += 1
        logger.info(f"[{n}/{len(repos)}] {repo}: {len(chunks)} fragments")

    logger.info(f"Indexed {done} repos this run; fragments per view: {dict(sizes)}")
    logger.info("Index assertions passed (no TEST file, one repo per index)")


if __name__ == "__main__":
    main()
