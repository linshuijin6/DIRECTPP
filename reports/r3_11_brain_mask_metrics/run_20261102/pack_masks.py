"""Losslessly package frozen mask>0 arrays, never recompute segmentations."""
import concurrent.futures
import csv
import hashlib
import json
import numpy as np
from pathlib import Path

OUT=Path(__file__).resolve().parent
DEST=OUT/'inputs/frozen_mask_union'
DEST.mkdir(exist_ok=True)
rows={r['ptid']:r for r in csv.DictReader((OUT/'input_index.csv').open())}


def pack(row):
    source=Path(row['mask_cache'])
    # Full's evaluation independently checks the complete original NPZ hash for
    # every subject. Here read only its mask member; final joining also requires
    # an exact mask-array hash match with Full, avoiding a second large NPZ read.
    digest=row['mask_cache_sha256_expected']
    with np.load(source,allow_pickle=False) as z:brain=np.asarray(z['mask']>0)
    assert brain.shape==(160,192,160)
    packed=np.packbits(brain.ravel())
    path=DEST/(row['ptid']+'.npz')
    np.savez_compressed(path,packed=packed)
    with np.load(path) as z:restored=np.unpackbits(z['packed']).reshape(brain.shape).astype(bool)
    assert np.array_equal(brain,restored)
    return {'ptid':row['ptid'],'fold':int(row['fold']),'full_cache_name':Path(row['target_cache']).name,
        'source_mask_cache':str(source),'source_mask_cache_sha256':digest,
        'source_npz_hash_validation':'Independently checked in Full evaluation before final merge',
        'packed_path':str(path),'packed_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'brain_mask_array_sha256':hashlib.sha256(brain.tobytes()).hexdigest(),'mask_voxels':int(brain.sum())}


with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    result=list(pool.map(pack,rows.values()))
(OUT/'mask_transfer_manifest.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({'subjects':len(result),'bytes':sum(p.stat().st_size for p in DEST.glob('*.npz')),'all_packbits_roundtrips_exact':True}),flush=True)
