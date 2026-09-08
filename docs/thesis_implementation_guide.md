# Thesis Implementation Guide
## Proposed Steps → What's Actually Built (and What Still Needs Doing)

This document maps every proposed implementation step to what is already in this
repository, noting where the repo goes further than proposed, where it differs,
and where you still need to manually act.

---

## PHASE 1 — Project Setup
**Status: ✅ Complete**

Everything is already set up:
- `requirements.txt` contains all dependencies (torch, transformers, peft,
  bitsandbytes, faiss-cpu, sentence-transformers, evaluate, Levenshtein, psutil, …)
- `configs/config.yaml` is the central control panel for all hyperparameters
- `src/` is fully structured with all modules in place
- Run `pip install -r requirements.txt` to get started on a new machine

---

## PHASE 2 — Datasets

### Step 1 — Download RepoBench
**Status: ✅ Script ready — you just need to run it**

`data/repobench/download.py` pulls `tianyang/repobench_python_v1.1` (the real
HuggingFace dataset ID, verified against the dataset card) across all three
configs (`cross_file_first`, `cross_file_random`, `in_file`) and saves each
to `data/repobench/<config_name>/`.

```bash
python data/repobench/download.py
```

---

### Step 2 — Download CrossCodeEval
**Status: ✅ Script ready — you just need to run it (or use the official archive)**

`data/crosscodeeval/download.py` defaults to the community HuggingFace mirror
`ZHENGRAN/cross_code_eval_python` (no email/request needed). The *official*
amazon-science/cceval release is only distributed as a manually-requested
`.tar.xz` — the script's docstring explains how to swap to that path if you
want the canonical benchmark instead of the mirror.

```bash
python data/crosscodeeval/download.py
```

---

### Step 3 — Convert to Working Format
**Status: ✅ Script ready — `src/preprocessing/prepare_datasets.py`**

Proposed format:
```json
{ "prompt": "...partial code...", "target": "...correct completion..." }
```

**Important difference — the repo uses a slightly different field naming:**
```json
{ "input": "...partial code...", "output": "...correct completion..." }
```

This is intentional and better — `src/finetuning/dataset.py` wraps these fields
in a proper instruction-following prompt template automatically:

```
### Instruction:
Complete the following code.

### Input:
{input}

### Response:
{output}
```

This is more robust than a raw prompt/target pair because it follows the
instruction-tuning format that Qwen2.5-Coder was trained on.

**What you need to do:**
```bash
# After both datasets are downloaded (Steps 1-2 above):
python src/preprocessing/prepare_datasets.py
```

This also adds a third field, `relevant_files`, used only for scoring
retrieval quality (Precision@K, Recall@K, MRR):
```json
{ "input": "...", "output": "...", "relevant_files": ["path/a.py", "path/b.py"] }
```

The script groups examples by repository before splitting 80/10/10 into
train/val/test, so the fine-tuned model is never trained on a repo it is
later tested against.

Storage format: `data/processed/` uses `.jsonl` (one JSON object per line).
This is already what all downstream code expects — no changes needed there.

---

## PHASE 3 — RAG-Only Baseline (Baseline A)

### Step 1 — Split Repository into Chunks
**Status: ✅ Done — and more sophisticated than proposed**

Proposed: Split `utils.py`, `auth.py`, `config.py` into simple chunks.

What the repo has (`src/preprocessing/chunker.py`):
- Line-based chunking with configurable `chunk_size` (default 256 lines) AND
  `chunk_overlap` (default 32 lines) — overlap ensures context is not lost at
  boundaries, which the original proposal did not include
- Recursively walks the entire repository directory
- Tracks `file_path`, `start_line`, `end_line`, `language` per chunk
- Controlled via `configs/config.yaml` → `retrieval.chunk_size` and
  `retrieval.chunk_overlap`

> Note in config.yaml: chunk_size is in lines. For embedding models with token
> limits, you may want to switch to token-based chunking later. The comment in
> chunker.py already suggests upgrading to a tree-sitter AST chunker for
> function-boundary-aware splitting — worth mentioning in your thesis methodology.

---

### Step 2 — Generate Embeddings
**Status: ✅ Done — better model than proposed**

Proposed: `BAAI/bge-small-en` (a general-purpose English text model)

What the repo has (`src/retrieval/embedder.py`): `microsoft/unixcoder-base`

**Why the repo choice is better for your thesis:**
- `unixcoder-base` is trained specifically on source code (GitHub)
- It understands code syntax, identifiers, and API names
- Using a code-specific embedding model is a stronger methodological choice and
  worth a sentence in your thesis methodology section
- Alternative: `BAAI/bge-base-en-v1.5` is available in config.yaml comments if
  you want to run an ablation comparing embedding models (good for RQ4)

Embeddings are L2-normalised (unit vectors) so cosine similarity = inner product,
which is what FAISS IndexFlatIP uses — this is all wired up correctly.

---

### Step 3 — Store Embeddings
**Status: ✅ Done — FAISS implemented with persistence**

Proposed: Use FAISS or ChromaDB, recommended FAISS initially.

What the repo has (`src/retrieval/vector_store.py`):
- FAISS `IndexFlatIP` (exact inner-product search on normalised vectors)
- `save()` and `load()` methods — index persists to `data/embeddings/`
- ChromaDB stub is noted in the docstring as a future swap
- Stored files: `index.faiss` + `chunks.pkl` (chunk metadata)

---

### Step 4 — Build Retriever
**Status: ✅ Done**

Proposed: Given `def create_order():` retrieve `OrderService.py`, `OrderFactory.py`,
`Customer.py`.

What the repo has (`src/retrieval/retriever.py`):
- `Retriever` class wraps embedder + vector store
- `retrieve(query)` → returns top-K `RetrievedChunk` objects with `content`,
  `file_path`, and `score`
- `build_context_string(query)` → returns formatted context block ready for prompt
- `top_k` is configurable (default 5, sweep values [1,3,5,10] in config for RQ4)

---

### Step 5 — Build Prompt
**Status: ✅ Done — more structured than proposed**

Proposed prompt:
```
Repository Context: <retrieved code>
Current File: <partial code>
Complete the code:
```

What the repo has (`src/hybrid/pipeline.py` and `experiments/run_comparison.py`):
```
### Retrieved Context:
{context}

### Current File:
{query}

### Response:
```

This is better — it uses instruction-following markers that align with how
Qwen2.5-Coder was trained, leading to more reliable completions.

---

### Step 6 — Generate Completion
**Status: ✅ Done — better model than proposed alternatives**

Proposed options: DeepSeek-Coder, Qwen2.5-Coder, CodeT5+, StarCoder2

What the repo uses: `Qwen/Qwen2.5-Coder-1.5B` with 4-bit quantization at
inference (`load_in_4bit: true` in config.yaml)

Why this is the right choice:
- State-of-the-art small code model (2024/2025)
- 1.5B parameters fits in 4–6 GB VRAM with 4-bit quantization
- The same model is used for both RAG-only (frozen) and fine-tuning (adapted),
  making the comparison fair — isolating the effect of each technique

**Result: Baseline A (RAG-Only) is fully implemented.**
Run: `python main.py index --repo-root <path> --repo-id <name>` to build the index.

---

## PHASE 4 — Fine-Tuning Baseline (Baseline B)

### Step 1 — Prepare Training Data
**Status: ⚠️ Partially done — format defined, data not yet created**

Proposed: `input: def process_order()` / `output: order = OrderFactory()`

What the repo has:
- `src/finetuning/dataset.py` reads `data/processed/train.jsonl` and
  `data/processed/val.jsonl` in `{"input": "...", "output": "..."}` format
- Wraps in instruction-following template automatically
- Handles tokenisation, truncation, and padding

**What you still need to do:**
```
TODO: Populate data/processed/train.jsonl and data/processed/val.jsonl
      by running your preprocessing script on RepoBench / CrossCodeEval.
      See Phase 2 Step 3 above.
```

---

### Step 2 — Choose Model
**Status: ✅ Done**

Proposed: Qwen2.5-Coder 1.5B or CodeT5+ (small enough to train)

What the repo uses: `Qwen/Qwen2.5-Coder-1.5B` — exactly the recommended choice.
Set in `configs/config.yaml` → `finetuning.base_model`.

---

### Step 3 — Use LoRA (not full fine-tuning)
**Status: ✅ Done — uses QLoRA which is even more memory-efficient**

Proposed: Use PEFT + LoRA to save GPU memory.

What the repo has (`src/finetuning/trainer.py`):
- Uses **QLoRA** (Quantized LoRA) — 4-bit NF4 quantization of base model weights
  + LoRA adapters on top. This is the most memory-efficient approach available.
- `lora_r: 8`, `lora_alpha: 16`, `lora_dropout: 0.05`
- Target modules: `q_proj`, `v_proj` (attention layers)
- Gradient checkpointing enabled
- Effective batch size = 16 via `gradient_accumulation_steps: 16`
  with `per_device_train_batch_size: 1` (fits in ~4 GB VRAM)

**For your thesis:** QLoRA is worth explicitly mentioning as your choice of
parameter-efficient fine-tuning (PEFT) method. Cite the QLoRA paper
(Dettmers et al., 2023).

---

### Step 4 — Train and Store Adapter
**Status: ✅ Done**

What the repo has:
- `trainer.py` saves the full model + tokenizer to `experiments/finetuned_model/`
- The adapter weights are merged with the base model on save

**What you need to do to actually run training:**
```bash
# TODO: Run this once your data/processed/train.jsonl is ready
python main.py finetune
```

**Result: Baseline B (Fine-Tuning-Only) is fully implemented.**

---

## PHASE 5 — Hybrid System (Your Contribution)
**Status: ✅ Done — matches proposed architecture exactly**

Proposed architecture:
```
Repository → Retriever → Relevant Code → Fine-Tuned Model → Completion
```

What the repo has (`src/hybrid/pipeline.py`):
- `HybridPipeline` class combines `Retriever` + fine-tuned `AutoModelForCausalLM`
- `complete(partial_code)` method:
  1. Calls `retriever.build_context_string(partial_code)`
  2. Formats context + query into prompt
  3. Generates with the fine-tuned model
- Supports 4-bit inference (same memory budget as baseline)
- `temperature=0.2` for slightly varied but mostly deterministic output

**Result: Baseline C (Hybrid) is fully implemented — this is your thesis contribution.**

---

## PHASE 6 — Evaluation Pipeline
**Status: ✅ Done — more complete than proposed**

### Exact Match
**Status: ✅ Done** — `src/evaluation/metrics.py` → `exact_match()`
Strips whitespace before comparing. Returns 1.0 or 0.0.

### Edit Similarity
**Status: ✅ Done** — `src/evaluation/metrics.py` → `edit_similarity()`
Uses `python-Levenshtein` (fast C extension), falls back to `difflib` if not installed.

### Identifier Accuracy
**Status: ✅ Done** — `src/evaluation/metrics.py` → `identifier_accuracy()`
Regex-based extraction of all non-keyword identifiers. Measures overlap between
predicted and reference identifier sets. This is your most enterprise-relevant metric.

> Upgrade path: Replace regex with `tree-sitter` AST parsing for more accurate
> identifier extraction — worth noting as a limitation/future work in your thesis.

### CodeBLEU
**Status: ✅ Done** — `src/evaluation/metrics.py` → `code_bleu()`
Via HuggingFace `evaluate` library. Falls back to 0.0 gracefully if library not
installed. Run `pip install evaluate sacrebleu` to enable.

### Retrieval Metrics — Precision@K, Recall@K, MRR
**Status: ✅ Done — MRR added, all wired into comparison output**
- `precision_at_k()`, `recall_at_k()`, `mean_reciprocal_rank()` all in `metrics.py`
- `evaluate_retrieval()` aggregates across all queries with K-sweep [1, 3, 5, 10]
- Results appear in `results/comparison_summary.md` under "Retrieval Quality" table
- Fine-Tuning-Only correctly shows N/A (no retrieval component)

**Status: ✅ Wired up** — `experiments/run_comparison.py` (`run_rag_only()` and
`run_hybrid()`) now builds `retrieved_list` from `retriever.retrieve(...)` and
`relevant_list` from each example's `relevant_files` field (written by
`prepare_datasets.py`). If any example is missing that field, retrieval
metrics are skipped with a warning instead of crashing — so this still works
even on a benchmark file you hand-write yourself without `relevant_files`.

### Efficiency — Latency and Memory
**Status: ✅ Done — more complete than proposed**

Proposed: `time.time()` for latency, track GPU usage.

What the repo has (`src/evaluation/latency.py`):
- `retrieval_latency_ms` — FAISS search time per sample
- `inference_latency_ms` — model generation time per sample
- `total_latency_ms` and `avg_total_ms` — end-to-end
- `peak_gpu_mb` — via `torch.cuda.max_memory_allocated()`
- `peak_cpu_ram_mb` — via `psutil` (process RSS) ← handles CPU-only runs too

All tracked in `LatencyRecord` dataclass and included in
`results/comparison_summary.md` under the "Efficiency" table.

---

## Running the Full Comparison
**Status: ✅ Ready — once data is in place**

```bash
# Step 1: Build the FAISS index from a repository
python main.py index --repo-root path/to/repo --repo-id my_repo

# Step 2: Fine-tune (needs data/processed/train.jsonl)
python main.py finetune

# Step 3: Run all three systems and generate comparison tables
python main.py compare \
    --benchmark data/processed/test.jsonl \
    --ft-model  experiments/finetuned_model
```

Output: `results/comparison_summary.md` — copy this table directly into your thesis.

---

## What You Still Need To Do — Step by Step

Everything in the code is ready and waiting. The only things blocking you from
running experiments are the steps below. Do them in order.

---

### 🔴 STEP 1 — Install all dependencies
**Do this first, on every machine you work on.**

```bash
pip install -r requirements.txt
```

This installs: torch, transformers, peft, bitsandbytes, faiss-cpu,
sentence-transformers, evaluate, Levenshtein, psutil, and everything else.

---

### 🔴 STEP 2 — Download RepoBench
**Script already written: `data/repobench/download.py`**

```bash
python data/repobench/download.py
```

Pulls `tianyang/repobench_python_v1.1` (verified real dataset ID) for all
three configs into `data/repobench/cross_file_first/`, `.../cross_file_random/`,
`.../in_file/`. Each row contains `context` (cross-file snippets),
`import_statement`, `cropped_code`, `next_line` (the prediction target), and more.

---

### 🔴 STEP 3 — Download CrossCodeEval
**Script already written: `data/crosscodeeval/download.py`**

```bash
python data/crosscodeeval/download.py
```

Defaults to the community HuggingFace mirror (`ZHENGRAN/cross_code_eval_python`)
so you don't have to email the original authors for the official `.tar.xz`
archive. Read the docstring at the top of that file if you'd rather use the
official release instead — it explains the small field-name differences.

---

### 🔴 STEP 4 — Run the Preprocessing Script
**Script already written: `src/preprocessing/prepare_datasets.py`**

```bash
python src/preprocessing/prepare_datasets.py
```

Reads everything downloaded in Steps 2-3, maps both datasets' native fields
onto the unified `{"input", "output", "relevant_files"}` format, groups by
repository, and writes an 80/10/10 split to `data/processed/train.jsonl`,
`val.jsonl`, `test.jsonl`. The `relevant_files` field is what makes retrieval
metrics (Precision@K, Recall@K, MRR) meaningful later — don't skip this step.

If either dataset's schema has changed since this was written, the script
logs a warning and skips that dataset rather than crashing — check the logs.

---

### 🟡 STEP 5 — Build the FAISS Search Index
**Run once after your data is ready.**

```bash
python main.py index --repo-root data/repobench/ --repo-id repobench
```

This runs `chunker.py` → `embedder.py` → `vector_store.py` and saves the index
to `data/embeddings/`. Takes a few minutes depending on dataset size.

---

### 🟡 STEP 6 — Fine-Tune the Model
**Run once after `data/processed/train.jsonl` exists.**

```bash
python main.py finetune
```

This runs `src/finetuning/trainer.py` with QLoRA on `Qwen2.5-Coder-1.5B`.
Saves the trained adapter to `experiments/finetuned_model/`.

Expected time: 1–3 hours depending on dataset size and GPU.
Requires ~4–6 GB VRAM (or will run slowly on CPU).

---

### 🟡 STEP 7 — Run the Full Comparison
**Do this after Steps 5 and 6 are complete.** (Retrieval ground truth is
already wired into `experiments/run_comparison.py` — nothing to edit here.)

```bash
python main.py compare \
    --benchmark data/processed/test.jsonl \
    --ft-model  experiments/finetuned_model
```

This runs all 3 systems (RAG-Only, Fine-Tuning-Only, Hybrid) on your test set
and writes:
- `results/rag_only_metrics.json`
- `results/finetuning_only_metrics.json`
- `results/hybrid_metrics.json`
- `results/comparison_summary.json`
- `results/comparison_summary.md` ← **copy this into your thesis**

---

### 🟢 OPTIONAL — Embedding Model Ablation (for RQ4)
**For extra depth on Research Question 4.**

In `configs/config.yaml`, change:
```yaml
retrieval:
  embedding_model: "BAAI/bge-base-en-v1.5"  # swap from unixcoder-base
```

Re-run `python main.py index` and then `python main.py compare` to see if
a general-purpose embedding model performs differently from a code-specific one.
This gives you a data point for your discussion of what retrieval strategy works best.

---

### 🟢 OPTIONAL — Upgrade Chunker to AST-Based Splitting
**For a stronger methodology section.**

`src/preprocessing/chunker.py` currently splits by line count. A better approach
is to split at function/class boundaries using `tree-sitter`. This means each chunk
is always a complete, syntactically meaningful unit.

Mention the current approach as a limitation in your thesis and note this as future work.

---

## Priority Order at a Glance

| Step | What | Blocker for |
|------|------|-------------|
| 1 | `pip install -r requirements.txt` | Everything |
| 2 | `python data/repobench/download.py` | Steps 4, 5, 6, 7 |
| 3 | `python data/crosscodeeval/download.py` | Steps 4, 5, 6, 7 |
| 4 | `python src/preprocessing/prepare_datasets.py` | Steps 5, 6, 7 |
| 5 | `python main.py index` | RAG-Only and Hybrid inference |
| 6 | `python main.py finetune` | Fine-Tuning-Only and Hybrid inference |
| 7 | `python main.py compare` | Getting your thesis results |
| — | Embedding ablation | Optional depth for RQ4 |
| — | AST chunker upgrade | Optional methodology improvement |

---

## Key Differences: Proposed vs. What's Built (All Improvements)

| Proposed | What's Actually Built | Why It's Better |
|----------|-----------------------|-----------------|
| `BAAI/bge-small-en` embeddings | `microsoft/unixcoder-base` | Code-specific model understands syntax and identifiers |
| Simple chunks, no overlap | Overlapping chunks (`chunk_overlap=32`) | No context lost at chunk boundaries |
| Raw `{"prompt", "target"}` format | `{"input", "output"}` + instruction template | Matches Qwen's training format → better completions |
| LoRA | QLoRA (4-bit NF4) | Lower memory, same quality, fits on 4 GB VRAM |
| `time.time()` latency | `time.perf_counter()` with ms precision | Higher resolution, more accurate benchmarking |
| GPU memory only | GPU + CPU RAM (`psutil`) | Covers CPU-only runs and full resource picture |
| P@K and R@K only | P@K, R@K + MRR + K-sweep [1,3,5,10] | MRR captures ranking quality; sweep supports RQ4 ablation |
| Single comparison | 3-section Markdown table (Quality + Retrieval + Efficiency) | Ready to paste directly into thesis |

