"""
src/evaluation/full_run_analysis.py
-----------------------------------
Local analysis (no GPU) of the supervisor-requested runs, read-only on results/b1 and results/b2:

  B2  the full 543-example run: the no-retrieval run (base, fine-tuned) and the retrieval runs (RAG, hybrid)
      are joined by task_id into one four-system table per view (main, staleness), with 95% bootstrap CIs,
      paired differences, hit vs miss, the staleness change on the 68 NEW-relevant examples, dense vs BM25.
  B1  the RAG-format settings S0 to S3 (pilot n=50 and staleness-test n=68): empty / fill-in-the-middle /
      very short answers and paired edit-similarity differences against S0.
  Functional proxies (empty, fim, parses, identifiers in repo) for every b1 and b2 run.

Bootstrap: 2,000 resamples, seed 42, same helpers as analyze_predictions.py.
Writes to results/additional_results/: full_run_summary.md, full_run_analysis.json, b1_settings.csv,
functional_proxies_full.csv and the joined predictions combined_<view>.jsonl.

    python -m src.evaluation.full_run_analysis
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np

from src.evaluation.analyze_predictions import (analyse, boot_diff_paired, boot_mean, load_rows)
from src.evaluation.functional_proxies import MARKER, evaluate as proxies_for, load_context

R = Path("results")
OUT = R / "additional_results"
SYSTEMS = ["base", "rag_only", "finetuning_only", "hybrid"]
NAMES = {"base": "base", "rag_only": "RAG (A)", "finetuning_only": "fine-tuned (B)", "hybrid": "hybrid (C)"}


def by_task(rows):
    return {r["task_id"]: r for r in rows}


def join(noretr: list[dict], retr: list[dict]) -> list[dict]:
    """One row per example with all four systems; retrieval fields come from the retrieval run."""
    base = by_task(noretr)
    assert set(base) == {r["task_id"] for r in retr}, "task ids differ between the two runs"
    out = []
    for r in sorted(retr, key=lambda r: r["task_id"]):
        b = base[r["task_id"]]
        assert b["reference"] == r["reference"], f"reference differs for {r['task_id']}"
        row = {k: v for k, v in r.items()}
        row["base"], row["finetuning_only"] = b["base"], b["finetuning_only"]
        out.append(row)
    return out


def metric_table(rows, summary: dict) -> list[dict]:
    table = []
    for s in SYSTEMS:
        em = boot_mean([r[s]["exact_match"] for r in rows])
        es = boot_mean([r[s]["edit_similarity"] for r in rows])
        table.append({"system": s, "n": es["n"], "em": em["mean"], "em_ci": em["ci95"], "es": es["mean"],
                      "es_ci": es["ci95"], "identifier_acc": summary.get(s, {}).get("identifier_accuracy"),
                      "codebleu": summary.get(s, {}).get("code_bleu")})
    return table


def quality_from_summary(*folders: str) -> dict:
    out = {}
    for f in folders:
        data = json.loads((R / "b2" / f / "comparison_summary.json").read_text(encoding="utf-8"))
        for s, v in data.items():
            if isinstance(v, dict):
                q = v.get("quality") or v
                out[s] = {"identifier_accuracy": q.get("identifier_accuracy"), "code_bleu": q.get("code_bleu")}
    return out


def paired(rows_a, rows_b, sys_a, sys_b, metric="edit_similarity", ids=None):
    A, B = by_task(rows_a), by_task(rows_b)
    keys = sorted(set(A) & set(B) if ids is None else set(ids) & set(A) & set(B))
    return {"n": len(keys), **boot_diff_paired([A[k][sys_a][metric] for k in keys], [B[k][sys_b][metric] for k in keys])}


def b1_rows(path: Path) -> dict:
    return by_task(load_rows(str(path / "predictions.jsonl")))


def count_problems(rows, system):
    empty = fim = short = 0
    for r in rows.values():
        p = r[system]["prediction"]
        raw = r[system].get("raw", p)
        empty += not p.strip()
        fim += bool(MARKER.search(p) or MARKER.search(raw.replace("<|endoftext|>", "")))
        short += len(p.strip()) < 5
    return empty, fim, short


def fmt(d):
    return f"{d['mean']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] (n={d['n']})"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    md, js = [], {}

    # ---------------------------------------------------------------- B2: four systems per view
    noretr = load_rows(str(R / "b2/test_noretr/predictions.jsonl"))
    runs = {"main": load_rows(str(R / "b2/test_main_dense/predictions.jsonl")),
            "staleness": load_rows(str(R / "b2/test_staleness_dense/predictions.jsonl"))}
    joined = {v: join(noretr, rows) for v, rows in runs.items()}
    for v, rows in joined.items():
        with open(OUT / f"combined_{v}.jsonl", "w", encoding="utf-8") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    md.append("# Full run, CrossCodeEval TEST, n=543, dense retrieval top-5, RAG/hybrid with --suppress-fim\n")
    md.append("Plain prompt for base and RAG; fine-tuned and hybrid use the training prompt. EM and edit similarity (ES) with 95% bootstrap CIs "
              "computed from predictions; identifier accuracy and CodeBLEU are the run's own corpus values (no CI).\n")
    for v, rows in joined.items():
        summ = quality_from_summary("test_noretr", "test_main_dense" if v == "main" else "test_staleness_dense")
        table = metric_table(rows, summ)
        an = analyse(rows)
        js[v] = {"table": table, "analysis": an}
        md.append(f"## {v} view\n\n| System | EM [95% CI] | Edit sim. [95% CI] | Identifier acc. | CodeBLEU |\n|---|---|---|---|---|")
        for t in table:
            md.append(f"| {NAMES[t['system']]} | {t['em']:.4f} {t['em_ci']} | {t['es']:.4f} {t['es_ci']} | {t['identifier_acc']} | {t['codebleu']} |")
        md.append("\nPaired differences, edit similarity (EM in the JSON):\n")
        for pair, by_m in an["paired_differences"].items():
            d = by_m["edit_similarity"]
            flag = "" if d["ci95"][0] <= 0 <= d["ci95"][1] else "  **excludes 0**"
            md.append(f"- {pair}: {d['mean']:+.4f} {d['ci95']}{flag}")
        md.append(f"\nHit vs miss (relevant file inside / outside the top-5 chunks); examples with a relevant file in the pool: {an['n_with_relevant_file']} of {an['n_examples']}\n")
        for system, by_m in an["hit_vs_miss"].items():
            g = by_m["edit_similarity"]
            md.append(f"- {NAMES[system]}: hit n={g['hit']['n']} ES {g['hit']['mean']}; miss n={g['miss']['n']} ES {g['miss']['mean']}; "
                      f"hit minus miss {g['hit_minus_miss']['mean']} {g['hit_minus_miss']['ci95']}")
        md.append("")

    # ---------------------------------------------------------------- staleness change
    new68 = sorted(by_task(load_rows(str(R / "b1/new68_staleness_S0/predictions.jsonl"))))
    md.append("## Staleness change (staleness view minus main view, edit similarity)\n")
    js["staleness_change"] = {}
    for s in ("rag_only", "hybrid"):
        a = paired(joined["staleness"], joined["main"], s, s)
        b = paired(joined["staleness"], joined["main"], s, s, ids=new68)
        js["staleness_change"][s] = {"all_543": a, "new_relevant_68": b}
        md.append(f"- {NAMES[s]}: all 543 {fmt(a)}; the 68 NEW-relevant examples {fmt(b)}")
    for pair in (("hybrid", "finetuning_only"), ("rag_only", "base")):
        for v in ("main", "staleness"):
            for label, ids in (("all 543", None), ("68 NEW-relevant", new68)):
                d = paired(joined[v], joined[v], pair[0], pair[1], ids=ids)
                js["staleness_change"][f"{pair[0]}-{pair[1]}|{v}|{label}"] = d
                md.append(f"- {pair[0]} minus {pair[1]}, {v} view, {label}: {fmt(d)}")
    md.append("")

    # ---------------------------------------------------------------- rank of the relevant file (hit vs miss is nearly empty at top-5)
    md.append("## Rank of the first relevant file among the retrieved files (examples with a relevant file in the pool; all top-5 chunks were in the prompt)\n")
    md.append("Groups are post-hoc (the prompt always held the top-5 chunks): rank 1, ranks 2 to 3, rank 4 or lower / not retrieved. Edit similarity.\n")
    js["by_rank"] = {}
    for v, rows in joined.items():
        groups = {"rank 1": [], "rank 2-3": [], "rank 4+ or missing": []}
        for r in rows:
            if not r["relevant_files"]:
                continue
            pos = [i for i, f in enumerate(r["retrieved_files"]) if f in set(r["relevant_files"])]
            g = "rank 1" if pos and pos[0] == 0 else "rank 2-3" if pos and pos[0] <= 2 else "rank 4+ or missing"
            groups[g].append(r)
        js["by_rank"][v] = {}
        for g, rs in groups.items():
            cells = {s: boot_mean([r[s]["edit_similarity"] for r in rs]) for s in SYSTEMS}
            js["by_rank"][v][g] = {"n": len(rs), **{s: c["mean"] for s, c in cells.items()}}
            md.append(f"- {v}, {g} (n={len(rs)}): " + ", ".join(f"{NAMES[s]} {cells[s]['mean']}" for s in SYSTEMS))
    md.append("")

    # ---------------------------------------------------------------- RAG vs base on usable RAG answers only
    md.append("## RAG minus base on the examples where the RAG answer is not empty (edit similarity; main and staleness view)\n")
    js["rag_usable"] = {}
    for v, rows in joined.items():
        keep = [r for r in rows if r["rag_only"]["prediction"].strip()]
        d = boot_diff_paired([r["rag_only"]["edit_similarity"] for r in keep], [r["base"]["edit_similarity"] for r in keep])
        d["n"] = len(keep)
        js["rag_usable"][v] = d
        md.append(f"- {v}: {len(rows) - len(keep)} empty RAG answers removed; RAG minus base {fmt(d)}")
    md.append("")

    # ---------------------------------------------------------------- dense vs BM25 (main view)
    bm = load_rows(str(R / "b2/test_main_bm25/predictions.jsonl"))
    md.append("## Dense vs BM25 retrieval (main view, n=543; BM25 minus dense)\n")
    js["bm25_vs_dense"] = {}
    for s in ("rag_only", "hybrid"):
        d = paired(bm, runs["main"], s, s)
        e = paired(bm, runs["main"], s, s, metric="exact_match")
        js["bm25_vs_dense"][s] = {"edit_similarity": d, "exact_match": e}
        md.append(f"- {NAMES[s]}: edit similarity {fmt(d)}; exact match {fmt(e)}")
    D, B = by_task(runs["main"]), by_task(bm)
    both = [k for k in D if D[k]["mrr"] is not None and B[k]["mrr"] is not None]
    mrr = boot_diff_paired([B[k]["mrr"] for k in both], [D[k]["mrr"] for k in both])
    hit = {n: float(np.mean([bool(X[k]["relevant_in_top_k"]) for k in both])) for n, X in (("dense", D), ("bm25", B))}
    js["bm25_vs_dense"]["retrieval"] = {"n": len(both), "mrr_diff": mrr, "hit_at_5": hit,
                                         "mrr_mean": {"dense": float(np.mean([D[k]["mrr"] for k in both])), "bm25": float(np.mean([B[k]["mrr"] for k in both]))}}
    md.append(f"- retrieval on the {len(both)} examples with a relevant file: MRR dense {js['bm25_vs_dense']['retrieval']['mrr_mean']['dense']:.4f}, "
              f"BM25 {js['bm25_vs_dense']['retrieval']['mrr_mean']['bm25']:.4f}; BM25 minus dense {mrr['mean']:+.4f} {mrr['ci95']}; hit@5 {hit}\n")

    # ---------------------------------------------------------------- B1: RAG settings
    md.append("## B1: RAG-format settings (S0 current, S1 no-FIM, S2 Qwen repo format, S3 both); RAG row, edit similarity\n")
    md.append("| Set | Setting | n | ES | empty | fim marker | under 5 chars | ES minus S0 [95% CI] | hybrid answers differing from S0 |\n|---|---|---|---|---|---|---|---|---|")
    csv_rows = []
    for tag, folder in (("pilot n=50", "pilot_main"), ("68-example staleness test", "new68_staleness")):
        base_rows = {s: b1_rows(R / "b1" / f"{folder}_{s}") for s in ("S0", "S1", "S2", "S3")}
        for s, rows in base_rows.items():
            empty, fim, short = count_problems(rows, "rag_only")
            es = float(np.mean([r["rag_only"]["edit_similarity"] for r in rows.values()]))
            keys = sorted(rows)
            d = boot_diff_paired([rows[k]["rag_only"]["edit_similarity"] for k in keys],
                                 [base_rows["S0"][k]["rag_only"]["edit_similarity"] for k in keys])
            hyb_diff = sum(rows[k]["hybrid"]["prediction"] != base_rows["S0"][k]["hybrid"]["prediction"] for k in keys)
            md.append(f"| {tag} | {s} | {len(rows)} | {es:.4f} | {empty} | {fim} | {short} | "
                      f"{d['mean']:+.4f} [{d['ci95'][0]:+.4f}, {d['ci95'][1]:+.4f}] | {hyb_diff} |")
            csv_rows.append({"set": tag, "setting": s, "n": len(rows), "rag_es": round(es, 4), "empty": empty, "fim": fim,
                             "under5": short, "es_minus_s0": d["mean"], "ci_lo": d["ci95"][0], "ci_hi": d["ci95"][1],
                             "hybrid_answers_changed": hyb_diff})
    with open(OUT / "b1_settings.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(csv_rows[0]))
        w.writeheader()
        w.writerows(csv_rows)
    js["b1"] = csv_rows

    # ---------------------------------------------------------------- functional proxies on every run
    repo_text, last_line = load_context()
    folders = sorted(p for p in (list((R / "b1").glob("*")) + [R / "b2/test_noretr", R / "b2/test_main_dense",
                                                              R / "b2/test_staleness_dense", R / "b2/test_main_bm25"]) if p.is_dir())
    prox = []
    for f in folders:
        for row in proxies_for(f / "predictions.jsonl", repo_text, last_line):
            row["run"] = str(f.relative_to(R))
            prox.append(row)
    fields = ["run", "system", "n", "pct_empty", "pct_fim_token", "pct_parses", "pct_ids_in_repo", "mean_id_share"]
    with open(OUT / "functional_proxies_full.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(prox)
    md.append("\n## Functional proxies (% of answers; rough proxies, see src/evaluation/functional_proxies.py)\n")
    md.append("| Run | System | n | empty | fim | parses | ids all in repo |\n|---|---|---|---|---|---|---|")
    for r in prox:
        if r["run"].startswith("b2"):
            md.append(f"| {r['run']} | {r['system']} | {r['n']} | {r['pct_empty']} | {r['pct_fim_token']} | {r['pct_parses']} | {r['pct_ids_in_repo']} |")

    (OUT / "full_run_summary.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (OUT / "full_run_analysis.json").write_text(json.dumps(js, indent=2), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
