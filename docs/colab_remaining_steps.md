# Colab: remaining steps for the full 543-example run (B2)

Written 2026-11-25. Done so far: setup, B1 (RAG fix), and **Step 14: `results/b2/test_main_dense`** (543 rows, saved on Drive; checkpoint at 06:08 Colab clock).
Remaining: **two runs** (Step 15), a checkpoint, and the finish. Full background is in `docs/colab_new_steps_file.md`.

Measured from the finished run: RAG 958.5 s and hybrid 1,105 s of total time for 543 examples (1.77 s and 2.03 s per example), GPU memory about 2.56 GB, no out-of-memory.
So the two runs below take about **35 minutes (base + fine-tuned) and about 36 minutes (staleness view), plus about 2 minutes loading each: about 1 h 15 min**
(an estimate from the earlier per-example times and this run; base and fine-tuned were not re-timed).

## Rules
1. One cell at a time; if a cell errors, copy the **full** output. Never paste tokens or passwords.
2. Do not touch the session while a run is going (nothing prints for about 15 to 18 minutes per system; the cell stays busy). Keep the tab open.
3. A run is saved to Drive only when it finishes, so stop between runs, never inside one.

## Start here: you are reconnecting, so the setup (Step A) is required
A reconnected runtime is a fresh machine: the code, the data and the `run` helper are gone (Drive and `results/b2/test_main_dense` are still there). Do **Step A in full, in order**, then Step 15.
(If you ever find yourself in a session where `/content/Thesisbaseline1` exists, the `run` helper is defined and `!ls results/b2` lists `test_main_dense`, you can skip Step A and go to Step 15.)

## Step A. Setup (about 5 minutes; do all of A1 to A6)
**A1.** Runtime > Change runtime type > **T4 GPU** > Save > Connect.

**A2. Cell 1**
```python
from google.colab import drive
drive.mount("/content/drive")
```

**A3. Cell 2**
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
**Run Cell 3 immediately after, with nothing in between.**

**A4. Cell 3**
```python
!python tools/colab_setup.py
```
Check: `cuda: True`, `gpu: Tesla T4`, both Drive links, `restoring crosscodeeval from ...`, every "Checking data" line `ok` (9378, 1059, 50, 206, 2018), last line `Setup finished.`
On `DIFFERS`, `MISSING`, `No GPU`, or `results already has files; refusing to replace it`: stop and send the output (or reset: Cell 2, then Cell 3 straight away).

**A5. Cell 4**
```python
!python -c "import rank_bm25, peft, bitsandbytes, faiss, transformers, sentence_transformers; print('imports ok')"
!ls -la experiments/finetuned_model/crosscodeeval/v2
!ls results/b2
```
Success: `imports ok`, the adapter files listed, and `test_main_dense` listed under `results/b2` (it is on Drive).

**A6. Cell 6, the `run` helper**
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

## Step 15. The two remaining runs (about 1 h 15 min in total)
```python
BEST = ["--suppress-fim"]
# 1. frozen base and fine-tuned model, all 543, no retrieval: output is identical in both views (about 35 min)
run("results/b2/test_noretr", "--subset", "test", "--systems", "base", "finetuning_only")
# 2. RAG and hybrid, staleness view (NEW files in the retrieval index), dense top-5 (about 36 min)
run("results/b2/test_staleness_dense", "--subset", "test", "--view", "staleness", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
```
`test_main_dense` is skipped automatically ("already done, skipping").
If you want to stop after the first run (for example to leave), run the checkpoint (Step 15b) after it finishes; run 2 can wait for a later session (do Step A first).
If it ends in the middle of a run, only that run is lost: do Step A and run this cell again.
`out of memory`: Runtime > Restart session, Step A, run this cell again; tell me which run failed.

## Step 15b. Checkpoint (after each run, and at the end)
```python
import glob, os, time
lines = [f"checkpoint {time.strftime('%Y-%m-%d %H:%M:%S')} (Colab clock)"]
for d in sorted(glob.glob("results/b2/*")):
    if not os.path.isdir(d):
        continue
    done = os.path.exists(f"{d}/comparison_summary.json")
    n = sum(1 for _ in open(f"{d}/predictions.jsonl", encoding="utf-8")) if os.path.exists(f"{d}/predictions.jsonl") else 0
    lines.append(f"{'DONE   ' if done else 'PARTIAL'} {d}  rows={n}")
open("results/b2/STATUS.txt", "w").write("\n".join(lines) + "\n")
print("\n".join(lines))
for d in ["test_noretr", "test_staleness_dense"]:
    if os.path.exists(f"results/b2/{d}/comparison_summary.md"):
        print("\n=====", d)
        !cat results/b2/{d}/comparison_summary.md
```
Expect `DONE` and `rows=543` for `test_main_dense`, `test_noretr` and `test_staleness_dense` (the last two once they have run). **Paste the whole output here.**
If anything is `PARTIAL` or the rows are not 543, send the output and do not disconnect.

## Step 16 (optional, only if GPU time is left; about 35 minutes per view). Skip if unsure.
```python
run("results/b2/test_main_bm25", "--subset", "test", "--view", "main", "--retriever", "bm25", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
run("results/b2/test_staleness_bm25", "--subset", "test", "--view", "staleness", "--retriever", "bm25", "--systems", "rag_only", "hybrid", "--save-raw", *BEST)
```
Run Step 15b again afterwards.

## Step 17. Confirm everything is written to Drive, then disconnect (do this last, every time)
`results/` is a link to Drive and Colab can buffer Drive writes for a short time, so verify and flush **before** disconnecting. This is the last cell you run: it unmounts Drive.
```python
import glob, os
from google.colab import drive

print("run folder                          files  predictions rows  summary.json")
for d in sorted(glob.glob("results/b2/*")):
    if not os.path.isdir(d):
        continue
    pred = f"{d}/predictions.jsonl"
    rows = sum(1 for _ in open(pred, encoding="utf-8")) if os.path.exists(pred) else 0
    files = len(os.listdir(d))
    ok = os.path.exists(f"{d}/comparison_summary.json")
    print(f"{d:36}{files:5}  {rows:16}  {'yes' if ok else 'NO (incomplete)'}")

drive.flush_and_unmount()   # forces pending writes to Drive; this unmounts Drive
print("flushed to Drive")
```
Check: `test_main_dense`, `test_noretr` and `test_staleness_dense` each show `543` rows and `yes` (the BM25 folders are optional; ignore an `NO (incomplete)` BM25 folder).
After `flushed to Drive` is printed, do not run anything else that writes files.
Then confirm from outside the runtime: in the browser open Drive > My Drive > thesis > outputs > results > b2 and check each finished folder has `predictions.jsonl` and
`comparison_summary.json` (the page may need a minute to refresh). If the runtime had already ended before you could run this cell, do only the browser check.

## Finish
1. `!wc -l results/b2/*/predictions.jsonl` (543 rows each) and `!ls results/b2` (not needed if Step 17 was run).
2. Runtime > **Disconnect and delete runtime** (Drive is not touched).
3. Download from Drive (My Drive > thesis > outputs > results) into the local `results/`: the whole `b2/` folder, and, if not done yet, `b1/` and `additional_results_colab/`.
   If copying is too slow now, leave everything on Drive and tell me; the pasted tables are enough for me to write the log entry, and the downloads are needed only for the
   per-example analysis (hit-versus-miss, paired differences, functional proxies on the full set).
4. Tell me. I will log Entry 44 (B1) and Entry 45 (B2), and run the full-set analysis locally.

## Files to bring back
- [ ] `results/b2/test_main_dense/`, `results/b2/test_noretr/`, `results/b2/test_staleness_dense/` (each with `predictions.jsonl` 543 rows, `comparison_summary.json`, `comparison_summary.md`)
- [ ] `results/b1/` (8 folders) and `results/additional_results_colab/` (git commit, Python version, `nvidia-smi`, pip freeze), if not already downloaded
- [ ] the Step 15b output pasted in the chat
