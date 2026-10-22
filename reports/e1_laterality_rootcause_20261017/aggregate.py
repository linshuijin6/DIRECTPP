#!/usr/bin/env python3
import os, json
import numpy as np
ROOT = "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
OUT = os.path.join(ROOT, "reports/e1_laterality_rootcause_20261017")
recs = json.load(open(os.path.join(OUT, "per_subject_index_evidence.json")))

# 1) header/orientation consistency
axcodes = {}
qform = {}
sform = {}
dets = []
mask_ax = {}
for r in recs:
    if "error" in r: continue
    axcodes[r["raw_axcodes"]] = axcodes.get(r["raw_axcodes"], 0) + 1
    qform[r["raw_qform_code"]] = qform.get(r["raw_qform_code"], 0) + 1
    sform[r["raw_sform_code"]] = sform.get(r["raw_sform_code"], 0) + 1
    dets.append(r["raw_det"])
    mask_ax[r["mask_axcodes"]] = mask_ax.get(r["mask_axcodes"], 0) + 1

print("raw MRI axcodes:", axcodes)
print("raw qform_code:", qform, "sform_code:", sform)
print("raw det sign: pos=%d neg=%d" % (sum(d>0 for d in dets), sum(d<0 for d in dets)))
print("mask axcodes:", mask_ax)

# 2) along which array axis do L/R separate, and sign consistency
# For each pair & axis, count sign of (cL - cR). The axis where |mean diff| is
# large & consistent is the L/R axis. Sign tells whether label17(L) sits at
# lower or higher index than label53(R).
print("\n== index-space separation per pair (axis with max |mean diff|) ==")
summary_pairs = {}
for name in recs[1]["pairs_index"].keys():
    diffs = {0: [], 1: [], 2: []}
    nvox = []
    for r in recs:
        if "error" in r: continue
        p = r["pairs_index"][name]
        if p["cL"] is None or p["cR"] is None: continue
        diffs[0].append(p["d_axis0"]); diffs[1].append(p["d_axis1"]); diffs[2].append(p["d_axis2"])
        nvox.append((p["nL"], p["nR"]))
    means = {a: float(np.mean(v)) if v else None for a, v in diffs.items()}
    # choose LR axis as the one with largest abs mean
    lr_axis = max(means, key=lambda a: abs(means[a]) if means[a] is not None else -1)
    vals = diffs[lr_axis]
    pos = sum(1 for x in vals if x > 0); neg = sum(1 for x in vals if x < 0)
    summary_pairs[name] = dict(
        lr_axis=lr_axis, mean_diff_lr=means[lr_axis],
        mean_diff_all=means, n=len(vals),
        frac_cL_gt_cR=round(pos/max(1,len(vals)), 3),
        frac_cL_lt_cR=round(neg/max(1,len(vals)), 3),
    )
    md = means[lr_axis]
    mds = "n/a" if md is None else f"{md:+.2f}"
    print(f"{name:16s} LRaxis={lr_axis} meanDiff(L-R)={mds}  cL>cR:{pos} cL<cR:{neg}  (n={len(vals)})")

json.dump(dict(raw_axcodes=axcodes, raw_qform=qform, raw_sform=sform,
               mask_axcodes=mask_ax,
               det_pos=sum(d>0 for d in dets), det_neg=sum(d<0 for d in dets),
               pairs=summary_pairs),
          open(os.path.join(OUT, "aggregate.json"), "w"), indent=1)

# 3) hippocampus degeneracy check across sample
hip_nL = [r["pairs_index"]["Hippocampus"]["nL"] for r in recs if "error" not in r]
hip_nR = [r["pairs_index"]["Hippocampus"]["nR"] for r in recs if "error" not in r]
print("\nHippocampus nL: min=%d median=%d max=%d" % (min(hip_nL), int(np.median(hip_nL)), max(hip_nL)))
print("Hippocampus nR: min=%d median=%d max=%d" % (min(hip_nR), int(np.median(hip_nR)), max(hip_nR)))
print("subjects with nL<=1:", sum(1 for x in hip_nL if x <= 1), "/", len(hip_nL))
print("subjects with nL much < nR (nL< nR/3):", sum(1 for a,b in zip(hip_nL,hip_nR) if a < b/3))
