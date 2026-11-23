# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.04 | 0.4935 | 0.2979 | 0.2367 |
| rag_only | 0.02 | 0.3857 | 0.2168 | 0.1549 |
| finetuning_only | 0.08 | 0.613 | 0.4142 | 0.213 |
| hybrid | 0.12 | 0.6398 | 0.4692 | 0.2093 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| base | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| rag_only | 0.84 | 0.7 | 0.4267 | 0.268 | 0.134 | 0.59 | 0.9767 | 1.0 | 1.0 |
| finetuning_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hybrid | 0.84 | 0.7 | 0.4267 | 0.268 | 0.134 | 0.59 | 0.9767 | 1.0 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| base | 0.0 | 78690.05 | 78690.05 | 1517.8 | 2345.65 |
| rag_only | 206.58 | 92037.12 | 92243.7 | 1667.39 | 2387.64 |
| finetuning_only | 0.0 | 96792.66 | 96792.66 | 1517.96 | 2409.47 |
| hybrid | 206.58 | 111841.86 | 112048.44 | 1667.67 | 2409.47 |
