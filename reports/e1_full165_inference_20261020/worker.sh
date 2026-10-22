#!/usr/bin/env bash
set -eu
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
fold="$1"
out=reports/e1_full165_inference_20261020
trap 'code=$?; printf "%s\n" "$code" > "$out/fold$fold.exit"' EXIT
export PYTHONDONTWRITEBYTECODE=1
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
if [ "$fold" = 1 ]; then
  export CUDA_VISIBLE_DEVICES=GPU-bad1ab40-7758-4710-4a2e-5713637a8af6
  export E1_ASSETS_ROOT=/home/linshuijin/DIRECTPP_E1/stage01_20261017
  python_bin=/home/pnxc/Anaconda3/envs/xiaochou/bin/python
else
  export CUDA_VISIBLE_DEVICES=GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417
  export E1_ASSETS_ROOT=/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017
  python_bin=/home/data/linshuijin/.conda/envs/xiaochou/bin/python
fi
"$python_bin" -u -B "$out/infer_full.py" --fold "$fold"
