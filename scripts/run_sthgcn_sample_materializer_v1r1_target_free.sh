#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${STHGCN_V1R1_PYTHON_BIN:-python3}
output=${STHGCN_V1R1_TARGET_FREE_OUTPUT:?STHGCN_V1R1_TARGET_FREE_OUTPUT is required}
registry="$repo_root/reproduction/STHGCN_SAMPLE_MATERIALIZER_V1R1_PROVENANCE_REGISTRY.json"
export PYTHONDONTWRITEBYTECODE=1

"$python_bin" -m unittest -v \
  tests.test_sthgcn_sample_materializer_v1r1_provenance \
  tests.test_sthgcn_sample_materializer_v1r1_governance

"$python_bin" "$repo_root/reproduction/audit_sthgcn_sample_materializer_v1r1_target_free.py" \
  --registry "$registry" \
  --output-dir "$output"

(
  cd "$output"
  sha256sum -c SHA256SUMS
)

echo "STHGCN_SAMPLE_MATERIALIZER_V1R1_TARGET_FREE=PASS"
echo "OUTPUT=$output"
