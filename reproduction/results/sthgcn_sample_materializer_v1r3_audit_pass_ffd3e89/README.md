# STHGCN Sample Materializer V1R3 Audit Repair — PASS

Date: 2026-09-10

## Decision

```text
V1R3 = PASS / V1R2_ORIGINAL_SPLIT_PROVENANCE_QUALIFIED
```

The server target-free qualification passed all 13 registered gates. The one
authorized real audit then passed for both preserved V1R2 datasets:

- NYC: 103,941 rows; train 83,228; validation 10,339; test 10,374;
- TKY: 405,000 rows; train 326,258; validation 39,224; test 39,518.

Every per-dataset audit check passed. Input hashes before and after the audit
were identical. No materializer was executed, no sidecar was regenerated, and
no graph, model, training, inference, loss, checkpoint, recommendation metric,
or target evaluation was performed.

## Exact repair

The preserved V1R2 receipts contain the exact 17 registered gate names, each
with the exact Boolean value `true`. They were serialized lexicographically by
`json.dump(..., sort_keys=True)`. V1R2 incorrectly compared dictionary
iteration order with the registry's R0-R16 presentation order.

V1R3 ignores JSON object order while still requiring an exact unique gate-name
set and exact Boolean `true` for every value. Duplicate JSON object keys are
rejected. Missing, extra, false, and non-Boolean gates remain failures.

## Authorities and identities

- V1R3 registration: `af081053d06318ef72473859f462dbfef5ba22e0`;
- V1R3 implementation: `ffd3e89d020275a3213e7b8ad26040b317523c17`;
- V1R2 failure archive: `cc1abb0d35626ec89d4b189e3674d29d3288c670`;
- V1R2 implementation: `d73f118afa9b51a1418acd5c1fa5eb32b5b0818b`;
- server target-free receipt SHA256:
  `01f7c852aab2c242c0b17f9d87837f64e69ff3b35d9afcf124a9893efd554f2d`;
- independent audit receipt SHA256:
  `25e3cbda656c569ed399829243d26259aeb332ce9ad28c830243d976e1e34d9b`.

## Interpretation boundary

This PASS qualifies only the original train/validation/test provenance attached
to the preserved V1R2 rows. It does not authorize or validate scenario labels,
activity centers, graph or hypergraph materialization, model construction,
training, inference, ranking quality, or publication claims. Any causal graph
materializer requires a separate prospective authority.
