# STHGCN Sample Materializer V1R2 — Independent-Audit Failure Archive

Date: 2026-09-10

## Decision

```text
Server target-free qualification = PASS (15/15)
NYC materializer receipt         = PASS (17/17)
TKY materializer receipt         = PASS (17/17)
Independent audit                = FAIL
Overall V1R2 decision            = PROTOCOL_FAILURE / STOP
Automatic retry                  = NOT PERFORMED
```

The V1R2 replay-directory repair closed the V1R1 `File exists` defect and
materialized both provenance sidecars. The independent audit nevertheless
returned `FAIL`, so the run is not promoted to qualified status.

## Exact audit failure

For both NYC and TKY, every independent check passed except `gate_set`.
The 17 registered gate names are all present exactly once and every value is
`true`. The failure is caused by an order-sensitive auditor predicate:

1. the producer serializes JSON with `sort_keys=True`;
2. the resulting gate object is lexicographically ordered;
3. the auditor compares `tuple(receipt["gates"])` with the registry's numeric
   R0-R16 order;
4. JSON object member order has no semantic gate-set meaning, so this is a
   deterministic audit false negative.

This diagnosis does not override the registered audit result. V1R2 remains
`PROTOCOL_FAILURE` until a new versioned audit repair is authorized and run.

## Preserved material

- NYC sidecar: 103,941 rows;
- TKY sidecar: 405,000 rows;
- complete original-split counts and `OriginalSplitTag x SplitTag` tables;
- dataset receipts and checksums;
- root summary and checksums;
- original independent-audit receipt;
- server target-free receipt;
- mechanical adjudication and Material Passport.

All archived checksums reproduce the server bytes. No scenario label, graph,
model, checkpoint, training, inference, loss, ranking metric, or target
evaluation was produced.

## Required next version

A V1R3 audit-only repair should preserve the V1R2 sidecars and replace the
order-sensitive gate predicate with exact unique-key-set equality plus the
existing all-values-true check. It must not regenerate the sidecars or broaden
the authorized scope.
