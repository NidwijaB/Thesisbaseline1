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
