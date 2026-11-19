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
   You should see `adapter_config.json`, `adapter_model.safetensors` and the `checkpoint-*` folders. If the
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
