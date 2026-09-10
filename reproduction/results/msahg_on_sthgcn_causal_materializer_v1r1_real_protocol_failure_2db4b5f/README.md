# MSAHG-on-STHGCN causal materializer V1R1 real runtime — protocol failure

- Date: `2026-09-10`
- Decision: `PROTOCOL_FAILURE / STOP_PRESERVE_NO_RETRY`
- Registration commit: `efdb7490155ca5006592506a4347425880ecb1cd`
- Audit implementation commit: `2db4b5f6e7068a93581e4dc3d31fa7a24051ab7e`
- Production materializer commit: `1f6fce9505eae929a8f131fc67556e513c4d1100`
- Server audit worktree: `/mnt/data4t/wyh/MSAHG-causal-materializer-real-audit-v1-2db4b5f`
- Preserved server output root: `/mnt/data4t/wyh/msahg_runs/msahg_on_sthgcn_causal_materializer_v1r1_real-d7e2706`
- Preserved `execution.log` bytes: `56`
- Preserved `execution.log` SHA256: `51b79caeeaef027e26400f39772a3eea3a69ca9df80db9669948b499ca922b73`

The registered server environment completed all nine pre-materialization tests.
The first production materializer invocation then stopped with the exact line:

```text
PROTOCOL_FAILURE=real materialization is not authorized
```

The failure occurred in `verify_runtime_authority` before the materializer read
either frozen sample CSV. The production materializer requires the authority
field `registry_sha256` to equal its own implementation-registry identity
`f9ff7c5ffe4affc4ccf4ff0d44dd9089274b4e416437f34219fa6b5c33ddc1ba`,
but the registered real-runtime authority bound that field to the outer runtime
registry identity
`6e3c4d003355d26efb34b28d9b0c1c1508c5bdd3073f216cad24353c0a37d1a4`.

No NYC or TKY dataset directory was created. There is no materialization
receipt, scenario ledger, graph shard, support result, model execution,
training, inference, checkpoint access, ranking metric, or target evaluation.
This failure is a registration/authority binding defect, not a data-admissibility
or scientific result.

The failed root remains immutable on the server. In accordance with the frozen
scope, this authority is exhausted and no invocation was retried. Repair and
rerun require a new versioned scope and explicit user approval.
