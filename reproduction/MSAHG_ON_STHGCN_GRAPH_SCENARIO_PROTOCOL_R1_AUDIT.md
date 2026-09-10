# MSAHG on STHGCN Graph and Scenario Protocol R1 - Read-Only Audit

Date: 2026-09-10

## 1. Decision

```text
PAPER_FAITHFUL_SCENARIO_PROTOCOL = BLOCKED
UPSTREAM_SOURCE_AS_GRAPH_AUTHORITY = REJECTED
STHGCN_CAUSAL_RECONSTRUCTION = FEASIBLE_BUT_NOT_YET_CONTRACTED
GRAPH_OR_SCENARIO_MATERIALIZATION = NOT_AUTHORIZED
MODEL_TRAINING_OR_METRICS = NOT_AUTHORIZED
```

The paper supplies a scientifically meaningful scenario idea, but the paper and
released source do not jointly determine one executable graph-and-scenario
protocol. A public-data engineering reconstruction is possible, but it must be
named and evaluated separately from a paper-faithful reproduction.

This decision does not reject MSAHG as a research idea and does not say that
scenario-aware hypergraphs are ineffective. It only rejects silent substitution
of missing semantics and use of the released source as if it exactly implemented
the paper.

## 2. Frozen authorities

- Paper: *Multifaceted Scenario-Aware Hypergraph Learning for Next POI
  Recommendation*, AAAI 2026, DOI `10.1609/aaai.v40i18.38552`.
- MSAHG official source: `https://github.com/COCOMiss/MSAHG`, frozen commit
  `3d74d70c852c56adcc09d907488410be5eda2744`.
- MSAHG reproduction repository: `https://github.com/xiaolaoji66/MSAHG`.
- This audit's base/result authority:
  `9e67e05875540cc87a21e15c4ff3623400c6ab49`.
- STHGCN official source:
  `https://github.com/alipay/Spatio-Temporal-Hypergraph-Model`, frozen commit
  `27b595846d29019799485985bff49f9ed02c4ade`.
- Completed public sample materialization result:
  `reproduction/results/sthgcn_sample_materializer_r1_a53acb3/`.

No GUGEN source, data, checkpoint, or result is an input to this audit.

## 3. Three quantities that must not be conflated

The phrase "six scenarios" is ambiguous. The frozen evidence contains three
different counts:

1. **Six marginal scenario groups/tasks**: `User/0`, `User/1`, `Time/0`,
   `Time/1`, `POI/0`, and `POI/1`. The released source allocates six loss slots
   through `sum({User:2, Time:2, POI:2})` and reports each marginal group.
2. **Eight split sub-hypergraphs** described by the paper: two collaborative,
   two temporal-user, two temporal-POI, and two geographical sub-hypergraphs.
   The transition view is one additional directed graph shared across groups.
3. **Eight possible joint label triples** from
   `2 x 2 x 2 = 8`. The paper says each trajectory forms a combined scenario,
   but the released training loop does not create eight joint task IDs.

R1 therefore cannot call the six source tasks eight composite scenarios. A
future reconstruction may preserve the six marginal tasks for comparison and
record the joint triple only as metadata, but that choice requires a prospective
contract.

## 4. Scenario identifiability audit

### 4.1 User type - blocked as a paper-faithful rule

The paper says a user is a tourist when accommodation check-ins, for example at
hotels or resorts, exceed a threshold percentage, for example 5 percent. The
examples do not fix:

- the complete accommodation category set;
- whether the threshold is exactly 5 percent;
- whether the boundary is `>` or `>=`;
- the denominator and filtering surface;
- whether validation/test check-ins are permitted in a static user label.

The released source only loads `user_group.pkl`; it contains no label builder.
The official sample has 159 labels: 114 in group 0 and 45 in group 1. On its
released train surface, the literal rule `category == Hotel` and share `> 0.05`
predicts only 8 group-1 users and disagrees with 37 of the stored labels.
Adding obvious broader categories such as Residence or Travel increases, rather
than resolves, the disagreement. This does not prove that the stored labels are
wrong; it proves that their construction is not identified by the released
materials.

The STHGCN NYC and TKY raw category-name vocabularies each contain the literal
category `Hotel`; the bounded lodging-name scan used here did not find a
separate resort/hostel/motel category. A future transparent reconstruction could
freeze `Hotel` as its complete category set and use training records only, but
that would be a new protocol choice.

### 4.2 Temporal context - reconstructable, not source-provenanced

The paper assigns weekday/weekend from the final check-in timestamp. The source
maps encoded values `0..47` to group 0 and `48..95` to group 1, but releases no
preprocessor establishing what those 96 values mean.

The qualified STHGCN materialization retains local timestamps and weekdays, so
a prospective rule can be exact: use the last **observed prefix event**, define
Monday-Friday as workday and Saturday-Sunday as weekend, and never use the next
POI target timestamp. That rule is implementable, but it is a reconstruction,
not evidence that the released MSAHG integers have the same provenance.

### 4.3 Spatial context - blocked as a paper-faithful rule

The paper fixes a 10-km radius but does not disclose NYC/TKY/Gowalla center
coordinates or the exact center authority. The source only consumes a
precomputed `city_tag` stored inside POI metadata and contains no label builder.

The official sample contains 4,981 tag-1 and 1,889 tag-0 POIs. A bounded grid
diagnostic found many nearby coordinates around `(40.7162, -74.0067)` that
reproduce those labels at 10 km, while a common NYC City Hall coordinate leaves
37 disagreements. This is evidence of non-unique reverse fitting, not authority
for selecting one center. STHGCN does not release these `city_tag` labels.

A future reconstruction must choose one of two explicit semantics:

- a fixed civic anchor with a frozen primary coordinate source; or
- a deterministic train-only activity center, in which case the groups must be
  named central/peripheral rather than claimed to be the authors' downtown and
  suburban labels.

No center is selected by this audit.

## 5. Released graph code versus paper claims

The following are direct source facts, not inferred performance effects.

| Surface | Paper claim | Released-source behavior | R1 consequence |
|---|---|---|---|
| Collaborative | POI nodes; each trajectory is a hyperedge | `gen_sparse_H_user` concatenates all trajectories for a user and uses one user column | Source does not implement the stated trajectory-hyperedge unit |
| Temporal | separate workday/weekend temporal-user and temporal-POI hypergraphs | source creates two matrices from an unprovenanced 96-slot encoding | Topology is readable; semantic labels are not identified |
| Geography | two region-specific geographical sub-hypergraphs | source constructs one POI adjacency per train/test split and never indexes it by region | The stated pair of geographical sub-hypergraphs is absent |
| Transition | one shared graph of consecutive directed transitions | source connects every earlier POI to every later POI inside a trajectory | Source transition semantics are transitive-order pairs, not consecutive pairs |
| Evaluation graph | unspecified | test datasets independently build collaborative, temporal, geographical, and transition structures from `test.pkl` and `test_poi.pkl` | Not admissible as a train-only benchmark authority |
| Task set | composite label triple in prose | `2+2+2=6` marginal task losses and reports | Joint eight-cell training is not implemented |

The model route confirms the geography defect: only the User mode selects a
scenario-specific collaborative matrix and only the Time mode selects
scenario-specific temporal matrices. Every POI-mode batch uses the same
`dataset.poi_geo_graph`; POI group affects sampling/task identity, not the
geographical graph topology.

## 6. Why source-exact reuse is rejected

Copying the released objects would create an internally inconsistent result:

- it would call a per-user incidence matrix a per-trajectory hypergraph;
- it would call all ordered within-trajectory pairs consecutive transitions;
- it would report split geography without having split geographical topology;
- it would allow validation/test interactions to alter graph structure;
- it would preserve six marginal tasks while describing them as eight joint
  scenarios.

These are protocol errors, not harmless implementation details. A source-exact
run may remain a diagnostic of the repository, but it cannot be the authority
for a new same-protocol STHGCN experiment.

## 7. Minimum admissible reconstruction candidate

The following is a **draft candidate**, not an executable contract.

### 7.1 Causal input boundary

- Construct every static graph from training interactions only.
- Freeze graph topology and normalization before validation/test scoring.
- Validation/test prefixes may be consumed only by an explicitly registered
  per-example sequence/context input; they may not mutate a global graph.
- Never use validation/test targets, later events, or cross-example evaluation
  interactions in graph construction.
- Fit user/POI/category vocabularies on training records exactly as qualified by
  the STHGCN materializer.

### 7.2 Candidate scenario labels

- `User/local` versus `User/tourist`: train-only per-user Hotel share, tourist
  iff share `> 0.05`; denominator is every post-filter training check-in of the
  user. This is provisional until accepted as a reconstruction choice.
- `Time/workday` versus `Time/weekend`: last observed prefix event in local
  time; Monday-Friday versus Saturday-Sunday.
- `POI/central` versus `POI/peripheral`: **OPEN** until a center rule is selected.
- Each sample carries all three labels. The primary APS/evaluation task set is
  the six marginal groups; the joint triple is recorded for support auditing
  only and receives no automatic model branch.

### 7.3 Candidate graph semantics

- Collaborative: binary POI-by-trajectory incidence; one training trajectory is
  one hyperedge; two matrices selected by the trajectory owner's user label.
- Temporal-user: binary half-hour-slot-by-user incidence from training events;
  separate workday/weekend matrices.
- Temporal-POI: binary half-hour-slot-by-POI incidence from training events;
  separate workday/weekend matrices.
- Geography: binary POI-by-neighborhood incidence with a 2.5-km neighborhood
  threshold; two regional matrices; anchors and members must be within the same
  registered region.
- Transition: one shared directed incidence with one hyperedge per distinct
  consecutive training pair; no transitive-order expansion.
- Normalization, isolated-node behavior, duplicate handling, and graph weights
  remain OPEN and must be frozen before implementation.

## 8. Gates required before implementation

The next prospective contract must fail closed on all of the following:

1. exact parent/source/data identities;
2. one chosen, named spatial-center rule for NYC and TKY;
3. exact scenario label definitions and boundary ties;
4. non-empty marginal groups and joint-cell support reported without tuning;
5. train-only graph provenance and no evaluation graph mutation;
6. exact incidence shapes, binary/count semantics, normalization, and isolated
   nodes;
7. exact eight split sub-hypergraphs plus one shared transition graph;
8. six-task ID bijection, with joint triples explicitly non-task metadata;
9. deterministic two-run byte identity;
10. no score, loss, checkpoint selection, or target evaluation.

## 9. Current authorization boundary

Authorized and completed here:

- read-only paper/source/public-record audit;
- versioned documentation of findings and a non-executable candidate protocol.

Not authorized here:

- scenario-label or graph materialization;
- selecting a spatial anchor by matching released labels;
- implementing a model data loader;
- training, metrics, validation/test evaluation, or hyperparameter selection;
- describing any future STHGCN result as a paper-table reproduction.

The next legitimate step is a separate prospective decision choosing whether to
stop, request missing author materials, or contract a clearly named
`MSAHG-on-STHGCN Causal Reconstruction V1`.
