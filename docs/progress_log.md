# Progress Log

Running record of what was asked, what was done, and what was found, so the
console history doesn't need to be re-read. The plan itself lives in
`docs/things_to_do_first` and is not changed by this log. Newest entries at the
bottom. Each entry notes which plan section it relates to.

Standing instruction from the user: stay close to the plan; do not deviate a lot.
Do not depend on raw repo data beyond what the benchmarks provide.

---

## Entry 1: Read the plan
- **Asked:** read `docs/things_to_do_first` and confirm.
- **Done:** read all 264 lines. No files changed.
- **Found:** nothing to report beyond the plan itself. First actions per Section 9
  are the dataset counts, the A3 rule, the hybrid import fix, then CrossCodeEval
  preprocessing.

## Entry 2: RepoBench download error
- **Asked:** `python data/repobench/download.py` failed with
  `BuilderConfig 'cross_file_first' not found. Available: ['default']`.
- **Cause:** the HF dataset `tianyang/repobench_python_v1.1` has one config
  (`default`). `cross_file_first`, `cross_file_random` and `in_file` are splits.
- **Done:** edited `data/repobench/download.py` to load the dataset once and save
  each split to `data/repobench/<split>/`. The user re-ran it and the download
  worked (three split folders exist).
- **Found:** the split names guessed from the plan were correct.

## Entry 3: Step-1 check on the downloaded data (Section 9, step 1; Section 2)
- **Asked:** do the first pre-check before any preprocessing, and log it.
- **Done:** read-only inspection of both datasets (nothing written into `data/`).
  Throwaway scripts were run from `/tmp`, not saved in the repo. Computed schema,
  repo counts, distinct files per repo, and how many repos meet the 3-file and
  5-file thresholds from Section 3.

### CrossCodeEval (Python), 2,665 examples
Saved as a DatasetDict with a single key named `train` (just a label; it is not a
training split, so don't use it as one).
Fields: `prompt`, `groundtruth`, `right_context`,
`metadata{repository, file, groundtruth_start_lineno, ...}`,
`crossfile_context_retrieval`, `crossfile_context_retrievalwref`.

| Measure | Count |
|---|---|
| Repos | 471 |
| Distinct (repo, target file) | 1,368 |
| Repos with >= 3 files / examples | 206 / 2,018 |
| Repos with >= 5 files / examples | 79 / 1,237 |

These match the numbers already recorded in Section 2 of the plan, so the
download is the same data. File reconstruction (prompt + groundtruth +
right_context) was verified earlier per the plan and was not repeated.

### RepoBench v1.1 (Python)
Fields: `repo_name`, `file_path`, `context` (list of `identifier`, `path`,
`snippet`), `import_statement`, `token_num`, `cropped_code`, `all_code`,
`next_line`, `gold_snippet_index`, `created_at`, `level`.

| Split | Examples | Repos | Distinct target files | Repos >= 3 target files / examples | Repos >= 5 target files / examples |
|---|---|---|---|---|---|
| cross_file_first | 8,033 | 1,751 | 4,588 | 622 / 5,828 | 227 / 3,563 |
| cross_file_random | 7,618 | 1,749 | 4,657 | 616 / 5,688 | 219 / 3,801 |
| in_file | 7,910 | 1,707 | 4,126 | 539 / 5,516 | 168 / 3,445 |

Counting snippet source paths as well as target files (the pool would hold both,
per Section 3), repos with >= 3 files rise to about 1,600 (cross_file_first:
1,614; >= 5 files: 1,182). Distinct paths are 17,237 for cross_file_first.

Other checks on the RepoBench fields:
- Candidates (`context` snippets) per example: min 2, mean about 11, max 75.
- `level` (context length bucket) runs from 2k to 128k. Each bucket is capped at
  1,000 examples, with fewer in the largest buckets.
- `cropped_code` is always contained in `all_code` (8,033 of 8,033 in
  cross_file_first).
- `next_line` appears in `all_code` in only 26 of 8,033 cases. So `all_code` is the
  file text up to the target line, **not** the full file. This fits the plan's
  statement that RepoBench pools are fragments, not full files (Section 3).
- `gold_snippet_index` is valid in 8,026 of 8,033 (cross_file_first) and 7,610 of
  7,618 (cross_file_random). The invalid ones are index >= number of snippets
  (for example index 12 with 2 snippets), so those examples must be dropped from
  retrieval metrics and the dropped share reported (Section 6).
- `in_file` has no usable gold index (0 valid of 7,910). That is expected, since
  it needs no cross-file retrieval. Use it only as a control, not for retrieval
  metrics.

### Takeaways
1. Both datasets support the Section 3 split well enough. CrossCodeEval is the
   small one: only 79 repos can support the NEW (staleness) files.
2. RepoBench has more repos at each threshold, so the staleness analysis has a
   larger sample there, once pools are built from snippet paths too.
3. The decisions about RepoBench pool construction and which setting(s) to use
   are not made yet. Per Section 2 the cross-file settings are preferred.
4. Not yet verified: the plan's "consistency of all_code" check only covers the
   substring relation above. Nothing was checked against real GitHub files.

## Next (per Section 9, not started)
- Step 2: settle the CrossCodeEval retrieval ground-truth rule (A3, still OPEN).
- Step 3: fix the missing import in the hybrid pipeline.
- Step 4: build CrossCodeEval preprocessing with leakage assertions.
## Entry 4: A3, CrossCodeEval retrieval ground-truth rule (Section 1, A3; Section 6)
- **Asked:** settle A3. The plan suggests "files named in the example's cross-file
  snippets that exist in the pool", then document it and report how many examples
  have at least one relevant pool file.
- **Done:** read-only check of how snippet filenames relate to target files
  (throwaway script in `/tmp`; nothing written into `data/`).
- **Found (data facts):**
  - Snippet `filename` values are repo-relative paths in the same format as
    `metadata.file` (for example `webui/app.py`), so they match directly.
  - No snippet names the example's own file (0 self-references), and every example
    has at least one snippet (mean about 4.8).
  - Only a minority of snippets come from files that are themselves target files:
    3,524 of 12,923 (27%) in `crossfile_context_retrieval`. The rest come from repo
    files that never appear as a target, so they can never be in the pool. This is
    the "pools hold only files that appeared in the benchmark" limitation in
    Section 10.
  - There are two snippet variants. `crossfile_context_retrieval` is the standard
    one. `crossfile_context_retrievalwref` was retrieved using the reference
    completion. Results are almost identical (1,461 vs 1,446 examples).
- **Rule adopted (proxy, no gold label exists):**
  For an example in repo R with target file F, the *relevant files* are the
  distinct filenames in `crossfile_context_retrieval` that (a) are in the pool for
  the current condition and (b) are not F. Pool = BASE (main condition) or
  BASE + NEW (staleness condition). Examples with no relevant file are excluded from
  P@k, R@k and MRR and the dropped share is reported. `retrievalwref` is only a
  sensitivity check, not the primary rule.
- **Coverage, measured against ALL target files in the repo (an upper bound):**

  | Subset | Examples | With >= 1 relevant file |
  |---|---|---|
  | All | 2,665 | 1,461 (54.8%) |
  | Repos >= 3 files | 2,018 | 1,349 (66.8%) |
  | Repos >= 5 files | 1,237 | 946 (76.5%) |

- **Caveat for the next step:** these figures are an upper bound. After the
  BASE/NEW/TEST split, a relevant file that lands in TEST (or in NEW under the main
  condition) is not in the pool, so the real share with a relevant file will be
  lower. It must be recomputed per condition once the split manifests exist, and
  the sample sizes reported.
- **Status:** A3 is settled in practice, but I have not edited the
  `[OPEN] A3` line in `docs/things_to_do_first`. You decide whether to mark it
  RESOLVED there.

## Entry 5: Section 1 review, do the scripts match the resolved decisions?
- **Asked:** is anything else in Section 1 outstanding, and do any scripts need
  changes before Section 2? Read-only review of `src/`; no files changed.
- **Found:** the Section 1 decisions are recorded in the plan, but the existing
  scripts still implement the OLD design:

| Plan item | Current code | Gap |
|---|---|---|
| A1/A2/A5 file-level BASE/NEW/TEST split, leakage assertions | `src/preprocessing/prepare_datasets.py` splits 80/10/10 by **repo**, mixes both datasets into one pool, uses the example's `prompt` and `groundtruth` as the input/output, with no assertions | Must be rewritten (plan Section 9, step 4). Test examples are never used as training data in the plan, but the current script has `groundtruth` as `output` for train examples. |
| A3 relevance rule | `relevant_files` = all snippet filenames, no pool filter | Update to the Entry 4 rule once the split manifests exist |
| A4 Python only | Python only everywhere (`chunker.py` defaults, CodeBLEU `lang="python"`) | Nothing to change |
| A6 per-repo index, pool files only | `FAISSVectorStore` is one flat index (`IndexFlatIP`, dim passed in), with no per-repo logic and no test-file exclusion. `chunker.py` reads files from disk, but the pools are in-memory text | Needs per-repo build, a text-based chunker, and an assertion that no TEST file is indexed |
| Section 5 (not Section 1) | `hybrid/pipeline.py` loads the model with `AutoModelForCausalLM` only | The "missing import" is probably `peft` (`PeftModel`) if the trainer saves an adapter. Unconfirmed; this is Section 9, step 3. |

- **Not changed:** retrieval and fine-tuning code beyond this. Nothing is blocking
  Section 2 itself (datasets are already downloaded and counted).

## Entry 6: RepoBench setting choice (Section 2)
- **Asked:** set RepoBench to the setting the plan suggests (cross-file).
- **Decision:** use the **cross-file settings** (`cross_file_first` and
  `cross_file_random`) for all RepoBench experiments, as Section 2 prefers. The
  plan says "cross-file settings" (plural), so both are kept. Results are reported
  per setting, not pooled. `in_file` stays downloaded but is excluded from
  experiments; it has no gold index, so it cannot support retrieval metrics (Entry 3).
- **Done:** changed the default `configs` of `convert_repobench` in
  `src/preprocessing/prepare_datasets.py` to drop `in_file`. That script is still
  the old design and will be rewritten in Section 9, step 4 (see Entry 5).
  `data/repobench/download.py` was left unchanged and still downloads all three
  splits.
- **Open:** whether to report `in_file` as an optional control later. Not needed
  now.

## Entry 7: CrossCodeEval pool and BASE/NEW/TEST split (Section 3; Section 4 assertions)
- **Asked:** start the script for Section 3 (the split), CrossCodeEval first
  (Section 9, step 4).
- **Done:** wrote `src/preprocessing/build_crosscodeeval_split.py` and ran it
  (`python -m src.preprocessing.build_crosscodeeval_split`). It rebuilds file text
  as `prompt + groundtruth + right_context`, dedupes by (repo, path), keeps repos
  with >= 3 files, and splits each repo's files by file with a fixed seed (42,
  per-repo). Targets: TEST about 27.5%, NEW about 17.5% (only repos with >= 5 files),
  at least 2 BASE and 1 TEST per repo.
  Outputs in `data/processed/crosscodeeval/`: `files.jsonl` (with text),
  `manifest.jsonl` (repo, path, split), `examples.jsonl` (task_id, repo, path, split).
- **Assertions that passed:** splits are disjoint (no TEST file in BASE or NEW);
  every example's target file has a split; per-repo minimums hold; NEW only
  appears in repos with >= 5 files; the line-number reconstruction check holds on
  all 2,665 examples.
- **Found:**
  - 1,368 distinct files; 0 duplicate (repo, path) keys had conflicting text.
  - 206 of 471 repos kept (matches Entry 3).
  - Files: BASE 618, NEW 100, TEST 273 (991 total).
  - Examples by target file: BASE 1,259, NEW 216, TEST 543.
  - BASE is 62% of files, a bit above the plan's 50 to 60%, because the 3- and
    4-file repos have no NEW. NEW is 10% overall for the same reason.
- **A3 coverage, TEST examples only (the real numbers behind Entry 4's upper bound):**

  | Condition | TEST examples with >= 1 relevant file in pool |
  |---|---|
  | Main (pool = BASE) | 292 of 543 (53.8%) |
  | Staleness (pool = BASE + NEW) | 327 of 543 (60.2%) |

  68 TEST examples have a relevant file in NEW. Only 339 TEST examples are in
  repos that have NEW files at all.
- **Not done:** the fine-tuning corpus (cut points inside BASE lines), the
  "test groundtruth not in the fine-tuning corpus" assertion, and the optional
  snippet enrichment. These need the corpus to exist first. The seed is a
  constant in the script, not yet in `config.yaml`.
- **Impact on the thesis:** the staleness analysis rests on roughly 68 TEST
  examples, and the main retrieval metrics on 292. Report these sample sizes (plan
  Section 3 already says to).

## Entry 8: CrossCodeEval fine-tuning corpus and Section 4 assertions (Sections 3, 4, 5)
- **Asked:** proceed with the next step after the split, and keep this log updated.
- **Done:** wrote `src/preprocessing/build_crosscodeeval_finetune.py` and ran it
  (`python -m src.preprocessing.build_crosscodeeval_finetune`). It builds the
  System B corpus from **BASE files only**, pooled across repos (one adapter per
  dataset). Outputs in `data/processed/crosscodeeval/finetune/`:
  `train.jsonl` and `val.jsonl` (`input` / `output`, the format
  `src/finetuning/dataset.py` reads), plus line-aligned `train_meta.jsonl` and
  `val_meta.jsonl` (repo, path, split, line_no) for provenance.
- **Design choices (override if you disagree):**
  - Cut point: right after a `.` (member access) inside a line; input = file prefix,
    output = rest of the line. I checked the benchmark first: all 2,665 CrossCodeEval
    prompts end in `.`, and no groundtruth starts with a space. This matches the
    plan's "cut points inside lines" and keeps train and test formats aligned.
  - Skipped comment lines and `import` / `from` lines.
  - Up to 20 cut points per BASE file, at most one per line, seed 42, per-file seed.
  - Prefix is truncated to the last 1,500 characters, to fit the 512-token limit in
    `config.yaml` (`max_seq_length`).
  - Validation = about 10% of the sampled lines, taken from the same BASE files but
    different target lines than training. This follows the plan ("from BASE files,
    never from TEST"). It is not file-held-out, so validation loss will be
    optimistic; use it for monitoring and early stopping only.
  - Input and output are kept raw (no `.strip()`), unlike the old
    `prepare_datasets.py`, because stripping would remove meaningful trailing
    characters of a mid-line prefix.
- **Assertions that passed (Section 4):** every example comes from a BASE file; no
  TEST path and no NEW path anywhere in the corpus; train and validation share no
  target line; no TEST groundtruth appears as a corpus output, and no TEST
  groundtruth of >= 20 characters appears inside any corpus input.
- **Found:**
  - 618 BASE files -> train 9,378, validation 1,059.
  - 7 candidate examples were dropped because they contained a TEST groundtruth
    string (see rule above). This is the measured size of the content-overlap issue.
  - Median input is about 1,455 characters (mostly at the 1,500 cap), median output
    22 characters (benchmark groundtruth median is 33). No empty outputs.
- **Not done / open:**
  - Short TEST groundtruths (< 20 characters) are only checked as exact corpus
    outputs, not as substrings of inputs. Substring checks on short strings would
    drop too much, since they match common code.
  - Optional snippet enrichment (plan Section 3, step 3) is not built.
  - Section 5 mentions a RAFT-style variant (fine-tuning with retrieval-formatted
    prompts). Not built; needs the retrieval pipeline first.
  - Seeds and these constants are in the scripts, not in `config.yaml`.
  - Plan Section 4 items for RepoBench are untouched.

## Entry 9: Missing import in the hybrid pipeline (Section 5; Section 9, step 3)
- **Asked:** fix the missing import in the hybrid pipeline.
- **Cause:** `src/finetuning/trainer.py` saves only the LoRA adapter
  (`model.save_pretrained` on a PEFT model), but `src/hybrid/pipeline.py` loaded
  that folder with plain `AutoModelForCausalLM` and never imported `peft`.
- **Done:** in `src/hybrid/pipeline.py`, added `from peft import PeftModel` (plus
  `json` and `Path`). The pipeline now reads `base_model_name_or_path` from the
  adapter's `adapter_config.json`, loads that base model (4-bit if enabled), and
  attaches the adapter with `PeftModel.from_pretrained`.
- **Verified:** the module imports cleanly (`peft` 0.20.0 is installed). **Not
  verified:** an actual model load or generation, since no adapter has been
  trained yet.
- **Same problem elsewhere, not fixed:** `build_generator` in
  `experiments/run_comparison.py` also loads the adapter folder directly (and
  without 4-bit). It is a different code path (the hybrid there does not use
  `HybridPipeline`) and its prompt format differs from the training format in
  `src/finetuning/dataset.py`. Leave until the evaluation wiring is reworked.

## Entry 10: RepoBench pool and BASE/NEW/TEST split (Sections 2, 3, 4)
- **Asked:** do the same split for RepoBench after the hybrid import fix.
- **Checked first (read-only):** the two cross-file settings overlap heavily: 1,530
  shared repos, 2,418 shared target files, and only 112 identical examples. So a
  separate split per setting would let a file be TEST in one and BASE in the other.
- **Done:** wrote `src/preprocessing/build_repobench_split.py` and ran it
  (`python -m src.preprocessing.build_repobench_split`). One shared split for both
  settings, one manifest. Outputs in `data/processed/repobench/`: `manifest.jsonl`,
  `pool.jsonl` (BASE and NEW fragments only), `examples.jsonl` (setting, row index
  into `data/repobench/<setting>`, repo, path, split, level, gold path). Results are
  still reported per setting; examples are not pooled across settings.
- **Design choices:**
  - File universe per repo = target files plus snippet source files (plan Section 3:
    "from context snippets and the code field").
  - Only target files can be TEST (a snippet-only file has no next line to predict).
  - Pool entries are fragments, deduplicated by (repo, path, text): a `prefix`
    (the longest `all_code` seen for a target file) or a distinct `snippet`.
  - TEST files are kept out of the pool by path AND by content (a fragment contained
    in a TEST file's text is dropped). 277 fragments were dropped by the content
    filter.
  - Same rules as CrossCodeEval: seed 42, repos with >= 3 files, NEW only for repos
    with >= 5 files, at least 2 BASE and 1 TEST file, TEST about 27.5% of files.
- **Assertions that passed:** TEST files are all target files; no TEST path and no
  TEST content in the pool; every example's file is in the manifest; per-repo
  minimums hold; NEW only for repos with >= 5 files.
- **Found:**
  - 1,826 of 1,970 repos kept (>= 3 files).
  - Files: BASE 12,649, NEW 3,482, TEST 5,330 (TEST is 24.8% of files).
  - Pool: 31,140 fragments (BASE: 1,046 prefixes + 23,562 snippets; NEW: 304
    prefixes + 6,228 snippets).
  - TEST examples: cross_file_first 6,276, cross_file_random 6,035. Because only
    target files can be TEST, about 78% of all target files are TEST and few target
    files remain in BASE.
  - Gold-file coverage for TEST examples (gold = file of `context[gold_snippet_index]`,
    must be in the pool and not the example's own file):

    | Setting | TEST examples | Gold in BASE (main) | Gold in BASE+NEW (staleness) | Gold in NEW |
    |---|---|---|---|---|
    | cross_file_first | 6,276 | 4,399 (70.1%) | 5,642 (89.9%) | 1,243 |
    | cross_file_random | 6,035 | 4,298 (71.2%) | 5,452 (90.3%) | 1,154 |

    Excluded from retrieval metrics: 2 (first) and 6 + 1 own-file (random) with no
    valid gold.
- **Impact on the thesis:** RepoBench has far more test examples than CrossCodeEval
  (12k vs 543) and a much larger staleness sample (about 1,200 per setting vs 68).
  Plan Section 9, step 8 already allows a smaller RepoBench sample if GPU time is
  tight; a sampling rule (seeded) is not defined yet.

## Entry 11: RepoBench fine-tuning corpus and Section 4 assertions (Sections 3, 4, 5)
- **Asked:** (part of "the same split" for RepoBench) mirror the CrossCodeEval
  corpus step.
- **Done:** wrote `src/preprocessing/build_repobench_finetune.py` and ran it
  (`python -m src.preprocessing.build_repobench_finetune`). Built from **BASE pool
  fragments only**, one corpus for RepoBench (both settings). Outputs in
  `data/processed/repobench/finetune/`: `train.jsonl`, `val.jsonl` (`input` /
  `output`) and line-aligned `train_meta.jsonl`, `val_meta.jsonl`.
- **Design choices (override if you disagree):**
  - Task format matches RepoBench: cut at a line boundary, input = lines before the
    cut, output = the full next line. Skipped blank, very short (< 8 chars) and
    comment lines; at least 2 lines of context.
  - Up to 8 cuts per `prefix` fragment and 1 per `snippet` fragment, seed 42.
  - Deduplicated identical (input, output) pairs, then a **seeded subsample to
    12,000 examples** (10% validation) to keep training cost near the CrossCodeEval
    corpus. The cap is a compute-matching choice, not from the plan.
  - Prefix capped at the last 1,500 characters (512-token limit in `config.yaml`).
  - Raw text kept, no `.strip()`.
  - Validation is different examples from the same BASE fragments (plan: "from BASE
    files"); like CrossCodeEval, not file-held-out, so use it for monitoring only.
- **Assertions that passed:** every example comes from a BASE file; no TEST path;
  no TEST `next_line` appears as a corpus output (exact match, any length); no TEST
  `next_line` of >= 20 characters appears inside an input; train and validation
  share no example.
- **Found:**
  - 27,586 candidates -> 26,815 unique -> 12,000 used: train 10,800, validation
    1,200 (3,253 from prefix fragments, 8,747 from snippet fragments).
  - 115 candidates dropped for matching a TEST next line exactly (9 of them short,
    < 20 characters). This is the measured size of the content-overlap issue.
  - Median input about 538 characters, median output 41. Inputs are much shorter than
    CrossCodeEval's because snippets are short fragments.
- **Not done / open:**
  - Short TEST next lines are not checked inside inputs (same reasoning as Entry 8).
  - RepoBench has no counterpart to the optional CrossCodeEval snippet enrichment.
  - A sampling rule for the very large RepoBench TEST set is not defined.
  - Constants and seeds live in the scripts, not `config.yaml`.
- **Status of Section 3 / Section 9 step 4:** both datasets now have a split
  manifest, a pool and a leakage-checked fine-tuning corpus. The old
  `src/preprocessing/prepare_datasets.py` is not used by these scripts and still
  carries the outdated design (Entry 5).

## Notes for thesis writing (author's reference; no results yet)
Collected from plan Sections 7, 8, 10, 12 and from facts found in Entries 3 to 11.
New points are added as bullets under "Added later" at the end of this section's
later entries, so check later entries for the tag `[writing note]`.

**Hypotheses to write down before any experiment runs (plan Section 7):**
- H1: hybrid > RAG-only > FT-only on cross-file-dependent examples.
- H2: the hybrid's gain shrinks when retrieval quality is high.
- H3: FT-only degrades most on NEW files and unseen code.
- H4 (low-data): with few files per repo, fine-tuning adds little relative to RAG.
  A legitimate finding either way.

**Expected vs Wang et al. (2025), to fill in (plan Section 7):** record their
findings, then your predictions, and say where you expect to match or differ.
- Their findings: RAG with suitable retrieval beats fine-tuning alone; the
  combination is best; BM25 beat dense embedders (UniXcoder, CodeT5) on C++;
  retrieval greatly increases input length and cuts throughput while fine-tuning
  costs upfront training but no runtime latency; fine-tuning degraded general code
  generation (forgetting).
- Their setting: one company's C++, about 120,000 files, 0.5B to 7B models.
- Your setting: public Python benchmarks, much smaller per-repo data, 1.5B with QLoRA.

**Objective and application domain (plan Sections 0 and 8):** the decision question
is "given a private repository and a single-GPU budget, which adaptation strategy
should a team choose, and when does the hybrid's extra complexity pay off?" Domain:
developer tooling for private codebases under privacy and GPU constraints.

**Contribution framing (plan Section 8):** the controlled experimental design, the
leakage-safe split construction, and the analysis, not the scripts. Conclusion
format: numeric recommendations with thresholds, not "it depends".

**Data facts you will likely want to cite (from this log):**
- CrossCodeEval: 471 repos, 1,368 target files; 206 repos with >= 3 files, 79 with
  >= 5. After the split: TEST 543 examples; 292 (53.8%) have a relevant file in the
  main pool, 327 (60.2%) under staleness; only 68 have a relevant file in NEW
  (Entries 3, 7).
- Only 27% of CrossCodeEval snippets come from files that are themselves targets, so
  most relevant repository code is simply not available to the pool (Entry 4). This
  supports the "benchmark-derived setting" limitation (plan Section 10).
- RepoBench: both cross-file settings overlap heavily (2,418 shared target files),
  which is why one shared split is used (Entry 10). TEST: 6,276 + 6,035 examples;
  gold file in the main pool for about 70%, in BASE+NEW for about 90%.
- CrossCodeEval prompts always end right after a '.', so training cuts use the
  same format (Entry 8). RepoBench is full next-line prediction (Entry 11).
- Fine-tuning validation is not file-held-out (Entries 8, 11): say so.
- The RepoBench corpus is capped at 12,000 examples to match CrossCodeEval training
  cost (Entry 11): say so, it is a design choice not in the plan.

**Limitations already visible (plan Section 10 plus extras):**
- Pools hold only files that appeared in the benchmarks (full files for
  CrossCodeEval, fragments for RepoBench).
- CrossCodeEval relevance is a proxy rule (Entry 4); the snippet variant used was
  the standard one, with the reference-aware variant as a sensitivity check only.
- Short TEST strings (< 20 characters) are not checked inside corpus inputs.
- Small CrossCodeEval staleness sample (68).

**Defense prep (plan Section 12):** short answers already exist there; this log
supplies the numbers behind them.

## Entry 12: Per-repo FAISS indexes for CrossCodeEval and sanity retrieval (Section 5; Section 1, A6; Section 9, step 5 prep)
- **Asked:** run `build_indexes.py` on one or two repos, check, then all 206 repos, add a
  small sanity retrieval, and log it.
- **Done:**
  - Read `chunker.py::chunk_text` and `src/retrieval/build_indexes.py`; no logic problems found.
  - Test run on two repos (`20171130-llmux-249dcdb`, which has NEW files, and
    `AICPS-RS2G-b4e985f`, which has none): llmux 3 chunks in `main` and 4 in `staleness`;
    AICPS 4 and 4. Matches the manifest.
  - **Bug found and fixed** in `src/retrieval/embedder.py`: UniXcoder reports
    `max_seq_length` 1026 but RoBERTa-style position ids start at `pad_token_id + 1 = 2`,
    so the real limit is 1,024 tokens and a full chunk crashed with
    `index 1026 is out of bounds`. The embedder now caps `max_seq_length` at
    `max_position_embeddings - pad_token_id - 1` (1,024). Longer chunks are truncated.
  - Full run (`python -m src.retrieval.build_indexes`): 206 repos, `main` 806 chunks,
    `staleness` 931 chunks (806 BASE + 125 NEW). Matches the sizing facts. Took about 17 minutes
    on CPU. Output in `data/embeddings/crosscodeeval/<repo>/{main,staleness}/` (gitignored).
  - Wrote `src/retrieval/sanity_check_indexes.py` and ran it: query = last 20 lines of each
    TEST prompt, searched in the example's own repo index.
- **Assertions that passed:** no TEST file in any index, every chunk belongs to its repo,
  `main` holds BASE only, `staleness` holds BASE + NEW only. In the sanity run, 0 TEST
  chunks were retrieved over 543 TEST examples.
- **Found (file-level hit@k vs the A3 rule, examples with >= 1 relevant file):**

  | View | Examples | hit@1 | hit@3 | hit@5 | hit@10 |
  |---|---|---|---|---|---|
  | main | 292 | 0.603 | 0.932 | 0.983 | 1.000 |
  | staleness | 327 | 0.532 | 0.893 | 0.960 | 0.997 |

  The example counts match Entry 7 (292 and 327).
- **Caveat / [writing note]:** these hit rates are inflated. Repos are small (3 to about
  10 chunks in a pool), so top-5 and top-10 cover almost the whole pool. Treat this only as
  a smoke test, not as a retrieval result. The informative numbers will be hit@1/hit@3 and
  P@k / MRR, and BM25 as the comparison. Staleness hit rates are lower because NEW files add
  competing candidates; hypothesis for H3 and the staleness analysis, not a finding yet.
- **Limitation (as expected):** about half of each chunk's tokens are cut at 1,024 tokens
  (median chunk about 1,045). Plan's 256 lines kept; report it.
- **Open:**
  - `rank_bm25` is not installed (needed for step 7).
  - ~~Index build is not yet committed~~ Corrected in Entry 13: `chunker.py`,
    `build_indexes.py`, `embedder.py` and `sanity_check_indexes.py` are already committed
    (commit `57cc604`, working tree clean).
  - Next: the pilot (trainer paths, evaluation wiring, seeded 50-example rule).

## Entry 13: Log fix, rank_bm25, and the seeded pilot sample (Section 9, step 5)
- **Asked:** fix the stale "uncommitted" line in Entry 12, install `rank_bm25`, then do item 3
  (the seeded rule for the 50 pilot examples).
- **Done:**
  - Entry 12's "not yet committed" line corrected: the index files are in commit `57cc604`
    and the working tree was clean.
  - Installed `rank_bm25` in `./venv` (import checked). Needed for the BM25 baseline (step 7).
  - Wrote `src/preprocessing/build_crosscodeeval_pilot.py` and ran it
    (`python -m src.preprocessing.build_crosscodeeval_pilot`). Candidates = TEST examples with
    >= 1 relevant file in the BASE pool (A3 rule, Entry 4). Draw = 50 with `random.Random(42)`
    from the sorted candidates. Output: `data/processed/crosscodeeval/pilot_ids.json`
    (task_ids, gitignored).
- **Assertion that passed:** candidate count is exactly 292, matching Entry 7.
- **Found:** 50 pilot examples from 40 repos; 37 of the 50 are in repos that have NEW files.
- **Notes:**
  - The sample is plain random, not stratified. Choosing from the 292 main-condition candidates
    means retrieval metrics are defined for every pilot example, but the staleness view's extra
    examples are not selected for.
  - [writing note] The pilot is a pipeline check, not a result; 50 examples are too few to
    compare systems.
  - Seed and N are constants in the script, not `config.yaml`.
- **Open / next:** point `trainer.py` at `data/processed/crosscodeeval/finetune/{train,val}.jsonl`,
  then rework evaluation wiring in `experiments/run_comparison.py` (prompt format, adapter
  loading per Entry 9, per-repo indexes, reading `pilot_ids.json`).

## Entry 14: Metrics review and revised order of work (Sections 6, 9)
- **Asked:** how a demo would work and how metrics are checked; then add a CodeBLEU check and
  first-line truncation to the evaluation rewiring, with `demo.py` after the trainer fix.
- **Done:** read-only review of `src/hybrid/pipeline.py` and `src/evaluation/metrics.py`; no code
  changed. Order of work recorded here.
- **Found:**
  - `code_bleu` in `metrics.py` catches every exception and returns 0.0. Loading
    `evaluate.load("code_bleu")` fails ("Module 'code_bleu' doesn't exist on the Hugging Face Hub"),
    so CodeBLEU would currently always be reported as 0.0 without any warning.
  - No adapter exists yet (no `adapter_config.json` anywhere; `experiments/finetuned_model` absent).
  - `torch.cuda.is_available()` is False on this machine. `load_in_4bit: true` (config) needs a GPU.
  - Predictions are not yet truncated to the first line before scoring.
- **Order of work:** (1) `trainer.py` -> new corpus paths; (2) `demo.py` (base / RAG / FT / hybrid side by
  side for a repo + snippet); (3) evaluation rewiring in `run_comparison.py`, including a CodeBLEU
  check that raises instead of returning 0.0 (and a replacement implementation, e.g. the
  `codebleu` PyPI package, to be chosen with the user) and first-line truncation of predictions.
- **[writing note]** Say which CodeBLEU implementation was used and that predictions were cut to the
  first line before scoring.

## Entry 15: Trainer fix and demo script (Section 9, step 5 prep)
- **Asked:** do the trainer fix, then write the demo.
- **Done (nothing trained or generated yet):**
  - `src/finetuning/trainer.py`: reads `data/processed/<dataset>/finetune/{train,val}.jsonl`
    (new `--dataset crosscodeeval|repobench`, default crosscodeeval); saves to
    `<finetuning.output_dir>/<dataset>/` (one adapter per dataset). Changed
    `evaluation_strategy` to `eval_strategy` (transformers 5.15 no longer accepts the old name).
  - `src/finetuning/dataset.py`: `load_jsonl` now reads UTF-8 explicitly (the Windows default
    codec would misread the corpus).
  - Wrote `src/demo.py` (`python -m src.demo`): base / rag / ft / hybrid side by side, using the
    training prompt format; retrieved chunks are prepended to the input as comments (each cut to
    1,200 chars). Takes `--task-id` (shows ground truth and the example's split) or `--repo` with
    `--code`/`--code-file`; `--adapter` enables ft and hybrid (base/rag use `disable_adapter()`).
    Validates the repo name against existing index folders.
  - Checked: the corpus loads through `build_dataset` (train 9,378, validation 1,059); `--help` and
    `build_prompt` work. The model has not been loaded or run.
- **Found / open (not changed, need your decision):**
  - `bitsandbytes` is not installed and there is no GPU, so QLoRA training cannot run here.
  - `dataset.py` tokenization sets labels = the whole prompt (instruction and input as well as the
    output) and pads to max_length with pad = eos, so the loss includes prompt and padding tokens.
    Truncation at 512 tokens could also cut the response end. Recommend masking prompt/pad labels
    with -100 so the model learns only the completion. Not changed yet.
  - The training format has no end-of-sequence token after the output, and no retrieval context.
    The hybrid therefore sees a prompt format (context in the input) it was not trained on;
    the plan's RAFT-style variant (Entry 8) would address this. [writing note]
  - `HybridPipeline` (src/hybrid/pipeline.py) uses a different prompt format from the demo and
    from training; to be unified in the evaluation rewiring.

## Entry 16: Colab GPU setup and trainer resume (Section 9, step 5 prep)
- **Asked:** set up Colab (used for GPU work only), explain the steps, make progress survive
  disconnects, and avoid manual uploads. The repo is public (confirmed by the user), so Colab
  clones it without a token.
- **Done (nothing run on Colab yet; the two Python files were only syntax-checked locally):**
  - `tools/colab_setup.py` (new, standard library only): checks Drive and GPU, installs pinned
    libraries (transformers 5.15.0, peft 0.20.0, accelerate 1.14.0, datasets 5.0.1,
    sentence-transformers 5.7.0, faiss-cpu 1.15.0, rank_bm25 0.2.2, Levenshtein 0.27.4, plus
    bitsandbytes unpinned), links `experiments/finetuned_model` and `results/` to
    `MyDrive/thesis/outputs/`, and gets the data. Data comes from a Drive cache
    (`MyDrive/thesis/cache/<dataset>_data.tar`) if present; otherwise it downloads the public
    benchmarks, re-runs the seeded split / corpus / pilot / index scripts, and writes the cache.
    The tar is written under a temporary name and renamed only when complete; extraction uses
    the `data` filter. Afterwards it compares corpus sizes with this log and prints `DIFFERS`
    on a mismatch (warning only).
  - `src/finetuning/trainer.py`: checkpoints every 100 steps (keeps the last 2) instead of per
    epoch, and resumes automatically from the latest checkpoint in the output folder. New
    `--no-resume` flag starts over.
  - `docs/colab_steps.md` (new): beginner-level guide (Part 0 to 5 plus troubleshooting) for
    pushing, GPU runtime, the three setup cells, training, saving, and returning later.
- **Design choices (override if you disagree):**
  - Data is rebuilt on Colab rather than uploaded, to avoid manual uploads; the cache means the
    slow build happens once. The alternative is uploading a ~140 MB zip of `data/processed/`
    and `data/embeddings/` to Drive, which guarantees identical data.
  - Commits and pushes stay on the local machine; nothing is pushed from Colab, so no GitHub
    credentials are needed there. No secrets are used anywhere in the setup.
- **Not verified / risks:**
  - The rebuilt data is expected to match the local data (fixed seeds), but this is unproven:
    the benchmark mirrors on Hugging Face could have changed. The size check is the safeguard.
  - The pinned versions are those installed locally; they have not been tried on Colab and one
    may need relaxing. Local torch is 2.13.0; the script does not touch Colab's torch.
  - `bitsandbytes` on a T4 and the 4-bit load have not been run anywhere yet.
  - Resume has not been exercised. If it works, the checkpoint folder on Drive is the only
    state needed.
- **Open / next:**
  - Commit and push the three files (waiting for the user's go-ahead), then run Part 0 to 2 of
    `docs/colab_steps.md` and report the data-check output.
  - Then the code fixes already listed in Entries 14 and 15: mask prompt/padding labels with -100
    and add EOS in `dataset.py`; unify the prompt format across training, demo and
    `HybridPipeline` (RAFT-style variant for the hybrid); replace the silent CodeBLEU; rewire
    `experiments/run_comparison.py`. The first Colab training run is only a smoke test until
    these are done.
  - The progress report (.docx, August) is out of date: it describes the 80/10/10 split by
    repository with both datasets mixed, says the hybrid import was already present (Entry 9
    found it missing), and calls the remaining work "mostly execution". Plan Section 11 already
    says to tell the supervisor about scope changes.
  - `docs/session_prompt` (the new-session prompt) is untracked and not part of this commit.
  - [writing note] Compute setup for the thesis: Colab T4 (16 GB) for training and evaluation
    runs, QLoRA 4-bit; state this in the limitations and cost discussion.


## Entry 17: Reference-paper analysis, retrieval comparison script, training/evaluation fixes (Sections 5, 6, 7, 9)
- **Asked:** (1) a comparison with the main reference paper for the committee, (2) a retrieval-only comparison
  (dense vs BM25) with plots that needs no training, (3) the code fixes listed in Entries 14 and 15, and
  (4) Colab steps for the training-curve plot, to be done once data exists. Written while the first Colab
  training run (old code) was still running.
- **Done (1), `docs/reference_paper_comparison.md`:** read Wang et al. (arXiv 2505.15179) in full from the
  PDF and wrote a side-by-side table, their findings with numbers, predictions per finding, and a fairness
  note. Findings that matter for the thesis:
  - They used 163,746 C++ files in total; 120,000 form the retrieval database and the fine-tuning data;
    test = 50,000 next-line instances from 20,000 other files. The plan's "about 120,000 files" is the
    retrieval/fine-tuning subset, not the whole set.
  - Six models including **Qwen2.5-Coder-1.5B**, the thesis model. Their 1.5B numbers (EM / edit sim / BLEU):
    base 24.48 / 60.78 / 41.47; BM25 RAG 55.81 / 77.26 / 68.35; UniXcoder RAG 41.47 / 70.08 / 55.77;
    fine-tuning 44.63 / 74.12 / 60.50.
  - Full fine-tuning on 8 x A100 80 GB (lr 5e-6), not QLoRA. Metrics are EM, ES, BLEU only: no P@k, R@k,
    MRR, no identifier accuracy, no staleness test, no per-repository split.
  - BM25 was the best retriever; CodeBERT embeddings gave almost no gain over no retrieval; RAG + fine-tuning
    beat either alone (averages over six models, e.g. BM25: EM 53.76 -> 57.43); fine-tuning plateaus beyond
    about 90,000 files while RAG keeps improving; fine-tuning cut HumanEval pass@1 by 24.1% on average.
  - Per-model table cells were read from a two-column PDF; alignment cross-checked but marked [CHECK] in the
    document. Do not compare absolute scores with this thesis (different language, scale, task, metrics).
- **Done (2):** wrote `src/retrieval/compare_retrievers.py` (dense / BM25 / random over the same chunks,
  hit@k, P@k, R@k, MRR with 95% bootstrap CIs, paired dense-minus-BM25 differences, a staleness subset of
  examples whose relevant file is in NEW, leakage abort) and `src/evaluation/plot_retrieval_comparison.py`
  and `src/evaluation/plot_training.py` (loss curve from `trainer_state.json`). **Not run**: it needs the
  indexes and was left for your go-ahead. Expected counts when run: 292 main, 327 staleness.
- **Done (3), code fixes:**
  - `src/prompting.py` (new): one prompt format for training, demo, hybrid and evaluation (same text as the
    first training run, so nothing about the prompt changed). `src/generation.py` (new): shared model loading
    and greedy one-line generation. `src/demo.py` and `src/hybrid/pipeline.py` now use them; the hybrid's
    separate prompt template and sampling (temperature 0.2) are gone.
  - `src/finetuning/dataset.py`: loss on the output and an end-of-sequence token only (prompt and padding are
    -100); the prompt is tokenised as one string as at inference; over-long inputs are cut from the left so
    the output is never cut; a hard length limit. `TRAINING_VERSION = 2`.
  - `src/finetuning/trainer.py`: `--run-name`; refuses to resume or mix checkpoints from older training code
    (the first Colab run is version 1; use `--run-name v2`).
  - `src/evaluation/metrics.py`: CodeBLEU now comes from the `codebleu` package and raises if it is missing
    or fails (no silent 0.0); `--skip-codebleu` records null; added `bootstrap_ci`; EM and ES now carry
    95% CIs. `src/evaluation/evaluator.py`: added the `base` system, n/a for missing values.
  - `experiments/run_comparison.py` rewritten: pilot_ids.json or all TEST examples, per-repo indexes, shared
    prompt and generation, one model loaded with the adapter switched off for base and RAG, predictions cut to
    the first line, A3 retrieval metrics per view, per-example `predictions.jsonl`. `main.py compare` forwards
    to it (its `evaluate` stub still reflects the old design and was left alone).
  - `tools/colab_setup.py`: also installs matplotlib and, best effort, `codebleu` and `tree-sitter-python`.
- **Verified:** 19 tests pass (new `tests/test_dataset.py` with a stub tokenizer, new metric tests); all
  changed modules import. With the real Qwen tokenizer on the first 400 training examples (max length 512):
  median 8 tokens carry loss (max 52), the end token is present in all 400, median sequence 330 tokens, and
  36 of 400 (9%) have their input cut from the left. The earlier code spent the loss on the whole padded
  512-token sequence, so the first Colab run's loss values are not comparable and its adapter is not a
  result.
- **Not verified:** nothing has been run on a GPU; `run_comparison.py` has only been import- and
  `--help`-checked; the `codebleu` package API and its install next to the pinned tree-sitter are untested.
- **Open / decisions for you:**
  - Run `compare_retrievers.py` (CPU, a few minutes) and look at the plots.
  - Retrain with `--run-name v2` on Colab, then the pilot (`docs/colab_steps.md`, Parts 3 to 3d).
  - RAFT-style training (retrieval-formatted prompts) is still not built: B trains without context, so C
    and A see retrieved chunks the adapter never saw in training. It needs a corpus builder that retrieves
    from BASE excluding the example's own file; decide whether to build it before the pilot or after.
  - Memory per system is not independent in `run_comparison.py` (one process, adapter stays loaded).
  - 9% of training inputs are shortened to fit 512 tokens; consider 768 or 1,024 if the T4 allows.
  - Plan wording: change "about 120,000 files" to "163,746 files, 120,000 as retrieval/fine-tuning corpus".
  - [writing note] Differences from Wang et al. belong in the research-gap table: retrieval-quality metrics,
    staleness test, QLoRA on one GPU, per-repository file-level split, public Python. Their forgetting result
    (-24.1% HumanEval) sets what to compare the thesis forgetting check against.

## Entry 18: First v2 fine-tuning run (CrossCodeEval), output analysed (Sections 5, 9; training)
- **Asked:** analyse the output of the first complete v2 run (`docs/first_train_results`) and give next steps.
- **Correction to earlier replies:** the run described in earlier replies as "the old run (version 1)" was this
  v2 run (adapter folder `v2`, identical numbers). The advice to stop it was wrong; the statement that the v2
  loss would start higher than v1 was also wrong. Nothing in the repo was affected.
- **Run facts (read from the output):** Qwen2.5-Coder-1.5B, QLoRA 4-bit, 1,089,536 trainable parameters
  (0.0705% of 1,544,803,840), 9,378 training and 1,059 validation examples, 3 epochs, 1,761 steps, effective
  batch 16. Started 2026-11-19 08:59, adapter saved 12:29. Training time 12,570 s (3 h 29 min), about 5.1 s/step
  and 2.24 samples/s on a Colab T4; GPU memory about 8.7 GB as shown by Colab (peak was not measured by the
  code). Adapter: `experiments/finetuned_model/crosscodeeval/v2` on Drive.
- **Loss (loss is now on the answer tokens and the end token only):** logged every 50 steps. Mean of the
  logged values: epoch 1 about 0.78 (1.14 at step 50, 0.80 at step 100), epoch 2 about 0.67, epoch 3 about 0.62;
  mean over the whole run 0.688. Validation loss at the end of each epoch: 0.6799, 0.6774, 0.6841.
  grad_norm stayed between about 0.65 and 2.1, no spikes, no nan. Learning rate decayed linearly from 2e-4 to
  about 1e-6.
- **Reading:** most of the learning happens in the first 100 to 200 steps. Training loss keeps falling in
  epochs 2 and 3 but validation loss is flat (0.680, 0.677, 0.684; differences of 0.003 to 0.007 are probably
  noise) and is slightly higher after epoch 3 than epoch 2. So epochs 2 and 3 add little, and the data may be
  starting to be memorised. Validation is NOT file-held-out (Entries 8, 11), so it is optimistic: a flat
  validation loss on this easier set suggests little to gain from more epochs on this corpus. This fits H4
  (low data, little gain from fine-tuning) but is not evidence for it yet. [writing note]
- **Missing for a conclusion:** the base model's loss on the same validation set. Without it there is no
  proof that fine-tuning improved anything; the pilot comparison and a base-versus-adapter validation loss are
  the way to find out.
- **Warnings in the output:**
  - Out-of-memory message during the first evaluation (tried to allocate 2.49 GB with 1.12 GB free of
    15.6 GB). PyTorch recovered; evaluation finished all 133 steps and training continued. Cause is the large
    default evaluation batch (8 sequences of up to 512 tokens against a 151k-token vocabulary). Not a failure,
    but lower `per_device_eval_batch_size` (for example 2) if it ever turns into a crash.
  - "Unauthenticated requests to the HF Hub": harmless here (public models). If a token is ever used it must
    be kept in Colab Secrets, never in code or logs.
- **Cost figures for the thesis (efficiency section):** QLoRA fine-tuning of the 1.5B model on one T4:
  about 3.5 hours, about 8.7 GB. Wang et al. report 4.6 hours and 31.5 GB for full fine-tuning of the same
  model on 8 x A100 80 GB, with a far larger training set, so compare memory, not hours.
- **Open / next:** check the adapter files on Drive; plot the loss curve from `trainer_state.json`; demo on
  one pilot example; `run_comparison --limit 5`; pilot (main and staleness); base-versus-adapter validation
  loss (script not written yet); decide on the number of epochs for later runs (2 would save about a third of
  the training time).

## Entry 19: GPU quota used up after v2; plan for the pilot; validation-loss script (Sections 6, 9)
- **Asked:** after the v2 run the free Colab GPU time ran out and `ls experiments/finetuned_model/crosscodeeval/v2`
  failed; write the next steps (local versus Colab, including the pilot), save the findings so far, and say what
  to do next.
- **Cause of the `ls` error (explained, not yet confirmed on Drive):** the path is a link that
  `tools/colab_setup.py` creates to `MyDrive/thesis/outputs/` in each session; the new CPU session had not run
  it, so the link did not exist. The adapter should be at
  `/content/drive/MyDrive/thesis/outputs/finetuned_model/crosscodeeval/v2`. **Not yet verified.** If it is not
  there, the adapter may have been lost with the session and training would have to be repeated; the steps to
  check this are in `docs/colab_steps.md`, Part 7.0.
- **Done:**
  - `docs/colab_steps.md`, new Part 7: why the error happened, what can be done now without a GPU (local versus
    Colab table), the one-session order for when the GPU returns (quick checks, pilot main, validation loss,
    pilot staleness, results download, disconnect), and a plain-language description of the pilot.
  - `src/finetuning/eval_loss.py` (new): validation loss of the base model and of the adapter on the same
    validation set, loss on answer tokens only, small batch (2) to avoid the out-of-memory message seen in
    training evaluation, writes `results/val_loss_base_vs_adapter.json`. Only `--help` was checked; it has not
    been run (needs a GPU, or a very slow CPU run).
  - `.gitignore`: `*.safetensors` and `experiments/finetuned_model/` added so that adapters and checkpoints
    cannot be committed by accident (the adapter is about 4 MB; the checkpoints are larger).
- **Findings so far (summary for the thesis; all from Entries 3 to 18):**
  - Data: file-level BASE/NEW/TEST splits with passing leakage checks for CrossCodeEval and RepoBench;
    CrossCodeEval TEST 543 examples, 292 (53.8%) with a relevant file in the main pool, 327 (60.2%) in the
    staleness pool, only 68 with a relevant file in NEW; RepoBench TEST 6,276 + 6,035 examples with the gold file
    in the main pool for about 70%.
  - Index smoke test (inflated, small pools): hit@1 0.603 (main), 0.532 (staleness) against the A3 rule.
  - Reference paper (Wang et al.): their numbers for Qwen2.5-Coder-1.5B and the differences from this thesis are
    in `docs/reference_paper_comparison.md`.
  - Fine-tuning v2 (CrossCodeEval, QLoRA 1.5B): 3 epochs, 1,761 steps, 3 h 29 min on a T4, about 8.7 GB;
    training loss about 0.78 / 0.67 / 0.62 per epoch, validation loss 0.680 / 0.677 / 0.684 (flat; not
    file-held-out). No evidence yet that fine-tuning helps; that needs the base-versus-adapter comparison and the
    pilot.
  - Not yet available: any completion-quality number (EM, edit similarity) for any system, any retrieval
    comparison (dense versus BM25) result, any staleness or hit/miss result.
- **Next (in order; where each runs is in `docs/colab_steps.md`, Part 7):**
  1. Colab CPU session: check the adapter on Drive.
  2. Local: download the adapter files and `trainer_state.json`; plot the loss curve; run the retrieval
     comparison (dense / BM25 / random) and its plots.
  3. Local: push the newest code (`eval_loss.py`, `.gitignore`).
  4. Colab T4 when the quota returns: quick checks, pilot (main), validation-loss comparison, pilot (staleness),
     download results, disconnect.
  5. Local: analyse results, update the log, presentation and report prompt.
- **Open:** the number of epochs for later runs (2 may be enough); whether to build the RAFT-style variant;
  memory per system is not independent in the evaluation script; a local CPU test of the evaluation code
  would need the free RAM and disk figures of this machine (a read-only check of them was not permitted, so I
  did not run it).
- **[writing note]** Training cost for the efficiency section: about 3.5 hours and 8.7 GB for QLoRA on a free
  T4; the free GPU quota ran out after one such run, which is a practical constraint worth stating.
