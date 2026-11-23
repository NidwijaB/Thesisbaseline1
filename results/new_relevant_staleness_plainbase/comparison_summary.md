# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0147 | 0.4567 | 0.2934 | 0.1644 |
| rag_only | 0.0294 | 0.3504 | 0.1912 | 0.1877 |
| finetuning_only | 0.0882 | 0.6036 | 0.403 | 0.1619 |
| hybrid | 0.1618 | 0.695 | 0.5508 | 0.4436 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| base | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| rag_only | 0.7157 | 0.5441 | 0.4412 | 0.3176 | 0.1691 | 0.3284 | 0.7721 | 0.935 | 0.9926 |
| finetuning_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hybrid | 0.7157 | 0.5441 | 0.4412 | 0.3176 | 0.1691 | 0.3284 | 0.7721 | 0.935 | 0.9926 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| base | 0.0 | 109334.26 | 109334.26 | 2042.54 | 2479.3 |
| rag_only | 1613.44 | 128729.64 | 130343.08 | 2171.86 | 2481.46 |
| finetuning_only | 0.0 | 120979.96 | 120979.96 | 2043.75 | 2461.39 |
| hybrid | 1613.44 | 154366.44 | 155979.88 | 2172.04 | 2422.09 |
