#!/usr/bin/env bash

set -u

repo=/root/autodl-tmp/DIRECTPP
report="$repo/reports/tracer_only_control_20261022"
config="$report/config.json"
python_bin=/root/miniconda3/bin/python
launcher="$repo/experiments/tracer_only_control/run.py"
lock="$report/queue.lock"

mkdir "$lock" || {
  echo "Refusing duplicate launch: $lock already exists" >&2
  exit 90
}

cd "$repo" || exit 91
export CUDA_VISIBLE_DEVICES=GPU-8fe130cf-e42b-59a3-6fc9-f43fe4160e0c

echo "$(date -Is) fold1 start"
"$python_bin" -u "$launcher" train --config "$config" --fold 1 \
  >"$report/fold1_train.log" 2>&1
fold1_status=$?
printf '%s\n' "$fold1_status" >"$report/fold1.exit"
echo "$(date -Is) fold1 exit=$fold1_status"
if [ "$fold1_status" -ne 0 ]; then
  printf '%s\n' "$fold1_status" >"$report/queue.exit"
  exit "$fold1_status"
fi

echo "$(date -Is) fold2 start"
"$python_bin" -u "$launcher" train --config "$config" --fold 2 \
  >"$report/fold2_train.log" 2>&1
fold2_status=$?
printf '%s\n' "$fold2_status" >"$report/fold2.exit"
echo "$(date -Is) fold2 exit=$fold2_status"
printf '%s\n' "$fold2_status" >"$report/queue.exit"
exit "$fold2_status"
