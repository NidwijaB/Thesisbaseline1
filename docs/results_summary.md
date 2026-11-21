# Results summary (single place for every real result so far)

Last updated 2026-11-19, after Entry 28 of `docs/progress_log.md` (the log has the full context,
caveats and decisions; this file only collects the numbers so they can be pasted into the report and
slides). Raw files are in `results/` (gitignored); regenerate with the commands given.

**Status in one line:** retrieval results exist for both datasets and one fine-tuning run is finished.
A pilot (n=50, main view) now gives completion scores for all four systems (section 5c); no full-set result yet.

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

## 5b. Overall completion (Entry 35, 2026-11-21; 58% in Entry 31, 65% in Entry 34)

About 67% of the project work (64 to 70%; thesis writing not counted; a weighted judgement, not a measurement).
Groundwork done (data, code, indexes, retrieval results, one training run); evaluation runs (28% of the weight)
are about 33% done (pilot and three variants, no full set). Weights and the original completed-versus-remaining table:
`docs/progress_log.md`, Entry 31; the revision: Entry 34.

## 5c. Pilot, main view, n=50 (Entry 33; pilot only, not findings)

Command: `python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit`.
Files: `results/pilot_main/` (on Drive). 50 CrossCodeEval TEST examples, dense retrieval, top-5, T4.

| System | EM | Edit sim. [95% CI] | Identifier acc. | CodeBLEU | Avg ms | Peak GPU MB |
|---|---|---|---|---|---|---|
| base | 0.00 | 0.236 [0.212, 0.262] | 0.018 | 0.068 | 1,798 | 2,009 |
| RAG (A) | 0.00 | 0.226 [0.205, 0.248] | 0.042 | 0.121 | 2,277 | 2,146 |
| fine-tuned (B) | 0.08 | 0.613 [0.549, 0.680] | 0.414 | 0.213 | 1,959 | 2,009 |
| hybrid (C) | 0.14 | 0.644 [0.570, 0.715] | 0.490 | 0.214 | 2,232 | 2,146 |

Caveat: base and RAG scores are suspiciously low (EM 0 of 50), probably a prompt-format effect (the adapter was
trained on this format, the base model was not); check `predictions.jsonl` before comparing. Hybrid vs fine-tuned:
CIs overlap. Retrieval: MRR 0.764, R@3 0.893. CodeBLEU's data-flow part is always 0 for one-line targets.

## 5d. Validation loss and staleness pilot (Entry 34; pilot only, not findings)

Validation loss on 1,059 examples (answer tokens + end token): base 2.735, adapter v2 0.6887 (difference 2.046).
`results/val_loss_base_vs_adapter.json`. Not file-held-out; much of the drop is probably format learning.

Staleness pilot (NEW files in the retrieval index; n=50; `results/pilot_staleness/`):

| System | EM | Edit sim. [95% CI] | Identifier acc. | CodeBLEU |
|---|---|---|---|---|
| base | 0.00 | 0.236 [0.212, 0.262] | 0.018 | 0.068 |
| RAG (A) | 0.00 | 0.213 [0.191, 0.237] | 0.028 | 0.067 |
| fine-tuned (B) | 0.08 | 0.613 [0.549, 0.680] | 0.414 | 0.213 |
| hybrid (C) | 0.16 | 0.657 [0.582, 0.728] | 0.507 | 0.288 |

Retrieval, staleness vs main: MRR 0.750 vs 0.764; R@3 0.783 vs 0.893. Completion barely changes (inside the CIs).
Base and fine-tuned are identical across views (no retrieval, greedy decoding). The pilot cannot test staleness
(H3): its examples have the relevant file in BASE, so NEW files are only distractors; the 68 NEW-relevant examples
are needed.

## 5e. Extra pilot runs: shorter code, BM25, HumanEval (Entry 35; n=50 / n=20, not findings)

Pilot main view, edit similarity (EM in brackets):

| Run | base | RAG | fine-tuned | hybrid |
|---|---|---|---|---|
| default (dense, full code) | 0.236 (0.00) | 0.226 (0.00) | 0.613 (0.08) | 0.644 (0.14) |
| code cut to 480 tokens | 0.256 (0.00) | 0.216 (0.00) | 0.611 (0.10) | 0.649 (0.16) |
| BM25 retrieval | 0.236 (0.00) | 0.224 (0.00) | 0.613 (0.08) | 0.640 (0.12) |

BM25 retrieval: MRR 0.840 vs 0.764 (dense), R@3 0.977 vs 0.893, retrieval time 203 ms vs 1,183 ms for 50. Better
retrieval did not change completion (inside the CIs); neither did shorter code.

HumanEval forgetting check (first 20 problems): base 0/20, fine-tuned 5/20. **Not valid as a forgetting measure:** the
stub is wrapped in the training prompt format, so the base model is penalised by the format. Rerun with the plain stub
on all 164 problems.

Open question before the full run: the base/RAG deficit may be a prompt-format artifact (base EM 0 of 50, HumanEval 0 of
20). See Entry 35.

## 6. Not available yet

EM / edit similarity / identifier accuracy / CodeBLEU for base, RAG, fine-tuned and hybrid; hit-versus-miss
accuracy; staleness effect on completion; forgetting check; noisy-context test; top-k sweep; RepoBench
completion and fine-tuning; latency and memory per system. All need the Colab GPU (pilot first).
