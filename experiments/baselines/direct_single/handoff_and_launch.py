"""Wait for one prior cloud-instance task, then preflight and launch one Single task.

CPU-only until the prior training and OOF receipts are present and the GPU is
idle. This process never stops, signals, or modifies a pre-existing job.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from common import json_write, sha256


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def gpu_state():
    gpu = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=uuid,memory.free,memory.total", "--format=csv,noheader,nounits"],
        text=True, timeout=10).strip().splitlines()
    apps = subprocess.check_output(
        ["nvidia-smi", "--query-compute-apps=pid,process_name,used_gpu_memory", "--format=csv,noheader,nounits"],
        text=True, timeout=10).strip()
    if len(gpu) != 1:
        raise RuntimeError(f"Expected one dedicated GPU, found {len(gpu)}")
    uuid, free, total = (part.strip() for part in gpu[0].split(","))
    return {"uuid": uuid, "free_mib": int(free), "total_mib": int(total), "compute_apps": apps}


def old_task_complete(args):
    training, oof = args.prior_training_complete, args.prior_oof_complete
    if not training.is_file():
        return False
    train_receipt = json.loads(training.read_text())
    if train_receipt.get("status") != "TRAINING_COMPLETE_NOT_INFERRED":
        return False
    if args.allow_prior_oof_pending:
        return True
    if not oof.is_file():
        return False
    return json.loads(oof.read_text()).get("status") == "COMPLETE_FOLD_OOF"


def allocation_receipt(path: Path, args, state: dict):
    receipt = {"allocation_status": "EXCLUSIVE", "gpu_uuid": state["uuid"],
               "host": socket.gethostname(), "issued_utc": utc_now(),
               "issued_by": "DIReCT Single per-instance handoff after prior training completion; live nvidia-smi no holders",
               "protection_id": f"direct-single-{args.task}-{os.getpid()}-{int(time.time())}",
               "prior_training_completion_sha256": sha256(args.prior_training_complete),
               "prior_oof_completion_sha256": (sha256(args.prior_oof_complete)
                                                if args.prior_oof_complete.is_file() else None),
               "prior_oof_pending_allowed": args.allow_prior_oof_pending,
               "live_gpu": state}
    json_write(path, receipt)
    return receipt


def run(args):
    config = json.loads(args.config.read_text())
    if config["task"] != args.task:
        raise RuntimeError("Task and frozen config differ")
    report = Path(config["report"])
    if (report / "launch.json").exists() or (report / "cuda_preflight.json").exists():
        raise RuntimeError("This task has already begun handoff or preflight")
    status_path = report / "handoff_status.json"
    json_write(status_path, {"status": "WAITING_FOR_PRIOR_TASK", "task": args.task,
                             "prior_training_receipt": str(args.prior_training_complete),
                             "prior_oof_receipt": str(args.prior_oof_complete),
                             "prior_oof_pending_allowed": args.allow_prior_oof_pending,
                             "checked_utc": utc_now()})
    while True:
        if (report / "launch.json").exists():
            raise RuntimeError("Another launcher has already started this task")
        if old_task_complete(args):
            try:
                state = gpu_state()
                if (state["uuid"] == args.gpu_uuid and not state["compute_apps"]
                        and state["free_mib"] >= 46080 and state["total_mib"] >= 48000):
                    break
            except Exception as error:
                print(f"{utc_now()} GPU query not yet ready: {error}", flush=True)
        time.sleep(args.poll_seconds)
    preflight_receipt = report / "gpu_allocation_preflight.json"
    allocation_receipt(preflight_receipt, args, state)
    env = os.environ.copy()
    env["CUDA_VISIBLE_DEVICES"] = args.gpu_uuid
    runner = Path(__file__).with_name("run.py")
    base = [sys.executable, "-u", str(runner)]
    try:
        with (report / "preflight.log").open("w") as stream:
            subprocess.run(base + ["smoke-test", "--config", str(args.config),
                       "--resource-receipt", str(preflight_receipt)], env=env,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)
        preflight = json.loads((report / "cuda_preflight.json").read_text())
        if preflight["status"] != "PASS_NO_FORMAL_TRAINING_STATE":
            raise RuntimeError(f"Preflight status: {preflight['status']}")
        if preflight["training_time_estimates"][args.task]["hours"] > 72:
            raise RuntimeError("Estimated task duration exceeds 72 hours")
        state = gpu_state()
        if state["uuid"] != args.gpu_uuid or state["compute_apps"] or state["free_mib"] < 46080:
            raise RuntimeError("GPU changed or was occupied after isolated preflight")
        train_receipt = report / "gpu_allocation_train.json"
        allocation_receipt(train_receipt, args, state)
        log = report / "train.log"
        with log.open("w") as stream:
            proc = subprocess.Popen(base + ["train", "--config", str(args.config),
                 "--resource-receipt", str(train_receipt), "--log-path", str(log)],
                 cwd=Path(__file__).resolve().parents[3], env=env,
                 stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        for _ in range(30):
            if (report / "launch.json").is_file():
                break
            if proc.poll() is not None:
                raise RuntimeError(f"Train process exited before launch receipt: code {proc.returncode}")
            time.sleep(2)
        else:
            raise RuntimeError("Train process did not create launch receipt within 60 seconds")
        launch = json.loads((report / "launch.json").read_text())
        if launch["pid"] != proc.pid:
            raise RuntimeError("Launch receipt PID differs from process PID")
        json_write(status_path, {"status": "TRAINING_STARTED", "task": args.task,
                "instance_host": socket.gethostname(), "gpu_uuid": args.gpu_uuid,
                "pid": proc.pid, "started_utc": launch["started_utc"],
                "config_sha256": sha256(args.config), "log": str(log),
                "checkpoint_dir": launch["checkpoint_dir"], "recovery": launch["recovery_path"],
                "preflight": str(report / "cuda_preflight.json")})
        print(json.dumps({"status": "TRAINING_STARTED", "task": args.task, "pid": proc.pid,
                          "gpu_uuid": args.gpu_uuid, "log": str(log)}), flush=True)
    except Exception as error:
        json_write(status_path, {"status": "BLOCKED", "task": args.task,
                                 "error": f"{type(error).__name__}: {error}", "checked_utc": utc_now(),
                                 "preflight_log": str(report / "preflight.log")})
        raise


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--task", required=True)
    p.add_argument("--config", type=Path, required=True)
    p.add_argument("--gpu-uuid", required=True)
    p.add_argument("--prior-training-complete", type=Path, required=True)
    p.add_argument("--prior-oof-complete", type=Path, required=True)
    p.add_argument("--allow-prior-oof-pending", action="store_true",
                   help="Allow launch after prior training is complete, while its OOF remains pending")
    p.add_argument("--poll-seconds", type=int, default=60)
    return p


if __name__ == "__main__":
    run(parser().parse_args())
