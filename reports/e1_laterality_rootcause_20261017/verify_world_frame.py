"""Independent re-check of the sub-agent conclusion (main agent, 2026-10-17).

prepare.py loads images with Lambdad(nib.load(p).get_fdata()), i.e. a bare array
with NO header affine. MONAI's meta affine (proc.affine) therefore maps processed
indices to RAW VOXEL INDICES, not to world mm. Hence ref.affine @ proc.affine is
the correct index->world map, and the sub-agent's "double-applied affine" diagnosis
must be re-tested. This script uses only MRI/mask/template geometry (no PET).
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np

R = Path("/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage01_20261017")
OUT = Path(__file__).resolve().parent
TEMPLATE = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/MNI152lin_T1_1mm_brain.nii.gz"
PAIRS = [(2, 41), (12, 51), (4, 43), (10, 49)]

geo = {r["ptid"]: r for r in json.loads((R / "geometry_qc_final.json").read_text())}
rows = [r for r in json.loads((R / "cohort.json").read_text()) if r["mri_mask_grid_pass"]]


def centroids(r):
    a = np.asarray(geo[r["ptid"]]["affine"])  # = ref.affine @ proc.affine (stored in cache)
    m = np.flip(np.rint(nib.load(r["mask"]).get_fdata(dtype=np.float32)).astype(np.int16), (0, 1, 2))
    out = {}
    for x, y in PAIRS:
        cx = (a @ np.r_[np.argwhere(m == x).mean(0), 1.0])[0]
        cy = (a @ np.r_[np.argwhere(m == y).mean(0), 1.0])[0]
        out[f"{x}_{y}"] = [float(cx), float(cy)]
    return r["ptid"], out


def template_check(step):
    t_im = nib.load(TEMPLATE)
    t = t_im.get_fdata()
    tf = t[::-1]
    res = []
    for r in rows[::step]:
        im = nib.load(r["mri"])
        assert im.shape == t.shape and np.allclose(im.affine, t_im.affine)
        x = im.get_fdata()
        res.append(dict(ptid=r["ptid"], corr=float(np.corrcoef(x.ravel(), t.ravel())[0, 1]),
                        corr_xflip=float(np.corrcoef(x.ravel(), tf.ravel())[0, 1])))
    return dict(template_affine_row0=t_im.affine[0].tolist(), n=len(res), rows=res,
                unflipped_better=sum(v["corr"] > v["corr_xflip"] for v in res))


if __name__ == "__main__":
    with ThreadPoolExecutor(8) as ex:
        cents = dict(ex.map(centroids, rows))
    summary = {}
    for k in [f"{x}_{y}" for x, y in PAIRS]:
        left = np.array([v[k][0] for v in cents.values()])
        right = np.array([v[k][1] for v in cents.values()])
        summary[k] = dict(n=len(left), label_left_mean_world_x=float(left.mean()),
                          label_left_frac_x_gt0=float((left > 0).mean()),
                          label_right_mean_world_x=float(right.mean()),
                          label_right_frac_x_lt0=float((right < 0).mean()))
    print(json.dumps(summary, indent=1), flush=True)
    tc = template_check(int(sys.argv[1]) if len(sys.argv) > 1 else 93)
    print("template", tc["n"], "unflipped_better", tc["unflipped_better"], flush=True)
    (OUT / "verify_world_frame.json").write_text(json.dumps(dict(world_centroid_summary=summary,
        template_registration_check=tc, per_subject=cents), indent=1))
