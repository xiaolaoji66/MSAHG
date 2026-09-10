#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${STHGCN_V1R3_PYTHON_BIN:-python3}
v1r2_output=${STHGCN_V1R2_PRESERVED_OUTPUT_ROOT:?STHGCN_V1R2_PRESERVED_OUTPUT_ROOT is required}
v1_output=${STHGCN_V1_OUTPUT_ROOT:?STHGCN_V1_OUTPUT_ROOT is required}
audit_output=${STHGCN_V1R3_AUDIT_OUTPUT:?STHGCN_V1R3_AUDIT_OUTPUT is required}
registry="$repo_root/reproduction/STHGCN_SAMPLE_MATERIALIZER_V1R3_AUDIT_REPAIR_REGISTRY.json"
export PYTHONDONTWRITEBYTECODE=1

"$python_bin" "$repo_root/reproduction/audit_sthgcn_sample_materializer_v1r3_provenance.py" \
  --registry "$registry" \
  --output-root "$v1r2_output" \
  --v1-output-root "$v1_output" \
  --audit-output "$audit_output"

echo "STHGCN_SAMPLE_MATERIALIZER_V1R3_PROVENANCE_AUDIT=PASS"
echo "AUDIT_OUTPUT=$audit_output"
