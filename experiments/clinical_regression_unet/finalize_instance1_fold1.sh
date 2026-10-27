#!/usr/bin/env bash
set -euo pipefail

cd /root/autodl-tmp/DIRECTPP_task_a

python_bin=/root/miniconda3/bin/python
config=reports/clinical_regression_unet_task_a_20261027_instance1/config.json
assets=/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027
fold1_complete="$assets/formal/fold1/complete.json"

export CUDA_VISIBLE_DEVICES=0

while [[ ! -f "$fold1_complete" ]]; do
  mapfile -t fold1_pids < <(pgrep -f 'clinical_regression_unet/run.py train.*--fold 1' || true)
  if (( ${#fold1_pids[@]} != 1 )); then
    echo "Expected one active fold 1 trainer before completion; found ${#fold1_pids[@]}" >&2
    exit 1
  fi
  sleep 60
done

"$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 1 --epoch 165
"$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 1 --epoch 200

while [[ ! -f "$assets/oof/epoch165/fold2/complete.json" || \
         ! -f "$assets/oof/epoch200/fold2/complete.json" ]]; do
  sleep 60
done

"$python_bin" -u experiments/clinical_regression_unet/run.py \
  summarize --config "$config"
