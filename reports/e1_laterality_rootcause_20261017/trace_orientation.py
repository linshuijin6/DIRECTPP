#!/usr/bin/env python3
"""Trace MONAI orientation chain & reproduce prepare.py world_affine for one subject.
Determine the true array index -> anatomy relationship for the mask grid.
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

sid = sys.argv[1] if len(sys.argv) > 1 else "002_S_0295"
item = byid[sid]

raw = nib.load(item["mri"])
print("RAW:", item["mri"])
print("  shape", raw.shape, "axcodes", nib.aff2axcodes(raw.affine))
print("  affine:\n", np.round(raw.affine, 3))

keys = ["mri"]
T = mt.Compose([
    mt.Lambdad(keys=keys, func=lambda p: nib.load(p).get_fdata()),
    mt.EnsureChannelFirstd(keys=keys, channel_dim="no_channel"),
    mt.Orientationd(keys=keys, axcodes="LPI"),
    mt.CropForegroundd(keys=keys, source_key="mri", allow_smaller=True),
    mt.HistogramNormalized(keys=["mri"]),
    mt.ResizeWithPadOrCropd(keys=keys, spatial_size=[160, 192, 160]),
    mt.Spacingd(keys=keys, pixdim=(1., 1., 1.)),
    mt.NormalizeIntensityd(keys=keys), mt.ScaleIntensityd(keys=keys)])
proc = T({"mri": item["mri"]})
pm = proc["mri"]
proc_aff = np.asarray(pm.affine)
print("\nPROC mri meta-affine (index->world):\n", np.round(proc_aff, 3))
print("  proc axcodes:", nib.aff2axcodes(proc_aff))

# prepare.py uses world_affine = raw.affine @ proc_aff  (the SUSPECT line)
world_affine = raw.affine @ proc_aff
print("\nprepare.py world_affine = raw.affine @ proc_aff:\n", np.round(world_affine, 3))
print("  world_affine axcodes:", nib.aff2axcodes(world_affine))
print("  world_affine det(3x3):", np.linalg.det(world_affine[:3, :3]))

# The historically-saved MRI array & mask: prepare.py does np.flip(mask,(0,1,2))
# before applying world_affine. The saved MRI equals np.flip(proc_mri,(0,1,2)).
# So the mask grid axes = reversed proc (LPI) axes.
saved = nib.load(item["saved_mri"]).get_fdata()
proc_arr = np.asarray(pm, dtype=np.float32).squeeze()
aligned = np.flip(proc_arr, (0, 1, 2))
print("\nsaved vs flip(proc) maxabs:", float(np.max(np.abs(saved - aligned))))

# True orientation reasoning:
# proc array is LPI -> index0 increases toward anatomical LEFT.
# saved = flip(proc) along all axes -> saved index0 increases toward anatomical RIGHT.
# mask is on the saved grid. prepare.py flips mask back to proc(LPI) grid, then
# applies world_affine. Let's compute what world_affine says for an index0 step.
step = world_affine[:3, 0]
print("\nworld_affine column for mask-grid(after flip=LPI) axis0 (dx,dy,dz):", np.round(step, 3))
print("  => +axis0 moves world x by", round(step[0], 3))

# Independent ground truth via the RAW MRI header (RAS+ world):
# Map raw array voxel (0,0,0) and (N-1,0,0) to world, see x sign.
N = raw.shape
c0 = nib.affines.apply_affine(raw.affine, [0, 0, 0])
c1 = nib.affines.apply_affine(raw.affine, [N[0]-1, 0, 0])
print("\nRAW array axis0: index0 world x=%.1f, index%d world x=%.1f" % (c0[0], N[0]-1, c1[0]))
print("  (RAS+: negative x = LEFT). So raw axis0 increasing goes toward",
      "LEFT" if c1[0] < c0[0] else "RIGHT")
