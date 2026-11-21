"""
experiments/dry_run_pipeline.py
--------------------------------
Model-free rehearsal of experiments/run_comparison.py. It runs everything that happens before and
after generation, so bugs show up locally instead of on the Colab GPU clock:

  1. adapter folder matches the config (base model name, files present)
  2. the pilot examples load, are all TEST, and the A3 relevance rule gives the expected counts
  3. retrieval from the per-repo index (main and staleness views), no TEST file retrieved
  4. prompts for all four systems, with token counts from the tokenizer only (no weights loaded)
  5. scoring and file-writing path, using stand-in predictions (reference text, empty text, and a
     two-line text) so that the first-line cut and the metric code are exercised
  6. CodeBLEU: reports whether the package is installed (it must raise, not return 0.0, when missing)

It loads the UniXcoder embedder (small) and the Qwen tokenizer (small); it never loads the 1.5B
weights. Stand-in predictions are NOT results; output goes to results/dry_run and is not a pilot.

Run from the project root:
    python -m experiments.dry_run_pipeline --adapter experiments/finetuned_model/crosscodeeval/v2
"""

from __future__ import annotations
import argparse
import json
from pathlib import Path

from rank_bm25 import BM25Okapi
from transformers import AutoTokenizer

from experiments.run_comparison import (INDEX_DIR, SPLIT_DIR, SYSTEMS, VIEWS, bm25_search, bm25_tokens,
                                        distinct_files, load_examples)
from src.evaluation.evaluator import compare_systems, run_evaluation
from src.evaluation.metrics import code_bleu
from src.prompting import build_plain_prompt, build_prompt, first_line, retrieval_query, truncate_code_left
from src.retrieval.embedder import CodeEmbedder
from src.retrieval.vector_store import FAISSVectorStore
from src.utils.config import load_config


def check(ok: bool, msg: str, problems: list):
    print(("ok      " if ok else "PROBLEM ") + msg)
    if not ok:
        problems.append(msg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--output-dir", default="results/dry_run")
    args = ap.parse_args()
    problems: list[str] = []
    cfg = load_config(args.config)
    top_k = cfg.retrieval.top_k

    # 1. adapter vs config
    acfg = json.loads((Path(args.adapter) / "adapter_config.json").read_text(encoding="utf-8"))
    check(acfg["base_model_name_or_path"] == cfg.llm.model,
          f"adapter base model {acfg['base_model_name_or_path']} == config llm.model {cfg.llm.model}", problems)
    check((Path(args.adapter) / "adapter_model.safetensors").exists(), "adapter_model.safetensors present", problems)

    # 2. examples
    examples = load_examples("pilot", None)
    check(len(examples) == 50, f"pilot examples loaded: {len(examples)} (expect 50)", problems)
    manifest = {(m["repo"], m["path"]): m["split"]
                for m in map(json.loads, open(SPLIT_DIR / "manifest.jsonl", encoding="utf-8"))}

    tok = AutoTokenizer.from_pretrained(cfg.llm.model)
    embedder = CodeEmbedder(cfg.retrieval.embedding_model)
    stores: dict[tuple, FAISSVectorStore] = {}
    max_len = cfg.finetuning.max_seq_length
    rows = {v: [] for v in VIEWS}
    n_prompt_tokens = {"no_retrieval": [], "retrieval": []}
    plain_tokens = {"no_retrieval": [], "retrieval": []}

    for view in VIEWS:
        for ex in examples:
            meta = ex["metadata"]
            repo, target = meta["repository"], meta["file"]
            key = (repo, view)
            if key not in stores:
                stores[key] = FAISSVectorStore.load(str(INDEX_DIR / repo / view))
            code = ex["prompt"]
            ranked = stores[key].search(embedder.embed([retrieval_query(code)])[0],
                                        top_k=max(top_k, stores[key].index.ntotal))
            chunks, files = ranked[:top_k], distinct_files(ranked)
            if any(manifest[(repo, f)] == "test" for f in files):
                problems.append(f"TEST file retrieved for {meta['task_id']} ({view})")
            relevant = sorted({s["filename"] for s in ex["crossfile_context_retrieval"]["list"]} - {target})
            relevant = [f for f in relevant if manifest.get((repo, f)) in VIEWS[view]]
            rows[view].append({"task_id": meta["task_id"], "code": code, "chunks": chunks,
                               "reference": first_line(ex["groundtruth"]),
                               "retrieved_files": files, "relevant_files": relevant})
            if view == "main":
                n_prompt_tokens["no_retrieval"].append(len(tok(build_prompt(code)).input_ids))
                n_prompt_tokens["retrieval"].append(len(tok(build_prompt(code, chunks)).input_ids))
                plain_tokens["no_retrieval"].append(len(tok(build_plain_prompt(code)).input_ids))
                plain_tokens["retrieval"].append(len(tok(build_plain_prompt(code, chunks)).input_ids))

    # 3. retrieval summary
    for view in VIEWS:
        have = sum(bool(r["relevant_files"]) for r in rows[view])
        hit = sum(bool(set(r["relevant_files"]) & {c.file_path for c in r["chunks"]})
                  for r in rows[view] if r["relevant_files"])
        print(f"info    {view}: {have} of 50 pilot examples have a relevant file; "
              f"relevant file inside the top-{top_k} chunks for {hit} of them")
    check(sum(bool(r["relevant_files"]) for r in rows["main"]) == 50,
          "all 50 pilot examples have a relevant file in the main pool (pilot is drawn from them)", problems)
    check(not any("TEST file retrieved" in p for p in problems), "no TEST file retrieved in either view", problems)

    # 4. prompt lengths (tokens). Training used max_seq_length; inference prompts are not cut.
    for name, vals in n_prompt_tokens.items():
        vals = sorted(vals)
        print(f"info    prompt tokens, {name}: median {vals[len(vals) // 2]}, max {vals[-1]}, "
              f"over training limit {max_len}: {sum(v > max_len for v in vals)} of {len(vals)}")
    print(f"info    generation limit max_new_tokens = {cfg.generation.max_new_tokens}")
    for name, vals in plain_tokens.items():          # --base-prompt plain (base and RAG only)
        vals = sorted(vals)
        print(f"info    with --base-prompt plain, prompt tokens, {name}: median {vals[len(vals) // 2]}, "
              f"max {vals[-1]}")
    check(all(len(tok(build_plain_prompt(r["code"])).input_ids) < len(tok(build_prompt(r["code"])).input_ids)
              for r in rows["main"][:5]), "plain prompt is shorter than the instruction prompt (no wrapper)", problems)

    # 4b. new run_comparison options: --retriever bm25 and --max-code-tokens 480
    bm25s, bm25_hit, bm25_with, cut_tokens = {}, 0, 0, {"no_retrieval": [], "retrieval": []}
    for ex, rec in zip(examples, rows["main"]):
        repo = ex["metadata"]["repository"]
        store = stores[(repo, "main")]
        if repo not in bm25s:
            bm25s[repo] = BM25Okapi([bm25_tokens(c.content) for c in store._chunks])
        ranked = bm25_search(store, bm25s[repo], retrieval_query(ex["prompt"]))
        if any(manifest[(repo, c.file_path)] == "test" for c in ranked):
            problems.append(f"BM25 returned a TEST file for {rec['task_id']}")
        if rec["relevant_files"]:
            bm25_with += 1
            bm25_hit += bool(set(rec["relevant_files"]) & {c.file_path for c in ranked[:top_k]})
        code = truncate_code_left(ex["prompt"], tok, 480)
        cut_tokens["no_retrieval"].append(len(tok(build_prompt(code)).input_ids))
        cut_tokens["retrieval"].append(len(tok(build_prompt(code, ranked[:top_k])).input_ids))
    print(f"info    BM25 (main): relevant file inside the top-{top_k} chunks for {bm25_hit} of {bm25_with}")
    check(len(rec["code"]) > 0 and truncate_code_left("a b c d e f", tok, 3) != "a b c d e f",
          "truncate_code_left shortens long code and leaves short code alone: "
          f"{truncate_code_left('a b c', tok, 10) == 'a b c'}", problems)
    for name, vals in cut_tokens.items():
        vals = sorted(vals)
        print(f"info    with --max-code-tokens 480, prompt tokens, {name}: median {vals[len(vals) // 2]}, "
              f"max {vals[-1]}, over {max_len}: {sum(v > max_len for v in vals)} of {len(vals)}")

    # 5. scoring path with stand-in predictions
    out_dir = Path(args.output_dir)
    recs = rows["main"]
    refs = [r["reference"] for r in recs]
    stand_in = {"base": ["" for _ in refs],                                   # empty output
                "rag_only": [first_line(r + "\nsecond line") for r in refs],   # cut check
                "finetuning_only": list(refs),                                 # perfect
                "hybrid": [r[:-1] if r else r for r in refs]}                  # nearly right
    results = {}
    for system, preds in stand_in.items():
        uses_retrieval = SYSTEMS[system][1]
        keep = [r for r in recs if r["relevant_files"]]
        results[system] = run_evaluation(
            system, preds, refs, output_dir=str(out_dir),
            retrieved_list=[r["retrieved_files"] for r in keep] if uses_retrieval else None,
            relevant_list=[r["relevant_files"] for r in keep] if uses_retrieval else None,
            k_values=list(cfg.retrieval.top_k_values), include_codebleu=False,
            extra={"stand_in_predictions": True})
    compare_systems(results, output_dir=str(out_dir))
    em = {s: results[s]["exact_match"] for s in results}
    print(f"info    stand-in exact match by system (expect rag/ft 1.0, base 0.0): {em}")

    # 6. CodeBLEU availability
    try:
        code_bleu(["x = 1"], ["x = 1"])
        print("ok      codebleu package works")
    except Exception as e:  # must raise, not return 0.0
        print(f"info    codebleu not usable here ({type(e).__name__}: {str(e)[:80]}); "
              f"the evaluation will stop unless --skip-codebleu is given. Good: it does not return 0.0.")

    print("\n" + ("DRY RUN FAILED:\n  " + "\n  ".join(problems) if problems else "DRY RUN PASSED (stand-in predictions only, not results)"))


if __name__ == "__main__":
    main()
