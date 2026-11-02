import json,pathlib,time,sys,os,statistics,torch,torch.nn.functional as F
repo=pathlib.Path("/root/autodl-tmp/DIRECTPP"); exp=repo/"experiments/baselines/swinunetr"
sys.path.insert(0,str(exp)); from model import build_model,parameter_count; from run import train_step,hardware
barrier=pathlib.Path(sys.argv[1]); tag=sys.argv[2]
shape=(1,1,160,192,160); gen=torch.Generator(device="cpu").manual_seed(20261029+(1 if tag.endswith("2") else 0))
model=build_model(use_checkpoint=True).cuda().train(); opt=torch.optim.Adam(model.parameters(),lr=1e-5); scaler=torch.amp.GradScaler("cuda")
ready=pathlib.Path(str(barrier)+"."+tag+".ready"); ready.write_text("ready")
deadline=time.time()+180
while not barrier.exists():
 if time.time()>deadline: raise TimeoutError("parallel barrier timed out")
 time.sleep(.02)
torch.cuda.synchronize(); torch.cuda.reset_peak_memory_stats(); times=[]; losses=[]; started=time.perf_counter()
for i in range(5):
 mri=torch.rand(shape,generator=gen,dtype=torch.float32).cuda(); target=torch.rand(shape,generator=gen,dtype=torch.float32).cuda()
 torch.cuda.synchronize(); t=time.perf_counter(); loss=train_step(model,{"mri":mri,"target":target},opt,scaler,torch,F); torch.cuda.synchronize(); dt=time.perf_counter()-t
 losses.append(loss)
 if i>=1: times.append(dt)
 del mri,target
out={"tag":tag,"status":"PASS","shape":list(shape),"parameters":parameter_count(model),"steps":5,"warmup":1,"measured_seconds":times,"median_seconds":statistics.median(times),"mean_seconds":statistics.mean(times),"wall_seconds":time.perf_counter()-started,"peak_allocated_bytes":torch.cuda.max_memory_allocated(),"peak_reserved_bytes":torch.cuda.max_memory_reserved(),"losses_finite":all(torch.isfinite(torch.tensor(losses))),"losses":losses}
pathlib.Path(str(barrier)+"."+tag+".json").write_text(json.dumps(out,indent=2)+"\n"); print(json.dumps(out,indent=2))
