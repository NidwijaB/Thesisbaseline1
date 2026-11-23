# Prompt for the Claude web app: updated progress report + progress presentation

Rewritten 2026-11-21 (after progress-log Entry 35). It is shorter than the earlier version on purpose: the long
facts live in the attached files, and this prompt tells the web app what to build and which numbers and caveats
to use.

## How to use
1. Open a new chat on the Claude web app.
2. Attach the files under "Files to attach".
3. Fill in the three `[YOU FILL IN]` items inside the prompt.
4. Paste everything between `=== PROMPT START ===` and `=== PROMPT END ===`.
5. The prompt asks for the report first and the slides second. Say "go" after each confirmation step.

## Files to attach

Must attach:
1. `docs/Nidwija_081MSCSK010_progress_report.docx`: the ORIGINAL August report (keep its structure, tone, citations).
2. `docs/slides/Midterm_Progress_Update.pptx`: the ORIGINAL September deck (new deck continues its look).
3. `docs/things_to_do_first`: the experiment plan (authoritative for the study design).
4. `docs/progress_log.md`: Entries 1 to 42, every decision, number and caveat. Entry 37 is the plain-language note on how the prompts
   were chosen; Entries 40 to 42 hold the plain-prompt pilot, the paired analysis and the RAG formatting problem.
5. `docs/results_summary.md`: every real result in one place.
6. `docs/reference_paper_comparison.md`: Wang et al. (2025) comparison, and `docs/references.md`.
7. The ready-made charts: `results/figures/pilot_main_vs_staleness.png`, `pilot_prompt_effect.png`, `pilot_staleness_68.png`,
   `pilot_paired_differences.png`, `pilot_cost.png`, `pilot_forgetting.png`, `pilot_numbers.csv` (every plotted number), and the older
   `training_loss.png` and retrieval figures; `docs/example_outputs.md` (six side-by-side example outputs); the result JSON files
   (`results/retrieval_comparison.json`, `results/repobench_retrieval_comparison.json`, `results/pilot_*_plainbase/comparison_summary.json`,
   `results/new_relevant_*_plainbase/comparison_summary.json`, `results/val_loss_base_vs_adapter.json`, `results/forgetting_humaneval_plain.json`).
8. `docs/next_steps_part3.md`: the remaining work (use it for the roadmap and "next steps").

Attach if you have them: the university's report template or formatting rules; supervisor or committee feedback
from the September defense; the original Figure 1 and Figure 3 images.

Do NOT attach: `venv/`, raw datasets, `.env` files, tokens, or anything with credentials. Nothing here has secrets.

=== PROMPT START ===

You are helping me, Nidwija Bhatta (MSc in Computer Systems and Knowledge Engineering, Tribhuvan University,
IOE Pulchowk Campus, student ID 081MSCSK010), prepare two documents for my thesis:

1. An UPDATED PROGRESS REPORT (a revised version of the attached August 2026 report).
2. A PROGRESS PRESENTATION (a follow-up to the attached September 2026 mid-term deck).

Thesis title: "Comparative Study of Fine-Tuning, Retrieval-Augmented Generation, and Hybrid Models for Code
Completion in Enterprise Repositories". Supervisor: Prof. Dr. Subarna Shakya.
Date for this task: [YOU FILL IN]. Submission or presentation date: [YOU FILL IN].
Report length: [YOU FILL IN, or "similar to the original plus about 6 pages"]. Slides: [YOU FILL IN, e.g. 16 to 18].

## 1. Ground rules (read first)

- **Use only the numbers and facts in this prompt and the attached files.** Never invent results, intervals, latency,
  memory or citations. If something is missing, list it as a question for me.
- **Only pilot-level results exist for completion quality** (50 examples, 68 for the staleness test; one model, one run, one seed). Label
  every such number "pilot, n=50" (or "n=68"). The full 543-example evaluation, RepoBench completion and multiple seeds are Part 2.
- **What you MAY say (pilot, with the interval or sample size):** fine-tuned beats the base model (paired edit-similarity difference
  +0.120, 95% interval [0.061, 0.187]); on the staleness test the hybrid improves when the relevant new file is in the index (+0.055
  [0.015, 0.103]) and beats the fine-tuned model there (+0.091 [0.036, 0.146]) while the fine-tuned model cannot change; BM25 retrieves
  better than dense retrieval but completion is the same; the adapter shows no significant forgetting on HumanEval (63 vs 66 of 164,
  McNemar p = 0.68); retrieval prompts cost about 0.1 to 0.3 s and 0.14 GB more per example.
- **What you may NOT say:**
  - that retrieval hurts, or that RAG is worse than the base model, as a finding about retrieval. It was measured (edit similarity 0.387
    vs 0.494) but about 22% of the frozen RAG system's answers were formatting failures (empty, or the literal token `<|fim_suffix|>`), so
    it is a prompt-format problem of the frozen model, being fixed (section 5, caveat 1);
  - that the hybrid generally beats the fine-tuned model: in the 50-example pilot the difference (+0.031 [-0.032, 0.089]) is not significant;
  - that fine-tuning degrades on new files (H3). Fine-tuned does not change on new files; what was shown is that retrieval adds the new file's
    knowledge for the hybrid;
  - anything about hit-versus-miss accuracy (only 0 to 4 retrieval misses per run), RepoBench completion, or results beyond the pilot.
- Hypotheses H1 to H4 were written BEFORE the experiments; label them as hypotheses.
- Audience: examiners who know software but maybe not machine learning. Explain terms in plain words the first
  time (retrieval = looking up relevant code at the moment of the question; fine-tuning = retraining the model on the
  project's own code; leakage = the model seeing the answers it is tested on).
- Keep the August report's citation style and use only references already in it and in `docs/references.md`.
- Be honest about limitations and open problems. They are a strength of the study.
- Say plainly where the design changed since August and why (section 3).

## 2. The study in brief

**Decision question (the objective):** "Given a private repository and a single-GPU budget, which adaptation
strategy should a team choose, and when does the hybrid's extra complexity pay off?" Conclusions must end as numeric
rules with thresholds. **Domain:** developer tooling for companies with private codebases, where privacy rules often
prevent sending code to commercial APIs, so teams self-host small open models on limited GPUs.

**Three systems, same base model (Qwen2.5-Coder-1.5B), same task, same metrics, same repository knowledge:**
- A, RAG-only: frozen model + retrieved code chunks (UniXcoder embeddings + FAISS per repository; BM25 baseline).
- B, fine-tuning-only: QLoRA 4-bit adapter trained on the repository files; no retrieval at answer time.
- C, hybrid: the fine-tuned model plus the same retrieval as A.
A plain "base" model (no retrieval, no adapter) is also run as a reference.

**Data (Python only; two public benchmarks, reported separately, never pooled):**
CrossCodeEval (complete the rest of a line; 2,665 examples, 471 repos) and RepoBench v1.1 (predict the next line; cross-file
settings). Neither has full repo files or a training split, so per-repository knowledge pools are built from the
benchmark data and **split by file** into BASE (retrieval and fine-tuning), NEW (retrieval only; tests staleness) and
TEST (evaluation targets only, in no pool, index or training data). Fixed seed 42; automated leakage checks.

**Prompt design (use for a methodology paragraph and one slide; plain language):** the task is to write the rest of a line cut in
the middle (for example `response = await repository_ratings.` -> `delete_rate(1, session, new_user)`). The fine-tuned model was
trained on an "instruction form" (Instruction: Complete the following code / Input: the code / Response:), so the first pilot gave every
system that form, to keep the prompt identical. The plain base model does not follow the form: for the example above it wrote
`from datetime import datetime`, RAG wrote a sentence, while fine-tuned and hybrid wrote the correct line. Across the 50 pilot
examples 33 base answers were import lines and 8 were sentences. Decision (option a): the frozen systems (base, RAG) now get a plain
continuation prompt (retrieved code as `#` comments, then the code, no form); the adapter systems keep the form they were trained on.
Same task, same retrieved chunks, same decoding and scoring; each model gets the prompt it can follow; the prompts are not byte-identical
(state this as a design choice and limitation). Rejected: few-shot examples (longer prompts, hand-picked examples could bias), and keeping
the form everywhere (leaves base and RAG meaningless). The first pilot's numbers are kept as a documented first attempt, with the
reason they were set aside. Tested without a GPU: automated tests of the prompt text and a dry run over all 50 pilot examples; the
GPU rerun is pending, so there is no evidence yet that the plain prompt fixes base and RAG.

**Hypotheses:** H1 hybrid > RAG-only > fine-tuning-only on cross-file-dependent examples. H2 the hybrid's gain shrinks
when retrieval quality is high. H3 fine-tuning-only degrades most on NEW files and unseen code. H4 (low data) with few
files per repository, fine-tuning adds little relative to RAG (a legitimate finding either way).

**Main reference paper:** Wang et al. (2025, arXiv 2505.15179). One company's C++ (163,746 files; 120,000 form the retrieval
and fine-tuning corpus), six models 0.5B to 7B, full fine-tuning on 8 x A100. They found: RAG with a good retriever
beats fine-tuning alone; the combination is best; BM25 beat dense retrievers; retrieval greatly increases input length;
fine-tuning cost HumanEval pass@1 24.1% on average. This thesis differs: public Python benchmarks, far smaller per-repo
data, 1.5B with QLoRA on one T4, retrieval-quality metrics (P@k, R@k, MRR), hit/miss analysis, staleness test,
per-repository file-level split. Compare direction of effects, never absolute scores. Their Qwen2.5-Coder-1.5B numbers
(EM / edit sim. / BLEU, top-5): base 24.48 / 60.78 / 41.47; RAG BM25 55.81 / 77.26 / 68.35; RAG UniXcoder 41.47 / 70.08 /
55.77; fine-tuning 44.63 / 74.12 / 60.50. See `docs/reference_paper_comparison.md`.

## 3. What changed since the August report and September deck (use as a "Changes and why" section and slide)

| Topic | August report / September deck | Now |
|---|---|---|
| Split | 80/10/10 by repository, both datasets mixed | By FILE inside each repository (BASE / NEW / TEST), datasets separate |
| Fine-tuning data | Prompt + answer of examples | BASE files only, cut points inside lines; never test prompts or answers |
| Leakage control | Repository split only | Automated checks: no TEST path or content in pool, index or training data; validation from BASE only; NEW absent from training |
| Retrieval ground truth | "CrossCodeEval gives relevant files" | CrossCodeEval has no gold label: a proxy rule is used; RepoBench has a gold snippet index |
| Retrieval | Dense UniXcoder + FAISS | Dense + BM25 baseline + top-k sweep |
| Evaluation | Metrics, latency, memory | Same plus hit vs miss, noisy context, staleness test, forgetting check, bootstrap confidence intervals |
| Objective | General comparison | The decision question above, with hypotheses and numeric rules |
| Hybrid import | Report said present | A real missing PEFT import was found and fixed |
| Remaining work | "Mostly execution" | Understated: leakage-safe design, analyses and GPU runs were added |
| Compute | "Available GPU" | Free Colab T4 (16 GB) with Google Drive; no GPU on the main workstation |
Note: CrossCodeEval is a community mirror; file text was rebuilt exactly for all 2,665 examples, but "matches the real
GitHub files" is NOT verified.

## 4. Progress: how much is done (put this table in the report AND on a slide)

The work is split in two parts. **Project Part 1 (this presentation) is the pilot-level study: data and leakage-safe splits, retrieval comparison,
one fine-tuning run, a four-system pilot on 50 examples with the fixed prompts, and the basic evaluation. Part 2 (thesis wrap-up) is the full
evaluation and the heavier work.**

**Part 1: about 96% done (range 94 to 98%; the presentation and report writing are not counted). This is a weighted judgement of effort, not a
measurement; say so.** The whole thesis project is about 74% done (August estimate: about 30 to 35%).

| Part 1 workstream | Weight | Done | Status |
|---|---|---|---|
| Plan, literature analysis, hypotheses | 8% | 100% | Finished |
| CrossCodeEval data (split, leakage checks, training corpus, pilot sample) | 15% | 100% | Finished |
| RepoBench data (split, corpus, 300-per-setting sample; used for retrieval in Part 1) | 10% | 100% | Finished |
| Pipeline code (prompts, training, evaluation, diagnostics, Colab setup; 39 automated tests) | 15% | 100% | Runs end to end on a T4 |
| Retrieval (indexes for both datasets; dense vs BM25 vs random) | 12% | 95% | Done |
| Fine-tuning (CrossCodeEval adapter, base-vs-adapter loss) | 10% | 100% | Done |
| Four-system pilot with the fixed prompts (main and staleness views, BM25, 68-example staleness test, HumanEval) | 20% | 95% | Done; a short follow-up run fixes the RAG formatting problem |
| Basic evaluation and comparison with the literature | 10% | 85% | Analysis, charts and examples done; final RAG numbers pending |

**Part 2 (planned, thesis wrap-up):** full 543-example CrossCodeEval comparison (both views) with hit-versus-miss analysis; RepoBench fine-tuning
and completion; noisy-context and top-k sweeps; the RAFT-style retrain decision; multiple fine-tuning seeds; numeric recommendations for the decision
question; the thesis chapters.

**Done in Part 1:** both datasets prepared with leakage-checked file-level splits; fine-tuning corpora; per-repository indexes (206 CrossCodeEval repos,
446 RepoBench sample repos); retrieval comparison on both datasets; one QLoRA fine-tuning run; the first pilot, the discovery that its base and RAG rows
were an instruction-prompt artifact, and the rerun with a plain prompt; staleness test; HumanEval forgetting check; reference-paper comparison.
**Left in Part 1:** a short GPU follow-up that tests two fixes for the frozen RAG system's formatting failures (diagnostic of the raw answers; forbidding
the fill-in-the-middle tokens; Qwen's repository-level prompt format), then refreshing the RAG numbers; the presentation and report.

## 5. Results to show (all real; section 6 says how to present them)

**Data (CrossCodeEval, 206 repos kept):** files BASE 618 / NEW 100 / TEST 273; TEST examples 543, of which 292 (53.8%) have a
relevant file in the main pool and 327 (60.2%) in the staleness pool; only 68 have a relevant file in NEW (the staleness
sample). Repos with >= 3 files: 206 of 471; with >= 5: 79. Fine-tuning corpus 9,378 train + 1,059 validation.
**Data (RepoBench, 1,826 repos kept):** files BASE 12,649 / NEW 3,482 / TEST 5,330; TEST examples 6,276 (cross_file_first)
and 6,035 (cross_file_random); gold file in the main pool for about 70%, in BASE+NEW for about 90%; about 1,200 NEW-gold
examples per setting. Fine-tuning corpus 10,800 train + 1,200 validation (capped at 12,000, a compute choice).
Leakage checks all pass (0 TEST files retrieved over 543 CrossCodeEval and 600 RepoBench queries).

**Retrieval comparison (relevance by proxy rule for CrossCodeEval; MRR with 95% CI):**
| Dataset, view (n) | dense UniXcoder | BM25 | random |
|---|---|---|---|
| CrossCodeEval main (292) | 0.770 [0.737, 0.804] | 0.884 [0.860, 0.908] | 0.633 |
| CrossCodeEval staleness (327) | 0.720 | 0.870 | 0.572 |
| CrossCodeEval, relevant file in NEW (68) | 0.716 | 0.885 | 0.553 |
| RepoBench cross_file_first main (300) | 0.446 | 0.466 | 0.323 |
| RepoBench cross_file_random main (300) | 0.484 | 0.535 | 0.319 |
BM25 is better on CrossCodeEval (paired difference CI excludes 0) and in cross_file_random; no clear difference in
cross_file_first. Pools are small (3 to about 10 files), so hit@5 and above are near 1 even for random: read hit@1, MRR
and the gap to random.

**Fine-tuning run (CrossCodeEval, QLoRA 4-bit, LoRA r=8, 1,089,536 trainable parameters = 0.07%):** 3 epochs, 1,761
steps, 3 h 29 min on a T4, about 8.7 GB. Training loss about 0.78 / 0.67 / 0.62 per epoch; validation loss about 0.68
(flat; validation is not file-held-out, so optimistic). **Validation loss, base vs adapter: 2.735 vs 0.689.**

**How the prompts were chosen (use for a methodology paragraph and one slide).** The task is to write the rest of a code line cut in the middle. The
first pilot gave every system the same "instruction form" the fine-tuned model was trained on; the plain model did not follow it (for the cut line
`response = await repository_ratings.` the base wrote `from datetime import datetime`, RAG a sentence, fine-tuned and hybrid the correct
`delete_rate(1, session, new_user)`). So base and RAG now get a plain continuation prompt (retrieved code as comments, then the code); the adapter
systems keep the form they were trained on. Same task, same retrieved chunks, same decoding and scoring; each model gets the prompt it can follow (the
prompts are not byte-identical: state this as a design choice). Plain minus instruction prompt, same 50 examples: base +0.257 edit similarity [0.191, 0.318],
RAG +0.161 [0.089, 0.239]; fine-tuned and hybrid exactly 0. The first pilot's numbers are kept only as the documented first attempt.

**Pilot, main view (50 CrossCodeEval TEST examples, seed 42, 40 repos; plain prompt for base and RAG; pilot, n=50):**
| System | EM | Edit sim. [95% CI] | Identifier acc. | CodeBLEU |
|---|---|---|---|---|
| base | 0.04 | 0.494 [0.426, 0.559] | 0.298 | 0.237 |
| RAG (A) | 0.02 | 0.387 [0.311, 0.468] | 0.217 | 0.140 |
| fine-tuned (B) | 0.08 | 0.613 [0.549, 0.680] | 0.414 | 0.213 |
| hybrid (C) | 0.14 | 0.644 [0.570, 0.715] | 0.490 | 0.214 |
Staleness view of the same 50 (new files added to the index): base 0.494 and fine-tuned 0.613 unchanged; RAG 0.403; hybrid 0.657 (EM 0.16, CodeBLEU 0.288).
Retrieval in the pilot: MRR 0.764 dense, 0.750 dense with new files, 0.840 BM25 (BM25 completion: RAG 0.386, hybrid 0.640, the same as dense).
Paired differences in edit similarity (95% bootstrap interval): fine-tuned minus base +0.120 [0.061, 0.187]; RAG minus base -0.106 [-0.172, -0.046]; hybrid minus
RAG +0.257 [0.168, 0.347]; **hybrid minus fine-tuned +0.031 [-0.032, 0.089] (not significant)**; RAG minus fine-tuned -0.226 [-0.310, -0.146].

**Staleness test: the 68 TEST examples whose relevant file is a NEW file (35 repositories; n=68):**
| System | Edit sim., main view (new file not in index) | Edit sim., staleness view (new file in index) |
|---|---|---|
| base | 0.457 | 0.457 |
| RAG | 0.384 | 0.350 |
| fine-tuned | 0.604 | 0.604 |
| hybrid | 0.640 [0.585, 0.694] | 0.695 [0.644, 0.746] |
Paired change for the hybrid: edit similarity +0.055 [0.015, 0.103], exact match 0.088 to 0.162 (+0.074 [0.015, 0.132]); the hybrid's answer changed on 27 of 68
examples (19 better, 8 worse); the relevant new file was in the top 5 chunks for 66 of 68. In the staleness view the hybrid beats the fine-tuned model by
+0.091 [0.036, 0.146]. RAG alone did not gain (-0.034 [-0.085, 0.018]). Fine-tuned and base cannot change (no retrieval).

**Forgetting check (HumanEval, all 164 problems, plain function stub for both models):** base 66/164 (pass@1 0.402), fine-tuned 63/164 (0.384), relative change
-4.5%, McNemar p = 0.68 (not significant). Wang et al. report -24.1% for full fine-tuning of larger models on 120,000 files.

**Cost (pilot, per example, one T4, 4-bit):** average time base 1.61 s, RAG 1.72 s, fine-tuned 1.91 s, hybrid 2.24 s (retrieval itself about 23 ms with dense,
4 ms with BM25); peak GPU 2.01 GB (base, fine-tuned) and 2.14 GB (RAG, hybrid); prompts with retrieval are about 2,100 tokens against about 430.

**Preliminary comparison with Wang et al. (direction only, never absolute numbers):** fine-tuning beats the base model: matches. Combination best: matches in
direction, not significant in the pilot. BM25 beats dense: matches for retrieval quality, no difference for completion. Retrieval raises input length and
time: matches. Fine-tuning hurts general ability: much smaller here (-4.5%, not significant). RAG beats the base model: not reproduced, but see caveat 1.

**Caveats that must appear next to these numbers:**
1. **The frozen RAG system has a formatting problem.** With the comment-wrapped chunks, 5 of 50 pilot answers are empty and 6 of 50 are the literal token
   `<|fim_suffix|>` (11 of 50 unusable; 14 and 18 of 68 in the staleness-test runs). On the 45 non-empty answers RAG is 0.430 against the base's 0.499, so a gap
   remains, but the "RAG is below base" result must not be read as "retrieval hurts". The hybrid shows none of these failures. Two fixes (forbidding Qwen's
   fill-in-the-middle tokens; Qwen's own repository-level prompt format) are being tested in a short GPU run; if it is done before the presentation, use its
   numbers instead and say so.
2. The first pilot (instruction prompt for all systems) is superseded: its base and RAG rows measured prompt format. State this once, plainly.
3. Pilot size: n=50 (68 for the staleness test) from one model, one run, one seed. Hybrid vs fine-tuned, dense vs BM25 and shorter-code results are inside the
   confidence intervals. Hit-versus-miss analysis is not possible (0 to 4 retrieval misses per run).
4. CodeBLEU's data-flow part is always 0 for one-line targets; lean on edit similarity, identifier accuracy and exact match.
5. CrossCodeEval relevance is a proxy rule; pools hold only benchmark files (fragments for RepoBench); validation set not file-held-out; Python only; CrossCodeEval is
   a community mirror; about half of long chunks are cut at the embedder's 1,024-token limit.

## 6. Diagrams, tables and charts to create

**Ready-made charts (use these images and their numbers; they come from `results/` via `src/evaluation/plot_pilot_results.py`, table in `pilot_numbers.csv`):**
`pilot_main_vs_staleness.png` (edit similarity, identifier accuracy, exact match by system), `pilot_prompt_effect.png` (instruction vs plain prompt, paired),
`pilot_staleness_68.png` (the 68-example staleness test and the paired change), `pilot_paired_differences.png` (which differences are real), `pilot_cost.png`,
`pilot_forgetting.png`; plus `training_loss.png` and the retrieval figures from earlier. `docs/example_outputs.md` has six side-by-side examples for the
examples slide. If you redraw a chart, keep: base grey, RAG blue, fine-tuned orange, hybrid green; value labels on bars; the "pilot, n=50" wording in the title.
The list below is what the report and slides need overall; do not redo what is already ready.

Style: same as the September deck (navy header bar, accent rule, simple boxes and arrows). Label axes and sample sizes.
Use ONLY the real numbers above. If you can create image or chart files, do; otherwise give each as a clean table, a
Mermaid diagram, or chart code (matplotlib) that I can run.

**Diagrams (6):**
1. End-to-end workflow of the three systems (A: files > chunks > embeddings > per-repo index > retriever > frozen model;
   B: BASE files > QLoRA > adapter on the same model; C: same retriever + fine-tuned model; shared base model, prompt, metrics).
2. Data pipeline replacing the old Figure 2 (benchmark > rebuild file text > dedupe > file-level split > BASE / NEW / TEST
   > leakage gate).
3. Split design for one repository (files coloured BASE / NEW / TEST; which feed the index and which feed fine-tuning; main
   vs staleness condition).
4. Leakage-safety checklist as a gate.
5. Compute workflow: local machine > GitHub > Colab T4 > Google Drive (checkpoints, results), with resume after disconnect.
6. Project status roadmap: done / in progress / not started, with Part 1 at about 96% and the whole thesis at about 74%.

**Tables (in the report; a few on slides):** the "Changes and why" table (section 3); the progress table (section 4); dataset
tables for both datasets (counts, split sizes, coverage); fine-tuning corpora; the retrieval comparison; the pilot results
(main and staleness, with variants); Wang et al.'s published numbers (clearly labelled, not comparable to this thesis); the
risks and limitations table.

**Charts (real data):**
1. Funnel per dataset: repos > repos with >= 3 files > >= 5 files (CrossCodeEval 471 > 206 > 79).
2. Stacked bars of files per split (CrossCodeEval 618/100/273; RepoBench 12,649/3,482/5,330).
3. Retrieval coverage and staleness sample sizes (CrossCodeEval 53.8% / 60.2%, 68 NEW-relevant; RepoBench gold in BASE
   70.1% / 71.2% vs BASE+NEW 89.9% / 90.3%; about 1,243 and 1,154 NEW-gold).
4. Retrieval comparison: grouped bars of MRR (and hit@1) for dense, BM25, random, with 95% CIs, per dataset and view; always
   show the random baseline.
5. Training loss curve (`results/figures/training_loss.png`), noting validation is not file-held-out.
6. Pilot completion quality: grouped bars of edit similarity and identifier accuracy by system, main vs staleness, titled
   "Pilot, n=50; not findings", with the prompt-format caveat in the subtitle.
7. Validation loss, base vs adapter (2.735 vs 0.689) with the note that much of the drop is format learning.
8. Cost: average ms per example and peak GPU MB by system (pilot).
9. Wang et al. published EM for the 1.5B model (24.48, 44.63, 41.47, 55.81), titled "published results, C++: not comparable".
10. Empty templates watermarked "PENDING: full evaluation not run": EM / edit similarity by system with CI whiskers; hit vs miss
    accuracy; staleness on the 68 NEW-relevant examples (A, B, C); top-k sweep; accuracy vs latency; forgetting check.

## 7. What to produce

**Report (Word, .docx)**, keeping the August report's front matter and section order. Sections: abstract (updated);
introduction with the decision question and domain; changes since the last report and why (section 3); literature and the
comparison with Wang et al. (concrete differences, not "does not fully address"); methodology (systems, file-level split,
leakage controls, retrieval, fine-tuning, metrics, extra analyses, hypotheses); implementation and compute setup;
prompt design (the paragraph above, with the example table); results so far (section 5, pilot clearly labelled, caveats printed with the numbers); progress and status (section 4
table and roadmap); expected results (empty templates); risks and limitations; revised timeline (table with
`[YOU FILL IN]` dates and a contingency period); references (existing only). Correct the hybrid-import and "mostly
execution" statements.

**Presentation (PowerPoint 16:9), [YOU FILL IN] slides**, same visual style as the September deck, with short plain-language
speaker notes on every slide. Suggested order: title; agenda; problem and decision question; what changed and why; the three
systems; how the prompts were chosen (one slide: the example, the four answers, the fix); data and file-level split; leakage-safe protocol; datasets in numbers; retrieval results; fine-tuning run; pilot
results (with the caveats slide right after); comparison with Wang et al.; hypotheses and evaluation plan; how much is done
(Part 1 about 96%, whole thesis about 74%, the Part 1 table and the Part 2 plan); compute workflow; remaining work and revised timeline; risks and limitations; thank you.

**Process:** (1) First reply: confirm you read every attachment, summarise in five bullets what changed since the old documents
and what the status is, and list missing information. Wait for my "go". (2) Then write the report. (3) After I say "go" again,
write the slides. (4) Finish with a list of open questions and every `[YOU FILL IN]` placeholder left.

=== PROMPT END ===

## Notes for you (not part of the prompt)

- Numbers come from `docs/progress_log.md` (Entries 3 to 42) and `docs/results_summary.md`. If new results arrive (the
  base-friendly prompt rerun, forgetting check, full runs), update sections 4 and 5 here before reusing the prompt, and remove
  the matching caveat and "may not claim" lines once they are settled.
- Download `results/pilot_*` from Drive before attaching so the charts can use the exact values.
- The original deck's text is generated by `docs/slides/generate_deck.py`, in case you want to edit the old deck locally instead.
