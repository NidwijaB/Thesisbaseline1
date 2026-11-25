# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| rag_only | 0.04 | 0.4132 | 0.2565 | 0.1529 |
| hybrid | 0.14 | 0.644 | 0.4898 | 0.2139 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| rag_only | 0.7642 | 0.62 | 0.3933 | 0.26 | 0.134 | 0.51 | 0.8933 | 0.97 | 1.0 |
| hybrid | 0.7642 | 0.62 | 0.3933 | 0.26 | 0.134 | 0.51 | 0.8933 | 0.97 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| rag_only | 1222.77 | 86960.76 | 88183.52 | 2141.88 | 2410.22 |
| hybrid | 1222.77 | 107621.97 | 108844.74 | 2145.68 | 2433.46 |
