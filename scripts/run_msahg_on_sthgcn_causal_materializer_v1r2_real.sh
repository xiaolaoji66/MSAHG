#!/usr/bin/env bash
set -euo pipefail
umask 022

audit_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${MSAHG_CAUSAL_REAL_PYTHON_BIN:-/usr/miniconda3/envs/gugen_mamba/bin/python}
materializer_root=/mnt/data4t/wyh/MSAHG-sthgcn-causal-materializer-v1r1-1f6fce9
sthgcn_root=/mnt/data4t/wyh/sthgcn-source-27b59584-provenance-v1r1
v1_root=/mnt/data4t/wyh/msahg_runs/sthgcn_sample_materializer_r1_replay-a53acb3-v1r1-input-pandas223
v1r2_root=/mnt/data4t/wyh/msahg_runs/sthgcn_sample_materializer_v1r2_provenance-d73f118
output_root=/mnt/data4t/wyh/msahg_runs/msahg_on_sthgcn_causal_materializer_v1r2_real-515c72a

registry="$audit_root/reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_REGISTRY.json"
runtime_authority="$audit_root/reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R2_REAL_RUNTIME_AUTHORITY.json"
materializer_registry="$materializer_root/reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_IMPLEMENTATION_REGISTRY.json"
materializer="$materializer_root/reproduction/msahg_on_sthgcn_causal_materializer_v1r1.py"
auditor="$audit_root/reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r2_real.py"
authority_sha=8eca4f83de89dab57a4f8dc4e52e55913c627b6b7ce82a47e5f1ba9718d88254

test -x "$python_bin"
test -d "$materializer_root"
test -d "$sthgcn_root"
test -d "$v1_root"
test -d "$v1r2_root"
test ! -e "$output_root"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$audit_root/reproduction${PYTHONPATH:+:$PYTHONPATH}"

cd "$audit_root"
"$python_bin" -m unittest -v \
  tests.test_msahg_on_sthgcn_causal_materializer_v1r2_real \
  tests.test_msahg_on_sthgcn_causal_materializer_v1r2_real_governance

mkdir -p "$output_root"
exec > >(tee "$output_root/execution.log") 2>&1

for dataset in nyc tky; do
  "$python_bin" "$materializer" \
    --registry "$materializer_registry" \
    --runtime-authority "$runtime_authority" \
    --runtime-authority-sha256 "$authority_sha" \
    --dataset "$dataset" \
    --sample-csv "$v1_root/$dataset/sample.csv" \
    --label-encoding "$v1_root/$dataset/label_encoding.json" \
    --provenance-sidecar "$v1r2_root/$dataset/record_split_provenance.csv" \
    --output-dir "$output_root/$dataset"
done

"$python_bin" "$auditor" \
  --registry "$registry" \
  --runtime-authority "$runtime_authority" \
  --materializer-root "$materializer_root" \
  --sthgcn-root "$sthgcn_root" \
  --v1-root "$v1_root" \
  --v1r2-root "$v1r2_root" \
  --materialization-root "$output_root" \
  --output "$output_root/independent_audit.json"

for dataset in nyc tky; do
  (
    cd "$output_root/$dataset"
    sha256sum -c SHA256SUMS
  )
done

{
  sha256sum "$output_root/independent_audit.json"
  sha256sum "$output_root/nyc/SHA256SUMS"
  sha256sum "$output_root/tky/SHA256SUMS"
} | sed "s#  $output_root/#  #" > "$output_root/ROOT_SHA256SUMS"

"$python_bin" - "$output_root/independent_audit.json" <<'PY'
from __future__ import print_function

import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    receipt = json.load(handle)
print("MSAHG_CAUSAL_REAL_V1R2_DECISION={}".format(receipt["decision"]))
print("PROTOCOL_PASS={}".format(receipt["protocol_pass"]))
print("SUPPORT_PASS={}".format(receipt["support_pass"]))
print("GATES_PASSED={}/{}".format(
    sum(value is True for value in receipt["gates"].values()),
    len(receipt["gates"]),
))
for dataset in ("nyc", "tky"):
    item = receipt["datasets"][dataset]
    print("{}: ROWS={} TRAIN={} TARGETS={} SUPPORT_PASS={}".format(
        dataset.upper(),
        item["rows"],
        item["training_rows"],
        item["eligible_targets"],
        item["support_floor_pass"],
    ))
PY

printf "OUTPUT_ROOT=%s\n" "$output_root"
