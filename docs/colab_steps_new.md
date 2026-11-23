# Colab steps (new): Project Part 1 pilot with the fixed prompts

Follow this top to bottom in one Colab session. It replaces the Colab parts of `docs/colab_steps_part2.md` and
`docs/next_steps_part3.md` for Part 1 (background and older troubleshooting are still in `docs/colab_steps.md`).

**What this session produces:** a valid four-system pilot (base, RAG, fine-tuned, hybrid) on the 50 CrossCodeEval pilot
examples, where base and RAG now get a plain continuation prompt, in two views (main and staleness), plus optional extras. Report
everything as "pilot, n=50".

**GPU time:** about 30 minutes for the core (sections A to C), about 1 hour with all extras (D).
**If the free quota ends early, do them in this order:** B3, C1, C2, then D1, D2, D3.

Rules: run one cell at a time and wait for it to finish. If a cell errors, stop and copy the **full** output (from the top of the
error). Never paste tokens or passwords into a cell.

**Before you start (on your computer):** commit and push the repository. Colab clones from GitHub; the new options
(`--base-prompt`, `--subset new_relevant`, `--prompt` for HumanEval) exist on Colab only after the push.

---

## A. Setup (about 5 minutes)

**A1.** Runtime > Change runtime type > **T4 GPU** > Save.

**A2. Cell 1, connect Drive**
```python
from google.colab import drive
drive.mount("/content/drive")
```
Success: `Mounted at /content/drive`.

**A3. Cell 2, get the latest code**
```python
import os, shutil, subprocess
if os.path.exists("/content/Thesisbaseline1"):
    shutil.rmtree("/content/Thesisbaseline1")
subprocess.run(["git", "clone", "--depth", "1",
                "https://github.com/NidwijaB/Thesisbaseline1", "/content/Thesisbaseline1"], check=True)
os.chdir("/content/Thesisbaseline1")
```

**A4. Cell 3, setup script (installs libraries, links Drive, restores data)**
```python
!python tools/colab_setup.py
```
Success: every "Checking data" line starts with `ok` (train 9378, val 1059, pilot_ids 50, 206 index folders, examples.jsonl 2018),
`cuda: True`, a Tesla T4, and the last line `Setup finished.` On `DIFFERS` or `MISSING`, stop and send me the output.

**A5. Cell 4, check the installs, the adapter and that the new code arrived**
```python
!python -c "import rank_bm25, peft, bitsandbytes, faiss, transformers, sentence_transformers; print('imports ok')"
!ls -la experiments/finetuned_model/crosscodeeval/v2
!python -m experiments.run_comparison --help | grep -E "base-prompt|new_relevant"
```
Success: `imports ok`; the adapter folder lists `adapter_config.json` and `adapter_model.safetensors`; the last command prints lines
mentioning `--base-prompt` and `new_relevant`. If the last command prints nothing, the push did not happen: push, then re-run Cells 2 to 4.
If a package is missing, re-run Cells 1 to 3 (safe; restores from the Drive cache).

---

## B. Quick checks (about 10 minutes; do these before the pilot)

**B1. Cell 5, dry run, no model**
```python
!python -m experiments.dry_run_pipeline --adapter experiments/finetuned_model/crosscodeeval/v2
```
Success: ends with `DRY RUN PASSED`, and prints "with --base-prompt plain, prompt tokens" lines (median about 423 and 2138).

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
- **Pass:** base and RAG outputs look like the rest of a code line (for example `delete_rate(1, session, ...)`, an attribute or a
  call), even if wrong. Fine-tuned and hybrid look as before. Continue to section C.
- **Fail:** base or RAG still write `import ...`, `#` comments, `# --- retrieved from ...`, or sentences. **Stop here** and send me
  these printed rows (and the 5-example `comparison_summary.md`): we switch to the few-shot option instead of spending GPU time.

---

## C. The pilot (core; about 15 minutes)

**C1. Cell 8, pilot, main view (50 examples, four systems, plain prompt for base and RAG)**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain
```
Output: `results/pilot_main_plainbase/`. About 7 minutes. Fine-tuned and hybrid should reproduce the first pilot (edit similarity
0.613 and 0.644); if they differ, tell me.

**C2. Cell 9, pilot, staleness view (NEW files added to the retrieval index)**
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

**D1. Cell 11, BM25 retrieval (Wang et al.: BM25 beats dense), about 7 minutes**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --retriever bm25
```
Output: `results/pilot_main_bm25_plainbase/`.

**D2. Cell 12 and 13, the staleness test proper: 68 examples whose relevant file is a NEW file (H3), about 6 to 8 minutes each**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant
```
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant --view staleness
```
Outputs: `results/new_relevant_main_plainbase/` and `results/new_relevant_staleness_plainbase/`. The log should say
"new_relevant subset: 68 TEST examples". In the main view the relevant new file cannot be retrieved; in the staleness view it can.

**D3. Cell 14, forgetting check on HumanEval with the plain stub (Wang et al.: fine-tuning lowered pass@1 by 24.1%)**
Runs model-generated code: **Colab only, never on your computer.** About 15 to 25 minutes for all 164 problems; use `--limit 40` if
time is short.
```python
!python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec
```
Output: `results/forgetting_humaneval_plain.json`. Success: base pass@1 is clearly above 0. If the script prints a WARNING that base
pass@1 is 0, send me the output.

---

## E. Finish (do not skip)

**E1. Cell 15, confirm everything is on Drive** (`results/` is linked to Drive by the setup script):
```python
!ls /content/drive/MyDrive/thesis/outputs/results
```
You should see `plain_test`, `pilot_main_plainbase`, `pilot_staleness_plainbase`, and any extras you ran.

**E2.** On your computer, copy these from `MyDrive/thesis/outputs/results/` into the project's `results/` folder (do not overwrite older
folders): `plain_test/`, `pilot_main_plainbase/`, `pilot_staleness_plainbase/`, and if run `pilot_main_bm25_plainbase/`,
`new_relevant_main_plainbase/`, `new_relevant_staleness_plainbase/`, `forgetting_humaneval_plain.json`.

**E3.** Runtime > **Disconnect and delete runtime**.

**E4.** Send me: the Cell 7 printout (B3), both summary tables (C3), anything that printed a WARNING, and tell me "results added".
I will read the predictions, run `analyze_predictions`, and log the findings.

---

## Quick fixes

| What you see | Do this |
|---|---|
| `unrecognized arguments: --base-prompt` / the grep in A5 prints nothing | Push did not happen or Cell 2 used an old clone; push, then re-run Cells 2 to 4 |
| `No module named ...` | Re-run Cells 1, 2, 3, then Cell 4 |
| `DIFFERS` / `MISSING` in the data check | Do not run anything else; send the output |
| `cuda: False` / `No GPU` | Runtime > Change runtime type > T4 GPU; restart from Cell 1 |
| `out of memory` | Runtime > Restart session; rerun from Cell 1; note which system failed |
| CodeBLEU error | Add `--skip-codebleu` to the command (it then shows n/a, never 0) |
| B3 fails (base/RAG still not code) | Stop; send the printed rows |
| Disconnected during a run | Re-run Cells 1 to 3; start the unfinished run again (a run writes its files at the end) |
