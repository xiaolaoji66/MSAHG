# STHGCN Sample Materializer V1R1 Provenance — Failure Archive

Date: 2026-09-10

## Decision

```text
Synthetic target-free qualification = PASS (12/12)
Real score-free NYC/TKY execution    = PROTOCOL_FAILURE
Automatic retry                      = NOT PERFORMED
V1R1                                 = STOP
```

The single authorized real execution failed before provenance materialization
because the implementation passed a directory already created by
`tempfile.mkdtemp` to `_write_replay`, which immediately attempted to create
the same directory with `exist_ok=False`.

This is an implementation directory-ownership defect. It is not a failure of
the NYC/TKY source data, original-split semantics, or any predictive model.

## Verified preconditions

- implementation commit:
  `38db98809e6f8bb3723e61163d1b428060aba8be`;
- registration commit:
  `be5efdc1ed56b6628dde82224eaf6df2abfec1cf`;
- frozen STHGCN commit:
  `27b595846d29019799485985bff49f9ed02c4ade`;
- exact frozen V1 replay completed before the V1R1 execution;
- NYC `sample.csv`: 103,941 records, SHA256
  `4923e232f04e6a1d28de73a2545240e021066087706a824bcb01f6b0cf9f8f65`;
- TKY `sample.csv`: 405,000 records, SHA256
  `b50fbd66c09463f1e2258a3fda33f3d4a11cd33cb2c20e1ede8873dab7cb47b0`;
- STHGCN, V1, and V1R1 worktrees remained clean after failure.

## Evidence boundary

The archived target-free receipt establishes only synthetic implementation
coherence. The failure receipt records the preserved real-execution error.
No scenario label, graph, model, checkpoint, training, inference, loss,
ranking metric, or target evaluation was produced.

A corrected real execution requires a new versioned repair and explicit
authority. This archive does not authorize a retry.
