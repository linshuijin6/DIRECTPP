#!/usr/bin/env python3
"""Stage 3B regional agreement and AD/CN contrast preservation.

Consumes Stage 3A regional uptake only. No PET volume access, ROI extraction,
inference, training, registration, classification, or SUV/SUVR calculation.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
E1 = ROOT / "reports/e1_stage01_20261017"
INPUT = OUT / "03a_regional_uptake.csv"
RECEIPT_3A = OUT / "03a_analysis_receipt.json"
REPS = 10_000
SEED = 20261017
SCOPES = ("overall", "fold1", "fold2")

# Recovered from original Fig. 4 and frozen in 01_roi_protocol_recon.md.
PAPER_PANELS = {
    "av45": {
        "A": {1025, 2025, 1032, 2032, 1033, 2033, 1028, 2028},
        "C": {1009, 1015, 1030, 1034},
        "E": {28, 60, 17, 53, 7},
    },
    "fdg": {
        "B": {1025, 2025, 1032, 2032, 1033, 2033, 1028, 2028},
        "D": {17, 53, 1010, 2010, 1031, 2031},
        "F": {10, 49, 2019, 2011, 2013},
    },
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def bh(pvalues: np.ndarray) -> np.ndarray:
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    ranked = pvalues[order]
    adjusted = ranked * len(ranked) / np.arange(1, len(ranked) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    result = np.empty_like(adjusted)
    result[order] = np.clip(adjusted, 0, 1)
    return result


def bootstrap_p(samples: np.ndarray) -> float:
    lower = (np.count_nonzero(samples <= 0) + 1) / (len(samples) + 1)
    upper = (np.count_nonzero(samples >= 0) + 1) / (len(samples) + 1)
    return float(min(1.0, 2 * min(lower, upper)))


def agreement_metrics(real: np.ndarray, pred: np.ndarray) -> dict:
    if len(real) < 3 or len(real) != len(pred):
        raise ValueError("Agreement requires at least three paired observations")
    bias_values = pred - real
    vx = real.var(ddof=1)
    vy = pred.var(ddof=1)
    cov = np.cov(real, pred, ddof=1)[0, 1]
    ccc = 2 * cov / (vx + vy + (real.mean() - pred.mean()) ** 2)
    matrix = np.column_stack([real, pred])
    grand = matrix.mean()
    row = matrix.mean(axis=1)
    col = matrix.mean(axis=0)
    msr = 2 * np.sum((row - grand) ** 2) / (len(real) - 1)
    msc = len(real) * np.sum((col - grand) ** 2)
    mse = np.sum((matrix - row[:, None] - col[None, :] + grand) ** 2) / (len(real) - 1)
    icc = (msr - mse) / (msr + mse + 2 * (msc - mse) / len(real))
    calibration = stats.linregress(real, pred)
    return {
        "n": len(real), "pearson_r": float(stats.pearsonr(real, pred).statistic),
        "ccc": float(ccc), "icc_a1": float(icc), "signed_bias_pred_minus_real": float(bias_values.mean()),
        "loa_low": float(bias_values.mean() - 1.96 * bias_values.std(ddof=1)),
        "loa_high": float(bias_values.mean() + 1.96 * bias_values.std(ddof=1)),
        "calibration_slope": float(calibration.slope), "calibration_intercept": float(calibration.intercept),
    }


def batched_agreement(real: np.ndarray, pred: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """CCC and E1-compatible ICC(A,1) for rows of bootstrap samples."""
    n = real.shape[1]
    mx = real.mean(axis=1)
    my = pred.mean(axis=1)
    dx = real - mx[:, None]
    dy = pred - my[:, None]
    vx = np.sum(dx * dx, axis=1) / (n - 1)
    vy = np.sum(dy * dy, axis=1) / (n - 1)
    cov = np.sum(dx * dy, axis=1) / (n - 1)
    ccc = 2 * cov / (vx + vy + (mx - my) ** 2)

    grand = (mx + my) / 2
    row_mean = (real + pred) / 2
    msr = 2 * np.sum((row_mean - grand[:, None]) ** 2, axis=1) / (n - 1)
    msc = n * ((mx - grand) ** 2 + (my - grand) ** 2)
    residual_x = real - row_mean - mx[:, None] + grand[:, None]
    residual_y = pred - row_mean - my[:, None] + grand[:, None]
    mse = np.sum(residual_x**2 + residual_y**2, axis=1) / (n - 1)
    icc = (msr - mse) / (msr + mse + 2 * (msc - mse) / n)
    return ccc, icc


def resample_indices(rng: np.random.Generator, indices: np.ndarray, batch: int) -> np.ndarray:
    return indices[rng.integers(0, len(indices), size=(batch, len(indices)))]


def agreement_bootstrap(real: np.ndarray, full: np.ndarray, ot: np.ndarray, folds: np.ndarray) -> dict:
    groups = {fold: np.flatnonzero(folds == fold) for fold in (1, 2)}
    if any(len(group) < 3 for group in groups.values()):
        raise ValueError("Insufficient fold observations")
    rng = np.random.default_rng(SEED)
    saved = {scope: {metric: np.empty(REPS) for metric in ("delta_ccc", "delta_icc")} for scope in SCOPES}
    offset = 0
    while offset < REPS:
        batch = min(100, REPS - offset)
        ids1 = resample_indices(rng, groups[1], batch)
        ids2 = resample_indices(rng, groups[2], batch)
        for scope, ids in (("fold1", ids1), ("fold2", ids2), ("overall", np.concatenate([ids1, ids2], axis=1))):
            rf, ff, oo = real[ids], full[ids], ot[ids]
            ccc_full, icc_full = batched_agreement(rf, ff)
            ccc_ot, icc_ot = batched_agreement(rf, oo)
            saved[scope]["delta_ccc"][offset:offset + batch] = ccc_full - ccc_ot
            saved[scope]["delta_icc"][offset:offset + batch] = icc_full - icc_ot
        offset += batch
    result = {}
    for scope in SCOPES:
        result[scope] = {}
        for metric in ("delta_ccc", "delta_icc"):
            values = saved[scope][metric]
            result[scope][metric] = {
                "ci_low": float(np.quantile(values, 0.025)), "ci_high": float(np.quantile(values, 0.975)),
                "p_raw": bootstrap_p(values),
            }
    return result


def disease_bootstrap(real: np.ndarray, full: np.ndarray, ot: np.ndarray, folds: np.ndarray, diagnosis: np.ndarray) -> dict:
    groups = {(fold, dx): np.flatnonzero((folds == fold) & (diagnosis == dx)) for fold in (1, 2) for dx in ("AD", "CN")}
    if any(len(group) < 2 for group in groups.values()):
        raise ValueError("Insufficient fold-diagnosis observations")
    rng = np.random.default_rng(SEED)
    saved = {scope: np.empty(REPS) for scope in SCOPES}
    offset = 0
    while offset < REPS:
        batch = min(250, REPS - offset)
        sampled = {key: resample_indices(rng, group, batch) for key, group in groups.items()}
        for scope, use_folds in (("fold1", (1,)), ("fold2", (2,)), ("overall", (1, 2))):
            ids_ad = np.concatenate([sampled[(fold, "AD")] for fold in use_folds], axis=1)
            ids_cn = np.concatenate([sampled[(fold, "CN")] for fold in use_folds], axis=1)
            contrast_real = real[ids_ad].mean(axis=1) - real[ids_cn].mean(axis=1)
            contrast_full = full[ids_ad].mean(axis=1) - full[ids_cn].mean(axis=1)
            contrast_ot = ot[ids_ad].mean(axis=1) - ot[ids_cn].mean(axis=1)
            saved[scope][offset:offset + batch] = np.abs(contrast_ot - contrast_real) - np.abs(contrast_full - contrast_real)
        offset += batch
    return {
        scope: {
            "ci_low": float(np.quantile(values, 0.025)), "ci_high": float(np.quantile(values, 0.975)),
            "p_raw": bootstrap_p(values),
        }
        for scope, values in saved.items()
    }


def flags(tracer: str, roi_id: int, key_rois: dict) -> dict:
    panels = [panel for panel, ids in PAPER_PANELS[tracer].items() if roi_id in ids]
    return {
        "is_key_roi": roi_id in key_rois[tracer],
        "is_paper_displayed_roi": bool(panels),
        "paper_figure_panels": ";".join(f"Fig4{panel}" for panel in panels),
    }


def scoped(group: pd.DataFrame, scope: str) -> pd.DataFrame:
    if scope == "fold1":
        return group[group.fold == 1]
    if scope == "fold2":
        return group[group.fold == 2]
    return group


def load_and_validate() -> tuple[pd.DataFrame, dict, dict]:
    receipt = read_json(RECEIPT_3A)
    expected = receipt["outputs"][INPUT.name]
    if sha256(INPUT) != expected["sha256"] or INPUT.stat().st_size != expected["bytes"]:
        raise RuntimeError("Stage 3A regional uptake identity mismatch")
    if receipt["epoch"] != 165 or receipt["status"] != "PASS":
        raise RuntimeError("Stage 3A PASS/Epoch 165 receipt required")
    data = pd.read_csv(INPUT)
    if len(data) != 290178 or data.duplicated(["ptid", "tracer", "fold", "roi_id"]).any():
        raise RuntimeError("Stage 3A row identity failure")
    invalid = ~data.roi_valid
    values = ["real_uptake", "full_uptake", "ot_uptake"]
    if not data.loc[invalid, values].isna().all().all() or data.loc[~invalid, values].isna().any().any():
        raise RuntimeError("Stage 3A validity/missingness failure")
    data = data[~invalid].copy()
    config = read_json(E1 / "config.json")
    labels = pd.read_csv(E1 / "roi_labels.csv")
    if set(data.roi_id) != set(labels.region) or len(labels) != 98:
        raise RuntimeError("ROI definition mismatch")
    for path in (E1 / "roi_labels.csv", E1 / "roi_validity.json", E1 / "hemisphere_label_map.json"):
        if sha256(path) != config["frozen_files"][str(path.resolve())]:
            raise RuntimeError(f"Frozen E1 asset changed: {path}")
    cohort = read_json(E1 / "cohort.json")
    diagnosis = {row["ptid"]: row["diagnosis"] for row in cohort}
    data["diagnosis"] = data.ptid.map(diagnosis)
    if data.diagnosis.isna().any():
        raise RuntimeError("Missing diagnosis")
    key_rois = {tracer: set(map(int, ids)) for tracer, ids in config["key_rois"].items()}
    return data, key_rois, receipt


def run() -> None:
    started = time.time()
    data, key_rois, receipt_3a = load_and_validate()
    agreement_rows = []
    comparison_rows = []
    disease_rows = []
    grouped = list(data.groupby(["tracer", "roi_id"], sort=True))
    for number, ((tracer, roi_id), group) in enumerate(grouped, 1):
        group = group.sort_values("ptid")
        common = {
            "real": group.real_uptake.to_numpy(float), "full": group.full_uptake.to_numpy(float),
            "ot": group.ot_uptake.to_numpy(float), "folds": group.fold.to_numpy(int),
        }
        boot = agreement_bootstrap(common["real"], common["full"], common["ot"], common["folds"])
        tag = flags(tracer, int(roi_id), key_rois)
        base = {
            "tracer": tracer, "roi_id": int(roi_id), "segmenter_name": group.segmenter_name.iloc[0],
            "physical_name": group.physical_name.iloc[0], **tag,
        }
        for scope in SCOPES:
            part = scoped(group, scope)
            real = part.real_uptake.to_numpy(float)
            metrics = {}
            for model, column in (("Full", "full_uptake"), ("OT", "ot_uptake")):
                values = agreement_metrics(real, part[column].to_numpy(float))
                agreement_rows.append({**base, "scope": scope, "fold": "all" if scope == "overall" else int(scope[-1]), "model": model, **values})
                metrics[model] = values
            comparison_rows.append(
                {
                    **base, "scope": scope, "fold": "all" if scope == "overall" else int(scope[-1]), "n": len(part),
                    "ccc_full": metrics["Full"]["ccc"], "ccc_ot": metrics["OT"]["ccc"],
                    "delta_ccc_full_minus_ot": metrics["Full"]["ccc"] - metrics["OT"]["ccc"],
                    "delta_ccc_ci95_low": boot[scope]["delta_ccc"]["ci_low"], "delta_ccc_ci95_high": boot[scope]["delta_ccc"]["ci_high"],
                    "delta_ccc_bootstrap_p_raw": boot[scope]["delta_ccc"]["p_raw"],
                    "icc_full": metrics["Full"]["icc_a1"], "icc_ot": metrics["OT"]["icc_a1"],
                    "delta_icc_full_minus_ot": metrics["Full"]["icc_a1"] - metrics["OT"]["icc_a1"],
                    "delta_icc_ci95_low": boot[scope]["delta_icc"]["ci_low"], "delta_icc_ci95_high": boot[scope]["delta_icc"]["ci_high"],
                    "delta_icc_bootstrap_p_raw": boot[scope]["delta_icc"]["p_raw"],
                }
            )

        disease = group[group.diagnosis.isin(["AD", "CN"])].copy()
        disease_boot = disease_bootstrap(
            disease.real_uptake.to_numpy(float), disease.full_uptake.to_numpy(float), disease.ot_uptake.to_numpy(float),
            disease.fold.to_numpy(int), disease.diagnosis.to_numpy(str),
        )
        for scope in SCOPES:
            part = scoped(disease, scope)
            ad = part[part.diagnosis == "AD"]
            cn = part[part.diagnosis == "CN"]
            contrasts = {
                name: float(ad[column].mean() - cn[column].mean())
                for name, column in (("real", "real_uptake"), ("full", "full_uptake"), ("ot", "ot_uptake"))
            }
            error_full = abs(contrasts["full"] - contrasts["real"])
            error_ot = abs(contrasts["ot"] - contrasts["real"])
            disease_rows.append(
                {
                    **base, "scope": scope, "fold": "all" if scope == "overall" else int(scope[-1]),
                    "n_ad": len(ad), "n_cn": len(cn), "contrast_real_ad_minus_cn": contrasts["real"],
                    "contrast_full_ad_minus_cn": contrasts["full"], "contrast_ot_ad_minus_cn": contrasts["ot"],
                    "contrast_error_full": error_full, "contrast_error_ot": error_ot,
                    "delta_error_ot_minus_full": error_ot - error_full,
                    "delta_error_ci95_low": disease_boot[scope]["ci_low"], "delta_error_ci95_high": disease_boot[scope]["ci_high"],
                    "delta_error_bootstrap_p_raw": disease_boot[scope]["p_raw"],
                }
            )
        if number == 1 or number % 20 == 0 or number == len(grouped):
            print(json.dumps({"event": "regional_analysis", "done": number, "total": len(grouped), "elapsed_seconds": round(time.time() - started, 1)}), flush=True)

    agreement = pd.DataFrame(agreement_rows)
    comparison = pd.DataFrame(comparison_rows)
    disease = pd.DataFrame(disease_rows)
    overall = comparison.scope == "overall"
    comparison["delta_ccc_q_bh_196"] = np.nan
    comparison["delta_icc_q_bh_196"] = np.nan
    comparison.loc[overall, "delta_ccc_q_bh_196"] = bh(comparison.loc[overall, "delta_ccc_bootstrap_p_raw"].to_numpy())
    comparison.loc[overall, "delta_icc_q_bh_196"] = bh(comparison.loc[overall, "delta_icc_bootstrap_p_raw"].to_numpy())
    comparison["ccc_direction"] = np.where(comparison.delta_ccc_full_minus_ot > 0, "Full", np.where(comparison.delta_ccc_full_minus_ot < 0, "OT", "Tie"))
    comparison["icc_direction"] = np.where(comparison.delta_icc_full_minus_ot > 0, "Full", np.where(comparison.delta_icc_full_minus_ot < 0, "OT", "Tie"))

    disease_overall = disease.scope == "overall"
    disease["delta_error_q_bh_196"] = np.nan
    disease.loc[disease_overall, "delta_error_q_bh_196"] = bh(disease.loc[disease_overall, "delta_error_bootstrap_p_raw"].to_numpy())
    disease["contrast_error_direction"] = np.where(disease.delta_error_ot_minus_full > 0, "Full", np.where(disease.delta_error_ot_minus_full < 0, "OT", "Tie"))

    summary_ids = set(
        (tracer, roi_id)
        for tracer in ("fdg", "av45")
        for roi_id in key_rois[tracer] | set().union(*PAPER_PANELS[tracer].values())
    )
    comparison_overall = comparison[overall].copy()
    disease_overall_table = disease[disease_overall].copy()
    summary = comparison_overall.merge(
        disease_overall_table[
            ["tracer", "roi_id", "n_ad", "n_cn", "contrast_real_ad_minus_cn", "contrast_full_ad_minus_cn",
             "contrast_ot_ad_minus_cn", "contrast_error_full", "contrast_error_ot", "delta_error_ot_minus_full",
             "delta_error_ci95_low", "delta_error_ci95_high", "delta_error_bootstrap_p_raw", "delta_error_q_bh_196",
             "contrast_error_direction"]
        ], on=["tracer", "roi_id"], validate="one_to_one",
    )
    summary = summary[[ (row.tracer, int(row.roi_id)) in summary_ids for row in summary.itertuples() ]].sort_values(["tracer", "roi_id"])

    agreement.to_csv(OUT / "03b_regional_agreement.csv", index=False, float_format="%.10g")
    comparison.to_csv(OUT / "03b_full_ot_agreement_comparison.csv", index=False, float_format="%.10g")
    disease.to_csv(OUT / "03b_disease_contrast.csv", index=False, float_format="%.10g")
    summary.to_csv(OUT / "03b_key_and_paper_roi_summary.csv", index=False, float_format="%.10g")

    integrity = {
        "stage3a_input_sha256": sha256(INPUT), "stage3a_input_bytes": INPUT.stat().st_size,
        "stage3a_receipt_expected_sha256": receipt_3a["outputs"][INPUT.name]["sha256"],
        "input_rows_total": 290178, "input_rows_valid": len(data), "subjects": int(data.ptid.nunique()),
        "tracer_subjects": {tracer: int(data[data.tracer == tracer].ptid.nunique()) for tracer in ("fdg", "av45")},
        "agreement_rows": len(agreement), "comparison_rows": len(comparison), "disease_rows": len(disease),
        "key_and_paper_summary_rows": len(summary),
        "agreement_duplicate_keys": int(agreement.duplicated(["tracer", "roi_id", "scope", "model"]).sum()),
        "comparison_duplicate_keys": int(comparison.duplicated(["tracer", "roi_id", "scope"]).sum()),
        "disease_duplicate_keys": int(disease.duplicated(["tracer", "roi_id", "scope"]).sum()),
        "agreement_families": {
            "delta_ccc": "196 overall tracer-ROI tests, BH-FDR",
            "delta_icc_a1": "196 overall tracer-ROI tests, BH-FDR",
            "fold_rows": "descriptive repeatability checks; no q-values",
        },
        "disease_family": "196 overall tracer-ROI contrast-error tests, diagnosis+fold-stratified subject bootstrap, BH-FDR",
        "delta_directions": {"agreement": "Full minus OT; positive favors Full", "disease": "Error_OT minus Error_Full; positive favors Full"},
        "paper_roi_source": "manuscript Fig. 4 panels A-F, mapped in 01_roi_protocol_recon.md; marking only, not added to E1 key set",
    }
    if integrity["agreement_duplicate_keys"] or integrity["comparison_duplicate_keys"] or integrity["disease_duplicate_keys"]:
        raise RuntimeError("Duplicate output identities")
    output_names = [
        "03b_regional_agreement.csv", "03b_full_ot_agreement_comparison.csv",
        "03b_disease_contrast.csv", "03b_key_and_paper_roi_summary.csv",
    ]
    output_receipts = {
        name: {"sha256": sha256(OUT / name), "bytes": (OUT / name).stat().st_size}
        for name in output_names
    }
    receipt = {
        "status": "PASS", "epoch": 165, "bootstrap_replicates": REPS, "seed": SEED,
        "input_and_integrity": integrity, "outputs": output_receipts,
        "source_hashes": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [
                ROOT / "manuscript/BMEF_main.tex", OUT / "01_roi_protocol_recon.md",
                OUT / "03a_roi_accuracy_report.md", INPUT, RECEIPT_3A,
                ROOT / "experiments/e1_clinical_conditioning/evaluate.py", E1 / "config.json",
                E1 / "roi_labels.csv", E1 / "roi_validity.json", E1 / "hemisphere_label_map.json",
            ]
        },
        "elapsed_seconds": time.time() - started,
    }
    write_json(OUT / "03b_analysis_receipt.json", receipt)
    print(json.dumps({"status": "PASS", **integrity}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    run()
