# Colab steps (new): Project Part 1 pilot with the fixed prompts

Follow this top to bottom in one Colab session. It replaces the Colab parts of `docs/colab_steps_part2.md` and
`docs/next_steps_part3.md` for Part 1 (background and older troubleshooting are still in `docs/colab_steps.md`).
Revised 2026-11-23 after the first attempt hit three setup problems; each fix is built into the steps below.

**What this session produces:** a valid four-system pilot (base, RAG, fine-tuned, hybrid) on the 50 CrossCodeEval pilot
examples, where base and RAG now get a plain continuation prompt, in two views (main and staleness), plus optional extras.
Report everything as "pilot, n=50".

**GPU time:** about 30 minutes for the core (sections A to C), about 1 hour with all extras (D).
**If the free quota ends early, do them in this order:** B3, C1, C2, then D1, D2, D3.

## Rules (read once)

1. **Run one cell at a time** and wait for it to finish. If a cell errors, stop and copy the **full** output (from the top of
   the error, not only the last line). Never paste tokens or passwords into a cell.
2. **The order rule (this caused the first failures):** Cell 2 deletes the project folder and clones it again, which wipes the
   restored data. So **Cell 3 must run straight after Cell 2, with nothing in between.** Do not run any `python -m ...` or
   other command that writes files before Cell 3 has finished: if something writes into `results/` first, Cell 3 stops with
   `results already has files; refusing to replace it`.
3. **If anything looks wrong at any point, the reset is always:** Cell 1 (if the runtime restarted), then Cell 2, then Cell 3,
   then Cell 4. It is safe (the data comes back from the Drive cache in about a minute; nothing on Drive is deleted).
4. Before you start, on your computer: **commit and push** the repository. Colab clones from GitHub; the new options
   (`--base-prompt`, `--subset new_relevant`, `--prompt` for HumanEval) exist on Colab only after the push.

---

## A. Setup (about 5 minutes; cells in this exact order)

**A1.** Runtime > Change runtime type > **T4 GPU** > Save.

**A2. Cell 1, connect Drive**
```python
from google.colab import drive
drive.mount("/content/drive")
```
Success: `Mounted at /content/drive`.

**A3. Cell 2, get the latest code** (deletes the old copy and clones fresh)
```python
import os, shutil, subprocess
if os.path.exists("/content/Thesisbaseline1"):
    shutil.rmtree("/content/Thesisbaseline1")
subprocess.run(["git", "clone", "--depth", "1",
                "https://github.com/NidwijaB/Thesisbaseline1", "/content/Thesisbaseline1"], check=True)
os.chdir("/content/Thesisbaseline1")
# The repository on GitHub currently contains a results/ folder (committed by mistake). It would stop
# Cell 3 ("results already has files"), so remove the cloned copy; the real results live on Drive.
results_dir = "/content/Thesisbaseline1/results"
if os.path.isdir(results_dir) and not os.path.islink(results_dir):
    shutil.rmtree(results_dir)
    print("removed the cloned results/ folder (Drive results are untouched)")
```
Success: no red error text (the "removed the cloned results/ folder" line is expected until the repository is cleaned, see the
note below). **Now run Cell 3 immediately.**

*Permanent fix (on your computer, once):* the `results/` files were committed to git before `.gitignore` listed them, so they are still
tracked and every clone contains them. Stop tracking them (the files stay on your disk):
`git rm -r --cached results`, then commit and push. After that the removal block in Cell 2 does nothing and can stay.

**A4. Cell 3, setup script** (installs libraries, links Drive, restores the data)
```python
!python tools/colab_setup.py
```
Success (check all of these):
- `[3/5]` prints `cuda: True` and `gpu: Tesla T4`;
- `[4/5]` prints both links: `experiments/finetuned_model -> ...` and `results -> ...`;
- `[5/5]` prints `restoring crosscodeeval from .../crosscodeeval_data.tar`;
- every "Checking data" line starts with `ok` (train 9378, val 1059, pilot_ids 50, 206 index folders, examples.jsonl 2018);
- the last line is `Setup finished.`

If you see `results already has files; refusing to replace it`, rule 2 was broken: run the reset (rule 3).
If `[5/5]` says `no cache ... rebuilding`, or any check line says `DIFFERS` or `MISSING`: stop and send me the output.

**A5. Cell 4, check installs, adapter and that the new code arrived**
```python
!python -c "import rank_bm25, peft, bitsandbytes, faiss, transformers, sentence_transformers; print('imports ok')"
!ls -la experiments/finetuned_model/crosscodeeval/v2
!ls data/processed/crosscodeeval/examples.jsonl
!python -m experiments.run_comparison --help | grep -E "base-prompt|new_relevant"
```
Success:
- `imports ok`;
- the adapter folder lists `adapter_config.json` and `adapter_model.safetensors`;
- `data/processed/crosscodeeval/examples.jsonl` is listed (not "No such file");
- the last command prints lines mentioning `--base-prompt` and `new_relevant`. If it prints nothing, the push did not happen:
  push on your computer, then do the reset (rule 3).

---

## B. Quick checks (about 10 minutes; before the pilot)

**B1. Cell 5, dry run, no model**
```python
!python -m experiments.dry_run_pipeline --adapter experiments/finetuned_model/crosscodeeval/v2
```
Success: ends with `DRY RUN PASSED`, and prints "with --base-prompt plain, prompt tokens" lines (median about 423 and 2138).
(It writes stand-in files to `results/dry_run/`, which is on Drive; harmless.)

**B2. Cell 6, 5-example test with the plain prompt**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --limit 5 --output-dir results/plain_test
```
Success: it finishes and writes `results/plain_test/`. Add `--skip-codebleu` only if CodeBLEU errors.

**B3. Cell 7, the gate: do base and RAG now write code continuations?**
```python
import json
rows = [json.loads(l) for l in open("results/plain_test/predictions.jsonl", encoding="utf-8")]
for r in rows:
    print("REF :", repr(r["reference"]))
    for s in ("base", "rag_only", "finetuning_only", "hybrid"):
        print(f"  {s:16}", repr(r[s]["prediction"])[:120], "| ES", r[s]["edit_similarity"])
```
- **Pass:** base and RAG outputs look like the rest of a code line (an attribute, a call, an argument list), even if wrong.
  Fine-tuned and hybrid look as before. Continue to section C.
- **Fail:** base or RAG still write `import ...`, `#` comments, `# --- retrieved from ...`, or sentences. **Stop here** and send
  me the printed rows and the 5-example `comparison_summary.md`: we switch to the few-shot option instead of spending GPU time.

---

## C. The pilot (core; about 15 minutes)

**C1. Cell 8, pilot, main view** (50 examples, four systems, plain prompt for base and RAG)
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain
```
Output: `results/pilot_main_plainbase/`. About 7 minutes. Fine-tuned and hybrid should reproduce the first pilot (edit similarity
0.613 and 0.644); if they differ, tell me.

**C2. Cell 9, pilot, staleness view** (NEW files added to the retrieval index)
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --view staleness
```
Output: `results/pilot_staleness_plainbase/`. About 7 minutes.

**C3. Cell 10, look at the results before you leave**
```python
!cat results/pilot_main_plainbase/comparison_summary.md
!cat results/pilot_staleness_plainbase/comparison_summary.md
```
Copy both tables into the chat when you send me the results (the files are also downloaded in section E).

---

## D. Extras (only if GPU time is left; each links to a finding in the literature)

**D1. Cell 11, BM25 retrieval** (Wang et al.: BM25 beats dense), about 7 minutes
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --retriever bm25
```
Output: `results/pilot_main_bm25_plainbase/`.

**D2. Cells 12 and 13, the staleness test proper:** 68 examples whose relevant file is a NEW file (H3), about 6 to 8 minutes each
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant
```
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant --view staleness
```
Outputs: `results/new_relevant_main_plainbase/` and `results/new_relevant_staleness_plainbase/`. The log should say
"new_relevant subset: 68 TEST examples". In the main view the relevant new file cannot be retrieved; in the staleness view it can.

**D3. Cell 14, forgetting check on HumanEval with the plain stub** (Wang et al.: fine-tuning lowered pass@1 by 24.1%)
Runs model-generated code: **Colab only, never on your computer.** About 15 to 25 minutes for all 164 problems; add `--limit 40`
if time is short.
```python
!python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec
```
Output: `results/forgetting_humaneval_plain.json`. Success: base pass@1 is clearly above 0. If the script prints a WARNING that base
pass@1 is 0, send me the output.

---

## E. Finish (do not skip)

**E1. Cell 15, confirm everything is on Drive** (`results/` is linked to Drive by the setup script)
```python
!ls /content/drive/MyDrive/thesis/outputs/results
```
You should see `plain_test`, `pilot_main_plainbase`, `pilot_staleness_plainbase`, and any extras you ran.

**E2.** On your computer, copy these from `MyDrive/thesis/outputs/results/` into the project's `results/` folder (do not overwrite
older folders): `plain_test/`, `pilot_main_plainbase/`, `pilot_staleness_plainbase/`, and if run `pilot_main_bm25_plainbase/`,
`new_relevant_main_plainbase/`, `new_relevant_staleness_plainbase/`, `forgetting_humaneval_plain.json`.

**E3.** Runtime > **Disconnect and delete runtime**.

**E4.** Send me: the Cell 7 printout (B3), both summary tables (C3), anything that printed a WARNING, and tell me "results added".
I will read the predictions, run `analyze_predictions`, and log the findings.

---

## Quick fixes

| What you see | Do this |
|---|---|
| `results already has files; refusing to replace it` (Cell 3) | Either the cloned repository contains a tracked `results/` folder (use the Cell 2 above, which removes it), or rule 2 was broken (something wrote into a local `results/` before Cell 3). Only local copies are lost; Drive is untouched. Do the reset: Cell 2, Cell 3 immediately, Cell 4 |
| `FileNotFoundError: ... data/processed/crosscodeeval/examples.jsonl` (or another `data/...` file) | The data is missing: Cell 3 was skipped, stopped early, or Cell 2 was re-run after it. Do the reset, and check every line of Cell 3 says `ok` |
| `unrecognized arguments: --base-prompt` / the grep in Cell 4 prints nothing | The push did not happen, or Cell 2 used an old clone. Push on your computer, then do the reset |
| `No module named ...` | Do the reset (it reinstalls the libraries), then Cell 4 |
| `DIFFERS` / `MISSING` in the data check | Do not run anything else; send the output |
| `[5/5]` says `no cache ... rebuilding` | The Drive cache was not found; the rebuild takes 10 to 20 minutes. Send me the output first if you are unsure |
| `cuda: False` / `No GPU` | Runtime > Change runtime type > T4 GPU; start again from Cell 1 |
| `out of memory` | Runtime > Restart session; do the reset; note which system failed |
| CodeBLEU error | Add `--skip-codebleu` to the command (it then shows n/a, never 0) |
| B3 fails (base/RAG still not code) | Stop; send the printed rows |
| Disconnected during a run | Do the reset; start the unfinished run again (a run writes its files at the end) |


---

## F. Follow-up session (2026-11-23, after the local analysis): why does the frozen RAG system fail?

Do this in a **new Colab session** (or the same one if it is still open and was set up with the rules at the top of this file). It is short
(about 15 to 20 minutes of GPU) and needs the latest code pushed first (new options `--save-raw`, `--rag-format`, `--suppress-fim`).

**Why:** the local analysis (progress log Entries 41 and 42) found that RAG gives empty answers (5 of 50) and writes the literal token
`<|fim_suffix|>` as its whole answer (6 of 50) with the comment-style prompt. These are formatting failures of the frozen model, not evidence that
retrieval is useless. The runs below find out which fix works. Everything is pilot, n=50, main view.

**Setup:** sections A1 to A5 above (Cell 1, Cell 2, Cell 3 immediately, Cell 4). Skip B and C (already done). In Cell 4 the last command should now
also show `--save-raw` (check: `!python -m experiments.run_comparison --help | grep -E "save-raw|rag-format|suppress-fim"` prints three entries).

**F1. Diagnostic: current prompt, save the raw completions (RAG and base; about 3 minutes)**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --systems base rag_only --save-raw
```
Output: `results/pilot_main_plainbase_raw/`. The predictions must equal the earlier run (RAG edit similarity 0.387, base 0.494); the log prints, per
system, how many answers stopped by `eos`, `newline` or `max_tokens`, and how many first lines are empty. Then:
```python
!python -m src.evaluation.inspect_raw results/pilot_main_plainbase_raw/predictions.jsonl
```
Copy this output into the chat.

**F2. Fix 1: forbid the fill-in-the-middle tokens (RAG only; about 3 minutes)**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --suppress-fim --systems rag_only --save-raw
```
Output: `results/pilot_main_plainbase_nofim_raw/`.

**F3. Fix 2: Qwen's own repository-level prompt format for the retrieved files (RAG only; about 3 minutes)**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --rag-format qwen_repo --systems rag_only --save-raw
```
Output: `results/pilot_main_plainbase_qwenrepo_raw/`. Run the inspect command on F2 and F3 as well (change the folder name).

**F4. Only if F3 (or F2) clearly improves RAG: rerun the full four-system pilot with that setting** (about 8 minutes each; add `--save-raw` if you
want the diagnostics again). Example for F3's format:
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --rag-format qwen_repo
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --rag-format qwen_repo --view staleness
```
Outputs: `results/pilot_main_plainbase_qwenrepo/` and `results/pilot_staleness_plainbase_qwenrepo/`. Do not run F4 until the local analysis of F1 to F3
says it is worth it; the hybrid is not affected by `--rag-format` (it keeps the training format), so only the RAG row can change.

**F5. Finish:** E1 to E3 above. Copy the new folders (`pilot_main_plainbase_raw/`, `pilot_main_plainbase_nofim_raw/`, `pilot_main_plainbase_qwenrepo_raw/`, and any
F4 folders) into the local `results/`, paste the three `inspect_raw` outputs into `docs/new_results_pilot_run_from_colab` (or a new file), and tell me.

| What you see | Do this |
|---|---|
| `unrecognized arguments: --save-raw` (or `--rag-format`, `--suppress-fim`) | The latest code is not on GitHub: commit and push, then do the reset (Cell 2, Cell 3 immediately, Cell 4) |
| F1 scores differ from the earlier run (RAG not 0.387 / base not 0.494) | Tell me; the diagnostic should not change any prediction |
| An error mentioning `bad_words_ids` in F2 | Send the full output; F3 is independent and can still be run |
