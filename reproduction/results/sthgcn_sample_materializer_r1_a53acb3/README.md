# STHGCN Sample Materializer R1 — Score-Free Result

Decision: `PASS`

## Authorities

- prospective registration: `7c813210665f61197e68e7e794c5da091a259569`
- portability authority: `cc91340e466f151c8e54777d35453f2c48721774`
- initial implementation: `9c317ea01ecd177a1e0d195a2cb97f8de6694b2d`
- provenance-bound implementation: `a53acb3a3f637c2da372661ed95559f92881f8fa`
- STHGCN source: `27b595846d29019799485985bff49f9ed02c4ade`

## Count qualification

| Dataset | Users | POIs | Post-filter events | Trajectories | Train targets | Validation endpoints | Test endpoints |
|---|---:|---:|---:|---:|---:|---:|---:|
| NYC | 1,048 | 4,981 | 103,941 | 14,130 | 72,206 | 1,407 | 1,357 |
| TKY | 2,282 | 7,833 | 405,000 | 65,499 | 274,597 | 6,875 | 7,049 |

The first four fields for each dataset exactly match the count witnesses
registered from the public STHGCN release. Eligible target counts are newly
materialized descriptive facts; they were not used to tune the protocol.

## Evidence

- both dataset receipts: `PASS`, 14/14 gates;
- independent output audit: `PASS`;
- source worktree remained clean at the exact STHGCN commit;
- a second fresh materialization produced byte-identical `sample.csv`, split
  files, and label mappings for both datasets;
- no graph, hypergraph, scenario label, checkpoint, loss, recommendation
  metric, inference, or training activity occurred.

The full CSVs are 181 MB and are not duplicated in Git. Their raw hashes are
frozen in `nyc/FULL_DATASET_SHA256SUMS` and
`tky/FULL_DATASET_SHA256SUMS`; they are regenerated from the frozen public
archives by `scripts/run_sthgcn_sample_materializer_r1.sh`. The deterministic
label maps and all receipts are archived here.

## Interpretation boundary

This PASS establishes a portable, score-free reconstruction of the public
STHGCN sample protocol. It is not a reproduction of the MSAHG paper table and
does not establish predictive gain. Graph construction, MSAHG scenarios,
model adaptation, training, and evaluation remain unregistered.
