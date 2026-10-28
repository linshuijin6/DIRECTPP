"""Watchdog for 4-GPU parallel train-side inference on node 3014.

Monitors 4 inference workers (GPU 0..3):
  - GPU 0: Full Fold 1 (914 volumes)
  - GPU 1: OT   Fold 1 (914 volumes)
  - GPU 2: Full Fold 2 (896 volumes)
  - GPU 3: OT   Fold 2 (896 volumes)
Total: 3,620 PET volumes.

Dispatches email notifications on activation, milestones (25%, 50%, 75%),
crashes/failures, and full completion using report_error.send_email.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import socket
import subprocess
import time
from pathlib import Path

from report_error import send_email

BASE_DIR = Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c3_train_side/20261028/epoch165")
LOG_FILE = Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c3_train_side/20261028/epoch165_watchdog.log")

TASKS = {
    "fold1_full": {
        "pattern": r"train_side_inference/run\.py infer.*--model Full.*--outer-fold 1",
        "dir": BASE_DIR / "outer_fold1" / "full",
        "expected_volumes": 914,
        "gpu": 0,
    },
    "fold1_ot": {
        "pattern": r"train_side_inference/run\.py infer.*--model OT.*--outer-fold 1",
        "dir": BASE_DIR / "outer_fold1" / "ot",
        "expected_volumes": 914,
        "gpu": 1,
    },
    "fold2_full": {
        "pattern": r"train_side_inference/run\.py infer.*--model Full.*--outer-fold 2",
        "dir": BASE_DIR / "outer_fold2" / "full",
        "expected_volumes": 896,
        "gpu": 2,
    },
    "fold2_ot": {
        "pattern": r"train_side_inference/run\.py infer.*--model OT.*--outer-fold 2",
        "dir": BASE_DIR / "outer_fold2" / "ot",
        "expected_volumes": 896,
        "gpu": 3,
    },
}

TOTAL_EXPECTED = sum(t["expected_volumes"] for t in TASKS.values())


def log_message(msg: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def notify(subject: str, message: str) -> None:
    hostname = socket.gethostname()
    full_subject = f"{subject} [{hostname}]"
    log_message(f"Sending email notification: {full_subject}")
    try:
        send_email(full_subject, message)
        log_message("Email notification sent successfully.")
    except Exception as e:
        log_message(f"ERROR: send_email failed: {e}")


def get_pid_matching(pattern: str) -> list[int]:
    try:
        out = subprocess.check_output(["pgrep", "-f", pattern]).decode().strip()
        if not out:
            return []
        return [int(line) for line in out.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []


def get_gpu_status() -> str:
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--id=0,1,2,3",
             "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,power.draw",
             "--format=csv,noheader"]
        ).decode(errors="replace").strip()
        return out
    except Exception as e:
        return f"nvidia-smi query failed: {e}"


def count_volumes(task_dir: Path) -> int:
    if not task_dir.exists():
        return 0
    # count generated_{tracer}_{ptid}.nii.gz excluding .tmp files
    files = glob.glob(str(task_dir / "*" / "generated_*.nii.gz"))
    return len(files)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watchdog for 3014 4-GPU inference")
    parser.add_argument("--interval", type=int, default=30, help="Check interval in seconds (default: 30)")
    args = parser.parse_args()

    log_message("Watchdog started for Node 3014 4-GPU parallel train-side inference.")
    gpu_initial = get_gpu_status()
    notify(
        "[WATCHDOG_ACTIVATED] Node 3014 4-GPU Inference Watchdog Active",
        f"Watchdog initialized on {socket.gethostname()} for Stage 4C-4 Train-side PET Inference.\n\n"
        f"Tasks (Total 3,620 volumes across 4 GPUs):\n"
        f"  - GPU 0: Outer-fold 1 Full (914 volumes)\n"
        f"  - GPU 1: Outer-fold 1 OT   (914 volumes)\n"
        f"  - GPU 2: Outer-fold 2 Full (896 volumes)\n"
        f"  - GPU 3: Outer-fold 2 OT   (896 volumes)\n\n"
        f"Output root: {BASE_DIR}\n\n"
        f"Current GPU Status:\n{gpu_initial}\n"
    )

    milestone_flags = {25: False, 50: False, 75: False}
    completed_tasks = set()
    start_time = time.time()

    while True:
        time.sleep(args.interval)
        total_done = 0
        status_lines = []

        all_done = True
        any_failed = False

        for name, info in TASKS.items():
            task_dir = info["dir"]
            pids = get_pid_matching(info["pattern"])
            v_count = count_volumes(task_dir)
            total_done += v_count

            is_complete = (task_dir / "complete.json").exists()
            has_failure = (task_dir / "failure.json").exists()

            if has_failure:
                any_failed = True
                fail_content = ""
                try:
                    with open(task_dir / "failure.json", "r", encoding="utf-8") as f:
                        fail_content = f.read()
                except Exception:
                    pass
                notify(
                    f"[ERROR] Task {name} Failed on Node 3014",
                    f"FAILURE DETECTED in {name}!\n"
                    f"Failure marker: {task_dir / 'failure.json'}\n\n"
                    f"Details:\n{fail_content}\n\n"
                    f"GPU Status:\n{get_gpu_status()}\n"
                )
                log_message(f"FATAL: Task {name} failed! Alert dispatched.")

            if not is_complete:
                all_done = False
                if not pids and not has_failure:
                    # process disappeared without complete.json and without failure.json
                    notify(
                        f"[ERROR] Task {name} Process Vanished on Node 3014",
                        f"ALERT: Worker for {name} is no longer running, but complete.json was not created!\n"
                        f"Output dir: {task_dir}\n"
                        f"Volumes generated so far: {v_count}/{info['expected_volumes']}\n\n"
                        f"GPU Status:\n{get_gpu_status()}\n"
                    )
                    log_message(f"ALERT: Worker for {name} vanished unexpectedly.")
            else:
                if name not in completed_tasks:
                    completed_tasks.add(name)
                    notify(
                        f"[MILESTONE] Task {name} Completed on Node 3014",
                        f"Task {name} has completed all {info['expected_volumes']} volumes!\n"
                        f"Receipt: {task_dir / 'complete.json'}\n"
                        f"Total progress: {total_done}/{TOTAL_EXPECTED} ({total_done/TOTAL_EXPECTED*100:.1f}%)\n"
                    )

            status_lines.append(
                f"{name} (GPU {info['gpu']}): {v_count}/{info['expected_volumes']} vols | "
                f"PIDs: {pids or 'None'} | Complete: {is_complete}"
            )

        pct = (total_done / TOTAL_EXPECTED) * 100
        elapsed_min = (time.time() - start_time) / 60
        log_message(f"Progress: {total_done}/{TOTAL_EXPECTED} ({pct:.1f}%) in {elapsed_min:.1f}m | " + "; ".join(status_lines))

        # Check milestones
        for mark in (25, 50, 75):
            if pct >= mark and not milestone_flags[mark]:
                milestone_flags[mark] = True
                notify(
                    f"[MILESTONE] Node 3014 4-GPU Inference Reached {mark}%",
                    f"Stage 4C-4 inference has reached {mark}% milestone!\n"
                    f"Completed volumes: {total_done}/{TOTAL_EXPECTED} ({pct:.1f}%)\n"
                    f"Elapsed time: {elapsed_min:.1f} minutes\n\n"
                    f"Per-task status:\n" + "\n".join(status_lines) + f"\n\nGPU Status:\n{get_gpu_status()}\n"
                )

        if all_done and len(completed_tasks) == len(TASKS):
            notify(
                "[SUCCESS] Node 3014 All 3,620 Inference Volumes Completed",
                f"Stage 4C-4 4-GPU Parallel Inference Fully Completed!\n"
                f"Total volumes: {total_done}/{TOTAL_EXPECTED} (100%)\n"
                f"Elapsed time: {elapsed_min:.1f} minutes\n\n"
                f"All 4 complete.json receipts verified.\n"
                f"GPU Status:\n{get_gpu_status()}\n"
            )
            log_message("All 4 inference tasks completed successfully. Watchdog exiting gracefully.")
            break

        if any_failed:
            log_message("Exiting watchdog due to task failure.")
            break


if __name__ == "__main__":
    main()
