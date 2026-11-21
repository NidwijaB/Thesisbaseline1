# Colab Steps, Part 2: running the pilot (GPU session of 2026-11-21)

This file is the short, exact run order for today. The background, troubleshooting and older steps are in
`docs/colab_steps.md` (Parts 2 to 9). Commands here use only options that exist in `experiments/run_comparison.py`
(`--adapter`, `--view`, `--limit`, `--4bit`, `--skip-codebleu`, `--output-dir`, `--max-code-tokens`, `--retriever`).

Rules for the whole session:
- Run one cell at a time, in order. Wait for it to finish before starting the next.
- If a step fails, **stop and copy the full output** (from the top of the error, not only the last line). Do not
  skip ahead.
- Report pilot numbers as "pilot, n=50", never as findings.
- Never paste tokens or passwords into a cell.
- Nothing here has run on Colab yet: the 4-bit load, generation, the `codebleu` install and `run_comparison.py`
  end to end are first-time runs, so a failure there is expected information, not a mistake.

Before you start, on your computer: commit and push the repository (Cell 2 clones from GitHub).

---

## A. Setup (every session)

**A1.** Runtime > Change runtime type > **T4 GPU** > Save.

**A2. Cell 1, connect Drive**
```python
from google.colab import drive
drive.mount("/content/drive")
```
Success: `Mounted at /content/drive`.

**A3. Cell 2, get the code**
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
Success:
- the output reaches `Setup finished.`;
- every line of "Checking data" starts with `ok` (including `pilot_ids.json: 50`, 206 index folders,
  `examples.jsonl: 2018`);
- it prints `cuda: True` and a GPU name.

If it stops with a pip error, or any line says `DIFFERS` or `MISSING`: stop and send the output.

**A5. Cell 4, confirm the install and the adapter** (this catches the `rank_bm25` problem before it costs time)
```python
!python -c "import rank_bm25, peft, bitsandbytes, faiss, transformers, sentence_transformers; print('imports ok')"
!ls -la experiments/finetuned_model/crosscodeeval/v2
```
Success: `imports ok`, and the folder lists `adapter_config.json` and `adapter_model.safetensors`.

**If a package is missing** (for example `No module named 'rank_bm25'`): the runtime was restarted or Cell 3 did not
finish. Re-run Cell 1, Cell 2, Cell 3 in that order (safe: it restores from the Drive cache in about a minute and
reinstalls the libraries), then Cell 4 again. If Cell 3 itself printed a pip error, send me that error.

---

## B. Quick checks (about 10 minutes; do these before the pilot)

**B1. Cell 5, dry run (no model, about a minute)**
```python
!python -m experiments.dry_run_pipeline --adapter experiments/finetuned_model/crosscodeeval/v2
```
Success: ends with `DRY RUN PASSED`. The CodeBLEU line tells you whether the `codebleu` install worked; if it says
it is unavailable, add `--skip-codebleu` to every `run_comparison` command below.

**B2. Cell 6, demo on one pilot example (first 4-bit model load)**
```python
import json
first_id = json.load(open("data/processed/crosscodeeval/pilot_ids.json"))[0]
!python -m src.demo --task-id {first_id} --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
```
Success: base, RAG, fine-tuned and hybrid each print a completion. Each should be non-empty and one line.
Stop and send the output if the model fails to load or a completion is empty or has several lines.

**B3. Cell 7, five-example test of the evaluation script**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --limit 5 --output-dir results/pipeline_test
```
Success: it finishes, and `results/pipeline_test/` holds a metrics file and `predictions.jsonl`. Add `--skip-codebleu`
if CodeBLEU errors. Watch for `out of memory` (RAG and hybrid prompts are about 2,000 tokens, up to about 6,000).
Do not start the pilot until this passes.

---

## C. The pilot (50 examples, four systems: base, RAG, fine-tuned, hybrid)

**C1. Cell 8, pilot on the main index**
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
```
Output: `results/pilot_main/`. Add `--skip-codebleu` only if it failed in B1 or B3.

**C2. Cell 9, base versus adapter validation loss** (is there any evidence fine-tuning helped?)
```python
!python -m src.finetuning.eval_loss --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
```
Output: `results/val_loss_base_vs_adapter.json`. Validation is not file-held-out, so it is optimistic; read it as a
comparison between base and adapter, not as an absolute number.

**C3. Cell 10, pilot on the staleness index** (NEW files in the retrieval index only)
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --view staleness
```
Output: `results/pilot_staleness/`.

**C4. Cell 11, look at the numbers before you leave**
```python
!ls results
!cat results/pilot_main/comparison_summary.md
```
If a file name differs, `!ls results/pilot_main` shows what was written. Check that no system shows empty
predictions or all-zero scores; if so, send the output instead of continuing.

---

## D. Extra runs (only if GPU time is left; most useful first)

Run each on the pilot, one cell each. Each writes to its own folder (suffix added automatically), so nothing is
overwritten.

**D1. Shorter code input** (21 of 50 pilot prompts exceed the 512 tokens used in training)
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --max-code-tokens 480
```

**D2. BM25 retrieval instead of UniXcoder** (BM25 won the retrieval comparison)
```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --retriever bm25
```

**D3. Forgetting check on HumanEval, 20 problems** (runs model-generated code: **Colab only, never on your computer**)
```python
!python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec --limit 20
```

---

## E. Finish (do not skip; the session's files are lost on disconnect unless they are on Drive)

**E1.** Check the results reached Drive (the setup script links `results/` to Drive):
```python
!ls /content/drive/MyDrive/thesis/outputs
```
**E2.** On your computer, download from `MyDrive/thesis/outputs/` into your project's `results/` folder:
`pilot_main/`, `pilot_staleness/`, `val_loss_base_vs_adapter.json`, `pipeline_test/` and any extra run folders
(`_code480`, `_bm25`, forgetting-check output).
**E3.** Locally, hit-versus-miss and paired differences (no GPU needed):
```
python -m src.evaluation.analyze_predictions results/pilot_main/predictions.jsonl
```
**E4.** In Colab: Runtime > **Disconnect and delete runtime**.
**E5.** Bring the outputs to Claude Code. They go into `docs/progress_log.md` as Entry 32 and
`docs/results_summary.md`, and the completion estimate (about 58%, Entry 31) is revised.

---

## If something goes wrong (quick table)

| What you see | Do this |
|---|---|
| `No module named ...` | Re-run Cells 1, 2, 3, then Cell 4. If Cell 3 printed a pip error, send it |
| `DIFFERS` / `MISSING` in the data check | Do not run anything else; send the output |
| `No GPU` / `cuda: False` | Runtime > Change runtime type > T4 GPU, restart from Cell 1 |
| `out of memory` | Runtime > Restart session, rerun from Cell 1; note which system failed |
| `CodeBLEU needs the 'codebleu' package` | Add `--skip-codebleu` (shows n/a, never 0) |
| Empty or multi-line completions | Stop; send the demo or test output |
| Disconnected | Re-run Cells 1 to 3; pilot runs are short, so start the unfinished run again |

## After this session (not today)
Full CrossCodeEval evaluation (543 TEST examples, `--subset test`), noisy context (`--noise-chunks 3`), top-k sweep
(`--top-k 1`, `3`, `10`), the RAFT-style decision, then RepoBench fine-tuning and completion
(`--datasets crosscodeeval repobench` in Cell 3).
