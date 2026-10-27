#!/usr/bin/env python3
"""Stage 3A: frozen-ROI normalized-uptake accuracy for Full versus OT.

Reads only the verified epoch-165 OOF predictions and E1 caches.  It performs
no inference, registration, resampling, classification, SUV/SUVR calculation,
or ROI selection.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import stats
from scipy import ndimage


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
E1 = ROOT / "reports/e1_stage01_20261017"
SPATIAL_RESULTS = OUT / "02_spatial_validation_results.json"
PREDICTION_INDEX = OUT / "02_prediction_identity_checks.csv"
EPOCH = 165
REPS = 10_000
SEED = 20261017
UNIT = "normalized uptake (arbitrary units)"


def read_json(path: Path):
    return json.loads(path.read_text())


def write_json(path: Path, value) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def load_protocol() -> dict:
    spatial = read_json(SPATIAL_RESULTS)
    if not spatial.get("pass") or spatial.get("subjects_checked") != 1856:
        raise RuntimeError("Stage 2 spatial PASS for 1,856 subjects is required")
    config = read_json(E1 / "config.json")
    labels = pd.read_csv(E1 / "roi_labels.csv")
    if len(labels) != labels.region.nunique() or len(labels) != 98:
        raise RuntimeError("Frozen ROI label table is not 98 unique labels")
    validity = read_json(E1 / "roi_validity.json")
    physical = read_json(E1 / "hemisphere_label_map.json")["labels"]
    for path in (E1 / "roi_labels.csv", E1 / "roi_validity.json", E1 / "hemisphere_label_map.json"):
        expected = config["frozen_files"][str(path.resolve())]
        if sha256(path) != expected:
            raise RuntimeError(f"Frozen E1 asset changed: {path}")
    if config["statistics"]["bootstrap_replicates"] != REPS or config["statistics"]["seed"] != SEED:
        raise RuntimeError("E1 statistical seed/repetition contract changed")

    cohort = read_json(E1 / "cohort.json")
    excluded = {x["ptid"] for x in read_json(E1 / "qc_exclusions.json")["excluded"]}
    active = [r for r in cohort if r["ptid"] not in excluded]
    if len(active) != 1856:
        raise RuntimeError(f"Expected 1,856 active E1 subjects, got {len(active)}")

    pred = pd.read_csv(PREDICTION_INDEX)
    pred = pred[(pred.epoch == EPOCH) & (pred["pass"] == True)].copy()  # noqa: E712
    if len(pred) != 5922 or pred.duplicated(["model", "ptid", "tracer", "fold"]).any():
        raise RuntimeError("Verified prediction index is incomplete or duplicated")
    if set(pred.model) != {"Full", "OT"}:
        raise RuntimeError("Unexpected model identities")
    paths = pred.set_index(["model", "ptid", "tracer"])["prediction"].to_dict()
    folds = pred.groupby("ptid").fold.nunique()
    if not (folds == 1).all():
        raise RuntimeError("A PTID occurs in more than one Full/OT OOF fold")
    fold_by_ptid = pred.groupby("ptid").fold.first().astype(int).to_dict()
    active_ids = {r["ptid"] for r in active}
    if set(fold_by_ptid) != active_ids:
        raise RuntimeError("Prediction subjects differ from E1 active cohort")
    expected_keys = {
        (m, r["ptid"], t)
        for m in ("Full", "OT") for r in active for t in ("fdg", "av45") if r[f"has_{t}"]
    }
    if set(paths) != expected_keys:
        raise RuntimeError("Prediction tracer availability differs from E1")

    label_ids = labels.region.astype(int).to_numpy()
    segmenter_names = labels.set_index("region").region_name.to_dict()
    physical_names = {int(label): physical[str(int(label))]["physical_name"] for label in label_ids}
    if len(set(physical_names.values())) != 98:
        raise RuntimeError("Physical ROI names are not unique")
    invalid = {ptid: set(map(int, values)) for ptid, values in validity["invalid_rois"].items()}
    if not set(invalid).issubset(active_ids):
        raise RuntimeError("ROI validity contains non-active subjects")
    if any(not bad.issubset(set(label_ids)) for bad in invalid.values()):
        raise RuntimeError("ROI validity contains unknown labels")
    key_rois = {t: set(map(int, ids)) for t, ids in config["key_rois"].items()}
    if any(not ids.issubset(set(label_ids)) for ids in key_rois.values()):
        raise RuntimeError("Key ROI set is outside frozen 98 labels")

    return {
        "config": config,
        "labels": label_ids,
        "segmenter_names": segmenter_names,
        "physical_names": physical_names,
        "invalid": invalid,
        "key_rois": key_rois,
        "active": active,
        "paths": paths,
        "fold_by_ptid": fold_by_ptid,
        "source_hashes": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in [
                OUT / "01_roi_protocol_recon.md",
                OUT / "02_spatial_compatibility_report.md",
                SPATIAL_RESULTS,
                ROOT / "experiments/e1_clinical_conditioning/evaluate.py",
                E1 / "config.json", E1 / "roi_labels.csv", E1 / "roi_validity.json",
                E1 / "hemisphere_label_map.json", PREDICTION_INDEX,
            ]
        },
    }


def regional_values(array: np.ndarray, flat_mask: np.ndarray, labels: np.ndarray, counts: np.ndarray) -> np.ndarray:
    if array.shape != (160, 192, 160) or array.dtype != np.float32 or not np.isfinite(array).all():
        raise ValueError(f"Invalid image array: shape={array.shape}, dtype={array.dtype}")
    sums = np.bincount(flat_mask, weights=array.ravel(), minlength=2036)
    return np.asarray([sums[label] / counts[label] if counts[label] else np.nan for label in labels], dtype=np.float64)


def subject_task(task: dict) -> dict:
    try:
        labels = np.asarray(task["labels"], dtype=int)
        with np.load(task["cache"], allow_pickle=False) as saved:
            mask = np.asarray(saved["mask"])
            reals = {tracer: np.asarray(saved[tracer], dtype=np.float32) for tracer in task["tracers"]}
        if mask.shape != (160, 192, 160) or not np.issubdtype(mask.dtype, np.integer):
            raise ValueError(f"Invalid mask: {mask.shape}/{mask.dtype}")
        flat_mask = mask.ravel().astype(np.int64, copy=False)
        counts = np.bincount(flat_mask, minlength=2036)
        bad = set(task["invalid"])
        rows = []
        for tracer in task["tracers"]:
            full = nib.load(task["paths"][f"Full:{tracer}"]).get_fdata(dtype=np.float32)
            ot = nib.load(task["paths"][f"OT:{tracer}"]).get_fdata(dtype=np.float32)
            real_values = regional_values(reals[tracer], flat_mask, labels, counts)
            full_values = regional_values(full, flat_mask, labels, counts)
            ot_values = regional_values(ot, flat_mask, labels, counts)
            for index, label in enumerate(labels):
                valid = int(label) not in bad and counts[label] > 0
                real_value = float(real_values[index]) if valid else np.nan
                full_value = float(full_values[index]) if valid else np.nan
                ot_value = float(ot_values[index]) if valid else np.nan
                rows.append(
                    {
                        "ptid": task["ptid"], "fold": task["fold"], "tracer": tracer,
                        "roi_id": int(label), "segmenter_name": task["segmenter_names"][str(int(label))],
                        "physical_name": task["physical_names"][str(int(label))],
                        "is_key_roi": int(label) in task["key_rois"][tracer],
                        "roi_valid": bool(valid), "voxel_count": int(counts[label]),
                        "real_uptake": real_value, "full_uptake": full_value, "ot_uptake": ot_value,
                        "abs_error_full": abs(full_value - real_value) if valid else np.nan,
                        "abs_error_ot": abs(ot_value - real_value) if valid else np.nan,
                        "delta_abs_error_ot_minus_full": abs(ot_value - real_value) - abs(full_value - real_value) if valid else np.nan,
                        "unit": UNIT,
                    }
                )
        return {"ptid": task["ptid"], "rows": rows, "error": ""}
    except Exception as exc:
        return {"ptid": task["ptid"], "rows": [], "error": repr(exc)}


def tasks(protocol: dict, ptids: list[str]) -> list[dict]:
    chosen = set(ptids)
    result = []
    for row in protocol["active"]:
        ptid = row["ptid"]
        if ptid not in chosen:
            continue
        tracers = [t for t in ("fdg", "av45") if row[f"has_{t}"]]
        result.append(
            {
                "ptid": ptid, "fold": protocol["fold_by_ptid"][ptid], "cache": row["cache"],
                "tracers": tracers, "labels": protocol["labels"].tolist(),
                "invalid": sorted(protocol["invalid"].get(ptid, set())),
                "segmenter_names": {str(k): v for k, v in protocol["segmenter_names"].items()},
                "physical_names": {str(k): v for k, v in protocol["physical_names"].items()},
                "key_rois": {k: sorted(v) for k, v in protocol["key_rois"].items()},
                "paths": {
                    f"{model}:{tracer}": protocol["paths"][(model, ptid, tracer)]
                    for model in ("Full", "OT") for tracer in tracers
                },
            }
        )
    return result


def extract(protocol: dict, ptids: list[str], workers: int) -> tuple[pd.DataFrame, list[dict]]:
    results, errors = [], []
    started = time.time()
    todo = tasks(protocol, ptids)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        future_map = {pool.submit(subject_task, task): task["ptid"] for task in todo}
        for number, future in enumerate(as_completed(future_map), 1):
            result = future.result()
            if result["error"]:
                errors.append({"ptid": result["ptid"], "error": result["error"]})
            else:
                results.extend(result["rows"])
            if number == 1 or number % 100 == 0 or number == len(todo):
                print(json.dumps({"event": "roi_extract", "done": number, "total": len(todo), "errors": len(errors), "elapsed_seconds": round(time.time() - started, 1)}), flush=True)
    frame = pd.DataFrame(results).sort_values(["tracer", "ptid", "roi_id"]).reset_index(drop=True)
    return frame, errors


def paired_bootstrap(delta: np.ndarray, folds: np.ndarray, reps=REPS, seed=SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    groups = [np.flatnonzero(folds == fold) for fold in np.unique(folds)]
    samples = []
    for _ in range(reps):
        ids = np.concatenate([rng.choice(group, len(group), replace=True) for group in groups])
        samples.append(float(np.mean(delta[ids])))
    return tuple(map(float, np.quantile(np.asarray(samples), [0.025, 0.975])))


def permutation_p(delta: np.ndarray) -> float:
    return float(
        stats.permutation_test(
            (delta,), lambda values: np.mean(values), permutation_type="samples",
            n_resamples=REPS, alternative="two-sided", random_state=SEED,
        ).pvalue
    )


def holm(pvalues: np.ndarray) -> np.ndarray:
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    ranked = pvalues[order]
    adjusted = np.maximum.accumulate((len(pvalues) - np.arange(len(pvalues))) * ranked)
    adjusted = np.clip(adjusted, 0, 1)
    result = np.empty_like(adjusted)
    result[order] = adjusted
    return result


def benjamini_hochberg(pvalues: np.ndarray) -> np.ndarray:
    pvalues = np.asarray(pvalues, dtype=float)
    order = np.argsort(pvalues)
    ranked = pvalues[order]
    adjusted = ranked * len(pvalues) / np.arange(1, len(pvalues) + 1)
    adjusted = np.minimum.accumulate(adjusted[::-1])[::-1]
    adjusted = np.clip(adjusted, 0, 1)
    result = np.empty_like(adjusted)
    result[order] = adjusted
    return result


def comparison_row(table: pd.DataFrame, tracer: str, scope: str, fold: int | None) -> dict:
    subset = table[table.tracer == tracer]
    if fold is not None:
        subset = subset[subset.fold == fold]
    delta = subset.delta_ot_minus_full.to_numpy(float)
    folds = subset.fold.to_numpy(int)
    ci_low, ci_high = paired_bootstrap(delta, folds)
    sd = float(np.std(delta, ddof=1))
    full_mean = float(subset.mae_full.mean())
    ot_mean = float(subset.mae_ot.mean())
    effect = float(delta.mean() / sd) if sd > 0 else np.nan
    return {
        "tracer": tracer, "scope": scope, "fold": fold if fold is not None else "all",
        "n": len(subset), "full_mae_mean": full_mean, "ot_mae_mean": ot_mean,
        "delta_ot_minus_full_mean": float(delta.mean()), "delta_ci95_low": ci_low,
        "delta_ci95_high": ci_high, "delta_sd": sd, "delta_median": float(np.median(delta)),
        "paired_cohen_dz": effect,
        "relative_mae_reduction_vs_ot_percent": float(100 * delta.mean() / ot_mean) if ot_mean != 0 else np.nan,
        "full_better_subjects": int(np.sum(delta > 0)), "ties": int(np.sum(delta == 0)),
        "ot_better_subjects": int(np.sum(delta < 0)), "permutation_p_raw": permutation_p(delta),
        "unit": UNIT,
    }


def analyze(regional: pd.DataFrame, protocol: dict) -> dict:
    expected_rows = (1597 + 1364) * 98
    if len(regional) != expected_rows or regional.duplicated(["ptid", "tracer", "fold", "roi_id"]).any():
        raise RuntimeError(f"Regional table identity failure: rows={len(regional)}, expected={expected_rows}")
    invalid_columns = ["real_uptake", "full_uptake", "ot_uptake", "abs_error_full", "abs_error_ot", "delta_abs_error_ot_minus_full"]
    invalid_rows = ~regional.roi_valid
    if not regional.loc[invalid_rows, invalid_columns].isna().all().all():
        raise RuntimeError("Invalid ROI was not excluded simultaneously in Real/Full/OT")
    if regional.loc[~invalid_rows, invalid_columns].isna().any().any():
        raise RuntimeError("Valid ROI contains missing values")

    valid = regional[regional.roi_valid].copy()
    subject = (
        valid.groupby(["ptid", "fold", "tracer"], as_index=False)
        .agg(valid_roi_count=("roi_id", "size"), mae_full=("abs_error_full", "mean"), mae_ot=("abs_error_ot", "mean"))
    )
    subject["delta_ot_minus_full"] = subject.mae_ot - subject.mae_full
    subject["unit"] = UNIT
    if len(subject) != 2961 or subject.duplicated(["ptid", "fold", "tracer"]).any():
        raise RuntimeError("Subject ROI MAE identity failure")

    primary_rows = []
    for tracer in ("fdg", "av45"):
        primary_rows.append(comparison_row(subject, tracer, "overall_primary", None))
        primary_rows.append(comparison_row(subject, tracer, "fold_descriptive", 1))
        primary_rows.append(comparison_row(subject, tracer, "fold_descriptive", 2))
    primary = pd.DataFrame(primary_rows)
    primary["p_holm_two_primary_tracers"] = np.nan
    overall_mask = primary.scope == "overall_primary"
    primary.loc[overall_mask, "p_holm_two_primary_tracers"] = holm(primary.loc[overall_mask, "permutation_p_raw"].to_numpy())

    roi_rows = []
    for (tracer, roi_id), group in valid.groupby(["tracer", "roi_id"], sort=True):
        delta = group.delta_abs_error_ot_minus_full.to_numpy(float)
        folds = group.fold.to_numpy(int)
        ci_low, ci_high = paired_bootstrap(delta, folds)
        fold1 = group[group.fold == 1].delta_abs_error_ot_minus_full
        fold2 = group[group.fold == 2].delta_abs_error_ot_minus_full
        sd = float(np.std(delta, ddof=1))
        roi_rows.append(
            {
                "tracer": tracer, "roi_id": int(roi_id),
                "segmenter_name": group.segmenter_name.iloc[0], "physical_name": group.physical_name.iloc[0],
                "is_key_roi": bool(group.is_key_roi.iloc[0]), "n": len(group),
                "n_fold1": len(fold1), "n_fold2": len(fold2),
                "full_mae_mean": float(group.abs_error_full.mean()), "ot_mae_mean": float(group.abs_error_ot.mean()),
                "delta_ot_minus_full_mean": float(delta.mean()), "delta_ci95_low": ci_low, "delta_ci95_high": ci_high,
                "delta_fold1_mean": float(fold1.mean()), "delta_fold2_mean": float(fold2.mean()),
                "delta_sd": sd, "paired_cohen_dz": float(delta.mean() / sd) if sd > 0 else np.nan,
                "permutation_p_raw": permutation_p(delta), "unit": UNIT,
            }
        )
    per_roi = pd.DataFrame(roi_rows)
    if len(per_roi) != 196:
        raise RuntimeError(f"Expected 196 tracer-ROI comparisons, got {len(per_roi)}")
    per_roi["q_bh_196"] = benjamini_hochberg(per_roi.permutation_p_raw.to_numpy())
    per_roi["fdr_significant_0_05"] = per_roi.q_bh_196 < 0.05
    per_roi["direction"] = np.where(per_roi.delta_ot_minus_full_mean > 0, "Full", np.where(per_roi.delta_ot_minus_full_mean < 0, "OT", "Tie"))
    key = per_roi[per_roi.is_key_roi].copy().sort_values(["tracer", "roi_id"])
    if len(key) != 20:
        raise RuntimeError(f"Expected 20 tracer-specific key ROIs, got {len(key)}")

    complete = subject[subject.valid_roi_count == 98]
    integrity = {
        "regional_rows": len(regional), "valid_regional_rows": len(valid),
        "invalid_regional_rows": int(invalid_rows.sum()),
        "subject_tracer_rows": len(subject),
        "subjects": int(subject.ptid.nunique()),
        "tracer_counts": subject.groupby("tracer").size().astype(int).to_dict(),
        "fold_tracer_counts": {f"fold{f}_{t}": int(len(subject[(subject.fold == f) & (subject.tracer == t)])) for f in (1, 2) for t in ("fdg", "av45")},
        "valid_roi_count_min": int(subject.valid_roi_count.min()), "valid_roi_count_max": int(subject.valid_roi_count.max()),
        "complete98_subject_tracer_rows": len(complete),
        "subject_tracer_rows_with_invalid_roi": int(len(subject) - len(complete)),
        "duplicate_regional_keys": int(regional.duplicated(["ptid", "tracer", "fold", "roi_id"]).sum()),
        "duplicate_subject_keys": int(subject.duplicated(["ptid", "tracer", "fold"]).sum()),
        "missing_valid_values": int(regional.loc[~invalid_rows, invalid_columns].isna().sum().sum()),
        "invalid_rows_all_three_uptakes_excluded": bool(regional.loc[invalid_rows, ["real_uptake", "full_uptake", "ot_uptake"]].isna().all().all()),
    }
    return {"subject": subject, "primary": primary, "per_roi": per_roi, "key": key, "integrity": integrity}


def run_precheck(workers: int) -> None:
    protocol = load_protocol()
    stage2_precheck = read_json(OUT / "02_precheck_results.json")["ptids"]
    regional, errors = extract(protocol, stage2_precheck, workers)
    if errors:
        raise RuntimeError(f"Precheck extraction failures: {errors}")
    sys.path.insert(0, str(ROOT / "experiments/e1_clinical_conditioning"))
    import evaluate as e1_evaluate

    max_e1_difference = 0.0
    max_direct_difference = 0.0
    invalid_triplet_failures = []
    for task in tasks(protocol, stage2_precheck):
        ptid = task["ptid"]
        with np.load(task["cache"], allow_pickle=False) as saved:
            mask = np.asarray(saved["mask"])
            for tracer in task["tracers"]:
                arrays = {
                    "real": np.asarray(saved[tracer], dtype=np.float32),
                    "full": nib.load(task["paths"][f"Full:{tracer}"]).get_fdata(dtype=np.float32),
                    "ot": nib.load(task["paths"][f"OT:{tracer}"]).get_fdata(dtype=np.float32),
                }
                table = regional[(regional.ptid == ptid) & (regional.tracer == tracer)].set_index("roi_id")
                bad = protocol["invalid"].get(ptid, set())
                for condition, array in arrays.items():
                    reference = e1_evaluate.apply_validity(e1_evaluate.regional(array, mask, protocol["labels"]), protocol["labels"], bad)
                    column = {"real": "real_uptake", "full": "full_uptake", "ot": "ot_uptake"}[condition]
                    observed = table.loc[protocol["labels"], column].to_numpy(float)
                    max_e1_difference = max(max_e1_difference, float(np.nanmax(np.abs(reference - observed))))
                    direct_values = np.asarray(ndimage.mean(array, labels=mask, index=protocol["labels"]), dtype=float)
                    for index, label in enumerate(protocol["labels"]):
                        direct = direct_values[index] if label not in bad else np.nan
                        if np.isfinite(direct):
                            max_direct_difference = max(max_direct_difference, abs(direct - observed[index]))
                invalid_part = table.loc[list(bad)] if bad else table.iloc[0:0]
                if len(invalid_part) and not invalid_part[["real_uptake", "full_uptake", "ot_uptake"]].isna().all().all():
                    invalid_triplet_failures.append({"ptid": ptid, "tracer": tracer})
    result = {
        "pass": bool(max_e1_difference == 0.0 and max_direct_difference <= 1e-6 and not invalid_triplet_failures),
        "subjects": len(stage2_precheck), "regional_rows": len(regional),
        "e1_evaluate_max_abs_difference": max_e1_difference,
        "direct_boolean_mean_max_abs_difference": max_direct_difference,
        "invalid_triplet_failures": invalid_triplet_failures,
        "same_mask_for_real_full_ot": True,
        "ptids": stage2_precheck,
    }
    write_json(OUT / "03a_precheck.json", result)
    print(json.dumps(result), flush=True)
    if not result["pass"]:
        raise SystemExit("ROI precheck failed; full extraction prohibited")


def run_full(workers: int) -> None:
    precheck = OUT / "03a_precheck.json"
    if not precheck.exists() or not read_json(precheck).get("pass"):
        raise SystemExit("Passing Stage 3A precheck is required")
    protocol = load_protocol()
    ptids = sorted(r["ptid"] for r in protocol["active"])
    regional, errors = extract(protocol, ptids, workers)
    if errors:
        write_json(OUT / "03a_extraction_errors.json", errors)
        raise SystemExit(f"ROI extraction failed for {len(errors)} subjects")
    result = analyze(regional, protocol)
    regional.to_csv(OUT / "03a_regional_uptake.csv", index=False, float_format="%.10g")
    result["subject"].to_csv(OUT / "03a_subject_roi_mae.csv", index=False, float_format="%.10g")
    result["primary"].to_csv(OUT / "03a_primary_paired_comparison.csv", index=False, float_format="%.10g")
    result["per_roi"].to_csv(OUT / "03a_per_roi_comparison.csv", index=False, float_format="%.10g")
    result["key"].to_csv(OUT / "03a_key_roi_summary.csv", index=False, float_format="%.10g")
    receipt = {
        "status": "PASS", "epoch": EPOCH, "bootstrap_replicates": REPS, "permutation_resamples": REPS,
        "seed": SEED, "delta_definition": "MAE_OT - MAE_Full; positive favors Full",
        "unit": UNIT, "input_source_hashes": protocol["source_hashes"],
        "integrity": result["integrity"],
        "outputs": {},
    }
    for name in ["03a_regional_uptake.csv", "03a_subject_roi_mae.csv", "03a_primary_paired_comparison.csv", "03a_per_roi_comparison.csv", "03a_key_roi_summary.csv", "03a_precheck.json"]:
        path = OUT / name
        receipt["outputs"][name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    write_json(OUT / "03a_analysis_receipt.json", receipt)
    print(json.dumps({"status": "PASS", **result["integrity"]}, ensure_ascii=False), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("precheck", "run"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.phase == "precheck":
        run_precheck(args.workers)
    else:
        run_full(args.workers)


if __name__ == "__main__":
    main()
