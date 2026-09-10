#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${STHGCN_V1R1_PYTHON_BIN:-python3}
sthgcn_root=${STHGCN_SOURCE_ROOT:?STHGCN_SOURCE_ROOT is required}
v1_output=${STHGCN_V1_OUTPUT_ROOT:?STHGCN_V1_OUTPUT_ROOT is required}
output=${STHGCN_V1R1_OUTPUT_ROOT:?STHGCN_V1R1_OUTPUT_ROOT is required}
audit_output=${STHGCN_V1R1_AUDIT_OUTPUT:?STHGCN_V1R1_AUDIT_OUTPUT is required}
registry="$repo_root/reproduction/STHGCN_SAMPLE_MATERIALIZER_V1R1_PROVENANCE_REGISTRY.json"
export PYTHONDONTWRITEBYTECODE=1

"$python_bin" "$repo_root/reproduction/sthgcn_sample_materializer_v1r1_provenance.py" \
  --sthgcn-root "$sthgcn_root" \
  --v1-output-root "$v1_output" \
  --registry "$registry" \
  --output-root "$output"

"$python_bin" "$repo_root/reproduction/audit_sthgcn_sample_materializer_v1r1_provenance.py" \
  --output-root "$output" \
  --v1-output-root "$v1_output" \
  --audit-output "$audit_output"

(
  cd "$output"
  sha256sum -c SHA256SUMS
)

echo "STHGCN_SAMPLE_MATERIALIZER_V1R1_PROVENANCE=PASS"
echo "OUTPUT=$output"
echo "INDEPENDENT_AUDIT=$audit_output"
