#!/usr/bin/env python3
"""Root-cause probe for E1 ROI laterality failure.
Read-only on existing data; writes only into this report dir.
No PET metrics used to choose orientation.
"""
import os, sys, json
os.environ["CUDA_VISIBLE_DEVICES"] = ""
import numpy as np
import nibabel as nib

ROOT = "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
OUT = os.path.join(ROOT, "reports/e1_laterality_rootcause_20261017")
COHORT = json.load(open(os.path.join(ROOT, "reports/e1_stage01_20261017/cohort.json")))

PAIRS = [
    (17, 53, "Hippocampus"),
    (2, 41, "CerebralWM"),
    (3, 42, "CerebralCortex"),
    (4, 43, "LateralVentricle"),
    (10, 49, "Thalamus"),
    (11, 50, "Caudate"),
    (12, 51, "Putamen"),
    (13, 52, "Pallidum"),
    (18, 54, "Amygdala"),
    (1025, 2025, "Precuneus"),
    (1008, 2008, "InfParietal"),
]

def axcodes_of(aff):
    return "".join(nib.aff2axcodes(aff))

def centroid_index(mask, label):
    coords = np.argwhere(mask == label)
    if len(coords) == 0:
        return None, 0
    return coords.mean(0), len(coords)

def analyze(item):
    sid = item["ptid"]
    raw = nib.load(item["mri"])
    raw_aff = raw.affine
    mask_im = nib.load(item["mask"])
    mask = np.rint(mask_im.get_fdata()).astype(np.int32)
    saved_im = nib.load(item["saved_mri"])
    rec = dict(
        ptid=sid,
        raw_axcodes=axcodes_of(raw_aff),
        raw_affine=raw_aff.tolist(),
        raw_qform_code=int(raw.header["qform_code"]),
        raw_sform_code=int(raw.header["sform_code"]),
        raw_det=float(np.linalg.det(raw_aff[:3, :3])),
        mask_axcodes=axcodes_of(mask_im.affine),
        mask_affine_identity=bool(np.allclose(mask_im.affine, np.eye(4))),
        saved_affine_identity=bool(np.allclose(saved_im.affine, np.eye(4))),
        mask_shape=list(mask.shape),
    )
    pair_idx = {}
    for (lL, lR, name) in PAIRS:
        cL, nL = centroid_index(mask, lL)
        cR, nR = centroid_index(mask, lR)
        pair_idx[name] = dict(
            left_label=lL, right_label=lR, nL=int(nL), nR=int(nR),
            cL=None if cL is None else cL.tolist(),
            cR=None if cR is None else cR.tolist(),
            d_axis0=None if (cL is None or cR is None) else float(cL[0]-cR[0]),
            d_axis1=None if (cL is None or cR is None) else float(cL[1]-cR[1]),
            d_axis2=None if (cL is None or cR is None) else float(cL[2]-cR[2]),
        )
    rec["pairs_index"] = pair_idx
    return rec

def main():
    n_sample = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    passing = ["100_S_0743", "128_S_4842"]
    byid = {c["ptid"]: c for c in COHORT}
    rng = np.random.default_rng(20261017)
    others = [c["ptid"] for c in COHORT if c["ptid"] not in passing]
    sel = [str(x) for x in rng.choice(others, size=min(n_sample, len(others)), replace=False)]
    ids = passing + sel
    recs = []
    for sid in ids:
        try:
            recs.append(analyze(byid[sid]))
        except Exception as e:
            recs.append(dict(ptid=sid, error=repr(e)))
    json.dump(recs, open(os.path.join(OUT, "per_subject_index_evidence.json"), "w"), indent=1)
    print("wrote", len(recs), "subject records")

if __name__ == "__main__":
    main()
