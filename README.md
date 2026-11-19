# Comparative Study of Fine-Tuning, Retrieval-Augmented Generation, and Hybrid Models for Code Completion in Enterprise Repositories

Controlled comparison of three ways to adapt a small code model (Qwen2.5-Coder-1.5B) to a private repository,
on public Python benchmarks (CrossCodeEval and RepoBench) and a single 16 GB GPU:

| # | System | Description |
|---|--------|-------------|
| A | **RAG-only** | Retrieved chunks added to the prompt of a **frozen** model |
| B | **Fine-tuning-only** | QLoRA adapter, **no retrieval** at inference |
| C | **Hybrid** *(proposed)* | Retrieved chunks fed to the **fine-tuned** model |

A `base` row (no retrieval, no adapter) is also reported as a reference.
Decision question: given a private repository and a single-GPU budget, which strategy should a team choose, and
when does the hybrid's extra complexity pay off? Hypotheses H1 to H4 are in `docs/things_to_do_first`.

**Where to start reading**

| If you want | Read |
|---|---|
| The plan and framework | `docs/things_to_do_first` |
| What was done, decisions, numbers, caveats | `docs/progress_log.md` (newest entries at the bottom) |
| Every real result in one place | `docs/results_summary.md` |
| How the GPU work runs on Colab | `docs/colab_steps.md` |
| The index of all docs (current vs historical) | `docs/README.md` |

---

## Repository map

```
configs/config.yaml          model names, retrieval and generation settings
data/                        download scripts (raw data and processed data are gitignored)
src/
  prompting.py               the ONE prompt format used by training, demo, hybrid and evaluation
  generation.py              model loading (4-bit, adapter) and greedy one-line generation
  demo.py                    side-by-side base / RAG / fine-tuned / hybrid on one example
  preprocessing/             file-level BASE/NEW/TEST splits, fine-tuning corpora, pilot and RepoBench samples,
                             chunker (prepare_datasets.py is the superseded first design)
  retrieval/                 embedder (UniXcoder), FAISS store, per-repo index builders, retriever,
                             dense / BM25 / random comparisons (CrossCodeEval and RepoBench)
  finetuning/                dataset, QLoRA trainer, base-vs-adapter validation loss
  hybrid/pipeline.py         hybrid inference pipeline
  evaluation/                metrics, evaluator, latency, plots, hit-vs-miss analysis, forgetting check
experiments/
  run_comparison.py          main evaluation: base / RAG / fine-tuned / hybrid on the pilot or the TEST set
  dry_run_pipeline.py        model-free rehearsal of run_comparison (no GPU, no model weights)
tools/colab_setup.py         one-command Colab setup (installs, Drive links, data cache, data checks)
tests/                       unit tests (python -m pytest tests)
docs/                        plan, log, results, Colab guide, reference-paper analysis, archive/
main.py                      older CLI wrapper (index / finetune / compare); the commands below are what we use
results/                     outputs (gitignored)
```

Everything is run from the project root, as modules (`python -m ...`).

---

## Running the study

Steps 1 to 3 are done locally; the GPU steps (4 to 6) run on Colab (`docs/colab_steps.md`). Outputs
under `data/processed`, `data/embeddings`, `results` and `experiments/finetuned_model` are gitignored.

```bash
pip install -r requirements.txt

# 1. Data: download, split by file (BASE/NEW/TEST), leakage-checked fine-tuning corpus, seeded samples
python data/crosscodeeval/download.py
python -m src.preprocessing.build_crosscodeeval_split
python -m src.preprocessing.build_crosscodeeval_finetune
python -m src.preprocessing.build_crosscodeeval_pilot            # 50 pilot examples
python data/repobench/download.py
python -m src.preprocessing.build_repobench_split
python -m src.preprocessing.build_repobench_finetune
python -m src.preprocessing.build_repobench_sample               # 300 examples per setting

# 2. Per-repository indexes (no TEST file is ever indexed)
python -m src.retrieval.build_indexes                            # CrossCodeEval, 206 repos
python -m src.retrieval.build_repobench_indexes --sample-repos   # RepoBench sample, 446 repos

# 3. Retrieval-only results (CPU)
python -m src.retrieval.compare_retrievers
python -m src.evaluation.plot_retrieval_comparison
python -m src.retrieval.compare_retrievers_repobench
python -m src.evaluation.plot_training --run results/training/trainer_state.json

# 4. Fine-tune (Colab GPU)
python -m src.finetuning.trainer --dataset crosscodeeval --run-name v2

# 5. Evaluate (Colab GPU); options: --view staleness, --retriever bm25, --max-code-tokens 480,
#    --noise-chunks N, --top-k K, --limit N (quick test), --skip-codebleu
python -m experiments.dry_run_pipeline --adapter experiments/finetuned_model/crosscodeeval/v2   # model-free check
python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit
python -m src.finetuning.eval_loss --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit

# 6. Analysis
python -m src.evaluation.analyze_predictions results/pilot_main/predictions.jsonl
python -m src.evaluation.forgetting_check --adapter ... --4bit --allow-exec   # Colab only: runs model-written code
```

Tests: `python -m pytest tests`. Evaluation output per run: `comparison_summary.md`, per-system `*_metrics.json`,
`predictions.jsonl` (one row per example) in `results/<subset>_<view>[_options]/`.

---

## Metrics

| Group | Metrics |
|---|---|
| Completion | Exact match, edit similarity, identifier accuracy, CodeBLEU (all with 95% bootstrap CIs; predictions are cut to the first line) |
| Retrieval | hit@k, precision@k, recall@k, MRR (file level; CrossCodeEval relevance is a proxy rule, RepoBench uses the gold snippet file) |
| Efficiency | retrieval and inference latency, peak GPU memory (shared process, so not independent per system) |
| Extra analyses | hit vs miss, staleness (NEW files in the index only), noisy context, top-k sweep, forgetting (HumanEval) |

---

## Configuration

`configs/config.yaml` holds model names and retrieval/generation settings. Seeds and several constants
(split ratios, sample sizes) currently live in the scripts, not in the config (an open item in the log).

---

## Datasets

| Dataset | Used for |
|---|---|
| **CrossCodeEval** (Python) | Primary: complete the rest of a line after a "."; 206 repos with at least 3 files |
| **RepoBench v1.1** (Python, cross-file settings) | Second dataset: next-line prediction; seeded 300-example sample per setting |

Both are public benchmarks used as a source of per-repository files; neither has a training split, so the
fine-tuning corpus is built from BASE files only (see the plan, Sections 3 and 4).

---

## References

See [`docs/references.md`](docs/references.md). Key papers: RepoBench, CrossCodeEval, Wang et al. (2025, the main
comparison, analysed in `docs/reference_paper_comparison.md`), RAFT, LoRA, QLoRA, Qwen2.5-Coder.
