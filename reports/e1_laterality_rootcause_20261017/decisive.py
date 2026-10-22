#!/usr/bin/env python3
"""DECISIVE: On the proc/LPI grid, increasing array-axis0 => anatomical LEFT
(both raw MRI and proc meta-affine have -1 on the x-row; translation does not
flip L/R). So a label is anatomically LEFT iff its axis0 centroid is LARGER.

We check: does FreeSurfer LEFT label (17,2,4,...) have the LARGER axis0 centroid
than its RIGHT partner, on the proc grid? If yes -> labels anatomically CORRECT,
and prepare.py's world_affine (raw@proc) is the bug. If labels have SMALLER axis0
-> labels are MIRRORED.
Also report what prepare.py's buggy criterion (xL<xR with raw@proc affine) does.
"""
import os, sys, json
os.environ["CUDA_VISIBLE_DEVICES"]=""
import numpy as np, nibabel as nib
sys.path.insert(0,"/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3003/home/data/liutuo/code")
import monai.transforms as mt
ROOT="/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"; OUT=ROOT+"/reports/e1_laterality_rootcause_20261017"
COHORT=json.load(open(ROOT+"/reports/e1_stage01_20261017/cohort.json")); byid={c["ptid"]:c for c in COHORT}
keys=["mri"]
T=mt.Compose([mt.Lambdad(keys=keys,func=lambda p:nib.load(p).get_fdata()),
 mt.EnsureChannelFirstd(keys=keys,channel_dim="no_channel"),mt.Orientationd(keys=keys,axcodes="LPI"),
 mt.CropForegroundd(keys=keys,source_key="mri",allow_smaller=True),mt.HistogramNormalized(keys=["mri"]),
 mt.ResizeWithPadOrCropd(keys=keys,spatial_size=[160,192,160]),mt.Spacingd(keys=keys,pixdim=(1.,1.,1.)),
 mt.NormalizeIntensityd(keys=keys),mt.ScaleIntensityd(keys=keys)])
PAIRS=[(17,53,"Hipp"),(2,41,"WM"),(4,43,"Vent"),(10,49,"Thal"),(12,51,"Puta"),(18,54,"Amyg"),(1025,2025,"Prec")]
shape=np.array([160,192,160])
def cen(m,l):
    c=np.argwhere(m==l); return (c.mean(0),len(c)) if len(c) else (None,0)
ids=["100_S_0743","128_S_4842"]+[c["ptid"] for c in COHORT[:50]]
tally={nm:dict(n=0,left_label_is_anatomical_left=0,buggy_pass=0) for _,_,nm in PAIRS}
for sid in ids:
    item=byid[sid]; raw=nib.load(item["mri"]); proc=T({"mri":item["mri"]})
    proc_aff=np.asarray(proc["mri"].affine); buggy=raw.affine@proc_aff
    mask=np.rint(nib.load(item["mask"]).get_fdata()).astype(np.int32)
    mlpi=np.flip(mask,(0,1,2))   # proc/LPI grid
    for lL,lR,nm in PAIRS:
        cL,nL=cen(mlpi,lL); cR,nR=cen(mlpi,lR)
        if cL is None or cR is None: continue
        tally[nm]["n"]+=1
        # anatomical left iff larger axis0 on LPI grid
        if cL[0]>cR[0]: tally[nm]["left_label_is_anatomical_left"]+=1
        xLb=nib.affines.apply_affine(buggy,cL)[0]; xRb=nib.affines.apply_affine(buggy,cR)[0]
        if xLb<xRb: tally[nm]["buggy_pass"]+=1
print(json.dumps(tally,indent=1))
json.dump(tally,open(OUT+"/decisive_tally.json","w"),indent=1)
