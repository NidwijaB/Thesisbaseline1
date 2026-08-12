# Comparative Study of Fine-Tuning, Retrieval-Augmented Generation, and Hybrid Models for Code Completion in Enterprise Repositories

A research framework implementing and evaluating three approaches to repository-level code completion:

| # | System | Description |
|---|--------|-------------|
| 1 | **RAG-Only** | Retrieval context injected into a **frozen** code LLM |
| 2 | **Fine-Tuning-Only** | Project-adapted model via LoRA/QLoRA, **no retrieval** |
| 3 | **Hybrid** *(proposed)* | Retrieved context fed into a **fine-tuned** model |

The study answers four research questions:

- **RQ1** — Does repository retrieval improve over standalone fine-tuning?
- **RQ2** — Does fine-tuning improve the usefulness of retrieved context?
- **RQ3** — Does the hybrid approach outperform both individual baselines?
- **RQ4** — What retrieval strategy best supports enterprise code completion?

---

## Quick Start

```bash
pip install -r requirements.txt

# 1. Index a repository
python main.py index --repo-root path/to/repo --repo-id my_repo

# 2. Fine-tune (needs data/processed/train.jsonl)
python main.py finetune

# 3. Run the full comparative study (all three systems, side-by-side report)
python main.py compare \
    --benchmark data/processed/test.jsonl \
    --ft-model  experiments/finetuned_model
```

Results are written to `results/`:
- `rag_only_metrics.json`
- `finetuning_only_metrics.json`
- `hybrid_metrics.json`
- `comparison_summary.json`
- **`comparison_summary.md`** ← copy into your thesis

---

## Project Structure

```
project-root/
├── configs/config.yaml            ← All hyperparameters & system toggles
├── data/
│   ├── repobench/                 ← (add RepoBench dataset here)
│   ├── crosscodeeval/             ← (add CrossCodeEval dataset here)
│   ├── processed/                 ← train.jsonl / val.jsonl / test.jsonl
│   └── embeddings/                ← FAISS index files
├── src/
│   ├── preprocessing/chunker.py  ← Line/AST-based code chunking
│   ├── retrieval/
│   │   ├── embedder.py            ← Code embedding (UniXCoder / BGE)
│   │   ├── vector_store.py        ← FAISS vector store
│   │   └── retriever.py           ← Query → context string
│   ├── finetuning/
│   │   ├── dataset.py             ← JSONL → HuggingFace Dataset
│   │   └── trainer.py             ← LoRA / QLoRA fine-tuning
│   ├── hybrid/pipeline.py         ← Hybrid inference pipeline
│   ├── evaluation/
│   │   ├── metrics.py             ← EM, Edit Sim, ID Accuracy, CodeBLEU, P@K, R@K
│   │   ├── latency.py             ← Retrieval / inference / GPU memory timing
│   │   └── evaluator.py           ← Per-system eval + comparison table generator
│   └── utils/
│       ├── config.py
│       └── logger.py
├── experiments/
│   ├── run_comparison.py          ← Main orchestration: runs all 3 systems
│   └── finetuned_model/           ← Saved model checkpoints (after training)
├── results/                       ← JSON + Markdown comparison outputs
├── tests/test_metrics.py
├── docs/references.md             ← Full bibliography
├── requirements.txt
└── main.py                        ← CLI entry point
```

---

## Metrics

### Code Completion Quality
| Metric | Description |
|--------|-------------|
| Exact Match (EM) | Prediction == Ground Truth |
| Edit Similarity | Levenshtein ratio |
| Identifier Accuracy | Correct function/class/variable names |
| CodeBLEU | N-gram + AST + data-flow similarity |

### Retrieval Quality
| Metric | Description |
|--------|-------------|
| Precision@K | Fraction of retrieved files that are relevant |
| Recall@K | Fraction of relevant files that were retrieved |

### Efficiency
| Metric | Description |
|--------|-------------|
| Retrieval latency (ms) | Time to retrieve context |
| Inference latency (ms) | Time to generate completion |
| Total latency (ms) | End-to-end completion time |
| Peak GPU memory (MB) | Maximum VRAM used |

---

## Configuration

All settings live in `configs/config.yaml`. Key knobs:

| Setting | Default | Notes |
|---------|---------|-------|
| `retrieval.embedding_model` | `microsoft/unixcoder-base` | Also try `BAAI/bge-base-en-v1.5` |
| `retrieval.top_k` | `5` | Ablation range in `top_k_values` |
| `finetuning.base_model` | `Qwen/Qwen2.5-Coder-7B` | Also try `deepseek-ai/deepseek-coder-6.7b-base` |
| `finetuning.method` | `lora` | `lora` \| `qlora` \| `full` |
| `systems.*.enabled` | `true` | Toggle individual systems on/off |

---

## Datasets

| Dataset | Purpose |
|---------|---------|
| **RepoBench** | Complete repositories, retrieval benchmarks, multi-file completion |
| **CrossCodeEval** | Cross-file dependencies, multilingual, completion targets |

Place datasets in `data/repobench/` and `data/crosscodeeval/` respectively.

---

## References

See [`docs/references.md`](docs/references.md) for the full bibliography.
Key papers: RepoBench · CrossCodeEval · RepoCoder · RAFT · LoRA · QLoRA · DeepSeek-Coder · Qwen2.5-Coder · StarCoder2.
