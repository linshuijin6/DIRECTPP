#!/usr/bin/env bash
# Tabular MLP ablation lightweight transfer from AutoDL instance 1 & 2.
#
# Transfers checkpoints + receipts + audit logs + OOF summary/metrics while
# excluding the 81 GB of generated .nii.gz predictions (5,926 files).
# All remote access is read-only; nothing on the instances is modified.

set -euo pipefail

REPO_ROOT="/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
TARGET_STORAGE="/mnt/datas230/users/linshuijin/DIRECTPP_tabular_mlp/20261028_v3"
LOCAL_REPORT_REL="reports/tabular_mlp_20261028_v3"
RESULTS_REL="results/tabular_mlp_20261028_v3"

SSH_PORT_1=36733
REMOTE_1="root@connect.weste.seetacloud.com"

SSH_PORT_2=40818
REMOTE_2="root@connect.westb.seetacloud.com"

R_ASSETS="/autodl-fs/data/DIRECTPP_tabular_mlp/20261028_v3"
R_REPORT="/root/autodl-tmp/DIRECTPP_task_a/reports/tabular_mlp_20261028_v3"

cd "$REPO_ROOT"

echo "=== step 1: prepare local directories ==="
mkdir -p "$TARGET_STORAGE/formal" "$TARGET_STORAGE/runtime"
mkdir -p "$LOCAL_REPORT_REL/oof_summary" "$LOCAL_REPORT_REL/oof" "$RESULTS_REL"

echo "=== step 2: formal/ full assets (~5.0 GB: 42 checkpoints + recovery + traces + receipts) ==="
rsync -avP --exclude="*.nii.gz" -e "ssh -p $SSH_PORT_1" \
  "$REMOTE_1:$R_ASSETS/formal/" "$TARGET_STORAGE/formal/"

echo "=== step 3: runtime/ audit logs (~4.4 MB) ==="
rsync -avP --exclude="*.nii.gz" -e "ssh -p $SSH_PORT_1" \
  "$REMOTE_1:$R_ASSETS/runtime/" "$TARGET_STORAGE/runtime/"

echo "=== step 4: conditions.pt (~3.7 MB) ==="
rsync -avP -e "ssh -p $SSH_PORT_1" \
  "$REMOTE_1:$R_ASSETS/conditions.pt" "$TARGET_STORAGE/conditions.pt"

echo "=== step 5: top-level report configs & receipts from Instance 1 (~4.5 MB) ==="
rsync -avP --exclude="oof_summary" --exclude="*.nii.gz" -e "ssh -p $SSH_PORT_1" \
  "$REMOTE_1:$R_REPORT/" "$LOCAL_REPORT_REL/"

echo "=== step 6: instance 2 preflight receipt (~2 KB) ==="
rsync -avP -e "ssh -p $SSH_PORT_2" \
  "$REMOTE_2:$R_REPORT/preflight_fold2.json" "$LOCAL_REPORT_REL/preflight_fold2.json"

echo "=== step 7: oof_summary/ into git report dir (~2 MB) ==="
rsync -avP --exclude="*.nii.gz" -e "ssh -p $SSH_PORT_1" \
  "$REMOTE_1:$R_REPORT/oof_summary/" "$LOCAL_REPORT_REL/oof_summary/"

echo "=== step 8: oof/ receipts & metrics only (exclude 5,926 .nii.gz, ~6 MB) ==="
rsync -avP --include="*/" --include="metrics.csv" --include="complete.json" --exclude="*" \
  -e "ssh -p $SSH_PORT_1" "$REMOTE_1:$R_ASSETS/oof/" "$LOCAL_REPORT_REL/oof/"

echo "=== step 9: workspace symlinks into /mnt/datas230 ==="
ln -sfn "$TARGET_STORAGE/formal"  "$RESULTS_REL/formal"
ln -sfn "$TARGET_STORAGE/runtime" "$RESULTS_REL/runtime"

echo "=== transfer completed successfully ==="
du -sh "$TARGET_STORAGE/formal" "$TARGET_STORAGE/runtime" "$LOCAL_REPORT_REL/oof_summary" "$LOCAL_REPORT_REL/oof"
ls -l "$RESULTS_REL"
