"""Read-only audit step 3: independent PTID+tracer+fold+epoch alignment of Full vs
Tracer-only OOF predictions; recomputes the paired comparison statistics; samples
NIfTI outputs for voxel-level differences and prediction_sha256 verification.
Writes audit_alignment_results.json only into this audit directory.
"""
import csv, hashlib, json
from pathlib import Path
import numpy as np
import nibabel as nib
from scipy import stats

REPO = Path("/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP")
FULL_CSV = REPO / "reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv"
TRACER_CSV = REPO / "reports/tracer_only_control_20261027/oof_summary/per_subject_metrics.csv"
PAIRED_CSV = REPO / "reports/tracer_only_control_20261027/oof_summary/paired_comparison_summary.csv"
FULL_OOF = Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/oof")
TRACER_OOF = Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022/oof")
OUT = Path(__file__).resolve().parent / "audit_alignment_results.json"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024 ** 2), b""):
            h.update(b)
    return h.hexdigest()

def load(path):
    rows = list(csv.DictReader(open(path)))
    for r in rows:
        r["fold"] = int(r["fold"]); r["epoch"] = int(r["epoch"])
        for m in ("ssim", "psnr", "mse", "mae"):
            r[m] = float(r[m])
    return rows

def main():
    full = load(FULL_CSV); tracer = load(TRACER_CSV)
    key = lambda r: (r["ptid"], r["tracer"], r["fold"], r["epoch"])
    fmap, tmap = {key(r): r for r in full}, {key(r): r for r in tracer}
    assert len(fmap) == len(full) and len(tmap) == len(tracer)
    common = sorted(set(fmap) & set(tmap))
    result = {
        "full_rows": len(full), "tracer_rows": len(tracer), "common_keys": len(common),
        "full_only": len(set(fmap) - set(tmap)), "tracer_only": len(set(tmap) - set(fmap)),
        "rows_per_epoch": {str(e): sum(1 for k in common if k[3] == e) for e in (165, 200)},
    }

    # per-row checkpoint identity summary
    ck = {}
    for k in common:
        ck.setdefault((k[2], k[3]), set()).add((fmap[k]["checkpoint_sha256"][:8], tmap[k]["checkpoint_sha256"][:8]))
    result["checkpoint_pairs_per_fold_epoch"] = {f"f{f}_e{e}": sorted(v) for (f, e), v in sorted(ck.items())}

    # recompute paired stats and compare with the archived paired_comparison_summary.csv
    paired = list(csv.DictReader(open(PAIRED_CSV)))
    recomputed, max_abs_err = {}, 0.0
    for epoch in (165, 200):
        for tracer in ("av45", "fdg"):
            keys = [k for k in common if k[3] == epoch and k[1] == tracer]
            for metric, mname in (("ssim", "SSIM"), ("psnr", "PSNR"), ("mse", "MSE"), ("mae", "MAE")):
                a = np.array([fmap[k][metric] for k in keys])
                b = np.array([tmap[k][metric] for k in keys])
                d = b - a
                t_stat, p_val = stats.ttest_rel(b, a)
                sd = d.std(ddof=1)
                cohen = d.mean() / sd if sd > 0 else float("nan")
                ci = stats.t.interval(0.95, len(d) - 1, loc=d.mean(), scale=stats.sem(d))
                row = {
                    "n": len(keys), "full_mean": a.mean(), "tracer_mean": b.mean(),
                    "diff_mean": d.mean(), "ci95": [ci[0], ci[1]], "cohen_d": cohen,
                    "t_stat": float(t_stat), "p_value": float(p_val),
                }
                ref = next(r for r in paired if int(r["epoch"]) == epoch and r["tracer"] == tracer and r["metric"] == mname)
                for rk, mk in (("n", "n"), ("full_mean", "full_mean"), ("tracer_only_mean", "tracer_mean"),
                               ("diff_mean", "diff_mean"), ("cohen_d", "cohen_d"), ("paired_t_stat", "t_stat"), ("p_value", "p_value")):
                    max_abs_err = max(max_abs_err, abs(float(ref[rk]) - row[mk]))
                recomputed[f"e{epoch}_{tracer}_{mname}"] = row
    result["paired_comparison_recomputed"] = recomputed
    result["paired_comparison_max_abs_deviation_vs_archived_csv"] = max_abs_err

    # NIfTI voxel sampling
    samples = [("002_S_0295", "fdg", 2, 165), ("002_S_0729", "av45", 1, 165), ("941_S_6854", "fdg", 2, 165),
               ("002_S_1261", "av45", 1, 165), ("002_S_0295", "fdg", 2, 200), ("941_S_6854", "fdg", 2, 200)]
    nifti_rows = []
    for ptid, tracer, fold, epoch in samples:
        k = (ptid, tracer, fold, epoch)
        if k not in fmap:
            continue
        fp = FULL_OOF / f"epoch{epoch}/fold{fold}/generated_{tracer}_{ptid}.nii.gz"
        tp = TRACER_OOF / f"epoch{epoch}/fold{fold}/generated_{tracer}_{ptid}.nii.gz"
        a = np.asarray(nib.load(str(fp)).dataobj, dtype=np.float64)
        b = np.asarray(nib.load(str(tp)).dataobj, dtype=np.float64)
        d = a - b
        nifti_rows.append({
            "ptid": ptid, "tracer": tracer, "fold": fold, "epoch": epoch,
            "full_path": str(fp), "tracer_path": str(tp),
            "full_sha256_matches_metrics": sha256_file(fp) == fmap[k]["prediction_sha256"],
            "tracer_sha256_matches_metrics": sha256_file(tp) == tmap[k]["prediction_sha256"],
            "shape": list(a.shape),
            "voxel_max_abs": float(np.abs(d).max()), "voxel_mean_abs": float(np.abs(d).mean()),
            "voxel_rmse": float(np.sqrt((d ** 2).mean())),
            "full_vs_tracer_ssim_diff_from_metrics": tmap[k]["ssim"] - fmap[k]["ssim"],
            "full_vs_tracer_mae_diff_from_metrics": tmap[k]["mae"] - fmap[k]["mae"],
        })
    result["nifti_voxel_samples"] = nifti_rows
    result["nifti_all_sha256_verified"] = all(r["full_sha256_matches_metrics"] and r["tracer_sha256_matches_metrics"] for r in nifti_rows)

    # same-subject cross-experiment fold sanity: no overlap of held-out sets
    f1 = {k[0] for k in common if k[2] == 1}; f2 = {k[0] for k in common if k[2] == 2}
    result["heldout_fold1_ptids"] = len(f1); result["heldout_fold2_ptids"] = len(f2)
    result["heldout_intersection"] = len(f1 & f2)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
