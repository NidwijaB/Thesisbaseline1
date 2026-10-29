"""
src/demo.py
-----------
Side-by-side demo of the four systems on one code snippet from an indexed
CrossCodeEval repo:

  base    frozen model, no retrieval, no adapter
  rag     frozen model + retrieved repo chunks
  ft      fine-tuned adapter, no retrieval        (needs --adapter)
  hybrid  fine-tuned adapter + retrieved chunks   (needs --adapter)

The code is either typed (--code / --code-file) or taken from a benchmark example
(--task-id), in which case the ground truth is shown too. Output is cut to the
first line, as the evaluation will do.

Run from the project root, for example:
    python -m src.demo --task-id project_cc_python/74
    python -m src.demo --repo <repo> --code-file snippet.py --adapter experiments/finetuned_model/crosscodeeval
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

import torch
from datasets import load_from_disk
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

from src.finetuning.dataset import PROMPT_TEMPLATE
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.retriever import Retriever
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config

SPLIT_DIR = Path("data/processed/crosscodeeval")
INDEX_DIR = Path("data/embeddings/crosscodeeval")
DATASET_DIR = Path("data/crosscodeeval/python")
QUERY_LINES = 20       # same query as sanity_check_indexes.py
MAX_CHUNK_CHARS = 1200  # keep the prompt small; chunks are up to 256 lines


def build_prompt(code: str, chunks: list | None = None) -> str:
    """Training prompt format (dataset.PROMPT_TEMPLATE); retrieved chunks, if any,
    are prepended to the input as comments."""
    context = ""
    if chunks:
        parts = []
        for c in chunks:
            body = "\n".join("# " + line for line in c.content[:MAX_CHUNK_CHARS].splitlines())
            parts.append(f"# --- retrieved from {c.file_path} ---\n{body}")
        context = "\n".join(parts) + "\n\n"
    return PROMPT_TEMPLATE.format(input=context + code, output="")


def load_model(base_name: str, adapter: str | None, use_4bit: bool):
    tokenizer = AutoTokenizer.from_pretrained(base_name, trust_remote_code=True)
    on_gpu = torch.cuda.is_available()
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.float16,
                             bnb_4bit_use_double_quant=True) if use_4bit else None
    model = AutoModelForCausalLM.from_pretrained(
        base_name, trust_remote_code=True, quantization_config=bnb,
        dtype=torch.float16 if on_gpu else torch.float32,
        device_map="auto" if on_gpu else None)
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return tokenizer, model


def complete(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                             stop_strings=["\n"], tokenizer=tokenizer,
                             pad_token_id=tokenizer.eos_token_id)
    text = tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return text.split("\n")[0]


def find_example(task_id: str):
    for ex in load_from_disk(str(DATASET_DIR))["train"]:
        if ex["metadata"]["task_id"] == task_id:
            return ex
    raise SystemExit(f"task_id not found: {task_id}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task-id", help="CrossCodeEval task_id; uses its prompt and shows the ground truth")
    ap.add_argument("--repo", help="indexed repo name (not needed with --task-id)")
    ap.add_argument("--code", help="code to complete")
    ap.add_argument("--code-file", help="file containing the code to complete")
    ap.add_argument("--view", choices=["main", "staleness"], default="main", help="index view")
    ap.add_argument("--adapter", help="LoRA adapter dir; enables the ft and hybrid systems")
    ap.add_argument("--top-k", type=int, default=3)
    ap.add_argument("--max-new-tokens", type=int, default=64)
    ap.add_argument("--4bit", dest="use_4bit", action="store_true", help="4-bit weights (needs GPU + bitsandbytes)")
    ap.add_argument("--config", default="configs/config.yaml")
    args = ap.parse_args()
    cfg = load_config(args.config)

    truth = None
    if args.task_id:
        ex = find_example(args.task_id)
        repo, code, truth = ex["metadata"]["repository"], ex["prompt"], ex["groundtruth"]
        split = {e["task_id"]: e["split"] for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))}
        print(f"[{args.task_id}] repo={repo} file={ex['metadata']['file']} split={split.get(args.task_id, 'not in a kept repo')}")
    else:
        repo = args.repo
        code = args.code if args.code is not None else Path(args.code_file).read_text(encoding="utf-8") if args.code_file else None
        if not repo or code is None:
            ap.error("give --task-id, or --repo with --code / --code-file")
    if not repo or "/" in repo or "\\" in repo or not (INDEX_DIR / repo / args.view).is_dir():
        raise SystemExit(f"no {args.view} index for repo {repo!r} under {INDEX_DIR}")

    query = "\n".join(code.split("\n")[-QUERY_LINES:])
    retriever = Retriever(CodeEmbedder(cfg.retrieval.embedding_model),
                          FAISSVectorStore.load(str(INDEX_DIR / repo / args.view)), top_k=args.top_k)
    chunks = retriever.retrieve(query)

    print("\n=== Code (last lines) ===")
    print("\n".join(code.split("\n")[-8:]))
    print(f"\n=== Retrieved ({args.view} index, top {args.top_k}) ===")
    for c in chunks:
        print(f"  {c.score:.3f}  {c.file_path}")

    tokenizer, model = load_model(cfg.llm.model, args.adapter, args.use_4bit)
    results = {}
    if args.adapter:
        results["ft"] = complete(tokenizer, model, build_prompt(code), args.max_new_tokens)
        results["hybrid"] = complete(tokenizer, model, build_prompt(code, chunks), args.max_new_tokens)
        with model.disable_adapter():
            results["base"] = complete(tokenizer, model, build_prompt(code), args.max_new_tokens)
            results["rag"] = complete(tokenizer, model, build_prompt(code, chunks), args.max_new_tokens)
    else:
        results["base"] = complete(tokenizer, model, build_prompt(code), args.max_new_tokens)
        results["rag"] = complete(tokenizer, model, build_prompt(code, chunks), args.max_new_tokens)

    print("\n=== Completions (first line) ===")
    if truth is not None:
        print(f"  truth   : {truth.split(chr(10))[0]}")
    for name in ("base", "rag", "ft", "hybrid"):
        if name in results:
            print(f"  {name:<8}: {results[name]}")


if __name__ == "__main__":
    main()