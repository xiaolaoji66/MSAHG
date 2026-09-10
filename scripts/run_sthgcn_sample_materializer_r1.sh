#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${STHGCN_MATERIALIZER_PYTHON_BIN:-python3}
sthgcn_root=${STHGCN_SOURCE_ROOT:?STHGCN_SOURCE_ROOT is required}
output_root=${STHGCN_MATERIALIZER_OUTPUT_ROOT:?STHGCN_MATERIALIZER_OUTPUT_ROOT is required}
registry="$repo_root/reproduction/STHGCN_SAMPLE_MATERIALIZER_R1_REGISTRY.json"

"$python_bin" "$repo_root/reproduction/sthgcn_sample_materializer_r1.py" \
  --sthgcn-root "$sthgcn_root" \
  --registry "$registry" \
  --output-root "$output_root" \
  --dataset all

"$python_bin" "$repo_root/reproduction/audit_sthgcn_sample_materializer_r1.py" \
  --output-root "$output_root" \
  --audit-output "$output_root/independent_audit.json"

(
  cd "$output_root"
  shasum -a 256 independent_audit.json > INDEPENDENT_AUDIT_SHA256SUMS
)

echo "STHGCN_SAMPLE_MATERIALIZER_R1=PASS"
echo "OUTPUT_ROOT=$output_root"
