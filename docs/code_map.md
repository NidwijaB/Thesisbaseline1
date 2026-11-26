# Code map: which file does what, and where the key values live

For the presentation: if someone asks "where is X in your code?", find X in section 1 (quick answers), then open the file. Paths are from the project root
(`D:\Users\nidwija.bhatta\Documents\Automation\Thesisbaseline1`). Line numbers are approximate (they drift if files are edited). Everything is run as
`python -m <module>` from the project root with the project's `venv`.

## 1. Quick answers (question -> where to look)

| If they ask... | Open | What to point at |
|---|---|---|
| Which model, quantisation, LoRA settings, learning rate, epochs? | `configs/config.yaml`, block `finetuning:` | `lora_r: 8`, `lora_alpha: 16`, `lora_dropout: 0.05`, `target_modules: [q_proj, v_proj]`, `learning_rate: 2.0e-4`, `epochs: 3`, `batch_size: 1` x `gradient_accumulation_steps: 16`, `max_seq_length: 512`, `bnb_4bit_*` (NF4, double quantisation) |
| How is the model fine-tuned? | `src/finetuning/trainer.py` | `run_finetuning()`: loads the 4-bit base model, wraps it with LoRA (`LoraConfig`), trains with the Hugging Face `Trainer`, saves the adapter |
| What exactly is the model trained on, and how is the loss computed? | `src/finetuning/dataset.py` | `encode_example()`: loss only on the answer tokens plus the end token (prompt and padding are `-100`); over-long inputs cut from the left; `TRAINING_VERSION = 2` |
| How were the training examples made without leaking test data? | `src/preprocessing/build_crosscodeeval_finetune.py` | cuts only inside BASE files (`EXAMPLES_PER_FILE = 20`, `VAL_FRAC = 0.1`, `MAX_PREFIX_CHARS = 1500`); leakage assertions at the end of `main()` |
| How is the BASE / NEW / TEST split done? | `src/preprocessing/build_crosscodeeval_split.py` | constants at the top (`SEED = 42`, `MIN_FILES = 3`, `MIN_FILES_FOR_NEW = 5`, `NEW_FRAC`, `TEST_FRAC`), `_split_repo()`, `check_assertions()` |
| How does retrieval work (chunks, embeddings, index)? | `src/preprocessing/chunker.py`, `src/retrieval/embedder.py`, `vector_store.py`, `retriever.py`, `build_indexes.py` | 256-line chunks with 32 overlap (`config.yaml` `retrieval:`), UniXcoder embeddings, FAISS `IndexFlatIP`, one index per repository |
| Where is BM25? | `experiments/run_comparison.py` (`bm25_search`, `--retriever bm25`) and `src/retrieval/compare_retrievers.py` | `rank_bm25.BM25Okapi` over the same chunks |
| What is the prompt? Where are the 4 systems defined? | `src/prompting.py` | `HEADER` / `FOOTER` (instruction format, used by the adapter systems), `build_plain_prompt()` (base and RAG), `format_context()` (retrieved chunks as `#` comments), `build_repo_prompt()` (Qwen repository format), `build_system_prompt()` chooses per system |
| How is the answer generated? | `src/generation.py` | `load_model()` (4-bit, optional adapter), `complete()` (greedy, `max_new_tokens` from the config = 128), `code_marker_ids()` for `--suppress-fim` |
| Where are the four systems actually run and compared? | `experiments/run_comparison.py` | `SYSTEMS` dict (line ~69): base = no adapter, no retrieval; rag_only = no adapter + retrieval; finetuning_only = adapter, no retrieval; hybrid = adapter + retrieval. `main()` does retrieval once per example, then loops over systems |
| What is the "hybrid"? | same `SYSTEMS` dict | hybrid = `(uses adapter, uses retrieval)`: the fine-tuned model with the same retrieved chunks in the prompt. `src/hybrid/pipeline.py` is a standalone class version of the same idea (retriever + fine-tuned model); the reported numbers come from `run_comparison.py` |
| How are exact match, edit similarity, identifier accuracy, CodeBLEU computed? | `src/evaluation/metrics.py` | `exact_match`, `edit_similarity` (Levenshtein ratio of the stripped strings), `identifier_accuracy`, `code_bleu` (the `codebleu` package; raises if missing, never a silent 0), `bootstrap_ci` |
| How are retrieval metrics computed? | `src/evaluation/metrics.py` | `precision_at_k`, `recall_at_k`, `mean_reciprocal_rank`, `evaluate_retrieval` |
| Where do the confidence intervals and paired tests come from? | `src/evaluation/analyze_predictions.py`, `full_run_analysis.py` | `boot_mean`, `boot_diff_paired` (2,000 resamples, seed 42); `analyse()` gives hit-vs-miss and paired differences |
| How do you check the pilot / full-run sampling? | `src/preprocessing/build_crosscodeeval_pilot.py`, `src/evaluation/supervisor_checks.py` | pilot = 50 drawn (seed 42) from the 292 TEST examples with a relevant file in the BASE pool |
| Forgetting check? | `src/evaluation/forgetting_check.py` | HumanEval pass@1 base vs adapter; executes model-written code, Colab only, needs `--allow-exec` |
| Validation loss base vs adapter? | `src/finetuning/eval_loss.py` | result in `results/val_loss_base_vs_adapter.json` (base 2.735, adapter 0.689) |
| How do I show a live example? | `src/demo.py` | `python -m src.demo --task-id <id> --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit` prints base / RAG / fine-tuned / hybrid next to the true answer (needs a GPU; use `docs/example_outputs.md` for saved examples) |
| How was Colab set up? | `tools/colab_setup.py`, `docs/colab_new_steps_file.md`, `docs/colab_remaining_steps.md` | pinned installs, Drive links, data cache and checks |

## 2. Folder by folder

### `configs/`
- `config.yaml`: the settings file. Blocks: `llm` (model `Qwen/Qwen2.5-Coder-1.5B`, 4-bit), `retrieval` (UniXcoder, FAISS, chunk 256/32, `top_k: 5`, sweep values `[1, 3, 5, 10]`),
  `finetuning` (QLoRA values above), `generation` (`max_new_tokens: 128`, greedy), `evaluation` (metric names). Seeds and split constants are in the scripts, not here.

### `data/` (scripts only; the data itself is gitignored)
- `crosscodeeval/download.py`, `repobench/download.py`: download the public benchmarks from Hugging Face.

### `src/preprocessing/` (data building; run once, outputs in `data/processed/`)
| File | Purpose |
|---|---|
| `build_crosscodeeval_split.py` | file-level BASE / NEW / TEST split per repository, leakage assertions, writes `files.jsonl`, `manifest.jsonl`, `examples.jsonl` |
| `build_crosscodeeval_finetune.py` | fine-tuning corpus (`train.jsonl` 9,378, `val.jsonl` 1,059) from BASE files only, plus checks that no TEST answer is in it |
| `build_crosscodeeval_pilot.py` | the 50 seeded pilot examples (`pilot_ids.json`) |
| `build_repobench_split.py`, `build_repobench_finetune.py`, `build_repobench_sample.py` | the same for RepoBench (split, corpus of 12,000, 300-per-setting evaluation sample) |
| `chunker.py` | splits files into 256-line chunks with 32 lines overlap |
| `prepare_datasets.py` | **superseded** first design (kept for history; do not present) |

### `src/retrieval/`
| File | Purpose |
|---|---|
| `embedder.py` | UniXcoder embeddings (note: capped at 1,024 tokens, a bug fixed in Entry 12) |
| `vector_store.py` | FAISS index wrapper, `RetrievedChunk` |
| `build_indexes.py`, `build_repobench_indexes.py` | per-repository indexes, "main" (BASE only) and "staleness" (BASE + NEW); assertion that no TEST file is indexed |
| `retriever.py` | `Retriever` class (query -> top-k chunks); used by `src/demo.py` and `src/hybrid/pipeline.py`. `experiments/run_comparison.py` calls the embedder and `vector_store` directly (and BM25) so that retrieval is done once per example for RAG and hybrid |
| `compare_retrievers.py`, `compare_retrievers_repobench.py` | dense vs BM25 vs random: hit@k, precision/recall@k, MRR with intervals (outputs `results/retrieval_comparison.json`, `repobench_retrieval_comparison.json`) |
| `sanity_check_indexes.py` | smoke test of the indexes |

### `src/finetuning/`
`trainer.py` (QLoRA training, checkpoints every 100 steps, resumable), `dataset.py` (tokenisation and loss masking), `eval_loss.py` (base vs adapter validation loss).

### `src/` top level
`prompting.py` (the one prompt format), `generation.py` (model loading and generation), `demo.py` (live side-by-side), `hybrid/pipeline.py` (hybrid inference class), `utils/` (config loader, logger).

### `experiments/`
- `run_comparison.py`: **the main evaluation script.** Options worth knowing: `--subset pilot|test|new_relevant`, `--view main|staleness`, `--retriever dense|bm25`, `--systems ...`, `--top-k`, `--base-prompt plain|instruction`,
  `--suppress-fim`, `--rag-format comments|qwen_repo`, `--save-raw`, `--4bit`. Writes `predictions.jsonl`, `comparison_summary.json/.md`, per-system metric files.
- `dry_run_pipeline.py`: model-free rehearsal (no GPU).

### `src/evaluation/` (metrics, analysis, plots)
| File | Purpose |
|---|---|
| `metrics.py`, `evaluator.py`, `latency.py` | metric functions, the per-system evaluation and summary table, timing and GPU memory |
| `analyze_predictions.py` | hit vs miss and paired differences for one run |
| `full_run_analysis.py` | **2026-11-25:** joins the no-retrieval and retrieval runs, four-system tables with intervals, staleness change, dense vs BM25, rank analysis, B1 settings, functional proxies |
| `functional_proxies.py` | % empty / fill-in-the-middle / parses / identifiers present in repo (rough proxies) |
| `supervisor_checks.py` | adapter scope and training examples per repo; pilot sampling check |
| `inspect_raw.py` | summarises the raw completions saved with `--save-raw` |
| `forgetting_check.py` | HumanEval forgetting check (Colab only) |
| `example_outputs.py`, `plot_pilot_results.py`, `plot_retrieval_comparison.py`, `plot_training.py` | produce the example file and the figures |

### `tests/`
39 unit tests (`python -m pytest tests`): metrics, prompts, dataset masking, analysis, generation diagnostics, run options, forgetting check.

### `docs/` (documents; the ones to know)
| File | Use |
|---|---|
| `progress_log.md` | every step with numbers (Entries 1 to 46); the answer to "what did you do when" |
| `results_summary.md` | every real result in one place (section 5g = the full 543-example run) |
| `report_update_2026-11-25.md` | today's results in report form |
| `reproducibility.md` | settings, versions, commands, fairness |
| `things_to_do_first` | the plan and hypotheses H1 to H4 |
| `reference_paper_comparison.md` | Wang et al. (2025) vs this thesis |
| `example_outputs.md` | six example completions side by side |
| `colab_new_steps_file.md`, `colab_remaining_steps.md`, `colab_steps.md` | how the GPU runs were done |
| `slides/`, `reportss/` | presentation files and report drafts |
| `steps.txt` (root), `thesis_implementation_guide.md`, `session_prompt`, `prepare_datasets.py` | **outdated** early design; avoid showing |

## 3. Where the numbers on the slides come from (all under `results/`, gitignored: only on this computer)
| Number or chart | File |
|---|---|
| Full run n=543 table (base, RAG, fine-tuned, hybrid) | `results/b2/test_noretr/comparison_summary.md` + `results/b2/test_main_dense/comparison_summary.md`; merged and with intervals in `results/additional_results/full_run_summary.md` |
| Staleness view (543) | `results/b2/test_staleness_dense/`; staleness-test 68 examples in `full_run_summary.md` (section "Staleness change") |
| Per-example predictions (to show a real answer) | `results/b2/*/predictions.jsonl` (one row per example, all systems) |
| RAG formatting fix (S0 to S3) | `results/b1/*/`, summary `results/additional_results/b1_settings.csv` |
| Functional proxies | `results/additional_results/functional_proxies_full.csv` |
| Pilot results (n=50), prompt effect, forgetting | `results/pilot_main_plainbase/`, `results/pilot_staleness_plainbase/`, `results/forgetting_humaneval_plain.json`, charts `results/figures/pilot_*.png`, numbers `results/figures/pilot_numbers.csv` |
| Retrieval comparison (dense vs BM25 vs random) | `results/retrieval_comparison.json`, `results/repobench_retrieval_comparison.json`, charts `results/figures/retrieval_*.png`, `hit_at_k_main.png` |
| Training curve | `results/figures/training_loss.png` (from `results/training/trainer_state.json`) |
| Validation loss base vs adapter | `results/val_loss_base_vs_adapter.json` |
| Training examples per repository | `results/additional_results/training_examples_per_repo.csv`, summary in `supervisor_checks.json` |
| Config and versions used | `results/additional_results/config_snapshot.yaml`, `adapter_v2_config.json`, `results/additional_results_colab/` (Colab versions, GPU, commit) |
| The adapter itself | `experiments/finetuned_model/crosscodeeval/v2/` (about 4 MB, `adapter_model.safetensors`) |

## 4. The data flow in one paragraph (for a verbal answer)
Benchmark data is downloaded (`data/*/download.py`), split by file into BASE / NEW / TEST per repository (`build_*_split.py`), the BASE files become the retrieval pool (chunked, embedded, indexed per repository:
`build_indexes.py`) and the fine-tuning corpus (`build_*_finetune.py`); TEST files appear in neither (assertions enforce it). The adapter is trained once (`trainer.py`, Colab T4). `run_comparison.py` then takes each TEST example,
retrieves chunks (`retriever.py` or BM25), builds the prompt for each of the four systems (`prompting.py`), generates one line (`generation.py`), scores it (`metrics.py`) and writes `predictions.jsonl`;
the analysis scripts turn those files into the tables, intervals and charts.

## 5. Honest notes if asked
- Seeds and split constants live in the scripts, not in `config.yaml` (open item).
- Only the adapter and `config.yaml` define "the model setup"; no secrets are used anywhere (the Hugging Face warning about an unauthenticated request is harmless: public models).
- `results/`, `data/processed/`, `data/embeddings/` and the adapter are gitignored: they exist on this computer and on Drive, not on GitHub.
- Model-written code (HumanEval) was executed only on Colab, never locally.
