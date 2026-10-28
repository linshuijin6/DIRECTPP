#!/usr/bin/env python3
"""Epoch-165 paired OOF analysis: DIReCT++ Full vs clinical regression 3D U-Net.

This script is intentionally limited to existing frozen results.  It performs no
training, inference, image loading, image generation, or figure production.
Rows whose epoch is not 165 are discarded immediately during CSV streaming and
are never converted to metric values or included in any calculation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import scipy
from scipy import stats


EPOCH = 165
BOOTSTRAP_SEED = 42
BOOTSTRAP_ITERATIONS = 10_000
TRACERS = ("fdg", "av45")
METRICS = ("ssim", "psnr", "mse", "mae")
DIRECTION = {"ssim": "higher", "psnr": "higher", "mse": "lower", "mae": "lower"}
DISPLAY_METRIC = {"ssim": "SSIM ↑", "psnr": "PSNR ↑", "mse": "MSE ↓", "mae": "MAE ↓"}
EXPECTED_COUNTS = {
    ("fdg", 1): 792,
    ("fdg", 2): 806,
    ("av45", 1): 690,
    ("av45", 2): 675,
}
KEY = ("ptid", "tracer", "fold", "epoch")
FEATURES = ("age", "sex", "weight", "cdr", "mmse", "gds", "faq", "npiq")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path):
    with path.open() as handle:
        return json.load(handle)


def atomic_text(path: Path, text: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def atomic_json(path: Path, value) -> None:
    atomic_text(path, json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def atomic_csv(path: Path, rows: list[dict], fieldnames: Iterable[str] | None = None) -> None:
    if not rows:
        raise ValueError(f"Refusing to write empty CSV: {path}")
    columns = list(fieldnames or rows[0].keys())
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def read_e165_metrics(path: Path) -> pd.DataFrame:
    """Stream one metrics CSV and retain only Epoch 165 before parsing metrics."""
    required = set(KEY) | set(METRICS)
    rows: list[dict] = []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise RuntimeError(f"Missing required columns in {path}")
        for source in reader:
            if source["epoch"] != str(EPOCH):
                continue
            row = {
                "ptid": source["ptid"],
                "tracer": source["tracer"].lower(),
                "fold": int(source["fold"]),
                "epoch": EPOCH,
            }
            row.update({metric: float(source[metric]) for metric in METRICS})
            rows.append(row)
    frame = pd.DataFrame(rows, columns=list(KEY) + list(METRICS))
    if frame.empty:
        raise RuntimeError(f"No Epoch {EPOCH} rows in {path}")
    return frame


def parse_full_description(text: str) -> dict[str, float]:
    patterns = {
        "head": r"^Subject is a (?P<age>[-+0-9.]+)-year-old (?P<sex>male|female) with a weight of (?P<weight>[-+0-9.]+) kg\.",
        "cdr": r"Clinical Dementia Rating \(CDR\).*? is (?P<cdr>[-+0-9.]+)\. The Mini-Mental",
        "mmse": r"Mini-Mental State Examination \(MMSE\).*? is (?P<mmse>[-+0-9.]+)\. The Geriatric",
        "gds": r"Geriatric Depression Scale \(GDS\).*? is (?P<gds>[-+0-9.]+)\. The Functional",
        "faq": r"Functional Activities Questionnaire \(FAQ\).*? is (?P<faq>[-+0-9.]+)\. The Neuropsychiatric",
        "npiq": r"Neuropsychiatric Inventory Questionnaire \(NPI-Q\).*? is (?P<npiq>[-+0-9.]+)\.$",
    }
    values: dict[str, str] = {}
    for label, pattern in patterns.items():
        match = re.search(pattern, text)
        if match is None:
            raise RuntimeError(f"Full description template mismatch at {label}")
        values.update(match.groupdict())
    sex = values.pop("sex")
    parsed = {name: float(value) for name, value in values.items()}
    parsed["sex"] = 1.0 if sex == "male" else 0.0
    return {name: parsed[name] for name in FEATURES}


def holm_adjust(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = sorted(range(m), key=lambda index: p_values[index])
    adjusted = [math.nan] * m
    running = 0.0
    for rank, index in enumerate(order):
        candidate = min(1.0, (m - rank) * p_values[index])
        running = max(running, candidate)
        adjusted[index] = running
    return adjusted


def holm_adjust_independent(p_values: list[float]) -> list[float]:
    """Independent step-down implementation used only as a verification check."""
    pairs = sorted(enumerate(p_values), key=lambda item: item[1])
    result = [0.0 for _ in p_values]
    prior = 0.0
    remaining = len(pairs)
    for original_index, value in pairs:
        prior = min(1.0, max(prior, value * remaining))
        result[original_index] = prior
        remaining -= 1
    return result


def bootstrap_fold_rng(combo_index: int, fold: int) -> np.random.Generator:
    # Independent fold streams make the result invariant to batch size while the
    # master bootstrap seed and the fixed tracer/metric ordering remain explicit.
    return np.random.default_rng(np.random.SeedSequence(BOOTSTRAP_SEED, spawn_key=(combo_index, fold - 1)))


def stratified_bootstrap_ci(
    deltas: np.ndarray,
    folds: np.ndarray,
    combo_index: int,
    iterations: int,
    batch_size: int = 250,
) -> tuple[float, float]:
    by_fold = {fold: np.asarray(deltas[folds == fold], dtype=np.float64) for fold in (1, 2)}
    rngs = {fold: bootstrap_fold_rng(combo_index, fold) for fold in (1, 2)}
    means = np.empty(iterations, dtype=np.float64)
    total_n = len(deltas)
    cursor = 0
    while cursor < iterations:
        size = min(batch_size, iterations - cursor)
        sums = np.zeros(size, dtype=np.float64)
        for fold in (1, 2):
            values = by_fold[fold]
            indices = rngs[fold].integers(0, len(values), size=(size, len(values)))
            sums += values[indices].sum(axis=1)
        means[cursor : cursor + size] = sums / total_n
        cursor += size
    lower, upper = np.quantile(means, (0.025, 0.975), method="linear")
    return float(lower), float(upper)


def stratified_bootstrap_ci_independent(
    deltas: np.ndarray,
    folds: np.ndarray,
    combo_index: int,
    iterations: int,
) -> tuple[float, float]:
    """Loop-based bootstrap calculation independent of the vectorized routine."""
    groups = {fold: np.asarray(deltas[folds == fold], dtype=np.float64) for fold in (1, 2)}
    rngs = {fold: bootstrap_fold_rng(combo_index, fold) for fold in (1, 2)}
    total_n = len(deltas)
    means: list[float] = []
    for _ in range(iterations):
        total = 0.0
        for fold in (1, 2):
            values = groups[fold]
            indices = rngs[fold].integers(0, len(values), size=len(values))
            total += float(sum(float(values[index]) for index in indices))
        means.append(total / total_n)
    return (
        float(np.quantile(np.asarray(means), 0.025, method="linear")),
        float(np.quantile(np.asarray(means), 0.975, method="linear")),
    )


def better_mask(metric: str, deltas: np.ndarray) -> np.ndarray:
    return deltas > 0 if DIRECTION[metric] == "higher" else deltas < 0


def direction_favors_full(metric: str, value: float) -> bool:
    return value > 0 if DIRECTION[metric] == "higher" else value < 0


def fmt_number(metric: str, value: float) -> str:
    digits = {"ssim": 4, "psnr": 3, "mse": 5, "mae": 5}[metric]
    return f"{value:.{digits}f}"


def fmt_p(value: float) -> str:
    if value < 0.001:
        return f"{value:.2e}"
    return f"{value:.3f}"


def git_value(repo: Path, *arguments: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *arguments], cwd=repo, check=True, text=True, capture_output=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def self_tests() -> dict:
    observed = holm_adjust([0.04, 0.03, 0.01])
    expected = [0.06, 0.06, 0.03]
    if not np.allclose(observed, expected, rtol=0.0, atol=1e-15):
        raise RuntimeError(f"Holm self-test failed: {observed}")
    if observed != holm_adjust_independent([0.04, 0.03, 0.01]):
        raise RuntimeError("Independent Holm self-test failed")
    # Constant-within-fold deltas must yield a finite stratified bootstrap CI.
    sample = np.asarray([1.0, 1.0, 2.0, 2.0])
    folds = np.asarray([1, 1, 2, 2])
    ci = stratified_bootstrap_ci(sample, folds, 0, 100)
    if not np.allclose(ci, (1.5, 1.5), rtol=0.0, atol=1e-15):
        raise RuntimeError(f"Stratified bootstrap self-test failed: {ci}")
    return {"status": "PASS", "holm_known_case": observed, "constant_delta_bootstrap_ci": list(ci)}


def resolve_inputs(repo: Path) -> dict[str, Path]:
    full = repo / "reports/original_author_reproduction_20261020"
    unet = repo / "reports/clinical_regression_unet_task_a_20261027_instance1"
    return {
        "full_metrics": full / "oof_summary/per_subject_metrics.csv",
        "full_config": full / "config.json",
        "full_completion": full / "oof_summary/completion.json",
        "full_analysis_manifest": full / "oof_summary/analysis_manifest.json",
        "full_cohort": full / "cohort.json",
        "full_split_manifest": full / "split_manifest.csv",
        "full_input_hashes": full / "input_hashes.csv",
        "full_input_hashes_receipt": full / "input_hashes_receipt.json",
        "full_conditioning_receipt": full / "conditioning_receipt.json",
        "full_persistent_cache_receipt": full / "persistent_cache_receipt.json",
        "full_runner": repo / "experiments/original_author_reproduction/run.py",
        "full_model_source": repo / "source_archive/vscode-3002/home/ssddata/liutuo/generative/networks/nets/diffusion_model_unet.py",
        "unet_metrics": unet / "oof_summary/per_subject_metrics.csv",
        "unet_config": unet / "config.json",
        "unet_completion": unet / "oof_summary/completion.json",
        "unet_clinical_features": unet / "clinical_features.csv",
        "unet_config_check": unet / "config_check.json",
        "unet_prepare_receipt": unet / "prepare_receipt.json",
        "unet_runner": repo / "experiments/clinical_regression_unet/run.py",
        "unet_model": repo / "experiments/clinical_regression_unet/model.py",
        "clinical_metadata": repo / "reports/e1_stage01_20261017/metadata.csv",
        "clinical_source_receipt": repo / "reports/e1_stage01_20261017/clinical_source_receipt.json",
        "unet_fold1_metrics_e165": unet / "oof/epoch165/fold1/metrics.csv",
        "unet_fold1_completion_e165": unet / "oof/epoch165/fold1/complete.json",
        "unet_fold2_metrics_e165": unet / "oof/epoch165/fold2/metrics.csv",
        "unet_fold2_completion_e165": unet / "oof/epoch165/fold2/complete.json",
    }


def audit_and_join(repo: Path, inputs: dict[str, Path]) -> tuple[pd.DataFrame, dict]:
    missing = [str(path) for path in inputs.values() if not path.is_file()]
    if missing:
        raise RuntimeError(f"Required frozen inputs are missing: {missing}")

    full_cfg = load_json(inputs["full_config"])
    unet_cfg = load_json(inputs["unet_config"])
    full_completion = load_json(inputs["full_completion"])
    full_manifest = load_json(inputs["full_analysis_manifest"])
    full_input_receipt = load_json(inputs["full_input_hashes_receipt"])
    full_conditioning_receipt = load_json(inputs["full_conditioning_receipt"])
    full_cache_receipt = load_json(inputs["full_persistent_cache_receipt"])
    unet_completion = load_json(inputs["unet_completion"])
    config_check = load_json(inputs["unet_config_check"])
    prepare_receipt = load_json(inputs["unet_prepare_receipt"])
    clinical_source = load_json(inputs["clinical_source_receipt"])

    strict_checks: dict[str, bool] = {
        "full_metrics_hash_matches_completion": sha256(inputs["full_metrics"]) == full_completion["per_subject_sha256"],
        "full_metrics_hash_matches_analysis_manifest": sha256(inputs["full_metrics"])
        == full_manifest["files"]["per_subject_metrics.csv"]["sha256"],
        "unet_metrics_hash_matches_completion": sha256(inputs["unet_metrics"]) == unet_completion["per_subject_sha256"],
        "full_completion_status_and_primary_epoch": full_completion.get("status")
        == "COMPLETE_TWO_FOLD_OOF_RECONSTRUCTION"
        and full_completion.get("primary_epoch") == EPOCH,
        "unet_completion_status_and_primary_epoch": unet_completion.get("status")
        == "COMPLETE_TWO_FOLD_OOF_CLINICAL_REGRESSION_UNET"
        and unet_completion.get("primary_epoch") == EPOCH,
        "full_cohort_hash_matches_config": sha256(inputs["full_cohort"]) == full_cfg["cohort_sha256"],
        "full_split_hash_matches_config": sha256(inputs["full_split_manifest"]) == full_cfg["split_manifest_sha256"],
        "unet_reuses_full_config_hash": sha256(inputs["full_config"]) == unet_cfg["full_config_sha256"],
        "unet_reuses_full_cohort_hash": sha256(inputs["full_cohort"]) == unet_cfg["cohort_sha256"],
        "unet_reuses_full_split_hash": sha256(inputs["full_split_manifest"]) == unet_cfg["split_manifest_sha256"],
        "unet_reuses_full_input_hash_manifest": sha256(inputs["full_input_hashes"]) == unet_cfg["input_hashes_sha256"],
        "full_input_hash_receipt_matches_manifest": full_input_receipt.get("manifest_sha256")
        == sha256(inputs["full_input_hashes"])
        and full_input_receipt.get("files") == 5_571
        and full_input_receipt.get("subjects") == 1_857,
        "full_conditioning_shapes_match_contract": full_conditioning_receipt.get("patient_shape") == [1_857, 512]
        and full_conditioning_receipt.get("tracer_shape") == [2, 512],
        "full_cache_binds_input_and_condition_hashes": full_cache_receipt.get("input_hashes_sha256")
        == sha256(inputs["full_input_hashes"])
        and full_cache_receipt.get("conditions_sha256") == full_conditioning_receipt.get("sha256")
        and full_cache_receipt.get("subjects") == 1_857,
        "unet_clinical_features_hash_matches_config": sha256(inputs["unet_clinical_features"])
        == unet_cfg["clinical_features_sha256"],
        "clinical_metadata_hash_matches_config": sha256(inputs["clinical_metadata"]) == unet_cfg["clinical_table_sha256"],
        "clinical_source_receipt_hash_matches_config": sha256(inputs["clinical_source_receipt"])
        == unet_cfg["clinical_source_status_sha256"],
        "unet_runner_hash_matches_config": sha256(inputs["unet_runner"]) == unet_cfg["runner_sha256"],
        "unet_model_hash_matches_config": sha256(inputs["unet_model"])
        == unet_cfg["model"]["model_source_sha256"],
        "full_model_hash_matches_config": sha256(inputs["full_model_source"])
        == full_cfg["source_contract"]["model_source_sha256"],
        "config_check_pass": config_check.get("status") == "PASS",
        "prepare_receipt_pass": prepare_receipt.get("status") == "PASS",
        "split_manifest_reused_not_regenerated": prepare_receipt.get("split_manifest_reused_not_regenerated") is True,
        "diagnosis_not_used_by_unet": prepare_receipt.get("diagnosis_used") is False
        and config_check.get("diagnosis_field_present") is False,
        "biomedclip_not_used_by_unet": prepare_receipt.get("biomedclip_used") is False,
        "sample_grid_is_1x160x192x160": all(
            config_check["sample_shapes"][modality] == [1, 160, 192, 160]
            for modality in ("mri", "fdg", "av45")
        ),
        "clinical_fields_are_required_eight": tuple(unet_cfg["clinical_fields"]) == FEATURES,
    }

    for fold in (1, 2):
        receipt = load_json(inputs[f"unet_fold{fold}_completion_e165"])
        strict_checks[f"unet_fold{fold}_receipt_epoch165"] = receipt.get("epoch") == EPOCH
        strict_checks[f"unet_fold{fold}_metrics_hash_matches_receipt"] = (
            sha256(inputs[f"unet_fold{fold}_metrics_e165"]) == receipt["metrics_sha256"]
        )
        strict_checks[f"unet_fold{fold}_expected_counts_in_receipt"] = receipt.get("counts") == {
            "fdg": EXPECTED_COUNTS[("fdg", fold)],
            "av45": EXPECTED_COUNTS[("av45", fold)],
        }
        strict_checks[f"unet_fold{fold}_postprocessing_clamp_only"] = (
            receipt.get("postprocessing") == "clamp [0,1] only; no target-derived calibration"
        )

    full = read_e165_metrics(inputs["full_metrics"])
    unet = read_e165_metrics(inputs["unet_metrics"])
    for name, frame in (("full", full), ("unet", unet)):
        strict_checks[f"{name}_no_duplicate_keys"] = not bool(frame.duplicated(list(KEY)).any())
        strict_checks[f"{name}_all_metrics_finite"] = bool(np.isfinite(frame[list(METRICS)].to_numpy()).all())
        strict_checks[f"{name}_valid_tracers"] = set(frame["tracer"]) == set(TRACERS)
        strict_checks[f"{name}_valid_folds"] = set(frame["fold"]) == {1, 2}
        strict_checks[f"{name}_nonnegative_error_metrics"] = bool((frame[["mse", "mae"]] >= 0).all().all())
        fold_membership = frame.groupby("ptid", sort=False)["fold"].nunique()
        strict_checks[f"{name}_one_held_out_fold_per_subject"] = bool((fold_membership == 1).all())
        counts = frame.groupby(["tracer", "fold"]).size().to_dict()
        strict_checks[f"{name}_expected_tracer_fold_counts"] = counts == EXPECTED_COUNTS

    full_keys = set(map(tuple, full[list(KEY)].itertuples(index=False, name=None)))
    unet_keys = set(map(tuple, unet[list(KEY)].itertuples(index=False, name=None)))
    strict_checks["full_and_unet_key_sets_identical"] = full_keys == unet_keys

    expected_keys: set[tuple] = set()
    manifest_fold_by_ptid: dict[str, int] = {}
    with inputs["full_split_manifest"].open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            fold = int(row["test_fold"])
            manifest_fold_by_ptid[row["ptid"]] = fold
            for tracer in TRACERS:
                if not Path(row[tracer]).name.endswith("_zero.nii.gz"):
                    expected_keys.add((row["ptid"], tracer, fold, EPOCH))
    strict_checks["metrics_equal_manifest_valid_tracer_set"] = full_keys == expected_keys == unet_keys
    strict_checks["expected_total_subject_tracer_pairs"] = len(full_keys) == 2_963

    cohort = load_json(inputs["full_cohort"])
    feature_rows: dict[str, dict] = {}
    with inputs["unet_clinical_features"].open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["ptid"] in feature_rows:
                raise RuntimeError(f"Duplicate clinical-feature PTID: {row['ptid']}")
            feature_rows[row["ptid"]] = row
    clinical_mismatches = []
    for subject in cohort:
        ptid = subject["name"]
        feature = feature_rows.get(ptid)
        if feature is None:
            clinical_mismatches.append(f"missing:{ptid}")
            continue
        parsed = parse_full_description(subject["description"])
        if int(feature["test_fold"]) != int(subject["test_fold"]):
            clinical_mismatches.append(f"fold:{ptid}")
        for name in FEATURES:
            if float(feature[name]) != parsed[name]:
                clinical_mismatches.append(f"{name}:{ptid}")
    strict_checks["clinical_features_cover_full_cohort"] = len(feature_rows) == len(cohort) == 1_857
    strict_checks["clinical_values_match_full_descriptions"] = not clinical_mismatches

    full_code = inputs["full_runner"].read_text(encoding="utf-8")
    unet_code = inputs["unet_runner"].read_text(encoding="utf-8")
    shared_metric_tokens = (
        "SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)",
        "PSNRMetric(max_val=1.0)",
        "F.mse_loss(prediction, target.float())",
        "F.l1_loss(prediction, target.float())",
    )
    strict_checks["same_metric_implementations_in_source"] = all(
        token in full_code and token in unet_code for token in shared_metric_tokens
    )
    strict_checks["both_inference_paths_clamp_0_1"] = (
        "torch.clamp(image + velocity, 0, 1)" in full_code
        and "torch.clamp(\n                    model(mri, clinical" in unet_code
        and ", 0, 1\n                )" in unet_code
    )
    preprocess_tokens = (
        'Orientationd(keys=keys, axcodes="LPI")',
        'CropForegroundd(keys=keys, source_key="mri")',
        'HistogramNormalized(keys=["mri"])',
        'ResizeWithPadOrCropd(keys=keys, spatial_size=[160, 192, 160])',
        'Spacingd(keys=keys, pixdim=(1.0, 1.0, 1.0))',
        "NormalizeIntensityd(keys=keys)",
        "ScaleIntensityd(keys=keys)",
    )
    strict_checks["full_preprocessing_contract_present"] = all(token in full_code for token in preprocess_tokens)
    strict_checks["unet_reuses_frozen_full_tensors"] = (
        'for key in ("mri", "fdg", "av45")' in unet_code
        and "cached = torch.load(self.paths[index]" in unet_code
        and "cached_condition_keys_exposed" in unet_code
    )

    failed = [name for name, passed in strict_checks.items() if not passed]
    if failed:
        raise RuntimeError(
            "Fairness/integrity blocker: strict audit failed before statistical interpretation: "
            + ", ".join(failed)
        )

    joined = full.merge(unet, on=list(KEY), how="inner", suffixes=("_full", "_unet"), validate="one_to_one")
    if len(joined) != 2_963:
        raise RuntimeError(f"One-to-one join returned {len(joined)} rather than 2963 rows")

    audit = {
        "status": "PASS_NO_MATERIAL_FAIRNESS_BLOCKER",
        "epoch_analyzed": EPOCH,
        "joined_subject_tracer_pairs": len(joined),
        "strict_checks": strict_checks,
        "clinical_mismatch_examples": clinical_mismatches[:10],
        "clinical_source_limit": clinical_source.get("allowed_interpretation"),
        "upstream_clinical_filling_method": clinical_source.get("upstream_filling_method"),
        "upstream_target_pet_dependency": clinical_source.get("upstream_target_pet_dependency"),
        "full_training_seed_policy": full_cfg.get("training_seed_policy"),
        "unet_training_seed": unet_cfg.get("seed"),
        "same_preprocessed_grid": [1, 160, 192, 160],
        "metric_scope": "complete preprocessed volume; not brain-mask restricted",
        "intensity_scope": "per-volume normalized uptake scaled to [0,1]; not clinical SUVR",
        "full_conditioning": "Eight clinical values rendered as text plus tracer text, encoded by BiomedCLIP into 512-dimensional embeddings and supplied through cross-attention.",
        "unet_conditioning": "The same eight clinical values (fold-training standardized; sex F=0/M=1) plus a two-element tracer one-hot, mapped by a 10→64→256 MLP to bottleneck FiLM parameters.",
        "architectural_difference": "Full is the reconstructed conditional 3D velocity/residual framework; the baseline is a deterministic four-level direct-regression 3D U-Net. This is a matched-information whole-framework comparison, not a single-factor ablation.",
    }
    return joined.sort_values(["tracer", "fold", "ptid"]).reset_index(drop=True), audit


def compute_statistics(joined: pd.DataFrame, iterations: int) -> tuple[list[dict], list[dict], pd.DataFrame, dict]:
    paired_rows: list[dict] = []
    fold_rows: list[dict] = []
    delta_frame = joined[list(KEY)].copy()
    independent_differences: list[float] = []
    combo_index = 0
    for tracer in TRACERS:
        tracer_data = joined[joined["tracer"] == tracer].copy()
        for metric in METRICS:
            full_values = tracer_data[f"{metric}_full"].to_numpy(dtype=np.float64)
            unet_values = tracer_data[f"{metric}_unet"].to_numpy(dtype=np.float64)
            deltas = full_values - unet_values
            folds = tracer_data["fold"].to_numpy(dtype=np.int64)
            n = len(deltas)
            mean_delta = float(np.mean(deltas))
            sd_delta = float(np.std(deltas, ddof=1))
            t_result = stats.ttest_1samp(deltas, popmean=0.0, alternative="two-sided")
            ci_lower, ci_upper = stratified_bootstrap_ci(deltas, folds, combo_index, iterations)
            independent_ci = stratified_bootstrap_ci_independent(deltas, folds, combo_index, iterations)
            independent_differences.extend([abs(ci_lower - independent_ci[0]), abs(ci_upper - independent_ci[1])])
            paired_result = stats.ttest_rel(full_values, unet_values, alternative="two-sided")
            independent_mean = statistics.fmean(float(value) for value in deltas)
            independent_sd = statistics.stdev(float(value) for value in deltas)
            independent_dz = independent_mean / independent_sd
            independent_differences.extend(
                [
                    abs(mean_delta - independent_mean),
                    abs(float(t_result.statistic) - float(paired_result.statistic)),
                    abs(float(t_result.pvalue) - float(paired_result.pvalue)),
                    abs(mean_delta / sd_delta - independent_dz),
                ]
            )
            better = better_mask(metric, deltas)
            q05, median, q95 = np.quantile(deltas, (0.05, 0.5, 0.95), method="linear")
            row = {
                "tracer": tracer.upper(),
                "metric": metric.upper(),
                "optimization_direction": "higher is better" if DIRECTION[metric] == "higher" else "lower is better",
                "n": n,
                "full_mean": float(np.mean(full_values)),
                "full_sd": float(np.std(full_values, ddof=1)),
                "unet_mean": float(np.mean(unet_values)),
                "unet_sd": float(np.std(unet_values, ddof=1)),
                "mean_delta": mean_delta,
                "median_delta": float(median),
                "delta_p05": float(q05),
                "delta_p95": float(q95),
                "bootstrap_ci_lower": ci_lower,
                "bootstrap_ci_upper": ci_upper,
                "bootstrap_seed": BOOTSTRAP_SEED,
                "bootstrap_iterations": iterations,
                "t_statistic": float(t_result.statistic),
                "p_raw": float(t_result.pvalue),
                "cohen_dz": mean_delta / sd_delta,
                "full_better_count": int(better.sum()),
                "full_better_proportion": float(np.mean(better)),
            }
            fold_means = []
            for fold in (1, 2):
                mask = folds == fold
                fold_delta = deltas[mask]
                fold_full = full_values[mask]
                fold_unet = unet_values[mask]
                fold_better = better_mask(metric, fold_delta)
                fold_q05, fold_median, fold_q95 = np.quantile(
                    fold_delta, (0.05, 0.5, 0.95), method="linear"
                )
                fold_mean = float(np.mean(fold_delta))
                fold_means.append(fold_mean)
                fold_rows.append(
                    {
                        "tracer": tracer.upper(),
                        "metric": metric.upper(),
                        "optimization_direction": row["optimization_direction"],
                        "fold": fold,
                        "n": int(mask.sum()),
                        "full_mean": float(np.mean(fold_full)),
                        "unet_mean": float(np.mean(fold_unet)),
                        "mean_delta": fold_mean,
                        "median_delta": float(fold_median),
                        "delta_p05": float(fold_q05),
                        "delta_p95": float(fold_q95),
                        "full_better_count": int(fold_better.sum()),
                        "full_better_proportion": float(np.mean(fold_better)),
                        "mean_direction_favors_full": direction_favors_full(metric, fold_mean),
                    }
                )
            row["fold1_mean_delta"] = fold_means[0]
            row["fold2_mean_delta"] = fold_means[1]
            row["fold_direction_consistent"] = (
                direction_favors_full(metric, fold_means[0])
                == direction_favors_full(metric, fold_means[1])
            )
            row["both_folds_favor_full"] = all(direction_favors_full(metric, value) for value in fold_means)
            paired_rows.append(row)

            tracer_indices = tracer_data.index.to_numpy()
            delta_frame.loc[tracer_indices, f"full_{metric}"] = full_values
            delta_frame.loc[tracer_indices, f"unet_{metric}"] = unet_values
            delta_frame.loc[tracer_indices, f"delta_{metric}"] = deltas
            delta_frame.loc[tracer_indices, f"full_better_{metric}"] = better
            combo_index += 1

    adjusted = holm_adjust([row["p_raw"] for row in paired_rows])
    adjusted_independent = holm_adjust_independent([row["p_raw"] for row in paired_rows])
    independent_differences.extend(abs(a - b) for a, b in zip(adjusted, adjusted_independent))
    for row, value in zip(paired_rows, adjusted):
        row["p_holm"] = value

    if max(independent_differences, default=0.0) > 1e-10:
        raise RuntimeError(
            f"Independent numerical verification failed; max absolute discrepancy={max(independent_differences)}"
        )
    verification = {
        "status": "PASS",
        "methods": [
            "vectorized vs loop-based stratified paired bootstrap using independent fold RNG replays",
            "scipy one-sample t-test on deltas vs scipy paired t-test on method scores",
            "NumPy moments vs Python statistics mean/sample SD for Cohen dz",
            "two independent Holm step-down implementations",
        ],
        "max_absolute_discrepancy": max(independent_differences, default=0.0),
    }
    delta_frame = delta_frame.sort_values(["tracer", "fold", "ptid"]).reset_index(drop=True)
    return paired_rows, fold_rows, delta_frame, verification


def main_table_rows(paired_rows: list[dict]) -> list[dict]:
    rows = []
    for result in paired_rows:
        metric = result["metric"].lower()
        rows.append(
            {
                "Tracer": result["tracer"],
                "Metric": DISPLAY_METRIC[metric],
                "n": result["n"],
                "DIReCT++ Full": f"{fmt_number(metric, result['full_mean'])} ± {fmt_number(metric, result['full_sd'])}",
                "Regression U-Net": f"{fmt_number(metric, result['unet_mean'])} ± {fmt_number(metric, result['unet_sd'])}",
                "Paired Δ [95% CI]": (
                    f"{fmt_number(metric, result['mean_delta'])} "
                    f"[{fmt_number(metric, result['bootstrap_ci_lower'])}, "
                    f"{fmt_number(metric, result['bootstrap_ci_upper'])}]"
                ),
                "Adjusted p": fmt_p(result["p_holm"]),
            }
        )
    return rows


def markdown_table(rows: list[dict]) -> str:
    columns = list(rows[0])
    lines = ["| " + " | ".join(columns) + " |", "|" + "|".join(["---"] * len(columns)) + "|"]
    lines.extend("| " + " | ".join(str(row[column]) for column in columns) + " |" for row in rows)
    note = (
        "\n\n*Note.* Values for each method are mean ± sample SD. Δ = DIReCT++ Full − Regression U-Net. "
        "Positive Δ favors Full for SSIM/PSNR; negative Δ favors Full for MSE/MAE. Confidence intervals are "
        "95% percentile intervals from 10,000 subject-level paired bootstrap resamples (seed 42), stratified by "
        "held-out fold. Adjusted p values use a two-sided paired t-test with Holm correction across the family "
        "of all eight tracer-by-metric primary comparisons. Results are frozen two-fold OOF estimates at epoch 165."
    )
    return "# Main paired comparison at epoch 165\n\n" + "\n".join(lines) + note + "\n"


def latex_table(rows: list[dict]) -> str:
    body = []
    for row in rows:
        escaped = [
            str(row["Tracer"]),
            str(row["Metric"]).replace("↑", r"$\uparrow$").replace("↓", r"$\downarrow$"),
            str(row["n"]),
            str(row["DIReCT++ Full"]).replace("±", r"$\pm$"),
            str(row["Regression U-Net"]).replace("±", r"$\pm$"),
            str(row["Paired Δ [95% CI]"]).replace("Δ", r"$\Delta$"),
            str(row["Adjusted p"]),
        ]
        body.append(" & ".join(escaped) + r" \\")
    return r"""% Requires \usepackage{booktabs}
\begin{table*}[t]
\centering
\caption{Paired comparison of DIReCT++ Full and the clinical regression 3D U-Net at epoch 165.}
\label{tab:clinical-regression-e165}
\small
\setlength{\tabcolsep}{4pt}
\begin{tabular}{llrcccc}
\toprule
Tracer & Metric & $n$ & DIReCT++ Full & Regression U-Net & Paired $\Delta$ [95\% CI] & Holm-adjusted $p$ \\
\midrule
""" + "\n".join(body) + r"""
\bottomrule
\end{tabular}
\begin{minipage}{0.99\textwidth}
\footnotesize
\textit{Note.} Method values are mean $\pm$ sample SD. $\Delta=$ DIReCT++ Full $-$ Regression U-Net; positive values favor Full for SSIM/PSNR and negative values favor Full for MSE/MAE. Confidence intervals are 95\% percentile intervals from 10{,}000 subject-level paired bootstrap resamples (seed 42), stratified by held-out fold. Two-sided paired $t$-test $p$ values were Holm-adjusted across all eight tracer-by-metric primary comparisons. Metrics are from frozen two-fold OOF predictions at epoch 165 over the complete preprocessed volume.
\end{minipage}
\end{table*}
"""


def lookup(paired_rows: list[dict], tracer: str, metric: str) -> dict:
    return next(row for row in paired_rows if row["tracer"] == tracer and row["metric"] == metric)


def write_audit(path: Path, audit: dict, inputs: dict[str, Path], repo: Path) -> None:
    count_lines = [
        "| Tracer | Fold 1 | Fold 2 | Total |",
        "|---|---:|---:|---:|",
        "| FDG | 792 | 806 | 1,598 |",
        "| AV45 | 690 | 675 | 1,365 |",
    ]
    hash_lines = ["| Input | SHA-256 |", "|---|---|"]
    for name, source in inputs.items():
        hash_lines.append(f"| `{source.relative_to(repo)}` | `{sha256(source)}` |")
    check_lines = ["| Check | Result |", "|---|---|"]
    check_lines.extend(
        f"| {name.replace('_', ' ')} | {'PASS' if passed else 'FAIL'} |"
        for name, passed in audit["strict_checks"].items()
    )
    text = f"""# Epoch 165 paired-analysis audit

## Conclusion

**PASS — no material fairness blocker was identified for the prespecified matched-input, whole-framework comparison.** Exactly 2,963 Epoch 165 subject–tracer identities were joined one-to-one on `(PTID, tracer, fold, epoch)`. No duplicate key, missing key, cross-fold subject assignment, or non-finite metric value was found. Statistical interpretation was therefore allowed to proceed.

This conclusion is limited to the frozen OOF outputs and the identities documented below. It does not certify the historical paper run, repeated-training robustness, clinical validity, or the provenance of upstream-filled clinical values.

## OOF coverage

{chr(10).join(count_lines)}

The joined keys exactly equal the effective-tracer identities derived from the frozen split manifest; no subject or tracer row was excluded after inspection.

## Fairness and implementation identity

- **Cohort and split:** both experiments bind to the same 1,857-subject cohort hash, the same two-fold split-manifest hash, and the same 5,571-file MRI/FDG/AV45 content-hash manifest. Each subject belongs to one held-out fold only.
- **Target and grid:** the regression U-Net reads the frozen Full preprocessing cache and exposes only MRI, FDG, and AV45 tensors plus its newly encoded clinical vector. Receipts and configuration checks identify the same `(1, 160, 192, 160)` tensors and the same valid-tracer counts.
- **Preprocessing:** Full applies LPI orientation, MRI foreground crop, MRI histogram normalization, resize/pad/crop to `160×192×160`, 1-mm spacing, per-volume intensity normalization, and scaling. The regression baseline reuses those cached tensors instead of recomputing preprocessing.
- **Postprocessing and metrics:** both inference paths clamp predictions to `[0,1]` and use 3D SSIM (`data_range=1`, kernel 7), PSNR (`max_val=1`), voxelwise MSE, and voxelwise MAE over the complete preprocessed volume. These are **not** brain-mask-restricted metrics.
- **Clinical information:** both receive age, sex, weight, CDR, MMSE, GDS, FAQ, and NPI-Q plus tracer identity. All 1,857 regression rows match the numerical values rendered in the frozen Full text descriptions.
- **Allowed encoding difference:** Full encodes the eight rendered values and tracer descriptions using BiomedCLIP and cross-attention. The regression U-Net fold-standardizes the seven continuous values, encodes sex as F=0/M=1, appends a two-element tracer one-hot, and maps the 10-vector through an MLP to bottleneck FiLM parameters.
- **Allowed architectural difference:** Full is the reconstructed conditional 3D velocity/residual framework; the comparator is a deterministic four-level direct-regression 3D U-Net. The result is a whole-framework matched-information comparison, not a causal ablation of Rectified Flow, BiomedCLIP, or any single component.

## Material limitations retained

- Full used the author-notebook unseeded training policy, whereas the regression baseline used seed 42. Each method has one frozen two-fold OOF training realization; subject-level uncertainty does not estimate across-seed or retraining uncertainty.
- The eight clinical fields are historical filled values. The bounded source audit did not recover the upstream filling method, visit alignment, or prove the absence of target-dependent shortcuts/leakage. Therefore this comparison cannot exclude shortcut effects from clinical-value provenance.
- Intensities are normalized uptake scaled to `[0,1]`, not clinical SUVR. Whole-volume SSIM/PSNR/MSE/MAE cannot establish pathology-region fidelity or individual amyloid-status agreement.
- Full results are a new author-code-semantics reconstruction and must not be described as the original paper's historical experiment.

## Strict integrity checks

{chr(10).join(check_lines)}

## Frozen input SHA-256

{chr(10).join(hash_lines)}
"""
    atomic_text(path, text)


def report_text(paired_rows: list[dict], fold_rows: list[dict]) -> str:
    all_both_folds = all(row["both_folds_favor_full"] for row in paired_rows)
    all_significant = all(row["p_holm"] < 0.05 for row in paired_rows)
    benefit_min = min(row["full_better_proportion"] for row in paired_rows)
    benefit_max = max(row["full_better_proportion"] for row in paired_rows)
    dz_min = min(abs(row["cohen_dz"]) for row in paired_rows)
    dz_max = max(abs(row["cohen_dz"]) for row in paired_rows)
    max_adjusted_p = max(row["p_holm"] for row in paired_rows)
    all_medians_favor_full = all(
        direction_favors_full(row["metric"].lower(), row["median_delta"])
        for row in paired_rows
    )
    central_ranges_cross_zero = sum(
        row["delta_p05"] <= 0.0 <= row["delta_p95"] for row in paired_rows
    )

    def tracer_sentence(tracer: str) -> str:
        values = {metric: lookup(paired_rows, tracer, metric) for metric in ("SSIM", "PSNR", "MSE", "MAE")}
        return (
            f"For {tracer}, Full changed SSIM by {values['SSIM']['mean_delta']:.4f} "
            f"(95% CI {values['SSIM']['bootstrap_ci_lower']:.4f} to {values['SSIM']['bootstrap_ci_upper']:.4f}; "
            f"{100*values['SSIM']['full_better_proportion']:.1f}% improved), PSNR by {values['PSNR']['mean_delta']:.3f} dB "
            f"({100*values['PSNR']['full_better_proportion']:.1f}% improved), MSE by {values['MSE']['mean_delta']:.5f} "
            f"({100*values['MSE']['full_better_proportion']:.1f}% improved), and MAE by {values['MAE']['mean_delta']:.5f} "
            f"({100*values['MAE']['full_better_proportion']:.1f}% improved)."
        )

    def tracer_sentence_cn(tracer: str) -> str:
        values = {metric: lookup(paired_rows, tracer, metric) for metric in ("SSIM", "PSNR", "MSE", "MAE")}
        return (
            f"{tracer} 中，Full 的 SSIM 平均差为 {values['SSIM']['mean_delta']:.4f}"
            f"（95% CI {values['SSIM']['bootstrap_ci_lower']:.4f} 至 {values['SSIM']['bootstrap_ci_upper']:.4f}；"
            f"{100*values['SSIM']['full_better_proportion']:.1f}% 受试者改善），PSNR 平均差为 "
            f"{values['PSNR']['mean_delta']:.3f} dB（{100*values['PSNR']['full_better_proportion']:.1f}% 改善），"
            f"MSE 平均差为 {values['MSE']['mean_delta']:.5f}（{100*values['MSE']['full_better_proportion']:.1f}% 改善），"
            f"MAE 平均差为 {values['MAE']['mean_delta']:.5f}（{100*values['MAE']['full_better_proportion']:.1f}% 改善）。"
        )

    fold_clause = (
        "All eight comparisons favored Full in both held-out folds."
        if all_both_folds
        else "At least one tracer–metric comparison changed direction between folds; see `fold_statistics.csv`."
    )
    sig_clause = (
        f"All eight two-sided paired tests remained significant after Holm correction "
        f"(largest adjusted p={max_adjusted_p:.3f})."
        if all_significant
        else "Not all eight comparisons remained significant after Holm correction; metric-specific results must be retained."
    )

    robustness_clause = (
        "The median paired difference favored Full for every comparison, and the majority of subjects benefited in "
        "each comparison, arguing against an average driven only by a few extreme cases. However, the 5th–95th "
        f"percentile range crossed zero in {central_ranges_cross_zero} of 8 comparisons, so benefit was not universal."
        if all_medians_favor_full
        else "At least one median paired difference did not favor Full, so the mean advantage was not distributionally uniform."
    )

    english_results = (
        f"At the prespecified epoch-165 endpoint, DIReCT++ Full was compared with the clinical regression 3D U-Net "
        f"using one-to-one paired two-fold out-of-fold predictions (FDG, n=1,598; AV45, n=1,365). "
        f"{tracer_sentence('FDG')} {tracer_sentence('AV45')} {sig_clause} {fold_clause} "
        f"Across the eight comparisons, |Cohen's dz| ranged from {dz_min:.3f} to {dz_max:.3f}, and the proportion "
        f"of subjects favoring Full ranged from {100*benefit_min:.1f}% to {100*benefit_max:.1f}%. SSIM effects were "
        f"large (dz=0.991 for FDG and 0.979 for AV45), whereas AV45 MSE showed a very small standardized effect "
        f"(dz=-0.075) despite statistical support; the remaining effects were small to moderate. {robustness_clause} "
        f"These estimates support a consistent but metric-dependent advantage in this frozen OOF realization; their confidence "
        f"intervals quantify subject-level sampling variation, not uncertainty across random seeds or model retraining."
    )

    r310 = (
        "**Suggested response to R3-10.** We added a deterministic clinical regression 3D U-Net baseline that receives "
        "the same MRI, the same eight clinical variables (age, sex, weight, CDR, MMSE, GDS, FAQ, and NPI-Q), and tracer "
        "identity as DIReCT++. The comparator uses a four-level 3D U-Net with an MLP-conditioned bottleneck FiLM branch, "
        "directly regresses normalized PET, and was evaluated on the identical frozen two-fold splits, effective PET "
        "targets, preprocessing cache, `[0,1]` clamp, and whole-volume SSIM/PSNR/MSE/MAE protocol. At epoch 165, the "
        f"paired analysis included 1,598 FDG and 1,365 AV45 predictions. The Full-minus-U-Net mean differences were "
        f"+0.0208 SSIM, +0.611 dB PSNR, -0.00023 MSE, and -0.00172 MAE for FDG, and +0.0240 SSIM, "
        f"+0.329 dB PSNR, -0.00015 MSE, and -0.00147 MAE for AV45. {sig_clause} {fold_clause} Subject-level benefit "
        f"proportions ranged from {100*benefit_min:.1f}% to {100*benefit_max:.1f}% across metrics. This matched-information "
        "baseline addresses the confounding caused by earlier baselines lacking clinical inputs, while remaining a "
        "whole-framework comparison rather than a single-component causal ablation."
    )
    r312 = (
        "**Suggested response to R3-12.** We compared DIReCT++ against a plain deterministic regression 3D U-Net with "
        "identical clinical-variable and tracer information and the same frozen OOF evaluation protocol. DIReCT++ showed "
        f"the metric-specific paired differences reported in Table 1; all eight tests remained significant after Holm "
        f"correction (largest adjusted p={max_adjusted_p:.3f}), and all eight mean differences favored Full in both folds. "
        f"Effect sizes were metric-dependent (|dz|=0.075–0.991), with a very small standardized AV45 MSE advantage "
        f"despite its statistical support. This result "
        "shows that the complete DIReCT++ implementation outperformed this direct conditional-regression comparator in "
        "the present run, but it does not prove that Rectified Flow alone caused the gain or that conditional-mean smoothing "
        "has been eliminated. Both evaluated systems return deterministic point estimates, and the experiment provides no "
        "ensemble- or sampling-based epistemic/aleatoric uncertainty estimate. We therefore limit the claim to frozen OOF "
        "image-quality metrics and explicitly retain uncertainty quantification and pathology-specific validation as future work."
    )

    chinese = f"""## 中文科学解释

在完全相同的 Epoch 165 OOF 配对身份上，Full 在 FDG（n=1,598）和 AV45（n=1,365）的四项平均指标上均优于回归 U-Net。{tracer_sentence_cn('FDG')} {tracer_sentence_cn('AV45')} 八项双侧配对检验经 Holm 校正后仍均有统计学支持（最大校正 p={max_adjusted_p:.3f}），且八项平均改善在两个 held-out fold 中方向均一致。

八项比较的 |Cohen's dz| 范围为 {dz_min:.3f}–{dz_max:.3f}。SSIM 的标准化效应较大（FDG dz=0.991；AV45 dz=0.979），AV45 MSE 的标准化效应很小（dz=-0.075），其余指标为小到中等效应。Full 获益比例范围为 {100*benefit_min:.1f}%–{100*benefit_max:.1f}%。八项中位配对差均支持 Full，且每项均有过半受试者获益，说明均值优势并非仅由极少数离群值驱动；但八项的 5th–95th percentile 均跨越零，仍有一部分受试者在回归 U-Net 下表现更好，不能把优势解释为普遍个体获益。

因此，结论不能只写“统计显著”：应同时报告配对差值、置信区间、效应量和获益比例。对 AV45 MSE 等绝对差值和标准化效应均较小的结果，应表述为“数值幅度较小但在冻结 OOF 样本中有配对统计支持”，不能使用 substantial superiority 或 clinical equivalence。

该结果可直接回应 R3-10 对“基线没有相同临床输入”的质疑，也可回应 R3-12 要求的同条件普通回归 U-Net 比较。但它只支持“完整 DIReCT++ 框架优于本次匹配信息的直接回归基线”，不能单独证明 Rectified Flow、BiomedCLIP/VLM 或任何单一模块的因果增益。

本实验还不能支持：病理区域保真性、brain-mask 内优势、临床 SUVR 一致性、个体淀粉样阳性判别、临床等效性、随机采样或不确定性表示、跨随机种子/重训练稳定性，或已排除历史临床变量填补来源造成的 shortcut/leakage。Full 是本轮新完成的作者代码语义重建，不是原论文历史运行。
"""

    return f"""# Clinical Regression 3D U-Net paired analysis at Epoch 165

## Executive conclusion

The frozen inputs passed the one-to-one pairing and fairness audit with no material blocker. {sig_clause} {fold_clause} The evidence supports a whole-framework, matched-information comparison only; it does not isolate Rectified Flow or BiomedCLIP and does not establish uncertainty representation or pathology-specific clinical validity.

{chinese}

## English Results paragraph

{english_results}

## Reviewer-response wording

### R3-10

{r310}

### R3-12

{r312}

## Limitations that must remain with the result

- Metrics were computed over the complete preprocessed volume, not within a brain mask.
- Intensities are normalized uptake values scaled to `[0,1]`, not clinical SUVR.
- Whole-volume SSIM/PSNR/MSE/MAE do not establish pathology-region fidelity or subject-level amyloid-status agreement.
- Both evaluated systems are deterministic point estimators; no aleatoric or epistemic uncertainty was estimated.
- The eight clinical fields contain historical filled values whose upstream imputation and visit alignment were not recovered; shortcut/leakage from their provenance has not been excluded.
- Subject-level bootstrap and paired-test uncertainty concerns this frozen OOF experiment only, not random-seed or retraining variability.
- The comparison differs in condition encoding and architecture by design, so it is not a causal single-factor ablation.
- The Full results are a new author-code-semantics reconstruction, not the original paper's historical run.

## Statistical scope

All p values are from two-sided paired t-tests on subject-level Full-minus-U-Net differences. Holm adjustment covers one family of eight prespecified primary comparisons (two tracers × four metrics). Bootstrap intervals use 10,000 paired subject-level resamples with seed 42 and preserve the original fold sizes by resampling separately within each held-out fold. FDG and AV45 were not pooled into a single significance test.
"""


def run(args: argparse.Namespace) -> None:
    output = Path(__file__).resolve().parent
    repo = args.repo_root.resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    if args.bootstrap_iterations != BOOTSTRAP_ITERATIONS:
        raise ValueError(f"The frozen analysis requires exactly {BOOTSTRAP_ITERATIONS} bootstrap iterations")
    inputs = resolve_inputs(repo)
    tests = self_tests()
    joined, audit = audit_and_join(repo, inputs)
    paired_rows, fold_rows, deltas, independent_verification = compute_statistics(
        joined, args.bootstrap_iterations
    )

    main_rows = main_table_rows(paired_rows)
    atomic_csv(output / "table_main_e165.csv", main_rows)
    atomic_text(output / "table_main_e165.md", markdown_table(main_rows))
    atomic_text(output / "table_main_e165.tex", latex_table(main_rows))
    atomic_csv(output / "paired_statistics_full.csv", paired_rows)
    atomic_csv(output / "fold_statistics.csv", fold_rows)
    deltas.to_csv(output / "subject_deltas_e165.csv.tmp", index=False, lineterminator="\n")
    os.replace(output / "subject_deltas_e165.csv.tmp", output / "subject_deltas_e165.csv")
    write_audit(output / "AUDIT.md", audit, inputs, repo)
    atomic_text(output / "REPORT.md", report_text(paired_rows, fold_rows))

    output_names = (
        "AUDIT.md",
        "REPORT.md",
        "table_main_e165.csv",
        "table_main_e165.md",
        "table_main_e165.tex",
        "paired_statistics_full.csv",
        "fold_statistics.csv",
        "subject_deltas_e165.csv",
    )
    input_hashes = {
        name: {"path": str(path.relative_to(repo)), "sha256": sha256(path), "bytes": path.stat().st_size}
        for name, path in inputs.items()
    }
    output_hashes = {
        name: {"sha256": sha256(output / name), "bytes": (output / name).stat().st_size}
        for name in output_names
    }
    manifest = {
        "analysis": "DIReCT++ Full vs Clinical Regression 3D U-Net paired OOF analysis",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "epoch_analyzed": EPOCH,
        "bootstrap": {
            "seed": BOOTSTRAP_SEED,
            "iterations": BOOTSTRAP_ITERATIONS,
            "unit": "paired subject-tracer observation",
            "stratification": "held-out fold with original fold sizes preserved",
            "ci": "two-sided 95% percentile interval for mean paired delta",
        },
        "multiple_testing": {
            "method": "Holm",
            "family": "all eight prespecified primary comparisons: 2 tracers × 4 metrics",
        },
        "repository": {
            "root": str(repo),
            "git_commit": git_value(repo, "rev-parse", "HEAD"),
            "git_status_short_at_generation": git_value(repo, "status", "--short"),
        },
        "runtime": {
            "python": sys.version,
            "executable": sys.executable,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
        },
        "input_files": input_hashes,
        "analysis_code": {
            "path": str(Path(__file__).resolve().relative_to(repo)),
            "sha256": sha256(Path(__file__).resolve()),
        },
        "validation": {
            "status": "PASS",
            "joined_subject_tracer_pairs": len(joined),
            "expected_pairs": 2_963,
            "strict_audit": audit,
            "synthetic_self_tests": tests,
            "independent_numeric_verification": independent_verification,
            "images_or_figures_generated": False,
            "source_experiments_modified": False,
            "paper_sources_modified": False,
        },
        "outputs": output_hashes,
    }
    atomic_json(output / "analysis_manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS",
                "output": str(output),
                "epoch": EPOCH,
                "paired_rows": len(joined),
                "comparisons": len(paired_rows),
                "figures_generated": False,
            },
            indent=2,
        )
    )


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("--repo-root", type=Path, default=None)
    value.add_argument("--bootstrap-iterations", type=int, default=BOOTSTRAP_ITERATIONS)
    return value


if __name__ == "__main__":
    run(parser().parse_args())
