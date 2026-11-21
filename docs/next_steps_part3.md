# Next steps, Part 3: after the first GPU session (written 2026-11-21)

Follows `docs/colab_steps_part2.md` (setup, pilot and extras, all done). This file is the order of work from here, split
into what you do **locally** and what you do on **Colab**. Background and troubleshooting: `docs/colab_steps.md`.
The record of what was found: `docs/progress_log.md`, Entries 32 to 35; numbers in `docs/results_summary.md`.

## Where the project stands

**About 65% of the project work is done (read as 62 to 68%; thesis writing not counted).** A weighted judgement
(Entry 35), not a measurement.

| Workstream | Weight | Done | Status |
|---|---|---|---|
| Plan, reference-paper analysis, hypotheses | 5.7% | 100% | Finished |
| CrossCodeEval data | 11.4% | 100% | Finished |
| RepoBench data | 8.0% | 90% | Nearly finished |
| Pipeline code | 17.0% | 97% | Runs end to end on a T4 |
| Retrieval (indexes, dense vs BM25 vs random, both datasets) | 9.1% | 87% | Done |
| Fine-tuning | 11.4% | 60% | CrossCodeEval adapter + loss comparison done; no RepoBench run, no RAFT variant |
| Evaluation runs | 28.4% | 25% | Pilot (n=50) done in 4 variants; **no full 543-example run; base/RAG prompt unresolved** |
| Extra analyses | 9.1% | 40% | Staleness view, shorter code, BM25 run; **forgetting check invalid**; hit/miss, noise, top-k, NEW-relevant subset not run |

What the pilot showed (n=50, not findings): fine-tuned and hybrid score far above base and RAG (edit similarity
0.61 to 0.66 vs 0.21 to 0.26); hybrid vs fine-tuned, dense vs BM25, staleness view and shorter code are all within noise.
Base exact match is 0 of 50 and base HumanEval 0 of 20, which suggests the base/RAG deficit is a **prompt-format
artifact**. Settling that is the first job, because every later comparison depends on it.

Rules for everything below: stop and copy the full output when a step fails; report pilot numbers as "pilot, n=50";
never paste tokens or passwords into a cell or file.

---

## PHASE 1. Local, no GPU (do first; about 1 to 2 hours)

**L1. Download the Colab results.** From Drive `MyDrive/thesis/outputs/results/` into this project's `results/`:
`pilot_main/`, `pilot_staleness/`, `pilot_main_code480/`, `pilot_main_bm25/`, `pipeline_test/`,
`val_loss_base_vs_adapter.json`, `forgetting_humaneval.json`. (Each folder has `predictions.jsonl`; they are gitignored.)

**L2. Read the base and RAG predictions** (the key check). In a terminal at the project root:
```
python -I -c "import json,itertools; rows=map(json.loads, open('results/pilot_main/predictions.jsonl', encoding='utf-8')); [print(r['task_id'], '| REF:', r['reference'], '| BASE:', repr(r['base']['prediction']), '| RAG:', repr(r['rag_only']['prediction']), '| FT:', repr(r['finetuning_only']['prediction'])) for r in itertools.islice(rows, 15)]"
```
This prints the reference next to the base, RAG and fine-tuned outputs for the first 15 rows (change `15` to see more). Look for:
- base or RAG outputs that are empty, repeat the prompt, continue with several lines, or are unrelated code;
- fine-tuned outputs that are close to the reference.

Decision from what you see:
| What you see | Meaning | Next |
|---|---|---|
| Base/RAG outputs are junk, empty or run-on | Prompt-format artifact | Do L4 (build a base-friendly prompt), rerun on Colab (C1) |
| Base/RAG outputs are plausible code but wrong | The deficit may be real | Still run C1 once to confirm; then proceed to the full run |
| Mixed | Report which rows | Send me 5 examples of each |

**L3. Hit-versus-miss and paired differences** (no GPU):
```
python -m src.evaluation.analyze_predictions results/pilot_main/predictions.jsonl
python -m src.evaluation.analyze_predictions results/pilot_staleness/predictions.jsonl
```
Writes `analysis.json` next to each file. Send me the output; I log it as the next entry.

**L4. DONE (2026-11-21, Entry 37): the three pieces the Colab steps need were built and tested locally** (decision (a):
plain continuation prompt for base and RAG). 34 tests pass and the dry run passes. They reach Colab only after L5 (push).
1. **A base-friendly prompt option for `run_comparison`** (for base and RAG; for example the plain code prefix, or a
   few-shot prompt), recorded in the metrics file and in the output folder name, default unchanged.
2. **A plain-stub option for `forgetting_check`** (both models get the raw HumanEval stub with no instruction wrapper),
   plus a guard against dividing by a zero base score.
3. **A subset filter for the 68 NEW-relevant CrossCodeEval TEST examples** (relevant file in NEW), for the real staleness
   test (H3). Expected count: 68.
Not built (lower priority): a pilot that includes retrieval misses; a repetition guard for the hybrid.

**L5. Commit and push** (you do this; Claude Code does not push): the new code, `docs/next_steps_part3.md`, and the
updated docs. Colab clones from GitHub, so nothing built in L4 reaches Colab until it is pushed.

**L6. Optional local work while waiting:** plots for the pilot results (a bar chart of edit similarity and identifier
accuracy by system and variant); the RepoBench retrieval plot; update `docs/claude_web_prompt.md` (it still says 58% and
"no completion score exists") before using it for the report and slides.

---

## PHASE 2. Colab session A: settle the prompt question and fix the forgetting check (about 40 minutes of GPU)

Do not start until L2 is done and L4 is pushed.

**C0. Setup (same as before):** T4 GPU; Cell 1 (Drive), Cell 2 (clone), Cell 3 (`!python tools/colab_setup.py`, all
checks `ok`), Cell 4 (imports and adapter check, see `docs/colab_steps_part2.md` section A).

**C1. Rerun the pilot with the plain prompt for base and RAG** (50 examples, main view):
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain
```
Success: `results/pilot_main_plainbase/` with all four systems (fine-tuned and hybrid should be identical to the first pilot).
Read the base and RAG predictions in `predictions.jsonl` BEFORE looking at scores: they should now be code continuations.
Read the result against `results/pilot_main/`:
- if base and RAG edit similarity rises a lot, the earlier deficit was a prompt artifact: the thesis compares systems
  "same task, best format per system", and states it;
- if it does not, the deficit is real and the comparison stands as it is.

**C2. Forgetting check, plain stub, all 164 problems** (Colab only; runs model-generated code):
```python
!python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec
```
(default prompt is `plain`; result in `results/forgetting_humaneval_plain.json`). Expect about 15 to 25 minutes. Success: base pass@1 is well above 0 (reported around 40% for this model; verify the figure in the Qwen2.5-Coder
report before citing it), and a relative change is printed. If base is still near 0, stop and send the output.

**C3. NEW-relevant subset, main and staleness views** (68 examples; the real test of "RAG handles new files, fine-tuning
does not"), both views; 68 examples from 35 repositories:
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant --view staleness
```
Outputs: `results/new_relevant_main_plainbase/` and `results/new_relevant_staleness_plainbase/`. Expect about 6 to 8
minutes each. In the main view the relevant NEW file cannot be retrieved; in the staleness view it can.

**C4. Finish:** download all new `results/` folders to your computer (Drive `MyDrive/thesis/outputs/results/`), then
Runtime > Disconnect and delete runtime. Send me the outputs; they become Entry 38.

---

## PHASE 3. Colab session B: the full CrossCodeEval comparison (about 3 hours of GPU; the main result)

Start only after Phase 2 has settled the prompt (a full run with a handicapped base wastes about 80 minutes per view).
Setup as in C0. Use the prompt variant Phase 2 decided on. Run one cell at a time; each writes to its own folder.

**F1. Full test set, main view** (543 TEST examples, four systems; about 75 to 80 minutes):
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --subset test
```
**F2. Full test set, staleness view** (about 75 to 80 minutes):
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --subset test --view staleness
```
Add `--retriever bm25` runs if time allows (about 6x faster retrieval, same completion in the pilot). Because Colab
can disconnect, run F1 and F2 in separate sessions if needed; each run finishes before it writes, so a disconnect loses
that run, not earlier ones.

**F3. Extras on the pilot or the NEW-relevant subset** (about 7 minutes each):
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --noise-chunks 3
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --top-k 1
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --top-k 3
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --top-k 10
```
(noisy-context test and top-k sweep; default top-k is 5.)

**Locally afterwards:** `python -m src.evaluation.analyze_predictions results/<run>/predictions.jsonl` for each
full run (hit vs miss, paired differences with 95% intervals), then send me the outputs (Entry 37).

---

## PHASE 4. RepoBench (about 5 hours of GPU, most of it fine-tuning)

1. Colab Cell 3 with both datasets: `!python tools/colab_setup.py --datasets crosscodeeval repobench` (first time it
   builds the 300-per-setting sample and indexes on the GPU; not yet run on Colab).
2. Fine-tune the RepoBench adapter (10,800 training examples; expect roughly 3 to 4 hours on a T4, one session's quota):
   ```python
   !python -m src.finetuning.trainer --dataset repobench --run-name v2
   ```
   Resumes from checkpoints after a disconnect (rerun the same command).
3. `run_comparison` has **no RepoBench support yet**: ask Claude Code to build it (reads `data/processed/repobench/` and the
   300-per-setting sample, per-setting results, gold-file retrieval rule), test it locally, push, then run both settings
   (`cross_file_first`, `cross_file_random`) on Colab.
If GPU time runs out, plan B from the plan file: report RepoBench as retrieval-only (already done, Entry 28) and state
the limitation.

---

## PHASE 5. Local wrap-up and decisions

- Decide on the RAFT-style retrain (hybrid sees retrieved context at inference that the adapter never saw in training).
  Only worth the extra roughly 3.5-hour training run if the full run shows the hybrid under-using retrieval.
- Move seeds and constants into `configs/config.yaml` (housekeeping, Claude Code can do it; do it after the runs so
  the saved data stays identical).
- Numeric recommendations for the decision question (thresholds, accuracy gain per added latency and per added GB).
- Update `docs/claude_web_prompt.md` with the real results; produce the updated report and presentation from it.
- Tell the supervisor about the scope changes (plan Section 11).

## What moves the percentage

| Step | Adds roughly |
|---|---|
| Phase 1 and 2 (prompt question, valid forgetting check, NEW-relevant staleness test) | +4 to 5 points |
| Phase 3 (full CrossCodeEval comparison and extras) | +12 to 15 points |
| Phase 4 (RepoBench fine-tuning and completion) | +8 to 10 points |
| Phase 5 (decisions, recommendations, housekeeping) | +3 to 4 points |

## Quick fixes

| What you see | Do this |
|---|---|
| `No module named ...` | Re-run Cells 1, 2, 3, then the imports check |
| `DIFFERS` / `MISSING` in the data check | Do not run anything else; send the output |
| `out of memory` | Runtime > Restart session, rerun from Cell 1; note which system failed |
| Colab disconnected during a run | Re-run Cells 1 to 3, then start that run again |
| `unrecognized arguments: --base-prompt` or `--subset new_relevant` | The new code was not pushed; do L5 (push), then re-run Cell 2 |
