# Prompt for the Claude web app: updated progress report + new presentation

How to use this file:
1. Open a new chat on the Claude web app.
2. Attach the files listed in "Files to attach" below.
3. Paste everything between the two lines marked `=== PROMPT START ===` and `=== PROMPT END ===`.
4. Before sending, fill in the items marked `[YOU FILL IN]`.

## Files to attach (in this order)

Must attach:
1. `docs/Nidwija_081MSCSK010_progress_report.docx` - the ORIGINAL progress report (August 2026). The
   new report must keep its structure, tone and citations, and update it.
2. `docs/slides/Midterm_Progress_Update.pptx` - the ORIGINAL defense presentation (September 2026).
   The new deck should look like a continuation of it.
3. `docs/things_to_do_first` - the experiment plan (the framework that replaced the report's
   original design). Authoritative for what the study does.
4. `docs/progress_log.md` - Entries 1 to 28: every decision, number and caveat so far.
4b. `docs/results_summary.md` - every real result so far in one place (retrieval comparison for both
   datasets, the fine-tuning run, what is still missing). Use its numbers for tables and charts.
5. `docs/figure2_data_pipeline.png` - the OLD data pipeline figure (it is outdated; the new one
   must replace it).
5b. `docs/reference_paper_comparison.md` - analysis of the main reference paper (Wang et al., 2025):
   what they did, their numbers, side-by-side table, predictions. Use it for the comparison section
   and slide.
5c. `results/retrieval_comparison.json`, `results/repobench_retrieval_comparison.json`, `results/figures/*.png`
   (dense vs BM25 vs random retrieval for CrossCodeEval and RepoBench, and the training loss curve; these exist now). Attach them so the charts use the
   real numbers instead of placeholders.

Attach if you have them (the web app cannot guess these):
6. The university's report template or formatting rules (margins, fonts, numbering, citation
   style, page limits). Without it, the report will only follow the old report's look.
7. Supervisor or committee feedback from the September defense (comments, questions, requested
   changes). The plan's Section 12 lists the earlier committee concerns, but not the actual
   feedback.
8. The original Figure 1 (end-to-end workflow) and Figure 3 / Code Snippet 4 images from the
   August report, if you want them redrawn rather than recreated. They are embedded in the .docx,
   but separate image files are easier for the web app to use.

Do NOT attach: `venv/`, raw datasets, `.env` files, tokens, or anything containing credentials.
Nothing in this prompt contains secrets; keep it that way.

=== PROMPT START ===

You are helping me, Nidwija Bhatta (MSc in Computer Systems and Knowledge Engineering, Tribhuvan
University, IOE Pulchowk Campus, student ID 081MSCSK010), prepare two documents for my thesis:

1. An UPDATED PROGRESS REPORT (a revised version of the attached August 2026 report).
2. A NEW PRESENTATION (a follow-up to the attached September 2026 mid-term deck).

Thesis title: "Comparative Study of Fine-Tuning, Retrieval-Augmented Generation, and Hybrid Models
for Code Completion in Enterprise Repositories". Supervisor: Prof. Dr. Subarna Shakya.
Today's date for this task: [YOU FILL IN, e.g. late November 2026]. Defense or submission
date: [YOU FILL IN].

## Ground rules (very important)

- **No results exist yet.** Nothing has been trained or evaluated. Do NOT invent accuracy numbers,
  confidence intervals, latency, memory, or any result. Where the final report would show results,
  create clearly labelled empty templates ("Results pending") and describe what each will show.
- Use only the numbers in this prompt and the attached files. If something is missing, say so and
  list it as a question for me instead of guessing.
- Keep hypotheses clearly labelled as hypotheses written BEFORE running experiments.
- Audience: examiners who know software but may not know machine learning. Explain terms in plain
  language the first time they appear (for example: "retrieval" = looking up relevant code at the
  moment of the question; "fine-tuning" = retraining the model on the project's own code;
  "leakage" = the model accidentally seeing the answers it is tested on).
- Keep the citation style of the original report. Use only the references already in it and in
  `docs/references.md`. Do not add new citations unless I give them.
- Be honest about limitations; they are a strength of the study, not something to hide.

## Part A. What changed since the August report and September deck

The original report and deck described a design that has since been replaced. The updated
documents must reflect the new design and say plainly that it changed and why.

| Topic | In the August report / September deck | Now (current, authoritative) |
|---|---|---|
| Split of data | 80/10/10 split BY REPOSITORY, both datasets mixed into one pool | Split BY FILE inside each repository into BASE / NEW / TEST. Each dataset is processed and reported separately; datasets are never pooled |
| Why | (the plan, section 1 A1/A2/A5: neither benchmark has a usable training split or full repository files, so knowledge pools are built from the benchmark data itself) | A file-level split lets the same repository supply knowledge for retrieval and fine-tuning while keeping test files unseen, and it supports the staleness test. [YOU CONFIRM this wording matches your reasoning] |
| Fine-tuning data | Prompt + ground truth of examples | Built only from BASE files with cut points inside lines. Never from test prompts or answers |
| Leakage control | Mentioned as repository split only | Automated checks that must pass: no TEST path or content in the pool, index or fine-tuning data; validation from BASE only; NEW files absent from fine-tuning |
| Language scope | Python only, not stated firmly | Python only for all experiments; multilingual CrossCodeEval is future work |
| Retrieval ground truth | "CrossCodeEval provides ground-truth relevant files" | CrossCodeEval has NO gold relevance label. A proxy rule is used (see Part C). RepoBench has a gold snippet index |
| Retrieval | Dense UniXcoder + FAISS only | Dense UniXcoder + FAISS, plus a BM25 baseline (prior work found BM25 can beat dense retrievers), plus a top-k sweep (1, 3, 5, 10) |
| Evaluation | Metrics + latency + memory | Same, plus extra analyses: hit vs miss, noisy-context injection, staleness test, forgetting check on HumanEval, cross-file-dependent subset, bootstrap confidence intervals |
| Objective | General comparison | Decision question: "Given a private repository and a single-GPU budget, which adaptation strategy should a team choose, and when does the hybrid's extra complexity pay off?" Conclusions must be numeric rules with thresholds, not "it depends" |
| Application domain | Enterprise-style repositories | Developer tooling for software companies with private codebases, where privacy rules often prevent sending proprietary code to commercial APIs, so teams self-host small open models under limited GPU budgets |
| Hybrid import | Report says the "missing import" was already present | Wrong: a real missing PEFT import was found and fixed (progress log Entry 9). The report must be corrected |
| "Work remaining" | "Mostly execution" | Understated. Remaining: fixes to training and evaluation code, GPU training, pilot, full runs, analysis, writing |
| Compute | "Available GPU" (unspecified) | No GPU on my main workspace. GPU work runs on Google Colab (T4, 16 GB) with Google Drive for saved work; later runs possibly on a cloud GPU rented by the hour |

Also note for the report: dataset numbers in the August report did not distinguish the community
mirror of CrossCodeEval from the official release. The log states the mirror is used and the
split was verified on all 2,665 examples (file text can be rebuilt exactly), but "content
matches the real GitHub files" is NOT verified.

## Part B. Work completed since the September deck (all verified unless marked)

1. Both datasets downloaded and inspected (RepoBench v1.1 Python, CrossCodeEval Python).
2. Retrieval ground-truth rule for CrossCodeEval defined and measured.
3. File-level BASE/NEW/TEST splits for both datasets, with automated leakage assertions that pass.
4. Fine-tuning corpora for both datasets, built from BASE files only, leakage-checked.
5. Per-repository FAISS indexes (UniXcoder) for all 206 CrossCodeEval repositories, with an
   assertion that no TEST file is indexed, and a smoke test.
6. Hybrid pipeline's missing PEFT import fixed (verified to import; model loading not yet run).
7. Bug found and fixed in the embedder: UniXcoder's real token limit is 1,024, not 1,026.
8. `rank_bm25` installed for the BM25 baseline (not yet used).
9. Seeded 50-example pilot set selected for CrossCodeEval.
10. Trainer pointed at the new corpora; interactive `demo.py` written (base / RAG / fine-tuned /
    hybrid side by side). Not yet run with a model.
11. Colab setup script and trainer checkpoint/resume support written (not yet run on Colab).
12. Review of the code found two problems: CodeBLEU always returned 0.0 silently, and the training loss
    counted the prompt and padding tokens (so the first Colab training run, made with that code, is a
    smoke test, not a result). Both are now FIXED in code (item 14); the fixed training has not been run yet.
13. Main reference paper (Wang et al., 2025) read in full and compared with this thesis (see
    `docs/reference_paper_comparison.md`); a correction to the plan was found: their data is 163,746 C++
    files, of which 120,000 are the retrieval and fine-tuning corpus.
14. Code fixes (19 automated tests pass): one shared prompt format for training, demo, hybrid and
    evaluation; training loss on the answer tokens only plus an end-of-answer token (checked on the real
    corpus with the real tokenizer: about 8 tokens per example carry the loss; 9% of inputs are shortened
    to fit 512 tokens); CodeBLEU now raises if unavailable instead of returning 0.0; bootstrap confidence
    intervals added; evaluation script rewritten for the pilot and full test set; a guard that prevents
    resuming training from checkpoints made by the older code.
15. Retrieval-only comparison written (dense UniXcoder vs BM25 vs a random floor, hit@k, P@k, R@k, MRR with
    95% bootstrap confidence intervals, plus the staleness subset) with plot scripts, including a training
    loss plot. NOT RUN yet; it needs no GPU and no training, so it is the first real result to come.

16. Retrieval-only comparison RUN on CrossCodeEval (Entry 20): BM25 beats UniXcoder (main view MRR 0.884 vs
    0.770, n=292, paired difference CI excludes 0); numbers in `docs/results_summary.md` section 1.
17. First valid fine-tuning run (v2, fixed code) finished on a Colab T4: 1,761 steps, 3 h 29 min, about 8.7 GB;
    training loss 0.78 / 0.67 / 0.62 per epoch, validation loss flat at about 0.68 (not file-held-out). No
    comparison with the base model yet, so no evidence that it helps (Entry 18).
18. RepoBench: seeded evaluation sample (300 per setting), per-repo indexes for its 446 repositories, and a
    retrieval comparison (Entries 24, 26, 28): BM25 better than dense in all four cells, significantly in
    cross_file_random; both beat random by less than on CrossCodeEval.
19. Evaluation tooling added: BM25 and prompt-length options for the system comparison, noisy-context option,
    hit-versus-miss and paired-difference analysis script, forgetting check (HumanEval) script, a model-free
    dry run of the pilot pipeline, stronger Colab setup checks (27 automated tests pass). Written and tested
    locally; none has produced a model result yet.

### Not done yet (be explicit about this in both documents)
No completion score exists for any system (no exact match, edit similarity, identifier accuracy or CodeBLEU),
no pilot has been run, and the base-versus-fine-tuned validation loss has not been computed. The pilot needs
the Colab GPU, whose free quota ran out after the v2 run. Still to do: pilot (50 examples) of base / RAG /
fine-tuned / hybrid; full CrossCodeEval evaluation (543 TEST examples) with BM25 and hit/miss analysis; extra
analyses (noisy context, top-k sweep, forgetting check, staleness effect on completion); RepoBench fine-tuning
and completion evaluation; whether to build the RAFT-style variant (the hybrid sees retrieved context at
inference that it never saw in training; prompts with retrieval are about 2,000 tokens against 512 in
training); moving seeds and constants into the config file; per-system GPU memory is not independent in the
current evaluation script (one process, shared model). The truncated-input and loss details are
implementation facts, not results.

## Part C. Method details to describe (current design)

**Systems** (same base model Qwen2.5-Coder-1.5B, same prompts, same metrics, same knowledge):
- System A, RAG-only: frozen model + retrieved chunks. 256-line chunks with 32-line overlap;
  microsoft/unixcoder-base embeddings; FAISS flat inner-product index on normalized vectors; one
  index per repository; BM25 baseline; top-k sweep.
- System B, fine-tuning-only: QLoRA (4-bit NF4), adapters on attention projection layers
  (q_proj, v_proj), LoRA rank 8, alpha 16, dropout 0.05, 3 epochs, batch 1 with gradient
  accumulation 16, learning rate 2e-4, max sequence 512 tokens. No retrieval at inference.
  One adapter per dataset.
- System C, hybrid: the fine-tuned model plus retrieval with the same retrieval and prompt format as A.
  Optional RAFT-style variant: fine-tune with retrieval-formatted prompts.

**Split design (per repository, by file, never by example, fixed seed 42):**
- Keep repositories with at least 3 distinct files.
- BASE (about 50 to 60% of files): the knowledge pool, used for BOTH retrieval and fine-tuning.
- NEW (about 15 to 20%, only repositories with at least 5 files): retrieval index only, never
  fine-tuning. Used for the staleness test.
- TEST (about 25 to 30%): targets that are evaluated. Never in the pool, index or fine-tuning data.
- At least 2 BASE files and 1 TEST file per repository.
- MAIN condition: pool = BASE (headline comparison). STALENESS condition: NEW added to the retrieval
  index only (A and C). Tests the claim that RAG handles new or changed code and fine-tuning does not.

**CrossCodeEval proxy relevance rule:** for an example in repo R with target file F, the relevant
files are the distinct files named in the example's cross-file snippets that (a) are in the pool for
the current condition and (b) are not F. Examples with none are excluded from retrieval metrics and
the excluded share is reported. A reference-aware snippet variant is used only as a sensitivity check.

**Fine-tuning corpus construction:**
- CrossCodeEval: cut right after a "." inside a line (all 2,665 benchmark prompts end in "."); input
  = file prefix (last 1,500 characters), output = rest of the line; up to 20 cut points per BASE
  file; skip comment and import lines; validation = about 10% of lines from the same BASE files
  but different lines (NOT file-held-out, so validation loss is optimistic; used for monitoring only).
- RepoBench: cut at a line boundary, output = full next line; up to 8 cuts per prefix fragment, 1 per
  snippet fragment; deduplicated; seeded subsample to 12,000 examples (10% validation). The 12,000
  cap is a compute-matching choice that is NOT in the plan; say so.

**Leakage assertions that passed:** TEST files disjoint from BASE and NEW; no TEST path in any
pool, index or corpus; no TEST ground truth or next line appears as a corpus output; no TEST
ground truth of at least 20 characters appears inside any corpus input (shorter strings are only
checked as exact outputs, a stated limitation); validation from BASE only; NEW absent from
fine-tuning; no TEST chunk retrieved in the smoke test (0 of 543 examples).

**Evaluation (planned):** exact match, edit similarity, identifier accuracy, CodeBLEU (implementation
to be chosen; predictions cut to the first line before scoring); retrieval P@k, R@k, MRR; latency
and memory per system; accuracy gain per added latency and per added GB; bootstrap confidence
intervals; multiple fine-tuning seeds if time allows.
Extra analyses: (1) hit vs miss, (2) noisy-context injection, (3) staleness test, (4) forgetting
check with a small HumanEval run before and after fine-tuning, (5) cross-file-dependent subset,
(6) top-k sweep.

**Hypotheses (written before experiments):**
- H1: hybrid > RAG-only > fine-tuning-only on cross-file-dependent examples.
- H2: the hybrid's gain shrinks when retrieval quality is high.
- H3: fine-tuning-only degrades most on NEW files and unseen code.
- H4 (low-data): with only a few files per repository, fine-tuning adds little relative to RAG; a
  legitimate finding either way.

**Expected vs Wang et al. (2025):** their findings: RAG with suitable retrieval beats fine-tuning
alone; the combination is best; BM25 beat dense embedders (UniXcoder, CodeT5) on C++; retrieval
greatly increases input length and cuts throughput, while fine-tuning costs training upfront but no
runtime latency; fine-tuning degraded general code generation. Their setting: one company's C++ (Tencent
WXG), 163,746 files of which 120,000 are the retrieval and fine-tuning corpus, six models from 0.5B to 7B
including Qwen2.5-Coder-1.5B, full fine-tuning on 8 x A100 GPUs, metrics EM / edit similarity / BLEU only.
Ours: public Python benchmarks, far smaller per-repo data, 1.5B
model with QLoRA. Concrete differences to put in the research gap table: public reproducible
benchmarks vs proprietary data; Python vs C++; 1.5B QLoRA vs full fine-tuning of larger models;
retrieval-quality metrics (P@k, R@k, MRR) and hit/miss analysis; cross-file and internal-API analysis;
low-data regime and staleness test. Replace the older wording "does not fully address" with these.
Use `docs/reference_paper_comparison.md` for the full side-by-side table and their numbers.
Rules for the comparison: compare direction and ranking of methods, NOT absolute scores (different
language, scale, task and metrics); never put this thesis's numbers on the same axis as theirs.
Their published numbers for Qwen2.5-Coder-1.5B (EM / ES / BLEU, top-5 retrieved snippets) may be shown
as a clearly labelled reference table or chart ("Wang et al. 2025, C++, published results"):
base 24.48 / 60.78 / 41.47; RAG BM25 55.81 / 77.26 / 68.35; RAG UniXcoder 41.47 / 70.08 / 55.77;
fine-tuning 44.63 / 74.12 / 60.50. Averaged over their six models: base+RAG-BM25 EM 53.76 vs
fine-tuned+RAG-BM25 57.43. Their fine-tuning cut HumanEval pass@1 by 24.1% on average.

## Part D. Data tables to use (exact numbers from the log)

### D1. CrossCodeEval (Python), 2,665 examples
| Measure | Count |
|---|---|
| Repositories | 471 |
| Distinct (repo, target file) | 1,368 |
| Repos with >= 3 files / examples | 206 / 2,018 |
| Repos with >= 5 files / examples | 79 / 1,237 |

After the split (206 repositories kept):
| Split | Files | Examples (by target file) |
|---|---|---|
| BASE | 618 | 1,259 |
| NEW | 100 | 216 |
| TEST | 273 | 543 |
| Total | 991 | 2,018 |

BASE is 62% of files (above the 50-60% target) because 3- and 4-file repositories have no NEW.
NEW is 10% of files overall for the same reason.

Retrieval-relevance coverage (TEST examples with at least one relevant file in the pool):
| Condition | TEST examples | With >= 1 relevant file |
|---|---|---|
| Main (pool = BASE) | 543 | 292 (53.8%) |
| Staleness (pool = BASE + NEW) | 543 | 327 (60.2%) |
Only 68 TEST examples have a relevant file in NEW (the staleness sample size). Only 339 TEST
examples are in repositories that have NEW files at all.
Upper bound before splitting: 54.8% of all examples (66.8% for repos >= 3 files, 76.5% for >= 5).
Only 27% of snippets (3,524 of 12,923) come from files that are themselves benchmark targets, so
most relevant repository code is simply not available to the pool (a stated limitation).

### D2. RepoBench v1.1 (Python), cross-file settings
| Split setting | Examples | Repos | Distinct target files | Repos >= 3 target files / examples | Repos >= 5 target files / examples |
|---|---|---|---|---|---|
| cross_file_first | 8,033 | 1,751 | 4,588 | 622 / 5,828 | 227 / 3,563 |
| cross_file_random | 7,618 | 1,749 | 4,657 | 616 / 5,688 | 219 / 3,801 |
| in_file (control, not used) | 7,910 | 1,707 | 4,126 | 539 / 5,516 | 168 / 3,445 |

Both cross-file settings overlap heavily (1,530 shared repositories, 2,418 shared target files, only
112 identical examples), so ONE shared split is used; results are still reported per setting.
After the split (1,826 of 1,970 repositories kept):
| Split | Files |
|---|---|
| BASE | 12,649 |
| NEW | 3,482 |
| TEST | 5,330 (24.8% of files) |
Pool: 31,140 fragments (BASE: 1,046 prefixes + 23,562 snippets; NEW: 304 prefixes + 6,228 snippets).
TEST examples: cross_file_first 6,276; cross_file_random 6,035.
Gold-file coverage for TEST examples:
| Setting | TEST examples | Gold in BASE (main) | Gold in BASE+NEW (staleness) | Gold in NEW |
|---|---|---|---|---|
| cross_file_first | 6,276 | 4,399 (70.1%) | 5,642 (89.9%) | 1,243 |
| cross_file_random | 6,035 | 4,298 (71.2%) | 5,452 (90.3%) | 1,154 |
RepoBench therefore has a much larger staleness sample (about 1,200 per setting) than CrossCodeEval (68).
RepoBench context facts: candidates per example min 2, mean about 11, max 75; gold index valid in
8,026 of 8,033 (first) and 7,610 of 7,618 (random); 277 fragments dropped by the content filter.

### D3. Fine-tuning corpora
| Dataset | Candidates | Train | Validation | Notes |
|---|---|---|---|---|
| CrossCodeEval | (from 618 BASE files) | 9,378 | 1,059 | 7 candidates dropped for containing a TEST ground truth; median input about 1,455 characters, median output 22 |
| RepoBench | 27,586 (26,815 unique) | 10,800 | 1,200 | 115 dropped for matching a TEST next line exactly (9 short); 3,253 from prefix fragments, 8,747 from snippet fragments; median input about 538 characters, median output 41 |

### D4. Retrieval index (CrossCodeEval)
206 repositories; `main` view 806 chunks (BASE only); `staleness` view 931 chunks (806 BASE + 125 NEW);
about 17 minutes to build on CPU. Median chunk is about 1,045 UniXcoder tokens but the model accepts
1,024, so roughly half of each long chunk is cut; the plan's 256-line chunk size is kept and this is
reported as a limitation.
Smoke test (query = last 20 lines of each TEST prompt; file-level hit@k against the proxy rule):
| View | Examples | hit@1 | hit@3 | hit@5 | hit@10 |
|---|---|---|---|---|---|
| main | 292 | 0.603 | 0.932 | 0.983 | 1.000 |
| staleness | 327 | 0.532 | 0.893 | 0.960 | 0.997 |
CAVEAT to print next to this table (the retrieval comparison in section D4b below supersedes it): repositories are tiny (3 to about 10 chunks per pool), so top-5 and
top-10 cover nearly the whole pool and these rates are inflated. This is a smoke test, not a retrieval
result. The staleness hit rates being lower (NEW files add competing candidates) is a hypothesis for
H3, not a finding.

### D4b. Retrieval comparison results (real; use these, they replace the PENDING templates)
See `docs/results_summary.md` sections 1 and 2 for the full tables. Headlines:
- CrossCodeEval main (n=292), MRR with 95% CI: dense 0.770 [0.737, 0.804], BM25 0.884 [0.860, 0.908], random
  0.633 [0.596, 0.672]; hit@1 0.603 / 0.784 / 0.397. Paired dense minus BM25 MRR -0.114 [-0.152, -0.075].
  Staleness (n=327): MRR 0.720 / 0.870 / 0.572; relevant-file-in-NEW subset (n=68): 0.716 / 0.885 / 0.553.
- RepoBench sample (n=300 per setting), MRR dense / BM25 / random: cross_file_first main 0.446 / 0.466 / 0.323;
  cross_file_random main 0.484 / 0.535 / 0.319. Differences dense vs BM25: not significant in cross_file_first,
  significant in cross_file_random. Right file ranked first only 22 to 34% of the time.
- Caveats: small pools (random already scores high at hit@3 and above); RepoBench sample has no NEW-gold
  examples, so its staleness view shows NEW files only as distractors.

### D5. Pilot
50 CrossCodeEval TEST examples drawn with a seeded random draw (seed 42) from the 292 main-condition
candidates; they come from 40 repositories, 37 of the 50 in repositories that have NEW files. The pilot
is a pipeline check, not a result; 50 examples are too few to compare systems.

## Part E. Diagrams and charts to create

Use a consistent style with the original deck (navy header bar, accent rule, simple boxes and arrows).
Charts must use ONLY the real numbers above. Label axes and sample sizes.

**Diagrams (replace or add):**
1. **End-to-end workflow, three systems** (update Figure 1): A = Repository files -> chunking ->
   embeddings -> per-repo FAISS index -> retriever -> frozen Qwen2.5-Coder-1.5B -> completion.
   B = BASE-file training examples -> QLoRA -> adapter on the same base model -> completion (no retrieval).
   C = same retriever -> fine-tuned model -> completion. Highlight C. Mark that all three share
   the same base model, prompt format and metrics.
2. **New data pipeline** (replaces the old Figure 2): benchmark data -> rebuild file text -> dedupe by
   (repo, file) -> file-level split BASE/NEW/TEST per repository -> [BASE: retrieval pool + fine-tuning
   corpus] [NEW: retrieval index only] [TEST: evaluation targets only, in no pool/index/corpus] ->
   leakage assertions gate.
3. **Split design graphic:** one repository drawn as a row of files colored BASE / NEW / TEST, with arrows
   showing which parts feed the index and which feed fine-tuning, and a "main" vs "staleness" condition
   showing NEW added to the index only.
4. **Leakage-safety checklist graphic:** the assertions in Part C as a gate that data must pass.
5. **Compute workflow:** local machine (edit, commit, push) -> GitHub -> Colab T4 (clone, setup, train) ->
   Google Drive (cache, checkpoints, adapters, results). Include "resume after disconnect".
6. **Project status roadmap:** done vs in progress vs not started (see Part F).

**Charts (real data):**
1. Funnel for each dataset: repositories -> repositories with >= 3 files -> with >= 5 files
   (CrossCodeEval 471 -> 206 -> 79; RepoBench target-file view 1,751 -> 622 -> 227 for cross_file_first).
2. Stacked bar of files per split: CrossCodeEval (618 / 100 / 273) and RepoBench (12,649 / 3,482 / 5,330).
3. Bar chart of retrieval-relevance coverage for TEST examples: CrossCodeEval main 53.8% vs staleness
   60.2%; RepoBench gold in BASE 70.1% / 71.2% vs BASE+NEW 89.9% / 90.3%.
4. Bar chart of fine-tuning corpus sizes (train/validation) for both datasets.
5. Grouped bar of the smoke-test hit@k for main vs staleness, WITH the "inflated, smoke test only" caveat
   in the chart title or note.
6. Staleness sample size comparison: CrossCodeEval 68 vs RepoBench about 1,243 and 1,154.
7. Reference chart from the main paper: grouped bars of Wang et al.'s published Qwen2.5-Coder-1.5B EM for
   base, fine-tuning, RAG-UniXcoder, RAG-BM25 (24.48, 44.63, 41.47, 55.81), titled "Wang et al. (2025),
   C++, published results: not comparable in absolute terms to this thesis".
8. Retrieval comparison (dense UniXcoder vs BM25 vs random; REAL numbers exist now, use `results/*.json`): grouped bars of hit@1, hit@3, MRR with 95%
   confidence intervals for the main pool (n expected 292) and the staleness pool (n expected 327), and a
   subset chart for the staleness sample (examples whose relevant file is in NEW, n expected 68). If
   `results/retrieval_comparison.json` is attached, use ITS numbers; otherwise draw empty templates marked
   "PENDING". Always show the random baseline: pools are tiny, so hit@5 and hit@10 are high even for
   random guessing.
9. Training loss curve (training and validation loss against step): `results/figures/training_loss.png` exists
   (v2 run); redraw it from `trainer_state.json` and say that the validation loss is not file-held-out. Validation loss is not file-held-out, so it is optimistic: say so.
10. Empty results template charts, clearly watermarked "PENDING - no results yet": EM / edit similarity by
   system A/B/C with confidence-interval whiskers; hit vs miss accuracy; accuracy vs latency scatter;
   top-k sweep line; staleness bar (A, B, C on NEW files).

## Part F. Timeline and status (rewrite the old table)

Status key: Done / In progress / Not started.
- Done: literature review; dataset download and inspection; relevance rule; splits and leakage checks
  for both datasets; fine-tuning corpora; CrossCodeEval and RepoBench indexes; retrieval comparison for both
  datasets (BM25 > dense); hybrid import fix; pilot sample; demo script; Colab setup; reference paper analysed;
  code fixes and evaluation tooling written and tested; first valid fine-tuning run (v2) finished.
- In progress / waiting: the pilot and all model evaluations wait for the Colab GPU quota (or a paid plan).
- Not started: any completion score; full CrossCodeEval evaluation (543 TEST examples); extra analyses run on
  model outputs; RepoBench fine-tuning and completion; results writing.
- My own estimate of project completion (work and analysis only, not writing): about 60% (Entry 29). The
  earlier "30 to 35%" is out of date.
Remaining plan, in order: (1) pilot (50 examples) of base/RAG/fine-tuned/hybrid on Colab; (2) full CrossCodeEval
evaluation, with a RAFT-style retrain only if the pilot shows the hybrid suffers from the prompt mismatch; (3) BM25 and hit/miss analysis on the full set; (4) RepoBench (seeded smaller
sample, retrieval-only first); (5) extra analyses (staleness, noisy context, forgetting, bootstrap CIs);
(6) numeric recommendations and writing; (7) revise the timeline with the supervisor.
Produce a revised timeline table with [YOU FILL IN] dates for each stage, and keep a contingency period.

## Part G. Risks, limitations, and defense points

**Risks:** GPU availability and Colab disconnects (mitigated by checkpoints and small model); rebuilt
data might differ from the logged data (mitigated by size checks); small CrossCodeEval staleness sample
(68 examples); RepoBench test set is large (about 12,000); results may be close to prior work (mitigated by
direct comparison and the explicit differences).
**Limitations to state:** pools hold only files that appeared in the benchmarks (full files for
CrossCodeEval, fragments for RepoBench), not full repositories; benchmark-derived setting, not a real
company's codebase; much smaller scale than Wang et al.; task formats differ between datasets so results
are separate; CrossCodeEval relevance is a proxy; staleness covers only repositories with enough files;
Python only; validation sets are not file-held-out; RepoBench corpus capped at 12,000 by a compute choice;
short strings under 20 characters are not checked inside corpus inputs; about half of long chunks are cut
at the embedding model's token limit; the CrossCodeEval copy is a community mirror and its match to real
GitHub files is not verified.
**Contribution framing:** the controlled experimental design, the leakage-safe split construction, and
the analysis, not the scripts. **Likely committee questions:** is it just AI work (application domain and
privacy/GPU constraints); what did you do yourself (design, split construction, metric design, analysis);
how does it differ from Wang et al.; is it only a comparison (hypotheses and extra analyses); what is the
objective and conclusion (decision question and numeric recommendations).

## What to produce

**1. Updated progress report** as a Word document (.docx), keeping the August report's front matter and
section order, with these changes:
- Update Methodology (split by file, leakage controls, BM25, extra analyses, hypotheses).
- Replace "Work Completed", "Work Remaining" and the timeline with Parts B, F.
- Add a section "Changes from the previous report and why" (table in Part A).
- Replace the research gap table using the concrete differences in Part C.
- Add data tables and charts from Parts D and E; mark all result slots as pending.
- Correct the hybrid-import statement and the "mostly execution" statement.
- Add Limitations and Risks from Part G.
- Keep references to those already used.
Report length: [YOU FILL IN, or "similar to the original, plus about 5 pages"].

**2. New presentation** (PowerPoint, 16:9) of about [YOU FILL IN, e.g. 15 to 18] slides, same visual style as the
original deck, covering: title; agenda; problem and decision question; what changed since the last
update and why; the three systems; data and file-level split design; leakage-safe protocol; datasets in
numbers; fine-tuning corpora and retrieval index; methodology and implementation (including the shared
prompt, loss on answer tokens only, leakage checks); comparison with the main reference paper (Wang et al.:
what they did, what they found, how this thesis differs, my predictions); evaluation plan and hypotheses;
results so far (retrieval comparison if available, otherwise the smoke-test findings, with caveat) and an
"expected results" slide using the empty templates; compute workflow; status and revised timeline; risks and limitations; next steps; thank you.
Add short speaker notes to each slide in plain language that I can say aloud to non-experts.

**3. A list of open questions** for me where this prompt or the attachments do not have enough
information, plus a list of every placeholder left to fill.

Before writing, confirm you have read all attachments, summarize in five bullets what you understood
changed since the old documents, and list anything missing. Then wait for my go-ahead.

=== PROMPT END ===

## Notes for you (not part of the prompt)

- The numbers above come from `docs/progress_log.md`. If you change data or settings later, update this
  file before reusing it.
- The new report and deck should only get real result numbers after the Colab runs finish.
- The original deck's slide text is generated by `docs/slides/generate_deck.py` if you want to edit the
  existing deck locally instead of using the web app.
