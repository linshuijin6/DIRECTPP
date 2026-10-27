#!/usr/bin/env python3
"""Validate Full/OT epoch-165 OOF arrays against frozen E1 MRI/mask grids.

This is a read-only scientific validation.  It does not calculate ROI uptake,
modify NIfTI headers, register images, or use PET similarity to select a
spatial transform.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from monai.data.utils import pickle_hashing
from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
E1_REPORT = ROOT / "reports/e1_stage01_20261017"
FULL_REPORT = ROOT / "reports/original_author_reproduction_20261020"
OT_REPORT = ROOT / "reports/tracer_only_control_20261027"
FULL_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020")
OT_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022")
FULL_CACHE = ROOT / "results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup"
EXPECTED_SHAPE = (160, 192, 160)
EPOCH = 165
MRI_TOLERANCE = 2e-6  # Frozen E1 saved-MRI replay gate; not selected from Full/OT results.


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


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def frozen_hash_check(config: dict, path: Path) -> dict:
    expected = config["frozen_files"].get(str(path.resolve()))
    actual = sha256(path)
    return {"path": str(path), "expected_sha256": expected, "actual_sha256": actual, "pass": actual == expected}


def normalized_input_rows(path: Path, kinds=("mri", "fdg", "av45")) -> dict:
    result = {}
    for row in read_csv(path):
        if row["kind"] in kinds:
            key = (row["ptid"], row["kind"])
            if key in result:
                raise RuntimeError(f"Duplicate input identity: {key}")
            result[key] = {"path": row["path"], "sha256": row["sha256"], "bytes": int(row["bytes"])}
    return result


def prediction_rows(path: Path, model: str) -> list[dict]:
    rows = []
    for row in read_csv(path):
        if int(row["epoch"]) != EPOCH:
            continue
        rows.append(
            {
                "model": model,
                "ptid": row["ptid"],
                "tracer": row["tracer"].lower(),
                "fold": int(row["fold"]),
                "epoch": int(row["epoch"]),
                "prediction": row["prediction"],
                "prediction_sha256": row["prediction_sha256"],
                "checkpoint_sha256": row["checkpoint_sha256"],
            }
        )
    keys = [(r["ptid"], r["tracer"], r["fold"], r["epoch"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError(f"Duplicate {model} OOF identity")
    return rows


def expected_prediction_path(model: str, row: dict) -> Path:
    base = FULL_ASSETS if model == "Full" else OT_ASSETS
    return base / "oof" / f"epoch{EPOCH}" / f"fold{row['fold']}" / f"generated_{row['tracer']}_{row['ptid']}.nii.gz"


def validate_receipts(rows: list[dict], model: str) -> dict:
    base = FULL_ASSETS if model == "Full" else OT_ASSETS
    receipts = {}
    for fold in (1, 2):
        receipt_path = base / "oof" / f"epoch{EPOCH}" / f"fold{fold}" / "complete.json"
        receipt = read_json(receipt_path)
        metrics = receipt_path.parent / "metrics.csv"
        checks = {
            "fold": fold,
            "path": str(receipt_path),
            "input_source": receipt.get("input_source"),
            "persistent_cache": receipt.get("persistent_cache"),
            "metrics_sha256_expected": receipt.get("metrics_sha256"),
            "metrics_sha256_actual": sha256(metrics),
            "checkpoint_sha256": receipt.get("checkpoint_sha256"),
            "metric_rows": int(receipt.get("metric_rows", -1)),
        }
        checks["pass"] = bool(
            checks["input_source"] == "verified_persistent_cache"
            and Path(checks["persistent_cache"]).resolve() == FULL_CACHE.resolve()
            and checks["metrics_sha256_expected"] == checks["metrics_sha256_actual"]
            and checks["metric_rows"] == sum(r["fold"] == fold for r in rows)
            and {r["checkpoint_sha256"] for r in rows if r["fold"] == fold} == {checks["checkpoint_sha256"]}
        )
        receipts[str(fold)] = checks
    return receipts


def build_identity() -> dict:
    started = time.time()
    e1_config = read_json(E1_REPORT / "config.json")
    e1_cohort = read_json(E1_REPORT / "cohort.json")
    full_cohort = read_json(FULL_REPORT / "cohort.json")
    exclusions = read_json(E1_REPORT / "qc_exclusions.json")["excluded"]
    excluded = {r["ptid"] for r in exclusions}
    e1_by_ptid = {r["ptid"]: r for r in e1_cohort}
    full_by_ptid = {r["name"]: r for r in full_cohort}
    active = sorted(set(e1_by_ptid) - excluded)
    if len(e1_by_ptid) != 1857 or len(full_by_ptid) != 1857 or set(e1_by_ptid) != set(full_by_ptid):
        raise RuntimeError("Full and E1 frozen cohorts are not the same 1,857 PTIDs")
    if len(active) != 1856 or excluded != {"016_S_4952"}:
        raise RuntimeError(f"Unexpected E1 active cohort/exclusion: {len(active)} {excluded}")

    full_rows = prediction_rows(FULL_REPORT / "oof_summary/per_subject_metrics.csv", "Full")
    ot_rows = prediction_rows(OT_REPORT / "oof_summary/per_subject_metrics.csv", "OT")
    fkeys = {(r["ptid"], r["tracer"], r["fold"], r["epoch"]) for r in full_rows}
    okeys = {(r["ptid"], r["tracer"], r["fold"], r["epoch"]) for r in ot_rows}
    if fkeys != okeys:
        raise RuntimeError(f"Full/OT epoch-165 identity mismatch: Full-only={len(fkeys-okeys)}, OT-only={len(okeys-fkeys)}")
    fold_by_ptid = {}
    for ptid, _tracer, fold, _epoch in fkeys:
        previous = fold_by_ptid.setdefault(ptid, fold)
        if previous != fold or full_by_ptid[ptid]["test_fold"] != fold:
            raise RuntimeError(f"Fold mismatch for {ptid}")

    active_set = set(active)
    filtered_full = [r for r in full_rows if r["ptid"] in active_set]
    filtered_ot = [r for r in ot_rows if r["ptid"] in active_set]
    expected = {
        (ptid, tracer)
        for ptid in active
        for tracer in ("fdg", "av45")
        if bool(e1_by_ptid[ptid][f"has_{tracer}"])
    }
    actual_full = {(r["ptid"], r["tracer"]) for r in filtered_full}
    actual_ot = {(r["ptid"], r["tracer"]) for r in filtered_ot}
    if expected != actual_full or expected != actual_ot:
        raise RuntimeError("E1 tracer availability and Full/OT OOF identities do not match")

    full_inputs = normalized_input_rows(FULL_REPORT / "input_hashes.csv")
    e1_inputs = normalized_input_rows(E1_REPORT / "input_hashes_final.csv")
    common_input_keys = set(full_inputs) & set(e1_inputs)
    mismatched_inputs = [
        {"ptid": k[0], "kind": k[1], "full": full_inputs[k], "e1": e1_inputs[k]}
        for k in sorted(common_input_keys)
        if full_inputs[k] != e1_inputs[k]
    ]

    source_checks = [
        frozen_hash_check(e1_config, E1_REPORT / "cohort.json"),
        frozen_hash_check(e1_config, E1_REPORT / "input_hashes_final.csv"),
        frozen_hash_check(e1_config, E1_REPORT / "hemisphere_label_map.json"),
        frozen_hash_check(e1_config, E1_REPORT / "roi_validity.json"),
    ]
    result = {
        "epoch": EPOCH,
        "e1_cohort": len(e1_by_ptid),
        "full_cohort": len(full_by_ptid),
        "excluded_ptids": sorted(excluded),
        "active_subjects": len(active),
        "active_tracer_counts": {t: sum(e1_by_ptid[p][f"has_{t}"] for p in active) for t in ("fdg", "av45")},
        "full_epoch165_rows_before_intersection": len(full_rows),
        "ot_epoch165_rows_before_intersection": len(ot_rows),
        "full_epoch165_rows_after_intersection": len(filtered_full),
        "ot_epoch165_rows_after_intersection": len(filtered_ot),
        "fold_subject_counts_before_intersection": {str(f): sum(v == f for v in fold_by_ptid.values()) for f in (1, 2)},
        "fold_subject_counts_after_intersection": {str(f): sum(fold_by_ptid[p] == f for p in active) for f in (1, 2)},
        "full_ot_key_equality": fkeys == okeys,
        "input_manifest_common_keys": len(common_input_keys),
        "input_manifest_mismatches": mismatched_inputs,
        "source_file_hash_checks": source_checks,
        "full_receipts": validate_receipts(full_rows, "Full"),
        "ot_receipts": validate_receipts(ot_rows, "OT"),
        "cache_dir": str(FULL_CACHE),
        "cache_file_count": len(list(FULL_CACHE.glob("*.pt"))),
        "elapsed_seconds": time.time() - started,
    }
    result["pass"] = bool(
        result["active_subjects"] == 1856
        and result["active_tracer_counts"] == {"fdg": 1597, "av45": 1364}
        and len(filtered_full) == len(filtered_ot) == 2961
        and result["cache_file_count"] == 1857
        and not mismatched_inputs
        and len(common_input_keys) == 5571
        and all(x["pass"] for x in source_checks)
        and all(x["pass"] for x in result["full_receipts"].values())
        and all(x["pass"] for x in result["ot_receipts"].values())
    )
    return {
        "summary": result,
        "active": active,
        "e1_by_ptid": e1_by_ptid,
        "full_by_ptid": full_by_ptid,
        "fold_by_ptid": fold_by_ptid,
        "full_rows": filtered_full,
        "ot_rows": filtered_ot,
    }


def cache_check(task: dict) -> dict:
    ptid = task["ptid"]
    cache_path = Path(task["full_cache"])
    e1_path = Path(task["e1_cache"])
    expected_e1_sha = task["e1_cache_sha256"]
    try:
        item = torch.load(cache_path, map_location="cpu", weights_only=False)
        full_mri = item["mri"].detach().cpu().numpy().squeeze()
        with np.load(e1_path, allow_pickle=False) as saved:
            e1_mri = np.asarray(saved["mri"])
            mask = np.asarray(saved["mask"])
            affine = np.asarray(saved["affine"], dtype=np.float64)
        if full_mri.shape == e1_mri.shape:
            difference = np.abs(full_mri.astype(np.float64) - e1_mri.astype(np.float64))
            max_abs = float(difference.max())
            mean_abs = float(difference.mean(dtype=np.float64))
            differing_voxels = int(np.count_nonzero(difference))
        else:
            max_abs = mean_abs = None
            differing_voxels = None
        mask_integer = bool(np.issubdtype(mask.dtype, np.integer) or np.array_equal(mask, np.rint(mask)))
        e1_actual_sha = sha256(e1_path)
        row = {
            "ptid": ptid,
            "diagnosis": task["diagnosis"],
            "fold": task["fold"],
            "full_cache": str(cache_path),
            "e1_cache": str(e1_path),
            "full_cache_internal_ptid": item.get("name"),
            "full_cache_internal_fold": int(item.get("test_fold", -1)),
            "full_mri_shape": "x".join(map(str, full_mri.shape)),
            "e1_mri_shape": "x".join(map(str, e1_mri.shape)),
            "mask_shape": "x".join(map(str, mask.shape)),
            "full_mri_dtype": str(full_mri.dtype),
            "e1_mri_dtype": str(e1_mri.dtype),
            "mask_dtype": str(mask.dtype),
            "full_mri_finite": bool(np.isfinite(full_mri).all()),
            "e1_mri_finite": bool(np.isfinite(e1_mri).all()),
            "mask_finite": bool(np.isfinite(mask).all()),
            "mask_integer": mask_integer,
            "mask_nonzero_voxels": int(np.count_nonzero(mask)),
            "mask_inside_finite_mri": bool(np.isfinite(e1_mri[mask != 0]).all()),
            "affine_finite": bool(affine.shape == (4, 4) and np.isfinite(affine).all()),
            "affine_determinant": float(np.linalg.det(affine[:3, :3])) if affine.shape == (4, 4) else None,
            "mri_exact_equal": bool(full_mri.shape == e1_mri.shape and np.array_equal(full_mri, e1_mri)),
            "mri_max_abs_error": max_abs,
            "mri_mean_abs_error": mean_abs,
            "mri_differing_voxels": differing_voxels,
            "mri_tolerance": MRI_TOLERANCE,
            "mri_within_frozen_e1_tolerance": bool(max_abs is not None and max_abs <= MRI_TOLERANCE),
            "e1_cache_sha256_expected": expected_e1_sha,
            "e1_cache_sha256_actual": e1_actual_sha,
            "e1_cache_sha256_match": e1_actual_sha == expected_e1_sha,
            "raw_saved_mri_replay_maxabs_receipt": float(task["raw_replay_maxabs"]),
            "raw_saved_mri_replay_pass_receipt": bool(task["raw_replay_maxabs"] <= 2e-6),
            "error": "",
        }
        row["pass"] = bool(
            row["full_cache_internal_ptid"] == ptid
            and row["full_cache_internal_fold"] == task["fold"]
            and full_mri.shape == e1_mri.shape == mask.shape == EXPECTED_SHAPE
            and row["full_mri_dtype"] == row["e1_mri_dtype"] == "float32"
            and row["full_mri_finite"] and row["e1_mri_finite"]
            and row["mask_finite"] and row["mask_integer"] and row["mask_nonzero_voxels"] > 0
            and row["mask_inside_finite_mri"] and row["affine_finite"]
            and row["mri_within_frozen_e1_tolerance"]
            and row["e1_cache_sha256_match"] and row["raw_saved_mri_replay_pass_receipt"]
        )
        return row
    except Exception as exc:
        return {"ptid": ptid, "diagnosis": task["diagnosis"], "fold": task["fold"], "pass": False, "error": repr(exc)}


def prediction_check(task: dict) -> dict:
    path = Path(task["prediction"])
    expected_path = Path(task["expected_path"])
    try:
        compressed = path.read_bytes()
        actual_sha = hashlib.sha256(compressed).hexdigest()
        image = nib.Nifti1Image.from_bytes(gzip.decompress(compressed))
        array = np.asanyarray(image.dataobj)
        affine = np.asarray(image.affine, dtype=np.float64)
        row = {
            "model": task["model"],
            "ptid": task["ptid"],
            "tracer": task["tracer"],
            "fold": task["fold"],
            "epoch": task["epoch"],
            "prediction": str(path),
            "expected_path": str(expected_path),
            "path_exact": path == expected_path,
            "prediction_sha256_expected": task["prediction_sha256"],
            "prediction_sha256_actual": actual_sha,
            "sha256_match": actual_sha == task["prediction_sha256"],
            "checkpoint_sha256": task["checkpoint_sha256"],
            "shape": "x".join(map(str, image.shape)),
            "dtype": str(image.get_data_dtype()),
            "finite": bool(np.isfinite(array).all()),
            "identity_affine": bool(np.array_equal(affine, np.eye(4))),
            "min": float(array.min()),
            "max": float(array.max()),
            "error": "",
        }
        row["pass"] = bool(
            row["path_exact"] and row["sha256_match"] and image.shape == EXPECTED_SHAPE
            and row["dtype"] == "float32" and row["finite"] and row["identity_affine"]
        )
        return row
    except Exception as exc:
        return {
            "model": task["model"], "ptid": task["ptid"], "tracer": task["tracer"],
            "fold": task["fold"], "epoch": task["epoch"], "prediction": str(path),
            "pass": False, "error": repr(exc),
        }


def parallel_map(function, tasks: list[dict], workers: int, label: str) -> list[dict]:
    results = []
    started = time.time()
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(function, task): task for task in tasks}
        for number, future in enumerate(as_completed(futures), 1):
            results.append(future.result())
            if number == 1 or number % 100 == 0 or number == len(tasks):
                print(json.dumps({"event": label, "done": number, "total": len(tasks), "elapsed_seconds": round(time.time() - started, 1)}), flush=True)
    return sorted(results, key=lambda r: tuple(r.get(k, "") for k in ("model", "ptid", "tracer")))


def make_tasks(identity: dict, ptids: list[str]) -> tuple[list[dict], list[dict]]:
    geometry = {r["ptid"]: r for r in read_json(E1_REPORT / "geometry_qc_final.json")}
    cache_tasks = []
    for ptid in ptids:
        full_row = identity["full_by_ptid"][ptid]
        e1_row = identity["e1_by_ptid"][ptid]
        full_cache_path = FULL_CACHE / (pickle_hashing(full_row).decode() + ".pt")
        geo = geometry[ptid]
        cache_tasks.append(
            {
                "ptid": ptid,
                "diagnosis": e1_row["diagnosis"],
                "fold": identity["fold_by_ptid"][ptid],
                "full_cache": str(full_cache_path),
                "e1_cache": e1_row["cache"],
                "e1_cache_sha256": geo["cache_sha256"],
                "raw_replay_maxabs": geo["saved_mri_replay_maxabs"],
            }
        )
    chosen = set(ptids)
    pred_tasks = []
    for row in identity["full_rows"] + identity["ot_rows"]:
        if row["ptid"] not in chosen:
            continue
        task = dict(row)
        task["expected_path"] = str(expected_prediction_path(row["model"], row))
        pred_tasks.append(task)
    return cache_tasks, pred_tasks


def choose_precheck(identity: dict) -> list[str]:
    full_keys = {(r["ptid"], r["tracer"]) for r in identity["full_rows"]}
    selected = []
    for fold in (1, 2):
        for diagnosis in ("AD", "CN", "EMCI", "LMCI", "MCI"):
            candidates = [
                ptid for ptid in identity["active"]
                if identity["fold_by_ptid"][ptid] == fold
                and identity["e1_by_ptid"][ptid]["diagnosis"] == diagnosis
                and (ptid, "fdg") in full_keys and (ptid, "av45") in full_keys
            ]
            if not candidates:
                raise RuntimeError(f"No dual-tracer precheck subject for fold={fold}, diagnosis={diagnosis}")
            selected.append(sorted(candidates)[0])
    return selected


def physical_centroid_checks(ptids: list[str], identity: dict) -> list[dict]:
    laterality = read_json(E1_REPORT / "hemisphere_label_map.json")
    pairs = ((2, 41), (12, 51), (4, 43), (10, 49))
    rows = []
    for ptid in ptids:
        with np.load(identity["e1_by_ptid"][ptid]["cache"], allow_pickle=False) as saved:
            mask = np.asarray(saved["mask"])
            affine = np.asarray(saved["affine"], dtype=np.float64)
        pair_results = {}
        for right_label, left_label in pairs:
            right_coords = np.argwhere(mask == right_label)
            left_coords = np.argwhere(mask == left_label)
            right_x = float(nib.affines.apply_affine(affine, right_coords.mean(0))[0]) if len(right_coords) else None
            left_x = float(nib.affines.apply_affine(affine, left_coords.mean(0))[0]) if len(left_coords) else None
            map_ok = (
                laterality["labels"][str(right_label)]["physical_hemisphere"] == "right"
                and laterality["labels"][str(left_label)]["physical_hemisphere"] == "left"
            )
            pair_results[f"{right_label}_{left_label}"] = {
                "right_label_physical_x": right_x,
                "left_label_physical_x": left_x,
                "map_names": [laterality["labels"][str(right_label)]["physical_name"], laterality["labels"][str(left_label)]["physical_name"]],
                "pass": bool(map_ok and right_x is not None and left_x is not None and right_x > left_x),
            }
        rows.append({"ptid": ptid, "fold": identity["fold_by_ptid"][ptid], "diagnosis": identity["e1_by_ptid"][ptid]["diagnosis"], "pairs": pair_results, "pass": all(v["pass"] for v in pair_results.values())})
    return rows


def overlay_panel(mri: np.ndarray, mask: np.ndarray, axis: int) -> Image.Image:
    areas = np.count_nonzero(mask, axis=tuple(i for i in range(3) if i != axis))
    index = int(np.argmax(areas))
    gray = np.take(mri, index, axis=axis)
    seg = np.take(mask != 0, index, axis=axis)
    gray = np.rot90(gray)
    seg = np.rot90(seg)
    boundary = seg & ~(np.roll(seg, 1, 0) & np.roll(seg, -1, 0) & np.roll(seg, 1, 1) & np.roll(seg, -1, 1))
    rgb = np.repeat(np.clip(gray * 255, 0, 255).astype(np.uint8)[..., None], 3, axis=2)
    rgb[boundary] = np.array([255, 50, 50], dtype=np.uint8)
    image = Image.fromarray(rgb).resize((180, 180), Image.Resampling.BILINEAR)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 179, 16), fill=(0, 0, 0))
    draw.text((4, 2), f"axis {axis} / slice {index}", fill=(255, 255, 255))
    return image


def make_overlay(ptids: list[str], identity: dict, path: Path) -> None:
    canvas = Image.new("RGB", (560, 212 * len(ptids)), "white")
    draw = ImageDraw.Draw(canvas)
    for row_index, ptid in enumerate(ptids):
        with np.load(identity["e1_by_ptid"][ptid]["cache"], allow_pickle=False) as saved:
            mri = np.asarray(saved["mri"])
            mask = np.asarray(saved["mask"])
        top = row_index * 212
        label = f"{ptid} | fold {identity['fold_by_ptid'][ptid]} | {identity['e1_by_ptid'][ptid]['diagnosis']} | red=mask boundary"
        draw.text((4, top + 2), label, fill=(0, 0, 0))
        for axis in range(3):
            canvas.paste(overlay_panel(mri, mask, axis), (4 + axis * 184, top + 24))
    canvas.save(path)


def summarize_phase(identity: dict, ptids: list[str], cache_rows: list[dict], pred_rows: list[dict], laterality_rows: list[dict], phase: str) -> dict:
    result = {
        "phase": phase,
        "identity": identity["summary"],
        "subjects_checked": len(ptids),
        "ptids": ptids,
        "cache_checks": {
            "rows": len(cache_rows),
            "passed": sum(bool(r["pass"]) for r in cache_rows),
            "failed_ptids": [r["ptid"] for r in cache_rows if not r["pass"]],
            "max_mri_max_abs_error": max((r.get("mri_max_abs_error") or 0.0) for r in cache_rows),
            "dtype_pairs": sorted({(r.get("full_mri_dtype"), r.get("e1_mri_dtype")) for r in cache_rows}),
        },
        "prediction_checks": {
            "rows": len(pred_rows),
            "passed": sum(bool(r["pass"]) for r in pred_rows),
            "failed": [{k: r.get(k) for k in ("model", "ptid", "tracer", "fold", "error")} for r in pred_rows if not r["pass"]],
            "by_model_tracer": {
                f"{model}_{tracer}": {
                    "rows": sum(r["model"] == model and r["tracer"] == tracer for r in pred_rows),
                    "passed": sum(r["model"] == model and r["tracer"] == tracer and r["pass"] for r in pred_rows),
                }
                for model in ("Full", "OT") for tracer in ("fdg", "av45")
            },
        },
        "laterality_checks": {
            "rows": len(laterality_rows),
            "passed": sum(bool(r["pass"]) for r in laterality_rows),
            "failed_ptids": [r["ptid"] for r in laterality_rows if not r["pass"]],
        },
    }
    result["pass"] = bool(
        result["identity"]["pass"]
        and result["cache_checks"]["rows"] == result["cache_checks"]["passed"] == len(ptids)
        and result["prediction_checks"]["rows"] == result["prediction_checks"]["passed"]
        and result["laterality_checks"]["rows"] == result["laterality_checks"]["passed"]
    )
    return result


def run_precheck(workers: int) -> None:
    identity = build_identity()
    ptids = choose_precheck(identity)
    cache_tasks, pred_tasks = make_tasks(identity, ptids)
    cache_rows = parallel_map(cache_check, cache_tasks, workers, "precheck_cache")
    pred_rows = parallel_map(prediction_check, pred_tasks, workers, "precheck_predictions")
    laterality_rows = physical_centroid_checks(ptids, identity)
    make_overlay(ptids, identity, OUT / "02_precheck_overlay.png")
    result = summarize_phase(identity, ptids, cache_rows, pred_rows, laterality_rows, "precheck")
    result["cache_rows"] = cache_rows
    result["prediction_rows"] = pred_rows
    result["laterality_rows"] = laterality_rows
    write_json(OUT / "02_precheck_results.json", result)
    print(json.dumps({"phase": "precheck", "pass": result["pass"], "subjects": len(ptids), "predictions": len(pred_rows)}), flush=True)
    if not result["pass"]:
        raise SystemExit("Precheck failed; full-cohort expansion is prohibited")


def run_full(workers: int) -> None:
    precheck_path = OUT / "02_precheck_results.json"
    if not precheck_path.exists() or not read_json(precheck_path).get("pass"):
        raise SystemExit("Passing precheck receipt is required before full expansion")
    identity = build_identity()
    ptids = identity["active"]
    cache_tasks, pred_tasks = make_tasks(identity, ptids)
    cache_rows = parallel_map(cache_check, cache_tasks, workers, "full_cache")
    if not all(r["pass"] for r in cache_rows):
        result = summarize_phase(identity, ptids, cache_rows, [], [], "full_stopped_at_mri_gate")
        write_json(OUT / "02_spatial_validation_results.json", result)
        write_csv(OUT / "02_spatial_subject_checks.csv", cache_rows)
        raise SystemExit("Core MRI grid check failed; prediction expansion stopped")
    pred_rows = parallel_map(prediction_check, pred_tasks, workers, "full_predictions")
    precheck = read_json(precheck_path)
    laterality_rows = precheck["laterality_rows"]
    result = summarize_phase(identity, ptids, cache_rows, pred_rows, laterality_rows, "full")
    result["laterality_checks"]["scope_note"] = "Current 10-subject physical-centroid replay plus frozen 1856/1856 laterality_fix_receipt gate"
    result["frozen_laterality_receipt"] = read_json(E1_REPORT / "laterality_fix_receipt.json")
    result["roi_validity_reuse"] = {
        "path": str(E1_REPORT / "roi_validity.json"),
        "sha256": sha256(E1_REPORT / "roi_validity.json"),
        "frozen_sha256": read_json(E1_REPORT / "config.json")["frozen_files"][str((E1_REPORT / "roi_validity.json").resolve())],
        "subject_keys": len(read_json(E1_REPORT / "roi_validity.json")["invalid_rois"]),
        "rule": read_json(E1_REPORT / "roi_validity.json")["rule"],
        "directly_reusable": bool(all(r["pass"] for r in cache_rows)),
    }
    write_json(OUT / "02_spatial_validation_results.json", result)
    write_csv(OUT / "02_spatial_subject_checks.csv", cache_rows)
    write_csv(OUT / "02_prediction_identity_checks.csv", pred_rows)
    print(json.dumps({"phase": "full", "pass": result["pass"], "subjects": len(ptids), "predictions": len(pred_rows)}), flush=True)
    if not result["pass"]:
        raise SystemExit("Full validation failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("precheck", "full"))
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    if args.phase == "precheck":
        run_precheck(args.workers)
    else:
        run_full(args.workers)


if __name__ == "__main__":
    main()
