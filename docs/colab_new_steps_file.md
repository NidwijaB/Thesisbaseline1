# Colab steps (one file): supervisor's requests B1 (RAG fix) and B2 (all 543 TEST examples)

This is the only file to follow for the new GPU work (it replaces `docs/colab_steps_supervisor_run.md`, now a pointer). Follow it top to bottom, one
cell at a time, waiting for each to finish. Written 2026-11-25 for `docs/review_sugesstions` part B.

**Layout:** Part 1 setup (every session) > Part 2 B1, the RAG fix on 50 + 68 examples (Session 1, about 45 to 60 min of GPU) > Part 3 finish and
send results back > **stop and wait for me to choose the best RAG setting** > Part 4 B2, the full 543-example run (Session 2, about 2 h, split into
runs that can be repeated one by one) > Part 5 finish.
All times are **estimates** from the pilot timings (per example: base 1.61 s, RAG 1.72 s, fine-tuned 1.91 s, hybrid 2.24 s, Entry 40) plus 1 to 2
minutes of model loading per run; the full run has never been done at this scale (prompts up to about 6,000 tokens), so Part 4 measures speed first.
Nothing here is a finding until the local analysis is done (pilot n=50, staleness test n=68, full run n=543).

## Rules (read once)
1. If a cell errors, copy the **full** output (from the top of the error). Never paste tokens or passwords into a cell.
2. **Cell 3 must run straight after Cell 2**, with nothing in between (Cell 2 deletes and re-clones the project, which wipes the restored data).
3. If anything looks wrong, reset: Cell 1 (if the runtime restarted), Cell 2, Cell 3, Cell 4. It is safe; nothing on Drive is deleted.
4. Before you start, on your computer: `git status` and push anything new (Colab clones from GitHub; Cell 4 tells you if the new options are missing).
   Today's new local files are not needed on Colab.
5. Everything is written to Drive, so a disconnect loses only the run in progress. The `run(...)` helper (Cell 6) skips runs that already finished:
   after a disconnect, repeat Cells 1 to 4 and 6, then run the same run cell again.

---

## Part 1. Setup (about 5 minutes; every session, after any restart)

**Step 1. GPU on.** Runtime > Change runtime type > Hardware accelerator **T4 GPU** > Save. Click **Connect** and wait for the RAM/Disk bars.

**Step 2. Cell 1, connect Drive**
```python
from google.colab import drive
drive.mount("/content/drive")
```
Allow access in the pop-up. Success: `Mounted at /content/drive`.

**Step 3. Cell 2, get the latest code**
```python
import os, shutil, subprocess
if os.path.exists("/content/Thesisbaseline1"):
    shutil.rmtree("/content/Thesisbaseline1")
subprocess.run(["git", "clone", "--depth", "1",
                "https://github.com/NidwijaB/Thesisbaseline1", "/content/Thesisbaseline1"], check=True)
os.chdir("/content/Thesisbaseline1")
results_dir = "/content/Thesisbaseline1/results"
if os.path.isdir(results_dir) and not os.path.islink(results_dir):
    shutil.rmtree(results_dir)
    print("removed the cloned results/ folder (Drive results are untouched)")
```
Success: no red error text (the "removed the cloned results/ folder" line is expected until `git rm -r --cached results` has been pushed).
**Run Cell 3 immediately.**

**Step 4. Cell 3, setup script** (installs libraries, links Drive, restores the data; about 3 to 5 minutes)
```python
!python tools/colab_setup.py
```
Check: `[3/5]` shows `cuda: True` and `gpu: Tesla T4`; `[4/5]` shows both Drive links; `[5/5]` shows `restoring crosscodeeval from .../crosscodeeval_data.tar`;
every "Checking data" line starts with `ok` (9378, 1059, 50, 206, 2018); the last line is `Setup finished.`
Stop and send the output on: `DIFFERS`, `MISSING`, `no cache ... rebuilding`, `No GPU`, or `results already has files; refusing to replace it` (Rule 2 broken: reset).

**Step 5. Cell 4, check installs, adapter and the new options**
```python
!python -c "import rank_bm25, peft, bitsandbytes, faiss, transformers, sentence_transformers; print('imports ok')"
!ls -la experiments/finetuned_model/crosscodeeval/v2
!python -m experiments.run_comparison --help | grep -E "save-raw|rag-format|suppress-fim|subset"
```
Success: `imports ok`; the adapter folder lists `adapter_config.json` and `adapter_model.safetensors`; the last command mentions `--save-raw`, `--rag-format`,
`--suppress-fim` and the `--subset` choices (`pilot,test,new_relevant`). If not, the push did not happen: push, then reset.

**Step 6. Cell 5, record the environment (about 1 minute; never saved for the earlier runs)**
```python
!mkdir -p results/additional_results_colab
!git -C /content/Thesisbaseline1 log -1 --format=%H | tee results/additional_results_colab/git_commit.txt
!python --version | tee results/additional_results_colab/python_version.txt
!nvidia-smi | tee results/additional_results_colab/nvidia_smi.txt
!pip freeze > results/additional_results_colab/pip_freeze_colab.txt
!wc -l results/additional_results_colab/pip_freeze_colab.txt
!grep -iE "^(torch|transformers|peft|accelerate|bitsandbytes|datasets|sentence-transformers|faiss|rank.bm25|codebleu|tree.sitter|numpy)" results/additional_results_colab/pip_freeze_colab.txt
```
**Copy the printed lines into the chat.** (A pip freeze needs a live runtime: it lists what is installed on that machine, so it cannot be recovered from the
printed output of an earlier, disconnected session. Any new session on the same Colab image has the same preinstalled libraries plus our pinned ones, so
this fresh record is valid for the environment of the new runs; for the old runs it is "same image, probably", not proven.)

**Step 7. Cell 6, the helper that runs one experiment and skips finished ones (once per session)**
```python
import os, subprocess
ADAPTER = "experiments/finetuned_model/crosscodeeval/v2"

def run(out_dir, *extra):
    """Run run_comparison into out_dir unless it already finished there (comparison_summary.json exists)."""
    if os.path.exists(f"{out_dir}/comparison_summary.json"):
        print("already done, skipping:", out_dir)
        return
    cmd = ["python", "-m", "experiments.run_comparison", "--adapter", ADAPTER, "--4bit",
           "--base-prompt", "plain", "--output-dir", out_dir, *extra]
    print(">>", " ".join(cmd))
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in p.stdout:
        print(line, end="")
    if p.wait() != 0:
        raise RuntimeError(f"run failed: {out_dir} (copy the output above)")
```
Success: no output. All runs use adapter v2, 4-bit, and the plain prompt for the frozen model, as in the earlier pilot.

---

## Part 2. B1: the RAG formatting fix (Session 1)

**What is tested.** The frozen RAG system gave an empty answer in 5 of 50 pilot examples and wrote the literal text `<|fim_suffix|>` in 6 of 50.
Four settings are compared for RAG and hybrid (`--systems rag_only hybrid`; the frozen base and the fine-tuned model do not use retrieval, their numbers stay as before):

| Setting | Flags added | Meaning |
|---|---|---|
| S0 | (none; `--save-raw` only) | reference: must reproduce the earlier run |
| S1 | `--suppress-fim` | forbids the fill-in-the-middle and file-separator tokens while generating (all systems in the run) |
| S2 | `--rag-format qwen_repo` | retrieved files in Qwen2.5-Coder's own repository layout (RAG only; the hybrid keeps its training format, so it should equal S0) |
| S3 | both | the two together |

**Step 8. Cell 7, the pilot: 50 examples, main view (about 5 minutes per run)**
```python
run("results/b1/pilot_main_S0", "--systems", "rag_only", "hybrid", "--save-raw")
```
**Check S0 before continuing:** RAG edit similarity must be **0.387** and hybrid **0.644** (exact match 0.14). If not, stop and send the output (the diagnostic must not
change any prediction). Then:
```python
run("results/b1/pilot_main_S1", "--systems", "rag_only", "hybrid", "--save-raw", "--suppress-fim")
run("results/b1/pilot_main_S2", "--systems", "rag_only", "hybrid", "--save-raw", "--rag-format", "qwen_repo")
run("results/b1/pilot_main_S3", "--systems", "rag_only", "hybrid", "--save-raw", "--suppress-fim", "--rag-format", "qwen_repo")
```
Add `"--skip-codebleu"` to a run only if CodeBLEU itself errors (it then shows n/a, never 0).

**Step 9. Cell 8, the 68 staleness-test examples: staleness view (about 6 minutes per run)**
```python
sub = ["--subset", "new_relevant", "--view", "staleness", "--systems", "rag_only", "hybrid", "--save-raw"]
run("results/b1/new68_staleness_S0", *sub)
run("results/b1/new68_staleness_S1", *sub, "--suppress-fim")
run("results/b1/new68_staleness_S2", *sub, "--rag-format", "qwen_repo")
run("results/b1/new68_staleness_S3", *sub, "--suppress-fim", "--rag-format", "qwen_repo")
```
Check: the log prints `new_relevant subset: 68 TEST examples`; S0 hybrid edit similarity should be about **0.695**.

**Step 10. Cell 9, count empty and fill-in-the-middle answers per run (no model; about 1 minute)**
```python
import glob
for d in sorted(glob.glob("results/b1/*")):
    print("=" * 30, d)
    !python -m src.evaluation.inspect_raw {d}/predictions.jsonl
    !grep -E "rag_only|hybrid" {d}/comparison_summary.md
```
**Copy the whole output into the chat.**

---

## Part 3. Finish Session 1, then wait for me

**Step 11. Check the files**
```python
!ls results/b1
!ls results/additional_results_colab
!wc -l results/b1/*/predictions.jsonl
```
Expect 8 folders (the four `pilot_main_*` files 50 rows, the four `new68_*` files 68 rows), each with `predictions.jsonl` and `comparison_summary.json`.

**Step 12. Download** (browser, Google Drive > My Drive > thesis > outputs > results) into the project's local `results/` folder (gitignored): the whole `b1/`
folder and `additional_results_colab/` (commit, Python version, `nvidia-smi`, pip freeze). No token or `.env` file is involved. If downloading is awkward, paste
the printed outputs into the chat.

**Step 13. Tell me.** I compute the empty / fill-in-the-middle counts, metrics with intervals and paired differences against S0, the functional proxies on the
new folders, and name the best RAG setting by the rule fixed in advance (fewest unusable answers first, then highest edit similarity; not worse than S0
for the hybrid). I log it as Entry 44. **Do not start Part 4 until I give you the setting (the `BEST` flags).**
If the GPU quota allows and you want to save time, you may stay connected and carry on with Part 4 in the same session once I reply (skip Part 1).

---

## Part 4. B2: all 543 TEST examples (updated 2026-11-25 after reading the B1 output in `docs/new_session_results`)

**Continue in the same session if it is still connected and Cells 1 to 6 have run (do NOT run Cells 1 to 3 again: Cell 2 would wipe the data).**
You are in `/content/Thesisbaseline1` and the `run(...)` helper from Step 7 exists. If the runtime disconnected or restarted, do Part 1 again first
(Steps 1 to 5 and 7; Step 6, the environment record, is already saved on Drive and need not be repeated).

**What B1 showed (read from the printed output; pilot n=50 and staleness-test n=68; full analysis follows locally):**
- S0 reproduced the earlier run exactly (RAG edit similarity 0.3872, hybrid 0.644), so the diagnostic did not change any prediction.
- RAG edit similarity per setting, pilot / 68-example set: S0 0.387 / 0.350, **S1 (no-FIM) 0.413 / 0.423**, S2 (Qwen repo format) 0.434 / 0.384, S3 0.434 / 0.384.
  Intervals overlap everywhere (for example pilot S0 [0.311, 0.468] vs S2 [0.352, 0.514]); no paired test yet.
- Empty first lines (RAG): pilot S0 5, S1 5, S2 7, S3 7; 68-set S0 1, S1 4, S2 14, S3 14. The `<|fim_suffix|>` answers of S0 (6 of 50, 18 of 68, found earlier)
  are not counted in these numbers; S1 makes them impossible. S2 and S3 give more empty answers (the model often ends with only a newline).
- The hybrid is identical in all four settings (pilot 0.644, 68-set 0.695), so these settings only matter for the RAG row.
- No setting solves the problem: even the best one still has about 13 of 50 and 16 of 68 RAG answers that are empty or under 5 characters (for example `\`, `erro`).
- **Setting chosen for B2 (provisional, by the rule fixed in advance: fewest unusable answers first, then edit similarity, hybrid not worse): S1 = `--suppress-fim`.**
  It has the fewest empty-plus-fill-in-the-middle answers on both sets and the higher or similar edit similarity. The final decision is confirmed locally with the saved
  predictions; if that changes it, only the RAG and hybrid runs 2 and 3 below would need repeating.
- **Measured speed (replaces the planned timing run):** per example, RAG about 1.8 s and hybrid about 2.2 s (pilot and 68-set, with retrieval about 25 ms); earlier base 1.61 s and
  fine-tuned 1.91 s. So: base + fine-tuned 543 x 3.5 s = about 32 min; RAG + hybrid 543 x 4.0 s = about 36 min per view; plus about 1.5 to 2 minutes to load the model for each run.
  **Total about 1 h 50 min for the three runs below** (an estimate: the full set has longer prompts than the pilot, so the first run is the check). Nothing is printed while a system runs
  (about 18 minutes each for RAG and hybrid); the cell stays busy until the run ends. Keep the tab open.

**Step 14. Cell 10, set the flags and start with the main-view RAG and hybrid run (about 40 min; first because it is the headline and tests the long prompts)**
```python
BEST = ["--suppress-fim"]
run("results/b2/test_main_dense", "--subset", "test", "--view", "main", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
```
Checks when it finishes: the log shows `test: 543 examples`-style counts (543), no `out of memory`, and the per-example time in the printed efficiency lines
(`avg_total_ms`, or total ms / 543) is below about 6000 ms. If it is much slower or runs out of memory, stop and send me the output before starting the next run.

**Step 14b. Checkpoint and stop here (do this as soon as Step 14 has finished; takes 2 minutes)**
A Colab runtime cannot be paused, and an idle one is reclaimed, but everything under `results/` is on Drive and stays. A run is saved only when it finishes, so stop
**between** runs, never inside one.
```python
import glob, os, time
lines = [f"checkpoint {time.strftime('%Y-%m-%d %H:%M:%S')} (Colab clock)"]
for d in sorted(glob.glob("results/b2/*")):
    done = os.path.exists(f"{d}/comparison_summary.json")
    n = sum(1 for _ in open(f"{d}/predictions.jsonl", encoding="utf-8")) if os.path.exists(f"{d}/predictions.jsonl") else 0
    lines.append(f"{'DONE   ' if done else 'PARTIAL'} {d}  rows={n}")
open("results/b2/STATUS.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
print()
!cat results/b2/test_main_dense/comparison_summary.md
```
Expect `DONE results/b2/test_main_dense rows=543`, followed by the results table (scores, retrieval metrics, cost) of the run.
**Step 14 result seen on 2026-11-25:** `test: 543 examples, view=main`; run time 05:05:28 to 05:39:53 (about 34 minutes); RAG stop reasons `{eos: 21, newline: 521, max_tokens: 1}`
with 26 empty first lines; hybrid `{eos: 542, max_tokens: 1}` with 0 empty first lines. (Pasted console output cut off before the metric lines; the cell above prints them.)
Then, before you leave: **paste the output of this cell into the chat** (not the progress bars), and run **Runtime > Disconnect and delete runtime** (it does not delete anything on Drive).
If the status says `PARTIAL` or rows is not 543, do not continue: send me the output.

**Resume later (in a new session, any time; Drive keeps everything). Do these in order:**
1. Part 1: Step 1 (T4 GPU), Step 2 (Cell 1), Step 3 (Cell 2), **Step 4 (Cell 3) straight after Cell 2**, Step 5 (Cell 4), Step 7 (Cell 6, the `run` helper). Skip Step 6.
2. Run Step 15 below (it defines `BEST` again and skips any run that already finished, so `test_main_dense` is not repeated).
3. Then Step 14b again (checkpoint), Part 5 (finish and download).

**Step 15. Cell 11, the other two runs (about 35 + 40 min; each is saved to Drive when it ends). Start with `BEST` again after a restart.**
```python
BEST = ["--suppress-fim"]
# frozen base and fine-tuned model, all 543, no retrieval: output is identical in both views (about 35 min)
run("results/b2/test_noretr", "--subset", "test", "--systems", "base", "finetuning_only")
# RAG and hybrid, staleness view (NEW files in the retrieval index), dense top-5 (about 40 min)
run("results/b2/test_staleness_dense", "--subset", "test", "--view", "staleness", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
```
If the session ends in the middle of a run, only that run is lost: repeat Part 1 (Steps 1 to 5, 7), define `BEST` again, and run the same cell; finished runs are skipped.
Each run writes `predictions.jsonl` (one row per example: predictions and scores per system, `retrieved_files`, `relevant_files`, `relevant_in_top_k` (the per-example retrieval hit
flag) and `mrr`), `comparison_summary.json` / `.md` and per-system metric files.
If GPU time is short, the order of importance is: main-view run (Step 14), then `test_noretr`, then the staleness run.

**Step 16. Cell 12, BM25 (optional, only if GPU time is left; about 35 minutes per view)**
```python
run("results/b2/test_main_bm25", "--subset", "test", "--view", "main", "--retriever", "bm25", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
run("results/b2/test_staleness_bm25", "--subset", "test", "--view", "staleness", "--retriever", "bm25", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
```

**Watch for:** `out of memory` (long prompts, up to about 6,000 tokens, on the 15 GB T4): Runtime > Restart session, Part 1 (Steps 1 to 5, 7), define `BEST`, run the same cell again;
tell me which run and system failed. Do not start anything else on the GPU while a run is going.

---

## Part 5. Finish Session 2
1. `!wc -l results/b2/*/predictions.jsonl` (543 rows each; the timing folders have 10) and `!ls results/b2`.
2. Disconnect: Runtime > **Disconnect and delete runtime**.
3. Download `results/b2/` into the local `results/` folder. Paste the timing output (Step 14) and the console output of the runs into the chat.

## Files to send back / save (checklist)
Session 1: [ ] `results/b1/` (8 folders) [ ] `results/additional_results_colab/` (4 files) [ ] the Cell 9 output and the Step 6 printed lines.
Session 2: [ ] `results/b2/test_noretr/`, `test_main_dense/`, `test_staleness_dense/` (and the BM25 folders if run), each with `predictions.jsonl` (543 rows),
`comparison_summary.json`, `comparison_summary.md` [ ] the Step 14 timing numbers and the run console output.
Already local (no GPU): `docs/reproducibility.md`, `results/functional_proxies.csv`, `results/additional_results/*`.

## Troubleshooting
| What you see | Do this |
|---|---|
| `unrecognized arguments: --save-raw` (or `--rag-format`, `--suppress-fim`) | The latest code is not on GitHub: push on your computer, then reset (Cell 2, 3, 4) |
| `results already has files; refusing to replace it` | Rule 2 was broken: reset |
| `DIFFERS` / `MISSING` in the data check | Do not run anything else; send the output |
| `out of memory` | Runtime > Restart session, Cells 1 to 4 and 6, run the same cell again (finished runs are skipped); tell me which run failed |
| `run failed: ...` | Copy the output above the message |
| Session disconnected | Cells 1 to 4 and 6, then run the same run cell again |
| S0 numbers differ from 0.387 / 0.644 | Stop; send the output |

## What I do locally after each session
Session 1: counts and metrics per setting, paired differences against S0, functional proxies, the best setting, Entry 44, `docs/results_summary.md`.
Session 2: merge the runs into one four-system table per view with 95% bootstrap intervals, hit-versus-miss analysis with the per-example hit flags, paired
differences, functional proxies, cost per system, the staleness test on all NEW-relevant examples, a log entry, updated documents and charts.
