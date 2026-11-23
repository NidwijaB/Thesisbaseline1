# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.04 | 0.4935 | 0.2979 | 0.2367 |
| rag_only | 0.02 | 0.3872 | 0.2165 | 0.1401 |
| finetuning_only | 0.08 | 0.613 | 0.4142 | 0.213 |
| hybrid | 0.14 | 0.644 | 0.4898 | 0.2139 |

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
| base | 0.0 | 80310.75 | 80310.75 | 2008.93 | 2495.5 |
| rag_only | 1170.44 | 84996.85 | 86167.28 | 2142.45 | 2541.44 |
| finetuning_only | 0.0 | 95336.73 | 95336.73 | 2009.11 | 2522.13 |
| hybrid | 1170.44 | 110934.3 | 112104.74 | 2146.1 | 2522.13 |
