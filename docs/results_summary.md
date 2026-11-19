# Results summary (single place for every real result so far)

Last updated 2026-11-19, after Entry 28 of `docs/progress_log.md` (the log has the full context,
caveats and decisions; this file only collects the numbers so they can be pasted into the report and
slides). Raw files are in `results/` (gitignored); regenerate with the commands given.

**Status in one line:** retrieval results exist for both datasets and one fine-tuning run is finished.
No completion score (exact match, edit similarity) exists for any system yet; the pilot has not been run.

---

## 1. Retrieval comparison, CrossCodeEval (Entry 20)

Command: `python -m src.retrieval.compare_retrievers` then `python -m src.evaluation.plot_retrieval_comparison`.
Files: `results/retrieval_comparison.json`, `results/figures/retrieval_*.png`, `results/figures/hit_at_k_main.png`.
Dense = UniXcoder; relevance = proxy rule (Entry 4); TEST files retrieved = 0 over 543 TEST examples.

| View (n) | System | hit@1 | hit@3 | MRR (95% CI) |
|---|---|---|---|---|
| main (292) | dense | 0.603 | 0.952 | 0.770 [0.737, 0.804] |
| main (292) | BM25 | 0.784 | 0.990 | 0.884 [0.860, 0.908] |
| main (292) | random | 0.397 | 0.849 | 0.633 [0.596, 0.672] |
| staleness (327) | dense / BM25 / random | 0.532 / 0.771 / 0.355 | 0.896 / 0.963 / 0.728 | 0.720 / 0.870 / 0.572 |
| staleness, relevant file in NEW (68) | dense / BM25 / random | 0.544 / 0.809 / 0.353 | 0.868 / 0.941 / 0.677 | 0.716 / 0.885 / 0.553 |

Paired dense minus BM25, main view: hit@1 -0.182 [-0.250, -0.113]; MRR -0.114 [-0.152, -0.075]. Both
intervals exclude 0: BM25 is better. On the 68 NEW-relevant examples the hit@3 interval includes 0.
Caveat: pools hold 3 to about 10 chunks, so hit@5 and hit@10 are near 1 even for random; read hit@1, MRR and
the gap to random.

## 2. Retrieval comparison, RepoBench sample (Entry 28)

Command: `python -m src.retrieval.compare_retrievers_repobench`. File: `results/repobench_retrieval_comparison.json`.
Sample: 300 TEST examples per setting (seed 42, gold file in the BASE pool; Entry 24). One relevant file per
example. TEST files retrieved = 0. Settings are not pooled.

| Setting, view | Median pool files | dense hit@1 / MRR | BM25 hit@1 / MRR | random hit@1 / MRR |
|---|---|---|---|---|
| cross_file_first, main | 9 | 0.247 / 0.446 | 0.260 / 0.466 | 0.127 / 0.323 |
| cross_file_first, staleness | 12 | 0.223 / 0.409 | 0.240 / 0.431 | 0.097 / 0.283 |
| cross_file_random, main | 11 | 0.290 / 0.484 | 0.337 / 0.535 | 0.110 / 0.319 |
| cross_file_random, staleness | 14 | 0.240 / 0.431 | 0.297 / 0.494 | 0.140 / 0.298 |

Paired dense minus BM25 (MRR, 95% CI): cross_file_first main -0.020 [-0.062, 0.020] (no evidence of a
difference); cross_file_random main -0.051 [-0.086, -0.014] and staleness -0.063 [-0.098, -0.028] (BM25 better).
Reading: both retrievers beat random but by less than on CrossCodeEval; the right file is first in only
22 to 34% of cases; adding NEW files lowers every system. Limitation: the sample has no examples whose gold
file is in NEW, so the staleness view shows NEW files only as distractors.

## 3. Fine-tuning run v2, CrossCodeEval (Entry 18)

QLoRA 4-bit, Qwen2.5-Coder-1.5B, LoRA r=8 (1,089,536 trainable parameters, 0.0705%), 9,378 training and
1,059 validation examples, 3 epochs, 1,761 steps, effective batch 16, Colab T4: 3 h 29 min, about 8.7 GB.
Training loss (answer tokens only) about 0.78 / 0.67 / 0.62 per epoch. Validation loss 0.680 / 0.677 / 0.684
(flat; not file-held-out, so optimistic). Plot: `results/figures/training_loss.png` (two validation points are in
the saved `trainer_state.json`; the third value comes from the training output).
Missing: base-model validation loss for comparison (script `src/finetuning/eval_loss.py` written, needs a GPU).
So there is NO evidence yet that fine-tuning improved anything.

## 4. Data facts used by the results (Entries 3, 7, 8, 10, 11, 13)

- CrossCodeEval: 206 repos kept; files BASE 618 / NEW 100 / TEST 273; TEST examples 543, of which 292 (53.8%)
  have a relevant file in the main pool, 327 (60.2%) in the staleness pool, 68 in NEW. Pilot = 50 examples.
- RepoBench: 1,826 repos kept; files BASE 12,649 / NEW 3,482 / TEST 5,330; TEST examples 6,276 + 6,035;
  evaluation sample 300 per setting (446 repos indexed: main 11,031 and staleness 13,984 fragments).
- Fine-tuning corpora: CrossCodeEval 9,378 + 1,059; RepoBench 10,800 + 1,200 (capped at 12,000, a compute choice).

## 5. Pipeline check, not a result (Entry 22)

Model-free dry run on the 50 pilot examples: no TEST file retrieved; a relevant file is in the top 5 chunks
for 48 of 50 (dense) and 50 of 50 (BM25) in the main view; prompt length median 437 tokens without retrieval
and 2,152 with it (training used 512). These are pipeline facts, not evaluation results.

## 6. Not available yet

EM / edit similarity / identifier accuracy / CodeBLEU for base, RAG, fine-tuned and hybrid; hit-versus-miss
accuracy; staleness effect on completion; forgetting check; noisy-context test; top-k sweep; RepoBench
completion and fine-tuning; latency and memory per system. All need the Colab GPU (pilot first).
