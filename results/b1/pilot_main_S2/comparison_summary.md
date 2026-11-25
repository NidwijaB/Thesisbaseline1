# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| rag_only | 0.04 | 0.4336 | 0.2643 | 0.1494 |
| hybrid | 0.14 | 0.644 | 0.4898 | 0.2139 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| rag_only | 0.7642 | 0.62 | 0.3933 | 0.26 | 0.134 | 0.51 | 0.8933 | 0.97 | 1.0 |
| hybrid | 0.7642 | 0.62 | 0.3933 | 0.26 | 0.134 | 0.51 | 0.8933 | 0.97 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| rag_only | 1241.8 | 87581.11 | 88822.91 | 2130.8 | 2428.0 |
| hybrid | 1241.8 | 108222.33 | 109464.13 | 2147.39 | 2456.29 |
