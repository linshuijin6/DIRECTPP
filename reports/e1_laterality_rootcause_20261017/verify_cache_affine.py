"""Direct check of the cached world affine: sample the raw registered MRI at the
world position of each processed voxel (as given by the cache affine) and compare
with the processed MRI, versus an x-mirrored mapping. MRI only; no PET."""
import json
from pathlib import Path

import nibabel as nib
import numpy as np
from scipy.ndimage import map_coordinates

R = Path("/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage01_20261017")
rows = [r for r in json.loads((R / "cohort.json").read_text()) if r["mri_mask_grid_pass"]][::186]
out = []
for r in rows:
    with np.load(r["cache"]) as z:
        mri, aff = z["mri"], z["affine"]
    raw = nib.load(r["mri"])
    ijk = np.argwhere(mri > 0.05)[::50]
    world = nib.affines.apply_affine(aff, ijk)
    res = {}
    for name, w in [("as_is", world), ("x_mirrored", world * np.array([-1, 1, 1]))]:
        vox = nib.affines.apply_affine(np.linalg.inv(raw.affine), w).T
        vals = map_coordinates(raw.get_fdata(), vox, order=1)
        res[name] = float(np.corrcoef(mri[tuple(ijk.T)], vals)[0, 1])
    out.append(dict(ptid=r["ptid"], **res))
    print(out[-1], flush=True)
(Path(__file__).resolve().parent / "verify_cache_affine.json").write_text(json.dumps(out, indent=1))
