"""Stop only the identity-verified author TAU task selected for this E1 queue."""
import json
import os
from pathlib import Path
import pwd
import signal
import subprocess
import time

pid=2296316
expected='/mnt/nfsdata/nfsdata/linshuijin/replicaLT/analysis/tau_suvrnorm_3fold_20261013/fold_0/round_2/configs/s2_bound.yaml'
uuid='GPU-4e00852f-6d7a-af71-10b5-1c59593a6681'
p=Path('/proc')/str(pid);cmd=p.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode()
assert expected in cmd and 'plasma_train.py' in cmd and p.stat().st_uid==os.getuid()
gpus=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid','--format=csv,noheader'],text=True)
assert any(uuid in l and l.split(',')[1].strip()==str(pid) for l in gpus.splitlines())
children=[];pending=[pid]
while pending:
 parent=pending.pop()
 for proc in Path('/proc').iterdir():
  if not proc.name.isdigit():continue
  try:
   status=proc.joinpath('status').read_text();ppid=int(next(l.split()[1] for l in status.splitlines() if l.startswith('PPid:')))
   if ppid==parent and proc.stat().st_uid==os.getuid():children.append(int(proc.name));pending.append(int(proc.name))
  except (FileNotFoundError,ProcessLookupError,PermissionError,StopIteration):pass
receipt=dict(node='3002',gpu_uuid=uuid,pid=pid,user=pwd.getpwuid(os.getuid()).pw_name,cmdline=cmd,start_stat=p.joinpath('stat').read_text(),owned_descendants=children,action='SIGTERM only exact author task and descendants',preserved_tau_pid=2306716,timestamp=time.time())
for target in [pid]+children:
 try:os.kill(target,signal.SIGTERM)
 except ProcessLookupError:pass
Path(__file__).with_name('resource_handoff_3002.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('SIGTERM verified TAU fold0', [pid]+children)
