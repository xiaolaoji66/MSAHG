# STHGCN Sample Materializer V1R2 — Replay-Directory Repair

Date: 2026-09-10

## Material Passport

- `material_id`: `STHGCN_SAMPLE_MATERIALIZER_V1R2_PROVENANCE`
- `material_type`: prospective score-free implementation repair
- `status`: `IMPLEMENTATION_AND_ONE_SCORE_FREE_EXECUTION_AUTHORIZED`
- `parent_commit`: `d7d8959eab2256d2e8153485165d11028c258025`
- `superseded_runtime`: V1R1 implementation commit
  `38db98809e6f8bb3723e61163d1b428060aba8be`
- `preserved_failure`: V1R1 failure archive commit
  `d7d8959eab2256d2e8153485165d11028c258025`
- `intended_output`: the unchanged V1R1 per-record original-split sidecar
- `not_an_output`: scenario labels, graph, model, loss, checkpoint, ranking, or metric

## 1. Confirmed defect

V1R1 passed its 12-gate synthetic qualification but its single authorized real
execution stopped before provenance materialization:

```text
PROTOCOL_FAILURE = [Errno 17] File exists: <temporary replay directory>
```

The cause is source-identifiable. `_prepare_dataset` used
`tempfile.mkdtemp`, which returned an already-created directory, and passed
that path to `_write_replay`. `_write_replay` correctly enforces a fresh output
with `mkdir(..., exist_ok=False)`, so the two directory-ownership assumptions
conflicted.

The failure does not concern NYC/TKY data. Immediately before V1R1 execution,
the frozen V1 materializer reproduced all five registered files byte-exactly
for both datasets: NYC 103,941 rows and TKY 405,000 rows.

## 2. Exact repair

V1R2 is add-only and leaves V1 and V1R1 immutable. It may make exactly this
semantic change:

```text
temporary parent (created by tempfile)
    -> replay child path (must not exist)
        -> _write_replay creates the child with exist_ok=False
```

The fresh-output invariant therefore remains strict. Changing
`_write_replay` to `exist_ok=True`, weakening hash checks, or reusing a partial
directory is prohibited.

All split, filter, sessionization, vocabulary, endpoint, cold-start, ordering,
CSV, JSON, and sidecar mathematics remain byte-equivalent to V1R1. V1R2 may
update only version/authority labels needed to identify the repaired runtime.

## 3. Mandatory regression witness

Target-free qualification must execute the previously untested directory
handoff, not merely a mock predicate. It must prove:

1. the temporary parent exists;
2. the replay child is absent before `_write_replay`;
3. `_write_replay` creates the child exactly once;
4. a pre-existing replay child is still rejected;
5. the V1R1 failure pattern is reproduced by the frozen V1R1 source;
6. no real data, graph, model, checkpoint, loss, ranking, or metric is accessed.

## 4. Frozen inputs

- reproduction repository: `https://github.com/xiaolaoji66/MSAHG`;
- V1R1 registration commit:
  `be5efdc1ed56b6628dde82224eaf6df2abfec1cf`;
- V1R1 implementation commit:
  `38db98809e6f8bb3723e61163d1b428060aba8be`;
- V1R1 failure archive commit:
  `d7d8959eab2256d2e8153485165d11028c258025`;
- frozen V1 source SHA256:
  `288daa4ab0de251cbbb0d4d8a1735af1193d42aa0c258757443fd2a154e65f3e`;
- frozen V1R1 source SHA256:
  `606de269b48b6d5394a292956b033b0c43daa86d703360969443ce80e1ddaf5e`;
- STHGCN commit:
  `27b595846d29019799485985bff49f9ed02c4ade`;
- qualified V1 NYC/TKY file hashes remain those in the V1R1 registry.

## 5. Output and execution

The successful output allowlist is unchanged:

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

V1R2 must use a fresh root. A failed/partial root is immutable evidence. No
automatic retry is allowed. The real run is a score-free reconstruction of
NYC and TKY provenance only.

## 6. Gates

V1R2 retains V1R1 gates R0-R13 and adds:

- `R14_REPLAY_CHILD_DIRECTORY_HANDOFF`;
- `R15_V1R1_FAILURE_REPRODUCED`;
- `R16_REPAIR_DELTA_EXACT`.

All 17 real gates and all target-free gates must be true. A synthetic PASS does
not authorize or predict a real PASS.

## 7. Authorization

Authorized:

- this scope and registry;
- an add-only V1R2 implementation, tests, target-free auditor, real auditor,
  and runners;
- local and server target-free qualification;
- one score-free NYC/TKY provenance execution against the frozen sources and
  exact V1 output;
- add-only archival of PASS or failure evidence.

Not authorized:

- modifying V1, V1R1, STHGCN, or their archived results;
- scenario labels, activity centers, graph/hypergraph materialization;
- model/data-loader/APS implementation;
- training, inference, loss, checkpoint access, ranking, or metrics;
- any change to preprocessing or provenance semantics;
- automatic retry after the single real execution.

## 8. Mechanical decision

```text
if all V1R2 target-free gates pass
and R0..R16 pass for NYC and TKY:
    V1R2 = PASS / ORIGINAL_SPLIT_PROVENANCE_QUALIFIED
else:
    V1R2 = PROTOCOL_FAILURE / STOP

V1R2 PASS != graph materializer authorization
V1R2 PASS != model or predictive evidence
```
