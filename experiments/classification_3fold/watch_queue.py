#!/usr/bin/env python3
"""One fixed per-instance classification queue, after its previous PID exits."""
import argparse
import ctypes
import errno
import fcntl
import json
import os
from pathlib import Path
import select
import shutil
import socket
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone


def write(path, value):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    tmp.replace(path)


def process_identity(pid):
    p = Path(f"/proc/{pid}/stat")
    try:
        text = p.read_text()
    except FileNotFoundError:
        return None
    fields = text.rsplit(")", 1)[1].split()
    return None if fields[0] == "Z" else fields[19]  # /proc starttime, not PID alone.


def gpu_state():
    info = subprocess.check_output(["nvidia-smi", "-i", "0",
        "--query-gpu=uuid,memory.free", "--format=csv,noheader,nounits"], text=True).strip()
    apps = subprocess.check_output(["nvidia-smi", "-i", "0",
        "--query-compute-apps=pid", "--format=csv,noheader"], text=True).strip()
    uuid, free = [x.strip() for x in info.split(",")]
    return dict(uuid=uuid, free_MiB=int(free), processes=apps)


def prior_eta(plan):
    path = Path(plan["prior_epochs_file"])
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    last = records[-1]
    epoch_s = statistics.median(r["seconds"] for r in records[-3:])
    since_record = max(0, time.time() - path.stat().st_mtime)
    remaining = (200 - last["epoch"]) * epoch_s - since_record
    delay = remaining * 1.03 + 120 if remaining > 0 else max(600, 3 * epoch_s)
    return max(300, delay), dict(last_logged_epoch=last["epoch"], epoch_seconds=epoch_s,
                                 elapsed_since_record_s=since_record)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--plan", type=Path, required=True)
    p.add_argument("--first-check-utc", help="Sleep until this ISO UTC deadline before any readiness check")
    args = p.parse_args()
    plan = json.loads(args.plan.read_text())
    state_path = args.plan.with_name("watch_status.json")
    lock = args.plan.with_suffix(".lock").open("a")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    root = Path(plan["code_root"])
    base = Path(plan["output_root"])
    base.mkdir(parents=True, exist_ok=True)

    def status(stage, **extra):
        value = dict(status=stage, instance=plan["instance"], monitor_pid=os.getpid(),
                     host=socket.gethostname(), checked_utc=datetime.now(timezone.utc).isoformat(),
                     prior_pid=plan["prior_pid"], **extra)
        write(state_path, value)
        print(json.dumps(value, ensure_ascii=False), flush=True)

    def timer(stage, seconds, **extra):
        wake = datetime.fromtimestamp(time.time() + seconds, timezone.utc).isoformat()
        status(stage, sleep_seconds=round(seconds), next_check_utc=wake, **extra)
        time.sleep(seconds)

    try:
        # PET-only follow-on: wait for the entire prior clinical queue, including
        # all its remaining children and persistence copies, using a PID event.
        # Existing queues without this option retain their original behavior.
        if plan.get("wait_for_prior_queue_exit"):
            if process_identity(plan["prior_pid"]) == plan["prior_starttime"]:
                status("WAIT_PRIOR_QUEUE_EXIT")
                # These four x86_64 cloud instances lack Python's wrapper.
                # SYS_pidfd_open=434; wait on the kernel event, without polling.
                libc = ctypes.CDLL(None, use_errno=True)
                libc.syscall.restype = ctypes.c_long
                fd = int(libc.syscall(434, plan["prior_pid"], 0))
                if fd < 0:
                    code = ctypes.get_errno()
                    if code != errno.ESRCH:
                        raise OSError(code, os.strerror(code))
                else:
                    try:
                        if process_identity(plan["prior_pid"]) == plan["prior_starttime"]:
                            select.select([fd], [], [])
                    finally:
                        os.close(fd)
            previous = json.loads(Path(plan["prior_queue_status"]).read_text())
            if previous["status"] != "QUEUE_COMPLETE":
                raise RuntimeError("Prior clinical queue exited before QUEUE_COMPLETE")
        if args.first_check_utc:
            delay = datetime.fromisoformat(args.first_check_utc).timestamp() - time.time()
            if delay > 0:
                timer("TIMER_WAIT_TRANSFER_CHECK", delay)
        while True:
            old_alive = process_identity(plan["prior_pid"]) == plan["prior_starttime"]
            inputs_ready = Path(plan["inputs_ready"]).is_file()
            release_path = Path(plan["release_file"])
            release = json.loads(release_path.read_text()) if release_path.is_file() else {}
            if old_alive:
                delay, estimate = prior_eta(plan)
                timer("TIMER_WAIT_PRIOR_PID", delay, inputs_ready=inputs_ready,
                      pilot_passed=release.get("pilot_passed", False), estimate=estimate)
            elif not inputs_ready or not release.get("pilot_passed", False):
                timer("TIMER_WAIT_INPUTS_OR_PILOT", 1800, inputs_ready=inputs_ready,
                      pilot_passed=release.get("pilot_passed", False))
            else:
                gpu = gpu_state()
                if gpu["uuid"] != plan["gpu_uuid"]:
                    raise RuntimeError("Assigned GPU UUID changed")
                if not gpu["processes"] and gpu["free_MiB"] >= 44000:
                    break
                timer("TIMER_WAIT_GPU_RELEASE", 1800, gpu=gpu)
        for index, job in enumerate(plan["jobs"], 1):
            output = base / job["task"] / job["condition"] / f"fold{job['fold']}"
            summary = output / "summary.json"
            if summary.is_file():
                prior = json.loads(summary.read_text())
                if (prior.get("status") == "complete" and prior.get("epochs") == 200
                        and prior.get("task") == job["task"]
                        and prior.get("condition") == job["condition"]
                        and prior.get("fold") == job["fold"]):
                    continue
                raise RuntimeError(f"Incomplete existing fit requires review: {output}")
            while True:
                gpu = gpu_state()
                if gpu["uuid"] != plan["gpu_uuid"]:
                    raise RuntimeError("Assigned GPU UUID changed")
                if not gpu["processes"] and gpu["free_MiB"] >= 44000:
                    break
                timer("TIMER_WAIT_GPU_RELEASE_NEXT_FIT", 600, job=job, gpu=gpu)
            log = base / f"{job['task']}_{job['condition']}_fold{job['fold']}.log"
            command = [sys.executable, "-B", "-u", str(root / "experiments/classification_3fold/run.py"),
                "fit", "--task", job["task"], "--condition", job["condition"],
                "--fold", str(job["fold"]), "--epochs", "200", "--batch-size", str(release["batch_size"]),
                "--gpu", "0", "--subjects", str(root / "reports/r2_11_classification_subjects.csv"),
                "--splits", str(root / "reports/r2_11_classification_3fold/splits.csv"),
                "--data-root", plan["data_root"], "--output", str(output)]
            with log.open("x") as stream:
                child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT)
                status("CLASSIFICATION_RUNNING", job=job, job_number=index,
                       jobs_total=len(plan["jobs"]), training_pid=child.pid, log=str(log))
                code = child.wait()
            if code != 0 or not summary.is_file() or json.loads(summary.read_text()).get("status") != "complete":
                raise RuntimeError(f"Fit failed, queue stopped: {job}, exit={code}; see {log}")
            persistent = Path(plan["persistent_root"]) / f"{time.strftime('%Y%m%d')}_{child.pid}" / job["task"] / job["condition"] / f"fold{job['fold']}"
            persistent.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(output, persistent)
            status("FIT_COMPLETE", job=job, job_number=index, jobs_total=len(plan["jobs"]),
                   persistent_output=str(persistent))
        status("QUEUE_COMPLETE", jobs_total=len(plan["jobs"]))
    except Exception as error:
        status("STOPPED_ERROR", error=f"{type(error).__name__}: {error}")
        raise


if __name__ == "__main__":
    main()
