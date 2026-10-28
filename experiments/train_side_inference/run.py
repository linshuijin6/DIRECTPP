#!/usr/bin/env python3
"""Fail-closed train-side PET inference for Stage 4C.

The default and currently validated operation is ``check-only``.  ``infer`` is
implemented for the subsequent, explicitly authorized stage and requires one
model/fold plus an acknowledgement flag.  It never consumes cross-OOF PET.
"""
from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_DIR = ROOT / "reports/full_ot_medical_evidence"
FULL_CONFIG = ROOT / "reports/original_author_reproduction_20261020/config.json"
FULL_CACHE_RECEIPT = ROOT / "reports/original_author_reproduction_20261020/persistent_cache_receipt.json"
MODE_OT = "tracer_only_fixed_empty_patient"
TRACERS = ("fdg", "av45")
PILOT_DIAGNOSES = ("CN", "AD", "EMCI", "LMCI")
PILOT_SUBJECTS_PER_FOLD = 4
PILOT_VOLUMES_PER_RUN = 8
FULL_SUBJECTS = {1: 457, 2: 448}
FULL_VOLUMES = {1: 914, 2: 896}
PILOT_OUTPUT_ROOT = Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c2_pilot/20261028/epoch165")
FORMAL_OUTPUT_ROOT = Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c3_train_side/20261028/epoch165")


class ContractError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 << 20), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def atomic_json(path: Path, value: dict) -> None:
    if path.exists():
        raise ContractError(f"refusing to overwrite result: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def check_file(path: Path, expected_sha: str, expected_bytes: int | None = None) -> dict:
    if not path.is_file():
        raise ContractError(f"missing file: {path}")
    size = path.stat().st_size
    digest = sha256(path)
    if expected_bytes is not None and size != int(expected_bytes):
        raise ContractError(f"byte-size mismatch: {path}")
    if digest != expected_sha:
        raise ContractError(f"SHA-256 mismatch: {path}")
    return {"path": str(path), "bytes": size, "sha256": digest}


def read_manifests(paths: list[Path], receipt: dict, config: dict) -> tuple[list[dict], list[dict]]:
    all_rows, identities = [], []
    for path in paths:
        meta = receipt["outputs"].get(path.name)
        if not meta:
            raise ContractError(f"manifest absent from frozen receipt: {path.name}")
        identities.append(check_file(path, meta["sha256"], meta["bytes"]))
        with path.open(newline="") as f:
            rows = list(csv.DictReader(f))
        if len(rows) != int(meta["rows"]):
            raise ContractError(f"row-count mismatch: {path}")
        all_rows.extend(rows)
    if len(paths) != 3 or len({p.name for p in paths}) != 3:
        raise ContractError("exactly the three frozen task manifests are required")
    allowed_tasks = set(config["tasks"])
    if {r["task"] for r in all_rows} != allowed_tasks:
        raise ContractError("task identity differs from frozen config")
    keys = [(r["task"], r["outer_fold"], r["ptid"]) for r in all_rows]
    if len(keys) != len(set(keys)):
        raise ContractError("duplicate task/outer_fold/PTID")
    return all_rows, identities


def validate_rows(rows: list[dict], config: dict) -> dict[int, list[dict]]:
    # Collapse task overlap, while requiring every shared identity to agree.
    canonical: dict[tuple[int, str], dict] = {}
    stable = ("diagnosis", "generator_fold", "source_mri_path", "source_mri_sha256")
    for row in rows:
        f, g = int(row["outer_fold"]), int(row["generator_fold"])
        if f not in (1, 2) or g not in (1, 2):
            raise ContractError("fold outside {1,2}")
        expected_role = "outer_test" if g == f else "outer_train"
        if row["outer_role"] != expected_role:
            raise ContractError(f"outer role/fold mismatch: {row['ptid']}")
        for model in ("full", "ot"):
            expected_ckpt = config["generator_checkpoints"][f"{model.upper() if model == 'ot' else 'Full'}_fold{f}"]
            if row[f"{model}_checkpoint_path"] != expected_ckpt["path"] or row[f"{model}_checkpoint_sha256"] != expected_ckpt["sha256"]:
                raise ContractError(f"manifest checkpoint binding mismatch: {model}, fold {f}, {row['ptid']}")
            expected_cond = config["conditions_identity"]["OT" if model == "ot" else "Full"]
            if row[f"{model}_condition_path"] != expected_cond["path"] or row[f"{model}_condition_sha256"] != expected_cond["sha256"]:
                raise ContractError(f"manifest condition binding mismatch: {model}, fold {f}, {row['ptid']}")
            for tracer in TRACERS:
                usage = row[f"{model}_{tracer}_existing_oof_usage"]
                status = row[f"{model}_{tracer}_asset_status"]
                if expected_role == "outer_train" and (usage != "FORBIDDEN_AS_OUTER_TRAIN_INPUT" or status != "PLANNED_MISSING"):
                    raise ContractError(f"cross-OOF is not forbidden for train-side row: {row['ptid']}")
        key = (f, row["ptid"])
        if key in canonical and any(canonical[key][k] != row[k] for k in stable):
            raise ContractError(f"task manifests disagree for {key}")
        canonical.setdefault(key, row)
    selected: dict[int, list[dict]] = {}
    for f in (1, 2):
        selected[f] = sorted(
            (r for (of, _), r in canonical.items() if of == f and int(r["generator_fold"]) != f),
            key=lambda r: r["ptid"],
        )
        if any(r["outer_role"] != "outer_train" or int(r["generator_fold"]) == f for r in selected[f]):
            raise ContractError("outer-test subject selected into train-side set")
        if len({r["ptid"] for r in selected[f]}) != len(selected[f]):
            raise ContractError("duplicate train-side PTID")
    return selected


def validate_execution_selection(rows: list[dict], outer_fold: int, expected_count: int | None = None) -> None:
    """Validate actual rows supplied to a run; used by execution and negative tests."""
    if outer_fold not in (1, 2):
        raise ContractError("requested outer fold outside {1,2}")
    if expected_count is not None and len(rows) != expected_count:
        raise ContractError(f"selection count {len(rows)} != strict expected count {expected_count}")
    if len({r["ptid"] for r in rows}) != len(rows):
        raise ContractError("duplicate PTID in execution selection")
    for row in rows:
        if int(row["outer_fold"]) != outer_fold:
            raise ContractError(f"row belongs to wrong outer fold: {row['ptid']}")
        if row["outer_role"] != "outer_train" or int(row["generator_fold"]) == outer_fold:
            raise ContractError(f"outer-test subject selected into train-side execution: {row['ptid']}")
        for model in ("full", "ot"):
            for tracer in TRACERS:
                if row[f"{model}_{tracer}_existing_oof_usage"] != "FORBIDDEN_AS_OUTER_TRAIN_INPUT":
                    raise ContractError(f"cross-OOF use not forbidden: {row['ptid']}")


def select_pilot(selected: dict[int, list[dict]]) -> dict[int, list[dict]]:
    pilot = {}
    for fold in (1, 2):
        chosen = []
        for diagnosis in PILOT_DIAGNOSES:
            candidates = sorted((r for r in selected[fold] if r["diagnosis"] == diagnosis), key=lambda r: r["ptid"])
            if not candidates:
                raise ContractError(f"pilot diagnosis absent in outer fold {fold}: {diagnosis}")
            chosen.append(candidates[0])
        validate_execution_selection(chosen, fold, PILOT_SUBJECTS_PER_FOLD)
        if [r["diagnosis"] for r in chosen] != list(PILOT_DIAGNOSES):
            raise ContractError("pilot diagnosis order changed")
        pilot[fold] = chosen
    if sum(len(v) for v in pilot.values()) * len(TRACERS) * 2 != 32:
        raise ContractError("pilot hard cap invariant is not 32 volumes")
    return pilot


def verify_full_runtime(selected: dict[int, list[dict]]) -> tuple[dict, list[dict], dict]:
    cfg = load_json(FULL_CONFIG)
    report = Path(cfg["report"])
    check_file(report / "cohort.json", cfg["cohort_sha256"])
    check_file(report / "split_manifest.csv", cfg["split_manifest_sha256"])
    cohort = load_json(report / "cohort.json")
    input_receipt = load_json(report / "input_hashes_receipt.json")
    input_manifest = check_file(report / "input_hashes.csv", input_receipt["manifest_sha256"])
    by_ptid = {r["name"]: r for r in cohort}
    if len(by_ptid) != len(cohort):
        raise ContractError("duplicate PTID in generator cohort")
    for f, rows in selected.items():
        for row in rows:
            original = by_ptid.get(row["ptid"])
            if original is None or int(original["test_fold"]) != int(row["generator_fold"]):
                raise ContractError(f"manifest generator fold differs from Full cohort: {row['ptid']}")
            if original["mri"] != row["source_mri_path"]:
                raise ContractError(f"manifest MRI path differs from generator cohort: {row['ptid']}")
    cache = load_json(FULL_CACHE_RECEIPT)
    recorded_cache_dir = Path(cache["cache_dir"])
    cache_dir = recorded_cache_dir
    if not cache_dir.is_dir():
        # The completed cache was moved, not regenerated; accept only the
        # uniquely named NFS backup of the receipt-bound namespace.
        fallback = recorded_cache_dir.with_name(recorded_cache_dir.name + "_nfs_backup")
        if fallback.is_dir():
            cache_dir = fallback
    files = list(cache_dir.glob("*.pt")) if cache_dir.is_dir() else []
    if cache.get("status") != "COMPLETE" or len(files) != len(cohort):
        raise ContractError("frozen persistent cache is absent or incomplete")
    expected_prefix = f"v1_{input_manifest['sha256'][:16]}_"
    if cache.get("input_hashes_sha256") != input_manifest["sha256"] or not str(cache.get("cache_namespace", "")).startswith(expected_prefix):
        raise ContractError("persistent-cache provenance binding mismatch")
    return cfg, cohort, {
        "receipt": str(FULL_CACHE_RECEIPT), "recorded_cache_dir": str(recorded_cache_dir),
        "cache_dir": str(cache_dir), "relocated_exact_namespace_backup": cache_dir != recorded_cache_dir,
        "files": len(files), "subjects": len(cohort),
        "input_manifest_sha256": input_manifest["sha256"],
        "cache_namespace": cache.get("cache_namespace"),
        "per_cache_file_sha256": "UNAVAILABLE; namespace/input/condition binding and complete expected file set are checked",
    }


def verify_conditions(config: dict, cohort: list[dict]) -> dict:
    import torch

    full_id = config["conditions_identity"]["Full"]
    ot_id = config["conditions_identity"]["OT"]
    full_path, ot_path = Path(full_id["path"]), Path(ot_id["path"])
    check_file(full_path, full_id["sha256"], full_id["bytes"])
    check_file(ot_path, ot_id["sha256"], ot_id["bytes"])
    full = torch.load(full_path, map_location="cpu", weights_only=False)
    ot = torch.load(ot_path, map_location="cpu", weights_only=False)
    if full.get("ptids") != [r["name"] for r in cohort]:
        raise ContractError("Full condition PTID order differs from frozen generator cohort")
    if tuple(full["patient"].shape) != (1857, 512) or tuple(full["tracer"].shape) != (2, 512):
        raise ContractError("Full condition tensor shape mismatch")
    if ot.get("condition_mode") != MODE_OT or ot.get("empty_text") != "":
        raise ContractError("OT is not frozen empty-patient+tracer conditioning")
    if tuple(ot["empty_patient"].shape) != (1, 512) or tuple(ot["tracer"].shape) != (2, 512):
        raise ContractError("OT condition tensor shape mismatch")
    tensors = (full["patient"], full["tracer"], ot["empty_patient"], ot["tracer"])
    if not all(bool(torch.isfinite(x).all()) for x in tensors):
        raise ContractError("non-finite conditioning tensor")
    if not torch.equal(full["tracer"], ot["tracer"]) or torch.equal(ot["tracer"][0], ot["tracer"][1]):
        raise ContractError("OT tracer tokens differ from Full or FDG/AV45 are identical")
    if ot.get("full_conditions_sha256") != full_id["sha256"]:
        raise ContractError("OT condition is not bound to frozen Full conditions")
    empty_sha = hashlib.sha256(ot["empty_patient"].contiguous().numpy().tobytes()).hexdigest()
    return {
        "Full": {"sha256": full_id["sha256"], "patient_shape": list(full["patient"].shape), "tracer_shape": list(full["tracer"].shape)},
        "OT": {"sha256": ot_id["sha256"], "mode": MODE_OT, "empty_patient_shape": [1, 512], "tracer_shape": [2, 512], "empty_patient_sha256": empty_sha},
    }


def verify_checkpoints(config: dict, conditions: dict) -> dict:
    result = {}
    for model in ("Full", "OT"):
        for fold in (1, 2):
            key = f"{model}_fold{fold}"
            item = config["generator_checkpoints"][key]
            check_file(Path(item["path"]), item["sha256"], item["bytes"])
            check_file(Path(item["receipt"]), item["receipt_sha256"])
            receipt = load_json(Path(item["receipt"]))
            if receipt.get("fold") != fold or receipt.get("epoch_one_based") != 165 or receipt.get("checkpoint_sha256") != item["sha256"] or receipt.get("model_sha256") != item["model_sha256"]:
                raise ContractError(f"checkpoint receipt mismatch: {key}")
            if model == "Full":
                if receipt.get("conditions_sha256") != conditions["Full"]["sha256"]:
                    raise ContractError(f"Full condition/checkpoint mismatch: {key}")
            else:
                if receipt.get("condition_mode") != MODE_OT or receipt.get("tracer_only_conditions_sha256") != conditions["OT"]["sha256"] or receipt.get("empty_patient_sha256") != conditions["OT"]["empty_patient_sha256"]:
                    raise ContractError(f"OT runtime/checkpoint mismatch: {key}")
            result[key] = {"path": item["path"], "sha256": item["sha256"], "receipt": item["receipt"], "epoch": 165, "fold": fold}
    return result


def overlaps(a: Path, b: Path) -> bool:
    a, b = a.resolve(strict=False), b.resolve(strict=False)
    return a == b or a in b.parents or b in a.parents


def verify_output(output_root: Path, config: dict, selected: dict[int, list[dict]], models=("Full", "OT"), folds=(1, 2)) -> dict:
    root = output_root.resolve(strict=False)
    protected = []
    for item in config["generator_checkpoints"].values():
        protected += [Path(item["path"]), Path(item["receipt"]), Path(item["path"]).parents[2] / "oof"]
    protected += [Path(x["path"]) for x in config["conditions_identity"].values()]
    protected += [Path(load_json(FULL_CACHE_RECEIPT)["cache_dir"]), ROOT, Path.home(), Path("/")]
    # Root always overlaps '/', so only reject a root equal to broad roots; for
    # all asset roots, reject equality or either ancestor relationship.
    if root in {Path("/"), ROOT.resolve(), Path.home().resolve()}:
        raise ContractError(f"unsafe broad output root: {root}")
    for p in protected[:-3]:
        if overlaps(root, p):
            raise ContractError(f"output overlaps protected asset: {p}")
    planned, counts = [], {}
    for model in models:
        for fold in folds:
            run_dir = root / f"outer_fold{fold}" / model.lower()
            if run_dir.exists():
                raise ContractError(f"run output already exists; refusing overwrite: {run_dir}")
            outputs = [run_dir / tracer / f"generated_{tracer}_{r['ptid']}.nii.gz" for r in selected[fold] for tracer in TRACERS]
            if any(p.exists() for p in outputs):
                raise ContractError(f"planned prediction already exists: {next(p for p in outputs if p.exists())}")
            counts[f"{model}_fold{fold}"] = {"subjects": len(selected[fold]), "volumes": len(outputs), "run_dir": str(run_dir)}
            planned.extend(outputs)
    if len(planned) != len(set(planned)):
        raise ContractError("duplicate planned output path")
    return {"root": str(root), "root_created": root.exists(), "counts": counts, "planned_volumes": len(planned), "layout": "outer_fold{f}/{model}/{tracer}/generated_{tracer}_{PTID}.nii.gz"}


def dependencies() -> dict:
    result = {"python": platform.python_version()}
    for name in ("torch", "monai", "nibabel", "numpy"):
        spec = importlib.util.find_spec(name)
        if spec is None:
            raise ContractError(f"missing runtime dependency: {name}")
        module = importlib.import_module(name)
        result[name] = getattr(module, "__version__", "unknown")
    import torch
    result.update(cuda_available=bool(torch.cuda.is_available()), cuda_version=torch.version.cuda)
    # Import entrypoints, but deliberately do not instantiate/load a model.
    full = importlib.import_module("experiments.original_author_reproduction.run")
    ot = importlib.import_module("experiments.tracer_only_control.run")
    for module, names in ((full, ("new_model", "build_transform", "context_from_batch")), (ot, ("_load_context_asset",))):
        if any(not hasattr(module, n) for n in names):
            raise ContractError("required preserved inference function is missing")
    result["entrypoints_importable"] = True
    result["model_instantiated"] = False
    return result


def preflight(config_path: Path, receipt_path: Path, manifests: list[Path], output_root: Path,
              models=("Full", "OT"), folds=(1, 2)) -> tuple[dict, dict, dict[int, list[dict]]]:
    receipt = load_json(receipt_path)
    config_meta = receipt["outputs"][config_path.name]
    check_file(config_path, config_meta["sha256"], config_meta["bytes"])
    config = load_json(config_path)
    if config.get("epoch") != 165 or config.get("outer_train_rule") != "generator_fold != outer_fold":
        raise ContractError("4B frozen execution rule changed")
    rows, manifest_ids = read_manifests(manifests, receipt, config)
    selected = validate_rows(rows, config)
    _, cohort, cache = verify_full_runtime(selected)
    condition_ids = verify_conditions(config, cohort)
    checkpoint_ids = verify_checkpoints(config, condition_ids)
    output = verify_output(output_root, config, selected, models=models, folds=folds)
    deps = dependencies()
    result = {
        "status": "PASS_CHECK_ONLY",
        "stage": "4C-1",
        "mode": "check-only",
        "epoch": 165,
        "config": check_file(config_path, config_meta["sha256"], config_meta["bytes"]),
        "manifests": manifest_ids,
        "subject_union": len({r["ptid"] for rs in selected.values() for r in rs}),
        "selected_by_outer_fold": {str(f): {"generator_fold": 3 - f, "subjects": len(rs), "volumes_per_model": 2 * len(rs)} for f, rs in selected.items()},
        "checkpoints": checkpoint_ids,
        "conditions": condition_ids,
        "persistent_cache": cache,
        "output_plan": output,
        "dependencies": deps,
        "real_inference_run": False,
        "model_loaded": False,
        "forward_run": False,
        "pet_written": False,
        "ready_for_gpu_inference_on_this_host": bool(deps["cuda_available"]),
    }
    return result, config, selected


def safety_tests(config: dict, selected: dict[int, list[dict]], output_root: Path) -> list[dict]:
    tests = []
    def expect(name, fn):
        try:
            fn()
        except ContractError as exc:
            tests.append({"name": name, "status": "PASS_REJECTED", "reason": str(exc)})
        else:
            tests.append({"name": name, "status": "FAIL_ACCEPTED"})

    pilot = select_pilot(selected)
    # These call the same selection validator used by real execution.  Fold-1
    # train rows belong to generator fold 2, so requesting fold 2 is invalid.
    expect("wrong_generator_fold", lambda: validate_execution_selection(pilot[1], 2, PILOT_SUBJECTS_PER_FOLD))
    bad_config = copy.deepcopy(config)
    bad_config["generator_checkpoints"]["Full_fold1"]["sha256"] = "0" * 64
    expect("wrong_checkpoint_sha", lambda: verify_checkpoints(bad_config, {"Full": {"sha256": config["conditions_identity"]["Full"]["sha256"]}, "OT": {"sha256": config["conditions_identity"]["OT"]["sha256"], "empty_patient_sha256": "unused"}}))
    bad_config = copy.deepcopy(config)
    bad_config["conditions_identity"]["OT"] = copy.deepcopy(config["conditions_identity"]["Full"])
    expect("full_ot_condition_mismatch", lambda: verify_conditions(bad_config, load_json(Path(load_json(FULL_CONFIG)["report"]) / "cohort.json")))
    oof = Path(config["generator_checkpoints"]["Full_fold1"]["path"]).parents[2] / "oof"
    expect("output_points_to_oof", lambda: verify_output(oof, config, selected))
    outer_test = copy.deepcopy(selected[2][0])  # generator_fold=1 => outer-test for fold 1
    outer_test["outer_fold"] = "1"
    outer_test["outer_role"] = "outer_test"
    expect("outer_test_selected", lambda: validate_execution_selection([outer_test], 1, 1))
    bad_cross_oof = copy.deepcopy(selected[1][0])
    bad_cross_oof["full_fdg_existing_oof_usage"] = "ALLOWED_OUTER_TEST"
    expect("cross_oof_allowed_on_train_row", lambda: validate_execution_selection([bad_cross_oof], 1, 1))
    with tempfile.TemporaryDirectory(prefix="directpp_4c1_") as tmp:
        root = Path(tmp) / "out"
        (root / "outer_fold1" / "full").mkdir(parents=True)
        expect("existing_output_refuses_overwrite", lambda: verify_output(root, config, selected, models=("Full",), folds=(1,)))
    bad_config = copy.deepcopy(config)
    bad_config["conditions_identity"]["OT"]["path"] += ".missing"
    expect("missing_ot_runtime", lambda: verify_conditions(bad_config, load_json(Path(load_json(FULL_CONFIG)["report"]) / "cohort.json")))
    return tests


def command_check(args) -> None:
    result, config, selected = preflight(
        args.config.resolve(), args.receipt.resolve(), [p.resolve() for p in args.manifests],
        args.output_root,
    )
    result["safety_tests"] = safety_tests(config, selected, args.output_root)
    result["safety_tests_status"] = "PASS" if all(x["status"] == "PASS_REJECTED" for x in result["safety_tests"]) else "FAIL"
    if result["safety_tests_status"] != "PASS":
        raise ContractError("one or more fail-closed safety tests failed")
    atomic_json(args.results.resolve(), result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def command_dry_run(args) -> None:
    """Enumerate the complete formal plan without loading a generator or writing PET."""
    from monai.data.utils import pickle_hashing

    output_root = args.output_root.resolve()
    if output_root == PILOT_OUTPUT_ROOT.resolve() or overlaps(output_root, PILOT_OUTPUT_ROOT):
        raise ContractError("formal output root overlaps pilot output")
    result, config, selected = preflight(
        args.config.resolve(), args.receipt.resolve(), [p.resolve() for p in args.manifests], output_root,
        models=("Full", "OT"), folds=(1, 2),
    )
    for fold in (1, 2):
        validate_execution_selection(selected[fold], fold, FULL_SUBJECTS[fold])
        if len(selected[fold]) * len(TRACERS) != FULL_VOLUMES[fold]:
            raise ContractError(f"full dry-run count mismatch for fold {fold}")
    union = {r["ptid"] for rows in selected.values() for r in rows}
    if len(union) != 905 or set(r["ptid"] for r in selected[1]) & set(r["ptid"] for r in selected[2]):
        raise ContractError("full dry-run unique subject union is not the frozen 905")

    _, cohort, cache_info = verify_full_runtime(selected)
    by_ptid = {r["name"]: r for r in cohort}
    cache_dir = Path(cache_info["cache_dir"])
    plans, missing_cache = [], []
    for model in ("Full", "OT"):
        condition = config["conditions_identity"][model]
        for fold in (1, 2):
            checkpoint = config["generator_checkpoints"][f"{model}_fold{fold}"]
            for row in selected[fold]:
                source = by_ptid[row["ptid"]]
                cache_key = pickle_hashing(source).decode() + ".pt"
                cache_path = cache_dir / cache_key
                if not cache_path.is_file():
                    missing_cache.append(str(cache_path))
                for tracer in TRACERS:
                    prediction = output_root / f"outer_fold{fold}" / model.lower() / tracer / f"generated_{tracer}_{row['ptid']}.nii.gz"
                    plans.append({
                        "model": model, "outer_fold": fold, "generator_fold": int(row["generator_fold"]),
                        "ptid": row["ptid"], "diagnosis": row["diagnosis"], "tracer": tracer,
                        "checkpoint_sha256": checkpoint["sha256"], "condition_sha256": condition["sha256"],
                        "cache_key": cache_key, "cache_path": str(cache_path),
                        "e1_cache_path": row["e1_cache_path"], "e1_cache_sha256": row["e1_cache_sha256"],
                        "prediction": str(prediction),
                    })
    if missing_cache:
        raise ContractError(f"full dry-run missing cache entry: {missing_cache[0]}")
    paths = [p["prediction"] for p in plans]
    if len(plans) != 3620 or len(set(paths)) != 3620:
        raise ContractError("full dry-run does not contain 3,620 unique prediction paths")
    if any(Path(p).exists() for p in paths):
        raise ContractError("formal prediction path is already occupied")
    safety = safety_tests(config, selected, output_root)
    if not all(x["status"] == "PASS_REJECTED" for x in safety):
        raise ContractError("dry-run safety rejection test failed")
    canonical_plan = json.dumps(plans, sort_keys=True, separators=(",", ":")).encode()
    receipt = {
        "stage": "4C-3_readiness", "status": "PASS_DRY_RUN",
        "runner": str(Path(__file__).resolve()), "runner_sha256": sha256(Path(__file__).resolve()),
        "formal_output_protocol": {
            "root": str(output_root),
            "layout": "outer_fold{f}/{model}/{tracer}/generated_{tracer}_{PTID}.nii.gz",
            "source_of_truth_after_execution": "per-run prediction_manifest.json and complete.json; downstream classification must parse receipts and must not synthesize paths",
            "pilot_root": str(PILOT_OUTPUT_ROOT), "pilot_isolated": True,
            "frozen_4b_manifests_modified": False,
        },
        "counts": {
            "Full_G1": {"subjects": 457, "volumes": 914},
            "OT_G1": {"subjects": 457, "volumes": 914},
            "Full_G2": {"subjects": 448, "volumes": 896},
            "OT_G2": {"subjects": 448, "volumes": 896},
            "unique_subjects": 905, "prediction_paths": 3620,
        },
        "plan_sha256": hashlib.sha256(canonical_plan).hexdigest(),
        "all_prediction_paths_unique": True,
        "formal_run_directories_unoccupied": True,
        "checkpoint_identity": result["checkpoints"], "condition_identity": result["conditions"],
        "cache": {**cache_info, "selected_cache_keys": 905, "all_selected_cache_keys_exist": True},
        "selection_rule": "frozen outer_train only; generator_fold != outer_fold; use G_f",
        "group_dry_run": {key: {**value, "status": "PASS"} for key, value in result["output_plan"]["counts"].items()},
        "rejection_tests": safety,
        "rejection_tests_status": "PASS",
        "models_loaded": False, "generator_forward_run": False, "pet_written": False,
        "pilot_outputs_modified": False, "full_inference_run": False, "classification_training_run": False,
    }
    atomic_json(args.results.resolve(), receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def cache_tree_identity(cache_dir: Path) -> list[tuple[str, int, int]]:
    return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in cache_dir.glob("*.pt"))


def tensor_sha(tensor) -> str:
    return hashlib.sha256(tensor.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


def command_controlled_inference(args, mode: str) -> None:
    """Single protected implementation shared by pilot and formal inference."""
    if mode not in ("pilot", "formal"):
        raise ContractError("unknown controlled inference mode")
    expected_ack = "RUN_STAGE_4C2_PILOT_8_VOLUMES" if mode == "pilot" else "RUN_STAGE_4C4_FULL_TRAIN_SIDE_PET"
    if args.acknowledge != expected_ack:
        raise ContractError(f"{mode} inference authorization missing or incorrect")
    required_root = PILOT_OUTPUT_ROOT if mode == "pilot" else FORMAL_OUTPUT_ROOT
    if args.output_root.resolve() != required_root.resolve():
        raise ContractError(f"{mode} output root differs from frozen derived-output contract")
    result, config, selected = preflight(
        args.config.resolve(), args.receipt.resolve(), [p.resolve() for p in args.manifests], args.output_root,
        models=(args.model,), folds=(args.outer_fold,),
    )
    execution_selected = select_pilot(selected) if mode == "pilot" else selected
    rows = execution_selected[args.outer_fold]
    expected_subjects = PILOT_SUBJECTS_PER_FOLD if mode == "pilot" else FULL_SUBJECTS[args.outer_fold]
    expected_volumes = PILOT_VOLUMES_PER_RUN if mode == "pilot" else FULL_VOLUMES[args.outer_fold]
    validate_execution_selection(rows, args.outer_fold, expected_subjects)
    if len(rows) * len(TRACERS) != expected_volumes:
        raise ContractError(f"{mode} volume count invariant failed")
    output_check = verify_output(args.output_root, config, execution_selected, models=(args.model,), folds=(args.outer_fold,))
    if output_check["planned_volumes"] != expected_volumes:
        raise ContractError(f"{mode} output plan count mismatch")
    if not result["dependencies"]["cuda_available"]:
        raise ContractError(f"CUDA is required for {mode} inference")

    import nibabel as nib
    import numpy as np
    import torch
    from monai.data import DataLoader, PersistentDataset
    from monai.data.utils import pickle_hashing
    from experiments.original_author_reproduction import run as full

    fold, model_name = args.outer_fold, args.model
    item = config["generator_checkpoints"][f"{model_name}_fold{fold}"]
    _, cohort, cache_info = verify_full_runtime(selected)
    by_ptid = {r["name"]: r for r in cohort}
    data = [by_ptid[r["ptid"]] for r in rows]
    cache_dir = Path(cache_info["cache_dir"])
    cache_before = cache_tree_identity(cache_dir)
    cache_keys = {r["name"]: pickle_hashing(r).decode() + ".pt" for r in data}
    missing = [key for key in cache_keys.values() if not (cache_dir / key).is_file()]
    if missing:
        raise ContractError(f"{mode} persistent-cache key missing: {missing[0]}")
    cache_sha_before = {ptid: sha256(cache_dir / key) for ptid, key in cache_keys.items()}
    full_conditions = torch.load(config["conditions_identity"]["Full"]["path"], map_location="cpu", weights_only=False)
    ot_asset = torch.load(config["conditions_identity"]["OT"]["path"], map_location="cpu", weights_only=False)
    transform = full.build_transform(full_conditions)
    loader = DataLoader(PersistentDataset(data, transform, cache_dir=cache_dir), batch_size=1, shuffle=False, num_workers=0)

    run_dir = args.output_root.resolve() / f"outer_fold{fold}" / model_name.lower()
    run_dir.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    records = []
    try:
        state = torch.load(item["path"], map_location="cpu", weights_only=False)
        generator = full.new_model().cuda().eval()
        generator.load_state_dict(state["model"])
        torch.cuda.reset_peak_memory_stats()
        ptid_to_index = {p: i for i, p in enumerate(full_conditions["ptids"])}
        with torch.no_grad():
            for batch in loader:
                ptid = batch["name"][0]
                row = next(r for r in rows if r["ptid"] == ptid)
                image = batch["mri"].cuda()
                mri_array = image.detach().cpu().numpy().squeeze()
                with np.load(row["e1_cache_path"], allow_pickle=False) as e1_npz:
                    e1 = np.asarray(e1_npz["mri"])
                if (mri_array.shape != e1.shape or mri_array.dtype != np.float32 or e1.dtype != np.float32
                        or not np.isfinite(mri_array).all() or not np.isfinite(e1).all()):
                    raise ContractError(f"pilot MRI identity/shape failed: {ptid}")
                mri_max_abs = float(np.max(np.abs(mri_array - e1)))
                if mri_max_abs > 2e-6:
                    raise ContractError(f"pilot MRI/E1 spatial gate failed: {ptid}, {mri_max_abs}")
                timestep = torch.tensor([0], device="cuda", dtype=torch.long)
                for ti, tracer in enumerate(TRACERS):
                    if model_name == "Full":
                        context = batch[f"{tracer}_index"].cuda()
                        expected = torch.stack((full_conditions["patient"][ptid_to_index[ptid]], full_conditions["tracer"][ti])).unsqueeze(0)
                        condition_sha = config["conditions_identity"]["Full"]["sha256"]
                    else:
                        cached = batch[f"{tracer}_index"]
                        if tuple(cached.shape[-2:]) != (2, 512):
                            raise ContractError("cached Full context shape mismatch")
                        expected = torch.stack((ot_asset["empty_patient"][0], ot_asset["tracer"][ti])).unsqueeze(0)
                        context = expected.cuda()
                        condition_sha = config["conditions_identity"]["OT"]["sha256"]
                    if not torch.equal(context.detach().cpu(), expected):
                        raise ContractError(f"runtime context mismatch: {model_name}, {ptid}, {tracer}")
                    velocity = generator(x=image, timesteps=timestep, context=context)
                    pred = torch.clamp(image + velocity, 0, 1).float()
                    array = pred.squeeze().detach().cpu().numpy()
                    # All gates precede any file creation for this prediction.
                    if array.shape != (160, 192, 160) or array.dtype != np.float32:
                        raise ContractError(f"prediction shape/dtype failed: {ptid}, {tracer}")
                    if not np.isfinite(array).all() or float(array.min()) < 0.0 or float(array.max()) > 1.0:
                        raise ContractError(f"prediction finite/range failed: {ptid}, {tracer}")
                    if float(array.max()) == float(array.min()):
                        raise ContractError(f"constant prediction rejected: {ptid}, {tracer}")
                    target_dir = run_dir / tracer
                    target_dir.mkdir(exist_ok=True)
                    path = target_dir / f"generated_{tracer}_{ptid}.nii.gz"
                    if path.exists():
                        raise ContractError(f"refusing overwrite: {path}")
                    tmp = target_dir / f".{path.name}.tmp.nii.gz"
                    nib.save(nib.Nifti1Image(array, np.eye(4)), tmp)
                    os.replace(tmp, path)
                    records.append({
                        "ptid": ptid, "diagnosis": row["diagnosis"], "execution_mode": mode, "outer_fold": fold,
                        "generator_fold": int(row["generator_fold"]), "model": model_name, "tracer": tracer,
                        "checkpoint_sha256": item["sha256"], "condition_sha256": condition_sha,
                        "context_sha256": tensor_sha(expected), "runtime_config_sha256": result["config"]["sha256"],
                        "cache_namespace": cache_info["cache_namespace"], "cache_key": cache_keys[ptid],
                        "cache_path": str(cache_dir / cache_keys[ptid]), "cache_hit_verified": True,
                        "cache_sha256_before": cache_sha_before[ptid],
                        "source_mri_sha256": row["source_mri_sha256"],
                        "e1_cache_sha256": row["e1_cache_sha256"], "mri_array_sha256": hashlib.sha256(mri_array.tobytes()).hexdigest(),
                        "mri_e1_max_abs_error": mri_max_abs, "formula": "clamp(MRI + model_velocity(t=0, context), 0, 1)",
                        "shape": "160x192x160", "dtype": str(array.dtype), "finite": True,
                        "min": float(array.min()), "max": float(array.max()), "std": float(array.std()),
                        "prediction": str(path), "prediction_sha256": sha256(path), "bytes": path.stat().st_size,
                    })
        if len(records) != expected_volumes:
            raise ContractError(f"{mode} generated {len(records)} records, expected exactly {expected_volumes}")
        cache_after = cache_tree_identity(cache_dir)
        if cache_after != cache_before:
            raise ContractError(f"PersistentDataset cache tree changed during {mode} inference")
        cache_sha_after = {ptid: sha256(cache_dir / key) for ptid, key in cache_keys.items()}
        if cache_sha_after != cache_sha_before:
            raise ContractError("PersistentDataset cache content SHA changed during inference")
        for record in records:
            record["cache_sha256_after"] = cache_sha_after[record["ptid"]]
        elapsed = time.monotonic() - started
        group = {
            "status": "COMPLETE", "mode": mode, "model": model_name, "outer_fold": fold, "epoch": 165,
            "subjects": [r["ptid"] for r in rows], "diagnoses": [r["diagnosis"] for r in rows],
            "records": len(records), "runtime_seconds": elapsed,
            "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated()),
            "cache_files_before": len(cache_before), "cache_files_after": len(cache_after),
            "cache_tree_unchanged": True, "selected_cache_sha_unchanged": True,
            "checkpoint_sha256": item["sha256"],
            "condition_sha256": config["conditions_identity"][model_name]["sha256"],
        }
        atomic_json(run_dir / "prediction_manifest.json", {"records": records})
        group["prediction_manifest_sha256"] = sha256(run_dir / "prediction_manifest.json")
        atomic_json(run_dir / "complete.json", group)
        print(json.dumps(group, ensure_ascii=False, indent=2), flush=True)
    except Exception as exc:
        # Preserve partial files and an explicit non-COMPLETE terminal marker.
        failure = {"status": "FAILED", "model": model_name, "outer_fold": fold, "error": repr(exc),
                   "traceback": traceback.format_exc(), "records_written": len(records),
                   "runtime_seconds": time.monotonic() - started}
        failure_path = run_dir / "failure.json"
        if not failure_path.exists():
            atomic_json(failure_path, failure)
        raise


def command_pilot(args) -> None:
    command_controlled_inference(args, "pilot")


def command_infer(args) -> None:
    command_controlled_inference(args, "formal")


def command_finalize_pilot(args) -> None:
    """Read-only QC of the four pilot runs and emit the required CSV/receipt."""
    import nibabel as nib
    import numpy as np
    import torch

    output_root = args.output_root.resolve()
    out_csv, out_receipt = args.output_csv.resolve(), args.output_receipt.resolve()
    if out_csv.exists() or out_receipt.exists():
        raise ContractError("refusing to overwrite pilot finalization outputs")
    config = load_json(args.config.resolve())
    full_conditions = torch.load(config["conditions_identity"]["Full"]["path"], map_location="cpu", weights_only=False)
    ot = torch.load(config["conditions_identity"]["OT"]["path"], map_location="cpu", weights_only=False)
    ptid_index = {p: i for i, p in enumerate(full_conditions["ptids"])}
    records, groups = [], []
    for fold in (1, 2):
        for model in ("Full", "OT"):
            run_dir = output_root / f"outer_fold{fold}" / model.lower()
            if (run_dir / "failure.json").exists():
                raise ContractError(f"pilot failure marker exists: {run_dir}")
            complete_path, manifest_path = run_dir / "complete.json", run_dir / "prediction_manifest.json"
            complete = load_json(complete_path)
            if complete.get("status") != "COMPLETE" or complete.get("records") != 8:
                raise ContractError(f"incomplete pilot group: {run_dir}")
            if complete.get("prediction_manifest_sha256") != sha256(manifest_path):
                raise ContractError(f"pilot group manifest SHA mismatch: {run_dir}")
            group_records = load_json(manifest_path).get("records", [])
            if len(group_records) != 8:
                raise ContractError(f"pilot group does not contain eight records: {run_dir}")
            expected_checkpoint = config["generator_checkpoints"][f"{model}_fold{fold}"]["sha256"]
            expected_condition = config["conditions_identity"][model]["sha256"]
            for row in group_records:
                if (row["model"], int(row["outer_fold"]), int(row["generator_fold"])) != (model, fold, 3 - fold):
                    raise ContractError("pilot identity/fold mismatch")
                if row["checkpoint_sha256"] != expected_checkpoint or row["condition_sha256"] != expected_condition:
                    raise ContractError("pilot checkpoint/condition mismatch")
                ti = TRACERS.index(row["tracer"])
                if model == "Full":
                    expected_context = torch.stack((full_conditions["patient"][ptid_index[row["ptid"]]], full_conditions["tracer"][ti])).unsqueeze(0)
                else:
                    expected_context = torch.stack((ot["empty_patient"][0], ot["tracer"][ti])).unsqueeze(0)
                if row["context_sha256"] != tensor_sha(expected_context):
                    raise ContractError("pilot context SHA mismatch")
                path = Path(row["prediction"])
                if not path.is_file() or sha256(path) != row["prediction_sha256"] or path.stat().st_size != int(row["bytes"]):
                    raise ContractError(f"pilot prediction file identity mismatch: {path}")
                image = np.asarray(nib.load(path).dataobj)
                if not np.array_equal(nib.load(path).affine, np.eye(4)):
                    raise ContractError(f"pilot prediction affine is not preserved identity: {path}")
                if image.shape != (160, 192, 160) or image.dtype != np.float32 or not np.isfinite(image).all():
                    raise ContractError(f"pilot prediction array QC failed: {path}")
                if float(image.min()) < 0 or float(image.max()) > 1 or float(image.max()) == float(image.min()):
                    raise ContractError(f"pilot prediction range/constant QC failed: {path}")
                if not Path(row["cache_path"]).is_file() or not row.get("cache_hit_verified"):
                    raise ContractError("pilot cache hit evidence failed")
                records.append(row)
            groups.append({**complete, "complete_sha256": sha256(complete_path)})
    if len(records) != 32 or len({r["prediction"] for r in records}) != 32:
        raise ContractError("pilot final count is not exactly 32 unique predictions")
    for fold in (1, 2):
        full_rows = {(r["ptid"], r["tracer"]): r for r in records if r["model"] == "Full" and int(r["outer_fold"]) == fold}
        ot_rows = {(r["ptid"], r["tracer"]): r for r in records if r["model"] == "OT" and int(r["outer_fold"]) == fold}
        if full_rows.keys() != ot_rows.keys() or len(full_rows) != PILOT_VOLUMES_PER_RUN:
            raise ContractError(f"Full/OT pilot subject-tracer pairing differs in fold {fold}")
        for key in full_rows:
            a, b = full_rows[key], ot_rows[key]
            if (a["mri_array_sha256"], a["cache_key"], a["source_mri_sha256"], a["e1_cache_sha256"]) != (b["mri_array_sha256"], b["cache_key"], b["source_mri_sha256"], b["e1_cache_sha256"]):
                raise ContractError(f"Full/OT MRI/cache identity differs: fold {fold}, {key}")
    actual_nifti = list(output_root.glob("outer_fold*/*/*/*.nii.gz"))
    if len(actual_nifti) != 32:
        raise ContractError(f"pilot output tree has {len(actual_nifti)} NIfTI files, expected 32")
    for fold in (1, 2):
        for ptid in sorted({r["ptid"] for r in records if int(r["outer_fold"]) == fold}):
            pair = [r for r in records if int(r["outer_fold"]) == fold and r["ptid"] == ptid]
            if {r["model"] for r in pair} != {"Full", "OT"} or len(pair) != 4:
                raise ContractError("Full/OT pilot subject/tracer pairing failed")
            if len({r["mri_array_sha256"] for r in pair}) != 1 or len({r["cache_key"] for r in pair}) != 1:
                raise ContractError("Full/OT did not use identical MRI/cache key")
            if {r["tracer"] for r in pair} != set(TRACERS):
                raise ContractError("Full/OT tracer pairing failed")
    fields = list(records[0])
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    tmp_csv = out_csv.with_suffix(".csv.tmp")
    with tmp_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(records)
    os.replace(tmp_csv, out_csv)
    cache_dir = Path(records[0]["cache_path"]).parent
    cache_files = list(cache_dir.glob("*.pt"))
    receipt = {
        "stage": "4C-2", "status": "PASS", "pilot_groups_complete": 4,
        "prediction_records": 32, "unique_prediction_files": 32,
        "identity_numeric_qc_pass": True, "full_ot_same_subject_mri_tracer_pass": True,
        "context_checkpoint_condition_pass": True,
        "spatial_threshold": 2e-6,
        "max_mri_e1_abs_error": max(float(r["mri_e1_max_abs_error"]) for r in records),
        "prediction_min": min(float(r["min"]) for r in records),
        "prediction_max": max(float(r["max"]) for r in records),
        "prediction_min_std": min(float(r["std"]) for r in records),
        "prediction_total_bytes": sum(int(r["bytes"]) for r in records),
        "cache_dir": str(cache_dir), "cache_files_after_all_runs": len(cache_files),
        "all_group_cache_tree_unchanged": all(g.get("cache_tree_unchanged") for g in groups),
        "groups": groups, "pilot_manifest": str(out_csv), "pilot_manifest_sha256": sha256(out_csv),
        "pilot_config": str(args.pilot_config.resolve()), "pilot_config_sha256": sha256(args.pilot_config.resolve()),
        "runner": str(Path(__file__).resolve()), "runner_sha256": sha256(Path(__file__).resolve()),
        "full_4b_manifests_modified": False, "full_queue_inference_run": False,
        "classification_training_run": False,
    }
    atomic_json(out_receipt, receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, default=DEFAULT_DIR / "04b_execution_config_draft.json")
    common.add_argument("--receipt", type=Path, default=DEFAULT_DIR / "04b_manifest_receipt.json")
    common.add_argument("--manifests", type=Path, nargs=3, default=[DEFAULT_DIR / "04b_manifest_ad_cn.csv", DEFAULT_DIR / "04b_manifest_mci_cn.csv", DEFAULT_DIR / "04b_manifest_lmci_emci.csv"])
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check-only", parents=[common])
    c.add_argument("--output-root", type=Path, default=FORMAL_OUTPUT_ROOT)
    c.add_argument("--results", type=Path, default=DEFAULT_DIR / "04c1_check_only_results.json")
    c.set_defaults(func=command_check)
    pilot = sub.add_parser("pilot", parents=[common])
    pilot.add_argument("--output-root", type=Path, default=PILOT_OUTPUT_ROOT)
    pilot.add_argument("--model", choices=("Full", "OT"), required=True)
    pilot.add_argument("--outer-fold", type=int, choices=(1, 2), required=True)
    pilot.add_argument("--acknowledge", required=True)
    pilot.set_defaults(func=command_pilot)
    dry = sub.add_parser("dry-run", parents=[common])
    dry.add_argument("--output-root", type=Path, default=FORMAL_OUTPUT_ROOT)
    dry.add_argument("--results", type=Path, default=DEFAULT_DIR / "04c3_dry_run_receipt.json")
    dry.set_defaults(func=command_dry_run)
    finalize = sub.add_parser("finalize-pilot")
    finalize.add_argument("--config", type=Path, default=DEFAULT_DIR / "04b_execution_config_draft.json")
    finalize.add_argument("--pilot-config", type=Path, default=DEFAULT_DIR / "04c2_pilot_config.json")
    finalize.add_argument("--output-root", type=Path, default=Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c2_pilot/20261028/epoch165"))
    finalize.add_argument("--output-csv", type=Path, default=DEFAULT_DIR / "04c2_pilot_prediction_manifest.csv")
    finalize.add_argument("--output-receipt", type=Path, default=DEFAULT_DIR / "04c2_pilot_receipt.json")
    finalize.set_defaults(func=command_finalize_pilot)
    i = sub.add_parser("infer", parents=[common])
    i.add_argument("--output-root", type=Path, default=FORMAL_OUTPUT_ROOT)
    i.add_argument("--model", choices=("Full", "OT"), required=True)
    i.add_argument("--outer-fold", type=int, choices=(1, 2), required=True)
    i.add_argument("--acknowledge", required=True)
    i.set_defaults(func=command_infer)
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    try:
        args.func(args)
    except ContractError as exc:
        raise SystemExit(f"BLOCKED: {exc}")
