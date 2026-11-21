# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.2562 | 0.0422 | 0.1113 |
| rag_only | 0.0 | 0.2162 | 0.0189 | 0.107 |
| finetuning_only | 0.1 | 0.6114 | 0.4197 | 0.2128 |
| hybrid | 0.16 | 0.6494 | 0.4958 | 0.2127 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| base | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| rag_only | 0.7642 | 0.62 | 0.3933 | 0.26 | 0.134 | 0.51 | 0.8933 | 0.97 | 1.0 |
| finetuning_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hybrid | 0.7642 | 0.62 | 0.3933 | 0.26 | 0.134 | 0.51 | 0.8933 | 0.97 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| base | 0.0 | 94176.59 | 94176.59 | 1669.88 | 2472.18 |
| rag_only | 1295.03 | 115908.31 | 117203.34 | 1841.89 | 2471.04 |
| finetuning_only | 0.0 | 84272.79 | 84272.79 | 1669.88 | 2471.41 |
| hybrid | 1295.03 | 106027.85 | 107322.88 | 1840.65 | 2471.41 |
