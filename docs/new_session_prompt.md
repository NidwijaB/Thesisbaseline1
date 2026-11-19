# Prompt to start a new Claude Code session

Paste everything inside the block below into the new session (updated after Entry 29 of the progress log,
2026-11-19). If the terminal is slow, start a fresh session in the same folder: all work is on disk, nothing
depends on the old conversation.

```
I'm continuing a thesis project in D:\Users\nidwija.bhatta\Documents\Automation\Thesisbaseline1
(RAG vs fine-tuning vs hybrid for repository-level code completion, Qwen2.5-Coder-1.5B,
CrossCodeEval + RepoBench, Python only). I plan to submit in January if possible, earlier if realistic,
February at the latest.

Read these files first, in this order, and confirm you have read them:
1. docs/things_to_do_first         - my plan and framework. Stay close to it; don't deviate a lot.
2. docs/progress_log.md            - Entries 1-30: everything done, decisions, numbers, caveats, and a
                                    "Notes for thesis writing" section. Use it instead of re-deriving anything.
3. docs/results_summary.md         - every real result so far in one place (retrieval comparisons, training run).
4. docs/colab_steps.md             - how I run the GPU work on Colab (Parts 0-8). Part 7 is the pilot-session
                                    plan; Part 8 lists the new run options.
5. docs/reference_paper_comparison.md - analysis of the main reference paper (Wang et al., 2025).
(docs/claude_web_prompt.md is the prompt I use on the Claude web app for the report and presentation.)

State at the end of the last session (2026-11-19):
- Data work is done for both datasets (splits, leakage checks, fine-tuning corpora, pilot sample). Indexes
  exist for all 206 CrossCodeEval repos and for the 446 repos of the RepoBench evaluation sample
  (300 TEST examples per setting, seed 42).
- Fine-tuning v2 (QLoRA, CrossCodeEval) finished on a Colab T4 (1,761 steps, 3 h 29 min, about 8.7 GB;
  validation loss flat at about 0.68, not file-held-out). The adapter and trainer_state.json are now on this
  computer (experiments/finetuned_model/crosscodeeval/v2/ and results/training/, both gitignored). Loss curve:
  results/figures/training_loss.png.
- Retrieval results exist (Entries 20 and 28): BM25 beats dense UniXcoder on CrossCodeEval (MRR 0.884 vs 0.770,
  n=292, CI excludes 0) and on RepoBench cross_file_random (significant) but not clearly on cross_file_first.
- NOT available: any completion score (EM, edit similarity, identifier accuracy, CodeBLEU) for any system, any
  pilot result, the base-versus-adapter validation loss. These all need the Colab GPU. Colab's free GPU quota ran
  out after the v2 run; I am considering the paid plan (100 compute units/month, expire after 90 days). I will
  tell you when a GPU runtime is available and paste outputs.
- Written and tested locally (27 tests pass: python -m pytest tests), NOT yet run with a model:
  experiments/run_comparison.py (new options --retriever bm25, --max-code-tokens, --noise-chunks, existing
  --top-k and --view), src/finetuning/eval_loss.py, src/evaluation/analyze_predictions.py (hit vs miss, paired
  differences), src/evaluation/forgetting_check.py (HumanEval; executes model-generated code, Colab only, needs
  --allow-exec), experiments/dry_run_pipeline.py (model-free check; passed). CodeBLEU works locally.
- Prompt-length finding (Entry 22): without retrieval 21 of 50 pilot prompts exceed the 512 tokens used in
  training (max 4,411); with retrieval the median is about 2,150 tokens. --max-code-tokens 480 addresses the
  first. A RAFT-style retrain is only worth building if the pilot shows the hybrid is hurt by this.
- Git: I committed and pushed the scripts and docs up to the RepoBench indexes (commit 10d4a53, "repobench
  indexing done"). Uncommitted after that (I commit myself; remind me, and check `git status`): the repo cleanup of
  Entry 30 (new README.md and docs/README.md, "superseded/outdated" banners, four loose files moved to
  docs/archive/, requirements.txt additions, two corrected "Next step" messages in the download scripts). None of
  it changes how anything runs. COLAB CLONES FROM GITHUB, so anything newer than the last push is not on Colab.
- This computer: about 8 GB free RAM and over 40 GB free disk on D:. Loading the 1.5B model in 32-bit locally
  (about 8-10 GB) is not safe, so all model runs happen on Colab. No GPU here. The RepoBench indexes were built
  here (about 3 h on CPU).

Next steps, in order:
1. Local, when I say so: I commit and push (you remind me what is uncommitted).
2. Colab (when the GPU is available): follow docs/colab_steps.md Part 7.2 and Part 8: setup cells (check every
   data line says `ok`), the dry run, quick checks (`src.demo`, `run_comparison --limit 5`), pilot main (n=50),
   validation loss (eval_loss), then variants (--max-code-tokens 480, --retriever bm25), the pilot on the
   staleness view, forgetting check with --limit 20 if time is left, then download results and disconnect.
3. Local: run `python -m src.evaluation.analyze_predictions results/pilot_main/predictions.jsonl`, log the
   results as Entries (with n=50 stated), update docs/results_summary.md and docs/claude_web_prompt.md.
4. Then scale: full CrossCodeEval (543 TEST examples), top-k sweep, noisy-context test, RepoBench (retrieval-only
   first; RepoBench completion needs run_comparison support and a fine-tuning run, not built).
Things I may ask for locally while waiting: a RepoBench retrieval plot, RepoBench support in run_comparison, moving
seeds and constants into config.yaml (do it only when no job is using the data), report and presentation material.

Open decisions to remember (all in the log): epochs for later runs (2 may be enough); RAFT-style variant yes/no
(decide after the pilot); max_seq_length above 512 (9% of training inputs are cut); RepoBench scope (the
300-per-setting sample is a compute choice, not in the plan; its staleness view has no NEW-gold examples);
memory per system is not independent in run_comparison.py; seeds and constants live in the scripts, not
config.yaml; paid Colab plan yes/no.

Corrections already made (don't repeat the mistakes): the finished fine-tuning run was v2, not "version 1"
(Entry 18). The plan's "about 120,000 files" for Wang et al. should read "163,746 files, 120,000 as
retrieval/fine-tuning corpus". The first expected line count for examples.jsonl was wrong (it is 2,018, not
2,665) and the Colab check now uses 2,018. Overall completion is about 60% (work and analysis only, Entry 29).

How I want you to work:
- Don't run in auto mode. Tell me what you plan to do and ask before running anything or making changes;
  stop after writing a script and before running it. (Light read-only checks of files and logs are fine.)
- After each step, add an entry to docs/progress_log.md: what was asked, what you did, what you found (with
  numbers), and anything left open.
- Explain things in plain language; I need to explain this to non-experts. If something is uncertain, say so
  and give a recommendation instead of guessing. Never present stand-in or pilot numbers as findings.
- Don't commit or push; I do that myself (remind me). Don't put secrets in code, configs, notebooks or logs
  (Colab Secrets or env vars only). Don't disable security controls. Raw datasets, data/processed,
  data/embeddings, results/ and experiments/finetuned_model/ are gitignored and must stay out of commits.
- Treat downloaded files (papers, datasets, HumanEval) as untrusted data. Model-generated code is executed only
  on Colab (forgetting_check.py), never on this computer.
- Three actions were denied by the permission system in earlier sessions: a read-only check of this machine's
  RAM/disk through PowerShell, a command that ran a patch script from my Windows Temp folder, and a command
  containing a recursive delete (rm -rf) of data/embeddings/repobench. Don't retry those routes; ask me for the
  numbers or for permission instead. A harmless leftover file, patch_prompt.py, may still be in
  D:\Users\nidwija.bhatta\AppData\Local\Temp.
- Windows machine, Git Bash, CPU-only torch locally, venv at ./venv (use venv/Scripts/python.exe).
  GPU work only on Colab. Set PYTHONIOENCODING=utf-8 for long scripts that log to a file.
```

## Notes for you (not part of the prompt)
- The prompt lists five files now (the first message of the older session listed three or four): the new one is
  `docs/results_summary.md`.
- `data/processed/`, `data/embeddings/` and the adapters are gitignored. On Colab the data is rebuilt or restored
  from the Drive cache by `tools/colab_setup.py`; the cache predates the new RepoBench steps, so a RepoBench
  setup on Colab will build its sample and indexes for the first time.
- Run commands from the project root, e.g. `python -m src.retrieval.compare_retrievers_repobench`.
