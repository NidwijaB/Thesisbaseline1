# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.2363 | 0.018 | 0.068 |
| rag_only | 0.0 | 0.226 | 0.0422 | 0.1212 |
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
| base | 0.0 | 89883.44 | 89883.44 | 2009.11 | 2516.96 |
| rag_only | 1182.74 | 112683.66 | 113866.4 | 2146.1 | 2583.34 |
| finetuning_only | 0.0 | 97940.81 | 97940.81 | 2009.11 | 2585.63 |
| hybrid | 1182.74 | 110400.33 | 111583.06 | 2146.1 | 2589.7 |
