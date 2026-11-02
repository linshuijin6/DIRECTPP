import json, pathlib, tempfile, time, statistics, sys, os
import torch
import torch.nn.functional as F
repo=pathlib.Path("/root/autodl-tmp/DIRECTPP")
sys.path.insert(0,str(repo/"experiments/baselines/swinunetr"))
from model import build_model, parameter_count
from run import train_step, save_recovery, hardware
cfg=json.load(open(repo/"reports/swinunetr_2fold_20261029/config.json"))
assert torch.cuda.is_available()
assert torch.cuda.get_device_name(0)=="NVIDIA GeForce RTX 4090"
shape=(1,1,160,192,160)
gen=torch.Generator(device="cpu").manual_seed(20261029)
model=build_model(use_checkpoint=True).cuda().train()
opt=torch.optim.Adam(model.parameters(),lr=1e-5)
scaler=torch.amp.GradScaler("cuda")
torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats()
times=[]; losses=[]
for i in range(5):
    mri=torch.rand(shape,generator=gen,dtype=torch.float32).cuda()
    target=torch.rand(shape,generator=gen,dtype=torch.float32).cuda()
    torch.cuda.synchronize(); t=time.perf_counter()
    loss=train_step(model,{"mri":mri,"target":target},opt,scaler,torch,F)
    torch.cuda.synchronize(); dt=time.perf_counter()-t
    if not (loss==loss and abs(loss)<float("inf")): raise RuntimeError("nonfinite loss")
    losses.append(loss)
    if i>=1: times.append(dt)
    del mri,target
params=parameter_count(model)
with tempfile.TemporaryDirectory(prefix="swinunetr_synth_cost_") as td:
    p=pathlib.Path(td)/"weights.pt"; torch.save(model.state_dict(),p); weight_bytes=p.stat().st_size
    q=pathlib.Path(td)/"recovery.pt"
    save_recovery(q,model,opt,scaler,0,{"synthetic_preflight":True},torch)
    recovery_bytes=q.stat().st_size
med=statistics.median(times)
counts=cfg["training_subjects_by_tracer_fold"]
est={}; total=0
for tr in ("FDG","AV45"):
    for fold in (1,2):
        steps=int(counts[tr][str(fold)])*800
        sec=steps*med; total+=sec
        est[f"{tr}_fold{fold}"]={"optimizer_updates":steps,"hours":sec/3600}
out={"status":"SYNTHETIC_TRAIN_STEP_PASS","scope":"5 synthetic full-volume optimizer updates; one warmup + four measured; not formal preflight or experiment","hardware":hardware(torch),"shape":list(shape),"dtype":"float32","model_parameters":params,"activation_checkpointing":True,"amp":"float16 autocast + GradScaler","optimizer":"Adam lr=1e-5","loss":"MSE","losses_finite":True,"loss_values":losses,"all_step_seconds":times,"step_median_seconds":med,"step_mean_seconds":statistics.mean(times),"peak_allocated_bytes":torch.cuda.max_memory_allocated(),"peak_reserved_bytes":torch.cuda.max_memory_reserved(),"weight_checkpoint_bytes":weight_bytes,"rolling_recovery_bytes":recovery_bytes,"persistent_milestones":4,"estimated_storage_per_instance_bytes":4*weight_bytes+recovery_bytes,"estimated_storage_four_instances_bytes":4*(4*weight_bytes+recovery_bytes),"training_estimates":est,"fdg_fold1_hours":est["FDG_fold1"]["hours"],"all_four_hours":total/3600,"synthetic_seed":20261029,"heldout_accessed":False,"formal_outputs_written":False}
path=pathlib.Path("/tmp/swinunetr_synthetic_cost_result.json")
path.write_text(json.dumps(out,indent=2)+"\n")
print(json.dumps(out,indent=2))
