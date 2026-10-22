#!/usr/bin/env bash
set -eu
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
out=reports/e1_full165_inference_20261020
trap 'code=$?; printf "%s\n" "$code" > "$out/summary.exit"' EXIT
export PYTHONDONTWRITEBYTECODE=1
export E1_ASSETS_ROOT=/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017
while [ ! -f "$out/fold1.exit" ] || [ ! -f "$out/fold2.exit" ]; do
  sleep 30
done
for fold in 1 2; do
  code=$(cat "$out/fold$fold.exit")
  if [ "$code" -ne 0 ]; then
    printf 'fold%s failed with exit %s; no automatic retry or partial final summary\n' "$fold" "$code"
    exit "$code"
  fi
done
/home/data/linshuijin/.conda/envs/xiaochou/bin/python -u -B "$out/summarize.py"
