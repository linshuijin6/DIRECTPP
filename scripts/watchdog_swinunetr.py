#!/usr/bin/env python3
"""Out-of-band watchdog monitor for SwinUNETR baseline training.

Monitors training process PID, log updates, recovery checkpoints, and completion receipts.
Dispatches email notifications on activation, milestones, successful completion, or crashes.
Operates strictly read-only and out-of-band without interfering with the training process.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import smtplib
import socket
import subprocess
import sys
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path


DEFAULT_TO = "1170414294@qq.com"
DEFAULT_FROM = "shuijinlin@stu.xjtu.edu.cn"
DEFAULT_SMTP_SERVER = "smtp.stu.xjtu.edu.cn"
DEFAULT_SMTP_PORT = 465
DEFAULT_SMTP_USER = "shuijinlin@stu.xjtu.edu.cn"
DEFAULT_SMTP_PWD = "kva2i63jzrc7yhk5"


def send_email(subject: str, content: str, max_retries: int = 3) -> bool:
    """Send an email notification via SSL SMTP with retry support."""
    to_email = os.environ.get("ERROR_TO_EMAIL") or DEFAULT_TO
    from_email = os.environ.get("ERROR_FROM_EMAIL") or DEFAULT_FROM
    smtp_server = os.environ.get("ERROR_SMTP_SERVER") or DEFAULT_SMTP_SERVER
    smtp_port = int(os.environ.get("ERROR_SMTP_PORT") or DEFAULT_SMTP_PORT)
    smtp_user = os.environ.get("ERROR_SMTP_USER") or DEFAULT_SMTP_USER
    smtp_password = os.environ.get("ERROR_SMTP_PASSWORD") or DEFAULT_SMTP_PWD

    msg = MIMEMultipart()
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(content, "plain", "utf-8"))

    for attempt in range(1, max_retries + 1):
        try:
            with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=15) as server:
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            print(f"[{datetime.datetime.now().isoformat()}] Email sent successfully: {subject}", flush=True)
            return True
        except Exception as e:
            print(f"[{datetime.datetime.now().isoformat()}] SMTP send failed (attempt {attempt}/{max_retries}): {e}", flush=True)
            if attempt < max_retries:
                time.sleep(5 * attempt)
    return False


def get_gpu_status() -> str:
    """Get compact nvidia-smi status."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,temperature.gpu,utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            stderr=subprocess.STDOUT,
            timeout=5
        ).decode("utf-8", errors="replace").strip()
        return out
    except Exception as e:
        return f"nvidia-smi error: {e}"


def get_log_tail(log_path: Path, n_lines: int = 60) -> str:
    """Return the last N lines of a log file."""
    if not log_path.is_file():
        return f"Log file does not exist yet: {log_path}"
    try:
        out = subprocess.check_output(
            ["tail", f"-n{n_lines}", str(log_path)],
            stderr=subprocess.STDOUT,
            timeout=5
        ).decode("utf-8", errors="replace").strip()
        return out
    except Exception as e:
        return f"Failed to read log tail: {e}"


def is_pid_alive(pid: int) -> bool:
    """Check if process PID is currently alive without sending a terminating signal."""
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def find_training_process() -> tuple[int, dict] | None:
    """Auto-discover a running swinunetr training process and parse its arguments."""
    try:
        out = subprocess.check_output(["ps", "-eo", "pid,command"], timeout=5).decode("utf-8", errors="replace")
    except Exception:
        return None

    for line in out.splitlines():
        if "swinunetr/run.py train" in line:
            parts = line.strip().split(maxsplit=1)
            pid = int(parts[0])
            cmd = parts[1]
            info = {"pid": pid, "cmd": cmd}
            tokens = cmd.split()
            for i, tok in enumerate(tokens):
                if tok == "--config" and i + 1 < len(tokens):
                    info["config"] = tokens[i + 1]
                elif tok == "--tracer" and i + 1 < len(tokens):
                    info["tracer"] = tokens[i + 1]
                elif tok == "--fold" and i + 1 < len(tokens):
                    info["fold"] = int(tokens[i + 1])
                elif tok == "--log-path" and i + 1 < len(tokens):
                    info["log_path"] = tokens[i + 1]
            return pid, info
    return None


def run_watchdog(instance_id: str, pid: int, tracer: str, fold: int,
                 assets_dir: Path, log_path: Path, config_path: Path | None = None,
                 poll_interval: int = 60, target_epochs: int = 200) -> None:
    hostname = socket.gethostname()
    run_dir = assets_dir / "formal" / tracer / f"fold{fold}"
    complete_json = run_dir / "complete.json"
    recovery_pt = run_dir / "recovery.pt"
    epochs_jsonl = run_dir / "training_epochs.jsonl"

    subject_prefix = f"[{instance_id.upper()}] SwinUNETR {tracer} Fold {fold}"

    activation_msg = (
        f"=====================================================\n"
        f"Watchdog External Monitor Activated on {instance_id}\n"
        f"=====================================================\n"
        f"Hostname: {hostname}\n"
        f"Activation Time: {datetime.datetime.now().isoformat()}\n"
        f"Task: SwinUNETR {tracer} Fold {fold} ({target_epochs} epochs budget)\n"
        f"Monitored Training PID: {pid}\n"
        f"Training Log Path: {log_path}\n"
        f"Formal Run Directory: {run_dir}\n"
        f"Expected Completion Receipt: {complete_json}\n"
        f"Current GPU Status: {get_gpu_status()}\n"
        f"Watchdog Poll Interval: {poll_interval}s\n"
        f"-----------------------------------------------------\n"
        f"Monitoring active: email will be sent on milestones, success, or abnormal exit.\n"
    )
    send_email(f"{subject_prefix} [WATCHDOG ACTIVATED]", activation_msg)

    last_epoch = 0
    notified_milestones = set()
    consecutive_missing_count = 0
    loop_count = 0

    print(f"[{datetime.datetime.now().isoformat()}] Watchdog loop started for PID {pid}...", flush=True)

    while True:
        time.sleep(poll_interval)
        alive = is_pid_alive(pid)
        loop_count += 1
        if loop_count % 30 == 0:  # Every 30 minutes
            print(f"[{datetime.datetime.now().isoformat()}] Heartbeat: PID {pid} alive, last_epoch={last_epoch}/{target_epochs}, GPU={get_gpu_status()}", flush=True)

        # Parse epochs_jsonl if present
        if epochs_jsonl.is_file():
            try:
                lines = [l.strip() for l in epochs_jsonl.read_text().splitlines() if l.strip()]
                if lines:
                    last_record = json.loads(lines[-1])
                    current_epoch = int(last_record.get("epoch", 0))
                    if current_epoch > last_epoch:
                        last_epoch = current_epoch
                        # Check milestones at every 50 epochs
                        if current_epoch in (50, 100, 150) and current_epoch not in notified_milestones:
                            notified_milestones.add(current_epoch)
                            milestone_msg = (
                                f"Milestone Update from {instance_id} ({hostname})\n"
                                f"Task: SwinUNETR {tracer} Fold {fold}\n"
                                f"Current Epoch: {current_epoch} / {target_epochs}\n"
                                f"Mean MSE Loss: {last_record.get('train_mse_mean')}\n"
                                f"Epoch Seconds: {last_record.get('seconds', 0):.1f}s\n"
                                f"Recovery Checkpoint: {recovery_pt} (exists: {recovery_pt.is_file()})\n"
                                f"GPU Status: {get_gpu_status()}\n"
                                f"Timestamp: {datetime.datetime.now().isoformat()}\n"
                            )
                            send_email(f"{subject_prefix} [MILESTONE Epoch {current_epoch}/{target_epochs}]", milestone_msg)
            except Exception as e:
                print(f"Error reading epochs jsonl: {e}", flush=True)

        if not alive:
            # PID not in process table: wait a moment to avoid race condition during exit
            time.sleep(5)
            if complete_json.is_file():
                # SUCCESSFUL COMPLETION
                try:
                    receipt = json.loads(complete_json.read_text())
                except Exception:
                    receipt = {}
                success_msg = (
                    f"=====================================================\n"
                    f"🎉 TRAINING COMPLETED SUCCESSFULLY on {instance_id}\n"
                    f"=====================================================\n"
                    f"Hostname: {hostname}\n"
                    f"Task: SwinUNETR {tracer} Fold {fold} ({target_epochs} epochs)\n"
                    f"Completion Receipt: {complete_json}\n"
                    f"Final Checkpoint: {receipt.get('final_checkpoint', 'N/A')}\n\n"
                    f"Completion Details:\n{json.dumps(receipt, indent=2, ensure_ascii=False)}\n\n"
                    f"Log Tail:\n{get_log_tail(log_path, 40)}\n\n"
                    f"GPU Status: {get_gpu_status()}\n"
                    f"Completion Time: {datetime.datetime.now().isoformat()}\n"
                )
                send_email(f"{subject_prefix} [SUCCESS] Training Complete", success_msg)
                print(f"[{datetime.datetime.now().isoformat()}] Training completed successfully. Watchdog exiting.", flush=True)
                break
            else:
                consecutive_missing_count += 1
                if consecutive_missing_count >= 2:
                    # PROCESS DIED WITHOUT COMPLETE.JSON -> ABNORMAL EXIT / CRASH
                    error_msg = (
                        f"=====================================================\n"
                        f"🚨 TRAINING PROCESS CRASHED / EXITED ABNORMALLY on {instance_id}\n"
                        f"=====================================================\n"
                        f"Hostname: {hostname}\n"
                        f"Task: SwinUNETR {tracer} Fold {fold}\n"
                        f"Monitored PID: {pid} has EXITED.\n"
                        f"Expected Completion Receipt ({complete_json}) was NOT created.\n"
                        f"Last Recorded Epoch: {last_epoch} / {target_epochs}\n"
                        f"Recovery Checkpoint Exists: {recovery_pt.is_file()}\n"
                        f"GPU Status: {get_gpu_status()}\n\n"
                        f"Log Tail (Last 80 lines):\n"
                        f"-----------------------------------------------------\n"
                        f"{get_log_tail(log_path, 80)}\n"
                        f"-----------------------------------------------------\n"
                        f"Crash Detection Time: {datetime.datetime.now().isoformat()}\n"
                    )
                    send_email(f"{subject_prefix} [ERROR] Training Exited Prematurely (PID={pid})", error_msg)
                    print(f"[{datetime.datetime.now().isoformat()}] PID {pid} died abnormally. Watchdog exiting.", flush=True)
                    break
        else:
            consecutive_missing_count = 0


def main():
    parser = argparse.ArgumentParser(description="Watchdog monitor for SwinUNETR baseline")
    parser.add_argument("--instance", type=str, default="", help="Instance identifier (e.g. instance3)")
    parser.add_argument("--pid", type=int, default=0, help="Training process PID")
    parser.add_argument("--tracer", type=str, choices=("FDG", "AV45", ""), default="")
    parser.add_argument("--fold", type=int, choices=(0, 1, 2), default=0)
    parser.add_argument("--assets-dir", type=Path, default=None)
    parser.add_argument("--log-path", type=Path, default=None)
    parser.add_argument("--config", type=Path, default=None)
    parser.add_argument("--poll-interval", type=int, default=60)
    parser.add_argument("--epochs", type=int, default=200)
    parser.add_argument("--auto", action="store_true", help="Auto-discover running swinunetr training process")

    args = parser.parse_args()

    pid = args.pid
    tracer = args.tracer
    fold = args.fold
    assets_dir = args.assets_dir
    log_path = args.log_path
    config_path = args.config

    if args.auto or pid == 0:
        discovered = find_training_process()
        if not discovered:
            print("ERROR: No running swinunetr training process found.", flush=True)
            sys.exit(1)
        d_pid, d_info = discovered
        pid = pid or d_pid
        tracer = tracer or d_info.get("tracer", "")
        fold = fold or d_info.get("fold", 0)
        if not log_path and "log_path" in d_info:
            log_path = Path(d_info["log_path"])
        if not config_path and "config" in d_info:
            config_path = Path(d_info["config"])

    if not config_path and not assets_dir:
        print("ERROR: Neither --config nor --assets-dir provided, and could not auto-discover.", flush=True)
        sys.exit(1)

    if config_path and not assets_dir:
        if config_path.is_file():
            cfg_data = json.loads(config_path.read_text())
            assets_dir = Path(cfg_data["assets"])
            target_epochs = int(cfg_data.get("epochs", args.epochs))
        else:
            print(f"ERROR: Config file not found: {config_path}", flush=True)
            sys.exit(1)
    else:
        target_epochs = args.epochs

    if not assets_dir or not log_path or not tracer or fold not in (1, 2):
        print(f"ERROR: Incomplete parameters: pid={pid}, tracer={tracer}, fold={fold}, assets_dir={assets_dir}, log_path={log_path}", flush=True)
        sys.exit(1)

    instance_id = args.instance or socket.gethostname()
    print(f"Starting watchdog for {instance_id}: PID={pid}, {tracer} Fold {fold}, Assets={assets_dir}, Log={log_path}", flush=True)
    run_watchdog(instance_id, pid, tracer, fold, assets_dir, log_path, config_path,
                 poll_interval=args.poll_interval, target_epochs=target_epochs)


if __name__ == "__main__":
    main()
