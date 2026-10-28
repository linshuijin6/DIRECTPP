#!/usr/bin/env python3
"""Fail-closed six-GPU launcher for the frozen Stage 4D 24-fit protocol."""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "reports/full_ot_medical_evidence"
RECEIPT_4C4 = REPORT_DIR / "04c4_full_inference_receipt.json"
PREFLIGHT = REPORT_DIR / "04d_full_preflight.json"
LAUNCH_RECEIPT = REPORT_DIR / "04d_training_launch_receipt.json"
RUNNER = REPO / "experiments/classification_2fold/run.py"
LAUNCH_ROOT = Path("/mnt/datas230/users/linshuijin/DIRECTPP_classification_2fold/launch_20261028_attempt2")
OUTPUT_ROOT = Path("/mnt/datas230/users/linshuijin/DIRECTPP_classification_2fold/20261028")
AUTHORIZATION = "RUN_STAGE_4D_24_FITS"
CONDITIONS = ("mri", "mri_real", "mri_full", "mri_ot")
ASSIGNMENTS = (
    (0, "ad_cn", 1),
    (1, "ad_cn", 2),
    (2, "mci_cn", 1),
    (3, "mci_cn", 2),
    (4, "lmci_emci", 1),
    (5, "lmci_emci", 2),
)


class LaunchError(RuntimeError):
    pass


def atomic_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def wait_for_4c4(timeout_seconds: int) -> dict:
    started = time.time()
    while time.time() - started <= timeout_seconds:
        if RECEIPT_4C4.is_file():
            try:
                receipt = json.loads(RECEIPT_4C4.read_text())
            except (OSError, json.JSONDecodeError):
                time.sleep(15)
                continue
            if receipt.get("status") == "COMPLETE" and int(receipt.get("actual_predictions", -1)) == 3620:
                return receipt
            raise LaunchError(f"4C-4 receipt exists but is not COMPLETE/3620: {receipt.get('status')}")
        time.sleep(15)
    raise LaunchError(f"timed out waiting for {RECEIPT_4C4}")


def run_preflight() -> None:
    if PREFLIGHT.exists():
        receipt = json.loads(PREFLIGHT.read_text())
        if receipt.get("status") != "PASS" or len(receipt.get("fits", [])) != 24:
            raise LaunchError(f"existing preflight is not PASS with 24 fits: {PREFLIGHT}")
        return
    log_path = LAUNCH_ROOT / "preflight.log"
    with log_path.open("w") as log:
        result = subprocess.run(
            [sys.executable, str(RUNNER), "preflight", "--output", str(PREFLIGHT)],
            cwd=REPO, stdout=log, stderr=subprocess.STDOUT, text=True,
        )
    if result.returncode != 0:
        raise LaunchError(f"classification preflight failed with rc={result.returncode}; see {log_path}")
    receipt = json.loads(PREFLIGHT.read_text())
    if receipt.get("status") != "PASS" or len(receipt.get("fits", [])) != 24:
        raise LaunchError("classification preflight output is not PASS with 24 fits")


def check_gpu(gpu: int) -> dict[str, int]:
    free = subprocess.run(
        ["nvidia-smi", "-i", str(gpu), "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    )
    free_mb = int(free.stdout.strip().splitlines()[0])
    processes = subprocess.run(
        ["nvidia-smi", "-i", str(gpu), "--query-compute-apps=pid", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, check=True,
    )
    pids = [line.strip() for line in processes.stdout.splitlines() if line.strip()]
    if pids or free_mb < 20000:
        raise LaunchError(f"GPU {gpu} is no longer free: free_mb={free_mb}, compute_pids={pids}")
    return {"physical_gpu": gpu, "free_mb": free_mb, "compute_processes": len(pids)}


def worker(args: argparse.Namespace) -> int:
    status_path = LAUNCH_ROOT / f"worker_{args.task}_fold{args.outer_fold}.json"
    status: dict[str, object] = {
        "status": "RUNNING", "host": socket.gethostname(), "physical_gpu": args.gpu,
        "task": args.task, "outer_fold": args.outer_fold, "pid": os.getpid(),
        "conditions": [], "started_epoch": time.time(),
    }
    atomic_json(status_path, status)
    for condition in CONDITIONS:
        command = [
            sys.executable, str(RUNNER), "fit", "--task", args.task,
            "--outer-fold", str(args.outer_fold), "--condition", condition,
            "--output-root", str(OUTPUT_ROOT), "--resume", "--authorization", AUTHORIZATION,
        ]
        result = subprocess.run(command, cwd=REPO)
        status["conditions"].append({"condition": condition, "returncode": result.returncode})
        if result.returncode != 0:
            status.update({"status": "FAILED", "failed_condition": condition, "ended_epoch": time.time()})
            atomic_json(status_path, status)
            return result.returncode
        atomic_json(status_path, status)
    status.update({"status": "COMPLETE", "ended_epoch": time.time()})
    atomic_json(status_path, status)
    return 0


def launch(args: argparse.Namespace) -> int:
    if socket.gethostname() != "server":
        raise LaunchError(f"launcher must run on node 3014/server, got {socket.gethostname()}")
    if LAUNCH_RECEIPT.exists() or LAUNCH_ROOT.exists():
        raise LaunchError("launch receipt/root already exists; refusing duplicate launch")
    LAUNCH_ROOT.mkdir(parents=True)
    try:
        receipt = wait_for_4c4(args.wait_seconds)
        run_preflight()
        gpu_checks = [check_gpu(gpu) for gpu, _, _ in ASSIGNMENTS]
        workers = []
        for gpu, task, fold in ASSIGNMENTS:
            log_path = LAUNCH_ROOT / f"worker_{task}_fold{fold}.log"
            log = log_path.open("w")
            env = os.environ.copy()
            env["CUDA_VISIBLE_DEVICES"] = str(gpu)
            process = subprocess.Popen(
                [sys.executable, str(Path(__file__)), "--worker", "--gpu", str(gpu),
                 "--task", task, "--outer-fold", str(fold)],
                cwd=REPO, env=env, stdout=log, stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            log.close()
            workers.append({"physical_gpu": gpu, "task": task, "outer_fold": fold,
                            "pid": process.pid, "log": str(log_path)})
        launch_receipt = {
            "status": "LAUNCHED", "host": socket.gethostname(), "launcher_pid": os.getpid(),
            "launched_epoch": time.time(), "stage4c4_status": receipt["status"],
            "preflight": str(PREFLIGHT), "preflight_status": "PASS", "fits": 24,
            "gpu_checks": gpu_checks, "workers": workers, "output_root": str(OUTPUT_ROOT),
        }
        atomic_json(LAUNCH_RECEIPT, launch_receipt)
        print(json.dumps(launch_receipt, indent=2))
        return 0
    except Exception as error:
        atomic_json(LAUNCH_ROOT / "launch_failure.json", {
            "status": "FAILED", "error": repr(error), "epoch": time.time(),
        })
        raise


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-seconds", type=int, default=3600)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--gpu", type=int)
    parser.add_argument("--task", choices=("ad_cn", "mci_cn", "lmci_emci"))
    parser.add_argument("--outer-fold", type=int, choices=(1, 2))
    return parser.parse_args()


if __name__ == "__main__":
    parsed = parse_args()
    try:
        if parsed.worker:
            if parsed.gpu is None or parsed.task is None or parsed.outer_fold is None:
                raise LaunchError("worker identity arguments are incomplete")
            raise SystemExit(worker(parsed))
        raise SystemExit(launch(parsed))
    except LaunchError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        raise SystemExit(2)
