# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0 | 0.0 | 0.0 | n/a |
| rag_only | 1.0 | 1.0 | 1.0 | n/a |
| finetuning_only | 1.0 | 1.0 | 1.0 | n/a |
| hybrid | 0.0 | 0.9804 | 0.9908 | n/a |

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
| base | - | - | - | - | - |
| rag_only | - | - | - | - | - |
| finetuning_only | - | - | - | - | - |
| hybrid | - | - | - | - | - |
