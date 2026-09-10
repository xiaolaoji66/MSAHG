# MSAHG on STHGCN Causal Reconstruction V1 — Prospective Contract

Date: 2026-09-10

## Material Passport

- `material_id`: `MSAHG_ON_STHGCN_CAUSAL_RECONSTRUCTION_V1`
- `material_type`: prospective data/graph protocol contract
- `status`: `REGISTERED / IMPLEMENTATION_AND_EXECUTION_NOT_AUTHORIZED`
- `paper_authority`: *Multifaceted Scenario-Aware Hypergraph Learning for
  Next POI Recommendation*, AAAI 2026, DOI
  `10.1609/aaai.v40i18.38552`
- `paper_source_authority`: `COCOMiss/MSAHG` commit
  `3d74d70c852c56adcc09d907488410be5eda2744`
- `data_protocol_authority`: `alipay/Spatio-Temporal-Hypergraph-Model` commit
  `27b595846d29019799485985bff49f9ed02c4ade`
- `qualified_sample_authority`: commit
  `9e67e05875540cc87a21e15c4ff3623400c6ab49`, path
  `reproduction/results/sthgcn_sample_materializer_r1_a53acb3/`
- `parent_audit`: commit
  `e9a6c5293de1bcf50df2720f9f473571e308e3c8`
- `intended_output`: deterministic, score-free scenario and graph material
- `not_an_output`: trained model, checkpoint, loss, recommendation metric, or
  paper-table reproduction
- `principal_limitation`: the paper and source do not identify one common
  executable graph/scenario protocol; V1 is an explicit reconstruction

## 1. Decision and purpose

```text
PAPER_FAITHFUL_REPRODUCTION              = BLOCKED
RECONSTRUCTION_VARIANT                  = MARGINAL_AXIS_V1
CAUSAL_SCENARIO_AND_GRAPH_PROTOCOL      = PROSPECTIVELY_FROZEN
SCENARIO_OR_GRAPH_IMPLEMENTATION        = NOT_AUTHORIZED
MATERIALIZATION_EXECUTION               = NOT_AUTHORIZED
MODEL_IMPLEMENTATION_OR_TRAINING        = NOT_AUTHORIZED
METRICS_OR_TARGET_EVALUATION            = NOT_AUTHORIZED
```

This contract defines one reproducible way to put the MSAHG model family on the
qualified STHGCN NYC and TKY sample surface. It is designed to answer a later
multi-scenario next-POI question without using validation/test interactions to
construct static graph state.

V1 is **not** described as an exact reproduction of the paper or its released
sample. Every underdetermined choice is named below. Passing a future
target-free qualification would establish only data/graph coherence, not
predictive value.

## 2. Why the reconstruction is marginal-axis rather than joint

The frozen evidence contains three different structures:

1. the paper assigns a user label, time label, and spatial label to each
   trajectory, creating eight possible joint triples;
2. the paper describes eight split graph views: two collaborative, two
   temporal-user, two temporal-POI, and two geographical;
3. the released optimizer defines six tasks: `User/0`, `User/1`, `Time/0`,
   `Time/1`, `POI/0`, and `POI/1`.

The paper's worked example suggests simultaneous selection of a collaborative,
temporal, and geographical view for one sample. The released code instead
selects only the graph associated with the currently optimized marginal task.
It provides neither eight joint APS task IDs nor a compositional rule for
combining three separately split parameter banks.

V1 therefore freezes the source-compatible **six marginal tasks**. Each task
selects one axis-specific graph pair and consumes registered global views for
the other axes. The joint triple is retained only for support auditing. This is
a deliberate reconstruction choice, not an interpretation of missing source.

Consequences:

- V1 produces six task-conditional prediction problems, not one uniquely
  defined composite predictor.
- A future joint/compositional scenario model must receive a new theory,
  architecture, and score contract.
- No V1 result may be summarized as an overall metric by averaging the six
  tasks unless that aggregation is separately registered before scoring.

## 3. Frozen causal and label boundary

### 3.1 Record authority

Only the deterministic files represented by
`reproduction/results/sthgcn_sample_materializer_r1_a53acb3/FULL_OUTPUT_SHA256SUMS`
may be consumed. The full CSV files are regenerated from the frozen STHGCN
archives and must match those hashes before use.

Vocabulary, split membership, eligible endpoints, timestamps, source order,
trajectory IDs, POI coordinates, and raw category names inherit the completed
STHGCN Sample Materializer R1 contract. No row may be added, removed, relabeled,
or moved between splits here.

### 3.2 Offline transductive training boundary

- Static user labels, POI labels, and all graph views are fitted from every
  post-filter **training** event, including training events that are not
  eligible prediction targets.
- They may use the complete training period. This is an offline transductive
  training convention, not an event-by-event online convention.
- Validation/test prefixes may later enter a registered sequence input, but
  validation/test events may not change any static label, center, graph edge,
  weight, degree, normalization, or vocabulary.
- No validation/test target, later event, metric, or released MSAHG group label
  may influence construction.

### 3.3 Per-example observed prefix

For an eligible target event at trajectory position `j > 0`, the observed
prefix is exactly positions `0..j-1` in that materialized trajectory. The
scenario's time and spatial labels use position `j-1`. They never use the
target event at position `j`.

### 3.4 User axis: local versus tourist

For each train-known user `u`, define

```text
hotel_share(u) =
    number of post-filter training events whose raw category name is exactly "Hotel"
    -------------------------------------------------------------------------------
                      number of all post-filter training events of u
```

- `User/0 = local` iff `hotel_share(u) <= 0.05`.
- `User/1 = tourist` iff `hotel_share(u) > 0.05`.
- String matching is Unicode code-point exact after the CSV parser's normal
  decoding; no stemming, synonym expansion, category hierarchy, or case
  folding is permitted.
- A train-known user with zero training events is a protocol failure.

This is a transparent reconstruction. The paper presents accommodation
categories and 5 percent as examples and does not publish a complete builder;
V1 does not claim to recover the authors' user labels.

### 3.5 Time axis: workday versus weekend

Let the final observed prefix event's materialized local timestamp have
weekday `w`, using ISO numbering Monday `0` through Sunday `6`.

- `Time/0 = workday` iff `w in {0,1,2,3,4}`.
- `Time/1 = weekend` iff `w in {5,6}`.
- Its half-hour slot is `2 * hour + floor(minute / 30)`, in `0..47`.
- Timezone conversion is inherited from Sample Materializer R1 and is not
  recomputed by this layer.

### 3.6 Spatial axis: central versus peripheral

The paper does not disclose a city-center authority. V1 therefore uses a
deterministic train-only **activity center**, not a claimed downtown coordinate.

For every train-known POI:

1. validate that every training latitude/longitude is finite and within
   `[-90,90] x [-180,180]`;
2. compute the coordinate-wise median latitude and longitude across its
   post-filter training events;
3. reject a POI when either coordinate has an even-sample median whose two
   middle values are non-finite (ordinary numeric averaging is otherwise used).

The dataset activity center is the coordinate-wise median across the unique
train-known POI coordinates. POIs are weighted equally, regardless of check-in
frequency. The center is serialized as IEEE-754 binary64 decimal round-trip
text and its raw bytes are hashed.

Using double-precision haversine distance with Earth radius
`6,371.0088 km`:

- `POI/0 = central` iff the last observed prefix POI is at distance
  `<= 10.0 km` from the activity center;
- `POI/1 = peripheral` iff the distance is `> 10.0 km`.

Boundary ties are central. The words `downtown` and `suburban` are forbidden in
V1 result claims because this activity-center construction is not the paper's
unreleased civic-center rule.

### 3.7 Joint label triples

Each eligible sample receives the ordered metadata triple
`(User/g_u, Time/g_t, POI/g_p)`. All eight possible triples are counted for
train, validation, and test independently. The triple:

- is not a seventh or eighth task;
- does not select an APS bank;
- does not authorize a composite forward pass;
- is not used to tune thresholds, merge groups, or drop samples.

## 4. Frozen graph semantics

### 4.1 Shared conventions

Let `U`, `P`, and `T=48` be the train-known user count, POI count, and half-hour
slot count. All base incidence values are binary: duplicate occurrences set an
entry to one and do not add weight. Construction uses training events only.

Every relation has one explicitly oriented raw binary matrix `B`. Each
directional propagation operator is obtained by independently row-normalizing
`B` or `B^T`:

```text
row_normalize(M)[i,j] = M[i,j] / sum_k M[i,k]  when the row sum is positive
                      = 0                      otherwise
```

This definition avoids treating source-code variable names as mathematical
orientation. A zero-degree row stays zero. No graph edge dropout is applied
during materialization or training: graph keep rate is exactly `1.0`.
Model-layer dropout remains a future model-contract setting and is not part of
graph identity.

Sparse coordinates must be lexicographically sorted and coalesced before
serialization. Shapes, index dtype, value dtype, nonzero count, and SHA256 are
receipt fields.

### 4.2 Collaborative views

V1 follows the released model's executable POI-to-user-to-POI operator rather
than the paper prose that calls each trajectory a hyperedge.

- `B_C_global` has shape `P x U`.
- `B_C_global[p,u] = 1` iff user `u` visits POI `p` in at least one training
  event.
- `B_C_0` and `B_C_1` have the same `P x U` shape; a column is populated only
  when that user has the corresponding frozen user label and is zero otherwise.
- `B_C_global` must equal the Boolean union of `B_C_0` and `B_C_1`, and their
  supports must be disjoint.
- The POI-to-user operator is `row_normalize(B_C^T)` with shape `U x P`; the
  user-to-POI operator is `row_normalize(B_C)` with shape `P x U`.

This choice permits the model to derive a full `U x d` user surface through
the transposed incidence. V1 explicitly records
`TRAJECTORY_HYPEREDGE_CLAIM_NOT_REPRODUCED`; substituting a `P x trajectory`
matrix would require an additional trajectory-to-user operator and a new
contract.

### 4.3 Temporal POI and temporal user views

- `H_TP_global` has shape `T x P`; entry `(t,p)` is one iff a training event
  visits POI `p` in half-hour slot `t`.
- `H_TU_global` has shape `T x U`; entry `(t,u)` is one iff user `u` has a
  training event in slot `t`.
- For `g in {workday, weekend}`, `H_TP_g` and `H_TU_g` use only training events
  whose own local weekday belongs to group `g`.
- Each global incidence is the Boolean union of its two disjoint event-group
  supports. An incidence coordinate may appear in both group matrices when the
  same user or POI occurs in the same slot on both workdays and weekends; this
  is legal and must be reported.

The scenario label for a sample uses the final prefix event, while temporal
graph construction uses every training event. These roles must not be mixed.

### 4.4 Geographical views

For each train-known POI, use the POI coordinate defined in Section 3.6 and its
static central/peripheral label under the same 10-km activity-center boundary.

Construct symmetric binary adjacency matrices `A_G_global`, `A_G_0`, and
`A_G_1`, each of shape `P x P`:

- `(p,q)` is present in `A_G_global` iff haversine distance is
  `<= 2.5 km`;
- `(p,q)` is present in `A_G_g` iff it is present globally and both POIs have
  spatial label `g`;
- self loops are present because distance `(p,p)=0`;
- cross-region edges exist only in `A_G_global` and in neither split view;
- normalization is left random-walk normalization `D^-1 A`, with zero-degree
  inverse set to zero.

The 2.5-km neighborhood threshold is inherited from the paper's implementation
setting; the 10-km label threshold serves a different role and must not be
substituted for it.

### 4.5 Shared directed transition view

For each training trajectory, enumerate only consecutive pairs
`(p_j, p_{j+1})`. Deduplicate identical directed pairs across the complete
training surface and sort them lexicographically by `(source,target)`. Each
distinct pair is one directed hyperedge `e`.

- `B_source` and `B_target` both have shape `P x E`.
- `B_source[source(e),e] = 1` and `B_target[target(e),e] = 1`; every column of
  each matrix contains exactly one nonzero.
- The source-read operator is `row_normalize(B_source^T)` with shape `E x P`.
- The target-write operator is `row_normalize(B_target)` with shape `P x E`.
- Their registered product
  `target_write @ source_read @ POI_values` propagates source information to
  target POIs.
- self-transitions are retained when consecutive POIs are identical.
- non-consecutive earlier-to-later pairs are forbidden.
- the transition view is shared across all six tasks.

The implementation adapter must prove the orientation used by the model core
with a two-node asymmetric synthetic witness. The existing paper-math reference
uses historically confusing `tar/src` key names; the future adapter must bind
them to the source-read and target-write roles above. Variable names alone are
not accepted as proof of orientation.

## 5. Task-to-graph routing

Every task bundle contains one collaborative pair, one temporal-POI pair, one
temporal-user pair, one geographical adjacency, and the shared transition pair.

| Task | Collaborative | Temporal POI/user | Geography | Eligible examples |
|---|---|---|---|---|
| `User/0` | `H_C_0` | global | global | user label local |
| `User/1` | `H_C_1` | global | global | user label tourist |
| `Time/0` | global | workday | global | prefix label workday |
| `Time/1` | global | weekend | global | prefix label weekend |
| `POI/0` | global | global | `A_G_0` | prefix label central |
| `POI/1` | global | global | `A_G_1` | prefix label peripheral |

Each eligible physical target is represented once in each axis and therefore
appears in exactly three task datasets. It must appear in only one group within
an axis. A future loss may sum or schedule the six task losses only under a
separate model/training contract.

The official-source behavior of using one unsplit geography matrix for both
POI groups is rejected for V1 because it makes the spatial task label unable to
select spatial topology.

## 6. Output contract for a future materializer

A future add-only implementation may write one fresh root per dataset
containing:

- `scenario_labels.jsonl`: stable sample identity plus three marginal labels
  and one joint triple;
- `activity_center.json`: center method, binary64 round-trip coordinates, and
  input identity;
- `group_support.json`: examples and distinct users for every split/marginal
  group, plus counts for all eight joint triples;
- `graph_manifest.json`: semantic names, shapes, dtypes, nonzeros, and hashes;
- immutable sparse tensor shards for the exact global/split incidences and
  transition pair;
- `materialization_receipt.json` and `SHA256SUMS`.

The output directory must not exist. Partial or failed output is preserved and
must not be overwritten or silently retried.

## 7. Target-free qualification gates

All gates fail closed.

1. `C0_AUTHORITY`: exact parent, paper/source commits, materializer result, and
   input hashes.
2. `C1_NO_EVAL_FIT`: labels, center, graphs, degrees, and normalization use
   training events only.
3. `C2_PREFIX_LABEL`: time/spatial labels use position `j-1`, never target
   position `j`.
4. `C3_USER_RULE`: exact Hotel share, strict `>0.05`, and complete denominator.
5. `C4_TIME_RULE`: exact local weekday and half-hour mapping.
6. `C5_SPATIAL_RULE`: exact unweighted unique-POI median activity center,
   haversine constants, and boundary ties.
7. `C6_LABEL_PARTITION`: each sample has exactly one label per axis; all six
   marginal groups are nonempty.
8. `C7_JOINT_METADATA_ONLY`: eight-cell counts are reported but cannot alter
   tasks or data.
9. `C8_COLLABORATIVE`: shapes, binary union, group columns, and disjoint user
   assignment are exact.
10. `C9_TEMPORAL`: global/split POI/user incidence semantics are exact.
11. `C10_GEOGRAPHY`: 2.5-km adjacency, 10-km group labels, self loops,
    cross-region rule, and normalization are exact.
12. `C11_TRANSITION`: distinct consecutive directed pairs only, including an
    asymmetric orientation witness.
13. `C12_ROUTING`: exact six-task bundle table and three-copies-per-target
    invariant.
14. `C13_DETERMINISM`: two fresh CPU runs produce byte-identical labels,
    centers, graph manifests, sparse shards, and checksums.
15. `C14_CAUSAL_PERTURBATION`: changing or deleting validation/test records in
    a synthetic fixture cannot change any train-derived label, center, graph,
    or hash.
16. `C15_SOURCE_IMMUTABLE`: both upstream source trees remain at their frozen
    commits and clean.
17. `C16_SCORE_FREE`: no model forward, loss, ranking, metric, checkpoint,
    optimizer, or target evaluation.
18. `C17_FAIL_CLOSED`: missing, extra, malformed, or false gates return
    nonzero and preserve evidence.

## 8. Statistical support gate before any score contract

Target-free materialization must report, without threshold search:

- for each of the six marginal groups and each split: target count and distinct
  user count;
- for each of the eight joint triples and each split: target count and distinct
  user count.

A six-task score contract is inadmissible unless every marginal group has:

- at least `200` train targets and `30` distinct train users;
- at least `100` validation targets and `30` distinct validation users;
- at least `100` test targets and `30` distinct test users.

Joint cells do not block the six marginal tasks. A later joint-scenario claim is
inadmissible for any joint cell with fewer than `100` evaluation targets or
`30` distinct evaluation users. No group may be merged, threshold changed, or
sample removed to satisfy support after counts are observed.

These are admissibility floors, not claims of statistical power or performance.

## 9. Falsification and STOP rules

```text
TARGET_FREE_PASS = C0..C17 all true

if any C gate fails:
    decision = PROTOCOL_FAILURE
    action   = STOP; preserve output; no automatic repair or retry

if TARGET_FREE_PASS and any marginal support floor fails:
    decision = DATA_NOT_ADMISSIBLE_FOR_SIX_TASK_SCORE
    action   = STOP before model implementation/training

if TARGET_FREE_PASS and support floors pass:
    decision = MATERIALIZATION_QUALIFIED_ONLY
    action   = request separate model and score-bearing authority
```

A future empirical result must be adjudicated against a separately frozen score
contract. In particular:

- target-free PASS cannot be called a positive model result;
- a gain in one task cannot be generalized to the other five;
- a six-task metric cannot be called a joint-scenario result;
- no result can be compared with the paper table as an exact reproduction;
- no validation/test result may be used to revise these scenario or graph
  definitions.

## 10. Current authorization boundary

Authorized and completed by this document:

- prospective selection of the `MARGINAL_AXIS_V1` reconstruction;
- exact causal, scenario, graph, routing, output, support, and STOP semantics;
- add-only publication of this contract and its registry.

Not authorized:

- materializer code or tests;
- reading/regenerating the full public CSV outputs for this new purpose;
- scenario-label, activity-center, or graph materialization;
- model/data-loader adaptation;
- APS, optimizer, loss, training, inference, checkpoint selection, or metrics;
- NYC/TKY target-bearing evaluation;
- joint/composite scenario routing;
- any claim of improvement, reproduction, or a new contribution.

The next lawful stage, if separately approved, is an add-only target-free
materializer implementation and synthetic qualification. A PASS there would
still require a new model/training contract before any score-bearing run.
