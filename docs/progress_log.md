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

## Entry 20: Loss curve and first retrieval comparison, run locally (Sections 5, 6)
- **Asked:** after the adapter files and `trainer_state.json` were placed locally (adapter in
  `experiments/finetuned_model/crosscodeeval/v2/`, state in `results/training/`; both gitignored), run the
  loss plot and the retrieval comparison, update the log. No commits or pushes (user does those).
- **Done (CPU only):**
  - `python -m src.evaluation.plot_training --run results/training/trainer_state.json` ->
    `results/figures/training_loss.png` (35 training points, 2 validation points).
  - `python -m src.retrieval.compare_retrievers` and `python -m src.evaluation.plot_retrieval_comparison` ->
    `results/retrieval_comparison.json` and four figures in `results/figures/`.
- **Checks that passed:** TEST files retrieved = 0 over 543 TEST examples; n = 292 (main), 327 (staleness),
  68 (staleness, relevant file in NEW). Matches Entries 7 and 12.
- **Found (dense = UniXcoder, 95% bootstrap CI in brackets; relevance by the A3 rule):**

  | View (n) | System | hit@1 | hit@3 | MRR |
  |---|---|---|---|---|
  | main (292) | dense | 0.603 | 0.952 | 0.770 [0.737, 0.804] |
  | main (292) | BM25 | 0.784 | 0.990 | 0.884 [0.860, 0.908] |
  | main (292) | random | 0.397 | 0.849 | 0.633 [0.596, 0.672] |
  | staleness (327) | dense / BM25 / random | 0.532 / 0.771 / 0.355 | 0.896 / 0.963 / 0.728 | 0.720 / 0.870 / 0.572 |
  | staleness, NEW-relevant (68) | dense / BM25 / random | 0.544 / 0.809 / 0.353 | 0.868 / 0.941 / 0.677 | 0.716 / 0.885 / 0.553 |

  Paired difference dense minus BM25 (main): hit@1 -0.182 [-0.250, -0.113], MRR -0.114 [-0.152, -0.075].
  Both CIs exclude 0, so BM25 is better here. This agrees in direction with Wang et al. (BM25 > UniXcoder).
  On the 68 NEW-relevant examples the hit@3 difference's CI includes 0 (-0.074 [-0.162, 0.015]); hit@1 and MRR do not.
- **Caveats [writing note]:** pools are tiny (3 to about 10 chunks), so random already gets hit@3 0.85 and hit@5
  0.98; only hit@1, MRR and the gap to random are informative. Dense is above random but not by much at hit@1
  (0.603 vs 0.397). Possible reasons (untested): UniXcoder truncates about half of each 256-line chunk (Entry 12),
  and BM25 matches identifiers directly. Retrieval quality is not completion quality; that needs the pilot.
- **Unexpected, to check:** `trainer_state.json` has global_step 1761 and epoch 3.0 but only two validation
  points (steps 587 and 1174: 0.6799, 0.6774). The third value (0.6841) in Entry 18 came from the training
  output, not from this file, so the file was probably saved before the final evaluation. Not a problem for
  the plot, but the curve shows two validation points, not three.
- **Not done:** the local CPU smoke test of the evaluation code (needs the free-RAM figure from the user; see
  Entry 19). Nothing committed or pushed.

## Entry 21: Status check before the first pilot; what is done, what is missing (Sections 6, 9)
- **Asked:** can the pilot run on Colab once the runtime is back, what to do in the first pilot run, summarise
  what is done and add anything missing. Also answered: free RAM on this machine is about 8 GB and D: has over
  40 GB free, so the 32-bit local model test (about 8 to 10 GB) was NOT run (the weights alone are about
  6.2 GB in 32-bit). Options given to the user: skip, test everything except the model, or bf16 on CPU.
- **Checked now:** `git status` shows local main equal to `origin/main`; `eval_loss.py`, `run_comparison.py`,
  `src/prompting.py` and `tools/colab_setup.py` are already pushed, so the earlier "push the newest code" step
  is no longer needed (Entry 19 listed it; correction). Uncommitted: `docs/new_session_prompt.md`,
  `docs/progress_log.md`, and the deletion of `docs/train_results/*` (the user moved those files into the
  gitignored `experiments/finetuned_model/.../v2/` and `results/training/`). 19 tests pass.
- **Done so far:**
  - Data: file-level BASE/NEW/TEST splits, leakage assertions, fine-tuning corpora and the pilot sample
    (50 examples, seed 42) for CrossCodeEval; splits and corpus for RepoBench (Entries 7 to 13).
  - CrossCodeEval per-repo indexes (206 repos) and a retrieval comparison: BM25 beats UniXcoder at hit@1 and
    MRR with CIs excluding 0 (Entry 20).
  - Code: shared prompt and generation modules, label-masked training with an end token, CodeBLEU that raises
    instead of returning 0.0, bootstrap CIs, rewritten `run_comparison.py`, `demo.py`, `eval_loss.py`,
    Colab setup (Entries 14 to 19).
  - Training: v2 QLoRA run on CrossCodeEval finished (Entry 18); adapter and `trainer_state.json` are now
    local; loss curve plotted (Entry 20).
  - Reference paper analysis (Entry 17).
- **Missing / not yet run (nothing here has a result):**
  1. Any completion number (EM, edit similarity, identifier accuracy, CodeBLEU) for base, RAG, fine-tuned,
     hybrid. `run_comparison.py` has never run end to end, even on a GPU.
  2. Base-versus-adapter validation loss (`eval_loss.py` written, not run).
  3. The `codebleu` package and `bitsandbytes` 4-bit load on Colab are untested (Entry 17).
  4. BM25 is not a system in `run_comparison.py` (retrieval comparison only); the hybrid and RAG use dense
     retrieval. The plan's BM25 baseline for completion is therefore not yet covered. Since BM25 won the
     retrieval comparison, consider adding a `--retriever bm25` option before the full run.
  5. Plan Section 6 extras not built: noisy-context injection, forgetting check (HumanEval before/after),
     top-k sweep, cross-file-dependent subset, hit-versus-miss script (data is in `predictions.jsonl`).
  6. RAFT-style variant, RepoBench fine-tuning run, and RepoBench evaluation. Open decisions unchanged:
     epochs (2 may be enough), max_seq_length above 512, RepoBench TEST sampling rule.
  7. Hypotheses and the "expected vs Wang et al." section are in the plan and notes but not yet written into
     the thesis text; Section 11 supervisor update (scope changes) and the outdated progress-report .docx.
  8. Seeds and constants are in scripts, not `config.yaml`; memory per system in the evaluation is not
     independent (one process, adapter stays loaded).
- **Plan for the first pilot run (Colab T4, one session; order = most important first, see colab_steps Part 7.2):**
  1. Cells 1 to 3; check the data lines say `ok` and the adapter exists.
  2. Quick checks: `src.demo` on the first pilot id, then `run_comparison --limit 5 --output-dir results/pipeline_test`.
     Stop and report if a completion is empty or multi-line, or if CodeBLEU fails (then add `--skip-codebleu`).
  3. Pilot, main view (50 examples, four systems).
  4. `src.finetuning.eval_loss` (base vs adapter).
  5. Pilot, staleness view.
  6. Download `results/pilot_main`, `results/pilot_staleness`, `results/val_loss_base_vs_adapter.json`, then
     disconnect. Report as "pilot, n=50", never as findings.
- **Open:** whether to run a no-model local test of the pipeline (prompts and retrieval for the 50 ids) before
  the GPU session; recommended, not yet written.

## Entry 22: Model-free dry run of the pilot pipeline, run locally (Section 9, step 5 prep)
- **Asked:** write and run a local check of the pilot pipeline that does not need the model (free RAM is only
  about 8 GB, so the 32-bit model test was skipped, Entry 21), and log what it is for.
- **Purpose:** the first Colab session has limited free GPU time. Everything in `run_comparison.py` that does
  not depend on generation can be tested on this machine, so plain bugs are found here and not on the GPU clock.
  It does not test the model load, the 4-bit path, generation quality, or CodeBLEU on a real install.
- **Done:** wrote `experiments/dry_run_pipeline.py` (run: `python -m experiments.dry_run_pipeline --adapter
  experiments/finetuned_model/crosscodeeval/v2`). It reuses `load_examples` and the retrieval and prompt code
  of `run_comparison.py`, loads only UniXcoder and the Qwen tokenizer (not the weights), and writes to
  `results/dry_run/` (stand-in predictions, not results; gitignored). Checks: adapter base model equals the
  config; the 50 pilot examples load and are TEST; retrieval in both views with no TEST file; prompt lengths;
  the scoring and file-writing path with stand-in predictions (reference text, empty, nearly right, and a
  two-line text cut to its first line); CodeBLEU availability.
- **Found (passed, no code bug in these paths):**
  - Adapter base model `Qwen/Qwen2.5-Coder-1.5B` matches `config.yaml`; adapter files present (LoRA r=8, alpha 16).
  - 50 pilot examples, all TEST, all with a relevant file in the main pool. A relevant file lies in the top-5
    chunks for 48 of 50 (main) and 46 of 50 (staleness). Dense retrieval on these 50: MRR 0.764, hit-style
    precision@1 0.62. 0 TEST files retrieved.
  - Scoring path correct: stand-in EM is 1.0 for exact copies, 0.0 for empty predictions, and the two-line
    stand-in is cut to one line and scores 1.0; edit similarity 0.98 for the nearly-right stand-in.
  - Local `codebleu` is not installed; `code_bleu` raises a clear error (does not return 0.0), as designed.
    On Colab check that the optional install in `colab_setup.py` worked, else use `--skip-codebleu`.
- **Found (needs a decision, matters for the pilot):** prompt lengths in tokens (Qwen tokenizer):
  - Without retrieval (base, fine-tuned): median 437, max 4,411; 21 of 50 exceed 512. Training cut inputs from
    the left to fit 512 tokens (Entry 17), but inference does not cut, so for those 21 examples the adapter sees
    a longer input than it was trained on.
  - With retrieval (RAG, hybrid): median 2,152, max 5,919; all 50 exceed 512. Expected (5 chunks of up to 1,200
    characters), and consistent with Wang et al.'s note that retrieval multiplies input length. It also means
    these two systems are slower and use more GPU memory; the T4 should cope with about 6,000 tokens in 4-bit,
    but the `--limit 5` check should confirm it (watch for out-of-memory). [writing note]
  - Recommendation: run the pilot as is (it is a pipeline check); afterwards consider truncating the code part of
    the prompt from the left at inference to the same limit as training, and report both variants.
- **Fix made:** `src/evaluation/evaluator.py` logged messages with the character "→", which the Windows console
  (cp1252) cannot print, so logging errors appeared on this machine (results were still written). Replaced with
  "->" in three log messages. Not a problem on Colab (UTF-8) but harmless to fix.
- **Open:** nothing committed or pushed (user does that). `experiments/dry_run_pipeline.py` and the evaluator
  change are new local changes that Colab does not need; the pilot will use the version already on GitHub.

## Entry 23: Overall completion estimate, for updating the progress report (as of 2026-11-19)
- **Asked:** how much of the work is complete, in percent, logged so the progress report can be updated.
- **Estimate: about 53% (read it as 50 to 55%), project work and research/analysis only.** Thesis writing is
  deliberately NOT counted (revised at the user's request; the first version, 48.7% including a 12% writing
  share, is replaced). This is a judgement, not a measurement: the weights are mine, based on effort, and the
  "done" shares come from Entries 1 to 22.

  | Workstream | Weight | Done | Contribution |
  |---|---|---|---|
  | Plan, reference-paper analysis, hypotheses | 5.7% | 100% | 5.7 |
  | CrossCodeEval data (split, leakage checks, corpus, pilot sample) | 11.4% | 100% | 11.4 |
  | RepoBench data (split and corpus; no indexes) | 8.0% | 85% | 6.8 |
  | Pipeline code (prompting, trainer, evaluation, demo, Colab setup, dry run) | 17.0% | 85% | 14.5 |
  | Retrieval (CrossCodeEval indexes, dense/BM25/random comparison) | 9.1% | 70% | 6.4 |
  | Fine-tuning (CrossCodeEval v2 done; no RepoBench run, no RAFT variant) | 11.4% | 50% | 5.7 |
  | Evaluation runs (no completion scores yet; dry run only) | 28.4% | 10% | 2.8 |
  | Extra analyses (noisy context, staleness, forgetting, hit/miss, top-k) | 9.1% | 0% | 0.0 |
  | **Total** | 100% | | **53.3** |

- **Reading:** the preparation work (data, code, indexes, one training run) is largely done; the results are
  not. No system has a completion score (EM, edit similarity), which is why the evaluation share is small.
  The percentage will rise quickly once the pilot and the full CrossCodeEval evaluation run (roughly +17 points
  for the full CrossCodeEval comparison and its extra analyses).
- **For the progress report (what changed since the August report; plan Section 11 says to tell the supervisor):**
  - Done and new: file-level BASE/NEW/TEST splits with automated leakage assertions for both datasets;
    per-repository indexes; the reference-paper comparison; the first QLoRA fine-tuning run (3 h 29 min on a
    T4, about 8.7 GB); the first dense-vs-BM25 retrieval result (BM25 better at hit@1 and MRR, CIs exclude 0).
  - Corrections to the August report: the split is by file within a repository, not an 80/10/10 split by
    repository; the two datasets are reported separately, not mixed; the hybrid import was missing (fixed,
    Entry 9); the remaining work is not only execution (leakage-safe design, hit/miss and staleness analyses
    were added); Python only.
  - Still to do: pilot and full CrossCodeEval comparison, extra analyses, RepoBench runs, thesis chapters.
  - Risks to mention: free Colab GPU quota ran out after one training run; prompts with retrieval are about
    2,000 tokens against 512 in training (Entry 22); CrossCodeEval staleness sample is small (68 examples).

## Entry 24: Local work while waiting for the GPU (Sections 6, 9)
- **Asked:** do the local steps suggested while the Colab GPU quota is unavailable. No commits or pushes
  (the user does those).
- **Done:**
  1. **CodeBLEU installed and tested locally** (`codebleu` 0.8.0, `tree-sitter` 0.26.1, `tree-sitter-python` 0.25.0
     in `./venv`; a dry-run of pip showed only these three packages would change). Identical code scores 1.0,
     different code 0.14, an empty prediction 0.0 (a real score, no silent failure). Note: Colab installs the
     same packages unpinned (`tools/colab_setup.py`), so the same versions are expected there; unverified.
  2. **`run_comparison.py` new options** (defaults unchanged): `--retriever bm25` (BM25 with the same tokeniser as
     `compare_retrievers.py`, over the same chunks and index views), `--max-code-tokens N` (keeps the last N tokens
     of the code in every prompt; chunks are not cut; helper `truncate_code_left` in `src/prompting.py`),
     `--noise-chunks N` (noisy-context test: N chunks from other repositories added at seeded random positions to
     the RAG and hybrid prompts; retrieval metrics stay on the real chunks). The output folder name gets a suffix
     (`_bm25`, `_code480`, `_noiseN`) so runs do not overwrite each other; each setting is recorded in the
     metrics file. `--top-k` already existed (top-k sweep = one run per value).
  3. **Dry run extended** (`experiments/dry_run_pipeline.py`): BM25 retrieval over the 50 pilot examples (relevant
     file inside the top-5 chunks for 50 of 50, against 48 of 50 for dense; no TEST file), and prompt lengths with
     `--max-code-tokens 480`: without retrieval the maximum falls from 4,411 to 494 tokens and none exceeds 512;
     with retrieval the median falls from 2,152 to 1,983 tokens (chunks dominate, 5 chunks of up to 1,200
     characters). Small n: not a retrieval result.
  4. **`src/evaluation/analyze_predictions.py`** (hit vs miss, and paired differences rag-base, ft-base,
     hybrid-rag, hybrid-ft, rag-ft, each with a 95% bootstrap CI and a flag when the CI excludes 0). Tested with
     three unit tests and a run on a synthetic `predictions.jsonl` (random numbers, deleted afterwards, not
     results). It works on the real file from Colab, also locally.
  5. **`src/evaluation/forgetting_check.py`** (HumanEval pass@1, base vs adapter). Cannot run here: it executes
     model-generated code, so it refuses to run without `--allow-exec` and the docs say Colab only. The
     time limit (10 s per program) is not a sandbox. Unit-tested only its cut and run helpers (24 tests pass).
  6. **RepoBench sampling rule decided and built** (`src/preprocessing/build_repobench_sample.py`): per setting,
     candidates = TEST examples whose gold file has a BASE fragment and is not the example's own file (4,399 for
     cross_file_first and 4,298 for cross_file_random, matching Entry 10), then 300 per setting with seed 42.
     446 distinct repos. This is a compute choice, not from the plan: say so. Plain random, not stratified.
  7. **RepoBench indexes** (`src/retrieval/build_repobench_indexes.py`, `--sample-repos`): one index per repo,
     main (BASE) and staleness (BASE + NEW), same A6 assertions (no TEST file). Fragments are cut to 3,000
     characters for embedding and storage. Started in the background for the 446 sample repos; log in
     `results/repobench_index_build.log`; restartable (skips finished repos). The 446 repos hold 14,033 fragments; early speed was about
     1 second per fragment, so expect about 4 hours (unmeasured end to end). Two repos (`16lemoing/dot`, `1in-oos/ccplus`) were built
     earlier in a 5-repo speed test with a 6,000-character cap, a small inconsistency.
  8. `docs/colab_steps.md` Part 8 lists the new options and a suggested order for the extra runs.
- **Not done:** `compare_retrievers` for RepoBench (needs its own query rule: `cropped_code`, gold index) and
  `run_comparison` support for RepoBench; the hit/miss analysis has not seen real predictions; cross-file-dependent
  subset (every CrossCodeEval pilot example has a relevant file by construction, so it is the whole pilot);
  moving seeds and constants into `config.yaml` (risky while indexes build, left for later).
- **Permission note:** one command was denied (it contained a recursive delete of the RepoBench index folder). I
  did not retry it; the 5 test repos from the speed test are still there.

## Entry 25: Tests for the new run options and Colab setup hardening (Section 9)
- **Asked:** do the two small local items (tests for the new `run_comparison` options; check and tidy
  `tools/colab_setup.py`), and leave anything that needs Colab until the pilot session.
- **Done:**
  - `tests/test_run_comparison_options.py` (3 tests): BM25 ranks the chunk sharing identifiers first and keeps
    all chunks; noise chunks come only from other repositories, are repeatable for the same task id and leave the
    real chunk in place; `truncate_code_left` keeps the text nearest the cursor and leaves short code and
    `None` unchanged. All 27 tests pass.
  - `tools/colab_setup.py`: (a) the RepoBench build now also runs `build_repobench_sample` and
    `build_repobench_indexes --sample-repos`, and `data/embeddings/repobench` is part of the Drive cache; (b) the
    data check now also verifies `pilot_ids.json` (50), the number of CrossCodeEval index folders (206) and
    `examples.jsonl` (2,018 lines), and `sample_repos.json` (446) for RepoBench, printing `ok`/`DIFFERS`/`MISSING`.
    I ran the check locally against this machine's data: all `ok`. My first expected value for `examples.jsonl`
    was wrong (2,665 instead of 2,018, which is the number of examples in repos with at least 3 files); the local
    run caught it before it reached Colab.
  - `docs/colab_steps.md`: note on the extra checks, and the model-free dry run
    (`python -m experiments.dry_run_pipeline ...`) added to the quick checks, so a bad cache shows up before GPU
    time is spent.
- **Not verified (needs Colab):** that the existing Drive cache passes the new checks (it was written before
  these checks existed; the local data does), that the RepoBench build steps work on Colab, and that the pinned
  installs behave. The first Colab cell output will show it.
- **Open:** the RepoBench index build is still running locally in the background; RepoBench retrieval comparison
  and RepoBench in `run_comparison` are not written. Nothing committed or pushed.

## Entry 26: RepoBench indexes finished (Sections 5, 9)
- **Done:** the background build (`build_repobench_indexes --sample-repos`, started 15:46, finished 18:55, about
  3 hours) completed. Log: `results/repobench_index_build.log`. 444 repos were indexed in this run plus the 2
  built earlier in the speed test, so all 446 sample repos have both views (checked: 0 missing main, 0 missing
  staleness). Fragments in this run: main 11,031, staleness 13,984. The A6 assertions passed (no TEST file in any
  index, one repo per index).
- **Speed:** about 1.5 to 3 repos per minute on CPU, 446 repos in about 3 hours (fragments cut to 3,000
  characters for embedding). On the Colab GPU the same step should be much faster; unmeasured.
- **Not done yet:** a RepoBench retrieval comparison (dense vs BM25 vs random on the 600 sampled examples) and
  RepoBench in `run_comparison`. Nothing committed or pushed.

## Entry 27: RepoBench retrieval comparison script written, not run (Sections 5, 6)
- **Asked:** write the RepoBench retrieval comparison (dense vs BM25 vs random) and stop before running it.
- **Done:** `src/retrieval/compare_retrievers_repobench.py`. It reuses the retrievers, metrics and bootstrap of
  `compare_retrievers.py` (CrossCodeEval) and reads the Entry 26 indexes and the Entry 24 sample (300 examples per
  setting, settings reported separately). Query = last 20 lines of `cropped_code`; relevant file = the gold snippet
  file; fragments collapse to a ranked list of distinct files; views main (BASE) and staleness (BASE + NEW).
  Output `results/repobench_retrieval_comparison.json`, including the pool sizes (distinct files per pool) so that
  the random floor can be read against them.
- **Checks built in:** each sampled row must be a TEST example matching `examples.jsonl` (same repo and path); the
  gold file must be in both pools; a retrieved TEST file aborts the run.
- **Limitation to state:** the sample was drawn from examples whose gold file is in BASE, so the staleness view
  here shows NEW files only as extra distractors. It has no examples whose gold file is in NEW (the RepoBench
  staleness sample would need a separate draw: not built). The existing retrieval plots read the CrossCodeEval
  result file only; no RepoBench plot yet.
- **Verified:** syntax and `--help` only. **Not run**; expected runtime a few minutes on CPU (600 queries).

## Entry 28: RepoBench retrieval comparison, run locally (Sections 5, 6)
- **Done:** ran `python -m src.retrieval.compare_retrievers_repobench` (CPU, about 3 minutes, 600 queries; 300 per
  setting). Output `results/repobench_retrieval_comparison.json` (gitignored).
- **Checks passed:** all 600 sampled rows matched the split file as TEST examples; gold file in every pool;
  TEST files retrieved: 0.
- **Found** (hit@1 / hit@3 / MRR; 95% CI of MRR in brackets; one relevant file per example):

  | Setting, view (n=300) | Median pool files | dense | BM25 | random |
  |---|---|---|---|---|
  | cross_file_first, main | 9 | 0.247 / 0.563 / 0.446 [0.406, 0.485] | 0.260 / 0.593 / 0.466 [0.427, 0.503] | 0.127 / 0.393 / 0.323 [0.291, 0.357] |
  | cross_file_first, staleness | 12 | 0.223 / 0.490 / 0.409 | 0.240 / 0.527 / 0.431 | 0.097 / 0.360 / 0.283 |
  | cross_file_random, main | 11 | 0.290 / 0.593 / 0.484 [0.442, 0.528] | 0.337 / 0.670 / 0.535 [0.495, 0.579] | 0.110 / 0.423 / 0.319 [0.288, 0.349] |
  | cross_file_random, staleness | 14 | 0.240 / 0.527 / 0.431 | 0.297 / 0.613 / 0.494 | 0.140 / 0.320 / 0.298 |

  Paired dense minus BM25 (95% CI):
  - cross_file_first: main MRR -0.020 [-0.062, 0.020], staleness MRR -0.022 [-0.061, 0.013]. Both CIs include 0, so
    no evidence of a difference in this setting.
  - cross_file_random: main MRR -0.051 [-0.086, -0.014], staleness MRR -0.063 [-0.098, -0.028]; hit@3 also
    excludes 0 in both views. BM25 is better here.
- **Reading:**
  - Both real retrievers beat random on MRR (CIs do not overlap in main view), but by much less than on CrossCodeEval
    (dense MRR 0.45 to 0.48 against random 0.32, versus 0.77 against 0.63 there), and absolute hit@1 is low (0.22 to
    0.34): the gold file is found first in only about a quarter to a third of cases. Retrieval is harder here than on
    CrossCodeEval, which fits RepoBench's fragment pools and its single gold file; unexplained in detail.
  - BM25 is better than dense in all four cells; the gap is clear in cross_file_random and not significant in
    cross_file_first. Same direction as CrossCodeEval and Wang et al. (BM25 > UniXcoder). [writing note]
  - Adding NEW files lowers every system (pool grows by about 3 files), most for dense: staleness adds distractors.
    Not a test of NEW gold files (see Entry 27 limitation).
  - Pools are small (median 9 to 14 files), so read hit@3 and above against random (0.32 to 0.42 at hit@3).
- **Not done:** a RepoBench retrieval plot; RepoBench completion (needs `run_comparison` support and a RepoBench
  fine-tuning run). Nothing committed or pushed.

## Entry 29: Results collected in one place; completion estimate updated (as of 2026-11-19)
- **Asked:** add the new findings to the log, set the results up somewhere else if not already, and say how much
  of the project is complete.
- **Done:**
  - The findings are in this log as Entry 20 (CrossCodeEval retrieval comparison, loss curve) and Entry 28
    (RepoBench retrieval comparison); Entry 26 has the RepoBench index build.
  - New file `docs/results_summary.md`: every real result in one place (both retrieval comparisons with CIs,
    the v2 fine-tuning run, data facts, the dry-run facts marked as not results, and a list of what is still
    missing), with the command and file that regenerate each.
  - `docs/claude_web_prompt.md` (the prompt for the report and presentation) was out of date (it said the
    retrieval comparison was not run and the fixed training not started). Updated: file list (log Entries 1 to 28,
    `results_summary.md`, both result JSON files), Part B (new items 16 to 19), "Not done yet", a new section D4b with
    the real retrieval numbers, chart notes for retrieval and the loss curve, the status/timeline part, and the
    remaining-plan order.
- **Completion estimate (project work and research/analysis only; thesis writing not counted): about 60%**
  (read as 57 to 62%; was about 53% in Entry 23). A judgement, same weights as Entry 23:

  | Workstream | Weight | Done now | Contribution | Was |
  |---|---|---|---|---|
  | Plan, reference-paper analysis, hypotheses | 5.7% | 100% | 5.7 | 5.7 |
  | CrossCodeEval data | 11.4% | 100% | 11.4 | 11.4 |
  | RepoBench data (split, corpus, sample) | 8.0% | 90% | 7.2 | 6.8 |
  | Pipeline code (adds BM25 / prompt-length / noise options, analysis, forgetting script, dry run) | 17.0% | 95% | 16.2 | 14.5 |
  | Retrieval (both datasets indexed and compared; no RepoBench plot, no NEW-gold RepoBench sample) | 9.1% | 88% | 8.0 | 6.4 |
  | Fine-tuning (CrossCodeEval v2 only) | 11.4% | 50% | 5.7 | 5.7 |
  | Evaluation runs (still no completion score; dry run only) | 28.4% | 12% | 3.4 | 2.8 |
  | Extra analyses (code written, none run on model outputs) | 9.1% | 20% | 1.8 | 0.0 |
  | **Total** | 100% | | **59.4** | 53.3 |

- **Reading:** the increase comes from the RepoBench indexes and retrieval results and from analysis code being
  written. The largest block, evaluation runs (28% of the weight), is still almost empty, so the next jump
  (about +15 to 20 points) comes only from the GPU runs: pilot, full CrossCodeEval comparison, base-versus-adapter
  validation loss.
- **Open:** `docs/new_session_prompt.md` still describes the state after Entry 19; update it before the next
  session if you want to use it (not changed here). Nothing committed or pushed.

## Entry 30: Repository cleanup that does not change how anything runs (2026-11-19)
- **Asked:** go through the repo and make it easier to navigate and understand, without changing how it is run
  (the Colab work is planned for the next day). The user had committed and pushed up to commit `10d4a53`.
- **Rule followed:** no code logic, module path, command-line option or output location was changed. Only
  documentation, docstrings, printed hints and unused loose files.
- **Done:**
  - `README.md` rewritten: it described the first design (flat train/val/test, `main.py index/finetune`, a 7B
    default). Now it has the study summary, where-to-start table, a repository map, the real run order
    ("Running the study", the commands we use) and the current metrics and datasets.
  - New `docs/README.md`: index of the docs, split into current, raw output and historical files.
  - "Outdated / superseded" notes added at the top of `steps.txt`, `docs/thesis_implementation_guide.md`,
    `docs/session_prompt` and in the docstring of `src/preprocessing/prepare_datasets.py` (kept, not deleted).
  - Two printed hints in `data/crosscodeeval/download.py` and `data/repobench/download.py` pointed to the
    superseded `prepare_datasets.py`; they now name the current first step (strings only).
  - Four unused loose files moved from the project root to `docs/archive/`: `questions.md`,
    `answers_to_presentation_questions.md`, `embedded_image_0.png`, `embedded_image_1.png` (nothing referenced
    them; checked by search). `thesis.md` stays at the root because it looks like a draft of the user's own.
  - `requirements.txt`: added packages the current code imports but the file lacked (`rank_bm25`, `codebleu`,
    `tree-sitter-python`, `matplotlib`). Colab does not read this file (`tools/colab_setup.py` has its own list).
  - `docs/new_session_prompt.md` updated (git state, Entry 30).
- **Checked after the changes:** 27 tests pass; the changed scripts compile; `run_comparison.py --help` works.
- **Left alone on purpose, suggestions:**
  - `.idea/` is tracked by git although `.gitignore` lists it; `git rm -r --cached .idea` would stop tracking it
    (a git change for the user to decide).
  - `main.py` (`evaluate` stub and the `index` / `finetune` wrappers reflect the old design),
    `src/retrieval/retriever.py` and `src/hybrid/pipeline.py` still work and are imported by the demo; merging or
    removing them is a code change, not done.
  - Scripts could be grouped into subfolders (for example `src/retrieval/` has seven runnable scripts) but moving
    them would change the `python -m ...` commands that the Colab guide uses.
  - `docs/first_train_results` is the raw v2 training output (475 lines of progress bars); trimming it is optional.
  - Seeds and constants are still in the scripts, not `config.yaml` (open item).

## Entry 31: Completion estimate with completed-vs-remaining table, for the report and presentation (2026-11-20)
- **Asked:** independent review of how much of the project work is done (thesis writing not counted), and a
  table of work completed versus work left, to be reused in the progress report and the presentation.
- **Estimate: about 58% (read as 55 to 60%).** A judgement, not a measurement. Same weights as Entries 23 and 29
  (Entry 29 gave 59.4%); rounded down because `experiments/run_comparison.py` has never run end to end, so the
  "pipeline code" share is credited at about 92% and not 95%. Based on reading the log, plan and results summary
  and listing the repo files; no code was re-run for this entry.

| Workstream | Weight | Done | Contribution | Status |
|---|---|---|---|---|
| Plan, reference-paper analysis, hypotheses | 5.7% | 100% | 5.7 | Finished |
| CrossCodeEval data (split, leakage checks, corpus, pilot sample) | 11.4% | 100% | 11.4 | Finished |
| RepoBench data (split, corpus, 300-per-setting sample) | 8.0% | 90% | 7.2 | Nearly finished |
| Pipeline code (prompting, trainer, evaluation, demo, Colab setup, dry run, 27 tests) | 17.0% | 92% | 15.6 | Written; never run end to end on a GPU |
| Retrieval (indexes for both datasets; dense vs BM25 vs random with CIs) | 9.1% | 87% | 7.9 | Done; no RepoBench plot, no NEW-gold RepoBench sample |
| Fine-tuning (CrossCodeEval v2 only) | 11.4% | 50% | 5.7 | No RepoBench run, no RAFT-style variant, no base-vs-adapter loss |
| Evaluation runs (EM, edit similarity, identifier accuracy, CodeBLEU for base / RAG / FT / hybrid) | 28.4% | 11% | 3.1 | Not run (needs GPU) |
| Extra analyses (hit/miss, noisy context, staleness effect, forgetting, top-k) | 9.1% | 17% | 1.5 | Code written; none run on model output |
| **Total** | 100% | | **58.1** | |

**Completed (summary for slides):**
- Both datasets downloaded and inspected; file-level BASE/NEW/TEST splits with passing leakage assertions.
- Fine-tuning corpora for both datasets (CrossCodeEval 9,378 + 1,059; RepoBench 10,800 + 1,200).
- Per-repo indexes: 206 CrossCodeEval repos, 446 RepoBench sample repos.
- Retrieval comparison on both datasets: BM25 better than UniXcoder dense (CrossCodeEval main MRR 0.884 vs 0.770,
  n=292, CI of the difference excludes 0).
- One QLoRA fine-tuning run (CrossCodeEval v2): 3 h 29 min on a T4, about 8.7 GB, validation loss flat at about 0.68.
- Shared prompt format, label-masked training, CodeBLEU that raises, bootstrap CIs, evaluation and analysis scripts,
  Colab setup, model-free dry run, hybrid PEFT import fix, reference-paper analysis.

**Left to do (summary for slides):**
1. 50-example pilot of base / RAG / fine-tuned / hybrid on a Colab GPU (free quota ran out after the v2 run).
2. Base-versus-adapter validation loss (`eval_loss.py`, written, not run): without it there is no evidence that
   fine-tuning helped.
3. Full CrossCodeEval evaluation (543 TEST examples) with BM25 and hit/miss analysis.
4. Extra analyses on model output: noisy context, top-k sweep, forgetting check (HumanEval, Colab only), staleness
   effect on completion.
5. RepoBench fine-tuning and completion evaluation.
6. Decide on the RAFT-style variant (hybrid sees about 2,000-token retrieval prompts, trained on 512 without context).
7. Housekeeping: seeds and constants into `config.yaml`; independent per-system memory measurement.
8. Numeric recommendations (the decision-question answer) once results exist.

- **Reading:** the groundwork is largely done; the results are not. Evaluation runs carry 28% of the weight and are
  almost empty, so the next jump (about +15 to 20 points) comes only from GPU runs. Risks: GPU quota; retrieval prompts
  about 2,000 tokens vs 512 in training; CrossCodeEval staleness sample is only 68 examples; `bitsandbytes` 4-bit and
  Colab `codebleu` installs untested on Colab.
- **Not changed:** `docs/Nidwija_081MSCSK010_progress_report.docx` (binary, still the August version). Use this
  entry and `docs/claude_web_prompt.md` to produce the updated report. Nothing committed or pushed.

## Entry 32: First GPU session on Colab, setup to 5-example pipeline test (2026-11-21; raw output in `docs/results_output_gpu_day2`)
- **Asked:** log the results of Colab steps A to B3 (`docs/colab_steps_part2.md`) before the pilot (C1) finishes.
- **Setup (Cell 3):** passed. Tesla T4, `cuda: True`, bitsandbytes 0.50.2. Data restored from the Drive cache and
  every check was `ok` (train 9,378, val 1,059, pilot 50, 206 index folders, examples.jsonl 2,018). Adapter v2 is on
  Drive (`adapter_model.safetensors` 4.4 MB, written 2026-11-19 12:29, plus checkpoint-1700 and checkpoint-1761).
  The pinned installs worked on Colab (no pip error). No CodeBLEU install warning appeared.
  An earlier `No module named 'rank_bm25'` error came from running the dry run before Cell 3 had completed in that
  runtime (Cell 3 does install it); the fix used is [YOU: re-ran Cells 1-3 / pip install - fill in].
- **Dry run (B1), on Colab:** `DRY RUN PASSED`. Adapter base model matches the config; 50 pilot examples load; no
  TEST file retrieved in either view; relevant file in top-5 for 48 of 50 (main) and 46 of 50 (staleness) with dense,
  50 of 50 with BM25. Prompt tokens identical to Entry 22/24 (no retrieval median 437, max 4,411, 21 of 50 over 512;
  with retrieval median 2,152, max 5,919; with `--max-code-tokens 480` max 494, none over 512). **`codebleu` package
  works on Colab** (this was listed as untested in Entry 17). Generation limit `max_new_tokens = 128`.
- **5-example test (B3), the first end-to-end run of `run_comparison.py` with the real model:** it finished and wrote
  `results/pipeline_test/` (metrics per system, `comparison_summary.*`, `predictions.jsonl`). The 4-bit load and
  generation worked, no out-of-memory. **This is a pipeline check, n=5, not a result** (CIs span most of the range).

  | System | EM | Edit sim. | Identifier acc. | CodeBLEU | Avg ms/example | Peak GPU MB |
  |---|---|---|---|---|---|---|
  | base | 0.0 | 0.156 | 0.10 | 0.000 | 3,796 | 1,698 |
  | rag_only | 0.0 | 0.176 | 0.10 | 0.000 | 2,372 (395 ms retrieval for all 5) | 1,823 |
  | finetuning_only | 0.2 | 0.584 | 0.35 | 0.144 | 1,599 | 1,698 |
  | hybrid | 0.2 | 0.658 | 0.55 | 0.149 | 2,151 | 1,823 |

  Retrieval on these 5: MRR 0.633, P@1 0.4, R@3 1.0 (tiny pools; not informative).
- **Observations to check (not conclusions):**
  - Base and RAG edit similarity (0.16 to 0.18) are very low, far below the fine-tuned systems. The base model is
    prompted in the format the adapter was trained on; if the base model does not follow it, base and RAG are being
    handicapped by the prompt, not by lacking the repository knowledge. **Read the base and rag_only rows of
    `results/pipeline_test/predictions.jsonl` before trusting any base/RAG vs FT comparison.** If the base outputs
    are junk or run on, consider a base-friendly prompt for A (plan: "same prompts" for all systems, so this needs a
    decision, and must be stated in the thesis either way).
  - Latency is confounded: the fine-tuned model was trained with an end-of-sequence token, so it stops early; base
    and RAG probably run to the 128-token limit before the first line is cut. The base ran first, so it also
    includes CUDA warm-up. Do not report latency per system from this run.
  - CodeBLEU is a warning-heavy score here: "no reference data-flows ... the data-flow match score degenerates to
    0". For one-line targets the data-flow component is always 0, which caps CodeBLEU. Report it with that caveat or
    lean on EM, edit similarity and identifier accuracy.
  - Peak GPU memory is small (1.7 to 1.8 GB for the 1.5B model in 4-bit, including prompts of about 2,000 tokens),
    so the T4 has plenty of room. Peak memory is reported per system (1,698 after 1,823), so the "not independent"
    concern in Entry 21 is partly resolved; the adapter is still loaded for base and RAG.
- **Timing estimate for the runs:** about 48 s of generation for 5 examples x 4 systems, so roughly 10 s per example
  across all four systems: the 50-example pilot should take about 8 to 9 minutes per view, and the full 543-example
  CrossCodeEval comparison about 1.5 hours per view (upper estimate, includes warm-up). Unmeasured end to end.
- **Not in the output file:** the demo run (B2) completions; fill in when available.
- **Next:** pilot main (C1), base-vs-adapter validation loss (C2), pilot staleness (C3), then the predictions check
  above. The completion estimate (about 58%, Entry 31) is not revised until C1 to C3 have results.

## Entry 33: Pilot, main view, 50 CrossCodeEval TEST examples, four systems (2026-11-21; raw output in `docs/results_output_gpu_day2`)
- **Asked:** log the C1 pilot run (`run_comparison --adapter .../v2 --4bit`, output `results/pilot_main/`).
- **Run facts:** 50 examples (seed-42 pilot set), view=main, top_k=5, dense retrieval (UniXcoder), adapter v2,
  4-bit, Colab T4. Whole run 08:55:05 to 09:02:05 (7 minutes, four systems, no out-of-memory, no errors).
  **This is the pilot: report as "pilot, n=50", not as findings.** Predictions cut to the first line before scoring.

  | System | EM [95% CI] | Edit sim. [95% CI] | Identifier acc. | CodeBLEU | Avg ms/example | Peak GPU MB |
  |---|---|---|---|---|---|---|
  | base | 0.00 [0.00, 0.00] | 0.236 [0.212, 0.262] | 0.018 | 0.068 | 1,798 | 2,009 |
  | rag_only (A) | 0.00 [0.00, 0.00] | 0.226 [0.205, 0.248] | 0.042 | 0.121 | 2,277 (+1,183 ms retrieval for all 50) | 2,146 |
  | finetuning_only (B) | 0.08 [0.02, 0.16] | 0.613 [0.549, 0.680] | 0.414 | 0.213 | 1,959 | 2,009 |
  | hybrid (C) | 0.14 [0.06, 0.24] | 0.644 [0.570, 0.715] | 0.490 | 0.214 | 2,232 | 2,146 |

  Retrieval (identical for A and C, dense): MRR 0.764, P@1 0.62, R@1 0.51, R@3 0.893, R@5 0.97, R@10 1.0. These
  equal the model-free dry run (Entry 22 and Entry 32), a consistency check on the retrieval path.
- **Reading (pilot only):**
  - The fine-tuned systems score far above base and RAG on edit similarity: the CIs do not overlap (B 0.55 to 0.68
    and C 0.57 to 0.72, against base 0.21 to 0.26 and RAG 0.20 to 0.25). RAG did not beat fine-tuning here, the
    opposite of Wang et al. and of H1's ordering for RAG vs fine-tuning. Do not state this as a finding yet: see the
    caveat next.
  - **Caveat, likely a prompt-format effect:** base and RAG get exact match 0 of 50 and identifier accuracy 0.02 to
    0.04, which is implausibly low for a 1.5B code model on single-line completion (Wang et al. report base EM
    24% on 1.5B, a different task). The adapter was trained on this prompt format and learned to emit one short
    completion and stop; the base model was not. The B-and-C gain over base and A may be mostly format learning,
    not repository knowledge. **Read the base and rag_only rows of `results/pilot_main/predictions.jsonl`
    before using any base/RAG vs fine-tuned comparison**, and decide whether A needs a base-friendly prompt (plan:
    "same prompts" for all systems, so state the choice in the thesis either way).
  - Hybrid vs fine-tuned-only: hybrid is higher (EM 0.14 vs 0.08, edit sim. 0.644 vs 0.613, identifier 0.49 vs
    0.41) but the CIs overlap heavily; no evidence of a difference at n=50. The paired comparison
    (`analyze_predictions`) will say more, still at n=50.
  - RAG vs base: edit similarity is the same (0.226 vs 0.236); CodeBLEU and identifier accuracy are higher with
    retrieval (0.121 vs 0.068, 0.042 vs 0.018). Weak, and again confounded by the prompt format.
  - Exact match is low everywhere (best 0.14), so edit similarity and identifier accuracy carry the comparison.
- **Correction to Entry 32:** it said base and RAG latency might be inflated by running to the token limit, and
  that base was slow in the 5-example test because of warm-up. In the 50-example run base (1,798 ms) is not slower than
  fine-tuned (1,959 ms), so there is no evidence of that effect; the 5-example latency was warm-up. Latency from
  this pilot is usable as a rough figure: retrieval adds about 24 ms per example (1,183 ms for 50) plus longer prompts
  (RAG 2,277 vs base 1,798 ms; hybrid 2,232 vs fine-tuned 1,959 ms). Still one T4, one process, n=50.
- **Memory:** peak GPU 2.0 GB without retrieval and 2.1 GB with retrieval prompts of about 2,000 tokens (up to
  about 6,000). The T4 has ample room, so memory is not a constraint for these runs; the memory cost of retrieval
  is about 0.14 GB here (for the efficiency section).
- **Timing:** 50 examples x 4 systems took 7 minutes, so the full 543-example CrossCodeEval comparison is about
  75 to 80 minutes per view (revised from Entry 32's 1.5 hours; unmeasured end to end).
- **Still to do from the session:** C2 (base-vs-adapter validation loss), C3 (staleness pilot), the predictions
  check above, then `analyze_predictions` (hit vs miss, paired differences with CIs). Completion estimate (about
  58%, Entry 31) is revised after C2 and C3.

## Entry 34: Base-vs-adapter validation loss (C2) and staleness pilot (C3) (2026-11-21; raw output in `docs/results_output_gpu_day2`)
- **Asked:** check the results so far and log what was done and found.
- **Done on Colab:** C2 `src.finetuning.eval_loss` (09:10) and C3 `run_comparison --view staleness` (09:14 to 09:21,
  7 minutes, no errors). Also `!cat results/pilot_main/comparison_summary.md`: its table matches Entry 33 exactly.
  `results/` on Drive now holds `dry_run`, `pilot_main`, `pilot_staleness`, `pipeline_test`,
  `val_loss_base_vs_adapter.json`. **Not yet downloaded locally** (checked: `results/pilot_*` absent on this
  machine), so `predictions.jsonl` has not been read and `analyze_predictions` has not been run.

### C2. Validation loss, base vs adapter (1,059 validation examples, 9,320 answer tokens, 4-bit, max length 512)
| Model | Loss on answer tokens + end token |
|---|---|
| base (adapter off) | 2.735 |
| adapter v2 | 0.6887 |
| difference | 2.046 |
- The adapter's loss (0.689) is close to the last training-time validation loss (0.684, Entry 18), so the two
  evaluation paths agree. Fine-tuning lowered the loss a great deal, so this is the first evidence that it did
  something. **Caveats [writing note]:** (1) validation is not file-held-out (Entries 8, 18), so the adapter's
  number is optimistic; (2) the loss includes the end-of-answer token and the output format, which the base model was
  never trained to produce, so much of the 2.0 drop is probably format learning, not repository knowledge. This
  matches the pilot (Entry 33), where the base model's completions score very low. It does not show that
  fine-tuning helps on held-out files; the held-out comparison is the pilot / full run on TEST examples.

### C3. Staleness pilot (NEW files added to the retrieval index only; same 50 examples, n=50, not findings)
| System | EM | Edit sim. [95% CI] | Identifier acc. | CodeBLEU | Avg ms | Main view (Entry 33) edit sim. |
|---|---|---|---|---|---|---|
| base | 0.00 | 0.236 [0.212, 0.262] | 0.018 | 0.068 | 1,860 | 0.236 |
| RAG (A) | 0.00 | 0.213 [0.191, 0.237] | 0.028 | 0.067 | 2,485 | 0.226 |
| fine-tuned (B) | 0.08 | 0.613 [0.549, 0.680] | 0.414 | 0.213 | 1,955 | 0.613 |
| hybrid (C) | 0.16 | 0.657 [0.582, 0.728] | 0.507 | 0.288 | 2,326 | 0.644 |

Retrieval, staleness vs main (dense): MRR 0.750 vs 0.764; R@1 0.477 vs 0.510; R@3 0.783 vs 0.893; R@5 0.915 vs 0.970;
P@1 0.62 in both. Peak GPU 2.0 GB (no retrieval) and 2.1 GB (retrieval), same as main.
- **Consistency checks that passed:** base and fine-tuned give exactly the same scores in both views (they use no
  retrieval and decoding is greedy), so the runs are repeatable and the view only changes A and C.
- **Reading (pilot only):**
  - Adding NEW files lowered retrieval slightly (R@3 0.89 to 0.78): more candidates compete. Caveat: the relevant
    set can also grow with NEW files (A3 rule), so recall is not strictly like for like.
  - Completion barely moved: RAG edit similarity 0.226 to 0.213; hybrid 0.644 to 0.657 (EM 0.14 to 0.16). These
    shifts are well inside the CIs. The hybrid CodeBLEU rise (0.214 to 0.288) is large for such a small change in the
    other metrics and has no CI; treat it as noise until the full run.
  - **This pilot cannot test the staleness claim (H3).** The 50 examples were drawn from examples whose relevant file
    is in BASE (Entry 13), so NEW files act only as distractors here. The real test needs examples whose relevant file
    is in NEW (68 in CrossCodeEval), where B cannot know the file and A/C can retrieve it. Not yet run: use
    `--subset test` on those 68 (a filter is not built yet).
  - B is unchanged by construction between views; so "B degrades on NEW" can only be shown on the NEW-relevant subset.

### Status after C1 to C3
- Done: pilot main (Entry 33), base-vs-adapter loss, pilot staleness; all ran end to end on a T4 (4-bit load,
  generation, CodeBLEU, retrieval, hybrid), with repeatable results. Whole GPU session so far about 35 minutes of
  compute. The estimate for the full 543-example run stays at about 75 to 80 minutes per view.
- Not done: read the predictions (base/RAG prompt-format question in Entry 33 still open); `analyze_predictions` (hit vs
  miss, paired differences with CIs); optional extras (D1 `--max-code-tokens 480`, D2 `--retriever bm25`, D3 forgetting
  check); full 543-example run; NEW-relevant subset run; RepoBench completion; RAFT-style decision.
- **Completion estimate revised:** about 65% (read as 62 to 68%; was 58%, Entry 31). Same weights: evaluation runs
  from 11% to about 30% done (pilot complete for main and staleness, no full set), extra analyses from 17% to about 25%
  (base-vs-adapter loss and a staleness view run; hit/miss and the rest pending), pipeline code to 97% (now run end to
  end), fine-tuning to 60% (the loss comparison exists). Contribution: 5.7 + 11.4 + 7.2 + 16.5 + 7.9 + 6.8 + 8.5 +
  2.3 = 66.3, rounded down to about 65 because the pilot is n=50 and the base/RAG comparison is unresolved.

## Entry 35: Extra pilot runs: shorter code input, BM25 retrieval, HumanEval forgetting check (2026-11-21; raw output in `docs/results_output_gpu_day2`)
- **Asked:** check the newer results and log what was done and found.
- **Done on Colab (all n=50, main view, adapter v2, 4-bit, T4; each about 7 minutes):**
  D1 `--max-code-tokens 480` (09:25 to 09:32, `results/pilot_main_code480/`), D2 `--retriever bm25`
  (09:34 to 09:41, `results/pilot_main_bm25/`), D3 `forgetting_check --limit 20` (`results/forgetting_humaneval.json`).
  No errors. Not yet downloaded locally.

### D1. Code cut to the last 480 tokens (Entry 22: 21 of 50 prompts exceeded the 512-token training length)
| System | EM | Edit sim. | Identifier acc. | CodeBLEU | Edit sim., full code (Entry 33) |
|---|---|---|---|---|---|
| base | 0.00 | 0.256 | 0.042 | 0.111 | 0.236 |
| RAG | 0.00 | 0.216 | 0.019 | 0.107 | 0.226 |
| fine-tuned | 0.10 | 0.611 | 0.420 | 0.213 | 0.613 |
| hybrid | 0.16 | 0.649 | 0.496 | 0.213 | 0.644 |
- Reading: no meaningful change (fine-tuned 0.613 to 0.611, hybrid 0.644 to 0.649; all inside the CIs). So the
  mismatch between the 512-token training length and longer inference prompts is **not** what drives the pilot
  scores. Peak GPU memory drops to 1.7 GB (from 2.0).

### D2. BM25 instead of UniXcoder for RAG and hybrid
| Retrieval metric (n=50) | dense (Entry 33) | BM25 |
|---|---|---|
| MRR | 0.764 | 0.840 |
| P@1 / R@1 | 0.62 / 0.51 | 0.70 / 0.59 |
| R@3 / R@5 | 0.893 / 0.970 | 0.977 / 1.000 |
| retrieval time, all 50 | 1,183 ms | 203 ms |

| System | EM | Edit sim. | Identifier acc. | CodeBLEU |
|---|---|---|---|---|
| RAG (A), BM25 | 0.00 | 0.224 | 0.021 | 0.097 |
| hybrid (C), BM25 | 0.12 | 0.640 | 0.469 | 0.209 |
(base and fine-tuned are unchanged: 0.236 and 0.613.)
- Reading: BM25 retrieves the right file better (agrees with Entries 20 and 28: MRR 0.84 vs 0.76 and about 6x faster
  retrieval) but **better retrieval did not improve completion**: RAG 0.226 to 0.224, hybrid 0.644 to 0.640 (EM
  0.14 to 0.12), all within noise. At n=50 this says retrieval quality is not the bottleneck for completion here, or
  that the models are not using the retrieved text. This bears on H2 (hybrid gain vs retrieval quality) but is not a
  test of it. [writing note] Together with RAG ≈ base in every run, it points at how the model uses context (the
  prompt), not at which retriever is used.

### D3. Forgetting check, HumanEval, first 20 problems, greedy
| Model | Passed | pass@1 |
|---|---|---|
| base (adapter off) | 0 / 20 | 0.00 |
| fine-tuned | 5 / 20 | 0.25 |
`relative_change` is `None` because the base score is 0 (division by zero).
- **This result is not usable as a forgetting measure, and it must not be reported as one.** (1) Base 0 of 20 is
  implausible for a 1.5B code model (Qwen2.5-Coder-1.5B base is reported at roughly 40% on HumanEval; check the
  Qwen report before citing). (2) The script wraps the HumanEval stub in the **training prompt format**
  (`src/prompting.py`), which only the adapter was trained on, so the base is penalised by the format, exactly as in the
  pilot (base and RAG exact match 0 of 50). (3) n=20 first problems only. The fine-tuned model beating the base
  is the opposite of forgetting and is explained by the format, not by better coding.
  Fix before relying on it: add an option that gives both models the plain HumanEval stub (no instruction wrapper),
  rerun on all 164 problems on Colab, and report that as the forgetting measure. Not built yet.
- **Memory note for the efficiency section:** peak GPU for systems without retrieval depends on whether UniXcoder
  is loaded in that run (base/fine-tuned: 2.0 GB with dense, 1.5 GB with BM25, which does not load the embedder). Compare
  systems within one run, not across runs. Added cost of retrieval prompts within a run: about 0.15 GB.

### What this adds up to (pilot, n=50; with Entries 33 and 34)
- Four systems now run end to end, with repeatable numbers. Fine-tuned and hybrid are far above base and RAG
  (edit similarity about 0.61 to 0.66 vs 0.21 to 0.26); hybrid vs fine-tuned and dense vs BM25 are within noise;
  more files in the index (staleness), shorter code and a better retriever do not move completion.
- **Everything points to one open question that must be settled before any comparison is reported: is the
  base/RAG deficit real or a prompt-format artifact?** Evidence for the artifact: base EM 0 of 50, base HumanEval 0 of 20,
  RAG equal to base regardless of retriever. Test (cheap): read `predictions.jsonl` for base and rag_only; then rerun
  base and RAG with a base-friendly prompt (the plain code prefix, or a few-shot prompt) on the same 50. If scores jump,
  the thesis needs a fairer prompt for A (and the forgetting prompt), and the plan's "same prompt" rule has to be
  restated as "same task, best format per system" with the choice documented.
- **Completion estimate revised: about 67%** (read as 64 to 70%; 65% in Entry 34). Evaluation runs about 33% done
  (pilot, three variants, still no full set and an unresolved base prompt), extra analyses about 40% (loss
  comparison, staleness view, shorter code, BM25 run done; forgetting needs a rerun; hit/miss, noisy context and
  top-k sweep not run). Rounded down from 68.5 because the base/RAG comparison and the forgetting check are not yet valid.
- **Next:** (1) download `results/` from Drive and read the base and RAG predictions; run `analyze_predictions`;
  (2) decide on the base-friendly prompt and the plain-stub forgetting option; (3) full 543-example run only after (2),
  since a full run with a handicapped base wastes about 80 minutes per view; (4) the 68-example NEW-relevant staleness
  subset; (5) RepoBench completion and fine-tuning.

## Entry 36: Local review of the Colab results: the base/RAG prompt-format artifact is confirmed (2026-11-21)
- **Asked:** go through the downloaded results (`results/`), suggest the next local steps, and log findings.
- **Done (read-only analysis, nothing in the code or data changed):** checked that all files arrived
  (`pilot_main`, `pilot_staleness`, `pilot_main_code480`, `pilot_main_bm25`, `pipeline_test`,
  `val_loss_base_vs_adapter.json`, `forgetting_humaneval.json`); read the first 14 rows of `pilot_main/predictions.jsonl`;
  classified every base, RAG, fine-tuned and hybrid prediction; ran `analyze_predictions` on `pilot_main`, `pilot_staleness`,
  `pilot_main_bm25` and `pilot_main_code480` (it wrote an `analysis.json` next to each `predictions.jsonl`). The numbers in
  the console output of Entries 33 to 35 match the downloaded metrics files and the loss JSON.
  Side note: `.gitignore` now lists `results/` (a change you made; `git status` shows only that file as modified).

### Finding 1: base and RAG are not attempting the task (the prompt-format artifact is confirmed)
What the 50 pilot predictions look like (counted by the first characters of each prediction):
| System | Import line | Comment line | Echo of "# --- retrieved from ... ---" | Prose | def/class | Other |
|---|---|---|---|---|---|---|
| base | 33 | 3 | 0 | 8 | 2 | 4 |
| RAG | 5 | 17 | 8 | 17 | 1 | 2 |
| fine-tuned | 0 | 0 | 0 | 0 | 0 | 50 |
| hybrid | 0 | 0 | 0 | 0 | 0 | 50 |
- Base writes things like `from datetime import datetime`, `import pytest`, or a sentence ("The provided code is incomplete
  ..."); RAG copies the comment header of a retrieved chunk, writes a comment, or answers in prose ("The response is a list
  of comments ..."; one output is the word-for-word instruction "Complete the following code."). The few "other" cases
  (4 base, 2 RAG) were not checked one by one. The fine-tuned and hybrid models always write a code continuation of the line.
- Cause: the prompt (`src/prompting.py`) is an instruction wrapper, `### Instruction ... ### Input: <code> ### Response:`,
  and the code ends mid-line. The adapter was trained on exactly this and learned to continue the line and stop; the base
  model was never told to continue the cut line, so it starts something new after "### Response:". With retrieval, the
  retrieved chunks are pasted before the code as `#` comment lines, so RAG continues the comment pattern.
- **Consequence:** the pilot's "base and RAG score about 0.23 edit similarity, fine-tuned and hybrid about 0.61 to 0.64" mostly
  measures prompt format, not repository knowledge. The base and RAG numbers (and every "fine-tuned minus base" and "hybrid minus
  RAG" difference, which the analysis flags as significant) must not be used to rank the systems. They are not wrong
  numbers; they answer a different question ("how well does each model follow this instruction format?"). This also explains
  base 0 of 50 exact match, base HumanEval 0 of 20 (same wrapper), and RAG equal to base for any retriever or code length.
- Not an artifact: the fine-tuned vs hybrid comparison, where both use the same format (Finding 2).

### Finding 2: hybrid vs fine-tuned-only (the comparison that is valid in the pilot)
- Hybrid minus fine-tuned, edit similarity, paired 95% CI: main +0.031 [-0.032, 0.089]; staleness +0.044 [-0.019, 0.107];
  BM25 +0.027 [-0.034, 0.082]; code cut to 480 tokens +0.038 [-0.023, 0.095]. Exact match: +0.06 [-0.04, 0.16] (main).
  Every interval includes 0, so there is no evidence of a difference at n=50. The four runs reuse the same 50 examples, so
  they are not four independent confirmations; the repeated small positive sign is not extra evidence.
- On the 50 examples (main): the hybrid prediction is identical to the fine-tuned one in 21; the hybrid is better in 17 and
  worse in 12 (by edit similarity). Exact-match hits: 9 examples in total (7 hybrid, 4 fine-tuned, 2 shared). So retrieval
  changes the answer in about 60% of cases, in both directions.
- Hybrid failure mode seen: example `project_cc_python/2413` produced an 814-character output that repeats `MagicMock(), ...`
  until the 128-token limit (edit similarity 0.058). Only one example, but it means the hybrid can degenerate when the
  retrieved context is long; a repetition guard or a shorter-context option may be worth adding. [writing note]

### Finding 3: hit-versus-miss cannot be analysed at this size
In the main view only 2 of 50 examples had no relevant file in the top 5 (4 of 50 in the staleness view, 0 in the BM25 view).
The hit-minus-miss numbers (for example hybrid edit similarity -0.20, CI excludes 0) rest on 2 examples and mean nothing. Hit
versus miss needs the full 543-example run (292 with a relevant file in the pool) or a pilot that includes misses.

### Finding 4: forgetting check and validation loss
- `forgetting_humaneval.json`: base passed 0 of 20; fine-tuned passed problems 2, 11, 14, 15, 16 (5 of 20); relative change
  `None`. Consistent with Finding 1: the base is scored on the instruction wrapper, so this is invalid as a forgetting measure.
- Validation loss file matches Entry 34 (base 2.735, adapter 0.6887, 1,059 examples, 9,320 answer tokens). The base loss is high
  for the same format reason.

### What this changes
1. The completion estimate (about 67%, Entry 35): revised to about **65%** (62 to 68%). The evaluation-runs share drops from about
   33% to about 25% because the pilot's base and RAG rows have to be rerun with a fair prompt. Revise again after the rerun.
2. The plan's "same prompt for all systems" rule needs a decision (below). Wang et al.'s base model was given the plain code
   prefix, not an instruction wrapper (as I understand their setup; check `docs/reference_paper_comparison.md`).

### Decision for you (affects the thesis wording)
How should base and RAG be prompted? Options:
- **(a) Plain continuation for base and RAG (recommended default).** Prompt = retrieved chunks as comments (RAG only) + the
  code, no instruction wrapper; the model simply continues from the cursor. The fine-tuned and hybrid models keep the format
  they were trained on. State in the thesis: "same task, same retrieved chunks, same decoding and scoring; each model gets the
  prompt it can follow". This is the standard completion setup. Trade-off: the prompts are no longer byte-identical.
- **(b) Few-shot instruction prompt for base and RAG.** Keep the wrapper but add two worked examples. Closer to "same prompt" but
  longer prompts and a choice of examples that could bias results.
- **(c) Keep the wrapper everywhere and report the format effect as a finding.** Easiest, but base and RAG stay uninformative and
  the RAG-vs-fine-tuning question cannot be answered.
- Whichever you choose, keep the instruction-wrapper numbers of the pilot as a documented first attempt and state why they were
  set aside (this entry); do not delete them.
- Fine-tuning with retrieval-formatted prompts (RAFT-style) is a separate question and is still open.

### Next local steps (in order)
1. Decide (a), (b) or (c) above.
2. Build (Claude Code, tested locally and by the dry run): the chosen base-friendly prompt as an option in `run_comparison`
   (default unchanged, recorded in the metrics file and output folder name); a plain-stub option and a zero-score guard for
   `forgetting_check`; a filter for the 68 NEW-relevant CrossCodeEval examples. Also worth building: a pilot that includes
   retrieval misses (for hit versus miss) and an optional repetition guard for the hybrid.
3. Add a unit test that the plain prompt has no instruction wrapper and that retrieved chunks still precede the code.
4. Commit and push; then Colab session A (`docs/next_steps_part3.md`, Phase 2): base/RAG rerun on the same 50, plain-stub
   HumanEval on 164 problems, the 68-example staleness subset.
5. `docs/claude_web_prompt.md`: caveat 1 and the "may not claim" line were updated in this entry; refresh the numbers after the rerun.

## Entry 37: Decision (a) and the new options built; how the prompts were chosen, used and tested (plain-language note for the demo) (2026-11-21)
- **Asked:** use option (a) from Entry 36 (plain continuation prompt for base and RAG), add a plain-language note on how the
  prompts were selected, with examples, how they were used and tested, then build the local items (Entry 36, "Next local
  steps", item 2). Colab steps come later.
- **Done (all local, no GPU, nothing run on a model yet):**
  1. `src/prompting.py`: `build_plain_prompt` (retrieved chunks as `#` comments + the code, no wrapper) and
     `build_system_prompt(code, chunks, uses_adapter, base_prompt)`, which picks the prompt for each system. Adapter systems (B, C) always
     get the instruction format; the frozen systems (base, A) get `instruction` (default, unchanged) or `plain`.
  2. `experiments/run_comparison.py`: new `--base-prompt {instruction,plain}` (default `instruction`, so old commands behave as
     before); recorded as `base_prompt` in every metrics file; the output folder gets the suffix `_plainbase`. New
     `--subset new_relevant`: the TEST examples whose relevant file (A3 rule) is a NEW file. **Checked on the real data: 68 examples
     from 35 repositories, as expected from Entry 7 (5 of them are also in the pilot).** Run it with `--view main` and `--view staleness`:
     in the main view retrieval cannot reach the NEW file, in the staleness view it can.
  3. `src/evaluation/forgetting_check.py`: new `--prompt {plain,instruction}` (default `plain`: both models get the raw HumanEval
     function stub); `relative_change()` returns `None` for a zero base score and the script prints a warning that a 1.5B code
     model should not score 0 with the plain prompt; the result file records the prompt and defaults to
     `results/forgetting_humaneval_<prompt>.json`, so the first (invalid) file `forgetting_humaneval.json` is not overwritten.
  4. `experiments/dry_run_pipeline.py`: also reports prompt lengths with `--base-prompt plain` (median 423 tokens without retrieval,
     2,138 with, vs 437 and 2,152 with the wrapper; the wrapper is only about 14 tokens) and checks the plain prompt is shorter.
- **Tests:** 34 automated tests pass (27 before; 7 new: plain prompt has no wrapper and ends at the cursor; retrieved chunks come
  first as comments; adapter systems always get the instruction format; the default is unchanged; an unknown option is rejected;
  HumanEval prompt modes and the zero-base guard; the NEW-relevant selection rule on synthetic data, including own-file,
  other-repository and non-TEST cases). The model-free dry run passes (`DRY RUN PASSED`).
- **Not verified:** the plain prompt has not been run on the model, so there is no evidence yet that base and RAG now continue the line
  properly; that is the Colab rerun. Not built (from Entry 36, lower priority): a pilot that includes retrieval misses, and a
  repetition guard for the hybrid (one 814-character `MagicMock()` loop).

### Plain-language note: how the prompts were chosen, used and tested (for the demo and presentation)
**The task, in one sentence.** We cut a line of code in the middle (for example `response = await repository_ratings.`) and ask each
system to write the rest of that one line (`delete_rate(1, session, new_user)`). A system gets only text as input, so the way we write
that text, the "prompt", matters a lot.

**Where the first prompt came from.** The project's first training run used an "instruction" format, like a form with three boxes:
```
### Instruction:
Complete the following code.

### Input:
    response = await repository_ratings.

### Response:
```
The fine-tuned model was trained on thousands of examples that look exactly like this, followed by the answer, so it learned the form.
We kept the same text for every system at first because the plan says all systems should see the same prompt, so that any difference
in the results comes from the method (retrieval, fine-tuning, both) and not from the wording.

**What went wrong (found by reading the pilot answers, Entry 36).** The fine-tuned model learned to read this form and write the rest
of the line. The plain model (never trained on the form) did not understand that it should continue the cut line. For the same cut line
(`response = await repository_ratings.`), correct answer `delete_rate(1, session, new_user)`:

| System | What it wrote | Reading |
|---|---|---|
| base model | `from datetime import datetime` | started something new, not a continuation |
| RAG (base + retrieved code) | `The response of the delete_rate function` | wrote a sentence about the code |
| fine-tuned | `delete_rate(1, session, new_user)` | correct |
| hybrid | `delete_rate(1, session, new_user)` | correct |

Over the 50 pilot examples: 33 of 50 base answers were `import` lines and 8 were sentences; RAG wrote comment lines, sentences or copied the
header of the retrieved code (`# --- retrieved from ... ---`). Fine-tuned and hybrid always wrote a code continuation. So the low scores of
base and RAG measured "can it read the form", not "does it know the repository". An analogy for the audience: it is like giving an
exam in a language that only one of the students was taught.

**How the new prompt was chosen.** Three options were considered (Entry 36): (a) give the plain model a normal code-completion prompt
(just the code up to the cursor, with retrieved code placed above it as comments); (b) keep the form but add two worked examples;
(c) keep the form and report the problem. We chose (a) because it is the standard way to ask a code model to continue code, it needs no
hand-picked examples that could bias the result, and it keeps the task, the retrieved code, the decoding and the scoring identical. The
trade-off, stated openly: the text is no longer byte-for-byte identical across systems; each model gets the prompt it can follow.
The fine-tuned and hybrid models keep the form they were trained on.

**What each system now receives (same cut line):**
| System | Prompt |
|---|---|
| base | the code only, ending at the cut: `...response = await repository_ratings.` |
| RAG (A) | retrieved code as `#` comment lines (with the file name), then the code, ending at the cut |
| fine-tuned (B) | the three-box form with the code in the Input box |
| hybrid (C) | the three-box form, with the retrieved code (as comments) at the top of the Input box |

**How it was used and tested.**
- Used: `run_comparison --base-prompt plain` switches base and RAG to the plain prompt; everything else (the 50 examples, retrieval,
  one-line decoding, scoring, intervals) is unchanged. The first pilot's numbers are kept as a documented first attempt.
- Tested without a GPU: 7 automated tests check the prompt text (no "Instruction" box in the plain prompt, the code is last, retrieved
  code comes first as comments, the adapter systems still get the form, the default is unchanged); a dry run on all 50 pilot examples
  builds both prompt types for every example and checks the lengths (plain is shorter by only about 14 tokens, so it cannot change speed
  or memory).
- To be tested on the GPU (Colab, later): rerun base and RAG on the same 50 examples with the plain prompt and read the answers first;
  if they are now code continuations, the scores become meaningful.
- Same lesson for the HumanEval forgetting check: the first run (base 0 of 20) used the form and is invalid; the redo uses the raw
  function stub for both models.

**One-line message for the slides:** "Our first prompt only suited the fine-tuned model, so the baselines looked unfairly bad. We
fixed it by giving each model the kind of prompt it understands while keeping the same task, retrieved code and scoring."

### Commands for the next Colab session (Phase 2 of `docs/next_steps_part3.md`; run after pushing)
```python
# C1: base and RAG with the plain prompt, same 50 examples (read results/pilot_main_plainbase/predictions.jsonl first)
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain
# C2: forgetting check, plain stub, all 164 problems (Colab only; runs model-generated code)
!python -m src.evaluation.forgetting_check --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --allow-exec
# C3: the 68-example staleness test, both views (add --base-prompt plain to every command)
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant
!python -m experiments.run_comparison --adapter experiments/finetuned_model/crosscodeeval/v2 --4bit --base-prompt plain --subset new_relevant --view staleness
```
The first command writes to `results/pilot_main_plainbase/`; the new-relevant runs to `results/new_relevant_main_plainbase/` and
`results/new_relevant_staleness_plainbase/`; the forgetting result to `results/forgetting_humaneval_plain.json`.
Expected time: C1 about 7 minutes, C2 about 15 to 25 minutes, C3 about 6 to 8 minutes per view.

### Status
Completion estimate unchanged at about 65% (Entry 36); the local building and testing for the rerun is done, the GPU results are not. Nothing
committed or pushed (you commit and push before Colab can use the new options).

## Entry 38: Scope for the upcoming presentation, agreed with the supervisor (2026-11-23)
- **Asked / decided:** the supervisor advised that, for the upcoming presentation, the pilot (50 CrossCodeEval examples) is completed with the
  fixed prompts (Entries 36 and 37) and given a basic evaluation, together with the comparison with the literature (Wang et al.). Heavier work
  (full 543-example run, RepoBench fine-tuning and completion, RAFT-style retrain, noise and top-k sweeps, multiple seeds) moves to the
  thesis wrap-up. This is a scope change to record (plan Section 11).
- **Done:** wrote `docs/next_steps_presentation.md`: local push, then one Colab session (core: pilot main and staleness with
  `--base-prompt plain`; recommended extras: BM25, the 68-example staleness test, HumanEval plain-stub forgetting check), a gate after the
  first run (base and RAG must now write code continuations, otherwise switch to few-shot), the local evaluation to produce, and the comparison
  with the literature (direction of effects only). Nothing run; no code changed in this entry.
- **Effect on the completion estimate:** the percentage in Entry 36 (about 65%) measures the full thesis project. For the presentation scope
  the remaining work is the Colab session above (about 30 to 60 minutes of GPU) and the local analysis; the rest is thesis wrap-up.

## Entry 39: Project Part 1 versus Part 2, and the completion estimate for Part 1 (2026-11-23)
- **Asked:** treat the current work as "Project Part 1" (for the upcoming presentation), define the scope accordingly, give the next
  steps, and keep the Colab steps in `docs/colab_steps_new.md`.
- **Done:** defined the two parts below; re-weighted the progress estimate for Part 1; wrote `docs/colab_steps_new.md` (setup, a gate
  after a 5-example test, the pilot in main and staleness views with the plain prompt, optional BM25 / 68-example staleness / HumanEval
  extras, finish). `docs/next_steps_presentation.md` stays as the overview and points to it for the Colab cells. No code changed; nothing run.

### Scope
**Part 1 (presentation, pilot level; in progress):** leakage-safe file-level splits for both datasets; fine-tuning corpora; per-repository
indexes; retrieval comparison (dense vs BM25 vs random) on both datasets; one QLoRA fine-tuning run on CrossCodeEval with a base-vs-adapter loss
comparison; a four-system pilot (base, RAG, fine-tuned, hybrid) on 50 CrossCodeEval examples with the fixed prompts, main and staleness
views; a basic evaluation (scores with intervals, paired differences, cost, example outputs); comparison with the literature (Wang et al.) by
direction of effect; presentation and progress report. Optional inside Part 1: BM25 pilot, the 68-example staleness test, HumanEval plain-stub
forgetting check.
**Part 2 (thesis wrap-up, later):** full 543-example CrossCodeEval comparison (both views) with hit-vs-miss analysis; RepoBench fine-tuning and
completion; noisy-context and top-k sweeps; RAFT-style retrain decision; multiple fine-tuning seeds; numeric recommendations for the decision
question; moving seeds and constants into `config.yaml`; thesis chapters.

### Part 1 completion estimate: about 78% (read as 75 to 80%; presentation and report writing not counted)
A judgement, same method as Entries 23, 29, 31 and 36, with weights re-set for Part 1:
| Workstream (Part 1) | Weight | Done | Contribution |
|---|---|---|---|
| Plan, literature analysis, hypotheses | 8% | 100% | 8.0 |
| CrossCodeEval data | 15% | 100% | 15.0 |
| RepoBench data (split, corpus, sample; used for retrieval only in Part 1) | 10% | 100% | 10.0 |
| Pipeline code (new prompt options built and tested locally, not yet run on a GPU) | 15% | 95% | 14.3 |
| Retrieval (both datasets indexed and compared) | 12% | 95% | 11.4 |
| Fine-tuning (CrossCodeEval adapter, loss comparison) | 10% | 100% | 10.0 |
| Four-system pilot with fixed prompts (first pilot done; base and RAG rerun and staleness view pending) | 20% | 30% | 6.0 |
| Basic evaluation and comparison with the literature (tooling and literature analysis done; results analysis pending) | 10% | 30% | 3.0 |
| **Total** | 100% | | **77.7** |
- For comparison: the whole thesis project is about 65% (Entry 36); Part 1 is further along because the heavy items (full run, RepoBench training) are
  outside it. The remaining Part 1 work is the Colab session (about 30 to 60 minutes of GPU) and the local analysis; the percentage should
  reach about 95% once the pilot rerun and its analysis are done (the rest is the presentation and report themselves).
- For slides: show "Part 1: about 78% (75 to 80%)" and "Part 2: planned" with the Part 2 list above.

## Entry 40: Part 1 pilot with the fixed (plain) prompts: all Colab runs finished (2026-11-23; raw console output in `docs/new_results_pilot_run_from_colab`)
- **Asked:** go through the new Colab results and log the findings; then list which files to copy over and where.
- **Source:** the pasted console output only. The result folders (and so `predictions.jsonl`) are **not copied here yet**, so everything below is read
  from the printed metrics; the example-level checks (what RAG writes, the empty RAG answer, paired tests) are pending the copy.
- **Runs completed (all ran without errors, Colab T4, 4-bit, adapter v2):** dry run (`DRY RUN PASSED`; plain-prompt lengths median 423 and 2,138
  tokens); 5-example gate test (`plain_test`); pilot main and staleness with `--base-prompt plain` (50 examples each); BM25 pilot; the 68-example
  staleness test in both views (log confirms "new_relevant subset: 68 TEST examples"); HumanEval forgetting check on all 164 problems.
  Setup was repeated after the tracked-`results/` problem (fixed by removing the cloned `results/` in Cell 2, see `docs/colab_steps_new.md`).

### 1. The gate passed: the prompt-format artifact is confirmed as the cause (pilot, n=50, main view)
| System | EM | Edit sim. [95% CI] | Identifier acc. | CodeBLEU | First pilot (instruction prompt) edit sim. |
|---|---|---|---|---|---|
| base (plain prompt) | 0.04 | 0.494 [0.426, 0.559] | 0.298 | 0.237 | 0.236 |
| RAG (plain prompt) | 0.02 | 0.387 [0.311, 0.468] | 0.217 | 0.140 | 0.226 |
| fine-tuned (instruction) | 0.08 | 0.613 [0.549, 0.680] | 0.414 | 0.213 | 0.613 (identical) |
| hybrid (instruction) | 0.14 | 0.644 [0.570, 0.715] | 0.490 | 0.214 | 0.644 (identical) |
- The plain prompt moved the base from 0.236 to 0.494 edit similarity (identifier accuracy 0.018 to 0.298; CodeBLEU 0.068 to 0.237) and RAG from
  0.226 to 0.387. The fine-tuned and hybrid rows reproduce the first pilot exactly (same prompt, greedy decoding), a consistency check that passed.
  In the 5-example gate test base and RAG wrote code lines (`assistant_name, "assistant")`, `anticipate_action(inp))`), so the instruction-wrapper
  explanation in Entries 36 and 37 was right. **The first pilot's base and RAG rows are retired; these are the numbers to use.**
- The gap between fine-tuned and base shrinks from 0.38 to 0.12 edit similarity once the base is prompted properly: most of the first gap was format.
  What is left is still a real difference (fine-tuned 0.613 vs base 0.494; intervals only just overlap; paired test pending).

### 2. New finding that goes against the first hypothesis ordering: retrieval alone hurt the frozen model
- RAG (0.387) is **below** the base model (0.494) in edit similarity, identifier accuracy (0.217 vs 0.298) and CodeBLEU (0.140 vs 0.237): adding the
  5 retrieved chunks made the frozen model worse, in the main view, the staleness view (RAG 0.403) and with BM25 (0.386). In Wang et al. RAG was the
  largest single gain (their 1.5B EM 24.5 to 55.8 with BM25). One empty RAG prediction was seen in the gate test.
- Not yet explained. Candidates to check once the predictions are here (untested): the model copies or continues the retrieved comments instead of the
  cut line; the five chunks (about 1,700 more tokens, truncated chunks of up to 1,200 characters) push the cursor line far from the model's attention;
  chunks are pasted as `#` comments (a format the model rarely sees); retrieval picks files that are related but whose style differs. This is the
  main item for the evaluation write-up and for the thesis wrap-up (for example a different way to place chunks, or fewer chunks).
- Hybrid vs fine-tuned: hybrid is higher in every run (main +0.031 edit sim., EM 0.14 vs 0.08) but the intervals overlap heavily at n=50 (not significant).
  So retrieval helps the adapted model slightly and hurts the frozen model; both are small-sample statements.

### 3. Staleness, pilot view (50 examples; NEW files added to the retrieval index)
Base 0.494 and fine-tuned 0.613 are unchanged (no retrieval); RAG 0.387 to 0.403; hybrid 0.644 to 0.657 (EM 0.14 to 0.16, CodeBLEU 0.214 to 0.288).
Retrieval recall@3 0.893 to 0.783 and MRR 0.764 to 0.750. Differences are inside the intervals.

### 4. The staleness test proper: the 68 examples whose relevant file is a NEW file (H3), main view vs staleness view
| System | Edit sim., main view | Edit sim., staleness view | EM main / staleness | Identifier acc. main / staleness |
|---|---|---|---|---|
| base | 0.457 | 0.457 | 0.015 / 0.015 | 0.293 / 0.293 |
| RAG | 0.384 | 0.350 | 0.015 / 0.029 | 0.219 / 0.191 |
| fine-tuned | 0.604 | 0.604 | 0.088 / 0.088 | 0.403 / 0.403 |
| hybrid | 0.640 [0.585, 0.694] | 0.695 [0.644, 0.746] | 0.088 / 0.162 | 0.478 / 0.551 |
- Direction as hypothesised: when the relevant new file is available to retrieval (staleness view) the hybrid improves (edit sim. +0.055, exact match
  0.088 to 0.162, identifier accuracy +0.07, CodeBLEU 0.374 to 0.444), while the fine-tuned model, which never saw that file, cannot change. This is the
  first evidence for H3's mechanism. **Caveats:** the hybrid intervals overlap (0.585 to 0.694 vs 0.644 to 0.746); a paired test over the same 68
  examples is needed; in the main view only 33 of the 68 have any relevant file in the pool, so retrieval metrics are on 33 queries there and 68 in the
  staleness view; RAG alone did not benefit (0.384 to 0.350), consistent with section 2.
- Retrieval in this subset (staleness view, 68 queries): MRR 0.716, recall@1 0.33, recall@3 0.77, recall@5 0.935 (main view, 33 queries: MRR 0.822).

### 5. BM25 vs dense for completion (pilot, plain prompt)
Retrieval is better with BM25 (MRR 0.840 vs 0.764; recall@3 0.977 vs 0.893; retrieval time 207 ms vs 1,170 ms for 50 examples), but completion is the
same: RAG edit sim. 0.386 vs 0.387, hybrid 0.640 vs 0.644, identifier accuracy 0.217 vs 0.217 (RAG), 0.469 vs 0.490 (hybrid). Better ranking did not help.

### 6. Forgetting check, valid this time (HumanEval, all 164 problems, plain stub, greedy, same prompt for both models)
Base 66/164 = pass@1 0.402; fine-tuned 63/164 = 0.384; relative change **-4.5%** (3 problems). The base now scores about 40%, which also confirms the old 0/20
was the prompt artifact. This is much smaller than Wang et al.'s -24.1% average (full fine-tuning of larger models on 120,000 files); here the LoRA
adapter trained on about 9,400 examples left general code ability nearly unchanged. With n=164 the 95% interval on a 0.402 pass rate is about +-0.07, so
the difference is not statistically distinguishable from 0 (a paired test is pending). [writing note]

### 7. Cost (pilot, main view, per example, one T4, 4-bit; one process)
Average time: base 1.61 s, RAG 1.72 s, fine-tuned 1.91 s, hybrid 2.24 s (retrieval itself about 23 ms per example with dense, 4 ms with BM25).
Peak GPU memory: 2.01 GB (base, fine-tuned), 2.14 GB (RAG, hybrid; 1.52 and 1.67 GB with BM25, where UniXcoder is not loaded). So retrieval adds about
0.14 GB and about 0.1 to 0.3 s per example; prompts with retrieval are about 2,100 tokens against about 430. The fine-tuned model is about 0.3 s per
example slower than the base (unmerged 4-bit LoRA adapter; cause not tested). Training cost was 3 h 29 min and 8.7 GB (Entry 18).

### 8. Preliminary comparison with Wang et al. (direction only; pilot n=50, different language, scale and method)
| Their finding | This pilot |
|---|---|
| RAG beats the base model by a lot | **Differs**: RAG was below the base (0.387 vs 0.494) |
| Fine-tuning beats the base model | Matches: 0.613 vs 0.494 (gap smaller than with the wrong prompt) |
| Combination is best | Matches in direction (hybrid highest everywhere), not significant vs fine-tuned at n=50 |
| BM25 beats dense retrieval | Matches for retrieval quality (both datasets); no difference for completion |
| Retrieval greatly increases input length and slows inference | Matches: about 2,100 vs 430 tokens; +0.3 s per example |
| Fine-tuning hurts general code ability (-24.1% HumanEval) | Much smaller here: -4.5% (3 of 164 problems) |
New-file mechanism (not in their study): hybrid improved on files only retrieval could know (+0.055 edit similarity).

### What this changes
- The earlier concern is resolved: the pilot is now valid for all four systems. Remove the "prompt-format artifact (open)" caveat from the slides and the web
  prompt; keep the instruction-prompt numbers only as the documented first attempt.
- **Part 1 completion estimate: about 92% (read as 90 to 94%)** (78% in Entry 39). Pilot with fixed prompts now about 90% (all runs done, analysis of the
  predictions and paired tests pending), basic evaluation and literature comparison about 55% (numbers collected, paired analysis, example outputs and
  charts pending). The remaining 8% is the local analysis. Whole-thesis estimate: about 72% (was 65%), because the pilot, staleness, BM25, 68-example and
  forgetting runs are done; the full 543-example run, RepoBench training and completion and the other Part 2 items remain.
- **Pending local steps once the folders are copied:** read the predictions (why RAG hurts; the empty RAG answers; examples to show), `analyze_predictions`
  on each run, paired comparisons across runs (main vs staleness on the 68 examples; plain vs instruction prompt), McNemar-style paired test for
  HumanEval, a pilot results table with intervals, example outputs, charts, then refresh the web prompt and the slides.

## Entry 41: Local analysis of the plain-prompt pilot results (2026-11-23)
- **Asked:** after copying the Drive results into `results/`, give the next local steps before the presentation (Friday) and the percentage done.
- **Done (read-only analysis; no code or data changed):** confirmed that all seven items arrived (`plain_test`, `pilot_main_plainbase`,
  `pilot_staleness_plainbase`, `pilot_main_bm25_plainbase`, `new_relevant_main_plainbase`, `new_relevant_staleness_plainbase`,
  `forgetting_humaneval_plain.json`; row counts 5, 50, 50, 50, 68, 68); ran `analyze_predictions` on the five run folders (it wrote an `analysis.json` next
  to each `predictions.jsonl`); wrote throw-away paired-bootstrap checks (10,000 resamples, seed 42, not saved in the repo) for comparisons across runs;
  an exact McNemar test for HumanEval; classified the RAG answers.

### 1. Paired comparisons, pilot main view, plain prompt (n=50, 95% bootstrap CI of the paired difference in edit similarity)
| Comparison | Difference | Reading |
|---|---|---|
| fine-tuned minus base | +0.120 [0.061, 0.187] | significant: fine-tuning helps (exact match +0.04 [0.00, 0.10]) |
| RAG minus base | -0.106 [-0.172, -0.046] | significant: RAG is **worse** than the base model |
| hybrid minus RAG | +0.257 [0.168, 0.347] | significant |
| hybrid minus fine-tuned | +0.031 [-0.032, 0.089] | not significant (exact match +0.06 [-0.04, 0.16]) |
| RAG minus fine-tuned | -0.226 [-0.310, -0.146] | significant: fine-tuning beats RAG alone |
The same picture holds in the staleness view and with BM25 (RAG minus base -0.090 and -0.108, both significant; hybrid minus fine-tuned +0.044 and +0.027, both not).
- **Prompt effect, same 50 examples, plain minus instruction prompt:** base +0.257 [0.191, 0.318]; RAG +0.161 [0.089, 0.239]; fine-tuned and hybrid exactly 0
  (as they should). So the first pilot's base and RAG rows were about 0.26 and 0.16 too low because of the prompt, now measured with intervals.

### 2. The staleness test (68 examples whose relevant file is a NEW file), paired across views (staleness view minus main view)
| System | Edit similarity | Exact match |
|---|---|---|
| base, fine-tuned | 0.000 (no retrieval, identical) | 0.000 |
| RAG | -0.034 [-0.085, +0.018] | +0.015 [0.000, 0.044] |
| hybrid | **+0.055 [+0.015, +0.103]** | **+0.074 [+0.015, +0.132]** |
- The hybrid's answer changed on 27 of 68 examples: 19 improved, 8 got worse. The relevant new file was in the top-5 chunks for 66 of 68 examples (staleness view).
- In the staleness view the hybrid beats the fine-tuned model by **+0.091 [0.036, 0.146]** edit similarity (in the main view +0.037 [-0.009, 0.085], not significant),
  and the fine-tuned model cannot improve, because it never saw those files. This is the first statistically supported evidence for the mechanism behind H3:
  retrieval gives access to new code that fine-tuning cannot. Caveats: n=68 from 35 repositories, one model, one seed; RAG alone did not benefit; the
  fine-tuned model also loses nothing in this subset (0.604), so this shows what retrieval adds, not that fine-tuning degrades on new files.

### 3. Why RAG alone looks bad: part of it is empty and cut-off answers (new finding, cause not yet known)
- RAG (frozen model with retrieved chunks) returns an **empty first line in 5 of 50** pilot answers (4 in the staleness view, 8 with BM25) and several cut-off words
  (`und` for `set_graph(self.old_g)`, `quer`, `che`); the base, fine-tuned and hybrid models return at most 0 or 1 such answers. Empty and cut-off answers
  score about 0 and pull the RAG mean down. On the 45 non-empty answers RAG is 0.430 and the base 0.499 on the same examples, so RAG is still lower, but the gap is
  about 0.07 instead of 0.11.
- RAG was worse than the base on 18 of 50 examples, better on 10, equal on 22. Where RAG helps it is by picking up a name from the retrieved code
  (`OverlappingWindowBasedLoader(window,overlap)` vs the reference `WindowBasedLoader(window=window, ...`).
- Likely causes (untested): the model ends its answer (new line or end-of-text) too early when the prompt is a long block of `#` comments followed by the code;
  or it spends its first tokens on a comment-style continuation. The saved predictions contain only the first line, so the raw completion and the stop reason
  are not available. A short diagnostic run (RAG only, saving the raw text, number of generated tokens and the reason it stopped) would settle it.
- Consequence for how to present RAG: the measured numbers are valid as run, but "RAG hurts" must be stated with this caveat: with this prompt design (chunks as
  comments), the frozen 1.5B model often stops early or copies; it is not evidence that retrieval is useless. The hybrid, which was fine-tuned on the code-continuation
  format, does not show the empty answers and does benefit from retrieval of new files (section 2).

### 4. Forgetting check, paired test
Base passes 66 of 164, fine-tuned 63; base-only 13 problems, fine-tuned-only 10; exact McNemar p = 0.68. No evidence of forgetting after this adapter
(relative change -4.5%, not significant); Wang et al.'s -24.1% was full fine-tuning of larger models on 120,000 files.

### 5. Hit versus miss
Still not usable at n=50 (main view 2 misses; staleness view 4; BM25 view 0; 68-example subset 1 and 2 misses). Leave it to the full run (thesis wrap-up).

### Status and percentages (as of 2026-11-23)
- **Project Part 1: about 95% done (read as 93 to 97%)**, from 92% (Entry 40). Weights as in Entry 39: pipeline now validated on a GPU (100%), the four-system pilot with
  fixed prompts done including a diagnosis of why RAG underperforms except for the raw-output check (95%), the basic evaluation and literature comparison done except
  for charts and example outputs (80%). Total 96.4, rounded down because of the unexplained RAG empty answers. Presentation and report writing are not counted.
- **Whole thesis project: about 73%** (72% in Entry 40; the full 543-example run, RepoBench training and completion, and the remaining sweeps stay in Part 2).
- **Remaining Part 1 work (all local except the optional diagnostic):** (a) optional Colab diagnostic for the empty RAG answers (about 5 to 10 minutes of GPU; code
  change first); (b) result tables and charts for the slides; (c) 5 to 6 example outputs side by side; (d) update `docs/results_summary.md` and `docs/claude_web_prompt.md`
  with the final numbers and the Part 1 framing; (e) commit and push (including `git rm -r --cached results`); (f) draft, review and rehearse the presentation.

## Entry 42: Diagnostics built, slide charts and example outputs generated; a second prompt problem found in the frozen RAG system (2026-11-23)
- **Asked:** do steps 1 to 4 of Entry 41 (diagnostic option, charts, example outputs, documents) and say whether the Colab step should come first.
- **Done:**
  1. **Diagnostic option** `run_comparison --save-raw`: saves each answer's raw completion (special tokens shown), the number of generated tokens and why
     generation stopped (`eos`, `newline` or `max_tokens`); same decoding, so the predictions do not change; the output folder gets `_raw`. New
     `src/evaluation/inspect_raw.py` summarises it (no GPU). New `generation.classify_stop` and `complete_detailed`.
  2. **Two fixes to test for the frozen RAG system** (both off by default, nothing changes unless asked): `--suppress-fim` forbids Qwen's
     fill-in-the-middle and file-separator tokens during generation (folder suffix `_nofim`); `--rag-format qwen_repo` gives the retrieved files in Qwen2.5-Coder's
     own repository-level layout (`<|repo_name|>`, `<|file_sep|> path`, then the file being completed; folder suffix `_qwenrepo`); it applies only to the
     frozen RAG system, the base and the adapter systems keep their prompts. Checked locally with the real tokenizer: the six marker tokens exist (ids
     151659 to 151664) and the repository markers tokenise as single tokens.
  3. **Slide charts** `src/evaluation/plot_pilot_results.py` (six figures in `results/figures/pilot_*.png` plus `pilot_numbers.csv` with every plotted number): pilot
     by system, main vs staleness view; prompt effect (instruction vs plain); the 68-example staleness test with the paired change; a forest plot of the paired
     differences; cost; HumanEval forgetting. Colours were checked with the dataviz skill's validator (passes; the aqua mark is below 3:1 on white, so every bar
     carries its value label and the table is in the CSV). The charts use the same bootstrap as `analyze_predictions` (2,000 resamples, seed 42), so the numbers
     match the log. I looked at every figure after rendering and fixed a legend that covered a value label.
  4. **Example outputs** `src/evaluation/example_outputs.py` -> `docs/example_outputs.md`: six cut lines with the four systems' answers, chosen by fixed
     rules written in the file (not by hand): fine-tuning learns the repository's calls; retrieval reaches a new file the adapter never saw (3560, hybrid 0.08 to
     1.00 edit similarity); a RAG failure; retrieval helping the frozen model (3095); a runaway hybrid answer (2413); a case hard for every system.
  5. **Tests:** 39 pass (36 before; 3 more for the repository-format prompt, where each format applies, and the token-id helper). Dry run unchanged.
  6. **Colab:** a follow-up session (section F of `docs/colab_steps_new.md`): the raw diagnostic, then the two fixes, RAG only, three runs of about 3 minutes each.
  7. **Numbers corrected in Entry 41** (my first throw-away bootstrap used a different seed than the analysis script): prompt effect base +0.257 [0.191, 0.318], RAG
     +0.161 [0.089, 0.239]; staleness change for the hybrid +0.055 [0.015, 0.103] (exact match +0.074 [0.015, 0.132]) and RAG -0.034 [-0.085, 0.018]. Conclusions unchanged.

### New finding: the frozen RAG system writes the fill-in-the-middle token as its answer
- With the plain prompt, RAG's answer is the literal text `<|fim_suffix|>` in **6 of 50** pilot examples (6 in the staleness view and 6 with BM25 as well), and in 14
  and 18 of the 68 staleness-test examples (main and staleness view). In the first pilot (instruction prompt) it never happened, and the base, fine-tuned and
  hybrid models never write it. Together with the 5 empty first lines, **11 of 50 (22%) RAG answers in the pilot are unusable**, and the cut-off words (`und`,
  `quer`, `che`) are a further sign.
- Why it is visible: that token decodes as text even with special tokens skipped (checked with the real tokenizer); the end-of-text token is skipped, so an
  immediate end shows as an empty answer. Likely cause (untested): the comment-wrapped chunks look like a multi-file repository to a model trained for
  fill-in-the-middle and repository-level completion, so it answers with a format marker or stops. The `--save-raw` run will show it.
- **Consequence:** the statement "RAG is below the base model" (Entries 40 and 41) is still what was measured, but it is now explained in large part by a prompt-format
  failure of the frozen model, not by retrieval being unhelpful. On the 39 pilot examples where RAG gave a usable answer the comparison is closer (computed after
  the Colab fix). Do **not** present "retrieval hurts" as a finding; present it as "the frozen model needs a prompt in its own repository format; with the comment
  format 22% of its answers failed". The hybrid is not affected (it was fine-tuned on code continuation), and its staleness gain stands.

### Answer to "Colab first or build first?"
Everything that can be built locally is built (the diagnostics and both fixes are in one push). The next Colab session is the follow-up in section F (about 15 to 20
minutes of GPU): it can run as soon as the code is pushed, in parallel with the writing of the slides. The charts and examples regenerate in seconds if a RAG number changes
(`python -m src.evaluation.plot_pilot_results`, `python -m src.evaluation.example_outputs`).

### Status
Project Part 1: about **96%** (94 to 98%): the analysis, charts and examples are done; the open item is the RAG fix (one short Colab session) and then refreshing the RAG
numbers in the documents. Whole thesis: about 74%.

## Entry 43: Supervisor's review requests: no-GPU part done (A1 to A4), Colab steps written for B1 and B2 (2026-11-25)
- **Asked:** the supervisor reviewed the progress report and asked for (1) a full-scale evaluation, (2) the RAG formatting problem fixed, (3) clearer implementation and
  reproducibility details, (4) a clearer account of the adapter setup and fairness (`docs/review_sugesstions`). Do the no-GPU part first, then write the Colab steps in a
  separate file; everything produced goes to `results/additional_results/`.
- **Done (no GPU; nothing trained or generated; no existing result changed):**
  - A1: `docs/reproducibility.md` (code commit `2650823`, config, adapter v2 training settings, trainer-state summary, software versions, run commands, fairness notes).
    Copies and parsed files in `results/additional_results/`: `config_snapshot.yaml`, `adapter_v2_config.json`, `trainer_state_summary.json`, `pip_freeze_local.txt`.
  - A2 and A3: new `src/evaluation/supervisor_checks.py` -> `supervisor_checks.json`, `training_examples_per_repo.csv`.
  - A4: new `src/evaluation/functional_proxies.py` -> `results/additional_results/functional_proxies.csv` (copy: `results/functional_proxies.csv`), one row per run folder and system.
  - B1 and B2: `docs/colab_new_steps_file.md` (not run).
- **A2 answer:** adapter v2 is **one global adapter** trained on the pooled BASE-file corpus of all 206 repositories. Training examples per repository: **min 10, median 39, max 180**
  (mean 45.5, total 9,378); validation per repository: min 1, median 5, max 20 (total 1,059). Every repository has training examples.
- **A3 answer:** the 50 pilot examples were drawn (seed 42) from the **292** TEST examples that have a relevant file in the BASE pool, **not** from all 543 (checked: all 50 are TEST,
  all 50 are among the 292, 40 repositories). So the pilot is favourable to retrieval compared with the full set; 251 of the 543 have no relevant file in the pool.
- **A4 results (plain-prompt runs, which are the valid ones; % of answers; "parses" = last prompt line plus answer parses with `ast` after closing open brackets, a rough proxy;
  "ids in repo" = share of non-empty answers whose identifiers, minus Python keywords and builtins, all occur in the repository's benchmark files):**

  | Run (n) | System | empty | `<\|fim..\|>` | parses | ids all in repo |
  |---|---|---|---|---|---|
  | pilot main (50) | base | 0.0 | 0.0 | 98.0 | 16.3 |
  | | RAG | 10.0 | 12.0 | 76.0 | 23.7 |
  | | fine-tuned | 0.0 | 0.0 | 100.0 | 53.1 |
  | | hybrid | 0.0 | 0.0 | 100.0 | 62.0 |
  | pilot staleness (50) | RAG / hybrid | 8.0 / 0.0 | 12.0 / 0.0 | 76.0 / 100.0 | 23.1 / 64.0 |
  | 68 new-file examples, staleness view | RAG / hybrid | 1.5 / 0.0 | 26.5 / 0.0 | 63.2 / 100.0 | 39.1 / 73.5 |

  The counts reproduce Entry 42 (RAG: 5 empty and 6 `<|fim_suffix|>` of 50; 14 and 18 fim of 68). Base, fine-tuned and hybrid never produce the marker. Runs with the first
  (instruction) prompt are in the CSV too but are retired (their base and RAG rows measure the prompt artifact, e.g. 2% parse).
- **Caveats (state them if these numbers are shown):** the "parses" and "ids in repo" columns are proxies, not tests of correctness; one-line answers can fail to parse alone yet be fine in the
  file; new variable or keyword names are legitimate but count as "not in repo"; the fine-tuned and hybrid models were trained on the same repositories' BASE files, so a higher share of known
  names is expected and is the effect being measured, not evidence of correctness. Repository text = only the files that appear in the benchmark. Pilot sizes (50, 68) are small.
- **Not done / open:** B1 (RAG fix on 50 and 68 examples, S0 to S3) and B2 (all 543 TEST examples, four systems, both views) need the GPU: steps in `docs/colab_new_steps_file.md`.
  Session 1 first (about 45 to 60 minutes, an estimate); Session 2 (about 2 hours, an estimate from pilot timings) only after the best RAG setting is chosen locally. The Colab `pip freeze`,
  Python and torch versions and the commit used were never recorded for the earlier runs; step A6 of the new guide records them. No retraining of the adapter is planned: fairness (item 4) is
  addressed in `docs/reproducibility.md`, section 7. Still open from Entry 41: `git rm -r --cached results`, and committing the new files (`src/evaluation/supervisor_checks.py`,
  `src/evaluation/functional_proxies.py`, `docs/reproducibility.md`, `docs/colab_new_steps_file.md`, `docs/review_sugesstions`): **I do not commit; please do.**
