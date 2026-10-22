#!/usr/bin/env bash
set -eu
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
export CUDA_VISIBLE_DEVICES=GPU-4e00852f-6d7a-af71-10b5-1c59593a6681
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export PYTHONDONTWRITEBYTECODE=1
export E1_ASSETS_ROOT=/home/linshuijin/DIRECTPP_E1/stage01_20261017
export SERVER_SSH_ADDRESS=3002
unset DRY_RUN
queue_state=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage2_launch_20261017/queues/3002_fold1
trap 'code=$?; printf "%s\n" "$code" > "$queue_state/queue.exit"' EXIT
for condition in Full No-Scores; do
  log=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage2_launch_20261017/logs/3002_fold1_"$condition.log"
  /home/pnxc/Anaconda3/envs/xiaochou/bin/python -u -B /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/experiments/e1_clinical_conditioning/run.py train --config /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage01_20261017/config.json --fold 1 --condition "$condition" > "$log" 2>&1 &
  worker=$!
  printf "%s\n" "$worker" > "$queue_state/$condition.pid"
  if wait "$worker"; then code=0; else code=$?; fi
  printf "%s\n" "$code" > "$queue_state/$condition.exit"
  if [ "$code" -ne 0 ]; then exit "$code"; fi
done
