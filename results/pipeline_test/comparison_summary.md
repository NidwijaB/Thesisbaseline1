# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.1556 | 0.1 | 0.0 |
| rag_only | 0.0 | 0.1761 | 0.1 | 0.0 |
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
| base | 0.0 | 18980.2 | 18980.2 | 1698.01 | 2212.19 |
| rag_only | 395.09 | 11465.75 | 11860.84 | 1823.37 | 2379.96 |
| finetuning_only | 0.0 | 7996.59 | 7996.59 | 1698.01 | 2384.34 |
| hybrid | 395.09 | 10358.3 | 10753.4 | 1823.37 | 2387.34 |
