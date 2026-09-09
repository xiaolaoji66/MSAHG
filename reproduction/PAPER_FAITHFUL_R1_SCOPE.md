# MSAHG Paper-Faithful Reproduction R1 — Prospective Scope

Date: 2026-09-09

## 1. Authorities

- Paper: *Multifaceted Scenario-Aware Hypergraph Learning for Next POI Recommendation*, AAAI 2026, DOI `10.1609/aaai.v40i18.38552`.
- Official repository: `https://github.com/COCOMiss/MSAHG`.
- Frozen upstream commit: `3d74d70c852c56adcc09d907488410be5eda2744`.
- Independent reproduction repository: `https://github.com/xiaolaoji66/MSAHG`.
- Parent result authority: `511f7c0c64b7378c966d808d7b3cea0684a19f33`.
- Completed source-exact sample replay: `reproduction/results/official_sample_r0r2_c723862a/`.

This scope is independent of GUGEN and CIPRA. Those repositories, models, data,
and results are not inputs to R1. Existing GUGEN work remains preserved and is
not deleted, rewritten, or reinterpreted.

## 2. Current fact boundary

The official sample replay is complete, but it is not a reproduction of the
paper tables. It used the repository's small NYC sample, used the upstream
training/evaluation behavior, selected on `test.pkl`, and never activated APS.
Its metrics are diagnostic evidence about the released code only.

The full paper result is presently blocked because the released repository does
not contain the paper datasets or a preprocessing pipeline that can recreate
them. More seriously, the paper/README reports 1,743 NYC users, whereas the
cited public NYC/Tokyo Foursquare source reports only about 1,082/1,083 NYC
users. Filtering a source cannot increase the number of users. Until the authors
identify the actual raw source or correct the table, the NYC paper-data identity
is unresolved.

## 3. R1 objective

R1 has two deliberately separate tracks.

### R1A — paper-math reconstruction

Implement and target-free qualify the architecture and Adaptive Parameter
Splitting semantics that are explicitly determined by the paper, while
recording every reconstruction choice that the paper leaves unspecified.

R1A may establish:

- tensor-shape and graph-propagation coherence;
- correct construction and use of shared versus task-specific parameter banks;
- exact optimizer reachability of every active parameter copy;
- per-task gradient-cosine computation and the registered split predicate;
- deterministic task indexing and checkpoint round trips;
- absence of target/test access in target-free qualification.

R1A may not establish paper accuracy, dataset fidelity, or successful empirical
reproduction.

### R1B — data/protocol identity gate

R1B must resolve the raw dataset, preprocessing, grouping, and split identity
before any result may be called a paper-table reproduction.

R1B is fail-closed. Missing information is not filled by convention, by GUGEN
preprocessing, or by tuning on the paper's reported numbers.

## 4. Paper-determined model surface

The reconstruction preserves the following high-level computation graph:

1. shared user and POI embeddings;
2. collaborative, temporal-user, temporal-POI, geographical, and directed
   transition graph propagation;
3. residual layer aggregation in the graph encoders;
4. four user-view representations combined with view-specific sigmoid gates;
5. four normalized POI-view representations combined by addition;
6. full-catalog user/POI dot-product scores;
7. recommendation loss plus pairwise cross-view InfoNCE with registered weight
   `lambda_cl = 0.1`;
8. six scenario tasks: two user, two temporal, and two spatial groups;
9. APS based on normalized per-task gradients and pairwise cosine similarity.

The paper describes 128-dimensional embeddings, three propagation layers,
2.5-km geographical adjacency, Adam with learning rate `1e-3` and weight decay
`5e-4`, batch size 200, 100 epochs, patience 10, and Acc@1/5/10/20 plus MRR.
These values are registered as paper claims, not yet as executable result
authority.

## 5. Released-code defects that R1A must not copy silently

The frozen upstream code has the following material deviations or defects:

1. `run.py` and `train_nash.py` repeatedly call `next(iter(loader))`; this
   creates a fresh iterator and resamples the first batch rather than traversing
   a persistent epoch iterator.
2. `run.py` uses `test.pkl` for epoch-by-epoch model selection and again for
   final evaluation; no independent validation endpoint is released.
3. the optimizer omits the paper's `weight_decay=5e-4`.
4. `adaptive_par.py` uses a split threshold of `-0.0001`, while the paper
   describes `-0.5`.
5. `run.py` evaluates splitting only at `divide_epoch` and
   `divide_epoch + 10`, not every ten training batches after the starting
   epoch as described in the paper.
6. `add_task_specific_params` reuses one registered parameter name for multiple
   groups. Later registration overwrites earlier registration, so some copies
   can become absent from `model.parameters()` and therefore absent from an
   optimizer created from that iterator.
7. parameters are swapped into live submodules through `setattr` during
   forward passes. Registration and optimizer membership can therefore depend
   on the last task executed.
8. the optimizer recreated inside `train()` is local and is not returned to
   `run.py`, so the caller does not retain that optimizer after the function
   returns.
9. checkpoints at the two split epochs are force-written even if their
   validation criterion is worse, which can overwrite the previously selected
   checkpoint.
10. README commands refer to missing `main.py`, `requirements.txt`, and (on
    current `main`) `run_nash_divide.py`.

These are source facts. Whether every deviation changes a particular metric is
not yet measured and must not be asserted without an experiment.

## 6. Missing or non-unique preprocessing choices

The paper and repository do not jointly determine:

- the exact raw file/version used for NYC, TKY, and Gowalla;
- the filters that yield the reported users, POIs, check-ins, and trajectories;
- the complete accommodation-category set and the exact tourist/local rule;
- city-center coordinates and boundary behavior for the 10-km split;
- trajectory sessionization, minimum lengths, and target construction;
- chronological train/validation/test ratios and cold-start handling;
- whether graph structures are built from train-only observations;
- all random seeds and the aggregation protocol behind the reported table.

No paper-faithful full-data run is authorized while these are unresolved.

## 7. R1A target-free gates

The implementation must pass all gates below before any score-bearing request:

- `A0_AUTHORITY_IDENTITY`: exact upstream and scope identities;
- `A1_NO_GUGEN_DEPENDENCY`: no imports, data paths, or checkpoints from GUGEN;
- `A2_FORWARD_SHAPES`: all six task outputs have full-catalog shape;
- `A3_GRAPH_VIEW_COHERENCE`: each registered view uses its registered graph;
- `A4_TASK_INDEX_BIJECTION`: six scenario tasks map bijectively to stable IDs;
- `A5_SHARED_ANCHOR`: before splitting, all tasks use shared parameters;
- `A6_SPLIT_PREDICATE`: cosine threshold is exactly the registered paper value;
- `A7_UNSPLIT_IDENTITY`: no-conflict APS is byte-identical to the shared model;
- `A8_SPLIT_ISOLATION`: a split task changes only its assigned parameter bank;
- `A9_OPTIMIZER_COMPLETENESS`: every trainable active bank is present exactly
  once in the optimizer;
- `A10_GRADIENT_REACHABILITY`: every active bank receives finite gradients;
- `A11_CHECKPOINT_ROUNDTRIP`: bank topology, tensors, optimizer state, and task
  mapping survive save/load;
- `A12_DETERMINISM`: same seed and synthetic fixture reproduce hashes;
- `A13_CPU_SMOKE`: finite CPU forward/backward;
- `A14_CUDA_SMOKE_IF_AVAILABLE`: finite CUDA forward/backward;
- `A15_TARGET_BLIND`: no paper dataset, dev target, test target, or score metric is
  accessed or computed.

Any failed gate preserves its output and stops R1A. It does not authorize an
automatic repair run.

## 8. Execution boundary

Authorized now:

- documentation and source-vs-paper audit;
- add-only R1A implementation;
- synthetic, target-free CPU/CUDA qualification;
- preparation of a draft author data/protocol request.

Not authorized by this scope:

- claiming reproduction of any paper table;
- selecting a substitute public dataset by matching reported counts;
- using GUGEN data as if it were MSAHG paper data;
- dev/test access or score-bearing training;
- tuning ambiguities against reported metrics;
- overwriting the source-exact sample result.

After R1A passes, a separate versioned execution authority is required for any
score-bearing engineering reconstruction. R1B must clear before the words
"paper-faithful empirical reproduction" are allowed.

## 9. Mechanical state

```text
OFFICIAL_SOURCE_SAMPLE_REPLAY = COMPLETE
PAPER_TABLE_REPRODUCTION      = BLOCKED
R1A_PAPER_MATH_RECONSTRUCTION = AUTHORIZED_TARGET_FREE_ONLY
R1B_DATA_PROTOCOL_IDENTITY    = OPEN / BLOCKED_ON_MISSING_AUTHORITY
SCORE_BEARING_EXECUTION       = NOT_AUTHORIZED
GUGEN_AS_INPUT                = PROHIBITED
```
