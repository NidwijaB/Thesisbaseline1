"""
src/evaluation/functional_proxies.py
------------------------------------
Cheap functional proxies computed from existing predictions.jsonl files (no GPU, no model, no code is run):
  pct_empty        first-line answer is empty
  pct_fim_token    answer contains a Qwen fill-in-the-middle / file-separator marker (<|fim_...|>, <|file_sep|> ...)
  pct_parses       PROXY for "valid Python": (last prompt line + answer) parses with ast, after closing any
                   brackets the one-line answer leaves open. A body is added after a trailing ':'.
                   A statement that fails here may still be fine in the full file; this is a rough check.
  pct_ids_in_repo  share of answers whose identifiers (minus Python keywords and builtins) ALL occur in the text
                   of the repository's files known to the benchmark (all splits). Hallucination proxy; the
                   repository's files are the benchmark's own, not the full repository.
  mean_id_share    mean over answers of the share of identifiers found in the repository text
Empty answers count as not parsing and have no identifiers (excluded from the two identifier columns).

    python -m src.evaluation.functional_proxies [run folders...]   (default: every results/*/predictions.jsonl)
Writes results/additional_results/functional_proxies.csv. results/functional_proxies.csv is a copy for convenience.
"""
from __future__ import annotations

import ast
import builtins
import csv
import io
import json
import keyword
import re
import shutil
import sys
import tokenize
from collections import defaultdict
from pathlib import Path

from datasets import load_from_disk

SPLIT_DIR = Path("data/processed/crosscodeeval")
OUT = Path("results/additional_results")
SYSTEMS = ["base", "rag_only", "finetuning_only", "hybrid"]
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MARKER = re.compile(r"<\|(fim_|file_sep|repo_name|endoftext)[^|]*\|>")
SKIP = set(keyword.kwlist) | set(dir(builtins)) | {"self", "cls"}
CLOSERS = {"(": ")", "[": "]", "{": "}"}


def closers_for(text: str) -> str | None:
    """Closing brackets needed to balance text (None if it closes something never opened)."""
    stack: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(text).readline):
            if tok.type == tokenize.OP and tok.string in CLOSERS:
                stack.append(CLOSERS[tok.string])
            elif tok.type == tokenize.OP and tok.string in CLOSERS.values():
                if not stack or stack.pop() != tok.string:
                    return None
    except (tokenize.TokenError, IndentationError):
        pass  # an unterminated bracket raises at EOF; the stack built so far is what we need
    return "".join(reversed(stack))


def parses(line: str) -> bool:
    text = line.strip()
    if not text:
        return False
    close = closers_for(text)
    if close is None:
        return False
    text += close
    if text.endswith(":"):
        text += " pass"
    try:
        ast.parse(text)
        return True
    except SyntaxError:
        return False


def idents(text: str) -> list[str]:
    # drop attribute-free noise: names right after a dot are kept (they are what the answer invents)
    return [i for i in IDENT.findall(text) if i not in SKIP]


def load_context():
    split = {e["task_id"]: e["split"] for e in map(json.loads, open(SPLIT_DIR / "examples.jsonl", encoding="utf-8"))}
    repo_text: dict[str, set[str]] = defaultdict(set)
    for f in map(json.loads, open(SPLIT_DIR / "files.jsonl", encoding="utf-8")):
        repo_text[f["repo"]].update(IDENT.findall(f["text"]))
    last_line = {}
    for ex in load_from_disk("data/crosscodeeval/python")["train"]:
        meta = ex["metadata"]
        if split.get(meta["task_id"]) == "test":
            last_line[meta["task_id"]] = ex["prompt"].rsplit("\n", 1)[-1]
    return repo_text, last_line


def evaluate(path: Path, repo_text, last_line) -> list[dict]:
    rows = [json.loads(line) for line in open(path, encoding="utf-8")]
    out = []
    for system in SYSTEMS:
        stats = {"n": 0, "empty": 0, "fim": 0, "parses": 0, "ids_ok": 0, "ids_n": 0, "share_sum": 0.0}
        for r in rows:
            if system not in r:
                continue
            pred = r[system]["prediction"]
            stats["n"] += 1
            if not pred.strip():
                stats["empty"] += 1
                continue
            if MARKER.search(pred):
                stats["fim"] += 1
            if parses(last_line[r["task_id"]] + pred):
                stats["parses"] += 1
            ids = idents(MARKER.sub("", pred))
            if ids:
                known = repo_text[r["repo"]]
                found = sum(i in known for i in ids)
                stats["ids_n"] += 1
                stats["ids_ok"] += found == len(ids)
                stats["share_sum"] += found / len(ids)
        if not stats["n"]:
            continue
        n = stats["n"]
        pct = lambda k: round(100 * stats[k] / n, 1)
        out.append({
            "run": path.parent.name, "system": system, "n": n,
            "pct_empty": pct("empty"), "pct_fim_token": pct("fim"), "pct_parses": pct("parses"),
            "pct_ids_in_repo": round(100 * stats["ids_ok"] / stats["ids_n"], 1) if stats["ids_n"] else "",
            "mean_id_share": round(stats["share_sum"] / stats["ids_n"], 3) if stats["ids_n"] else "",
        })
    return out


def main() -> None:
    folders = [Path(p) for p in sys.argv[1:]] or sorted(p.parent for p in Path("results").glob("*/predictions.jsonl"))
    repo_text, last_line = load_context()
    rows = []
    for folder in folders:
        rows += evaluate(folder / "predictions.jsonl", repo_text, last_line)
    OUT.mkdir(parents=True, exist_ok=True)
    fields = ["run", "system", "n", "pct_empty", "pct_fim_token", "pct_parses", "pct_ids_in_repo", "mean_id_share"]
    with open(OUT / "functional_proxies.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    shutil.copy(OUT / "functional_proxies.csv", "results/functional_proxies.csv")
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
