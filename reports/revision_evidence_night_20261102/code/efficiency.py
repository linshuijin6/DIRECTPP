"""Frozen real-input Full forward benchmark; no optimizer or output mutation."""
from pathlib import Path
import sys,json,time,os,platform,hashlib,subprocess
import numpy as np,pandas as pd,torch
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102/G6';OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'experiments/original_author_reproduction'))
import run as full
cfg,cohort=full.load_config(ROOT/'reports/original_author_reproduction_20261020/config.json')
checkpoint=Path(cfg['assets'])/'formal/fold1/first_part_165.pth';receipt=json.loads(checkpoint.with_suffix('.json').read_text());assert full.sha256(checkpoint)==receipt['checkpoint_sha256']
idx=pd.read_csv(ROOT/'reports/r3_11_brain_mask_metrics/run_20261102/input_index.csv');row=idx[(idx.model=='Full')&(idx.fold==1)&(idx.tracer=='fdg')].sort_values('ptid').iloc[0]
data=torch.load(row.target_cache,map_location='cpu',weights_only=False)
assert data['name']==row.ptid and torch.cuda.is_available()
free,total=torch.cuda.mem_get_info();assert free>22*1024**3
model=full.new_model().cuda().eval();state=torch.load(checkpoint,map_location='cpu',weights_only=False);model.load_state_dict(state['model']);del state
mri=data['mri'].unsqueeze(0).cuda();t=torch.zeros(1,device='cuda',dtype=torch.long)
parameters=sum(p.numel() for p in model.parameters())
times=[];memory=[];checks=[]
with torch.inference_mode():
    for tracer in ('fdg','av45'):
        context=data[tracer+'_index'].unsqueeze(0).cuda()
        def forward(): return torch.clamp(mri+model(x=mri,timesteps=t,context=context),0,1).float()
        for _ in range(10):forward()
        torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats()
        outputs=[]
        for repeat in range(50):
            torch.cuda.synchronize();start=time.perf_counter();pred=forward();torch.cuda.synchronize();duration=time.perf_counter()-start
            times.append(dict(tracer=tracer,repeat=repeat,seconds=duration));
            if repeat<2:outputs.append(pred.cpu().numpy())
        checks.append(dict(tracer=tracer,same_input_repeat_max_abs=float(np.abs(outputs[0]-outputs[1]).max())))
        memory.append(dict(tracer=tracer,peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved()))
pd.DataFrame(times).to_csv(OUT/'latency_samples.csv',index=False)
summary=[]
for tracer,s in pd.DataFrame(times).groupby('tracer'):
    v=s.seconds.to_numpy();summary.append(dict(model='Full',tracer=tracer,n=len(v),mean_s=v.mean(),sample_sd_s=v.std(ddof=1),median_s=np.median(v),p05_s=np.quantile(v,.05),p95_s=np.quantile(v,.95),parameters=parameters,**{k:v for k,v in next(m for m in memory if m['tracer']==tracer).items() if k!='tracer'}))
pd.DataFrame(summary).to_csv(OUT/'summary.csv',index=False)
(OUT/'receipt.json').write_text(json.dumps(dict(status='COMPLETE',checkpoint=str(checkpoint),checkpoint_sha256=receipt['checkpoint_sha256'],input_ptid=row.ptid,input_cache=row.target_cache,input_cache_sha256=full.sha256(Path(row.target_cache)),shape=list(mri.shape),device=torch.cuda.get_device_name(),gpu_query=subprocess.check_output(['nvidia-smi','--query-gpu=uuid,name,driver_version','--format=csv,noheader'],text=True),python=sys.executable,torch=torch.__version__,numpy=np.__version__,hostname=platform.node(),precision='float32; native attention backend',warmup=10,repeats=50,includes='GPU-resident MRI + cached clinical/tracer embeddings; one tracer per forward, residual+clamp; synchronized wall clock',excludes='text encoding, preprocessing, disk I/O, host-device copy, NIfTI writes',determinism=checks,flops='unavailable: no verified operator-complete MAC/FLOP counter; not inferred from parameter count'),indent=2))
print(json.dumps(summary,indent=2),flush=True)
