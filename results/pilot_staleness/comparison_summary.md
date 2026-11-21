# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.2363 | 0.018 | 0.068 |
| rag_only | 0.0 | 0.2131 | 0.0283 | 0.0671 |
| finetuning_only | 0.08 | 0.613 | 0.4142 | 0.213 |
| hybrid | 0.16 | 0.657 | 0.5073 | 0.2883 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| base | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| rag_only | 0.7504 | 0.62 | 0.3667 | 0.264 | 0.144 | 0.4767 | 0.7833 | 0.915 | 1.0 |
| finetuning_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hybrid | 0.7504 | 0.62 | 0.3667 | 0.264 | 0.144 | 0.4767 | 0.7833 | 0.915 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| base | 0.0 | 93002.82 | 93002.82 | 2009.11 | 2477.88 |
| rag_only | 1197.76 | 123058.49 | 124256.25 | 2146.1 | 2548.91 |
| finetuning_only | 0.0 | 97739.69 | 97739.69 | 2009.11 | 2549.38 |
| hybrid | 1197.76 | 115108.95 | 116306.71 | 2146.1 | 2549.4 |
