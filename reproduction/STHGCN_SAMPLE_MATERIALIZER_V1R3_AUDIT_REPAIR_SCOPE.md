# STHGCN Sample Materializer V1R3 — Audit-Only Gate-Set Repair

Date: 2026-09-10

## Material Passport

- `material_id`: `STHGCN_SAMPLE_MATERIALIZER_V1R3_AUDIT_REPAIR`
- `material_type`: prospective score-free independent-auditor repair
- `status`: `AUDITOR_IMPLEMENTATION_AND_ONE_AUDIT_EXECUTION_AUTHORIZED`
- `parent_commit`: `cc1abb0d35626ec89d4b189e3674d29d3288c670`
- `frozen_input`: archived V1R2 NYC/TKY sidecars and receipts
- `intended_output`: one revised independent-audit receipt
- `not_an_output`: regenerated data, scenario labels, graph, model, or metric

## 1. Confirmed V1R2 audit defect

V1R2 generated both provenance sidecars and recorded all 17 real gates as
`true`. Its independent auditor failed only the `gate_set` check.

The producer writes receipts through `json.dump(..., sort_keys=True)`, so gate
object keys are serialized lexicographically. The V1R2 auditor compared the
loaded dictionary's iteration order to the registry's R0-R16 presentation
order using tuple equality. JSON object member order is not part of the gate-set
semantics; therefore this was a deterministic false negative.

## 2. Exact repair

V1R3 is audit-only and add-only. It must not edit or regenerate V1R2 outputs.
The sole semantic repair is:

```text
old: tuple(observed_gate_keys) == expected_gate_sequence

new: len(observed_gate_keys) == len(expected_gate_names)
     and set(observed_gate_keys) == set(expected_gate_names)
     and every observed gate value is exactly true
```

The JSON parser must reject duplicate object keys before reduction. Missing,
extra, duplicate, non-boolean, or false gate values remain failures. File
allowlists, hashes, row identity, split provenance, replay identity, repair
witnesses, and no-downstream checks remain unchanged.

## 3. Frozen inputs

- V1R2 registration commit:
  `fd5aa7739d031c1fa20336084823a63ee56e7acc`;
- V1R2 implementation commit:
  `d73f118afa9b51a1418acd5c1fa5eb32b5b0818b`;
- V1R2 audit-failure archive commit:
  `cc1abb0d35626ec89d4b189e3674d29d3288c670`;
- V1R2 materializer source SHA256:
  `2cd6d32cc8742e6e1f3f6e95e57ff262df24c02bcf4f80d778f8d6ba0f37a91c`;
- V1R2 auditor source SHA256:
  `4c0439546c9cebe1bfc973724f60526b5bb5c7afa5a84f0b2ee288b86b668e23`;
- archived output manifest SHA256:
  `0892de52898df79d1fa97bf6bb474258ba8948f7439c0e0085c716d5491ccdd8`;
- archived V1R2 result manifest SHA256:
  `51cdd28ae2a57012a4bfa72f9ebca1ea13a47d88eae0d5f33bcc2a352fde86bc`;
- NYC sidecar SHA256:
  `57c0b434918d5cd1bb421f2654c430a572e3e70f6c587ad398e078c8fd0f93d3`;
- TKY sidecar SHA256:
  `5f287bb802943a3e8f99ff307acf2f8c47f5c4e46eab62fd62ff00c7a0de211d`;
- frozen V1 `sample.csv` files remain required only for identity comparison.

## 4. Target-free qualification

Synthetic qualification must prove that:

- all 17 exact gate names pass regardless of JSON object order;
- missing, extra, duplicate, false, and non-boolean gates fail closed;
- the frozen V1R2 receipt reproduces the old order-sensitive failure;
- the new predicate accepts the same receipt without changing it;
- no real row, model, graph, target, checkpoint, loss, or metric is accessed.

## 5. One real audit

One independent audit may read the preserved V1R2 output root and exact frozen
V1 `sample.csv` files. It may emit one fresh audit receipt. It may not write
inside the V1R2 output root or regenerate any sidecar.

A failed audit receipt is immutable evidence and stops this version. No
automatic retry is authorized.

## 6. Authorization

Authorized:

- this scope and registry;
- add-only V1R3 auditor, tests, target-free qualification, and runners;
- local and server target-free qualification;
- one audit-only execution against the preserved V1R2 result;
- add-only archival of PASS or failure evidence.

Not authorized:

- modifying V1, V1R1, V1R2, STHGCN, or archived outputs;
- re-running the materializer or regenerating sidecars;
- scenario, activity-center, graph, hypergraph, or model construction;
- training, inference, loss, checkpoint access, ranking, or metrics;
- target evaluation or additional datasets;
- automatic retry after the single real audit.

## 7. Mechanical decision

```text
if all target-free gates pass
and the one V1R3 independent audit passes:
    V1R3 = PASS / V1R2_ORIGINAL_SPLIT_PROVENANCE_QUALIFIED
else:
    V1R3 = PROTOCOL_FAILURE / STOP

V1R3 PASS != graph materializer authorization
V1R3 PASS != model or predictive evidence
```
