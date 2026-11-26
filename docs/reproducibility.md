# Reproducibility details

Written 2026-11-25 for the supervisor's review (`docs/review_sugesstions`, A1 to A3). Every value is read from a file in this
repository or from the saved Colab console output; anything that was not recorded says so. Supporting files are in
`results/additional_results/` (gitignored): `config_snapshot.yaml`, `adapter_v2_config.json`, `trainer_state_summary.json`,
`pip_freeze_local.txt`, `training_examples_per_repo.csv`, `supervisor_checks.json`.

## 1. Code version
- Git commit when this file was first written: `2650823385ca610efd45d9dbc2119ba3bfce4bac` (2026-11-23); on 2026-11-25 `main` and `origin/main` are at `5afdeeb` ("added results in gitignore file"). Commit used on Colab for B1 and B2: `bd097937de23412fae67d5f0886b17643fbf7a12`.
- Colab clones the public repository `https://github.com/NidwijaB/Thesisbaseline1` (depth 1) at the start of every session, so a Colab run uses the
  latest push at that moment. **The commit used by each Colab run before 2026-11-25 was not recorded** (the B1 and B2 runs used `bd097937de23412fae67d5f0886b17643fbf7a12`); the v2 training ran on 2026-11-19 with the code of
  that day (training code version 2, `TRAINING_VERSION = 2`). Future runs: write down `git rev-parse HEAD` in the session (see
  `docs/colab_new_steps_file.md`).
- Seeds: 42 for every split, sample and bootstrap (constants in the scripts; `project.seed: 42` in the config is not read by them).

## 2. Configuration (`configs/config.yaml`, unchanged for the v2 run; full copy in `results/additional_results/config_snapshot.yaml`)
| Block | Values |
|---|---|
| Model | `Qwen/Qwen2.5-Coder-1.5B` (base model, not the instruct version) |
| Retrieval | `microsoft/unixcoder-base`, FAISS `IndexFlatIP` on normalised vectors, chunks of 256 lines with 32 overlap, top_k 5; BM25 (`rank_bm25` `BM25Okapi`) as the alternative |
| Generation | `max_new_tokens` 128, greedy (`do_sample=False`; `temperature` in the config is not used), answer cut to the first line before scoring |
| Metrics | exact match, edit similarity, identifier accuracy, CodeBLEU (`codebleu` package), bootstrap 95% intervals |

## 3. Adapter v2 (QLoRA, CrossCodeEval)
Source: `configs/config.yaml` (finetuning block), `src/finetuning/trainer.py`, `adapter_config.json` of the adapter, `trainer_state.json`.
| Item | Value |
|---|---|
| Method | QLoRA: base weights 4-bit NF4, double quantisation, compute dtype float16 (`prepare_model_for_kbit_training`) |
| LoRA | r = 8, alpha = 16, dropout = 0.05, target modules `q_proj`, `v_proj`, bias none, task CAUSAL_LM (PEFT 0.20.0) |
| Trainable parameters | 1,089,536 of 1,544,803,840 (0.0705%) (progress log, Entry 18) |
| Learning rate / schedule | 2e-4; `Trainer` default linear decay to 0 (logged: 1.94e-4 at step 50, 1.4e-6 at step 1750); no warm-up set; optimizer = library default (not set in the code) |
| Batch | per-device 1, gradient accumulation 16, effective batch 16 |
| Epochs / steps | 3 epochs, 1,761 steps |
| Max length | `max_seq_length` 512 tokens; over-long inputs are cut from the left so the answer is never cut (`src/finetuning/dataset.py`) |
| Loss | answer tokens plus an end-of-sequence token only; prompt and padding masked (-100) |
| Precision / memory | fp16 flag on, gradient checkpointing on |
| Checkpoints | every 100 steps, last 2 kept; evaluation at the end of each epoch |
| Seed | not passed to the `Trainer`; the library default applies (42 in the Transformers version used; **not verified in the saved output**) |
| Hardware / time | Colab T4 (16 GB); 12,570 s (3 h 29 min), about 8.7 GB as shown by Colab; started 2026-11-19 08:59, adapter saved 12:29 |
| Data | `data/processed/crosscodeeval/finetune/{train,val}.jsonl`: 9,378 training and 1,059 validation examples from BASE files only |

### trainer_state.json summary (`results/training/trainer_state.json`, parsed in `results/additional_results/trainer_state_summary.json`)
- Global step 1,761 of 1,761, epoch 3.0, no `nan`; gradient norm between 0.65 and 2.11 over the 35 logged values (every 50 steps).
- Logged training loss: 1.142 at step 50, 0.633 at step 1750 (answer tokens only); epoch means about 0.78 / 0.67 / 0.62 (Entry 18).
- Validation loss stored in the file: 0.6799 (epoch 1) and 0.6774 (epoch 2); epoch 3 (0.6841) is from the console output (Entry 18) because the final
  evaluation was not written into the saved state. Validation is not file-held-out, so it is optimistic.
- Base-versus-adapter validation loss (1,059 examples): base 2.735, adapter 0.6887 (`results/val_loss_base_vs_adapter.json`, Entry 34).

### Is adapter v2 one global adapter? (checked, `results/additional_results/supervisor_checks.json`)
**Yes.** One adapter was trained on the pooled BASE-file corpus of all 206 repositories (plan Section 3: one adapter per dataset); there are no
per-repository adapters. Every one of the 206 repositories contributes training examples. Training examples per repository: **minimum 10, median 39,
maximum 180** (mean 45.5, total 9,378); validation examples per repository: minimum 1, median 5, maximum 20 (total 1,059). The number of examples depends
on how many BASE files a repository has (20 cut points per file at most). Per-repository counts: `training_examples_per_repo.csv`.
Consequence for the thesis: the adapter learns patterns shared across repositories and repository-specific names only in proportion to how many
examples each repository has; this is the "low-data regime" of hypothesis H4.

## 4. How the 50 pilot examples were drawn (checked)
The pilot is **not** a random sample of all 543 TEST examples. The candidates were the **292 TEST examples that have at least one relevant file in the
BASE pool** (main condition, A3 rule, Entries 4 and 13); 50 were drawn from the sorted candidate list with `random.Random(42)`
(`src/preprocessing/build_crosscodeeval_pilot.py`). Verified now: all 50 are TEST examples and all 50 are among the 292; they come from 40
repositories. Because of this choice, retrieval has something to find for every pilot example, which makes the pilot **favourable to retrieval** compared with
the full 543 (where 251 examples have no relevant file in the pool). The 68 staleness-test examples are a different subset (TEST examples with a relevant NEW
file, `--subset new_relevant`). The full run (`--subset test`) uses all 543.

## 5. Software versions
**Colab** (the environment of all training and evaluation runs): from the saved setup output (`docs/results_output_gpu_day2`): GPU Tesla T4,
`bitsandbytes` 0.50.2, installed by `tools/colab_setup.py` with
`pip install transformers==5.15.0 peft==0.20.0 accelerate==1.14.0 datasets==5.0.1 sentence-transformers==5.7.0 bitsandbytes faiss-cpu==1.15.0
rank_bm25==0.2.2 Levenshtein==0.27.4 nltk psutil pyyaml matplotlib` (the CodeBLEU packages are installed by a separate step in the Colab notes).
**Recorded on Colab on 2026-11-25** (session of the B1 and B2 runs, `results/additional_results_colab/`: `git_commit.txt`, `python_version.txt`, `nvidia_smi.txt`, `pip_freeze_colab.txt`, 729 lines):
Python 3.13.16; GPU Tesla T4 (15,360 MiB), driver 580.82.07, CUDA 13.0; torch 2.14.1+cu130; transformers 5.15.0; peft 0.20.0; accelerate 1.14.0; bitsandbytes 0.50.2;
datasets 5.0.1; sentence-transformers 5.7.0; faiss-cpu 1.15.0; rank-bm25 0.2.2; codebleu 0.8.0; tree-sitter 0.26.1; tree-sitter-python 0.25.0; numpy 2.4.6. The code of that
session was commit `bd097937de23412fae67d5f0886b17643fbf7a12` ("updated after review", an ancestor of the current `main` head `5afdeeb`; the local analysis scripts ran on head `5afdeeb` plus the uncommitted `src/evaluation/full_run_analysis.py`).
**Not recorded for the earlier runs** (adapter training 2026-11-19, pilot runs 2026-11-21 and 2026-11-23): their Python, torch, CUDA and codebleu versions and commit. Colab's preinstalled
packages change over time, so the 2026-11-25 record is exact for the B1 and B2 runs and "same pinned libraries, torch and Python probably newer" for the earlier ones (torch 2.14.1 here vs 2.13.0 locally;
the pinned libraries are identical).
**Local machine** (Windows, Python 3.11.9, CPU torch; used for data building, retrieval, analysis; full list in `results/additional_results/pip_freeze_local.txt`):
torch 2.13.0, transformers 5.15.0, peft 0.20.0, accelerate 1.14.0, datasets 5.0.1, sentence-transformers 5.7.0, faiss-cpu 1.15.0, rank-bm25 0.2.2,
Levenshtein 0.27.4, codebleu 0.8.0, tree-sitter 0.26.1, tree-sitter-python 0.25.0, numpy 2.4.6, nltk 3.10.2. The pinned libraries match the Colab pins above.

## 6. Run commands (from the project root)
Data (local or Colab; Colab restores a cache or rebuilds with the same seeds):
```
python -m src.preprocessing.build_crosscodeeval_split
python -m src.preprocessing.build_crosscodeeval_finetune
python -m src.preprocessing.build_crosscodeeval_pilot
python -m src.retrieval.build_indexes
python -m src.retrieval.compare_retrievers            # then: python -m src.evaluation.plot_retrieval_comparison
```
Training (Colab T4, about 3.5 h): `python -m src.finetuning.trainer --dataset crosscodeeval --run-name v2`
Evaluation (Colab, adapter at `experiments/finetuned_model/crosscodeeval/v2`):
```
python -m experiments.dry_run_pipeline --adapter experiments/finetuned_model/crosscodeeval/v2
python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain                       # pilot, main
python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --view staleness
python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant --view staleness
python -m src.finetuning.eval_loss --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec   # Colab only: runs generated code
```
Local analysis: `python -m src.evaluation.analyze_predictions <run>/predictions.jsonl`, `python -m src.evaluation.plot_pilot_results`,
`python -m src.evaluation.supervisor_checks`, `python -m src.evaluation.functional_proxies`. Tests: `python -m pytest tests` (39 pass).
Exact flags for every run reported so far: `docs/colab_steps_new.md` sections C, D and F and `docs/progress_log.md` Entries 32 to 42.

## 7. Fairness of the comparison (adapter setup)
- Same base model (`Qwen2.5-Coder-1.5B`, 4-bit NF4 at inference for all four systems), same greedy decoding, same 128-token limit, answer cut to the first
  line, same metrics, same examples in the same order.
- Base and RAG (frozen model) use the **plain** code-continuation prompt; fine-tuned and hybrid use the **training prompt format** (instruction wrapper)
  they were trained on. Each model is given the format it works with; a prompt-format comparison shows the choice matters a lot (plain minus instruction
  for the base: +0.257 edit similarity, Entry 41). This is a documented design choice, not a hidden difference.
- The hybrid sees retrieved chunks that the adapter never saw in training (no retrieval-formatted fine-tuning, no RAFT-style variant yet).
- The adapter was trained on BASE files of the same repositories it is tested on (different files; TEST files never in the corpus, leakage assertions in
  Entries 8 and 11). The frozen base model has no such repository exposure, so part of the fine-tuning gain is "knows this repository's names", which is
  the effect being measured, not a leak. Retrieval pools hold the same BASE files (main view), so both channels carry the same information.
- One seed, one adapter, one model size: no variance estimate over training runs. State as a limitation.
