"""Collect one first-five-update receipt, then stop; no monitoring loop."""
import argparse
from datetime import datetime,timezone
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/e1_clinical_conditioning'))
from common import load_config,sha,write_json
p=argparse.ArgumentParser();p.add_argument('--node',required=True);p.add_argument('--fold',required=True,type=int);a=p.parse_args()
cfg=load_config(ROOT/'reports/e1_stage01_20261017/config.json');report=Path(cfg['execution_report'])
q=report/'queues'/f'{a.node}_fold{a.fold}';pid=int((q/'Full.pid').read_text());proc=Path('/proc')/str(pid)
folder=Path(cfg['assets'])/'formal'/f'fold{a.fold}_Full';start=json.loads((folder/'start.json').read_text());five=json.loads((folder/'startup_5_updates.json').read_text())
assert five['pid']==pid and start['pid']==pid and five['optimizer_updates']==5 and math.isfinite(five['loss'])
assert five['config_sha256']==sha(Path(cfg['report'])/'config.json')==start['config_sha256']
cmd=proc.joinpath('cmdline').read_bytes().replace(b'\0',b' ').decode();assert 'run.py train' in cmd and '--condition Full' in cmd
uuid=start['hardware']['visible_devices'];apps=subprocess.check_output(['nvidia-smi','--query-compute-apps=gpu_uuid,pid,used_memory','--format=csv,noheader'],text=True)
assert any(uuid in l and l.split(',')[1].strip()==str(pid) for l in apps.splitlines())
rss={l.split(':')[0]:l.split(':')[1].strip() for l in proc.joinpath('status').read_text().splitlines() if l.startswith(('VmRSS:','VmHWM:'))}
start_ticks=int(proc.joinpath('stat').read_text().split()[21])
boot_time=int(next(l.split()[1] for l in Path('/proc/stat').read_text().splitlines() if l.startswith('btime ')))
write_json(report/f'startup_{a.node}.json',dict(node=a.node,fold=a.fold,condition='Full',pid=pid,queue_pid=int((q/'queue.pid').read_text()),
 process_start_ticks=start_ticks,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
 process_start_time_utc=datetime.fromtimestamp(boot_time+start_ticks/os.sysconf('SC_CLK_TCK'),timezone.utc).isoformat(),cmdline=cmd,gpu_uuid=uuid,
 config_sha256=five['config_sha256'],initial_model_sha256=start['initial_model_sha256'],
 first_five_updates_pass=True,process_alive_at_collection=True,collected_unix_time=time.time(),
 start=start,first_five=five,host_memory=rss,
 log=str(report/'logs'/f'{a.node}_fold{a.fold}_Full.log'),queue=str(q),asset_root=cfg['assets'],
 next_condition='No-Scores',next_condition_status='QUEUED',monitoring_handed_to='Gemini'))
print(a.node,'Full first-five actual updates PASS, PID',pid,'GPU',uuid)
