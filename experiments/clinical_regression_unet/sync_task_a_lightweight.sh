#!/usr/bin/env bash
# Task A (clinical_regression_unet) lightweight transfer from AutoDL instance 1.
#
# Transfers checkpoints + receipts + audit logs + OOF summary/metrics while
# excluding the 81 GB of generated .nii.gz predictions (5,926 files).
# All remote access is read-only; nothing on the instances is modified.
#
# Usage:
#   sync_task_a_lightweight.sh [snapshot|sync|all]     (default: all)
#
#   snapshot : step 0 only -- resolve first held-out subjects locally,
#              capture a remote terminal snapshot + remote cache-file hashes.
#   sync     : rsync steps 1-5 only.
#   all      : snapshot then sync.

set -euo pipefail

REPO_ROOT="/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
PYBIN="/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python"
TARGET_STORAGE="/mnt/datas230/users/linshuijin/DIRECTPP_clinical_regression_unet/task_a_20261027"
LOCAL_REPORT_REL="reports/clinical_regression_unet_task_a_20261027_instance1"
RESULTS_REL="results/clinical_regression_unet_task_a_20261027"
SSH_PORT=36733
REMOTE="root@connect.weste.seetacloud.com"
R_ASSETS="/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027"
R_CACHE="/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3"
R_REPORT="/root/autodl-tmp/DIRECTPP_task_a/reports/clinical_regression_unet_task_a_20261027_instance1"

cd "$REPO_ROOT"
STAGE="${1:-all}"

json_field() {  # json_field '<json>' <key>
  "$PYBIN" -c 'import json,sys; print(json.loads(sys.argv[1])[sys.argv[2]])' "$1" "$2"
}

snapshot() {
  mkdir -p "$TARGET_STORAGE"

  echo "=== step 0a: resolve first held-out subject of each fold (local data) ==="
  INFO_F1="$($PYBIN experiments/clinical_regression_unet/verify_task_a_preservation.py --print-heldout-first --fold 1)"
  INFO_F2="$($PYBIN experiments/clinical_regression_unet/verify_task_a_preservation.py --print-heldout-first --fold 2)"
  echo "fold1: $INFO_F1"
  echo "fold2: $INFO_F2"
  CACHE_F1="$(json_field "$INFO_F1" cache_file)"
  CACHE_F2="$(json_field "$INFO_F2" cache_file)"

  echo "=== step 0b: remote terminal snapshot (read-only) ==="
  SNAP_TXT="$TARGET_STORAGE/remote_terminal_snapshot_$(date +%Y%m%d_%H%M%S).txt"
  ssh -p "$SSH_PORT" "$REMOTE" "
    set -e
    A=$R_ASSETS; C=$R_CACHE; R=$R_REPORT
    hostname; date
    echo '--- formal (recursive listing) ---';  ls -laR \$A/formal
    echo '--- runtime (recursive listing) ---'; ls -laR \$A/runtime
    echo '--- oof non-nii.gz files ---'; find \$A/oof -type f ! -name '*.nii.gz' | sort
    echo '--- oof_summary files ---'; ls -la \$R/oof_summary
    echo '--- oof_summary hashes ---'; sha256sum \$R/oof_summary/*
    echo '--- checkpoint receipt hashes (both folds) ---'; sha256sum \$A/formal/fold1/*.json \$A/formal/fold2/*.json
    echo '--- oof receipt hashes ---'; sha256sum \$A/oof/epoch*/fold*/*.json
    echo '--- remote cache subject hashes ---'; sha256sum \$C/$CACHE_F1 \$C/$CACHE_F2
  " > "$SNAP_TXT"
  echo "snapshot written: $SNAP_TXT"

  echo "=== step 0c: machine-readable remote cache hashes ==="
  CACHE_HASHES="$(ssh -p "$SSH_PORT" "$REMOTE" "sha256sum $R_CACHE/$CACHE_F1 $R_CACHE/$CACHE_F2")"
  "$PYBIN" - "$INFO_F1" "$INFO_F2" "$CACHE_HASHES" "$SNAP_TXT" <<'PYEOF'
import json, sys, time
from pathlib import Path

target = Path("/mnt/datas230/users/linshuijin/DIRECTPP_clinical_regression_unet/task_a_20261027")
f1, f2 = json.loads(sys.argv[1]), json.loads(sys.argv[2])
hashes = {}
for line in sys.argv[3].strip().splitlines():
    digest, path = line.split()
    hashes[path.rsplit("/", 1)[1]] = digest
payload = {
    "captured_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    "instance1_ssh": "ssh -p 36733 root@connect.weste.seetacloud.com",
    "remote_cache_dir": "/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3",
    "snapshot_text": sys.argv[4],
    "subjects": {
        "1": {**f1, "remote_cache_sha256": hashes[f1["cache_file"]]},
        "2": {**f2, "remote_cache_sha256": hashes[f2["cache_file"]]},
    },
}
(target / "remote_cache_subject_hashes.json").write_text(
    json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
)
print(f"remote cache hashes written: {target / 'remote_cache_subject_hashes.json'}")
PYEOF
}

sync_assets() {
  echo "=== step 1: formal/ full assets (~1.4 GB: 21 checkpoints per fold + recovery + traces + receipts) ==="
  rsync -avP --exclude="*.nii.gz" -e "ssh -p $SSH_PORT" \
    "$REMOTE:$R_ASSETS/formal/" "$TARGET_STORAGE/formal/"

  echo "=== step 2: runtime/ audit logs (~4.2 MB) ==="
  rsync -avP --exclude="*.nii.gz" -e "ssh -p $SSH_PORT" \
    "$REMOTE:$R_ASSETS/runtime/" "$TARGET_STORAGE/runtime/"

  echo "=== step 3: oof_summary/ into git report dir (~2.1 MB) ==="
  mkdir -p "$LOCAL_REPORT_REL/oof_summary"
  rsync -avP --exclude="*.nii.gz" -e "ssh -p $SSH_PORT" \
    "$REMOTE:$R_REPORT/oof_summary/" "$LOCAL_REPORT_REL/oof_summary/"

  echo "=== step 4: oof/ receipts only (metrics.csv + complete.json; 5,926 .nii.gz excluded) ==="
  mkdir -p "$LOCAL_REPORT_REL/oof"
  rsync -avP --include="*/" --include="metrics.csv" --include="complete.json" --exclude="*" \
    -e "ssh -p $SSH_PORT" "$REMOTE:$R_ASSETS/oof/" "$LOCAL_REPORT_REL/oof/"

  echo "=== step 5: workspace symlinks into /mnt/datas230 ==="
  mkdir -p "$RESULTS_REL"
  ln -sfn "$TARGET_STORAGE/formal"  "$RESULTS_REL/formal"
  ln -sfn "$TARGET_STORAGE/runtime" "$RESULTS_REL/runtime"

  echo "=== transfer summary ==="
  du -sh "$TARGET_STORAGE/formal" "$TARGET_STORAGE/runtime" "$LOCAL_REPORT_REL/oof_summary" "$LOCAL_REPORT_REL/oof"
  ls -l "$RESULTS_REL"
}

case "$STAGE" in
  snapshot) snapshot ;;
  sync)    sync_assets ;;
  all)     snapshot; sync_assets ;;
  *) echo "usage: $0 [snapshot|sync|all]" >&2; exit 2 ;;
esac
