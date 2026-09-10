# STHGCN Sample Protocol R1 — Score-Free Qualification

Date: 2026-09-10

## Authorities

- MSAHG registration: `87e21b86f39f7491e2460f0647ace0e14d6fbb17`
- Auditor implementation: `f606afafd6b71e3fa34142207a8dc162d71cbe15`
- STHGCN upstream: `27b595846d29019799485985bff49f9ed02c4ade`
- STHGCN repository: `https://github.com/alipay/Spatio-Temporal-Hypergraph-Model`

## Result

```text
DECISION          = PASS
GATES             = 13 / 13
TRAINING          = false
RECOMMENDER SCORE = false
SAMPLE MATERIAL   = false
GRAPH MATERIAL    = false
SCENARIO LABELS   = false
```

The PASS establishes the identity and inspectability of the public STHGCN
sample-protocol source only. It does not establish that the released TKY
chained assignment is portable, that the combined-file STHGCN graph is an
admissible MSAHG input, or that the MSAHG scenario labels are identified.

The next mechanical state is:

```text
SAMPLE_PROTOCOL_SOURCE = QUALIFIED
SAMPLE_MATERIALIZER     = NOT AUTHORIZED
SCENARIO_LABEL_PROTOCOL = NOT REGISTERED
MSAHG TRAINING          = NOT AUTHORIZED
PAPER-TABLE REPRODUCTION = BLOCKED
```

## Registered hazards preserved by the receipt

- the TKY validation/test split uses Pandas chained assignment;
- the STHGCN PyG builder starts from combined `sample.csv`;
- the six MSAHG scenario labels remain under-specified.

`qualification_receipt.json` is the immutable machine-readable result.
