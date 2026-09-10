# MSAHG-on-STHGCN Target Admissibility V1R3 — Prospective Scope

Date: `2026-09-10`

## 1. Status and purpose

```text
V1R2_REAL_MATERIALIZATION = PROTOCOL_FAILURE / IMMUTABLE
V1R3_TARGET_ADMISSIBILITY = PROSPECTIVELY APPROVED; VERSIONED EXECUTION AUTHORITY PENDING
V1R3_MATERIALIZATION      = CONDITIONALLY DRAFTABLE, NOT YET AUTHORIZED
MODEL / TRAINING / METRIC = NOT AUTHORIZED
```

This scope supersedes only the V1/V1R2 assumption that every row in the full
STHGCN `sample.csv` whose materialized `SplitTag` is train, validation, or test
is an eligible prediction target. It does not relabel a failed execution and it
does not authorize a model, training, inference, recommendation metrics, or any
post-hoc deletion.

The V1R2 failure is preserved at commit
`727c82e8e1c822fa1acc8bab7f1511c2a2388b3e`. Its first NYC invocation failed
before creating a dataset output because the complete `sample.csv` contains
validation/test rows whose train-fitted user or POI encoding is the padding ID.

## 2. Official STHGCN source semantics

The source authority is `alipay/Spatio-Temporal-Hypergraph-Model` commit
`27b595846d29019799485985bff49f9ed02c4ade` at the registered clean server
worktree. The following source identities and meanings are frozen before the
real audit:

- `preprocess/preprocess_fn.py`, SHA256
  `aaf6134b6912a69cdc77d34f6e62ac134329acee2e08175c626844944ebf0966`:
  `remove_unseen_user_poi` constructs train user/POI sets and removes
  validation/test endpoints whose current user or current POI did not appear
  in training.
- `preprocess/preprocess_main.py`, SHA256
  `d8ade2ff7f5e17db7322d38db6a0b2d003f7bd27133ea6a773d927a8f904bfba`:
  NYC encoders are fitted on training, unseen IDs map to padding, the official
  split filter is applied, and both the complete `sample.csv` and filtered
  split sample files are written.
- `dataset/lbsn_dataset.py`, SHA256
  `6c1ecd998b50fc180eb56af3d05de7a96b67be9ae50a291bebe9192ea5074b9e`:
  the complete sample is used for graph/history state while filtered split
  sample files supply prediction nodes, labels, and indices.
- `README.md`, SHA256
  `90d667566b38e9404ac93e0ef35523a17f597b5a220fb30e82acc9d81b10ee4e`:
  it explicitly distinguishes the complete sample from filtered samples and
  reports the official post-filter split counts frozen below.

The V1R3 audit therefore uses two distinct row roles:

1. **history/graph row**: every row of the frozen complete `sample.csv`, with
   graph fitting still restricted by the existing train-only contract;
2. **eligible target row**: a row whose materialized `SplitTag` is train,
   validation, or test and whose current encoded `UserId` and `PoiId` both
   belong to their train-fitted vocabularies.

For the registered encodings, train-vocabulary membership is exactly:

```text
offset <= encoded_id < offset + len(classes)
```

Padding IDs are not members. No category, coordinate, timestamp, trajectory,
or provenance field participates in target filtering.

## 3. Frozen expected official target counts

The following counts are registered prospectively from the official STHGCN
README, before reading audit results:

| dataset | train | validation | test |
|---|---:|---:|---:|
| NYC | 72,206 | 1,400 | 1,347 |
| TKY | 274,597 | 6,868 | 7,038 |

The target-admissibility rule must reproduce all six counts exactly. A count
mismatch is a protocol failure, not a threshold to tune.

## 4. Immediate-prefix admissibility

The existing six-task reconstruction assigns the time and POI scenario from
the immediate observed prefix event. Consequently every eligible target must:

1. have exactly one preceding row in the same materialized pseudo-session with
   trajectory rank exactly one smaller; and
2. have an immediate-prefix `PoiId` inside the train-fitted POI vocabulary.

The official source filter constrains the current endpoint, not necessarily its
immediate prefix. V1R3 therefore measures this condition independently. It is
not permitted to delete a target, substitute an earlier prefix, map padding to
a new graph node, merge scenario groups, or infer a missing POI label.

Any eligible target violating either condition makes the current six-task
causal reconstruction inadmissible and stops this line.

## 5. Frozen scenario and support audit

Only if all eligible targets have admissible immediate prefixes, the auditor
reconstructs the unchanged V1 scenario labels:

- `User/0` local and `User/1` tourist from train-only exact-`Hotel` share with
  threshold `0.05`;
- `Time/0` workday and `Time/1` weekend from the immediate prefix timestamp;
- `POI/0` central and `POI/1` peripheral from train-only median POI coordinates,
  the train-only activity center, and the frozen `10.0 km` radius.

No graph shard is materialized in this audit. For each dataset, split, and all
six marginal tasks, support must still meet the frozen floors:

```text
train      >= 200 targets and >= 30 distinct users
validation >= 100 targets and >= 30 distinct users
test       >= 100 targets and >= 30 distinct users
```

Threshold search, group merge, subgroup deletion, and recommendation metric
computation are forbidden.

## 6. Fail-closed gates and decisions

The audit gates are:

```text
A0  authority and clean implementation lineage
A1  immutable STHGCN source identities
A2  immutable sample, encoding, and provenance identities
A3  complete sample/provenance row identity
A4  official current-endpoint membership rule
A5  exact official split counts for NYC and TKY
A6  unique immediate-prefix reconstruction
A7  all eligible prefix POIs train-known
A8  unchanged train-only user labels
A9  unchanged train-only activity center and POI labels
A10 six marginal tasks form exact per-axis partitions
A11 all frozen support floors pass
A12 source and inputs remain byte-identical
A13 no model, target score, or recommendation metric is executed
```

Mechanical decisions:

```text
any identity/protocol gate fails
  -> PROTOCOL_FAILURE / PRESERVE / NO RETRY

official target counts match, but prefix or support gate fails
  -> DATA_NOT_ADMISSIBLE_FOR_CURRENT_SIX_TASK_RECONSTRUCTION / STOP

all gates pass
  -> TARGET_ADMISSIBILITY_QUALIFIED_FOR_SEPARATE_V1R3_MATERIALIZER_REPAIR
```

The PASS decision authorizes drafting and requesting a separate versioned
materializer repair under the already approved conditional progression. It is
not itself a materialization result and grants no model or score-bearing
authority.

## 7. Execution and preservation boundary

Exactly one audit invocation over NYC and TKY is authorized in one fresh server
output root. The invocation may read only the frozen complete samples,
train-fitted encoding JSON files, provenance sidecars, and the clean official
STHGCN source files named above. It writes only a compact receipt and checksum
manifest.

Any command failure exhausts this audit authority. The server output and log
must be preserved. Automatic retry is forbidden. Existing V1 and V1R2 failure
directories, target-free results, source worktrees, and frozen input roots must
not be modified.
