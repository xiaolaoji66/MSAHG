#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${MSAHG_CAUSAL_V1R1_PYTHON_BIN:-python3}
sthgcn_root=${STHGCN_SOURCE_ROOT:?STHGCN_SOURCE_ROOT is required}
output_dir=${MSAHG_CAUSAL_V1R1_TARGET_FREE_OUTPUT:?MSAHG_CAUSAL_V1R1_TARGET_FREE_OUTPUT is required}
registry="$repo_root/reproduction/MSAHG_ON_STHGCN_CAUSAL_MATERIALIZER_V1R1_IMPLEMENTATION_REGISTRY.json"

test -x "$python_bin"
test -d "$sthgcn_root"
test ! -e "$output_dir"

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo_root/reproduction${PYTHONPATH:+:$PYTHONPATH}"

cd "$repo_root"
"$python_bin" -m unittest -v \
  tests.test_msahg_on_sthgcn_causal_materializer_v1r1 \
  tests.test_msahg_on_sthgcn_causal_materializer_v1r1_governance

"$python_bin" \
  reproduction/audit_msahg_on_sthgcn_causal_materializer_v1r1_target_free.py \
  --registry "$registry" \
  --sthgcn-root "$sthgcn_root" \
  --output-dir "$output_dir"

(
  cd "$output_dir"
  sha256sum -c SHA256SUMS
)

"$python_bin" - "$output_dir/target_free_receipt.json" <<'PY'
from __future__ import print_function

import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as handle:
    receipt = json.load(handle)
print("MSAHG_CAUSAL_MATERIALIZER_V1R1_TARGET_FREE={}".format(receipt["decision"]))
print("GATES_PASSED={}/{}".format(
    sum(value is True for value in receipt["gates"].values()),
    len(receipt["gates"]),
))
print("FAILED_GATES={}".format(receipt["failed_gates"]))
print("IMPLEMENTATION_COMMIT={}".format(
    receipt["authorities"]["implementation_commit"]
))
PY
