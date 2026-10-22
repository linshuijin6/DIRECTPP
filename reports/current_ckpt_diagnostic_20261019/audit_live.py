"""Read-only process/GPU identity receipt for the two already running fits."""
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime, timezone, timedelta

out = Path(__file__).resolve().parent
root = out.parents[1]
node = sys.argv[1]
label = sys.argv[2]
launch = json.loads((root / 'reports/e1_amp_recovery_20261018/launch_receipt.json').read_text())
job = next(j for j in launch['jobs'] if j['node'] == node)
pid = job['pid']
proc = Path('/proc') / str(pid)
cmd = proc.joinpath('cmdline').read_bytes().split(b'\0')
cmd = [c.decode() for c in cmd if c]
assert proc.stat().st_uid == os.getuid()
assert 'train' in cmd and 'e1_clinical_conditioning/run.py' in cmd[3]
assert cmd[cmd.index('--fold') + 1] == str(job['fold'])
assert cmd[cmd.index('--condition') + 1] == 'Full'
boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
start_ticks = int(proc.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19])
assert boot_id == job['boot_id'] and start_ticks == job['process_start_ticks']
gpu = job['gpu_uuid']
q = lambda args: subprocess.check_output(['nvidia-smi', '--id=' + gpu, *args], text=True).strip()
receipt = dict(timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),
               node=node, physical_gpu=job['physical_gpu'], gpu_uuid=gpu, pid=pid,
               queue_pid=job['queue_pid'], boot_id=boot_id, process_start_ticks=start_ticks,
               process_identity_matches_launch=True, cmdline=cmd,
               gpu=q(['--query-gpu=index,uuid,memory.used,memory.free,utilization.gpu', '--format=csv']),
               apps=q(['--query-compute-apps=gpu_uuid,pid,process_name,used_memory', '--format=csv']),
               status=proc.joinpath('status').read_text(),
               queues={p.name:p.read_text().strip() for p in Path(job['queue']).glob('*.exit')})
(out / f'live_{node}_{label}.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(node, pid, 'verified', receipt['queues'])
