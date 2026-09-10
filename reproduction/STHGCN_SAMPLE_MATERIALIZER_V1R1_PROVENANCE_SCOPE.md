# STHGCN Sample Materializer V1R1 — Original-Split Provenance Repair

Date: 2026-09-10

## Material Passport

- `material_id`: `STHGCN_SAMPLE_MATERIALIZER_V1R1_PROVENANCE`
- `material_type`: prospective score-free data-provenance repair
- `status`: `IMPLEMENTATION_AND_ONE_SCORE_FREE_EXECUTION_AUTHORIZED`
- `parent_commit`: `cccf03c605bb3b1d7374e34a5eac9c247ea3b48b`
- `frozen_v1_result`: commit
  `9e67e05875540cc87a21e15c4ff3623400c6ab49`, path
  `reproduction/results/sthgcn_sample_materializer_r1_a53acb3/`
- `intended_output`: immutable per-record original-split sidecar plus receipts
- `not_an_output`: scenario labels, graph, model, loss, checkpoint, or metric
- `reason`: V1 retained endpoint eligibility as `SplitTag` but did not serialize
  the pre-eligibility `_split_original` field for ignored records

## 1. Problem and decision

Sample Materializer R1 correctly used `_split_original` internally to fit
training vocabularies and determine eligible endpoints. It then serialized only
`SplitTag`. First events and non-final validation/test events were overwritten
as `ignore`, so their original train/validation/test membership is not
recoverable from `sample.csv` alone.

The MSAHG-on-STHGCN causal reconstruction requires every post-filter training
event for static labels and graphs. Using `SplitTag == train` would omit ignored
training events. Treating every `ignore` row as training could include
validation/test events. Both shortcuts are rejected.

V1R1 therefore adds one sidecar without modifying V1:

```text
STHGCN_SAMPLE_MATERIALIZER_R1             = PASS / IMMUTABLE
V1R1_ORIGINAL_SPLIT_PROVENANCE_REPAIR     = PROSPECTIVE
SCENARIO_OR_GRAPH_MATERIALIZATION         = NOT_AUTHORIZED
MODEL_TRAINING_OR_METRICS                 = NOT_AUTHORIZED
```

## 2. Frozen inputs

- reproduction repository: `https://github.com/xiaolaoji66/MSAHG`;
- parent reconstruction contract commit:
  `cccf03c605bb3b1d7374e34a5eac9c247ea3b48b`;
- original V1 implementation source:
  `reproduction/sthgcn_sample_materializer_r1.py`;
- qualified V1 result commit:
  `9e67e05875540cc87a21e15c4ff3623400c6ab49`;
- STHGCN repository: `https://github.com/alipay/Spatio-Temporal-Hypergraph-Model`;
- STHGCN commit: `27b595846d29019799485985bff49f9ed02c4ade`;
- NYC/TKY archive and member identities already frozen by V1;
- exact V1 data-file hashes listed in the accompanying registry.

The execution must receive both the clean STHGCN source tree and the existing
qualified V1 full-output root. Neither input may be modified.

## 3. Repair semantics

V1R1 imports the frozen V1 module and replays its exact raw loading,
filtering/sessionization, encoding, ordering, and endpoint construction.

Before the internal `_split_original` field is discarded, V1R1 creates one row
for each serialized `sample.csv` row, in the same order:

| Column | Meaning |
|---|---|
| `check_ins_id` | V1 deterministic check-in ID |
| `source_ordinal` | V1 raw-source ordinal |
| `raw_trajectory_id` | V1 raw trajectory/session identity |
| `SplitTag` | serialized endpoint-eligibility state |
| `OriginalSplitTag` | pre-eligibility `train`, `validation`, or `test` |

`source_ordinal` must be unique within a dataset and provides the join key. The
pair `(check_ins_id, source_ordinal)` must also be unique. Row order must match
V1 `sample.csv` exactly.

For every row whose `SplitTag` is not `ignore`, `SplitTag` must equal
`OriginalSplitTag`. An ignored row may have any of the three legal original
splits. No original split is inferred from trajectory membership, timestamp,
or endpoint state.

## 4. Exact replay requirement

The newly replayed bytes for the following files must equal the frozen V1
hashes before any sidecar is accepted:

- `sample.csv`;
- `train_sample.csv`;
- `validate_sample.csv`;
- `test_sample.csv`;
- `label_encoding.json`.

The replay files are temporary qualification material and are not copied into
the V1R1 output. Their mismatch produces `V1_REPLAY_IDENTITY_MISMATCH` and
STOP. V1 receipts are not compared because their runtime/commit identity is
intentionally version-specific.

The existing V1 output root is independently checked against the same frozen
hashes. V1R1 never edits, replaces, or appends files inside it.

## 5. Output contract

One fresh, non-overwriting V1R1 output root contains:

```text
nyc/record_split_provenance.csv
nyc/provenance_receipt.json
nyc/SHA256SUMS
tky/record_split_provenance.csv
tky/provenance_receipt.json
tky/SHA256SUMS
provenance_summary.json
SHA256SUMS
```

Receipts contain authorities, V1 replay hashes, sidecar hashes, original-split
counts, cross-tabulation of `OriginalSplitTag x SplitTag`, gates, runtime, and
the score-free interpretation boundary.

A failed or partial root is evidence. It is preserved, returns nonzero, and is
never overwritten or automatically retried.

## 6. Qualification gates

All fourteen gates are mandatory:

1. `R0_AUTHORITY`: exact parent, V1 source, V1 result, STHGCN commit, and raw
   archive identities.
2. `R1_FRESH_OUTPUT`: output did not exist and no overwrite occurred.
3. `R2_V1_INPUT_IMMUTABLE`: existing V1 data files match frozen hashes before
   and after execution.
4. `R3_EXACT_V1_REPLAY`: all five replayed data/mapping files match V1 hashes.
5. `R4_ROW_BIJECTION`: sidecar and sample have equal row counts, equal order,
   and a unique one-to-one `source_ordinal` join.
6. `R5_LEGAL_ORIGINAL_SPLIT`: every original split is exactly train,
   validation, or test.
7. `R6_VISIBLE_SPLIT_IMPLICATION`: every non-ignore serialized split equals its
   original split.
8. `R7_IDENTITY_STABILITY`: check-in, ordinal, and raw-trajectory identities
   match the replayed sample.
9. `R8_COUNT_CONSERVATION`: NYC/TKY post-filter row counts remain 103,941 and
   405,000, with no missing original split.
10. `R9_TWO_RUN_DETERMINISM`: two fresh synthetic executions produce byte-
    identical sidecars and receipts after excluding no fields.
11. `R10_SOURCE_IMMUTABLE`: STHGCN and reproduction source authorities remain
    clean and unchanged during real execution.
12. `R11_NO_DOWNSTREAM_MATERIAL`: no scenario, center, graph, model, checkpoint,
    loss, ranking, or metric output exists.
13. `R12_SCORE_FREE`: no training, inference, target evaluation, metric, or
    checkpoint access occurs.
14. `R13_FAIL_CLOSED`: missing/extra/false gates, identity mismatches, or
    existing output produce nonzero with preserved evidence.

## 7. Authorization

Authorized:

- add-only V1R1 scope, registry, implementation, tests, runner, and independent
  auditor;
- local synthetic qualification;
- one score-free NYC/TKY execution against the exact frozen public archives and
  qualified V1 output;
- add-only archival of PASS or failure evidence.

Not authorized:

- any edit to V1 source, V1 result, MSAHG source, or STHGCN source;
- scenario labels, activity center, graph/hypergraph construction;
- model/data-loader/APS implementation;
- training, forward inference, loss, checkpoint, ranking, or metrics;
- changing split or preprocessing rules;
- an automatic retry after real-execution failure.

## 8. Mechanical decision

```text
if R0..R13 all true for NYC and TKY:
    V1R1 = PASS / ORIGINAL_SPLIT_PROVENANCE_QUALIFIED
else:
    V1R1 = PROTOCOL_FAILURE / STOP

V1R1 PASS != causal graph materializer authorization
V1R1 PASS != model or predictive evidence
```
