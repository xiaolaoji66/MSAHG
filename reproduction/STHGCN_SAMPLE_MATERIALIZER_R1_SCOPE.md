# STHGCN Sample Materializer R1 — Prospective Scope

Date: 2026-09-10

## 1. Purpose

This scope authorizes an add-only, score-free materializer for the public NYC
and TKY records distributed by STHGCN. The output is a deterministic sample
surface for a later, separately registered MSAHG-on-STHGCN experiment.

This stage does not train or run STHGCN, MSAHG, or GUGEN; does not construct a
hypergraph; does not define MSAHG scenario labels; and does not compute loss,
MRR, accuracy, ranking, or checkpoint selection.

## 2. Frozen authority

- Reproduction repository: `https://github.com/xiaolaoji66/MSAHG`.
- Parent result commit:
  `f09a5016958a3495764f55cd69f93d5bc5e147bb`.
- Qualified protocol implementation:
  `f606afafd6b71e3fa34142207a8dc162d71cbe15`.
- Protocol registration:
  `87e21b86f39f7491e2460f0647ace0e14d6fbb17`.
- STHGCN repository:
  `https://github.com/alipay/Spatio-Temporal-Hypergraph-Model`.
- STHGCN commit:
  `27b595846d29019799485985bff49f9ed02c4ade`.
- STHGCN NYC archive SHA256:
  `974bc90b3e0cdec6ec29a0a953ac41d3f81880e17bdd4c7c0cd94f2afc9e17d2`.
- STHGCN TKY archive SHA256:
  `823cd400a8d67b360c50217c1e8141e566a2b804ca8af9feac9ff9c0f76220c7`.

The STHGCN source tree is read-only evidence. No source file in that tree may
be edited or imported as mutable runtime authority.

## 3. Portable reference semantics

R1 freezes the intended sample protocol as an explicit, version-independent
reference implementation. It does not promise byte identity with artifacts
created by an unspecified legacy Pandas environment.

### 3.1 Shared rules

- Use stable ordering with source ordinal as the final tie breaker.
- Fit user, POI, category, hour, and weekday vocabularies on training records
  only.
- Map validation/test values unseen during training to the registered padding
  ID and exclude validation/test targets whose user or POI is unseen.
- The first event of every trajectory is not a prediction target.
- Validation and test retain only the final non-first event of each trajectory
  as an eligible endpoint.
- Preserve every post-filter event in `sample.csv`, including records marked
  `ignore`, so future causal graph materialization can be separately audited.
- Produce deterministic CSV, JSON mapping, receipt, and SHA256 files.

### 3.2 NYC

- Preserve split membership from `raw/NYC_train.csv`, `raw/NYC_val.csv`, and
  `raw/NYC_test.csv` exactly.
- Preserve the published trajectory identifier before encoding it.
- Encode trajectory IDs over the complete combined NYC source surface.
- Use zero-based train vocabulary IDs and padding ID equal to vocabulary size,
  matching the STHGCN NYC path.

### 3.3 TKY

- Parse the STHGCN-distributed `dataset_TSMC2014_TKY.txt` with Latin-1 input
  encoding and compute local time as UTC plus the supplied minute offset.
- Retain POIs with more than 9 records, then retain users with more than 9
  records after POI filtering.
- Sort the filtered records globally by local timestamp and source ordinal;
  assign the first `floor(0.8N)` records to train, the next records through
  `floor(0.9N)` to validation, and the remainder to test.
- This explicit positional assignment is the authority. The STHGCN chained
  assignment in `preprocess/file_reader.py` is recorded as a source defect and
  is not replayed as a protocol rule.
- Remove an event only when it has neither a same-user predecessor nor a
  same-user successor within 24 hours. A gap exactly equal to 24 hours is
  considered connected.
- After isolation filtering, sort by user, local timestamp, and source ordinal;
  start a new trajectory on user change or a gap strictly greater than 1,440
  minutes.
- Use train vocabulary IDs shifted by one and padding ID zero, matching the
  STHGCN TKY path.

## 4. Outputs

For each dataset the materializer writes a fresh, non-overwriting directory:

- `sample.csv`: the complete post-filter record surface with split/ignore
  state and deterministic IDs;
- `train_sample.csv`, `validate_sample.csv`, and `test_sample.csv`: eligible
  next-POI samples only;
- `label_encoding.json`: ordered training vocabularies and padding IDs;
- `materialization_receipt.json`: input identities, counts, invariants,
  decision, and interpretation boundary;
- `SHA256SUMS`: raw hashes for all preceding outputs.

The output directory must not already exist. A mismatch or partial output is
preserved as evidence and returns non-zero; it must not be overwritten by an
automatic retry.

## 5. Qualification gates

- `M0_AUTHORITY`: exact parent, STHGCN commit, and archive identities.
- `M1_FRESH_OUTPUT`: no overwrite and no implicit retry.
- `M2_PORTABLE_SPLIT`: NYC file splits and explicit TKY chronological split.
- `M3_FILTER_AND_SESSION`: exact filtering, isolation, and session predicates.
- `M4_TRAIN_ONLY_VOCABULARY`: mappings are fit on train records only.
- `M5_TARGET_CONSTRUCTION`: first-event exclusion and final-event dev/test
  endpoint.
- `M6_COLD_START`: unseen validation/test user/POI endpoints are excluded.
- `M7_DETERMINISM`: stable tie handling and repeatable synthetic output.
- `M8_SOURCE_IMMUTABLE`: STHGCN worktree commit and cleanliness unchanged.
- `M9_NO_GRAPH`: no graph or hypergraph is materialized.
- `M10_NO_SCENARIOS`: no MSAHG scenario label is created.
- `M11_SCORE_FREE`: no score, loss, metric, training, or checkpoint activity.
- `M12_COUNT_WITNESS`: observed counts are compared with registered STHGCN
  reported statistics, without result-driven rule changes.
- `M13_FAIL_CLOSED`: any failed gate produces `HOLD` and a non-zero exit.

## 6. Count interpretation

The STHGCN README reports 103,941 NYC and 405,000 TKY post-preprocessing
check-ins, with 14,130 and 65,499 trajectories respectively. These are
qualification witnesses, not tuning targets. Exact agreement supports the
portable reconstruction. Disagreement produces `HOLD / COUNT_MISMATCH`; it
does not authorize changing the frozen predicates.

Eligible train/validation/test endpoint counts are descriptive receipt fields,
not paper claims and not optimization objectives.

## 7. Execution boundary

Authorized:

- add-only materializer documentation, registry, implementation, runner, and
  synthetic tests;
- score-free reading and materialization of the frozen public NYC/TKY archives;
- receipt/checksum generation and independent count/invariant audit;
- add-only archival of PASS or HOLD evidence.

Not authorized:

- STHGCN/MSAHG/GUGEN training or inference;
- recommendation metrics or target scoring;
- graph/hypergraph construction;
- scenario-label construction;
- model adaptation, tuning, or comparison;
- paper-table reproduction claims;
- changing predicates to force reported-count agreement.

## 8. Mechanical state

```text
STHGCN_SOURCE_PROTOCOL_AUDIT = PASS
SAMPLE_MATERIALIZER_R1       = PROSPECTIVE / SCORE_FREE_AUTHORIZED
GRAPH_MATERIALIZATION        = NOT_AUTHORIZED
SCENARIO_LABELS              = NOT_REGISTERED
MODEL_TRAINING_OR_SCORING     = NOT_AUTHORIZED
```
