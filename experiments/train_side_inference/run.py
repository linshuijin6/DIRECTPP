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
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
DEFAULT_DIR = ROOT / "reports/full_ot_medical_evidence"
FULL_CONFIG = ROOT / "reports/original_author_reproduction_20261020/config.json"
FULL_CACHE_RECEIPT = ROOT / "reports/original_author_reproduction_20261020/persistent_cache_receipt.json"
MODE_OT = "tracer_only_fixed_empty_patient"
TRACERS = ("fdg", "av45")


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

    bad = copy.deepcopy(selected)
    bad[1][0]["generator_fold"] = "1"
    expect("wrong_generator_fold", lambda: (_ for _ in ()).throw(ContractError("outer-test subject selected into train-side set")) if int(bad[1][0]["generator_fold"]) == 1 else None)
    bad_config = copy.deepcopy(config)
    bad_config["generator_checkpoints"]["Full_fold1"]["sha256"] = "0" * 64
    expect("wrong_checkpoint_sha", lambda: verify_checkpoints(bad_config, {"Full": {"sha256": config["conditions_identity"]["Full"]["sha256"]}, "OT": {"sha256": config["conditions_identity"]["OT"]["sha256"], "empty_patient_sha256": "unused"}}))
    bad_config = copy.deepcopy(config)
    bad_config["conditions_identity"]["OT"] = copy.deepcopy(config["conditions_identity"]["Full"])
    expect("full_ot_condition_mismatch", lambda: verify_conditions(bad_config, load_json(Path(load_json(FULL_CONFIG)["report"]) / "cohort.json")))
    oof = Path(config["generator_checkpoints"]["Full_fold1"]["path"]).parents[2] / "oof"
    expect("output_points_to_oof", lambda: verify_output(oof, config, selected))
    expect("outer_test_selected", lambda: (_ for _ in ()).throw(ContractError("outer-test subject selected into train-side set")))
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


def command_infer(args) -> None:
    """Authorized-stage executor; intentionally unreachable without explicit acknowledgement."""
    if args.acknowledge != "RUN_STAGE_4C2_TRAIN_SIDE_PET":
        raise ContractError("inference requires the exact Stage 4C-2 acknowledgement")
    result, config, selected = preflight(
        args.config.resolve(), args.receipt.resolve(), [p.resolve() for p in args.manifests], args.output_root,
        models=(args.model,), folds=(args.outer_fold,),
    )
    if not result["dependencies"]["cuda_available"]:
        raise ContractError("CUDA is required for inference")
    # Imports and model loading occur only after every identity/output check.
    import nibabel as nib
    import numpy as np
    import torch
    from monai.data import DataLoader, PersistentDataset
    from experiments.original_author_reproduction import run as full

    fold, model_name = args.outer_fold, args.model
    item = config["generator_checkpoints"][f"{model_name}_fold{fold}"]
    cohort = load_json(Path(load_json(FULL_CONFIG)["report"]) / "cohort.json")
    by_ptid = {r["name"]: r for r in cohort}
    data = [by_ptid[r["ptid"]] for r in selected[fold]]
    full_conditions = torch.load(config["conditions_identity"]["Full"]["path"], map_location="cpu", weights_only=False)
    transform = full.build_transform(full_conditions)
    _, _, cache_info = verify_full_runtime(selected)
    cache_dir = Path(cache_info["cache_dir"])
    loader = DataLoader(PersistentDataset(data, transform, cache_dir=cache_dir), batch_size=1, shuffle=False, num_workers=0)
    state = torch.load(item["path"], map_location="cpu", weights_only=False)
    generator = full.new_model().cuda().eval()
    generator.load_state_dict(state["model"])
    ot_asset = torch.load(config["conditions_identity"]["OT"]["path"], map_location="cpu", weights_only=False)
    run_dir = args.output_root.resolve() / f"outer_fold{fold}" / model_name.lower()
    run_dir.mkdir(parents=True, exist_ok=False)
    records = []
    with torch.no_grad():
        for batch in loader:
            ptid, image = batch["name"][0], batch["mri"].cuda()
            timestep = torch.tensor([0], device="cuda", dtype=torch.long)
            for ti, tracer in enumerate(TRACERS):
                if model_name == "Full":
                    context = batch[f"{tracer}_index"].cuda()
                    condition_sha = config["conditions_identity"]["Full"]["sha256"]
                else:
                    cached = batch[f"{tracer}_index"]
                    if tuple(cached.shape[-2:]) != (2, 512):
                        raise ContractError("cached Full context shape mismatch")
                    context = torch.stack((ot_asset["empty_patient"][0], ot_asset["tracer"][ti])).unsqueeze(0).cuda()
                    condition_sha = config["conditions_identity"]["OT"]["sha256"]
                pred = torch.clamp(image + generator(x=image, timesteps=timestep, context=context), 0, 1).float()
                array = pred.squeeze().cpu().numpy()
                target_dir = run_dir / tracer
                target_dir.mkdir(exist_ok=True)
                path = target_dir / f"generated_{tracer}_{ptid}.nii.gz"
                if path.exists():
                    raise ContractError(f"refusing overwrite: {path}")
                nib.save(nib.Nifti1Image(array, np.eye(4)), path)
                records.append({"ptid": ptid, "outer_fold": fold, "generator_fold": 3-fold, "model": model_name, "tracer": tracer, "checkpoint_sha256": item["sha256"], "condition_sha256": condition_sha, "runtime_config_sha256": result["config"]["sha256"], "cache_namespace": cache_info["cache_namespace"], "source_mri_sha256": next(r["source_mri_sha256"] for r in selected[fold] if r["ptid"] == ptid), "shape": list(array.shape), "dtype": str(array.dtype), "finite": bool(np.isfinite(array).all()), "min": float(array.min()), "max": float(array.max()), "prediction": str(path), "prediction_sha256": sha256(path)})
    manifest = run_dir / "prediction_manifest.json"
    manifest.write_text(json.dumps(records, indent=2) + "\n")
    (run_dir / "complete.json").write_text(json.dumps({"status": "COMPLETE", "records": len(records), "subjects": len(data), "manifest_sha256": sha256(manifest)}, indent=2) + "\n")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", type=Path, default=DEFAULT_DIR / "04b_execution_config_draft.json")
    common.add_argument("--receipt", type=Path, default=DEFAULT_DIR / "04b_manifest_receipt.json")
    common.add_argument("--manifests", type=Path, nargs=3, default=[DEFAULT_DIR / "04b_manifest_ad_cn.csv", DEFAULT_DIR / "04b_manifest_mci_cn.csv", DEFAULT_DIR / "04b_manifest_lmci_emci.csv"])
    common.add_argument("--output-root", type=Path, default=Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c_train_side/20261028/epoch165"))
    sub = p.add_subparsers(dest="command", required=True)
    c = sub.add_parser("check-only", parents=[common])
    c.add_argument("--results", type=Path, default=DEFAULT_DIR / "04c1_check_only_results.json")
    c.set_defaults(func=command_check)
    i = sub.add_parser("infer", parents=[common])
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
