# Main reference paper vs this thesis

Reference: Wang, C., Yang, Z., Gao, S., Gao, C., Peng, T., Huang, H., Deng, Y., Lyu, M. (2025).
*RAG or Fine-tuning? A Comparative Study on LCMs-based Code Completion in Industry.* FSE Companion '25.
arXiv:2505.15179.

Source of every statement about the paper below: the paper's own text (read in full from the arXiv
PDF). Page and table references use the arXiv v1 layout. Statements about this thesis come from
`docs/things_to_do_first` and `docs/progress_log.md`. Anything marked [CHECK] I could not confirm.

## 1. What the paper did, in plain language

They asked: for a company's private code, is it better to (a) look up similar code at question time
(RAG) or (b) retrain the model on the company's code (fine-tuning), and does doing both help?

- **Data:** Tencent WXG's backend C++ code. 163,746 files after filtering. 120,000 of them form BOTH the
  retrieval database and the fine-tuning data; 23,746 are for validation; 20,000 other files were used to
  build the test set of 50,000 next-line instances (each input = 20 consecutive lines, target = the next line).
- **Models (six):** Qwen2.5-Coder 0.5B, 1.5B, 3B, 7B and DeepSeek-Coder 1.3B, 6.7B.
- **RAG:** the retrieval database is 914,667 function- and class-level pieces (split with Tree-Sitter).
  Similarity-based retrieval with six retrievers (Random, BM25, CodeBERT, UniXcoder, CodeT5, CoCoSoDa),
  top-5 snippets prepended to the prompt; plus dependency-based retrieval (function-call lookup).
- **Fine-tuning:** full fine-tuning (not LoRA) on file text as plain next-token prediction; learning rate 5e-6,
  batch 32, sequence length 4,096, BF16, on 8 x A100 80 GB GPUs.
- **Metrics:** exact match (EM), edit similarity (ES), BLEU. Efficiency: training hours and GPU memory,
  retrieval latency, throughput. No retrieval-quality metrics (no P@k, R@k or MRR).
- **Research questions:** RQ1 effectiveness of each; RQ2 combining them; RQ3 efficiency; RQ4 sensitivity
  (top-k and codebase size). Plus a forgetting check (HumanEval, MBPP, CRUXEval, CodeXGLUE).

## 2. Their findings (with their numbers)

1. Base models struggle on the private code: best base model (Qwen2.5-Coder-7B) gets about 28% EM, 44% BLEU.
2. Both help. RAG reaches a higher ceiling than fine-tuning: BM25 gave the best accuracy; CodeBERT
   embeddings were no better than no retrieval at all (EM +2.5% average); dependency-based RAG gave only +8.9% EM.
   Fine-tuning gave average relative gains of 78.3% EM, 21.3% ES, 44.6% BLEU.
3. Combining them is better than either: average gains of 7.79% EM, 5.27% ES, 7.91% BLEU over the better single
   method; fine-tuned models use retrieved context better.
4. Efficiency: fine-tuning is expensive up front (3.5 to 23.2 hours and 18.3 to 74.8 GB for Qwen 0.5B to 7B;
   6.8 and 41.4 hours for DeepSeek 1.3B and 6.7B) but adds no runtime cost. RAG is cheap to prepare (BM25 index
   in 2 minutes) but adds runtime cost: BM25 retrieval 10.8 ms vs 49 to 116 ms for neural retrievers, and each
   retrieved snippet adds about 500 input tokens, reducing throughput.
5. Scale: both improve with more code, but fine-tuning flattens beyond about 90,000 files (+0.35 points EM from
   90K to 120K) while RAG keeps improving.
6. Forgetting: after fine-tuning, average HumanEval pass@1 fell by 24.1% and MBPP by 11.7% (relative); code
   reasoning and translation changed much less.
7. More retrieved snippets (top-k up to 5) helped both base and fine-tuned models, with a smaller marginal
   benefit for fine-tuned ones.

### Numbers for the model this thesis uses (Qwen2.5-Coder-1.5B), their Table 3, top-5 retrieved snippets
| Method | EM | Edit sim | BLEU |
|---|---|---|---|
| Base (no adaptation) | 24.48 | 60.78 | 41.47 |
| RAG, random snippets | 23.72 | 60.06 | 41.03 |
| RAG, BM25 | 55.81 | 77.26 | 68.35 |
| RAG, CodeBERT | 23.79 | 60.21 | 41.05 |
| RAG, UniXcoder | 41.47 | 70.08 | 55.77 |
| RAG, CodeT5 | 42.38 | 70.49 | 56.75 |
| RAG, CoCoSoDa | 49.35 | 74.56 | 62.61 |
| RAG, dependency-based | 27.05 | 61.62 | 44.55 |
| Fine-tuning only | 44.63 | 74.12 | 60.50 |

Combination results (their Table 4) are averages over all six models, not 1.5B alone:
| Method (avg of 6 models) | EM | ES | BLEU |
|---|---|---|---|
| Base + RAG-BM25 | 53.76 | 74.42 | 65.57 |
| Fine-tuned + RAG-BM25 | 57.43 | 76.90 | 69.78 |
| Base + RAG-UniXcoder | 41.64 | 70.43 | 56.21 |
| Fine-tuned + RAG-UniXcoder | 52.08 | 77.05 | 66.45 |

[CHECK] The per-model columns above were read from a two-column PDF; row/column alignment was cross-checked
(values rise with model size; the 7B base EM matches the paper's "about 28%"), but confirm against the PDF
before quoting any single cell.

## 3. Side by side

| Aspect | Wang et al. (2025) | This thesis |
|---|---|---|
| Code | One company's private C++ (Tencent WXG) | Public Python benchmarks (CrossCodeEval, RepoBench) |
| Scale | 163,746 files; 120,000 for retrieval and fine-tuning; 50,000 test instances | CrossCodeEval: 618 BASE files, 543 TEST examples; RepoBench: 12,649 BASE files, about 12,000 TEST examples |
| Unit of "a repository" | One huge codebase | Hundreds of small repositories, one index and one split each |
| Models | Six, 0.5B to 7B, two families | One: Qwen2.5-Coder-1.5B |
| Fine-tuning | Full fine-tuning, 8 x A100 80 GB | QLoRA (4-bit), one T4 16 GB |
| Fine-tuning data | Whole files, plain next-token prediction | Cut points inside lines (prefix to rest of line / next line), BASE files only |
| RAG units | Function and class level (Tree-Sitter) | 256-line chunks with 32-line overlap (RepoBench: snippet fragments) |
| Retrievers | Random, BM25, CodeBERT, UniXcoder, CodeT5, CoCoSoDa, dependency-based | UniXcoder (dense) and BM25 |
| Test leakage control | Test files are a separate file set; no per-example assertions reported | File-level BASE/NEW/TEST split per repository and automated leakage assertions |
| Completion metrics | EM, ES, BLEU | EM, ES, identifier accuracy, CodeBLEU |
| Retrieval metrics | None (accuracy only) | P@k, R@k, MRR, hit vs miss |
| Efficiency | Training hours, GPU memory, retrieval latency, throughput | Latency and memory per system, gain per added latency and per added GB |
| Forgetting | HumanEval, MBPP, CRUXEval, CodeXGLUE | Small HumanEval check before and after |
| Staleness (new files) | Not studied | Staleness test with NEW files in the index only |
| Codebase-size effect | 30K, 60K, 90K, 120K files | Low-data regime (few files per repository); size effect not varied |
| Conclusion format | Qualitative guidance | Numeric decision rules with thresholds |

## 4. Where this thesis expects to match or differ (predictions, written before results)

| Their finding | Expected here | Reason |
|---|---|---|
| RAG beats fine-tuning alone | Match, with caution | Same direction expected under H1. Small pools (3 to about 10 chunks per repository) limit what retrieval can add (H4 applies to both) |
| Combination beats either alone | Match, smaller gain | H1; H2 says the gain shrinks when retrieval is already good |
| BM25 beats dense retrievers | Test it, do not assume | Our chunks are 256 lines, theirs are functions. UniXcoder here truncates about half of each long chunk, which may hurt dense retrieval more than BM25 |
| Dense CodeBERT useless | Not applicable | We do not test CodeBERT |
| Fine-tuning costs hours of A100 time | Differ in size | QLoRA on 1.5B with about 10,000 short examples is much cheaper, but adapters learn less |
| Fine-tuning plateaus with more data, RAG keeps scaling | Cannot test directly | Our data is small. H4: with few files, fine-tuning adds little relative to RAG |
| Fine-tuning causes forgetting | Test it | LoRA with a low rank may forget less than full fine-tuning. Report before and after |
| Each snippet adds about 500 tokens, slowing inference | Match | We also measure latency and memory per system |
| New code is handled by RAG but not by fine-tuning | Our own extension (H3) | They did not run a staleness test; it is a stated difference |

## 5. How to compare fairly (important for the defense)

- Do NOT plot your numbers on the same axis as theirs as if equal. Different language, scale, models, data
  and metrics. Compare direction ("they found RAG above fine-tuning; we found ...") and ranking of methods.
- One reference point is closer than the rest: Qwen2.5-Coder-1.5B, next-line completion, EM and ES. Their
  1.5B base EM is 24.48. Your base numbers on CrossCodeEval will come from a different task (rest of line after
  a "."), so even this is only indicative.
- Their absolute EM values are high partly because retrieved code comes from the same codebase and the test
  lines are near neighbors of retrieved code. Your pools are far smaller and retrieval often misses (only
  53.8% of CrossCodeEval TEST examples have any relevant file in the pool), so expect much smaller RAG gains.

## 6. Corrections to your plan and notes

- Plan Section 7 says their setting is "about 120,000 files". More precisely: 163,746 files in total, of which
  120,000 are the retrieval and fine-tuning corpus. Suggest changing the wording.
- Plan Section 7 says "0.5B to 7B models": correct (Qwen2.5-Coder 0.5B to 7B plus DeepSeek-Coder 1.3B and 6.7B).
- Plan Section 7 says "full fine-tuning of larger models": correct.
- "BM25 beat dense embedders (UniXcoder, CodeT5)": correct. The paper also includes CoCoSoDa, which was the
  best dense retriever (EM 49.35 vs BM25 55.81 on the 1.5B model).
- The plan's metric list is wider than theirs (they report no P@k, R@k, MRR and no identifier accuracy).
  This is a genuine difference to put in the research gap table.
- They report generation as greedy decoding with up to 512 new tokens; this thesis cuts predictions to the first
  line. Say so when comparing EM.

## 7. Likely committee questions this answers

- "How is your work different from the main paper?" Section 3 table.
- "Do your results agree with theirs?" Section 4 table (fill in after the runs).
- "Why not simply repeat their study?" Their data is proprietary C++ and their compute is 8 x A100; this thesis
  asks the same question for public Python code and a single 16 GB GPU, and adds the staleness test and
  retrieval-quality analysis.
