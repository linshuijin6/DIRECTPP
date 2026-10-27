#!/usr/bin/env bash
set -euo pipefail

project_root=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
python_bin=/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python
config=reports/clinical_regression_unet_task_a_20261027_node3014_parallel/config.json
assets=/mnt/datas230/users/linshuijin/DIRECTPP_clinical_regression_unet/task_a_20261027_node3014_parallel
runtime="$assets/runtime"

cd "$project_root"
mkdir -p "$runtime"
export CUDA_DEVICE_ORDER=PCI_BUS_ID

nvidia-smi -i 1,3,4,5,6 \
  --query-gpu=timestamp,index,uuid,name,memory.total,memory.used,memory.free,utilization.gpu \
  --format=csv,noheader,nounits > "$runtime/gpu_before.csv"

"$python_bin" experiments/clinical_regression_unet/run.py \
  check-config --config "$config" --no-write
CUDA_VISIBLE_DEVICES=1 "$python_bin" experiments/clinical_regression_unet/run.py \
  smoke-test --cuda --full-sample --config "$config"

CUDA_VISIBLE_DEVICES=1 "$python_bin" -u experiments/clinical_regression_unet/run.py \
  train --config "$config" --fold 1 > "$runtime/fold1_train.log" 2>&1 &
fold1_pid=$!
CUDA_VISIBLE_DEVICES=3 "$python_bin" -u experiments/clinical_regression_unet/run.py \
  train --config "$config" --fold 2 > "$runtime/fold2_train.log" 2>&1 &
fold2_pid=$!
printf 'fold1_pid=%s\nfold2_pid=%s\n' "$fold1_pid" "$fold2_pid" > "$runtime/training_pids.txt"

set +e
wait "$fold1_pid"
fold1_rc=$?
wait "$fold2_pid"
fold2_rc=$?
set -e
printf 'fold1_rc=%s\nfold2_rc=%s\n' "$fold1_rc" "$fold2_rc" > "$runtime/training_exit_codes.txt"
if (( fold1_rc != 0 || fold2_rc != 0 )); then
  echo "Parallel training failed; inference was not started" >&2
  exit 1
fi

CUDA_VISIBLE_DEVICES=1 "$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 1 --epoch 165 > "$runtime/fold1_epoch165_infer.log" 2>&1 &
infer_1_165_pid=$!
CUDA_VISIBLE_DEVICES=3 "$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 2 --epoch 165 > "$runtime/fold2_epoch165_infer.log" 2>&1 &
infer_2_165_pid=$!
CUDA_VISIBLE_DEVICES=4 "$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 1 --epoch 200 > "$runtime/fold1_epoch200_infer.log" 2>&1 &
infer_1_200_pid=$!
CUDA_VISIBLE_DEVICES=5 "$python_bin" -u experiments/clinical_regression_unet/run.py \
  infer --config "$config" --fold 2 --epoch 200 > "$runtime/fold2_epoch200_infer.log" 2>&1 &
infer_2_200_pid=$!
printf 'fold1_epoch165_pid=%s\nfold2_epoch165_pid=%s\nfold1_epoch200_pid=%s\nfold2_epoch200_pid=%s\n' \
  "$infer_1_165_pid" "$infer_2_165_pid" "$infer_1_200_pid" "$infer_2_200_pid" \
  > "$runtime/inference_pids.txt"

set +e
wait "$infer_1_165_pid"
infer_1_165_rc=$?
wait "$infer_2_165_pid"
infer_2_165_rc=$?
wait "$infer_1_200_pid"
infer_1_200_rc=$?
wait "$infer_2_200_pid"
infer_2_200_rc=$?
set -e
printf 'fold1_epoch165_rc=%s\nfold2_epoch165_rc=%s\nfold1_epoch200_rc=%s\nfold2_epoch200_rc=%s\n' \
  "$infer_1_165_rc" "$infer_2_165_rc" "$infer_1_200_rc" "$infer_2_200_rc" \
  > "$runtime/inference_exit_codes.txt"
if (( infer_1_165_rc != 0 || infer_2_165_rc != 0 || infer_1_200_rc != 0 || infer_2_200_rc != 0 )); then
  echo "Parallel inference failed; summary was not started" >&2
  exit 1
fi

"$python_bin" -u experiments/clinical_regression_unet/run.py \
  summarize --config "$config" > "$runtime/summarize.log" 2>&1
printf '0\n' > "$runtime/pipeline.exit"
