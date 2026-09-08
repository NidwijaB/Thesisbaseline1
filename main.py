"""
main.py
-------
Entry point for:

  "Comparative Study of Fine-Tuning, Retrieval-Augmented Generation,
   and Hybrid Models for Code Completion in Enterprise Repositories"

Sub-commands
------------
  index     — Embed & index a repository into the vector store
  finetune  — Fine-tune a code LLM with LoRA/QLoRA
  evaluate  — Evaluate a single system
  compare   — Run all three systems and produce a comparison report (main study output)

Quick start
-----------
  # 1. Index your repository
  python main.py index --repo-root path/to/repo --repo-id my_repo

  # 2. Fine-tune
  python main.py finetune

  # 3. Full comparative evaluation (all three systems)
  python main.py compare --benchmark data/processed/test.jsonl \\
                         --ft-model  experiments/finetuned_model
"""

import argparse
from src.utils.config import load_config
from src.utils.logger import get_logger

logger = get_logger("main")


# ── Sub-command handlers ──────────────────────────────────────────────────────

def cmd_index(args):
    # Chunk -> embed -> store a repository so it can be searched later (RAG component).
    from src.preprocessing.chunker import chunk_repository
    from src.retrieval.embedder import CodeEmbedder
    from src.retrieval.vector_store import FAISSVectorStore

    cfg = load_config(args.config)
    r = cfg.retrieval

    logger.info(f"Chunking repository: {args.repo_root}")
    chunks = chunk_repository(
        args.repo_root,
        repo_id=args.repo_id,
        chunk_size=r.chunk_size,
        chunk_overlap=r.chunk_overlap,
    )
    logger.info(f"Total chunks: {len(chunks)}")

    embedder = CodeEmbedder(model_name=r.embedding_model)
    embeddings = embedder.embed([c.content for c in chunks])

    store = FAISSVectorStore(dim=embeddings.shape[1])
    store.add(embeddings, chunks)
    store.save(cfg.paths.embeddings + args.repo_id)
    logger.info("Indexing complete.")


def cmd_finetune(args):
    # Trains the Fine-Tuning-only baseline (QLoRA on data/processed/train.jsonl).
    from src.finetuning.trainer import run_finetuning
    run_finetuning(config_path=args.config)


def cmd_evaluate(args):
    """Evaluate a single system (useful for quick iteration)."""
    import json
    from pathlib import Path
    from src.evaluation.evaluator import run_evaluation

    examples = [json.loads(l) for l in Path(args.benchmark).read_text().splitlines() if l.strip()]
    references = [e["output"] for e in examples]

    logger.info(f"Evaluating system: {args.system} on {len(examples)} examples")
    logger.info("Wire up your generation function in the relevant src/ module, then call run_evaluation().")
    # Stub — replace predictions list with actual model outputs:
    # run_evaluation(args.system, predictions, references, output_dir="results")


def cmd_compare(args):
    """Run the full comparative study — the main research output."""
    # Just forwards to experiments/run_comparison.py with the same CLI args,
    # so `python main.py compare ...` and `python experiments/run_comparison.py ...`
    # behave identically.
    import sys
    sys.argv = [
        "run_comparison.py",
        "--benchmark", args.benchmark,
        "--ft-model",  args.ft_model,
        "--config",    args.config,
        "--output-dir", args.output_dir,
    ]
    if args.systems:
        sys.argv += ["--systems"] + args.systems

    from experiments.run_comparison import main as run_main
    run_main()


# ── Argument Parser ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Comparative Study of Fine-Tuning, RAG, and Hybrid Models "
            "for Code Completion in Enterprise Repositories"
        )
    )
    parser.add_argument("--config", default="configs/config.yaml")
    sub = parser.add_subparsers(dest="command")

    # index
    p_idx = sub.add_parser("index", help="Embed & index a repository")
    p_idx.add_argument("--repo-root", required=True)
    p_idx.add_argument("--repo-id",   required=True)
    p_idx.set_defaults(func=cmd_index)

    # finetune
    p_ft = sub.add_parser("finetune", help="Fine-tune the code model (LoRA/QLoRA)")
    p_ft.set_defaults(func=cmd_finetune)

    # evaluate (single system)
    p_ev = sub.add_parser("evaluate", help="Evaluate a single system")
    p_ev.add_argument("--benchmark", required=True)
    p_ev.add_argument("--system", choices=["rag_only", "finetuning_only", "hybrid"],
                      default="hybrid")
    p_ev.set_defaults(func=cmd_evaluate)

    # compare (all three — main research output)
    p_cmp = sub.add_parser(
        "compare",
        help="Run all three systems and produce a side-by-side comparison report"
    )
    p_cmp.add_argument("--benchmark",  required=True, help="Path to test.jsonl")
    p_cmp.add_argument("--ft-model",   required=True, help="Fine-tuned model directory")
    p_cmp.add_argument("--output-dir", default="results")
    p_cmp.add_argument("--systems",    nargs="+",
                       choices=["rag_only", "finetuning_only", "hybrid"],
                       default=None, help="Subset of systems to run (default: all)")
    p_cmp.set_defaults(func=cmd_compare)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    args.func(args)


if __name__ == "__main__":
    main()
