#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${MSAHG_V1R3_PYTHON_BIN:-python3}
registry="$repo/reproduction/MSAHG_ON_STHGCN_TARGET_ADMISSIBILITY_V1R3_REGISTRY.json"
authority="$repo/reproduction/MSAHG_ON_STHGCN_TARGET_ADMISSIBILITY_V1R3_EXECUTION_AUTHORITY.json"

exec "$python_bin" \
  "$repo/reproduction/audit_msahg_on_sthgcn_target_admissibility_v1r3.py" \
  --registry "$registry" \
  --runtime-authority "$authority" \
  --sthgcn-root /mnt/data4t/wyh/sthgcn-source-27b59584-provenance-v1r1 \
  --v1-root /mnt/data4t/wyh/msahg_runs/sthgcn_sample_materializer_r1_replay-a53acb3-v1r1-input-pandas223 \
  --v1r2-root /mnt/data4t/wyh/msahg_runs/sthgcn_sample_materializer_v1r2_provenance-d73f118 \
  --output /mnt/data4t/wyh/msahg_runs/msahg_on_sthgcn_target_admissibility_v1r3-727c82e
