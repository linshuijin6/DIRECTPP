"""Complete exact reference transport; CRC only locates blocks, SHA accepts arrays."""
import argparse,concurrent.futures,csv,hashlib,io,json,time,zipfile,zlib
from pathlib import Path
import numpy as np
import torch

OUT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('mode',choices=['requests','finalize']);a=p.parse_args()
rows=list(csv.DictReader((OUT/'mismatch_index.csv').open()));groups={}
for r in rows:groups.setdefault(r['ptid'],[]).append(r)
tasks=['fdg_fold1','fdg_fold2','av45_fold1','av45_fold2']
low={t:zipfile.ZipFile(OUT/t/'lowbits.zip') for t in tasks}
crc={t:zipfile.ZipFile(OUT/'crc'/t/'block_crc.zip') for t in tasks}
exceptions={t:zipfile.ZipFile(OUT/'exceptions'/t/'exceptions.zip') for t in tasks} if a.mode=='finalize' else {}
dest=OUT/('exact_patches' if a.mode=='finalize' else 'requests');dest.mkdir(exist_ok=False)
outputs={t:zipfile.ZipFile(dest/(('patches_' if a.mode=='finalize' else 'requests_')+t+'.zip'),'x',compression=zipfile.ZIP_STORED) for t in tasks}
root=Path('/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup')
torch.set_num_threads(2)


def work(rs):
    item=torch.load(root/rs[0]['cache_name'],map_location='cpu',weights_only=False);assert item['name']==rs[0]['ptid']
    result=[]
    for r in rs:
        t=r['tracer']+'_fold'+r['fold'];name=r['ptid']+'_'+r['tracer']+'.npz'
        canonical=item[r['tracer']].detach().cpu().numpy().squeeze().copy()
        assert hashlib.sha256(canonical.tobytes()).hexdigest()==r['canonical_sha256']
        bits=canonical.view(np.uint32)
        with np.load(io.BytesIO(low[t].read(name))) as z:plane=z['low']
        delta=((plane.astype(np.int16)-(bits&15).astype(np.int16)+8)%16)-8
        candidate=(bits.astype(np.int64)+delta).astype(np.uint32)
        with np.load(io.BytesIO(crc[t].read(name))) as z:checks=z['crc']
        view=memoryview(candidate.tobytes())
        local=np.fromiter((zlib.crc32(view[j:j+256]) for j in range(0,len(view),256)),dtype=np.uint32)
        bad=np.flatnonzero(local!=checks).astype(np.int32)
        audit={**r,'exception_blocks':len(bad),'total_blocks':len(checks)}
        buffer=io.BytesIO()
        if a.mode=='requests':
            np.savez_compressed(buffer,indices=bad)
        else:
            with np.load(io.BytesIO(exceptions[t].read(name))) as z:indices=z['indices'];values=z['values']
            assert np.array_equal(indices,bad) and values.dtype==np.float32
            candidate.reshape(-1,64)[indices]=values.view(np.uint32)
            assert hashlib.sha256(candidate.tobytes()).hexdigest()==r['base_sha256'], 'Exact reference SHA failed: '+name
            xor=np.bitwise_xor(bits,candidate)
            assert hashlib.sha256(np.bitwise_xor(candidate,xor).tobytes()).hexdigest()==r['canonical_sha256']
            np.savez_compressed(buffer,xor=xor)
            diff=canonical.astype(np.float64)-candidate.view(np.float32).astype(np.float64)
            audit.update(different_voxels=int(np.count_nonzero(xor)),max_abs_difference=float(np.max(np.abs(diff))),
                mean_abs_difference=float(np.mean(np.abs(diff))),max_ulp_difference=int(np.max(np.abs(bits.astype(np.int64)-candidate.astype(np.int64)))),
                reference_full_array_sha256_verified=True,canonical_full_array_sha256_verified=True)
        result.append((t,name,buffer.getvalue(),audit))
    return result


audits=[];start=time.time()
try:
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        for i,result in enumerate(pool.map(work,groups.values())):
            for t,name,data,audit in result:outputs[t].writestr(name,data);audits.append(audit)
            if i%40==0:print(json.dumps({'mode':a.mode,'subjects':i+1,'total':len(groups),'targets':len(audits),'seconds':time.time()-start}),flush=True)
finally:
    for z in list(outputs.values())+list(low.values())+list(crc.values())+list(exceptions.values()):z.close()
assert len(audits)==1401
if a.mode=='finalize':
    with (OUT/'exact_target_difference_audit.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(audits[0]));w.writeheader();w.writerows(audits)
    receipts={t:{'sha256':hashlib.sha256((dest/('patches_'+t+'.zip')).read_bytes()).hexdigest(),
        'bytes':(dest/('patches_'+t+'.zip')).stat().st_size,'targets':sum(r['tracer']+'_fold'+r['fold']==t for r in audits)} for t in tasks}
    (dest/'patch_receipts.json').write_text(json.dumps({'status':'PASS_EXACT_LOSSLESS_TARGET_TRANSPORT','targets':len(audits),'tasks':receipts,
        'max_abs_difference':max(r['max_abs_difference'] for r in audits),'max_ulp_difference':max(r['max_ulp_difference'] for r in audits),
        'acceptance':'Every full reference and canonical array matches SHA-256; CRC used only for transport block selection','source_arrays_unchanged':True},indent=2)+'\n')
else:
    (dest/'request_summary.json').write_text(json.dumps({'targets':len(audits),'exception_blocks':sum(r['exception_blocks'] for r in audits),'total_blocks':sum(r['total_blocks'] for r in audits)},indent=2)+'\n')
print(json.dumps({'status':'PASS','mode':a.mode,'targets':len(audits)}),flush=True)
