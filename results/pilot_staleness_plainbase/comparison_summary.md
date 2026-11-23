# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.04 | 0.4935 | 0.2979 | 0.2367 |
| rag_only | 0.0 | 0.4033 | 0.2132 | 0.1494 |
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
| base | 0.0 | 78532.75 | 78532.75 | 2008.93 | 2423.68 |
| rag_only | 1392.7 | 86732.7 | 88125.4 | 2142.45 | 2470.36 |
| finetuning_only | 0.0 | 98883.81 | 98883.81 | 2009.11 | 2470.81 |
| hybrid | 1392.7 | 118302.85 | 119695.54 | 2146.1 | 2470.83 |
