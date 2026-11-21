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
4. `docs/progress_log.md`: Entries 1 to 37, every decision, number and caveat. Entry 37 holds the plain-language note on how the prompts were chosen.
5. `docs/results_summary.md`: every real result in one place.
6. `docs/reference_paper_comparison.md`: Wang et al. (2025) comparison, and `docs/references.md`.
7. `results/figures/*.png`, `results/retrieval_comparison.json`, `results/repobench_retrieval_comparison.json`,
   and (after downloading from Drive) `results/pilot_main/comparison_summary.json`,
   `results/pilot_staleness/comparison_summary.json`, `results/val_loss_base_vs_adapter.json`.
8. `docs/next_steps_part3.md`: the remaining work in order (use it for the roadmap and "next steps").

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
- **Only pilot results exist for completion quality** (50 examples; one model, one run). Label every such number
  "pilot, n=50". Do not call anything a finding or a conclusion. The full 543-example evaluation has not been run.
- **Claims you may NOT make** (the data does not support them yet):
  - that RAG is worse than fine-tuning, or that fine-tuned beats base. The base and RAG scores are held back by a
    prompt-format artifact (see section 5, caveat 1);
  - that fine-tuning causes forgetting, or does not. The forgetting check is invalid and being redone;
  - that RAG handles new files better than fine-tuning (the staleness hypothesis). The pilot cannot test it;
  - that hybrid beats fine-tuned-only, or that BM25 beats dense for completion. The differences are inside the noise.
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

**About 65% of the project work is done (range 62 to 68%; thesis writing not counted). This is a weighted judgement
of effort, not a measurement; say so.** (August estimate was about 30 to 35%.)

| Workstream | Weight | Done | Status |
|---|---|---|---|
| Plan, reference-paper analysis, hypotheses | 5.7% | 100% | Finished |
| CrossCodeEval data (split, leakage checks, training corpus, pilot sample) | 11.4% | 100% | Finished |
| RepoBench data (split, corpus, 300-per-setting sample) | 8.0% | 90% | Nearly finished |
| Pipeline code (prompting, training, evaluation, demo, Colab setup, 27 tests) | 17.0% | 97% | Runs end to end on a T4 |
| Retrieval (indexes for both datasets; dense vs BM25 vs random) | 9.1% | 87% | Done |
| Fine-tuning | 11.4% | 60% | CrossCodeEval adapter and loss comparison done; no RepoBench adapter, no RAFT-style variant |
| Evaluation runs (EM, edit similarity, identifier accuracy, CodeBLEU) | 28.4% | 25% | Pilot (n=50) in four variants; no full 543-example run |
| Extra analyses (hit/miss, noisy context, staleness, forgetting, top-k) | 9.1% | 40% | Staleness view, shorter code, BM25 done; forgetting check invalid; the rest not run |

**Done:** both datasets prepared with leakage-checked file-level splits; fine-tuning corpora; per-repository indexes
(206 CrossCodeEval repos, 446 RepoBench sample repos); retrieval comparison on both datasets; one QLoRA fine-tuning run;
a pilot of all four systems; reference-paper analysis.
**Left (in order):** (1) rerun base and RAG with the plain continuation prompt on the same 50 examples (decided; the option is
built and tested locally, the GPU run is pending); (2) redo the forgetting check with the plain HumanEval stub on all 164 problems
(built, run pending); (3) the 68-example staleness test, relevant file in NEW (subset built, 68 examples from 35 repos, run pending);
(4) full CrossCodeEval comparison (543 TEST examples, main and staleness views) with hit/miss analysis, noisy-context and
top-k extras; (5) RepoBench fine-tuning and completion; (6) decide on the RAFT-style variant; (7) numeric recommendations.
Rough effect on progress: steps 1 to 3 about +4 to 5 points, step 4 about +12 to 15, step 5 about +8 to 10, the rest +3 to 4.

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

**Pilot (50 CrossCodeEval TEST examples, seed 42, 40 repos; all four systems; pilot, n=50):**
| System | EM | Edit sim. [95% CI] | Identifier acc. | CodeBLEU |
|---|---|---|---|---|
| base | 0.00 | 0.236 [0.212, 0.262] | 0.018 | 0.068 |
| RAG (A) | 0.00 | 0.226 [0.205, 0.248] | 0.042 | 0.121 |
| fine-tuned (B) | 0.08 | 0.613 [0.549, 0.680] | 0.414 | 0.213 |
| hybrid (C) | 0.14 | 0.644 [0.570, 0.715] | 0.490 | 0.214 |
Staleness view (NEW files added to the index; same 50): RAG 0.213 edit sim., hybrid 0.657 (EM 0.16, CodeBLEU 0.288);
base and fine-tuned are identical to the main view. Retrieval inside the pilot: MRR 0.764 (dense, main), 0.750 (staleness),
0.840 (BM25). Variants, edit similarity (base / RAG / fine-tuned / hybrid): code cut to 480 tokens 0.256 / 0.216 / 0.611 /
0.649; BM25 retrieval 0.236 / 0.224 / 0.613 / 0.640. Cost in the pilot: average 1.8 to 2.3 s per example per system; peak GPU
about 2.0 GB (2.1 with retrieval prompts of about 2,000 tokens); BM25 retrieval 203 ms vs 1,183 ms (dense) for all 50.
Prompts with retrieval are about 2,000 tokens against 512 in training.

**Caveats that must appear next to these numbers:**
1. **Prompt-format artifact (confirmed by reading the predictions, Entry 36).** Base exact match is 0 of 50 and base HumanEval
   0 of 20. The prompt is an instruction wrapper that the adapter was trained on; the base model does not continue the cut line:
   33 of 50 base outputs are import lines and 8 are prose; RAG outputs are comment lines (17), prose (17) or echoes of the
   retrieved-chunk header (8); every fine-tuned and hybrid output is a code continuation. So the base and RAG rows measure prompt
   format, not repository knowledge, and must not be used to rank RAG against fine-tuning. A rerun of base and RAG with a plain
   continuation prompt is the next step. (Hit-vs-miss is also not analysable at n=50: only 2 of 50 examples are retrieval misses.)
2. **Forgetting check invalid.** HumanEval first 20 problems: base 0/20, fine-tuned 5/20, with the same prompt-format
   problem. It will be redone on all 164 problems with the plain stub. Do not present it as forgetting.
3. **Staleness not yet tested.** The pilot examples have their relevant file in BASE, so NEW files act only as distractors
   (retrieval recall@3 fell from 0.89 to 0.78 but completion barely moved). The real test uses the 68 NEW-relevant examples.
4. Small pilot (n=50): hybrid vs fine-tuned, dense vs BM25, shorter code all within the confidence intervals.
5. CodeBLEU's data-flow part is always 0 for one-line targets; lean on EM, edit similarity and identifier accuracy.
6. CrossCodeEval relevance is a proxy; pools hold only benchmark files (fragments for RepoBench); validation not
   file-held-out; Python only; CrossCodeEval is a community mirror; about half of long chunks are cut at the embedder's
   1,024-token limit.

## 6. Diagrams, tables and charts to create

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
6. Project status roadmap: done / in progress / not started, with the 65% figure.

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
(65%, the completed-vs-remaining table); compute workflow; remaining work and revised timeline; risks and limitations; thank you.

**Process:** (1) First reply: confirm you read every attachment, summarise in five bullets what changed since the old documents
and what the status is, and list missing information. Wait for my "go". (2) Then write the report. (3) After I say "go" again,
write the slides. (4) Finish with a list of open questions and every `[YOU FILL IN]` placeholder left.

=== PROMPT END ===

## Notes for you (not part of the prompt)

- Numbers come from `docs/progress_log.md` (Entries 3 to 37) and `docs/results_summary.md`. If new results arrive (the
  base-friendly prompt rerun, forgetting check, full runs), update sections 4 and 5 here before reusing the prompt, and remove
  the matching caveat and "may not claim" lines once they are settled.
- Download `results/pilot_*` from Drive before attaching so the charts can use the exact values.
- The original deck's text is generated by `docs/slides/generate_deck.py`, in case you want to edit the old deck locally instead.
