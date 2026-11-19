# Colab Guide: Setting Up and Running the GPU Work

This guide uses Google Colab only for the GPU work (training and evaluation). Your own
computer is still where you edit code, commit, and write the thesis.

## How it fits together (the 30-second version)

- **Colab** is a rented computer with a GPU. It is wiped every time you disconnect.
- **GitHub** holds your code. Colab downloads it fresh each session.
- **Google Drive** is the filing cabinet that survives. The data cache, trained adapters,
  checkpoints and results are saved there.

So each new session you repeat a short setup, and your trained work is still waiting on Drive.

Folders created on your Drive automatically:

    My Drive/thesis/cache/     data, built once and reused every session
    My Drive/thesis/outputs/   trained adapters, checkpoints, results

---

## Part 0. Before you open Colab (once, on your own computer)

Colab downloads the code from GitHub, so the Colab files must be pushed first.

1. Make sure these files are committed and pushed to `main`:
   - `tools/colab_setup.py`
   - `src/finetuning/trainer.py`
   - `docs/colab_steps.md`
2. Open https://github.com/NidwijaB/Thesisbaseline1 in a browser and confirm
   `tools/colab_setup.py` is visible there. If it is not, Colab will not find it.
3. Make sure you have about 5 GB free on Google Drive (the cache is a few GB once RepoBench is
   added; CrossCodeEval alone is small).

---

## Part 1. Open a notebook and turn on the GPU

1. Go to https://colab.research.google.com and sign in with the Google account whose Drive you
   want to use.
2. Click **File > New notebook**.
3. Click **Runtime > Change runtime type**.
4. Under hardware accelerator choose **T4 GPU**, then **Save**.
5. Click **Connect** (top right). Wait until it shows RAM/Disk bars.

How to know it worked: run a cell containing `!nvidia-smi`. You should see a table that
mentions "Tesla T4". If it says the command is not found, the GPU is not on; repeat steps 3 and 4.

---

## Part 2. Setup (3 cells; repeat these at the start of every session)

In Colab, a cell is a box you type code into. Click **+ Code** to add one. Press the play
button on the left of a cell (or Shift+Enter) to run it. Run the cells **in order** and wait for
each to finish before starting the next one.

### Cell 1: connect Google Drive

```python
from google.colab import drive
drive.mount("/content/drive")
```

A pop-up asks you to allow access to your Drive. Click through and **Allow**.
Success looks like: `Mounted at /content/drive`.

### Cell 2: download the code from GitHub

```python
import os, shutil, subprocess
if os.path.exists("/content/Thesisbaseline1"):
    shutil.rmtree("/content/Thesisbaseline1")
subprocess.run(["git", "clone", "--depth", "1",
                "https://github.com/NidwijaB/Thesisbaseline1", "/content/Thesisbaseline1"],
               check=True)
os.chdir("/content/Thesisbaseline1")
```

The repository is public, so no password or token is needed. Do not put any token in a cell.
Success looks like: no red error text. Check with a new cell: `!ls tools` should list `colab_setup.py`.

### Cell 3: run the setup script

```python
!python tools/colab_setup.py
```

This does five things and prints a numbered heading for each:

1. Checks Drive is connected.
2. Installs the libraries (about 2 to 3 minutes).
3. Checks the GPU and prints `cuda: True` and a GPU name.
4. Links the output folders to Drive.
5. Prepares the data:
   - **First time ever:** downloads the public benchmarks and rebuilds the splits, training
     sets and search indexes, then saves a cache to Drive. Expect about 10 to 20 minutes.
   - **Every later session:** restores from the cache in about a minute.

At the end it prints a "Checking data" list. Each line should start with `ok`:

    ok      data/processed/crosscodeeval/finetune/train.jsonl: 9378 (log says 9378)
    ok      data/processed/crosscodeeval/finetune/val.jsonl: 1059 (log says 1059)

If any line says `DIFFERS` or `MISSING`, **do not train**. Copy the output and bring it back to
Claude Code; it means the rebuilt data is not identical to the data in your progress log.

The last line should read: `Setup finished.`

When you are ready for RepoBench later, run instead:

```python
!python tools/colab_setup.py --datasets crosscodeeval repobench
```

---

## Part 2b. Stop the old training run (do this once, before starting the fixed one)

The run that is going now was started with the earlier training code (version 1). Its loss counted the
prompt and padding, and it has no end-of-answer token, so its adapter is a smoke test, not a result. It is
safe to stop it; you lose nothing you need.

1. In the Colab notebook that is training, click the **stop square** on the left of the running cell
   (or Runtime > Interrupt execution, or press Ctrl+M then I). Wait until the cell stops spinning and
   the red text `KeyboardInterrupt` appears. Stopping early is normal and safe.
2. Free the GPU so it is not wasted: Runtime > **Disconnect and delete runtime**. This wipes Colab's local
   disk only. Everything on Drive stays.
3. **Do not delete the old folder on Drive.**
   `My Drive/thesis/outputs/finetuned_model/crosscodeeval/` holds the version-1 checkpoints. Leave it:
   the new run goes in a separate sub-folder (`v2`), and the trainer refuses to mix the two.
4. Optional, if the old run already saved at least one epoch (a folder named `checkpoint-<number>` exists in
   that Drive folder): later, after the new session's setup, you can plot its loss curve for comparison
   (see Part 3d). It only exists if a checkpoint was saved; the old code saved once per epoch.
5. Make sure the new code is on GitHub before you start the new run (Part 0). Cell 2 downloads the latest
   pushed code each session; if the push has not happened, Colab would train with the old code again.

Then do Part 2 (Cells 1 to 3) in a fresh notebook session and start Part 3.

---

## Part 3. Run training

**Which run is which.** Your first Colab run used the earlier training code (version 1): its loss counted
the prompt and padding, and it had no end-of-answer token. Keep that folder, but do not reuse it. The fixed
code (version 2) must go in its own folder, and the trainer refuses to mix them: if you start it in the old
folder it stops and tells you to use `--run-name`.

Before this step, make sure the latest code is pushed to GitHub and Cell 2 has downloaded it.

In a new cell:

```python
!python -m src.finetuning.trainer --dataset crosscodeeval --run-name v2
```

What to expect:

- The model downloads from Hugging Face (about 3 GB, a few minutes, first session only).
- A line like `trainable params: ...`, then a progress bar. Loss values will look different from the
  first run (much higher at the start): now only the answer tokens count, so they are not comparable.
- A checkpoint is saved to Drive every 100 steps (the last 2 are kept).
- When it finishes, the adapter is in
  `My Drive/thesis/outputs/finetuned_model/crosscodeeval/v2/`.

### If Colab disconnects mid-training

Nothing is lost beyond the last 100 steps. Repeat Part 2 (Cells 1 to 3) and run the same command
(same `--run-name v2`). It finds the latest checkpoint on Drive and continues. Use `--no-resume` only if
you deliberately want to start over.

---

## Part 3b. Retrieval comparison (no GPU needed)

Compares dense (UniXcoder) retrieval with BM25 and a random baseline on the CrossCodeEval TEST examples.
It only reads the indexes, so it also runs on a CPU runtime or on your own machine.

```python
!python -m src.retrieval.compare_retrievers
!python -m src.evaluation.plot_retrieval_comparison
```

Outputs: `results/retrieval_comparison.json` and pictures in `results/figures/` (on Drive when run on Colab).
Check that the first lines say "TEST files retrieved (must be 0): 0" and that the example counts are
292 (main) and 327 (staleness). Read the dense and BM25 scores against the random row: pools are tiny, so even
random guessing scores high at k=5 and k=10.

## Part 3c. Pilot evaluation of the systems (GPU, after training finishes)

Runs base, RAG, fine-tuned and hybrid on the 50 pilot examples and writes metrics, a comparison table and one
row per example:

```python
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
```

- Output folder: `results/pilot_main/` (`comparison_summary.md`, `predictions.jsonl`, per-system metrics).
- If the CodeBLEU packages did not install in Part 2, add `--skip-codebleu`. It then shows `n/a`, never 0.
- Add `--limit 5` for a quick test first. Add `--view staleness` for the staleness index.
- 50 examples are a pipeline check, not a result: report them as "pilot, n=50".

## Part 3d. Plot the training curve (step 4, after training has produced checkpoints)

```python
!python -m src.evaluation.plot_training --run experiments/finetuned_model/crosscodeeval/v2
```

This reads the Trainer's `trainer_state.json` from the latest checkpoint and saves
`results/figures/training_loss.png` (training loss, plus validation loss each epoch). Validation loss is not
file-held-out, so it is optimistic: use the picture to show training behaves, not to claim generalisation.
You can also run it on a finished or interrupted run; no other step has to wait.
To keep the first (version 1) curve for comparison, run it on the old folder with
`--run experiments/finetuned_model/crosscodeeval --output results/figures/training_loss_v1.png`,
and label it "earlier training code".

---

## Part 3e. After EVERY training run (checklist)

Do these in order each time a run ends, whether it finished or was stopped. `<run>` means the folder you
trained into, for example `experiments/finetuned_model/crosscodeeval/v2`.

1. **Check it really finished.** The last training lines should say `Adapter saved to ...`. In a cell:
   ```python
   !ls -la experiments/finetuned_model/crosscodeeval/v2
   ```
   This only works in a session where Cells 1 to 3 have run (Cell 3 creates the link to Drive). In a fresh
   session, use the Drive path from Part 7.0 instead. You should see `adapter_config.json`, `adapter_model.safetensors` and the `checkpoint-*` folders. If the
   adapter files are missing, the run stopped early: start the same command again, it resumes (Part 3).
2. **Look at the numbers printed during training.** Loss should go down over time and never show `nan`.
   A loss that stays flat or jumps to `nan` means something is wrong: stop and bring the output to Claude Code.
3. **Plot the training curve** (Part 3d) and keep `results/figures/training_loss.png`.
4. **Try the adapter on one example** before any long evaluation (about a minute):
   ```python
   import json
   first_id = json.load(open("data/processed/crosscodeeval/pilot_ids.json"))[0]   # a TEST example
   !python -m src.demo --task-id {first_id} --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
   ```
   It prints base, RAG, fine-tuned and hybrid completions next to the true answer. Check they are one line
   and look like code. The example comes from the pilot list, so it is a TEST example.
5. **Run a small evaluation first, then the pilot** (Part 3c): `--limit 5`, and if that works the full 50.
6. **Record what happened** (this is for your progress log, which you keep on your own computer): which run
   folder, how many steps, the final training and validation loss, how long it took, any warnings, and the
   pilot numbers with n=50. Paste the printed output to Claude Code and it will write the log entry.
7. **Back up.** The Drive folders `thesis/outputs/` and `thesis/cache/` are your saved copy. For an extra
   copy, right-click the adapter folder in Drive and download it.
8. **Release the GPU.** Runtime > **Disconnect and delete runtime**. Free Colab limits how much GPU time you
   get, so do not leave a finished session idling.
9. **Do not push from Colab.** Any code change is made and committed on your own computer; the next session
   downloads it in Cell 2.

---

## Part 4. Saving your work

| What | Where it is saved | What you do |
|---|---|---|
| Trained adapters, checkpoints, results, figures | Google Drive (`thesis/outputs/`) | Nothing, it is automatic |
| Data cache | Google Drive (`thesis/cache/`) | Nothing, it is automatic |
| Code changes | GitHub | Edit and commit on your own computer, then push |
| Progress log entries | `docs/progress_log.md` | Written on your own computer |

Do not push from Colab. That way no GitHub login ever has to be stored in Colab.
Notebooks are gitignored (`*.ipynb`), so a notebook with outputs cannot end up in the repository.

---

## Part 5. Coming back later (the routine)

1. Open Colab, set the runtime to T4 GPU, click Connect.
2. Run Cell 1, Cell 2, Cell 3 (about 3 to 5 minutes).
3. Run the training or evaluation command.
4. Your earlier results are still in `My Drive/thesis/outputs/`.

---

## Part 6. Order of work (status: the fixed v2 run is training on the pushed code)

Each step says where it runs. Parts 2b, 3 to 3e hold the detailed commands. Do not skip the "stop and
check" lines: they protect your limited GPU time.

Done: the old run was stopped or finished (Part 2b), the fixed code was pushed, and v2 was started with
`--run-name v2`. That `--run-name` worked, so the new training code is the one running.

**While v2 is training (Colab), do NOT:**
- re-run Cell 2 or Cell 3 in that session (Cell 2 deletes the code folder the training is using);
- open a second GPU notebook (it competes for the same limited free GPU time);
- start any other command in the same notebook.
If you change code on your own computer in the meantime, that is fine: the running session keeps the code it
already has. Those changes only matter from step B below.

**Step A. Watch v2 (Colab).** Send Claude Code the first progress-bar lines (seconds per step) and, each
epoch, the `loss` and `eval_loss` values. If the free GPU time runs out or Colab disconnects, nothing is lost
beyond the last 100 steps: when the GPU is available again, repeat Cells 1 to 3 and run the SAME command
(`--run-name v2`); it resumes. If v2 ends early without `Adapter saved to`, that is the same case: run the
command again.

**Step B. Before the pilot: make sure Colab has the latest code (your computer, then Colab).** If you
changed any code after starting v2 (for example evaluation fixes), commit and push it first. After v2 has
finished, run Cells 1, 2, 3 again; this fetches the latest push. Check the code is current:
```python
!python -m src.finetuning.trainer --help
```
The list must include `--run-name`. If you pushed something newer, check that file is present
(for example `!ls src`). Never do this while v2 is still training.

**Step C. After v2 finishes: check the adapter (Colab).** Part 3e steps 1 to 3: the adapter files exist in
`experiments/finetuned_model/crosscodeeval/v2`, the loss never showed `nan`, and you note the final training and
validation loss and the run time.

**Step D. Test the v2 adapter on a few examples before the full pilot (Colab, about 10 minutes).**
```python
import json
first_id = json.load(open("data/processed/crosscodeeval/pilot_ids.json"))[0]
!python -m src.demo --task-id {first_id} --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --limit 5 --output-dir results/pipeline_test
```
This is a quick check that generation works and the completions are single lines of code. Stop and bring the
output to Claude Code if either command errors or prints empty completions. Add `--skip-codebleu` to the
second command if CodeBLEU did not install (Part 2). `results/pipeline_test` is only for this check.

**Step E. The pilot (Colab, after step D worked).** Run these in this order (Part 3c has the details):
1. Pilot on the main index (50 examples):
   ```python
   !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
   ```
2. Pilot on the staleness index (BASE plus NEW files in the index only):
   ```python
   !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --view staleness
   ```
3. Training curve: Part 3d.
4. Finish the rest of the Part 3e checklist (record the numbers, back up), then disconnect the runtime.

Outputs land in `results/pilot_main/`, `results/pilot_staleness/` and `results/figures/` on Drive.

**Step F. Bring the results back (your computer).** In your browser, open My Drive > thesis > outputs and
download these into your project's `results/` folder (it is gitignored, so nothing is committed by accident):
- `pilot_main/` and `pilot_staleness/`: `comparison_summary.md`, the `*_metrics.json` files, `predictions.jsonl`
- `figures/*.png`
- `trainer_state.json` from the newest `checkpoint-*` folder inside `finetuned_model/crosscodeeval/v2/`
Do not download or copy any tokens or `.env` files; none are involved. If downloading is awkward, paste the
printed output into Claude Code instead.

**Step G. Local analysis (your computer, with Claude Code).** Retrieval comparison (dense vs BM25 vs random;
it needs no Colab), the hit-versus-miss analysis from `predictions.jsonl`, plots, the progress-log entry, and
updating the prompt for the presentation. State in every table that the pilot has n=50.

**Step H. Only after the pilot works: scale up (Colab).** The full CrossCodeEval TEST set (543 examples) with
`--subset test`. Test with `--limit 10` first and look at the time it takes before the full run; free GPU time
is limited. RepoBench needs `python tools/colab_setup.py --datasets crosscodeeval repobench` first and a
sampling rule for its large test set, which is not decided yet.

What is not available yet, so do not expect it in these steps: BM25 inside the system comparison (it is
only in the retrieval comparison for now), the noisy-context test, the forgetting check, and a
retrieval-formatted (RAFT-style) training variant.

---

## Part 7. The v2 run has finished and the free GPU time is used up (current situation)

### 7.0 Why `ls experiments/finetuned_model/crosscodeeval/v2` said "No such file or directory"
That path is only a shortcut. Cell 3 (the setup script) creates `experiments/finetuned_model` as a link to
Drive, and Colab's local disk is wiped whenever a session resets. In the new CPU session Cells 1 to 3 have not
run, so the shortcut does not exist. The adapter itself is on Drive. Check it there (Colab, CPU session, 2 minutes):
```python
from google.colab import drive
drive.mount("/content/drive")
!ls -la /content/drive/MyDrive/thesis/outputs/finetuned_model/crosscodeeval/v2
```
You want to see `adapter_config.json`, `adapter_model.safetensors` and `checkpoint-*` folders.
- If the folder is missing, also run `!ls /content/drive/MyDrive/thesis/outputs/finetuned_model` and
  `!ls /content/drive/MyDrive/thesis`, and send the output to Claude Code. A missing folder would mean the Drive
  link was not in place when the adapter was saved and the adapter was lost with the session; that is a
  different problem and needs a decision from you (it would mean training again).
- To run later Cells on a CPU session, the setup script needs `python tools/colab_setup.py --allow-cpu`;
  without it Cell 3 stops with "No GPU".

### 7.1 What to do NOW, without a GPU
| # | Where | What |
|---|---|---|
| 1 | Colab (CPU session) | Check the adapter on Drive (7.0). |
| 2 | Your computer, browser | Download from Drive `My Drive/thesis/outputs/finetuned_model/crosscodeeval/v2/`: `adapter_config.json`, `adapter_model.safetensors` (about 4 MB), and from the newest `checkpoint-*` folder inside it, `trainer_state.json`. Save the adapter files in your project at `experiments/finetuned_model/crosscodeeval/v2/` and `trainer_state.json` at `results/training/trainer_state.json`. Both folders are gitignored. |
| 3 | Your computer | Training-loss plot: `python -m src.evaluation.plot_training --run results/training/trainer_state.json` (writes `results/figures/training_loss.png`). |
| 4 | Your computer | Retrieval comparison, dense vs BM25 vs random: `python -m src.retrieval.compare_retrievers` then `python -m src.evaluation.plot_retrieval_comparison`. No GPU, no adapter. |
| 5 | Your computer | Push the newest code to GitHub (the validation-loss script `src/finetuning/eval_loss.py` and `.gitignore` are new). The GPU session needs it. |
| 6 | Your computer, with Claude Code | Progress log, presentation and report updates using the plots and tables that exist. |
| 7 | Optional, your computer | A tiny CPU test of the evaluation code only (`--limit 2 --systems finetuning_only`, no `--4bit`). It downloads the 3 GB base model and loads it in 32-bit, so it needs about 8 GB of free memory and is slow (not timed). Tell Claude Code your free RAM and disk first. The aim is only to catch a bug before the GPU session. |

### 7.2 When the GPU is available again (Colab, T4), one short session
GPU quota returns by itself after a while (hours, sometimes about a day); nothing needs to be bought. Only
start the session when step 5 above is done and you are ready to run everything in one go, in this order
(most important first, in case the quota ends early):
1. Runtime > Change runtime type > T4 GPU. Run Cells 1, 2, 3 (Part 2). Check the adapter exists:
   `!ls -la experiments/finetuned_model/crosscodeeval/v2` (it works now because Cell 3 creates the link).
2. Quick checks, about 10 minutes:
   ```python
   import json
   first_id = json.load(open("data/processed/crosscodeeval/pilot_ids.json"))[0]
   !python -m src.demo --task-id {first_id} --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
   !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --limit 5 --output-dir results/pipeline_test
   ```
   Add `--skip-codebleu` to the second command if the CodeBLEU install failed. Stop and send the output if either
   errors or prints empty completions.
3. **The pilot, main index** (50 examples, all four systems):
   ```python
   !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
   ```
4. **Base-versus-adapter validation loss** (answers whether fine-tuning lowered the loss at all):
   ```python
   !python -m src.finetuning.eval_loss --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
   ```
5. **The pilot, staleness index** (new files in the retrieval index only):
   ```python
   !python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --view staleness
   ```
6. Then the rest of the Part 3e checklist: record the numbers, download `results/pilot_main/`,
   `results/pilot_staleness/` and `results/val_loss_base_vs_adapter.json` from Drive into your project's
   `results/` folder, and **disconnect the runtime**.
The session length for steps 2 to 5 has not been measured. Training took 3.5 hours; evaluation passes are much
shorter (the Trainer's validation pass took under 2 minutes).

### 7.3 What "the pilot" means, so you can explain it
The pilot is a rehearsal on 50 examples picked by a fixed random draw (seed 42) from the CrossCodeEval TEST
examples. It runs four systems on the same 50 questions: the plain model (base), the plain model plus retrieved
code (RAG, System A), the fine-tuned model alone (System B) and the fine-tuned model plus retrieved code
(hybrid, System C). It proves the whole pipeline works end to end and gives first, rough numbers. With only 50
examples the numbers have wide error bars, so report them as "pilot, n=50", never as findings.

---

## Troubleshooting

| What you see | What it means | What to do |
|---|---|---|
| `Google Drive is not mounted` | Cell 1 was skipped or the pop-up was not accepted | Re-run Cell 1 and click Allow |
| `Run this from the project root` | Cell 2 did not finish, or the folder changed | Re-run Cell 2, then Cell 3 |
| `No GPU` | Runtime is on CPU | Runtime > Change runtime type > T4 GPU, then start again from Cell 1 |
| `tools/colab_setup.py: No such file` | Files were not pushed to GitHub | Do Part 0, then re-run Cell 2 |
| A pip install error naming a version | A pinned library version is not available on Colab | Copy the error to Claude Code; we relax that one pin and note it in the log |
| Trainer stops saying checkpoints are from training-code version 1 | You pointed the fixed code at the old run's folder | Add `--run-name v2` to the training command; do not delete the old folder |
| `CodeBLEU needs the 'codebleu' package` | The optional install in Part 2 failed | Add `--skip-codebleu` to the evaluation command (it then shows n/a, never 0) |
| `out of memory` during training | GPU memory full | Restart the runtime (Runtime > Restart session) and start again from Cell 1 |
| Session disconnected | Idle too long or the 12-hour limit | Part 5, then resume training |
| `DIFFERS` in the data check | Rebuilt data does not match your log | Do not train; bring the output to Claude Code |

## Limits to know about

- Free Colab can disconnect after roughly 90 minutes idle or about 12 hours in total, and GPU
  availability is not guaranteed at busy times. Frequent checkpoints are what protect you.
- Keep the browser tab open while training.
- Do not paste passwords, tokens or API keys into any cell or file. None are needed for this
  setup.
