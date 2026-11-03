"""Lossless-reference transport: export float32 low bits plus full-array hash.

The receiving side must reconstruct and verify the exact full reference hash;
the low bits alone are never accepted as a replacement PET array.
"""
import argparse,csv,hashlib,io,json,time,zipfile
from pathlib import Path
import numpy as np
import torch

p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--tracer',required=True);p.add_argument('--fold',type=int,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
rows=[r for r in csv.DictReader(a.index.open()) if r['tracer']==a.tracer and int(r['fold'])==a.fold]
torch.set_num_threads(2);start=time.time()
with zipfile.ZipFile(a.out/'lowbits.zip','x',compression=zipfile.ZIP_STORED) as packet:
    for i,r in enumerate(rows):
        path=Path('/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3')/r['cache_name']
        item=torch.load(path,map_location='cpu',weights_only=False)
        assert item['name']==r['ptid'] and int(item['test_fold'])==a.fold
        real=item[a.tracer].detach().cpu().numpy().squeeze().copy()
        assert real.dtype==np.float32 and real.shape==(160,192,160)
        assert hashlib.sha256(real.tobytes()).hexdigest()==r['base_sha256']
        buffer=io.BytesIO();np.savez_compressed(buffer,low=(real.view(np.uint32)&15).astype(np.uint8))
        packet.writestr(r['ptid']+'_'+r['tracer']+'.npz',buffer.getvalue())
        if i%40==0:print(json.dumps({'encoded':i+1,'total':len(rows)}),flush=True)
    packet.writestr('manifest.json',json.dumps(rows))
receipt={'status':'COMPLETE_REFERENCE_ENCODING','targets':len(rows),'low_bits':4,'array_dtype':'float32','sha256':hashlib.sha256((a.out/'lowbits.zip').read_bytes()).hexdigest(),'bytes':(a.out/'lowbits.zip').stat().st_size,'elapsed_seconds':time.time()-start,'source_files_modified':False}
(a.out/'complete.json').write_text(json.dumps(receipt,indent=2)+'\n')
