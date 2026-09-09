# MSAHG AAAI 2026 official-sample replay R0R2

## Decision

- Official released NYC sample source replay: **COMPLETE**
- Paper Table 1 reproduction: **NOT ESTABLISHED**
- Independent test evidence: **INVALID BY UPSTREAM PROTOCOL**
- Adaptive parameter separation on this sample: **NOT ACTIVATED**

This result is independent of GUGEN and CIPRA. It starts MSAHG from random
initialization and consumes only the official repository's `datasets/sample.zip`.

## Identity

- Frozen official upstream: `COCOMiss/MSAHG`
- Frozen upstream commit: `3d74d70c852c56adcc09d907488410be5eda2744`
- Reproduction fork: `xiaolaoji66/MSAHG`
- R0R2 wrapper commit: `c723862aa39ca0aeaba11aabf0501bb13ca0d215`
- Seed: `2023`
- Dataset argument: `NYC`
- Requested epochs: `100`
- Executed epochs: `42` (`0` through `41`; upstream early stop then fired)
- Saved checkpoint epoch: `30`
- Saved checkpoint `task_groups`: `{}`

## Environment

The run used Python 3.10.20, PyTorch 2.4.1+cu118, DGL 1.1.3, CVXPY 1.5.2,
and one NVIDIA GeForce RTX 2080 Ti. Exact versions are in `environment.txt`.

This is not claimed to be an exact environment replay: the upstream README
requires Python 3.12+, while its `environment.yml` pins Python 3.8.20 and omits
DGL and CVXPY.

## Emitted group diagnostics

| Scenario | Group | Acc@1 | Acc@5 | Acc@10 | Acc@20 | MRR |
|---|---:|---:|---:|---:|---:|---:|
| User | 0 | 0.218750 | 0.527083 | 0.625000 | 0.687500 | 0.350899 |
| User | 1 | 0.206250 | 0.458333 | 0.537500 | 0.581250 | 0.315890 |
| Time | 0 | 0.168750 | 0.508333 | 0.643750 | 0.689583 | 0.321167 |
| Time | 1 | 0.233333 | 0.535417 | 0.618750 | 0.658333 | 0.354708 |
| POI | 0 | 0.287500 | 0.670833 | 0.785417 | 0.827083 | 0.453214 |
| POI | 1 | 0.145833 | 0.400000 | 0.493750 | 0.562500 | 0.260664 |

These are upstream-emitted sample diagnostics, not comparable paper results.
The source repeatedly creates a new dataloader iterator inside each step and
uses the same `test.pkl` both for per-epoch checkpoint decisions and final
reporting. It also force-saves at epochs 20 and 30. In this run, the upstream
checkpoint criterion was highest at epoch 5 (`17.777000`) but the final stored
checkpoint is epoch 30; therefore the archived scores are neither an
independent test nor a clean best-checkpoint estimate.

## Files

- `console.log`: complete wrapper/stdout/stderr log
- `environment.txt`: runtime package and CUDA versions
- `FULL_OUTPUT_SHA256SUMS`: hashes of every file in the immutable server output
- `result/NYC.pt`: upstream checkpoint
- `result/NYC_args.yaml`: upstream arguments
- `result/group_result.txt`: upstream group metrics
- `result/log_training.txt`: upstream training/evaluation log
- `RESULT_RECEIPT.json`: mechanical result summary
- `ARCHIVE_SHA256SUMS`: archive integrity hashes

The complete server output remains at:

```text
/mnt/data4t/wyh/msahg_runs/msahg_official_sample_r0r2-c723862a-gpu0
```
