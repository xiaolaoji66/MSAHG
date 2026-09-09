#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 MSAHG_REPO STHGCN_REPO OUTPUT_JSON" >&2
  exit 64
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd -P)
msahg_repo=$(CDPATH= cd -- "$1" && pwd -P)
sthgcn_repo=$(CDPATH= cd -- "$2" && pwd -P)
output=$3

python_bin=${MSAHG_STHGCN_AUDIT_PYTHON_BIN:-python3}

test "$msahg_repo" = "$repo_root"
git -C "$msahg_repo" rev-parse --git-dir >/dev/null
git -C "$sthgcn_repo" rev-parse --git-dir >/dev/null
test ! -e "$output"

cd "$repo_root"
"$python_bin" -m unittest -v tests.test_sthgcn_sample_protocol_r1
"$python_bin" reproduction/audit_sthgcn_sample_protocol_r1.py \
  --msahg-repo "$msahg_repo" \
  --sthgcn-repo "$sthgcn_repo" \
  --output "$output"

sha256sum "$output"
