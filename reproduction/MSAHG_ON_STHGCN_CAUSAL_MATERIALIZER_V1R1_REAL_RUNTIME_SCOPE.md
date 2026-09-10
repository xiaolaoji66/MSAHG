# MSAHG-on-STHGCN Causal Materializer V1R1 — Real Runtime Scope

Date: 2026-09-10

## Material Passport

- `material_id`: `MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_REAL_RUNTIME`
- `material_type`: prospective real-data materialization and independent-audit authority
- `parent_result`: `d7e2706d82656c718e70df621efbc90e29e74d6f`
- `materializer_implementation`: `1f6fce9505eae929a8f131fc67556e513c4d1100`
- `target_free_result`: `d7e2706d82656c718e70df621efbc90e29e74d6f`
- `datasets`: frozen STHGCN-derived NYC and TKY only
- `status`: `REAL_MATERIALIZATION_AND_SUPPORT_AUDIT_AUTHORIZED`
- `not_an_output`: model, training run, checkpoint, recommendation metric, or
  predictive conclusion

## 1. Purpose

This scope authorizes the previously qualified V1R1 materializer to read the
exact frozen NYC and TKY public-data artifacts and their qualified
`OriginalSplitTag` sidecars. It may create the frozen Marginal-Axis V1 scenario
labels, activity center, graph shards, graph manifest, and support ledger once
per dataset in fresh server directories.

The resulting artifacts must be independently audited before they can become
input authority for any later model contract. This stage only decides whether
the materialization is structurally valid and whether every registered marginal
group meets the pre-existing support floors.

## 2. Exact input authority

Only these preserved server roots may be read:

- V1 records and encodings:
  `/mnt/data4t/wyh/msahg_runs/sthgcn_sample_materializer_r1_replay-a53acb3-v1r1-input-pandas223`;
- V1R2 original-split sidecars:
  `/mnt/data4t/wyh/msahg_runs/sthgcn_sample_materializer_v1r2_provenance-d73f118`;
- STHGCN source authority:
  `/mnt/data4t/wyh/sthgcn-source-27b59584-provenance-v1r1`.

For each dataset, `sample.csv`, `label_encoding.json`, and
`record_split_provenance.csv` must match the exact hashes already frozen in the
V1R1 implementation registry. The implementation commit, target-free receipt,
causal contract, and upstream source commits must also match exactly.

No GUGEN artifact, released MSAHG group label, development metric, test metric,
checkpoint, or additional dataset may be read.

## 3. Authorized implementation surface

One direct child of this registration may add exactly:

- `reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_real.py`;
- `scripts/run_msahg_on_sthgcn_causal_materializer_v1r1_real.sh`;
- `tests/test_msahg_on_sthgcn_causal_materializer_v1r1_real.py`;
- `tests/test_msahg_on_sthgcn_causal_materializer_v1r1_real_governance.py`.

The auditor must be independent of the production materializer: it may not
import the production module or use its graph/scenario builder functions. It
must reconstruct labels and graph coordinates directly from the frozen inputs
using NumPy, pandas, SciPy, and the Python standard library.

## 4. Authorized execution

Exactly one fresh materializer invocation is authorized for NYC and exactly one
for TKY. After both succeed, exactly one independent audit is authorized over
the two preserved output roots. The runner must record console logs and must not
retry any failed invocation.

The materializer may perform its registered two-build byte-determinism check
inside a single invocation. This is one execution, not a retry.

If any command fails, all existing output and logs must be preserved and the
stage stops. Repair or rerun requires a new versioned scope and explicit user
approval.

## 5. Independent audit requirements

For each dataset the auditor must independently verify:

1. source, input, implementation, and runtime-authority identity;
2. exact output inventory and every `SHA256SUMS` entry;
3. materialization receipt identity and score-free boundary;
4. one scenario row per eligible target in stable source order;
5. scenario labels reconstructed from the immediate prefix, never the target;
6. strict Hotel-share user label, workday/weekend time label, and train-only
   activity-center spatial label;
7. exactly three marginal tasks per target and metadata-only joint triples;
8. support counts independently reproduced from scenario rows;
9. collaborative, temporal-POI, temporal-user, geographical, and directed
   transition raw coordinates independently reconstructed from training rows;
10. raw binary dtypes, normalized row-stochastic operators, zero-row behavior,
    deterministic NPZ metadata, shapes, nonzeros, and hashes;
11. input and source worktrees unchanged after the audit;
12. no model, loss, training, inference, checkpoint, ranking, or metric action.

## 6. Frozen support gate

Every one of the six marginal groups must have:

- train: at least 200 eligible targets and 30 distinct users;
- validation: at least 100 eligible targets and 30 distinct users;
- test: at least 100 eligible targets and 30 distinct users.

The eight joint cells are reported as metadata and do not block the six-task
route. No threshold search, post-hoc group merge, row deletion, or label change
is allowed after observing support.

## 7. Mechanical decision

```text
if any identity, reconstruction, graph, determinism, or score-free audit fails:
    decision = PROTOCOL_FAILURE
    action   = STOP; preserve outputs; no retry

elif any registered marginal support floor fails:
    decision = DATA_NOT_ADMISSIBLE_FOR_SIX_TASK_SCORE
    action   = STOP before model implementation or training

else:
    decision = MATERIALIZATION_QUALIFIED_ONLY
    action   = request a separate prospective model contract
```

`MATERIALIZATION_QUALIFIED_ONLY` is not evidence that MSAHG improves next-POI
recommendation and does not authorize model implementation, training, inference,
checkpoint access, recommendation metrics, target evaluation, or paper claims.

## 8. Archival boundary

The complete immutable materialized roots remain on the server. GitHub may
archive only the independent audit receipt and small materialization receipts,
manifests, support ledgers, checksum manifests, and a README containing exact
server paths and hashes. Large scenario JSONL and sparse graph shards must not
be duplicated into Git without a separate storage decision.
