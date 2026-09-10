# MSAHG-on-STHGCN causal materializer V1R2 real runtime — protocol failure

- Date: `2026-09-10`
- Decision: `PROTOCOL_FAILURE / STOP_PRESERVE_NO_RETRY`
- V1R2 registration commit: `14b4de54aef4e1cf6640601b87655c4bb4934314`
- V1R2 audit implementation commit: `c5ff38e8cb346fbd6ca3d41c70c83971c6fc6f39`
- Production materializer commit: `1f6fce9505eae929a8f131fc67556e513c4d1100`
- Server audit worktree: `/mnt/data4t/wyh/MSAHG-causal-materializer-real-audit-v1r2-c5ff38e`
- Preserved server output root: `/mnt/data4t/wyh/msahg_runs/msahg_on_sthgcn_causal_materializer_v1r2_real-515c72a`
- Preserved `execution.log` bytes: `48`
- Preserved `execution.log` SHA256: `9ea5a445cd45d9de360801a6718d965a458f694a27e7aa5dcdfc033aef25f8d0`

The registered server environment passed all nine pre-materialization tests,
including direct acceptance of the corrected V1R2 authority by the immutable
production verifier and rejection of the exhausted V1 binding. The first NYC
materializer invocation then stopped with the exact line:

```text
PROTOCOL_FAILURE=unknown train-fitted UserId id
```

No NYC or TKY dataset directory was created. There is no materialization
receipt, scenario ledger, graph shard, support result, model execution,
training, inference, checkpoint access, ranking metric, or target evaluation.

## Read-only failure diagnosis

The frozen NYC encoding uses:

- `UserId`: offset `0`, class count `1047`, padding ID `1047`;
- `PoiId`: offset `0`, class count `4980`, padding ID `4980`.

The frozen NYC sample contains `1240` UserId-padding rows and `1205`
PoiId-padding rows overall. Of these, `187` UserId-padding rows and `211`
PoiId-padding rows are marked as eligible by the existing rule
`OriginalSplitTag == train OR SplitTag in {train, validation, test}`. The first
reported invalid user row is source ordinal `84009`, split `validation`, with
`UserId=1047` and `PoiId=4980`.

The input identities after this read-only diagnosis remain:

- NYC `sample.csv`: `4923e232f04e6a1d28de73a2545240e021066087706a824bcb01f6b0cf9f8f65`;
- NYC `label_encoding.json`: `1d8ae8f4a04908868f9ad4e186944a9f3e84b472bd015b2bbad9b663fff3c64b`;
- NYC `record_split_provenance.csv`: `57c0b434918d5cd1bb421f2654c430a572e3e70f6c587ad398e078c8fd0f93d3`.

Both source worktrees remained clean. The dual registry binding repair itself
is qualified, but the real-data admissibility contract is not. Treating
padding/OOV targets as graph nodes, deleting them, or changing their split tag
would alter the eligible-target semantics and is not authorized by V1R2.

The failed root remains immutable on the server. This authority is exhausted;
no invocation was retried. Any resolution requires a prospective rule that
distinguishes graph-vocabulary-admissible records from score/evaluation records,
plus a new versioned scope and explicit approval.
