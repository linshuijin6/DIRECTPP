"""Non-invasive watchdog for Task A (clinical_regression_unet) training & inference.

Monitors running processes, log updates, and completion artifacts.
On error or crash, dispatches email notification using report_error.send_email.
On milestone or final completion, also sends notification.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Optional

from report_error import send_email


ASSETS_DIR = Path("/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027")
RUNTIME_DIR = ASSETS_DIR / "runtime"


def get_pids_matching(pattern: str) -> list[int]:
    """Return list of active process IDs matching pattern."""
    try:
        out = subprocess.check_output(["pgrep", "-f", pattern]).decode().strip()
        if not out:
            return []
        return [int(line) for line in out.splitlines() if line.strip()]
    except subprocess.CalledProcessError:
        return []


def get_log_tail(log_path: Path, n_lines: int = 50) -> str:
    """Return last N lines of log file."""
    if not log_path.exists():
        return f"Log file {log_path} does not exist."
    try:
        out = subprocess.check_output(["tail", f"-n{n_lines}", str(log_path)]).decode(
            errors="replace"
        )
        return out.strip()
    except Exception as e:
        return f"Failed to read log tail: {e}"


def get_nvidia_smi() -> str:
    """Get compact nvidia-smi summary."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=index,name,temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"]
        ).decode(errors="replace").strip()
        return out
    except Exception as e:
        return f"nvidia-smi error: {e}"


def notify(subject: str, message: str) -> None:
    hostname = socket.gethostname()
    full_subject = f"{subject} [{hostname}]"
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Sending email: {full_subject}")
    try:
        send_email(full_subject, message)
        print("Email sent successfully.")
    except Exception as e:
        print(f"ERROR: send_email failed: {e}")


def monitor_instance_1(poll_interval: int = 60, max_idle_seconds: int = 1800) -> None:
    log_path = RUNTIME_DIR / "formal_pipeline.log"
    fold1_train_complete = ASSETS_DIR / "formal/fold1/complete.json"
    fold1_infer165_complete = ASSETS_DIR / "oof/epoch165/fold1/complete.json"
    fold1_infer200_complete = ASSETS_DIR / "oof/epoch200/fold1/complete.json"
    overall_complete = ASSETS_DIR / "completion.json"

    print(f"Watchdog started for Instance 1 on {socket.gethostname()}")
    notify(
        "[WATCHDOG_ACTIVATED] Task A Instance 1 Watchdog Active",
        f"Watchdog started on Instance 1 ({socket.gethostname()}).\n"
        f"Monitoring Fold 1 training, inference (e165/e200), and final summarize.\n"
        f"Poll interval: {poll_interval}s, max idle timeout: {max_idle_seconds}s.\n"
        f"GPU Status: {get_nvidia_smi()}"
    )

    notified_milestones = set()
    last_log_mtime = log_path.stat().st_mtime if log_path.exists() else time.time()
    last_log_size = log_path.stat().st_size if log_path.exists() else 0

    while True:
        time.sleep(poll_interval)
        now = time.time()

        # Check milestones
        if fold1_train_complete.exists() and "fold1_train" not in notified_milestones:
            notified_milestones.add("fold1_train")
            notify(
                "[MILESTONE] Instance 1 Fold 1 Training Finished",
                f"Fold 1 training successfully completed!\n"
                f"Receipt: {fold1_train_complete}\n"
                f"Now waiting for/running Fold 1 inference e165 & e200.\n"
                f"GPU Status: {get_nvidia_smi()}"
            )

        if fold1_infer165_complete.exists() and "fold1_infer165" not in notified_milestones:
            notified_milestones.add("fold1_infer165")
            notify(
                "[MILESTONE] Instance 1 Fold 1 Epoch 165 Inference Done",
                f"Fold 1 Epoch 165 inference completed!\nReceipt: {fold1_infer165_complete}"
            )

        if fold1_infer200_complete.exists() and "fold1_infer200" not in notified_milestones:
            notified_milestones.add("fold1_infer200")
            notify(
                "[MILESTONE] Instance 1 Fold 1 Epoch 200 Inference Done",
                f"Fold 1 Epoch 200 inference completed!\nReceipt: {fold1_infer200_complete}"
            )

        if overall_complete.exists() and "overall_complete" not in notified_milestones:
            notified_milestones.add("overall_complete")
            summary_tail = get_log_tail(RUNTIME_DIR / "fold1_finalize.log", 30)
            notify(
                "[SUCCESS] Instance 1 Task A Full Pipeline Completed",
                f"Task A two-fold clinical regression UNet pipeline fully completed!\n"
                f"Receipt: {overall_complete}\n\n"
                f"Finalize log:\n{summary_tail}"
            )
            print("All pipeline goals achieved. Watchdog exiting gracefully.")
            break

        # Check active processes
        train_pids = get_pids_matching(r"clinical_regression_unet/run\.py train.*--fold 1")
        finalize_pids = get_pids_matching(r"finalize_instance1_fold1\.sh")
        infer_pids = get_pids_matching(r"clinical_regression_unet/run\.py infer.*--fold 1")
        summarize_pids = get_pids_matching(r"clinical_regression_unet/run\.py summarize")

        # 1. Did training crash before producing complete.json?
        if not fold1_train_complete.exists() and not train_pids:
            tail = get_log_tail(log_path, 60)
            notify(
                "[ERROR] Instance 1 Fold 1 Training Process Vanished",
                f"ALERT: Fold 1 training process is no longer running, but complete.json was NOT created!\n\n"
                f"GPU Status: {get_nvidia_smi()}\n\n"
                f"Last 60 lines of {log_path}:\n{tail}"
            )
            print("Training crash detected. Alert sent. Exiting watchdog.")
            break

        # 2. Did finalize script crash before overall completion?
        if not finalize_pids and not overall_complete.exists() and fold1_train_complete.exists() and not infer_pids and not summarize_pids:
            fin_log = RUNTIME_DIR / "fold1_finalize.log"
            tail = get_log_tail(fin_log, 60)
            notify(
                "[ERROR] Instance 1 Finalize Script Vanished",
                f"ALERT: finalize_instance1_fold1.sh is not running and completion.json is missing.\n\n"
                f"GPU Status: {get_nvidia_smi()}\n\n"
                f"Last 60 lines of {fin_log}:\n{tail}"
            )
            print("Finalize crash detected. Alert sent. Exiting watchdog.")
            break

        # 3. Check for stalls in training log
        if not fold1_train_complete.exists() and log_path.exists():
            curr_size = log_path.stat().st_size
            curr_mtime = log_path.stat().st_mtime
            if curr_size != last_log_size:
                last_log_size = curr_size
                last_log_mtime = curr_mtime
            elif (now - last_log_mtime) > max_idle_seconds and "stall_warning" not in notified_milestones:
                notified_milestones.add("stall_warning")
                tail = get_log_tail(log_path, 30)
                notify(
                    "[WARNING] Instance 1 Training Log Stalled",
                    f"WARNING: No new output in {log_path} for > {int((now - last_log_mtime) / 60)} minutes.\n"
                    f"Active train PIDs: {train_pids}\n"
                    f"GPU Status: {get_nvidia_smi()}\n\n"
                    f"Last log lines:\n{tail}"
                )


def monitor_instance_2(poll_interval: int = 60, max_idle_seconds: int = 1800) -> None:
    log_path = RUNTIME_DIR / "fold2_pipeline.log"
    fold2_train_complete = ASSETS_DIR / "formal/fold2/complete.json"
    fold2_infer165_complete = ASSETS_DIR / "oof/epoch165/fold2/complete.json"
    fold2_infer200_complete = ASSETS_DIR / "oof/epoch200/fold2/complete.json"

    print(f"Watchdog started for Instance 2 on {socket.gethostname()}")
    notify(
        "[WATCHDOG_ACTIVATED] Task A Instance 2 Watchdog Active",
        f"Watchdog started on Instance 2 ({socket.gethostname()}).\n"
        f"Monitoring Fold 2 training and inference (e165/e200).\n"
        f"Poll interval: {poll_interval}s, max idle timeout: {max_idle_seconds}s.\n"
        f"GPU Status: {get_nvidia_smi()}"
    )

    notified_milestones = set()
    last_log_mtime = log_path.stat().st_mtime if log_path.exists() else time.time()
    last_log_size = log_path.stat().st_size if log_path.exists() else 0

    while True:
        time.sleep(poll_interval)
        now = time.time()

        # Check milestones
        if fold2_train_complete.exists() and "fold2_train" not in notified_milestones:
            notified_milestones.add("fold2_train")
            notify(
                "[MILESTONE] Instance 2 Fold 2 Training Finished",
                f"Fold 2 training successfully completed!\n"
                f"Receipt: {fold2_train_complete}\n"
                f"Now proceeding to Fold 2 inference e165 & e200.\n"
                f"GPU Status: {get_nvidia_smi()}"
            )

        if fold2_infer165_complete.exists() and "fold2_infer165" not in notified_milestones:
            notified_milestones.add("fold2_infer165")
            notify(
                "[MILESTONE] Instance 2 Fold 2 Epoch 165 Inference Done",
                f"Fold 2 Epoch 165 inference completed!\nReceipt: {fold2_infer165_complete}"
            )

        if fold2_infer200_complete.exists() and "fold2_infer200" not in notified_milestones:
            notified_milestones.add("fold2_infer200")
            tail = get_log_tail(log_path, 30)
            notify(
                "[SUCCESS] Instance 2 Fold 2 Pipeline Finished",
                f"Fold 2 training & both inference runs completed!\n"
                f"Receipt: {fold2_infer200_complete}\n\n"
                f"Log tail:\n{tail}"
            )
            print("Fold 2 goals achieved. Watchdog exiting gracefully.")
            break

        # Check active processes
        runner_pids = get_pids_matching(r"run_instance2_fold2\.sh")
        train_pids = get_pids_matching(r"clinical_regression_unet/run\.py train.*--fold 2")
        infer_pids = get_pids_matching(r"clinical_regression_unet/run\.py infer.*--fold 2")

        # 1. Did training crash before producing complete.json?
        if not fold2_train_complete.exists() and not train_pids:
            tail = get_log_tail(log_path, 60)
            notify(
                "[ERROR] Instance 2 Fold 2 Training Process Vanished",
                f"ALERT: Fold 2 training process is no longer running, but complete.json was NOT created!\n\n"
                f"GPU Status: {get_nvidia_smi()}\n\n"
                f"Last 60 lines of {log_path}:\n{tail}"
            )
            print("Fold 2 crash detected. Alert sent. Exiting watchdog.")
            break

        # 2. Did runner script vanish before infer200 complete?
        if not runner_pids and not fold2_infer200_complete.exists() and not infer_pids:
            tail = get_log_tail(log_path, 60)
            notify(
                "[ERROR] Instance 2 Runner Script Vanished",
                f"ALERT: run_instance2_fold2.sh is not running and fold 2 is incomplete.\n\n"
                f"GPU Status: {get_nvidia_smi()}\n\n"
                f"Last 60 lines of {log_path}:\n{tail}"
            )
            print("Runner crash detected. Alert sent. Exiting watchdog.")
            break

        # 3. Check for stalls in log
        if not fold2_train_complete.exists() and log_path.exists():
            curr_size = log_path.stat().st_size
            curr_mtime = log_path.stat().st_mtime
            if curr_size != last_log_size:
                last_log_size = curr_size
                last_log_mtime = curr_mtime
            elif (now - last_log_mtime) > max_idle_seconds and "stall_warning" not in notified_milestones:
                notified_milestones.add("stall_warning")
                tail = get_log_tail(log_path, 30)
                notify(
                    "[WARNING] Instance 2 Training Log Stalled",
                    f"WARNING: No new output in {log_path} for > {int((now - last_log_mtime) / 60)} minutes.\n"
                    f"Active train PIDs: {train_pids}\n"
                    f"GPU Status: {get_nvidia_smi()}\n\n"
                    f"Last log lines:\n{tail}"
                )


def main() -> None:
    parser = argparse.ArgumentParser(description="Watchdog for Task A runs")
    parser.add_argument("--instance", type=int, choices=[1, 2], required=True,
                        help="Instance ID (1 or 2)")
    parser.add_argument("--poll-interval", type=int, default=60,
                        help="Seconds between status checks (default: 60)")
    parser.add_argument("--max-idle", type=int, default=1800,
                        help="Max seconds without log growth before warning (default: 1800)")
    args = parser.parse_args()

    if args.instance == 1:
        monitor_instance_1(poll_interval=args.poll_interval, max_idle_seconds=args.max_idle)
    else:
        monitor_instance_2(poll_interval=args.poll_interval, max_idle_seconds=args.max_idle)


if __name__ == "__main__":
    main()
