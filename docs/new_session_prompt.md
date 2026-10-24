# Prompt to start a new Claude Code session

Paste everything inside the block below into the new session.

```
I'm continuing a thesis project in D:\Users\nidwija.bhatta\Documents\Automation\Thesisbaseline1
(RAG vs fine-tuning vs hybrid for repository-level code completion, Qwen2.5-Coder-1.5B,
CrossCodeEval + RepoBench, Python only).

Read these two files first, in this order, and confirm you have read them:
1. docs/things_to_do_first  - my plan and framework. Stay close to it; don't deviate a lot
   and don't rely on raw repo data beyond the benchmarks.
2. docs/progress_log.md     - everything done so far (Entries 1-11), the decisions made,
   and a "Notes for thesis writing" section. Use it instead of re-deriving anything.

State at the end of the last session:
- Plan Sections 1-3 are implemented for both datasets: split manifests, pools, and
  leakage-checked fine-tuning corpora are in data/processed/{crosscodeeval,repobench}/.
  Scripts: src/preprocessing/build_{crosscodeeval,repobench}_{split,finetune}.py.
- A3 (CrossCodeEval relevance rule) is settled (Entry 4). RepoBench uses both cross-file
  settings with one shared split (Entries 6, 10). Hybrid pipeline peft import is fixed (Entry 9).
- I was in the middle of Section 9, step 5 prep: the per-repo retrieval index. I wrote
  src/preprocessing/chunker.py::chunk_text and src/retrieval/build_indexes.py
  (per-repo FAISS, "main" = BASE and "staleness" = BASE+NEW views, TEST asserted absent).
  They have NOT been run yet and are NOT yet in the progress log (this would be Entry 12)
  and NOT yet committed.
- Sizing facts for the index: 931 chunks (806 BASE, 125 NEW) at 256 lines / 32 overlap;
  median chunk is about 1,045 UniXcoder tokens, and the model window is 1,026, so roughly
  half of each chunk's tokens are cut. Keep the plan's 256 lines and report this as a
  limitation. rank_bm25 is not installed (needed for the BM25 baseline, Section 9, step 7).

Next steps, in order:
1. Run build_indexes.py on one or two repos with --repos first, check the output, then
   all 206 repos; add a small sanity retrieval; log it as Entry 12.
2. Then the pilot (Section 9, step 5): all three systems on about 50 CrossCodeEval TEST
   examples. This still needs: a trainer pointed at data/processed/crosscodeeval/finetune/
   train.jsonl and val.jsonl (current trainer.py reads the old data/processed/train.jsonl),
   evaluation wiring in experiments/run_comparison.py (its prompt format differs from
   training and its adapter loading is wrong, see Entry 9), and a seeded rule for picking
   the 50 examples.

Open items to remember (all in the log):
- RepoBench TEST set is large (about 12k examples); it needs a seeded sampling rule if GPU
  time is tight. The RepoBench corpus is capped at 12,000 examples (a compute-matching
  choice that is not in the plan; I haven't confirmed it).
- Seeds and constants live in the scripts, not config.yaml.
- Old src/preprocessing/prepare_datasets.py is no longer used and has the outdated design.

How I want you to work:
- Don't run in auto mode. Tell me what you plan to do and ask before running anything or
  making changes; stop after writing a script and before running it.
- After each step, add an entry to docs/progress_log.md: what was asked, what you did, what
  you found (with numbers), and anything left open.
- I write the thesis text myself; just note hypotheses and points for me in the log.
- Don't put secrets in code, configs, or logs. Raw datasets under data/ are gitignored and
  must stay out of commits (GitHub's 100 MB limit); commit or push only when I ask.
- Windows machine, Git Bash, CPU-only torch, venv at ./venv (use venv/Scripts/python.exe).
- If something is uncertain, say so and give me a recommendation instead of guessing.
```

## Notes for you (not part of the prompt)
- Uncommitted: `chunker.py`, `build_indexes.py`, the "Notes for thesis writing" section
  of the log, and this file. They are on disk, so a new session in the same folder sees them.
- `data/processed/` and `data/embeddings/` are gitignored. If you clone the repo somewhere
  else, re-run the preprocessing scripts to regenerate them.
- Run commands from the project root, e.g. `python -m src.retrieval.build_indexes --repos <repo>`.
