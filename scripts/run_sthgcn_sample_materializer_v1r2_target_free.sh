#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${STHGCN_V1R2_PYTHON_BIN:-python3}
output=${STHGCN_V1R2_TARGET_FREE_OUTPUT:?STHGCN_V1R2_TARGET_FREE_OUTPUT is required}
registry="$repo_root/reproduction/STHGCN_SAMPLE_MATERIALIZER_V1R2_PROVENANCE_REGISTRY.json"
export PYTHONDONTWRITEBYTECODE=1

"$python_bin" -m unittest -v \
  tests.test_sthgcn_sample_materializer_v1r2_provenance \
  tests.test_sthgcn_sample_materializer_v1r2_governance

"$python_bin" "$repo_root/reproduction/audit_sthgcn_sample_materializer_v1r2_target_free.py" \
  --registry "$registry" \
  --output-dir "$output"

(
  cd "$output"
  sha256sum -c SHA256SUMS
)

echo "STHGCN_SAMPLE_MATERIALIZER_V1R2_TARGET_FREE=PASS"
echo "OUTPUT=$output"
