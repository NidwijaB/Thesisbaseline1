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

## Part 3. Run training

In a new cell:

```python
!python -m src.finetuning.trainer --dataset crosscodeeval
```

What to expect:

- The model downloads from Hugging Face (about 3 GB, a few minutes, first session only).
- You will see a line like `trainable params: ...` and then a progress bar.
- A checkpoint is saved to Drive every 100 steps (the last 2 are kept).
- When it finishes, the adapter is in
  `My Drive/thesis/outputs/finetuned_model/crosscodeeval/`.

Important: until the training-code fixes in `docs/progress_log.md` (Entry 15: masking the prompt
in the loss, adding an end-of-answer token) are done, treat this run as a **test that the setup
works**, not as a result to keep or report.

### If Colab disconnects mid-training

Nothing is lost beyond the last 100 steps. Repeat Part 2 (Cells 1 to 3) and run the same
training command again. It finds the latest checkpoint on Drive and continues. Use
`--no-resume` only if you deliberately want to start over.

---

## Part 4. Saving your work

| What | Where it is saved | What you do |
|---|---|---|
| Trained adapters, checkpoints, results | Google Drive (`thesis/outputs/`) | Nothing, it is automatic |
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
| `out of memory` during training | GPU memory full | Restart the runtime (Runtime > Restart session) and start again from Cell 1 |
| Session disconnected | Idle too long or the 12-hour limit | Part 5, then resume training |
| `DIFFERS` in the data check | Rebuilt data does not match your log | Do not train; bring the output to Claude Code |

## Limits to know about

- Free Colab can disconnect after roughly 90 minutes idle or about 12 hours in total, and GPU
  availability is not guaranteed at busy times. Frequent checkpoints are what protect you.
- Keep the browser tab open while training.
- Do not paste passwords, tokens or API keys into any cell or file. None are needed for this
  setup.
