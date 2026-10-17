"""Re-extract every Syn ROI from preserved volumes, three CPU readers.

Real CSV values retained: verified against six source-volume preprocessing
replays (588 ROI checks); this is a bounded provenance check, not full replay.
"""
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd

import analyze_evidence as analysis

ROOT=analysis.ROOT
OUT=analysis.OUT/'image_derived'
OUT.mkdir(exist_ok=True)


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def one_subject(item):
    subject, paths, regions = item
    mp=ROOT/'data/data_augmentation_mri_fenge'/f'{subject}fenge.nii.gz'
    mi=nib.load(mp)
    mask=mi.get_fdata(dtype=np.float32).astype(np.int16)
    counts=np.bincount(mask.ravel(),minlength=2036)
    provenance=[dict(kind='mask',subject=subject,path=str(mp),bytes=mp.stat().st_size,sha256=sha(mp),
                     min=float(mask.min()),max=float(mask.max()),label174_voxels=int(counts[174]))]
    means={}
    for tracer,p in paths.items():
        img=nib.load(p);a=img.get_fdata(dtype=np.float32)
        assert a.shape==mask.shape and np.allclose(img.affine,mi.affine),(p,mp)
        assert np.isfinite(a).all(),p
        assert a.max()>a.min(),p
        sums=np.bincount(mask.ravel(),weights=a.ravel(),minlength=2036)
        means[tracer]={int(r):float(sums[r]/counts[r]) if counts[r]>0 else np.nan for r in regions[tracer]}
        provenance.append(dict(kind='syn_'+tracer,subject=subject,path=str(p),bytes=p.stat().st_size,sha256=sha(p),
                               min=float(a.min()),max=float(a.max()),label174_voxels=None))
    return subject,means,provenance


def main():
    start=time.monotonic()
    regions={};csvs={};subjects={}
    for tracer in ['av45','fdg']:
        csvs[tracer]={int(float(p.stem.removeprefix('region_'))):pd.read_csv(p) for p in
                      (ROOT/f'4_analysis_and_figures/statistics_{tracer}').glob('region_*.csv')}
        regions[tracer]=sorted(csvs[tracer])
        subjects[tracer]=set(next(iter(csvs[tracer].values())).subject)
    items=[]
    for s in sorted(subjects['av45']|subjects['fdg']):
        paths={t:ROOT/f'data/data_augmentation_{t}_generated/{s}.nii.gz' for t in subjects if s in subjects[t]}
        assert all(p.exists() for p in paths.values())
        items.append((s,paths,regions))
    allmeans={};provenance=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        for i,(s,m,pr) in enumerate(pool.map(one_subject,items),1):
            allmeans[s]=m;provenance.extend(pr)
            if i%50==0:print(i,'/',len(items),'elapsed_s',round(time.monotonic()-start),flush=True)
    comparisons=[];folders={}
    for t in ['av45','fdg']:
        folders[t]=OUT/f'paired_regions_{t}';folders[t].mkdir(exist_ok=True)
        for r,d in csvs[t].items():
            old=d[f'syn_{t}_mean'].copy()
            d[f'syn_{t}_mean']=[allmeans[s][t][r] for s in d.subject]
            delta=d[f'syn_{t}_mean']-old
            comparisons.append(dict(tracer=t,region=r,n=len(d),csv_vs_volume_mae=float(delta.abs().mean()),
                                    max_abs_difference=float(delta.abs().max()),matched_1e6=int((delta.abs()<1e-6).sum())))
            d.to_csv(folders[t]/f'region_{r}.0.csv',index=False)
    pd.DataFrame(provenance).to_csv(OUT/'source_volume_sha256.csv',index=False)
    pd.DataFrame(comparisons).to_csv(OUT/'old_csv_syn_vs_actual_volumes.csv',index=False)
    (OUT/'extraction_receipt.json').write_text(json.dumps(dict(
        subjects=len(items),syn_volumes=sum(map(len,subjects.values())),cpu_readers=3,
        extraction_wall_seconds=time.monotonic()-start,
        real_source='original real_*_mean CSV columns; six direct upstream-volume checks, 588 regional comparisons',
        syn_source='all available saved Syn volumes; voxel means re-extracted using corresponding preserved SynthSeg masks',
        quantitative_scale='normalized uptake; no SUVR; no TOST',
        cohort='retrospective; not established generator-unseen'),indent=2))
    analysis.OUT=OUT
    analysis.regions(folders)


if __name__=='__main__':main()
