#!/usr/bin/env python3
"""Validate finished modality uploads and relay them through the shared cloud FS."""
import concurrent.futures
import argparse
import json
from pathlib import Path
import shlex
import subprocess
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/r2_11_classification_3fold"
HOST = "root@connect.westb.seetacloud.com"
PORTS = {3: 44919, 4: 22299, 5: 15055, 6: 51712}
INPUTS = "/root/autodl-tmp/DIRECTPP_classification_inputs"
REMOTE_REPORT = "/root/autodl-tmp/DIRECTPP/reports/r2_11_classification_3fold"
RELAY = "/autodl-fs/data/DIRECTPP_classification_transfer_20261031"


def status(stage, **kwargs):
    value = dict(status=stage, checked_utc=datetime.now(timezone.utc).isoformat(), **kwargs)
    p = REPORT / "staging_status.json"
    t = p.with_suffix(".tmp"); t.write_text(json.dumps(value, indent=2) + "\n"); t.replace(p)
    print(json.dumps(value), flush=True)


def timer(stage, seconds, **kwargs):
    wake = datetime.fromtimestamp(time.time() + seconds, timezone.utc).isoformat()
    status(stage, sleep_seconds=round(seconds), next_check_utc=wake, **kwargs)
    time.sleep(seconds)


def remote_python(node, code, timeout=180):
    command = "/root/miniconda3/bin/python -B -c " + shlex.quote(code)
    return subprocess.check_output(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15",
        "-p", str(PORTS[node]), HOST, command], text=True, timeout=timeout)


def validate(node, modality=None):
    code = f'''from pathlib import Path
import json,time
root=Path({INPUTS!r})
expected=json.loads(Path({(REMOTE_REPORT + '/transfer_sizes.json')!r}).read_text())
modality={modality!r}
if modality: expected={{p:n for p,n in expected.items() if p.startswith(modality+'/')}}
bad=[p for p,n in expected.items() if not (root/p).is_file() or (root/p).stat().st_size!=n]
result=dict(instance={node},files=len(expected),bytes=sum(expected.values()),bad_files=len(bad),examples=bad[:3],checked_epoch=time.time())
if not bad and modality is None: (root/'inputs_ready.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))'''
    return json.loads(remote_python(node, code))


def relay_modality(modality):
    # The four instances share this FS; keep only one modality there at a time.
    code = f'''from pathlib import Path
import json,shutil
src=Path({INPUTS!r})/{modality!r}; dst=Path({RELAY!r})/{modality!r}
dst.parent.mkdir(parents=True,exist_ok=True)
needed=sum(p.stat().st_size for p in src.iterdir())
if shutil.disk_usage(dst.parent).free < needed+2*1024**3: raise RuntimeError('Insufficient temporary shared space')
shutil.copytree(src,dst)
print('Relay ready')'''
    remote_python(6, code, timeout=3600)


def copy_peer(node, modality):
    code = f'''from pathlib import Path
import shutil
src=Path({RELAY!r})/{modality!r}; dst=Path({INPUTS!r})/{modality!r}
shutil.copytree(src,dst)
print('Peer copy complete')'''
    remote_python(node, code, timeout=3600)
    result = validate(node, modality)
    if result["bad_files"]:
        raise RuntimeError(f"Instance {node} size validation failed: {result}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--first-check-utc")
    args = parser.parse_args()
    uploads = json.loads((REPORT / "active_upload_processes.json").read_text())
    pending = {Path(x["command"].split()[-1]).stem.removeprefix("transfer_"): x for x in uploads}
    completed = []
    if args.first_check_utc:
        delay = datetime.fromisoformat(args.first_check_utc).timestamp() - time.time()
        if delay > 0:
            timer("TIMER_WAIT_UPLOAD_CHECK", delay)
    while pending:
        active = []
        for modality, upload in list(pending.items()):
            p = Path(f"/proc/{upload['pid']}/stat")
            try:
                fields = p.read_text().rsplit(")", 1)[1].split()
            except FileNotFoundError:
                fields = None
            if fields and fields[0] != "Z" and fields[19] == upload["starttime"]:
                active.append(upload["pid"])
                continue
            # Producer exit can precede draining the last SSH buffers.
            result = validate(6, modality)
            if result["bad_files"]:
                timer("TIMER_WAIT_SSH_DRAIN", 300, modality=modality)
                result = validate(6, modality)
            if result["bad_files"]:
                raise RuntimeError(f"Upload incomplete: {modality}: {result}")
            status("RELAYING_MODALITY_VIA_SHARED_FS", modality=modality, completed=completed)
            relay_modality(modality)
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                results = list(pool.map(lambda node: copy_peer(node, modality), [3, 4, 5]))
            remote_python(6, f"import shutil; shutil.rmtree({str(Path(RELAY) / modality)!r})")
            completed.append(modality)
            del pending[modality]
            status("MODALITY_READY_ON_ALL_FOUR", modality=modality, completed=completed)
        if pending:
            code = f'''from pathlib import Path
import json,time
root=Path({INPUTS!r}); expected=json.loads(Path({(REMOTE_REPORT + '/transfer_sizes.json')!r}).read_text())
present=sum(min((root/p).stat().st_size,n) for p,n in expected.items() if (root/p).is_file())
print(json.dumps(dict(present=present,total=sum(expected.values()),now=time.time())))'''
            progress = json.loads(remote_python(6, code))
            reference = json.loads((REPORT / "upload_estimate_reference.json").read_text())
            elapsed = max(1, progress["now"] - reference["epoch"])
            rate = max(1024**2, (progress["present"] - reference["bytes"]) / elapsed)
            delay = max(300, (progress["total"] - progress["present"]) / rate * 1.2 + 300)
            timer("TIMER_WAIT_UPLOAD_CHECK", delay, upload_pids=active, completed=completed,
                  progress=progress, estimated_bytes_per_second=rate)
    results = [validate(node) for node in [3, 4, 5, 6]]
    if any(x["bad_files"] for x in results):
        raise RuntimeError(f"Final input validation failed: {results}")
    status("ALL_FOUR_INPUTS_READY", instances=results)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        status("STOPPED_ERROR", error=f"{type(error).__name__}: {error}")
        raise
