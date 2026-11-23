# Next steps for the presentation: complete the pilot run with the fixed prompts (scope set with the supervisor, 2026-11-23)

**Scope agreed with the supervisor.** For the upcoming presentation: finish the pilot (50 CrossCodeEval examples) with the
fixed prompts, do a basic evaluation of those results, and compare the direction of the findings with the literature (Wang et
al. 2025, already analysed in `docs/reference_paper_comparison.md`). Heavier work (full 543-example run, RepoBench training and
completion, RAFT-style retrain, extra sweeps) moves to the thesis wrap-up. Report everything as **"pilot, n=50"**.

Detailed Colab cell-by-cell setup is in `docs/colab_steps_part2.md` (section A). The prompt story (what went wrong and the fix) is
in `docs/progress_log.md`, Entries 36 and 37.

## What "done" means for the presentation
1. A valid four-system pilot (base, RAG, fine-tuned, hybrid) where base and RAG actually attempt the task (plain prompt).
2. The same pilot with the staleness view (new files in the index).
3. A basic evaluation: exact match, edit similarity, identifier accuracy, CodeBLEU with intervals; paired differences; cost
   (time and GPU memory); a few example outputs.
4. A short comparison with the literature: does the direction match Wang et al.? (not the absolute numbers).
5. Updated slides and report text from `docs/claude_web_prompt.md`.

## STEP 1. Local, before Colab (about 20 minutes)
1. **Commit and push** (you do this). Colab clones from GitHub, so the new options (`--base-prompt`, `--subset new_relevant`,
   `--prompt` for HumanEval) exist on Colab only after the push. Files changed: `src/prompting.py`, `experiments/run_comparison.py`,
   `experiments/dry_run_pipeline.py`, `src/evaluation/forgetting_check.py`, `tests/test_prompting.py`, the two edited test files,
   and `docs/`.
2. Optional sanity check: `venv\Scripts\python -m pytest -q` (expect 34 passed).

## STEP 2. Colab session (T4 GPU; about 35 to 60 minutes of GPU)
**Follow `docs/colab_steps_new.md` for the exact cells (it adds a 5-example gate test before the pilot). The list below is the summary.**
Setup as before: GPU runtime; Cell 1 (Drive), Cell 2 (clone), Cell 3 (`!python tools/colab_setup.py`, every check `ok`), Cell 4 (imports
and adapter check from `docs/colab_steps_part2.md`). If Cell 3 or any run errors, stop and send the full output.

**Core runs (needed for the presentation):**
- **P1. Pilot, main view, plain prompt for base and RAG (about 7 min):**
  ```python
  !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain
  ```
  Output: `results/pilot_main_plainbase/`. **Gate: before looking at scores, check that base and RAG now write code continuations**
  (print a few rows of `predictions.jsonl`, or send them to me). Fine-tuned and hybrid should be identical to the first pilot
  (same prompt, greedy decoding): edit similarity 0.613 and 0.644. If base and RAG are still imports, comments or sentences, stop:
  send me the output and we switch to option (b) (few-shot) instead of burning more GPU time.
- **P2. Pilot, staleness view, plain prompt (about 7 min):**
  ```python
  !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --view staleness
  ```
  Output: `results/pilot_staleness_plainbase/`.

**Recommended extras (about 7 to 15 min each; do them if the session is going well; each answers a hypothesis in the literature):**
- **P3. BM25 retrieval, plain prompt** (Wang et al.: BM25 beats dense): add `--retriever bm25` to the P1 command. Output:
  `results/pilot_main_bm25_plainbase/`.
- **P4. The staleness test proper, 68 examples whose relevant file is new** (H3; both views):
  ```python
  !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant
  !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant --view staleness
  ```
- **P5. Forgetting check on HumanEval, plain stub** (Wang et al.: fine-tuning lowered pass@1 by 24.1% on average); runs model-generated
  code, Colab only; about 15 to 25 minutes for 164 problems (use `--limit 40` if time is short):
  ```python
  !python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec
  ```
  Success: base pass@1 clearly above 0. If it is still 0, the script prints a warning; send me the output.

**Skip for now (thesis wrap-up):** full 543-example run, RepoBench fine-tuning and completion, noise and top-k sweeps, `--max-code-tokens`
reruns, RAFT-style retrain, multiple seeds.

**Finish:** make sure the new folders are on Drive (`MyDrive/thesis/outputs/results/`), download them, then Runtime > Disconnect and
delete runtime. The session cost is the only quota-sensitive part (about 30 min core, about 1 hour with all extras).

## STEP 3. Local, after Colab (about 1 to 2 hours; send me the folders, I do the analysis)
1. Copy the new folders from Drive into this project's `results/` (same as last time; do not overwrite older folders):
   `pilot_main_plainbase/`, `pilot_staleness_plainbase/`, and any of `pilot_main_bm25_plainbase/`, `new_relevant_*_plainbase/`,
   `forgetting_humaneval_plain.json`.
2. Tell me "results added". I will: read the base and RAG predictions first; run `analyze_predictions` on each run (paired differences
   with 95% intervals; hit-vs-miss only if there are enough misses); compare against the first pilot; write the findings as the next
   progress-log entry.
3. **Basic evaluation I will produce (and you can follow):**
   - table: exact match, edit similarity, identifier accuracy, CodeBLEU per system, main and staleness, with intervals;
   - paired differences: RAG vs base, fine-tuned vs base, hybrid vs RAG, hybrid vs fine-tuned (what is and is not significant at n=50);
   - cost: average time per example and peak GPU memory per system, plus retrieval time;
   - 5 to 6 side-by-side example outputs (one cut line, the four answers) for the demo, including a failure case;
   - effect of retrieval quality (dense vs BM25) if P3 was run; staleness result if P4 was run; forgetting if P5 was run.
4. **Comparison with the literature** (direction of effects, never absolute scores): a one-page table from
   `docs/reference_paper_comparison.md`: Wang et al.'s findings (RAG beats fine-tuning alone; combination best; BM25 beats dense;
   retrieval raises input length and slows inference; fine-tuning hurts general code ability) against this pilot (match / differ /
   cannot say), with the reasons for each difference (public Python vs one company's C++; QLoRA 1.5B vs full fine-tuning; 50
   examples vs 50,000; small per-repository pools). Findings already available without the rerun: BM25 beat dense in retrieval on both
   datasets (agrees with Wang et al.); retrieval prompts are about 2,000 tokens vs 437 and cost more time and memory (agrees).
5. Update `docs/claude_web_prompt.md` with the new numbers and then use it to draft the presentation and the progress report.

## STEP 4. Presentation content (suggested; the web prompt has the full outline)
Problem and decision question; what changed since September; three systems; data split and leakage checks; datasets in numbers;
retrieval results; fine-tuning run; **how the prompts were chosen (one slide: the example, the four answers, the fix)**; pilot
results (main and staleness) with caveats; comparison with the literature; how much is done; what moves to the thesis wrap-up
(full evaluation, RepoBench, heavier training); risks and limitations; thank you.

## If something goes wrong
| What you see | Do this |
|---|---|
| `unrecognized arguments: --base-prompt` | The push did not happen or Cell 2 used an old clone; push, re-run Cell 2 and Cell 3 |
| `No module named ...` | Re-run Cells 1, 2, 3, then the imports check |
| `DIFFERS` or `MISSING` in the data check | Do not run anything else; send the output |
| Base and RAG still write imports, comments or sentences | Stop after P1; send 10 rows of `predictions.jsonl` |
| `out of memory` | Runtime > Restart session; rerun from Cell 1; note which system failed |
| Disconnected | Re-run Cells 1 to 3; start the unfinished run again (each run writes only at the end) |
