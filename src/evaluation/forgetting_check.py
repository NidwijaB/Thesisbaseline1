"""
src/evaluation/forgetting_check.py
-----------------------------------
Forgetting check (plan Section 6, extra 4): HumanEval pass@1 (greedy, one sample per problem) of the
base model and of the fine-tuned model, to see whether fine-tuning damaged general code generation
(Wang et al. report a 24.1% relative HumanEval drop for full fine-tuning).

Both models see the same prompt, so the only difference is the adapter. One model is loaded; the base
numbers use `disable_adapter()`. --prompt plain (default) gives both models the raw HumanEval function
stub to continue, which is the normal way to test a code model. --prompt instruction wraps the stub in
the training prompt format (src/prompting.py): the first run (20 problems, base 0/20) used it, and it is
NOT a valid forgetting measure because the frozen model does not follow that wrapper (progress log
Entries 35 and 36). Completions are cut at the first top-level statement after the
function (def / class / if __name__ / print / assert).

SAFETY: this EXECUTES MODEL-GENERATED CODE and runs the benchmark's tests. Run it only on Colab (a
throw-away machine), never on your own computer. Each program runs in a separate Python process
(`python -I`) in a temporary folder with a 10 s time limit; that limits runaway loops but it is NOT
a security sandbox (no network or file-system isolation). The script refuses to run without
--allow-exec. The HumanEval data is downloaded from the Hugging Face hub (openai/openai_humaneval)
and treated as untrusted data.

Colab:
    !python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec
Output: results/forgetting_humaneval.json (pass@1 per model, difference, per-problem results).
Use --limit 20 for a quick test first. Default output file: results/forgetting_humaneval_<prompt>.json.
"""

from __future__ import annotations
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from src.prompting import build_prompt

STOP = ["\ndef ", "\nclass ", "\nif __name__", "\nprint(", "\nassert ", "\n#"]


def build_humaneval_prompt(stub: str, mode: str) -> str:
    """plain: the raw function stub, the model continues the body. instruction: the training format."""
    if mode == "plain":
        return stub
    if mode == "instruction":
        return build_prompt(stub)
    raise ValueError(f"prompt mode must be 'plain' or 'instruction', got {mode!r}")


def relative_change(base: float, finetuned: float):
    """(finetuned - base) / base, or None when the base score is 0 (undefined)."""
    return None if base == 0 else round((finetuned - base) / base, 4)


def cut_completion(text: str) -> str:
    """Keep the function body: stop at the first line that starts at column 0 after the stub."""
    end = len(text)
    for s in STOP:
        i = text.find(s)
        if i != -1:
            end = min(end, i)
    return text[:end]


def generate(tokenizer, model, prompt: str, max_new_tokens: int) -> str:
    import torch
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=max_new_tokens, do_sample=False,
                             stop_strings=STOP, tokenizer=tokenizer, pad_token_id=tokenizer.eos_token_id)
    return tokenizer.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True)


def run_program(source: str, timeout: int = 10) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "prog.py"
        path.write_text(source, encoding="utf-8")
        try:
            r = subprocess.run([sys.executable, "-I", str(path)], cwd=tmp, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False
        return r.returncode == 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", required=True)
    ap.add_argument("--4bit", dest="use_4bit", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-new-tokens", type=int, default=384)
    ap.add_argument("--prompt", choices=["plain", "instruction"], default="plain",
                    help="plain = raw HumanEval stub for both models (valid forgetting measure, default); "
                         "instruction = training wrapper (first, invalid run)")
    ap.add_argument("--output", default=None, help="default: results/forgetting_humaneval_<prompt>.json")
    ap.add_argument("--config", default="configs/config.yaml")
    ap.add_argument("--allow-exec", action="store_true",
                    help="confirm that you are on a throw-away machine (Colab): model-generated code is executed")
    args = ap.parse_args()
    if not args.allow_exec:
        ap.error("this runs model-generated code; use it on Colab only and pass --allow-exec")

    from datasets import load_dataset
    from src.generation import load_model
    from src.utils.config import load_config

    cfg = load_config(args.config)
    problems = list(load_dataset("openai/openai_humaneval", split="test"))
    if args.limit:
        problems = problems[:args.limit]
    tokenizer, model = load_model(cfg.llm.model, args.adapter, args.use_4bit)

    results = {"base": [], "finetuned": []}
    for name in results:
        for p in problems:
            prompt = build_humaneval_prompt(p["prompt"], args.prompt)
            if name == "base":
                with model.disable_adapter():
                    raw = generate(tokenizer, model, prompt, args.max_new_tokens)
            else:
                raw = generate(tokenizer, model, prompt, args.max_new_tokens)
            body = cut_completion(raw)
            program = p["prompt"] + body + "\n\n" + p["test"] + f"\n\ncheck({p['entry_point']})\n"
            results[name].append({"task_id": p["task_id"], "passed": run_program(program)})
        print(f"{name}: {sum(r['passed'] for r in results[name])}/{len(problems)}")

    pass1 = {k: round(sum(r["passed"] for r in v) / len(v), 4) for k, v in results.items()}
    rel = relative_change(pass1["base"], pass1["finetuned"])
    if rel is None:
        print("WARNING: base pass@1 is 0, so the relative change is undefined. A 1.5B code model should not score 0 "
              "on HumanEval with the plain prompt: check the generated completions before trusting this run.")
    out = {"n_problems": len(problems), "prompt": args.prompt, "pass@1": pass1, "relative_change": rel,
           "adapter": args.adapter, "per_problem": results}
    output = Path(args.output or f"results/forgetting_humaneval_{args.prompt}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"pass@1 {pass1}, relative change {rel}. Saved {output}")


if __name__ == "__main__":
    main()
