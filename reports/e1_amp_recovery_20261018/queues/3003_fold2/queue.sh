#!/usr/bin/env bash
set -eu
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
export CUDA_VISIBLE_DEVICES=GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PYTHONDONTWRITEBYTECODE=1
export E1_ASSETS_ROOT=/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017
export SERVER_SSH_ADDRESS=3003
unset DRY_RUN
queue_state=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_amp_recovery_20261018/queues/3003_fold2
printf "%s\n" "$$" > "$queue_state/queue.pid"
trap 'code=$?; printf "%s\n" "$code" > "$queue_state/queue.exit"' EXIT
for condition in Full No-Scores; do
  log=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_amp_recovery_20261018/logs/3003_fold2_"$condition.log"
  /home/data/linshuijin/.conda/envs/xiaochou/bin/python -u -B /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/experiments/e1_clinical_conditioning/run.py train --config /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage01_20261017/config.json --fold 2 --condition "$condition" > "$log" 2>&1 &
  worker=$!
  printf "%s\n" "$worker" > "$queue_state/$condition.pid"
  if wait "$worker"; then code=0; else code=$?; fi
  printf "%s\n" "$code" > "$queue_state/$condition.exit"
  if [ "$code" -ne 0 ]; then exit "$code"; fi
done
