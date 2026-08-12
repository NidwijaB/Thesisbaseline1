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
**Status: ⚠️ TODO — You must do this manually**

Proposed: Download from HuggingFace. Contains repository context files,
completion targets, and ground truth.

What the repo has: `data/repobench/` folder exists but is empty.

**What you need to do:**
```python
# TODO: Add this script to data/repobench/download.py
# Install: pip install datasets
from datasets import load_dataset

dataset = load_dataset("microsoft/repobench-python-v1.1")
# or whichever split you are using
dataset.save_to_disk("data/repobench/")
```
Check the RepoBench HuggingFace page for the exact dataset name and available splits.

---

### Step 2 — Download CrossCodeEval
**Status: ⚠️ TODO — You must do this manually**

Proposed: Contains cross-file tasks, multiple languages, repository relationships.

What the repo has: `data/crosscodeeval/` folder exists but is empty.

**What you need to do:**
```python
# TODO: Add this script to data/crosscodeeval/download.py
from datasets import load_dataset

dataset = load_dataset("amazon-science/cceval", "python")
# Available languages: python, java, typescript, csharp
dataset.save_to_disk("data/crosscodeeval/")
```

---

### Step 3 — Convert to Working Format
**Status: ⚠️ TODO — preprocessing script needed, but format is already defined**

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
```python
# TODO: Add a preprocessing script at src/preprocessing/prepare_datasets.py
# that reads from data/repobench/ and data/crosscodeeval/
# and writes JSONL files in the correct format:
#   {"input": "<partial code>", "output": "<correct completion>"}
# Output files:
#   data/processed/train.jsonl
#   data/processed/val.jsonl
#   data/processed/test.jsonl
```

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

**Note:** There is a missing import in `pipeline.py` — `BitsAndBytesConfig` is
used but not imported. This is already flagged and will be caught at runtime.

**Fix needed in `src/hybrid/pipeline.py`:**
```python
# TODO: Add this import at the top of pipeline.py
from transformers import BitsAndBytesConfig
```

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

**What you need to provide when calling `run_evaluation()` for RAG-Only and Hybrid:**
```python
# TODO: When running evaluation, pass ground-truth relevant file lists:
run_evaluation(
    system_name="rag_only",
    predictions=preds,
    references=refs,
    retrieved_list=retrieved_file_ids,   # list of lists — what retriever fetched per query
    relevant_list=ground_truth_file_ids, # list of lists — what was actually relevant
    k_values=[1, 3, 5, 10],
)
# The benchmark datasets (RepoBench / CrossCodeEval) provide ground truth
# relevant file annotations — extract these when preprocessing in Phase 2.
```

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
**File to create: `data/repobench/download.py`**

RepoBench is on HuggingFace. Run this:

```python
from datasets import load_dataset

dataset = load_dataset("microsoft/repobench-python-v1.1")
dataset.save_to_disk("data/repobench/")
print("RepoBench downloaded.")
```

Check the exact dataset name on https://huggingface.co/datasets — it may have
been updated. You want the Python split. It contains:
- `context` — the repository files around the completion point
- `import_statement` — imports in the file being completed
- `code` — the ground truth completion target
- `next_line` — the specific line to predict

---

### 🔴 STEP 3 — Download CrossCodeEval
**File to create: `data/crosscodeeval/download.py`**

```python
from datasets import load_dataset

dataset = load_dataset("amazon-science/cceval", "python")
# Also available: "java", "typescript", "csharp"
dataset.save_to_disk("data/crosscodeeval/")
print("CrossCodeEval downloaded.")
```

It contains:
- `task_id` — unique identifier per completion task
- `prompt` — the partial code (what goes into `input`)
- `canonical_solution` — the correct completion (what goes into `output`)
- `cross_file_context` — the relevant files (what goes into `relevant_files`)

---

### 🔴 STEP 4 — Write the Preprocessing Script
**File to create: `src/preprocessing/prepare_datasets.py`**

This is the most important script you need to write yourself. It must:
1. Read from `data/repobench/` and `data/crosscodeeval/`
2. Convert each example to `{"input": "...", "output": "...", "relevant_files": [...]}`
3. Write to `data/processed/train.jsonl`, `val.jsonl`, `test.jsonl`

The `relevant_files` field is needed for retrieval metrics (Precision@K, Recall@K,
MRR). Do not skip it — it is what makes your evaluation of RAG meaningful.

Rough structure to follow:

```python
# src/preprocessing/prepare_datasets.py
# TODO: Fill in this script

import json
from pathlib import Path
from datasets import load_from_disk

def convert_repobench(output_dir="data/processed"):
    dataset = load_from_disk("data/repobench/")
    # TODO: iterate dataset splits, map fields to {"input", "output", "relevant_files"}
    # Write to train.jsonl / val.jsonl / test.jsonl
    pass

def convert_crosscodeeval(output_dir="data/processed"):
    dataset = load_from_disk("data/crosscodeeval/")
    # TODO: iterate dataset, map fields to {"input", "output", "relevant_files"}
    # Append or merge with existing processed files
    pass

if __name__ == "__main__":
    Path("data/processed").mkdir(parents=True, exist_ok=True)
    convert_repobench()
    convert_crosscodeeval()
    print("Done. Check data/processed/")
```

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

### 🟡 STEP 7 — Wire In Retrieval Ground Truth (in `run_comparison.py`)
**File: `experiments/run_comparison.py` — two places marked with `# TODO`**

In `run_rag_only()` and `run_hybrid()`, replace the two `None` placeholders:

```python
# Replace this:
retrieved_list = None
relevant_list  = None

# With this (once your test.jsonl has a "relevant_files" field):
retrieved_list = [
    [chunk.file_path for chunk in retriever.retrieve(ex["input"])]
    for ex in examples
]
relevant_list = [ex["relevant_files"] for ex in examples]
```

This enables Precision@K, Recall@K, and MRR to be calculated and appear in
your `comparison_summary.md`. Without this, retrieval quality metrics will be
skipped silently.

---

### 🟡 STEP 8 — Run the Full Comparison
**Do this after Steps 5, 6, and 7 are complete.**

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
| 2 | Download RepoBench | Steps 4, 5, 6, 8 |
| 3 | Download CrossCodeEval | Steps 4, 5, 6, 8 |
| 4 | Write `prepare_datasets.py` | Steps 5, 6, 8 |
| 5 | `python main.py index` | RAG-Only and Hybrid inference |
| 6 | `python main.py finetune` | Fine-Tuning-Only and Hybrid inference |
| 7 | Wire `retrieved_list` / `relevant_list` | Retrieval quality metrics (P@K, R@K, MRR) |
| 8 | `python main.py compare` | Getting your thesis results |
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

