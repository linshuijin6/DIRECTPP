"""Evaluate existing baseline NIfTIs against frozen cached PET and frozen masks."""
import argparse
import csv
import hashlib
import io
import json
import sys
import socket
import time
import zipfile
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from scipy.ndimage import minimum_filter

PROJECT=Path('/root/autodl-tmp/DIRECTPP')
sys.path.insert(0,str(PROJECT/'source_archive/vscode-3002/home/ssddata/liutuo'))
from masked_metrics import metric_values


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for b in iter(lambda:stream.read(8*1024**2),b''):h.update(b)
    return h.hexdigest()


def run():
    p=argparse.ArgumentParser()
    p.add_argument('--tracer',required=True,choices=['fdg','av45'])
    p.add_argument('--fold',required=True,type=int,choices=[1,2])
    p.add_argument('--inputs',required=True,type=Path)
    p.add_argument('--output',required=True,type=Path)
    p.add_argument('--pilot',action='store_true')
    a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads((a.inputs/'input_manifest.json').read_text())
    ssim_sha=next(v for k,v in manifest['source_evidence'].items() if k.endswith('/generative/metrics/ssim.py'))
    ssim_source=PROJECT/'source_archive/vscode-3002/home/ssddata/liutuo/generative/metrics/ssim.py'
    assert sha(ssim_source)==ssim_sha
    torch.set_num_threads(2)
    torch.backends.cudnn.allow_tf32=False
    torch.backends.cuda.matmul.allow_tf32=False
    allrows=list(csv.DictReader((a.inputs/'input_index.csv').open()))
    rows=[r for r in allrows if r['model']!='Full' and r['tracer']==a.tracer and int(r['fold'])==a.fold]
    masks={r['ptid']:r for r in json.loads((a.inputs/'mask_transfer_manifest.json').read_text())}
    bundle_receipt=json.loads((a.inputs/'mask_bundle_receipt.json').read_text())
    bundle_bytes=(a.inputs/'frozen_mask_union.zip').read_bytes()
    assert hashlib.sha256(bundle_bytes).hexdigest()==bundle_receipt['sha256']
    bundle=zipfile.ZipFile(io.BytesIO(bundle_bytes))
    grouped={}
    for row in rows:grouped.setdefault(row['ptid'],[]).append(row)
    if a.pilot:
        grouped=dict(list(grouped.items())[:1])
    count=0;start=time.time();writer=None
    with (a.output/'metrics.csv').open('x',newline='') as stream,(a.output/'asset_checks.jsonl').open('x') as checks:
        for ptid,rs in grouped.items():
            m=masks[ptid];mask_bytes=bundle.read(ptid+'.npz')
            assert hashlib.sha256(mask_bytes).hexdigest()==m['packed_sha256']
            with np.load(io.BytesIO(mask_bytes)) as z:brain=np.unpackbits(z['packed']).reshape((160,192,160)).astype(bool)
            maskhash=hashlib.sha256(brain.tobytes()).hexdigest()
            assert maskhash==m['brain_mask_array_sha256'] and int(brain.sum())==m['mask_voxels']
            valid=minimum_filter(brain.astype(np.uint8),size=7,mode='constant',cval=0)[3:-3,3:-3,3:-3]>0
            cache=Path('/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3')/m['full_cache_name']
            item=torch.load(cache,map_location='cpu',weights_only=False)
            assert item['name']==ptid and int(item['test_fold'])==a.fold
            real=item[a.tracer].detach().cpu().numpy().squeeze().copy()
            targethash=hashlib.sha256(real.tobytes()).hexdigest()
            assert real.shape==brain.shape and np.isfinite(real).all() and 0<=real.min()<=real.max()<=1
            for r in rs:
                prediction=Path(r['prediction_original'])
                actual=sha(prediction)
                assert actual==r['prediction_sha256_expected']
                image=nib.load(prediction);pred=np.asarray(image.dataobj,dtype=np.float32)
                assert pred.shape==real.shape and np.isfinite(pred).all() and 0<=pred.min()<=pred.max()<=1
                values,whole=metric_values(real,pred,brain,valid,'cuda:0')
                output={'model':r['model'],'ptid':ptid,'tracer':a.tracer,'fold':a.fold,'epoch':int(r['epoch']),**values,
                    'mask_voxels':int(brain.sum()),'valid_ssim_centers':int(valid.sum()),'prediction':str(prediction),
                    'prediction_sha256':actual,'checkpoint_sha256':r['checkpoint_sha256'],
                    'target_array_sha256':targethash,'brain_mask_array_sha256':maskhash}
                if writer is None:writer=csv.DictWriter(stream,fieldnames=list(output));writer.writeheader()
                writer.writerow(output);stream.flush();count+=1
            checks.write(json.dumps({'ptid':ptid,'tracer':a.tracer,'fold':a.fold,'cache':str(cache),'cache_sha256':sha(cache),
                'target_array_sha256':targethash,'brain_mask_array_sha256':maskhash,'mask_source_npz_sha256':m['source_mask_cache_sha256']})+'\n');checks.flush()
            if count%40==0:print(json.dumps({'metric_rows':count,'expected_rows':len(rows),'elapsed_seconds':time.time()-start}),flush=True)
    expected_rows=2 if a.pilot else len(rows)
    assert count==expected_rows
    (a.output/'complete.json').write_text(json.dumps({'status':'COMPLETE_FROZEN_MASKED_EVALUATION','tracer':a.tracer,'fold':a.fold,
        'metric_rows':count,'metrics_sha256':sha(a.output/'metrics.csv'),'asset_checks_sha256':sha(a.output/'asset_checks.jsonl'),
        'host':socket.gethostname(),'python':sys.version,'torch':torch.__version__,
        'evaluator_sha256':sha(__file__),'shared_metrics_sha256':sha(Path(__file__).with_name('masked_metrics.py')),
        'ssim_source_sha256':ssim_sha,'input_index_sha256':sha(a.inputs/'input_index.csv'),
        'elapsed_seconds':time.time()-start,'pilot':a.pilot,'source_files_unchanged':True},indent=2)+'\n')


if __name__=='__main__':run()
