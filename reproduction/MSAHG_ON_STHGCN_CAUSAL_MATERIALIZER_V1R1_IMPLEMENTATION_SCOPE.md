# MSAHG on STHGCN Causal Materializer V1R1 — Target-Free Implementation Scope

Date: 2026-09-10

## Material Passport

- `material_id`: `MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1`
- `material_type`: prospective add-only target-free implementation authority
- `status`: `IMPLEMENTATION_AND_TARGET_FREE_QUALIFICATION_AUTHORIZED`
- `parent_result`: `9bb6248b7cd8730b9c05676926f213afe3e476fc`
- `mathematical_authority`: MSAHG-on-STHGCN Causal Reconstruction V1
- `provenance_authority`: STHGCN Sample Materializer V1R3 PASS
- `intended_output`: materializer code, synthetic qualification, and one server
  target-free receipt
- `not_an_output`: real NYC/TKY scenarios or graphs, model, checkpoint, loss,
  recommendation metric, or predictive conclusion

## 1. Purpose

This scope authorizes an add-only implementation of the already frozen
`MARGINAL_AXIS_V1` scenario and graph mathematics. It does not modify the V1
contract. It closes the input-authority gap by binding the unchanged V1R2
original-split sidecars qualified by the V1R3 audit.

The implementation must be executable on synthetic frames without accessing a
real dataset. A separate versioned runtime authority remains mandatory before
reading the real V1 CSVs or V1R2 sidecars for scenario/graph materialization.

## 2. Frozen input chain

The future real materializer must consume, by exact hash:

1. V1 `sample.csv` and `label_encoding.json` for NYC and TKY;
2. the unchanged V1R2 `record_split_provenance.csv` sidecar for each dataset;
3. the V1R3 PASS receipt proving row identity and original-split provenance;
4. no other public, validation, test, paper-sample, or GUGEN material.

`OriginalSplitTag == train` is the sole static-fit selector. `SplitTag` controls
only eligible target reporting. Rows with `SplitTag == ignore` remain eligible
for static fitting when their original split is train.

If an eligible example's last observed prefix POI has no train-fitted coordinate
or its user has no train-fitted user label, materialization must fail. No
fallback, nearest label, evaluation-derived coordinate, or row deletion is
permitted.

## 3. Exact implementation surface

The implementation may add exactly:

- `reproduction/msahg_on_sthgcn_causal_materializer_v1r1.py`;
- `reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_target_free.py`;
- `scripts/run_msahg_on_sthgcn_causal_materializer_v1r1_target_free.sh`;
- `tests/test_msahg_on_sthgcn_causal_materializer_v1r1.py`;
- `tests/test_msahg_on_sthgcn_causal_materializer_v1r1_governance.py`.

The production module may expose a future real-data CLI, but it must refuse to
materialize unless supplied a separately registered runtime authority whose
`real_materialization_authorized` field is exactly `true`. This V1R1 registry
sets it to `false`.

## 4. Sparse shard format

Each graph object is serialized as a deterministic NumPy-compatible `.npz`
archive with fixed ZIP metadata and exactly three entries:

- `indices.npy`: shape `2 x nnz`, `int64`, lexicographically sorted;
- `values.npy`: shape `nnz`, raw matrices `uint8`, normalized operators
  `float64`;
- `shape.npy`: shape `2`, `int64`.

Duplicate coordinates are coalesced before serialization. Raw matrices are
binary. Normalized operators use the V1 row-normalization rule and zero rows
remain zero. Two fresh synthetic runs must be byte-identical.

## 5. Synthetic qualification requirements

All C0-C17 gates from the V1 contract remain mandatory. In particular, the
synthetic fixture must prove:

- train-only fitting is invariant to validation/test perturbation;
- target labels use the immediate previous event in the same trajectory;
- Hotel share boundary `0.05` is local and strict values above it are tourist;
- workday/weekend and half-hour slots are exact;
- spatial center, 10-km labels, 2.5-km graph edges, self loops, and region
  restriction are exact;
- collaborative and temporal global/split unions are exact;
- transition edges are distinct consecutive directed pairs only and the
  source-to-target orientation passes an asymmetric witness;
- each eligible target maps to exactly one group per axis and therefore three
  marginal tasks; joint triples remain metadata only;
- missing provenance, duplicate identity, unknown prefix POI, malformed
  coordinates, false/extra/missing gates, and existing output fail closed;
- source inputs are unchanged and no downstream activity occurs.

Synthetic support counts are structural witnesses only; the real support floors
cannot be adjudicated before a separately authorized real materialization.

## 6. Authorization

Authorized:

- this scope and registry;
- the exact five-file add-only implementation;
- local unit and governance tests;
- synthetic CPU target-free qualification;
- one server target-free qualification and add-only archival of its receipt.

Not authorized:

- modifying any prior contract, source, receipt, sidecar, or result;
- reading the real NYC/TKY CSVs or sidecars for this new materialization;
- real scenario-label, activity-center, graph, or support materialization;
- changing thresholds, label rules, graph semantics, or task routing;
- model/data-loader/APS implementation;
- training, inference, loss, optimizer, checkpoint, metrics, or target access;
- automatic retry after a failed server qualification.

## 7. Mechanical decision

```text
if all C0..C17 target-free gates are exactly true:
    V1R1 = TARGET_FREE_PASS
    next = request separate real-materialization authority
else:
    V1R1 = PROTOCOL_FAILURE / STOP
```

`TARGET_FREE_PASS` is implementation coherence only. It is not real-data
admissibility, model correctness, or evidence of recommendation improvement.
