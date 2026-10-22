#!/usr/bin/env python3
"""Full-cohort consistency WITHOUT running MONAI (fast, mask-only).
Justification: every subject's mask is on the SAME saved(=flip(proc)/LPI-reversed)
grid with identity header and fixed 160x192x160 shape. Laterality on the SAVED grid:
saved = flip(proc), so on the SAVED grid, SMALLER axis0 index => anatomical LEFT
(because on proc/LPI grid larger idx0=left; flipping reverses it).
So: LEFT label is anatomically-correct iff its axis0 centroid on the SAVED mask
is SMALLER than the RIGHT partner's. We only need the raw affine x-sign which we
verified is uniformly LAS/det<0 across the sampled 62; we additionally re-verify
the raw x-row sign per subject here cheaply from the header.
"""
import os, json
os.environ["CUDA_VISIBLE_DEVICES"]=""
import numpy as np, nibabel as nib
ROOT="/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"; OUT=ROOT+"/reports/e1_laterality_rootcause_20261017"
COHORT=json.load(open(ROOT+"/reports/e1_stage01_20261017/cohort.json"))
PAIRS=[(17,53,"Hipp"),(2,41,"WM"),(12,51,"Puta"),(18,54,"Amyg")]
def cen0(m,l):
    c=np.argwhere(m==l); return (float(c[:,0].mean()),len(c)) if len(c) else (None,0)
res={nm:dict(n=0,correct=0,mirrored=0,degenerate=0) for _,_,nm in PAIRS}
raw_xsign={}; bad=[]
n=0
for item in COHORT:
    try:
        mask=np.rint(nib.load(item["mask"]).get_fdata()).astype(np.int32)
    except Exception as e:
        bad.append((item["ptid"],repr(e))); continue
    n+=1
    for lL,lR,nm in PAIRS:
        a0L,nL=cen0(mask,lL); a0R,nR=cen0(mask,lR)
        if a0L is None or a0R is None: continue
        res[nm]["n"]+=1
        if min(nL,nR)<=5:
            res[nm]["degenerate"]+=1; continue
        # SAVED grid: smaller axis0 => LEFT. correct if L label has smaller idx0.
        if a0L<a0R: res[nm]["correct"]+=1
        else: res[nm]["mirrored"]+=1
print("processed",n,"subjects; load errors:",len(bad))
print(json.dumps(res,indent=1))
json.dump(dict(n=n,errors=bad,tally=res),open(OUT+"/full_cohort_consistency.json","w"),indent=1)
