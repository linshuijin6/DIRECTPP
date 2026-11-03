"""Same frozen Single inference protocol, writing exclusively new report assets."""
import argparse,sys,json,time,hashlib,subprocess
from pathlib import Path
import numpy as np
import torch,nibabel as nib
from torch.utils.data import DataLoader
from monai.metrics import PSNRMetric

p=argparse.ArgumentParser(); p.add_argument('--task',required=True); p.add_argument('--out',required=True)
a=p.parse_args(); root=Path('/root/autodl-tmp/DIRECTPP')
sys.path.insert(0,str(root/'experiments/baselines/direct_single'))
import run as native
cfg_path=root/'reports/direct_single_2fold_20261030'/a.task/'config.json'
cfg,cohort=native.load_config(cfg_path)
native.validate_cache(cfg,cohort)
if not (Path(cfg['report'])/'training_complete.json').is_file():
    # Prior user authorization ended FDG after the prespecified165 milestone.
    policy=json.loads((root/'reports/revision_evidence_night_20261102/code/single_endpoint_policy.json').read_text())
    item=next(x for x in policy['instances'] if x['checkpoint165']['task']==a.task)
    assert item['user_stop_receipt']['requested_policy']=='user_stop_after_saved_epoch165'
    assert item['user_stop_receipt']['verified_epoch']==165 and item['checkpoint165']['checkpoint_readable']
assert cfg['primary_epoch']==165
cp=Path(cfg['assets'])/'formal/checkpoint_epoch165.pt'
receipt=json.loads(cp.with_suffix('.json').read_text())
assert native.sha256(cp)==receipt['checkpoint_sha256']
state=torch.load(cp,map_location='cpu',weights_only=False)
assert all(state.get(k)==v for k,v in native.checkpoint_identity(cfg).items())
free,total=torch.cuda.mem_get_info(); assert free>44*1024**3
gpu=subprocess.check_output(['nvidia-smi','--query-compute-apps=pid','--format=csv,noheader'],text=True).strip()
# This Python process may own an initialized CUDA context; other PIDs block.
import os
assert not any(int(x.strip())!=os.getpid() for x in gpu.splitlines() if x.strip().isdigit()),gpu
out=Path(a.out); out.mkdir(parents=True,exist_ok=False)
conditions=native.prepared_conditions(cfg,cohort)
model=native.build_model().cuda().eval(); model.load_state_dict(state['model'])
sys.path.insert(0,str(native.AUTHOR_ROOT)); from generative.metrics import SSIMMetric
tracer,fold=cfg['tracer'],cfg['fold']
rows=[r for r in cohort if int(r['test_fold'])==fold and native.valid_target(r,tracer)]
loader=DataLoader(native.FullCacheDataset(rows,Path(cfg['cache']['path'])),batch_size=1,shuffle=False,num_workers=0,pin_memory=True)
ssim=SSIMMetric(spatial_dims=3,data_range=1.0,kernel_size=7); psnr=PSNRMetric(max_val=1.)
metrics=[]; started=time.time()
with torch.inference_mode():
    for batch in loader:
        sid=batch['name'][0]; mri=batch['mri'].cuda(); target=batch[tracer.lower()].cuda()
        context=native.context_for(batch,conditions,tracer)
        velocity=model(x=mri,timesteps=torch.zeros(1,device='cuda',dtype=torch.long),context=context)
        pred=torch.clamp(mri+velocity.float(),0,1)
        affine=batch['affine'][0].numpy() if isinstance(batch['affine'],torch.Tensor) else np.asarray(batch['affine'][0])
        image=out/f'generated_{tracer}_{sid}.nii.gz'
        nib.save(nib.Nifti1Image(pred.squeeze().cpu().numpy(),affine),image)
        metrics.append(dict(ptid=sid,tracer=tracer.lower(),fold=fold,epoch=165,
            ssim=float(ssim(pred,target).mean()),psnr=float(psnr(pred,target).mean()),
            mse=float(torch.nn.functional.mse_loss(pred,target.float())),mae=float(torch.nn.functional.l1_loss(pred,target.float())),
            prediction=str(image),prediction_sha256=native.sha256(image),checkpoint_sha256=receipt['checkpoint_sha256']))
        if len(metrics)%50==0: print(json.dumps(dict(done=len(metrics),total=len(rows),seconds=time.time()-started)),flush=True)
assert len(metrics)==cfg['heldout_metric_rows']
native.csv_write(out/'metrics.csv',metrics)
native.json_write(out/'completion.json',dict(status='COMPLETE_FOLD_OOF',task=a.task,epoch=165,metric_rows=len(metrics),
    metrics_sha256=native.sha256(out/'metrics.csv'),checkpoint_sha256=receipt['checkpoint_sha256'],
    config_sha256=native.sha256(cfg_path),seconds=time.time()-started,protocol='native command_infer; float32; clamp[0,1]; single tracer forward; outputs isolated',
    gpu=torch.cuda.get_device_name(),peak_allocated=torch.cuda.max_memory_allocated(),peak_reserved=torch.cuda.max_memory_reserved()))
print('COMPLETE',a.task,flush=True)
