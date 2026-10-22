"""One-off read-only asset verification; writes only a new launch receipt."""
import argparse
import json
import os
from pathlib import Path
import socket
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/e1_clinical_conditioning'))
from common import active_rows,check_frozen,load_config,sha,write_json

p=argparse.ArgumentParser();p.add_argument('--receipt',type=Path,required=True);p.add_argument('--wait-for-copy',action='store_true');a=p.parse_args()
cfg=load_config(ROOT/'reports/e1_stage01_20261017/config.json');check_frozen(cfg)
rows=active_rows(cfg,json.loads((Path(cfg['report'])/'cohort.json').read_text()))
missing=[r['ptid'] for r in rows if not Path(r['cache']).is_file()]
if missing and not a.wait_for_copy:raise RuntimeError(f'Copy incomplete: {len(missing)} active subject files absent')
started=time.monotonic();total=0
for i,row in enumerate(rows):
 while not Path(row['cache']).is_file():
  if not a.wait_for_copy or time.monotonic()-started>1800:raise RuntimeError('Input copy did not finish within the preparation window')
  time.sleep(2)
 assert sha(row['cache'])==row['cache_sha256'],f"Cache SHA mismatch: {row['ptid']}"
 total+=Path(row['cache']).stat().st_size
 if (i+1)%400==0:print('Verified',i+1,'/',len(rows),flush=True)
conditions=Path(cfg['assets'])/'conditions';index=json.loads((conditions/'index.json').read_text())
assert {r['ptid'] for r in rows}<=set(index['ptids'])
for name,digest in index['files'].items():assert sha(conditions/name)==digest
for fold in [1,2]:
 d=conditions/cfg['adapter_subdir'];r=json.loads((d/f'adapter_fold{fold}.json').read_text())
 assert sha(d/f'adapter_fold{fold}.npy')==r['sha256']
 test={x['ptid'] for x in rows if x['test_fold']==fold};assert set(r['outer_test_ptids'])==test
 for tracer in ['fdg','av45']:
  expected={x['ptid'] for x in rows if x['test_fold']!=fold and x['has_'+tracer]}
  assert set(r['fit_ptids'][tracer])==expected and not expected&test
  assert sha(Path(cfg['assets'])/'pet_features'/f'{tracer}.npy')==r['feature_hashes'][tracer]
write_json(a.receipt,dict(host=socket.gethostname(),asset_root=cfg['assets'],active_subjects=len(rows),
 cache_files_sha_pass=True,cache_bytes=total,conditions_sha_pass=True,adapter_identity_pass=True,
 wall_seconds=time.monotonic()-started,config_sha256=sha(Path(cfg['report'])/'config.json'),gpu_used=False))
print('Complete active assets SHA/identity PASS',flush=True)
