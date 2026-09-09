#!/usr/bin/env bash
set -euo pipefail

repo=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
python_bin=${MSAHG_R1_PYTHON_BIN:-python}
output=${1:?usage: run_msahg_paper_math_r1_target_free.sh OUTPUT_DIR}

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$repo/reproduction${PYTHONPATH:+:$PYTHONPATH}"

"$python_bin" -m unittest -v tests.test_msahg_paper_math_r1
"$python_bin" "$repo/reproduction/audit_msahg_paper_math_r1.py" \
  --repo "$repo" \
  --output "$output"

(
  cd "$output"
  sha256sum -c SHA256SUMS
)
