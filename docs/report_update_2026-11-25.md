# Report update: everything done on 2026-11-25 (for pasting into Claude / the report)

Self-contained summary of today's work only, with verified numbers (source: `docs/progress_log.md` Entries 43 to 45, `results/additional_results/`). Use it to update the
progress report after the supervisor's review. Pilot numbers from earlier days are not repeated except where needed for contrast.

## 1. Why this work was done
The supervisor reviewed the progress report and asked for: (1) a full-scale evaluation instead of pilot size, (2) the RAG formatting problem fixed, (3) clearer implementation and
reproducibility details, (4) a clearer account of the adapter setup and experimental fairness.

## 2. What was done today (no GPU, then two Colab T4 sessions)
| Request | What was done | Result |
|---|---|---|
| (3) reproducibility | `docs/reproducibility.md`: configuration, adapter v2 settings, training-state summary, software versions, commits, run commands | written; Colab environment recorded for the first time |
| (4) adapter and fairness | Adapter facts checked from the data; fairness section written | see section 3 |
| (2) RAG fix | B1: four prompt/decoding settings tested for RAG and hybrid on the 50 pilot and 68 staleness-test examples | section 4 |
| (1) full-scale evaluation | B2: all 543 CrossCodeEval TEST examples, four systems, main and staleness views, dense top-5; BM25 main view | section 5 |

## 3. Setup facts (reproducibility and fairness)
- **Adapter v2 is one global adapter:** trained once on the pooled BASE-file corpus of all 206 repositories (no per-repository adapters). Training examples per repository: **minimum 10, median 39, maximum 180**
  (mean 45.5, total 9,378); validation per repository min 1, median 5, max 20 (total 1,059).
- **How the 50 pilot examples were drawn:** from the **292** TEST examples that have a relevant file in the BASE pool, not from all 543 (seed 42; verified: all 50 are TEST examples, in 40 repositories).
  So the pilot favoured retrieval; the full run uses all 543 (of which 292 in the main view and 327 in the staleness view have a relevant file in the pool).
- **QLoRA settings:** Qwen2.5-Coder-1.5B base; 4-bit NF4 with double quantisation, fp16 compute; LoRA r=8, alpha=16, dropout 0.05, target modules q_proj and v_proj (1,089,536 trainable parameters, 0.0705%);
  learning rate 2e-4 with linear decay; effective batch 16 (1 x 16 accumulation); 3 epochs, 1,761 steps; maximum length 512 tokens; loss on answer tokens and end token only; Colab T4, 3 h 29 min, about 8.7 GB.
  Training loss about 0.78 / 0.67 / 0.62 per epoch; validation loss 0.680 / 0.677 / 0.684 (flat; not file-held-out); base-model validation loss 2.735 vs adapter 0.689.
- **Environment recorded on 2026-11-25:** Python 3.13.16, Tesla T4 (15,360 MiB), CUDA 13.0, torch 2.14.1+cu130, transformers 5.15.0, peft 0.20.0, accelerate 1.14.0, bitsandbytes 0.50.2, datasets 5.0.1,
  sentence-transformers 5.7.0, faiss-cpu 1.15.0, rank-bm25 0.2.2, codebleu 0.8.0; code commit `bd097937de23412fae67d5f0886b17643fbf7a12`. The environments of earlier runs (training, pilots) were **not recorded**
  (stated as a limitation); local analysis uses Python 3.11.9 and torch 2.13.0 with the same pinned libraries.
- **Fairness:** same base model, same 4-bit loading, greedy decoding, 128 new tokens maximum, answer cut to the first line, same metrics and same examples for all systems. Base and RAG use a plain code-continuation prompt; fine-tuned and hybrid
  use the training prompt format they were trained on (each model gets the format it works with; the effect of the choice was measured earlier: +0.257 edit similarity for the base). The adapter was trained on BASE files of the same repositories that
  are tested on (different files; TEST files never in the training corpus, leakage assertions pass); the retrieval pool holds the same BASE files, so both channels carry the same repository information. One seed, one adapter.

## 4. B1: the RAG formatting fix (pilot n=50 and staleness test n=68)
Problem: the frozen RAG system wrote the literal text `<|fim_suffix|>` as its answer (6 of 50; 18 of 68) or an empty line (5 of 50), so 22% of pilot answers were unusable.
Settings tested for RAG and hybrid: S0 current; S1 `--suppress-fim` (forbid fill-in-the-middle tokens while generating); S2 `--rag-format qwen_repo` (retrieved files in Qwen2.5-Coder's repository format); S3 both. S0 reproduced the earlier run exactly (RAG 0.3872, hybrid 0.644).

| Set | Setting | RAG edit sim. | empty answers | fill-in-the-middle answers | under 5 characters | RAG edit sim. minus S0 [95% CI] |
|---|---|---|---|---|---|---|
| pilot n=50 | S0 current | 0.387 | 5 | 6 | 9 | - |
| | S1 no-FIM | 0.413 | 5 | 0 | 13 | +0.026 [-0.006, 0.071] |
| | S2 Qwen repo format | 0.434 | 7 | 0 | 10 | +0.047 [-0.007, 0.106] |
| | S3 both | 0.434 | 7 | 0 | 10 | same as S2 |
| staleness test n=68 | S0 | 0.350 | 1 | 18 | 10 | - |
| | S1 | 0.423 | 4 | 0 | 16 | +0.072 [0.020, 0.127] |
| | S2 | 0.384 | 14 | 0 | 20 | +0.034 [-0.029, 0.102] |
| | S3 | 0.384 | 14 | 0 | 20 | same as S2 |

- The hybrid's answers were identical in all four settings in every example, so the settings only affect the RAG row.
- **Chosen setting: S1 (`--suppress-fim`)**, by a rule fixed before looking (fewest empty plus fill-in-the-middle answers, then edit similarity, hybrid not worse).
- **No setting solves the problem:** even in S1, 13 of 50 and 16 of 68 RAG answers are empty or under 5 characters (for example `\` or a cut-off word). The remaining failure is a limitation of the frozen model with this prompt format, not evidence about retrieval.
- Honest statement for the report: the fix removes the fill-in-the-middle failure but not the underlying weakness; a better frozen-RAG prompt (few-shot examples, proper stopping) is future work.

## 5. B2: full-scale evaluation, CrossCodeEval TEST, n=543 (dense UniXcoder retrieval, top-5 chunks; RAG and hybrid with `--suppress-fim`)
### 5.1 Completion quality (main view)
| System | Exact match [95% CI] | Edit similarity [95% CI] | Identifier accuracy | CodeBLEU | Time per example | Peak GPU memory |
|---|---|---|---|---|---|---|
| base | 0.018 [0.007, 0.030] | 0.470 [0.450, 0.490] | 0.287 | 0.191 | 1.58 s | 2,480 MB |
| RAG (A) | 0.024 [0.011, 0.039] | 0.442 [0.418, 0.465] | 0.275 | 0.184 | 1.77 s | 2,557 MB |
| fine-tuned (B) | 0.068 [0.048, 0.090] | 0.599 [0.578, 0.617] | 0.426 | 0.235 | 1.79 s | 2,481 MB |
| hybrid (C) | 0.111 [0.085, 0.136] | 0.628 [0.607, 0.649] | 0.479 | 0.300 | 2.03 s | 2,561 MB |

Staleness view (new files added to the retrieval index only): RAG edit similarity 0.444 (exact match 0.031), hybrid 0.636 (exact match 0.118, identifier accuracy 0.495, CodeBLEU 0.313); base and fine-tuned are identical in both views (no retrieval).
Retrieval (292 examples with a relevant file in the main pool): MRR 0.770, recall@1 0.487, recall@3 0.921, recall@5 0.987. Staleness view (327 examples): MRR 0.720, recall@3 0.843. Retrieval itself costs about 20 ms per example; the cost of RAG is mostly the longer prompt (about 2,100 vs 430 tokens).

### 5.2 Paired differences in edit similarity (95% bootstrap CI, same 543 examples; an interval that excludes 0 is a real difference at this sample)
| Comparison | Main view | Staleness view |
|---|---|---|
| fine-tuned minus base | **+0.129 [0.108, 0.150]** | same (no retrieval) |
| RAG minus base | **-0.028 [-0.050, -0.007]** | **-0.026 [-0.048, -0.005]** |
| hybrid minus fine-tuned | **+0.029 [0.014, 0.044]** | **+0.037 [0.021, 0.052]** |
| hybrid minus RAG | **+0.186 [0.161, 0.211]** | **+0.192 [0.166, 0.217]** |
| RAG minus fine-tuned | **-0.157 [-0.182, -0.133]** | **-0.155 [-0.180, -0.130]** |
- **RAG below base is mostly caused by empty answers:** after removing the 26 examples (27 in the staleness view) where the RAG answer is empty, RAG minus base is -0.007 [-0.026, +0.013] (main, n=517) and -0.003 [-0.023, +0.017] (staleness, n=516): no difference. So retrieval in this prompt format neither helps nor harms the frozen model once format failures are excluded.
- **Hybrid versus fine-tuned alone:** a small but real gain (+0.03 edit similarity; exact match 0.111 vs 0.068). At the pilot size (n=50) this difference was not significant.

### 5.3 Staleness test (hypothesis H3: retrieval reaches code that fine-tuning never saw)
- Staleness view minus main view, hybrid: all 543 examples +0.008 [0.001, 0.016]; the 68 examples whose relevant file is a NEW file **+0.055 [0.015, 0.103]**. RAG alone: +0.002 [-0.010, 0.014] (all) and +0.028 [-0.034, 0.092] (the 68): no benefit.
- On those 68, hybrid minus fine-tuned: +0.037 [-0.009, 0.085] in the main view and **+0.091 [0.036, 0.146]** in the staleness view; the fine-tuned model cannot change because it never saw those files.
- These 68 examples and the hybrid answers are the same as in the pilot analysis, so this reproduces rather than independently replicates that result.

### 5.4 Dense versus BM25 retrieval (main view, n=543)
Retrieval: on the 292 examples with a relevant file, MRR BM25 0.884 vs dense 0.770 (difference **+0.114 [0.074, 0.155]**); hit@5 1.000 vs 0.983. Completion: RAG edit similarity -0.002 [-0.016, +0.011], hybrid +0.003 [-0.004, +0.010]: **better retrieval ranking did not change completion.**
(The BM25 staleness-view run was stopped when the free GPU allowance ran low and is not reported.)

### 5.5 Hit versus miss
At top-5 the relevant file is retrieved in almost every case (287 hits and 5 misses in the main view; 314 and 13 in the staleness view), because repository pools are small (3 to about 10 chunks), so a hit-versus-miss comparison has no statistical power.
Grouped instead by the rank of the first relevant file (post hoc; the top-5 chunks were always in the prompt), edit similarity for rank 1 (n=176), ranks 2 to 3 (n=102), rank 4 or lower (n=14): hybrid 0.623 / 0.637 / 0.685; RAG 0.445 / 0.456 / 0.448; fine-tuned 0.588 / 0.604 / 0.579; base 0.452 / 0.455 / 0.470.
No dependence on the rank of the relevant file is visible. A top-k sweep (k = 1 and 3) is needed for a usable hit-versus-miss analysis.

### 5.6 Functional proxies (share of answers, n=543; rough proxies, not correctness tests)
| System (run) | Empty | Parses as Python (after closing open brackets) | All identifiers present in the repository's benchmark files |
|---|---|---|---|
| base | 0.2% | 93.6% | 16.6% |
| RAG, dense | 4.8% | 86.4% | 23.2% |
| RAG, BM25 | 5.5% | 84.7% | 22.8% |
| fine-tuned | 0.0% | 98.5% | 55.2% |
| hybrid, dense | 0.0% | 98.7% | 64.1% (65.6% staleness view) |
The identifier proxy favours the adapter systems, which were trained on the same repositories; "parses" is checked on one line plus the last prompt line. Fill-in-the-middle markers: 0 for RAG (suppressed), 0.4% for base.

## 6. How the results relate to the hypotheses and the reference paper (direction only)
- **H1 (hybrid > RAG-only > fine-tuned-only):** partly supported: hybrid is highest; but fine-tuned-only is above RAG-only (the opposite of Wang et al., where RAG beat fine-tuning), and RAG-only is not above the base model. The RAG row is limited by the frozen model's format failures.
- **H2 (hybrid's gain shrinks when retrieval is good):** not testable yet; BM25 gave much better retrieval but no better completion; a top-k sweep is needed.
- **H3 (fine-tuning degrades on new files; retrieval helps):** supported in mechanism: the hybrid gains +0.055 on files only retrieval can know; fine-tuning alone cannot change. Fine-tuning does not lose anything on those 68 files (0.604).
- **H4 (low data, fine-tuning adds little):** not supported for the fine-tuned model: +0.129 edit similarity over base with about 9,400 training examples; forgetting after fine-tuning was small (HumanEval 66 to 63 of 164, -4.5%, McNemar p = 0.68, earlier result).
- Compared with Wang et al.: same direction for "combination is best", "fine-tuning beats the base", and "retrieval lengthens the prompt and slows inference"; different for "RAG beats fine-tuning" (here RAG alone did not help the frozen model), and far smaller forgetting. Different language, scale, model count and metrics: compare direction only.

## 7. Limitations to state
One fine-tuning run (one seed), one model size (1.5B), one dataset for completion (CrossCodeEval, Python); pools hold only the benchmark's files (3 to about 10 chunks per repository) so top-5 almost always contains the relevant file; the RAG system's prompt format is not optimised (about 5% empty answers; a larger share very short);
validation loss is not file-held-out; the pilot was drawn from the 292 examples with a relevant file (favourable to retrieval) but the full run uses all 543; only 292 (main) or 327 (staleness) of the 543 have a relevant file, so retrieval metrics use those;
the staleness subset is 68 examples from 35 repositories; the BM25 staleness view was not run; Colab environments of earlier runs were not recorded; the identifier and parse proxies are rough.

## 8. Future work / thesis proposal (not done; to be written as such in the report)
1. RepoBench fine-tuning and completion (RepoBench so far only has data splits, indexes and retrieval comparison).
2. Top-k sweep (1, 3, 10) and noisy-context test (`--noise-chunks`), which also give a usable hit-versus-miss split.
3. A better frozen-RAG prompt (few-shot examples or Qwen's repository format with proper stopping) so that the RAG baseline is measured fairly.
4. RAFT-style retraining (fine-tune with retrieved context) and the decision on 2 versus 3 epochs and a longer maximum sequence length.
5. More seeds for fine-tuning, and error bars across training runs.
6. BM25 staleness view; other retrievers; a larger model size.
7. Numeric recommendations for the decision question (thresholds on retrieval quality, cost per accuracy gain), using the full-run costs: fine-tuning 3 h 29 min and 8.7 GB once; per example RAG +0.19 s, hybrid +0.45 s over base.

## 9. Status
Supervisor's requests: (1) full-scale CrossCodeEval evaluation done; (2) RAG fix tested, partially effective; (3) reproducibility file written; (4) adapter setup and fairness stated. Completion estimate (a judgement): Part 1 about 98%, whole thesis about 80%.
