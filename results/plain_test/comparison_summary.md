# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.2551 | 0.1 | 0.0385 |
| rag_only | 0.0 | 0.2274 | 0.0 | 0.0 |
| finetuning_only | 0.2 | 0.5836 | 0.35 | 0.1438 |
| hybrid | 0.2 | 0.6576 | 0.55 | 0.1486 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| base | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| rag_only | 0.6333 | 0.4 | 0.3333 | 0.2 | 0.1 | 0.4 | 1.0 | 1.0 | 1.0 |
| finetuning_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hybrid | 0.6333 | 0.4 | 0.3333 | 0.2 | 0.1 | 0.4 | 1.0 | 1.0 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| base | 0.0 | 11316.53 | 11316.53 | 1697.02 | 2381.82 |
| rag_only | 349.77 | 6805.38 | 7155.15 | 1822.64 | 2531.5 |
| finetuning_only | 0.0 | 9177.38 | 9177.38 | 1698.01 | 2534.01 |
| hybrid | 349.77 | 9381.35 | 9731.12 | 1823.37 | 2537.02 |
