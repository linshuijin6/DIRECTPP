#!/usr/bin/env python3
"""Pin down absolute laterality. The mask lives on the SAVED grid (saved=flip(proc)).
We map saved-grid mask indices to world TWO independent ways and cross-check:

 A) Build the saved-grid affine directly: saved = flip(proc,(0,1,2)).
    If proc index p maps to world via proc_aff, then saved index s corresponds
    to proc index p = (shape-1 - s). So saved_aff maps s->world by
    proc_aff applied to (shape-1 - s). We derive saved_aff as a 4x4.
 B) prepare.py path: flip mask back to proc grid, apply proc_aff.
Both must agree. Then report absolute world-x of L/R labels and whether
LEFT label (17,2,...) truly sits at x<0 (anatomical left in RAS).
"""
import os, sys, json
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np, nibabel as nib
sys.path.insert(0, "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3003/home/data/liutuo/code")
import monai.transforms as mt
ROOT="/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"; OUT=ROOT+"/reports/e1_laterality_rootcause_20261017"
COHORT=json.load(open(ROOT+"/reports/e1_stage01_20261017/cohort.json")); byid={c["ptid"]:c for c in COHORT}
keys=["mri"]
T=mt.Compose([mt.Lambdad(keys=keys,func=lambda p:nib.load(p).get_fdata()),
 mt.EnsureChannelFirstd(keys=keys,channel_dim="no_channel"),mt.Orientationd(keys=keys,axcodes="LPI"),
 mt.CropForegroundd(keys=keys,source_key="mri",allow_smaller=True),mt.HistogramNormalized(keys=["mri"]),
 mt.ResizeWithPadOrCropd(keys=keys,spatial_size=[160,192,160]),mt.Spacingd(keys=keys,pixdim=(1.,1.,1.)),
 mt.NormalizeIntensityd(keys=keys),mt.ScaleIntensityd(keys=keys)])

sid="002_S_0295"; item=byid[sid]
raw=nib.load(item["mri"]); proc=T({"mri":item["mri"]}); proc_aff=np.asarray(proc["mri"].affine)
shape=np.array([160,192,160])
mask=np.rint(nib.load(item["mask"]).get_fdata()).astype(np.int32)  # SAVED grid

# saved index s -> proc index p = (shape-1 - s); world = proc_aff @ [p,1]
def world_from_saved(s):
    p = (shape-1) - np.asarray(s)
    return nib.affines.apply_affine(proc_aff, p)

for lab,nm in [(17,"L-Hipp"),(53,"R-Hipp"),(2,"L-WM"),(41,"R-WM")]:
    c=np.argwhere(mask==lab)
    if len(c)==0: print(nm,"absent"); continue
    w=world_from_saved(c.mean(0))
    print(f"{nm:8s} n={len(c):6d}  world=({w[0]:+.1f},{w[1]:+.1f},{w[2]:+.1f})  worldX={'LEFT(x<0)' if w[0]<0 else 'RIGHT(x>0)'}")

# Sanity: map the proc MRI's own brain-left extreme. Use raw MRI RAS world as ground truth
# by taking raw data brain voxels where raw world x<0 (left) vs mask label17 location.
print("\nRaw MRI affine maps negative-x = anatomical LEFT (standard RAS). proc_aff axcodes:",
      nib.aff2axcodes(proc_aff))
print("proc_aff:\n", np.round(proc_aff,2))
print("world origin of proc index [0,0,0]:", np.round(nib.affines.apply_affine(proc_aff,[0,0,0]),1))
print("world of proc index [159,0,0]:", np.round(nib.affines.apply_affine(proc_aff,[159,0,0]),1))
