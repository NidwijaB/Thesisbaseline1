# Comparative Study Results

## Code Completion Quality

| System | Exact Match | Edit Sim | Identifier Acc | CodeBLEU |
|--------|------------|----------|----------------|----------|
| base | 0.0147 | 0.4567 | 0.2934 | 0.1644 |
| rag_only | 0.0147 | 0.384 | 0.2186 | 0.219 |
| finetuning_only | 0.0882 | 0.6036 | 0.403 | 0.1619 |
| hybrid | 0.0882 | 0.6402 | 0.4775 | 0.3739 |

## Retrieval Quality (RAG-Only & Hybrid)

| System | MRR | P@1 | P@3 | P@5 | P@10 | R@1 | R@3 | R@5 | R@10 |
|--------|-----|-----|-----|-----|------|-----|-----|-----|------|
| base | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| rag_only | 0.8217 | 0.697 | 0.404 | 0.2606 | 0.1333 | 0.5606 | 0.899 | 0.9697 | 1.0 |
| finetuning_only | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A |
| hybrid | 0.8217 | 0.697 | 0.404 | 0.2606 | 0.1333 | 0.5606 | 0.899 | 0.9697 | 1.0 |

## Efficiency

| System | Retrieval (ms) | Inference (ms) | Total (ms) | GPU Mem (MB) | CPU RAM (MB) |
|--------|---------------|----------------|------------|--------------|--------------|
| base | 0.0 | 108634.73 | 108634.73 | 2042.54 | 2516.79 |
| rag_only | 1574.11 | 127336.57 | 128910.69 | 2174.21 | 2557.6 |
| finetuning_only | 0.0 | 121960.4 | 121960.4 | 2043.75 | 2557.97 |
| hybrid | 1574.11 | 152721.65 | 154295.76 | 2175.12 | 2538.3 |
