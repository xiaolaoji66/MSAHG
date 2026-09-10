# MSAHG-on-STHGCN causal materializer V1R2 real runtime scope

## 1. Status and repair boundary

- Date: `2026-09-10`
- Parent failure archive: `515c72a01eb76b859e48f82af24d504a6b7b3ad5`
- Supersedes only the exhausted V1 real-runtime authority registered at
  `efdb7490155ca5006592506a4347425880ecb1cd`.
- Production materializer remains immutable at
  `1f6fce9505eae929a8f131fc67556e513c4d1100`.
- Target-free materializer result remains immutable at
  `d7e2706d82656c718e70df621efbc90e29e74d6f`.

V1 failed before reading either real sample because one `registry_sha256` field
was incorrectly required to name both the immutable production implementation
registry and the outer real-runtime registry. V1R2 repairs only that identity
binding. It does not change data, scenario definitions, graph construction,
support floors, materialization mathematics, or the independent reconstruction.

## 2. Dual registry binding

The V1R2 runtime authority must expose two non-interchangeable fields:

1. `registry_sha256` binds the immutable production materializer registry:
   `f9ff7c5ffe4affc4ccf4ff0d44dd9089274b4e416437f34219fa6b5c33ddc1ba`.
2. `real_runtime_registry_sha256` binds the V1R2 outer execution registry.

The unchanged production materializer consumes the first field. The V1R2
independent auditor verifies both fields and the complete authority-file hash.
Neither binding may be inferred, substituted, or selected at runtime.

## 3. Frozen real inputs and semantics

The NYC and TKY sample CSVs, train-fitted encodings, provenance sidecars,
server paths, row counts, and SHA256 identities remain exactly those registered
in V1. The six marginal tasks remain:

- `User/0`, `User/1`;
- `Time/0`, `Time/1`;
- `POI/0`, `POI/1`.

Labels are reconstructed from the immediate observed prefix. Graphs and
activity-center statistics are fitted from `OriginalSplitTag == train` only.
Joint triples remain metadata only. No label, threshold, support floor, graph
radius, post-hoc group merge, or row filtering may change.

## 4. Authorized execution

After target-free tests pass, exactly one fresh production materializer
invocation is authorized for NYC and exactly one for TKY. After both succeed,
exactly one independent audit is authorized over the two new output roots.

The materializer's registered two-build byte-determinism check is internal to
one invocation and is not a retry. Any command failure exhausts this authority:
preserve all output and logs, stop, and do not retry. A further repair or rerun
requires another versioned scope and explicit user approval.

## 5. Independent audit and support decision

The V1R2 auditor reuses the immutable V1 independent reconstruction algorithms
and changes only authority verification and receipt versioning. It must verify
all nineteen frozen R0-R18 gates, including exact source/input/output identity,
immediate-prefix scenarios, six-task routing, independent support counts,
independent reconstruction of all graph families, deterministic sparse format,
source immutability, score-free behavior, and support-decision consistency.

Every one of the six marginal tasks must satisfy:

- train: at least 200 targets and 30 distinct users;
- validation: at least 100 targets and 30 distinct users;
- test: at least 100 targets and 30 distinct users.

The mechanical decisions remain:

```text
protocol failure  -> STOP_PRESERVE_NO_RETRY
support failure   -> DATA_NOT_ADMISSIBLE_FOR_SIX_TASK_SCORE
all gates pass    -> MATERIALIZATION_QUALIFIED_ONLY
```

`MATERIALIZATION_QUALIFIED_ONLY` is not a model or predictive-performance
result. This scope does not authorize model/data-loader/APS implementation,
training, inference, loss, optimizer, checkpoint access, recommendation metric
computation, target evaluation, threshold search, additional seeds, or claims.

## 6. Archival boundary

Complete materialized roots remain immutable on the server. GitHub may archive
only small receipts, manifests, support ledgers, checksum manifests, and a
README with exact server paths and hashes. Large scenario JSONL files and sparse
graph shards remain server-only unless separately authorized.
