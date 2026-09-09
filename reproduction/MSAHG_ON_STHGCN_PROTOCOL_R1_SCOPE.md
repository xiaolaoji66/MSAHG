# MSAHG on STHGCN Protocol R1 — Prospective Scope

Date: 2026-09-09

## 1. Objective

R1 defines a public, versioned, same-protocol benchmark for evaluating the
reconstructed MSAHG computation graph on the data protocol released with
STHGCN. It does not replace the unresolved MSAHG paper-data authority and it
does not authorize a claim that the MSAHG paper tables have been reproduced.

The admissible future claim is narrowly:

> MSAHG was evaluated on a qualified reconstruction of the public STHGCN
> sample protocol, using the same frozen samples and endpoints as every
> comparator in that experiment.

## 2. Frozen authorities

- MSAHG paper: *Multifaceted Scenario-Aware Hypergraph Learning for Next POI
  Recommendation*, AAAI 2026, DOI `10.1609/aaai.v40i18.38552`.
- MSAHG source repository: `https://github.com/COCOMiss/MSAHG`.
- MSAHG frozen upstream commit:
  `3d74d70c852c56adcc09d907488410be5eda2744`.
- Reproduction repository: `https://github.com/xiaolaoji66/MSAHG`.
- R1 parent evidence commit:
  `6afeb73ebcbfc384ac3fff1912eee83aae95cf8a`.
- STHGCN source repository:
  `https://github.com/alipay/Spatio-Temporal-Hypergraph-Model`.
- STHGCN frozen upstream commit:
  `27b595846d29019799485985bff49f9ed02c4ade`.
- STHGCN license: Apache-2.0, frozen by SHA256 in
  `reproduction/STHGCN_PROTOCOL_R1_SHA256SUMS`.

No GUGEN source, dataset, checkpoint, result, or preprocessing artifact is an
input to this scope.

## 3. Why this is a new protocol, not a paper-data repair

The released MSAHG repository reports:

| Dataset | Users | POIs | Check-ins | Trajectories |
|---|---:|---:|---:|---:|
| NYC | 1,743 | 7,289 | 57,327 | 6,102 |
| TKY | 1,383 | 17,023 | 507,260 | 41,374 |

The STHGCN release reports after preprocessing:

| Dataset | Users | POIs | Check-ins | Trajectories |
|---|---:|---:|---:|---:|
| NYC | 1,048 | 4,981 | 103,941 | 14,130 |
| TKY | 2,282 | 7,833 | 405,000 | 65,499 |

These identities are not interchangeable. Results from this scope must never
be copied into, compared numerically with, or described as a reproduction of
the MSAHG paper table without an explicit same-protocol qualifier.

## 4. Sample-level protocol selected from STHGCN

R1 adopts only the sample-level data surface:

- raw or pre-split records;
- user, POI, category, coordinate, and timestamp fields;
- deterministic split identity;
- trajectory/session identity;
- train-only label vocabulary;
- cold-start handling;
- next-POI target construction;
- last-event validation/test endpoint.

R1 does not adopt the serialized STHGCN PyG hypergraphs as MSAHG inputs.
MSAHG graph and sub-hypergraph construction must be separately registered and
must be train-only or demonstrably prefix-causal.

### 4.1 NYC

The frozen STHGCN archive contains the GETNext-derived files
`NYC_train.csv`, `NYC_val.csv`, and `NYC_test.csv`. Their split membership is
already determined before the STHGCN code concatenates them. R1 preserves
those file-level splits exactly.

The raw archive contains 83,228 training records, 10,339 validation records,
and 10,374 test records, for 103,941 records in total. These are source-file
counts, not eligible evaluation samples after first-event and cold-start
filtering.

### 4.2 TKY

The STHGCN release starts from `dataset_TSMC2014_TKY.txt`, filters POIs with
frequency `<= 9`, then users with frequency `<= 9`, sorts globally by local
timestamp, and intends an 80/10/10 chronological split. A gap strictly greater
than 1,440 minutes starts a new trajectory. Label encoders are fitted on the
training partition; unseen validation/test users or POIs are removed; the
first event of every trajectory is not a prediction sample; and validation and
test retain only the final event of each trajectory for metrics.

The source implementation performs the validation/test assignment through
Pandas chained indexing. That statement is not accepted as a portable split
authority. R1 must first replay it in the frozen legacy dependency environment
and compare it with an explicit-index reference implementation. If the source
assignment does not produce the intended split, the reference implementation
must be versioned as a protocol reconstruction; the source must remain
unchanged and its behavior must remain recorded.

## 5. Hypergraph leakage boundary

STHGCN calls `generate_hypergraph_from_file(sample.csv, ...)`, where
`sample.csv` contains all split records. Its sampler later removes target
trajectory check-ins beyond each sample time and dynamically recomputes some
target-trajectory quantities. Consequently, the mere use of the full file is
not by itself proof that every sampled message contains future information.

It is nevertheless not equivalent to a train-only graph authority: graph
topology, full-trajectory statistics, and global distance ranges are first
materialized from the combined file. R1 therefore does not import these PyG
objects. Any later MSAHG graph materializer requires a separate causal-input
audit.

## 6. Scenario-label boundary

The STHGCN fields are sufficient to calculate candidate temporal and spatial
rules, but they do not identify the exact six MSAHG scenario labels. In
particular, the released materials do not jointly determine the complete
tourist category set, all user-boundary behavior, city-center coordinates, or
spatial boundary ties.

R1 therefore keeps scenario-label construction closed. A later version may
define a transparent reconstructed scenario protocol, but it must be named as
such and cannot be called the authors' original grouping.

## 7. R1 qualification gates

- `Q0_MSAHG_AUTHORITY`: exact MSAHG parent and upstream identities.
- `Q1_STHGCN_AUTHORITY`: exact STHGCN repository commit and clean source.
- `Q2_LICENSE_AND_SOURCE_HASHES`: frozen license, code, config, and archive
  hashes.
- `Q3_ARCHIVE_MEMBERS`: exact NYC and TKY archive member names and bytes.
- `Q4_NYC_RAW_SPLIT_COUNTS`: exact file-level NYC counts and chronological
  non-overlap.
- `Q5_TKY_RAW_IDENTITY`: exact raw TKY rows, users, POIs, and member hash.
- `Q6_SOURCE_SEMANTICS`: source statements for filtering, sessionization,
  train-only encoding, cold-start removal, first-event removal, and last-event
  endpoints are present and frozen.
- `Q7_SPLIT_ASSIGNMENT_AUDIT`: source chained assignment is explicitly
  detected and cannot be silently treated as portable.
- `Q8_FULL_GRAPH_INPUT_AUDIT`: combined-file hypergraph construction is
  detected and remains excluded from MSAHG inputs.
- `Q9_DATASET_IDENTITY_SEPARATION`: STHGCN and MSAHG reported counts remain
  explicitly distinct.
- `Q10_NO_GUGEN_DEPENDENCY`: no GUGEN source, data, model, or result input.
- `Q11_SCORE_FREE`: qualification may read public records for identity and
  split checks, but computes no recommendation score, loss, accuracy, MRR, or
  checkpoint selection.
- `Q12_FAIL_CLOSED`: missing or mismatched authority produces a non-zero exit.

## 8. Execution boundary

Authorized by this prospective scope:

- add-only protocol documentation and registry;
- a read-only source/archive qualification auditor;
- local and server replay of that score-free data-identity auditor;
- tests for the auditor and its fail-closed behavior.

Not authorized:

- model training or recommendation metric computation;
- validation/test target evaluation;
- MSAHG paper-table claims;
- a scenario-label materializer;
- MSAHG graph materialization;
- STHGCN or MSAHG hyperparameter tuning;
- data-dependent threshold selection;
- editing either frozen upstream source tree.

## 9. Mechanical state

```text
MSAHG_PAPER_TABLE_REPRODUCTION = BLOCKED
STHGCN_SAMPLE_PROTOCOL         = PROSPECTIVE / SCORE_FREE_QUALIFICATION_AUTHORIZED
STHGCN_PYG_GRAPH_REUSE         = PROHIBITED
SCENARIO_LABEL_PROTOCOL        = NOT_REGISTERED
MSAHG_SCORE_EXECUTION          = NOT_AUTHORIZED
GUGEN_AS_INPUT                 = PROHIBITED
```
