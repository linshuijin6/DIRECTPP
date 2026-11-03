"""Re-evaluate frozen predictions using exact, hash-verified canonical PET.

XOR decoding only restores bytes read from the frozen Full PET cache. It does
not normalize, resample, register, or generate any PET prediction.
"""
import argparse,csv,hashlib,io,json,socket,sys,time,zipfile
from pathlib import Path
import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import minimum_filter
from remote_evaluate import metric_values,sha,PROJECT

p=argparse.ArgumentParser();p.add_argument('--tracer',required=True);p.add_argument('--fold',type=int,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--patches',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
torch.set_num_threads(2);torch.backends.cudnn.allow_tf32=False;torch.backends.cuda.matmul.allow_tf32=False
ssim_source=PROJECT/'source_archive/vscode-3002/home/ssddata/liutuo/generative/metrics/ssim.py'
manifest=json.loads((a.inputs/'input_manifest.json').read_text())
ssim_sha=next(v for k,v in manifest['source_evidence'].items() if k.endswith('/generative/metrics/ssim.py'))
assert sha(ssim_source)==ssim_sha
task=a.tracer+'_fold'+str(a.fold)
patch_receipt=json.loads((a.patches/'patch_receipts.json').read_text())['tasks'][task]
patch_bytes=(a.patches/('patches_'+task+'.zip')).read_bytes()
assert hashlib.sha256(patch_bytes).hexdigest()==patch_receipt['sha256']
patches=zipfile.ZipFile(io.BytesIO(patch_bytes))
mask_bytes=(a.inputs/'frozen_mask_union.zip').read_bytes()
assert hashlib.sha256(mask_bytes).hexdigest()==json.loads((a.inputs/'mask_bundle_receipt.json').read_text())['sha256']
masks=zipfile.ZipFile(io.BytesIO(mask_bytes))
mask_index={r['ptid']:r for r in json.loads((a.inputs/'mask_transfer_manifest.json').read_text())}
requests=[r for r in csv.DictReader((a.inputs/'mismatch_index.csv').open()) if r['tracer']==a.tracer and int(r['fold'])==a.fold]
predictions=[r for r in csv.DictReader((a.inputs/'input_index.csv').open()) if r['model']!='Full' and r['tracer']==a.tracer and int(r['fold'])==a.fold]
by_ptid={}
for r in predictions:by_ptid.setdefault(r['ptid'],[]).append(r)
start=time.time();count=0;writer=None
with (a.out/'metrics.csv').open('x',newline='') as stream,(a.out/'asset_checks.jsonl').open('x') as checks:
    for req in requests:
        ptid=req['ptid'];mask_record=mask_index[ptid]
        packed=masks.read(ptid+'.npz');assert hashlib.sha256(packed).hexdigest()==mask_record['packed_sha256']
        with np.load(io.BytesIO(packed)) as z:brain=np.unpackbits(z['packed']).reshape((160,192,160)).astype(bool)
        brainhash=hashlib.sha256(brain.tobytes()).hexdigest();assert brainhash==mask_record['brain_mask_array_sha256']
        valid=minimum_filter(brain.astype(np.uint8),size=7,mode='constant',cval=0)[3:-3,3:-3,3:-3]>0
        path=Path('/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3')/req['cache_name']
        cached=torch.load(path,map_location='cpu',weights_only=False)
        assert cached['name']==ptid and int(cached['test_fold'])==a.fold
        base=cached[a.tracer].detach().cpu().numpy().squeeze().copy()
        assert base.dtype==np.float32 and hashlib.sha256(base.tobytes()).hexdigest()==req['base_sha256']
        patch_member=patches.read(ptid+'_'+a.tracer+'.npz')
        with np.load(io.BytesIO(patch_member)) as z:xor=z['xor']
        assert xor.dtype==np.uint32 and xor.shape==base.shape
        real=np.bitwise_xor(base.view(np.uint32),xor).view(np.float32)
        targethash=hashlib.sha256(real.tobytes()).hexdigest();assert targethash==req['canonical_sha256']
        assert np.isfinite(real).all() and 0<=real.min()<=real.max()<=1
        for row in by_ptid[ptid]:
            prediction=Path(row['prediction_original']);actual=sha(prediction)
            assert actual==row['prediction_sha256_expected']
            pred=np.asarray(nib.load(prediction).dataobj,dtype=np.float32)
            assert pred.shape==real.shape and np.isfinite(pred).all()
            values,_=metric_values(real,pred,brain,valid,'cuda:0')
            result={'model':row['model'],'ptid':ptid,'tracer':a.tracer,'fold':a.fold,'epoch':int(row['epoch']),**values,
                'mask_voxels':int(brain.sum()),'valid_ssim_centers':int(valid.sum()),'prediction':str(prediction),
                'prediction_sha256':actual,'checkpoint_sha256':row['checkpoint_sha256'],
                'target_array_sha256':targethash,'brain_mask_array_sha256':brainhash}
            if writer is None:writer=csv.DictWriter(stream,fieldnames=list(result));writer.writeheader()
            writer.writerow(result);stream.flush();count+=1
        checks.write(json.dumps({**req,'decoded_target_sha256':targethash,'brain_mask_array_sha256':brainhash,'patch_member_sha256':hashlib.sha256(patch_member).hexdigest(),'exact_canonical_bytes_verified_before_evaluation':True})+'\n');checks.flush()
        if count%40==0:print(json.dumps({'metric_rows':count,'expected':2*len(requests),'seconds':time.time()-start}),flush=True)
assert count==2*len(requests)
(a.out/'complete.json').write_text(json.dumps({'status':'COMPLETE_EXACT_CANONICAL_TARGET_RECHECK','metric_rows':count,'targets':len(requests),
    'metrics_sha256':sha(a.out/'metrics.csv'),'asset_checks_sha256':sha(a.out/'asset_checks.jsonl'),
    'evaluator_sha256':sha(__file__),'metrics_helper_sha256':sha(Path(__file__).with_name('masked_metrics.py')),
    'ssim_source_sha256':ssim_sha,'host':socket.gethostname(),'torch':torch.__version__,'elapsed_seconds':time.time()-start,
    'source_arrays_modified':False,'new_predictions_generated':False},indent=2)+'\n')
