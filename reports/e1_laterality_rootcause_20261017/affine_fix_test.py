#!/usr/bin/env python3
"""Definitive test: compute hippocampus L/R centroid world-x under
(a) prepare.py's world_affine (raw@proc), and
(b) the correct index->world affine (proc_aff alone on the LPI grid).
Ground truth: in true RAS world, LEFT structures have x<0.
We do NOT use PET. We use the MONAI meta-affine which maps processed-array
indices to the real MNI/RAS world (verified: LPI axcodes, correct MNI origin).
"""
import os, sys, json
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np
import nibabel as nib
sys.path.insert(0, "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3003/home/data/liutuo/code")
import monai.transforms as mt

ROOT = "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
OUT = os.path.join(ROOT, "reports/e1_laterality_rootcause_20261017")
COHORT = json.load(open(os.path.join(ROOT, "reports/e1_stage01_20261017/cohort.json")))
byid = {c["ptid"]: c for c in COHORT}

keys = ["mri"]
def build():
    return mt.Compose([
        mt.Lambdad(keys=keys, func=lambda p: nib.load(p).get_fdata()),
        mt.EnsureChannelFirstd(keys=keys, channel_dim="no_channel"),
        mt.Orientationd(keys=keys, axcodes="LPI"),
        mt.CropForegroundd(keys=keys, source_key="mri", allow_smaller=True),
        mt.HistogramNormalized(keys=["mri"]),
        mt.ResizeWithPadOrCropd(keys=keys, spatial_size=[160, 192, 160]),
        mt.Spacingd(keys=keys, pixdim=(1., 1., 1.)),
        mt.NormalizeIntensityd(keys=keys), mt.ScaleIntensityd(keys=keys)])
T = build()

PAIRS = [(17,53,"Hipp"),(2,41,"WM"),(4,43,"Vent"),(10,49,"Thal"),
         (12,51,"Puta"),(18,54,"Amyg"),(1025,2025,"Prec")]

def centroid(mask, lab):
    c = np.argwhere(mask == lab)
    return (c.mean(0), len(c)) if len(c) else (None, 0)

ids = ["100_S_0743","128_S_4842"] + [c["ptid"] for c in COHORT[:40]]
rows = []
for sid in ids:
    item = byid[sid]
    raw = nib.load(item["mri"])
    proc = T({"mri": item["mri"]})
    proc_aff = np.asarray(proc["mri"].affine)          # correct index->RAS world (LPI grid)
    buggy_aff = raw.affine @ proc_aff                   # prepare.py world_affine
    mask = np.rint(nib.load(item["mask"]).get_fdata()).astype(np.int32)
    mask_lpi = np.flip(mask, (0,1,2))                   # prepare.py flips mask to proc(LPI) grid
    r = dict(ptid=sid)
    for lL,lR,nm in PAIRS:
        cL,nL = centroid(mask_lpi,lL); cR,nR = centroid(mask_lpi,lR)
        if cL is None or cR is None:
            r[nm]=None; continue
        xL_b = nib.affines.apply_affine(buggy_aff,cL)[0]
        xR_b = nib.affines.apply_affine(buggy_aff,cR)[0]
        xL_c = nib.affines.apply_affine(proc_aff,cL)[0]
        xR_c = nib.affines.apply_affine(proc_aff,cR)[0]
        r[nm]=dict(nL=int(nL),nR=int(nR),
                   buggy_pass=bool(xL_b<xR_b),  # prepare.py criterion
                   correct_pass=bool(xL_c<xR_c),
                   xL_correct=round(float(xL_c),1), xR_correct=round(float(xR_c),1))
    rows.append(r)

# tally for hippocampus & the robust WM pair
def tally(nm):
    bp = sum(1 for r in rows if r.get(nm) and r[nm]["buggy_pass"])
    cp = sum(1 for r in rows if r.get(nm) and r[nm]["correct_pass"])
    tot= sum(1 for r in rows if r.get(nm))
    return dict(n=tot, buggy_pass=bp, correct_pass=cp)

res = {nm: tally(nm) for _,_,nm in PAIRS}
print(json.dumps(res, indent=1))
json.dump(dict(tally=res, rows=rows), open(os.path.join(OUT,"affine_fix_test.json"),"w"), indent=1)
print("\nInterpretation: with correct index->world affine (proc_aff), does LEFT label have x<0?")
# For WM (large, robust): print mean world-x of L and R labels
for nm in ["WM","Hipp","Puta"]:
    xl=[r[nm]["xL_correct"] for r in rows if r.get(nm)]
    xr=[r[nm]["xR_correct"] for r in rows if r.get(nm)]
    print(f"  {nm}: mean worldX  Left-label={np.mean(xl):+.1f}  Right-label={np.mean(xr):+.1f}")
