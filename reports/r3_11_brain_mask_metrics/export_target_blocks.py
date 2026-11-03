"""Export reference-block checksums or requested exact reference blocks."""
import argparse,csv,hashlib,io,json,time,zipfile,zlib
from pathlib import Path
import numpy as np
import torch

p=argparse.ArgumentParser();p.add_argument('--index',type=Path,required=True);p.add_argument('--tracer',required=True);p.add_argument('--fold',type=int,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--requests',type=Path)
a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);torch.set_num_threads(2)
rows=[r for r in csv.DictReader(a.index.open()) if r['tracer']==a.tracer and int(r['fold'])==a.fold]
requests=zipfile.ZipFile(a.requests) if a.requests else None
name='exceptions.zip' if requests else 'block_crc.zip'
start=time.time()
with zipfile.ZipFile(a.out/name,'x',compression=zipfile.ZIP_STORED) as packet:
    for i,r in enumerate(rows):
        source=Path('/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3')/r['cache_name']
        item=torch.load(source,map_location='cpu',weights_only=False)
        assert item['name']==r['ptid'] and int(item['test_fold'])==a.fold
        real=item[a.tracer].detach().cpu().numpy().squeeze().copy()
        raw=real.tobytes();assert hashlib.sha256(raw).hexdigest()==r['base_sha256']
        buffer=io.BytesIO();member=r['ptid']+'_'+r['tracer']+'.npz'
        if requests:
            with np.load(io.BytesIO(requests.read(member))) as z:indices=z['indices']
            np.savez_compressed(buffer,indices=indices,values=real.reshape(-1,64)[indices])
        else:
            view=memoryview(raw)
            checks=np.fromiter((zlib.crc32(view[j:j+256]) for j in range(0,len(view),256)),dtype=np.uint32)
            np.savez_compressed(buffer,crc=checks)
        packet.writestr(member,buffer.getvalue())
        if i%40==0:print(json.dumps({'targets':i+1,'total':len(rows),'seconds':time.time()-start}),flush=True)
    packet.writestr('manifest.json',json.dumps(rows))
(a.out/'complete.json').write_text(json.dumps({'status':'COMPLETE_EXACT_REFERENCE_TRANSPORT','targets':len(rows),'payload':name,
    'sha256':hashlib.sha256((a.out/name).read_bytes()).hexdigest(),'bytes':(a.out/name).stat().st_size,
    'block_float32_values':64,'final_acceptance':'Full-array SHA-256, never block CRC alone','source_arrays_modified':False},indent=2)+'\n')
