#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
output_root=${1:?usage: reproduce_official_sample_r0.sh OUTPUT_DIRECTORY}
python_bin=${MSAHG_PYTHON_BIN:-python}
device_id=${MSAHG_DEVICE_ID:-0}
num_epochs=${MSAHG_NUM_EPOCHS:-100}

test ! -e "$output_root"
mkdir -p "$output_root"
run_root="$output_root/source_exact_workspace"
result_root="$output_root/result"
mkdir -p "$run_root/datasets" "$result_root"

(
  cd "$repo_root"
  sha256sum -c reproduction/UPSTREAM_SHA256SUMS
)

for source_name in \
  adaptive_par.py \
  build_graph.py \
  dataset.py \
  metrics.py \
  model_devide.py \
  run.py \
  train_nash.py \
  utils.py
do
  cp "$repo_root/$source_name" "$run_root/$source_name"
done

unzip -q "$repo_root/datasets/sample.zip" -d "$run_root/datasets"

export DGLBACKEND=pytorch

"$python_bin" - <<'PY' > "$output_root/environment.txt"
import platform
import cvxpy
import dgl
import joblib
import numpy
import pandas
import scipy
import torch
import tqdm
import yaml

print("python={}".format(platform.python_version()))
for module in (torch, numpy, scipy, pandas, yaml, tqdm, joblib, dgl, cvxpy):
    print("{}={}".format(module.__name__, getattr(module, "__version__", "unknown")))
print("cuda_available={}".format(torch.cuda.is_available()))
print("cuda_version={}".format(torch.version.cuda))
if torch.cuda.is_available():
    print("cuda_device={}".format(torch.cuda.get_device_name(0)))
PY

export PYTHONHASHSEED=2023
export CUDA_DEVICE_ORDER=PCI_BUS_ID

(
  cd "$run_root"
  "$python_bin" run.py \
    --dataset NYC \
    --deviceID "$device_id" \
    --seed 2023 \
    --num_epochs "$num_epochs" \
    --batch_size 200 \
    --finetune_batch_size 20 \
    --lr 0.001 \
    --divide_epoch 20 \
    --accu_loss 20 \
    --lrdecay 0.75 \
    --save_dir "$result_root" \
    2>&1 | tee "$output_root/console.log"
)

(
  cd "$output_root"
  find . -type f -not -name SHA256SUMS -print0 \
    | sort -z \
    | xargs -0 sha256sum > SHA256SUMS
)

printf 'MSAHG_OFFICIAL_SAMPLE_R0_COMPLETE=%s\n' "$output_root"
