"""Summarize approved full R2-5 OOF inference; pilot is never pooled as formal evidence."""
import csv
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import TRACERS, active_rows, check_frozen, load_config, write_json
from evaluate import paired_bootstrap

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/r2_5_inference_score_removal_20261030"
FULL_REPORT = ROOT / "reports/e1_full165_inference_20261020"
ERROR_METRICS = ("roi_mae", "brain_mae")
SCORE_METRICS = ("psnr", "ssim7", "ssim11")


def holm_two(pvalues):
    order = np.argsort(pvalues)
    result = np.empty(2)
    result[order[0]] = min(1.0, 2 * pvalues[order[0]])
    result[order[1]] = max(result[order[0]], pvalues[order[1]])
    return result


def main():
    cfg = load_config(ROOT / "reports/e1_stage01_20261017/config.json")
    check_frozen(cfg)
    rows = active_rows(cfg, json.loads((Path(cfg["report"]) / "cohort.json").read_text()))
    expected = {(r["ptid"], r["test_fold"], t) for r in rows for t in TRACERS if r["has_" + t]}
    frames = []
    for fold in (1, 2):
        folder = REPORT / "full" / f"fold{fold}"
        complete = json.loads((folder / "complete.json").read_text())
        identity = json.loads((folder / "run_identity.json").read_text())
        index = json.loads((folder / "prediction_index.json").read_text())
        full_snapshot = json.loads((FULL_REPORT / f"fold{fold}/snapshot.json").read_text())
        if (complete["status"] != "COMPLETE" or complete["stage"] != "full"
                or complete["subjects"] != 928 or identity["checkpoint_training_condition"] != "Full"
                or identity["inference_conditions"] != ["No-Scores"]
                or identity["checkpoint_sha256"] != full_snapshot["checkpoint_sha256"]
                or len(index) != complete["volumes"]):
            raise RuntimeError(f"Incomplete or mismatched fold {fold} inference")
        frame = pd.read_csv(folder / "per_subject_metrics.csv")
        if len(frame) != len(index) or set(frame["fold"]) != {fold}:
            raise RuntimeError(f"Fold {fold} metric/index mismatch")
        indexed = {(e["ptid"], e["fold"], e["tracer"]) for e in index}
        measured = set(frame[["ptid", "fold", "tracer"]].itertuples(index=False, name=None))
        if len(indexed) != len(index) or indexed != measured:
            raise RuntimeError(f"Fold {fold} prediction pairing mismatch")
        if any(e["checkpoint_sha256"] != identity["checkpoint_sha256"] for e in index):
            raise RuntimeError(f"Fold {fold} checkpoint binding mismatch")
        metric_lookup = frame.set_index(["ptid", "fold", "tracer"])
        for e in index:
            row = metric_lookup.loc[(e["ptid"], e["fold"], e["tracer"])]
            if (row["prediction_sha256"] != e["sha256"]
                    or row["cache_sha256"] != e["cache_sha256"]
                    or row["checkpoint_training_condition"] != "Full"):
                raise RuntimeError(f"Prediction receipt mismatch: {e['ptid']} {e['tracer']}")
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    actual = set(frame[["ptid", "fold", "tracer"]].itertuples(index=False, name=None))
    if actual != expected or len(frame) != len(expected):
        raise RuntimeError("No-Scores OOF coverage differs from the frozen eligible cohort")
    contrasts = []
    for tracer in TRACERS:
        subset = frame[frame.tracer == tracer]
        folds = subset.fold.to_numpy()
        for metric in (*ERROR_METRICS, *SCORE_METRICS, "full_vs_no_scores_voxel_mae"):
            values = (subset["delta_" + metric] if metric != "full_vs_no_scores_voxel_mae"
                      else subset[metric]).to_numpy(float)
            if not np.isfinite(values).all():
                raise RuntimeError(f"Nonfinite {tracer} {metric}")
            estimate, ci = paired_bootstrap([values], folds, lambda x: x.mean(),
                                            reps=cfg["statistics"]["bootstrap_replicates"],
                                            seed=cfg["statistics"]["seed"])
            contrast = dict(tracer=tracer, metric=metric, n=len(values), mean=float(estimate),
                            ci_low=float(ci[0]), ci_high=float(ci[1]),
                            meaning="No-Scores minus Full" if metric != "full_vs_no_scores_voxel_mae"
                            else "Full versus No-Scores voxel MAE", unit="normalized uptake"
                            if metric in (*ERROR_METRICS, "full_vs_no_scores_voxel_mae") else
                            ("dB" if metric == "psnr" else "dimensionless"))
            if metric in ERROR_METRICS:
                contrast["p_permutation"] = float(stats.permutation_test(
                    (values,), lambda x: x.mean(), permutation_type="samples",
                    n_resamples=10000, random_state=cfg["statistics"]["seed"]).pvalue)
            contrasts.append(contrast)
    for metric in ERROR_METRICS:
        pair = [r for r in contrasts if r["metric"] == metric]
        adjusted = holm_two(np.array([r["p_permutation"] for r in pair]))
        for row, p in zip(pair, adjusted):
            row["p_holm_within_endpoint_two_tracers"] = float(p)
    out = REPORT / "full" / "paired_summary"
    out.mkdir(exist_ok=False)
    with (out / "contrasts.csv").open("x", newline="") as f:
        fields = list(dict.fromkeys(k for r in contrasts for k in r))
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(contrasts)
    write_json(out / "summary.json", dict(status="COMPLETE", subjects=frame.ptid.nunique(),
        volumes=len(frame), contrasts=contrasts,
        bootstrap="10000 subject draws stratified within outer folds; seed 20261017",
        multiplicity="Holm within each primary endpoint across FDG and AV45",
        interpretation="fixed Full weights, alternative inference-time patient token; normalized uptake only"))


if __name__ == "__main__":
    main()
