# MSAHG-on-STHGCN Target Admissibility V1R3 — Protocol Failure

Date: `2026-09-10`

## Frozen outcome

```text
decision = PROTOCOL_FAILURE
reason   = OFFICIAL_FILTERED_TARGET_COUNTS_NOT_REPRODUCED
retry    = false
```

Authority lineage:

```text
727c82e8e1c822fa1acc8bab7f1511c2a2388b3e  V1R2 failure archive
80a0dfccc306d961d95e77334188a93e7a624ad3  V1R3 registration
bd9e7f6e518eda833d25f4fd1b6ff8639c934ad6  V1R3 implementation
7c2ea94c6aa59c797ddd993c5dfe5a237d1a245b  one-audit authority
```

Server evidence is preserved at:

```text
/mnt/data4t/wyh/MSAHG-target-admissibility-v1r3-7c2ea94
/mnt/data4t/wyh/msahg_runs/msahg_on_sthgcn_target_admissibility_v1r3-727c82e
/mnt/data4t/wyh/msahg_runs/msahg_on_sthgcn_target_admissibility_v1r3-727c82e.execution.log
```

## Primary protocol failure

The prospectively frozen current-endpoint rule did not reproduce the official
STHGCN README counts exactly:

| dataset | split | registered official | reconstructed | difference |
|---|---|---:|---:|---:|
| NYC | train | 72,206 | 72,206 | 0 |
| NYC | validation | 1,400 | 1,407 | +7 |
| NYC | test | 1,347 | 1,357 | +10 |
| TKY | train | 274,597 | 274,597 | 0 |
| TKY | validation | 6,868 | 6,875 | +7 |
| TKY | test | 7,038 | 7,049 | +11 |

No unregistered rule may delete the extra endpoints. Gate
`A5_EXACT_OFFICIAL_SPLIT_COUNTS` therefore failed and has protocol precedence.

## Additional registered blockers observed

These do not override the primary `PROTOCOL_FAILURE`, but they show that merely
replacing the official-count constants would not qualify the current six-task
reconstruction:

- `A7_PREFIX_POI_TRAIN_KNOWN` failed: 119 NYC and 34 TKY otherwise eligible
  targets have an immediate prefix POI outside the train-fitted vocabulary.
- `A10_EXACT_AXIS_PARTITIONS` failed because those targets cannot receive the
  frozen POI-axis label without deletion, substitution, or a new padding node.
- `A11_SUPPORT_FLOORS` failed for NYC `User/1`:
  - validation: 69 targets and 27 distinct users;
  - test: 76 targets and 24 distinct users;
  - registered floor: 100 targets and 30 distinct users.

The TKY support floors passed, but a per-dataset PASS cannot override the NYC
failure or the cross-dataset protocol failure.

## Integrity boundary

- All registered STHGCN source hashes remained exact before and after audit.
- All NYC/TKY sample, encoding, and provenance hashes remained exact.
- No graph or scenario file was materialized.
- No model, training, inference, checkpoint, recommendation metric, threshold
  search, or target evaluation was executed.
- Automatic retry was not performed and is not authorized.

The only valid next state is to preserve this failure. Any new data semantics,
prefix policy, support policy, or reconstruction family requires a separate
prospective scope and explicit approval.
