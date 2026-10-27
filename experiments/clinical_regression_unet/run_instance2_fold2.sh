#!/usr/bin/env bash
set -euo pipefail

cd /root/autodl-tmp/DIRECTPP_task_a

python_bin=/root/miniconda3/bin/python
config=reports/clinical_regression_unet_task_a_20261027_instance1/config.json

export CUDA_VISIBLE_DEVICES=0

"$python_bin" experiments/clinical_regression_unet/run.py \
  check-config --config "$config" --no-write
"$python_bin" -u experiments/clinical_regression_unet/run.py \
  train --config "$config" --fold 2
"$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 2 --epoch 165
"$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 2 --epoch 200
