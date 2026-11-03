"""Reconstruct exact remote references by hash, then encode canonical PET XOR.

This is lossless array transport, not PET normalization or resampling. Every
reference reconstruction and every canonical reconstruction must match SHA-256.
"""
import concurrent.futures,csv,hashlib,io,json,time,zipfile
from pathlib import Path
import numpy as np
import torch

OUT=Path(__file__).resolve().parent
RUN=OUT.parent
rows=list(csv.DictReader((OUT/'mismatch_index.csv').open()))
by_subject={}
for r in rows:by_subject.setdefault(r['ptid'],[]).append(r)
torch.set_num_threads(2)
packets={name:zipfile.ZipFile(OUT/name/'lowbits.zip') for name in ['fdg_fold1','fdg_fold2','av45_fold1','av45_fold2']}
outputs={name:zipfile.ZipFile(OUT/('patches_'+name+'.zip'),'x',compression=zipfile.ZIP_STORED) for name in packets}
cache_root=Path('/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup')


def process(rs):
    item=torch.load(cache_root/rs[0]['cache_name'],map_location='cpu',weights_only=False)
    assert item['name']==rs[0]['ptid']
    results=[]
    for r in rs:
        task=r['tracer']+'_fold'+r['fold']
        canonical=item[r['tracer']].detach().cpu().numpy().squeeze().copy()
        assert canonical.dtype==np.float32 and hashlib.sha256(canonical.tobytes()).hexdigest()==r['canonical_sha256']
        with np.load(io.BytesIO(packets[task].read(r['ptid']+'_'+r['tracer']+'.npz'))) as z:low=z['low']
        bits=canonical.view(np.uint32)
        nearest_delta=((low.astype(np.int16)-(bits&15).astype(np.int16)+8)%16)-8
        reference=(bits.astype(np.int64)+nearest_delta).astype(np.uint32)
        actual=hashlib.sha256(reference.tobytes()).hexdigest()
        if actual!=r['base_sha256']:
            raise RuntimeError('Low-bit reference reconstruction failed; no target accepted: '+r['ptid']+' '+r['tracer'])
        xor=np.bitwise_xor(bits,reference)
        restored=np.bitwise_xor(reference,xor)
        assert hashlib.sha256(restored.tobytes()).hexdigest()==r['canonical_sha256']
        buffer=io.BytesIO();np.savez_compressed(buffer,xor=xor)
        diff=canonical.astype(np.float64)-reference.view(np.float32).astype(np.float64)
        audit={**r,'different_voxels':int(np.count_nonzero(xor)),
            'max_abs_difference':float(np.max(np.abs(diff))),'mean_abs_difference':float(np.mean(np.abs(diff))),
            'max_ulp_difference':int(np.max(np.abs(nearest_delta))),
            'reference_full_array_sha256_verified':True,'canonical_full_array_sha256_verified':True}
        results.append((task,r['ptid']+'_'+r['tracer']+'.npz',buffer.getvalue(),audit))
    return results


start=time.time();audits=[]
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,result in enumerate(pool.map(process,by_subject.values())):
            for task,name,data,audit in result:
                outputs[task].writestr(name,data);audits.append(audit)
            if i%40==0:print(json.dumps({'subjects':i+1,'total':len(by_subject),'targets':len(audits),'seconds':time.time()-start}),flush=True)
finally:
    for z in outputs.values():z.close()
    for z in packets.values():z.close()
assert len(audits)==1401
with (OUT/'exact_target_difference_audit.csv').open('x',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(audits[0]));w.writeheader();w.writerows(audits)
receipts={name:{'sha256':hashlib.sha256((OUT/('patches_'+name+'.zip')).read_bytes()).hexdigest(),
                'bytes':(OUT/('patches_'+name+'.zip')).stat().st_size,
                'targets':sum(r['tracer']+'_fold'+r['fold']==name for r in audits)} for name in outputs}
(OUT/'patch_receipts.json').write_text(json.dumps({'status':'PASS_EXACT_LOSSLESS_TARGET_TRANSPORT','tasks':receipts,
    'targets':len(audits),'max_abs_difference':max(r['max_abs_difference'] for r in audits),
    'max_ulp_difference':max(r['max_ulp_difference'] for r in audits),'source_arrays_unchanged':True},indent=2)+'\n')
print(json.dumps({'status':'PASS','targets':len(audits),'patch_bytes':sum(r['bytes'] for r in receipts.values())}),flush=True)
