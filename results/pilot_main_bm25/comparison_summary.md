# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.2363 | 0.018 | 0.068 |
| rag_only | 0.0 | 0.2241 | 0.0207 | 0.0971 |
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
| base | 0.0 | 92611.66 | 92611.66 | 1517.81 | 2315.9 |
| rag_only | 202.53 | 120168.08 | 120370.61 | 1667.92 | 2387.34 |
| finetuning_only | 0.0 | 97281.1 | 97281.1 | 1517.81 | 2391.61 |
| hybrid | 202.53 | 111412.99 | 111615.52 | 1667.92 | 2391.73 |
