"""Measure one outer-training fold's CPU cache; never constructs a network."""
import argparse
import json
import os
import resource
import socket
import time
from pathlib import Path
import torch
from common import active_rows,check_frozen,load_config,write_json
from run import get_data


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--config",type=Path,required=True);a=p.parse_args()
    cfg=load_config(a.config);check_frozen(cfg);torch.set_num_threads(4)
    rows=[r for r in active_rows(cfg,json.loads((Path(cfg["report"])/"cohort.json").read_text())) if r["test_fold"]!=1]
    required=len(rows)*3*160*192*160*4
    available=int(next(s.split()[1] for s in Path('/proc/meminfo').read_text().splitlines() if s.startswith('MemAvailable:')))*1024
    assert required<cfg['training_cache_budget_gib']*1024**3 and available>required+16*1024**3
    start=time.monotonic();cpu=time.process_time();cached={}
    for i,r in enumerate(rows):
        cached[r['ptid']]=get_data(r,device='cpu')
        if (i+1)%100==0:print('CPU cache',i+1,'/',len(rows),'elapsed',round(time.monotonic()-start),flush=True)
    payload=sum(t.numel()*t.element_size() for d in cached.values() for t in d.values())
    rss=int(next(s.split()[1] for s in Path('/proc/self/status').read_text().splitlines() if s.startswith('VmRSS:')))*1024
    assert payload==required and not torch.cuda.is_initialized()
    write_json(Path(cfg['report'])/'full_fold_cache_probe.json',dict(
        host=socket.gethostname(),pid=os.getpid(),fold=1,training_subjects=len(rows),
        outer_test_overlap=0,array_payload_bytes=payload,measured_resident_bytes=rss,
        peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
        wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu,
        available_memory_before_bytes=available,torch_threads=4,
        cuda_initialized=False,model_constructed=False,optimization_performed=False))
    print('Full-fold CPU cache measured; arrays released on exit',flush=True)
