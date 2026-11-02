"""Isolated two-fold, single-tracer SwinUNETR MRI-to-PET baseline."""
from __future__ import annotations

import argparse
import csv
import contextlib
import hashlib
import json
import os
import random
import shutil
import socket
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from model import build_model, parameter_count  # noqa: E402

TRACERS = ("FDG", "AV45")
SHAPE = (160, 192, 160)
EPOCHS = 200
RECOVERY_INTERVAL = 10
MILESTONES = (50, 100, 150, 200)
LR = 1e-5
FULL_REPORT = ROOT / "reports/original_author_reproduction_20261020"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def csv_write(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise RuntimeError(f"Refusing to write an empty CSV: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as stream:
        return list(csv.DictReader(stream))


def expected_cache_names(cohort: list[dict]) -> set[str]:
    from monai.data.utils import pickle_hashing

    return {pickle_hashing(row).decode() + ".pt" for row in cohort}


def fold_counts(cohort: list[dict]) -> dict[str, int]:
    return {str(fold): sum(int(row["test_fold"]) == fold for row in cohort) for fold in (1, 2)}


def valid_target(row: dict, tracer: str) -> bool:
    return not Path(row[tracer.lower()]).name.endswith("_zero.nii.gz")


def full_identity(full_config_path: Path) -> tuple[dict, list[dict], list[dict], dict]:
    full_config_path = full_config_path.resolve()
    report = full_config_path.parent
    full_cfg = json.loads(full_config_path.read_text())
    required = {
        "cohort.json": full_cfg["cohort_sha256"],
        "split_manifest.csv": full_cfg["split_manifest_sha256"],
    }
    for name, expected in required.items():
        path = report / name
        if not path.is_file() or sha256(path) != expected:
            raise RuntimeError(f"Frozen Full identity mismatch: {path}")
    cohort = json.loads((report / "cohort.json").read_text())
    manifest = read_csv(report / "split_manifest.csv")
    split_receipt = json.loads((report / "split_receipt.json").read_text())
    cache_receipt = json.loads((report / "persistent_cache_receipt.json").read_text())
    completion_path = report / "oof_summary/completion.json"
    completion = json.loads(completion_path.read_text())
    if len(cohort) != 1857 or len(manifest) != 1857 or len({r["name"] for r in cohort}) != 1857:
        raise RuntimeError("Full cohort must contain 1,857 unique subjects")
    counts = fold_counts(cohort)
    if counts != {"1": 929, "2": 928}:
        raise RuntimeError(f"Unexpected frozen Full fold sizes: {counts}")
    if split_receipt.get("unique_ptids") != 1857 or split_receipt.get("held_out_intersection_count") != 0:
        raise RuntimeError("Full split receipt does not establish subject-disjoint coverage")
    if not split_receipt.get("held_out_union_complete"):
        raise RuntimeError("Full split receipt does not establish complete held-out coverage")
    for i, (subject, split) in enumerate(zip(cohort, manifest)):
        if (int(split["paired_index"]) != i or split["ptid"] != subject["name"]
                or int(split["test_fold"]) != int(subject["test_fold"])):
            raise RuntimeError(f"Full split ordering mismatch at row {i}")
        for key in ("mri", "fdg", "av45"):
            if split[key] != subject[key]:
                raise RuntimeError(f"Full manifest path mismatch at row {i}/{key}")
    effective_by_fold = {
        str(fold): {
            tracer: sum(int(row["test_fold"]) == fold and valid_target(row, tracer) for row in cohort)
            for tracer in ("FDG", "AV45")
        }
        for fold in (1, 2)
    }
    effective = {tracer: sum(effective_by_fold[str(f)][tracer] for f in (1, 2)) for tracer in TRACERS}
    if effective != {"FDG": 1598, "AV45": 1365}:
        raise RuntimeError(f"Frozen Full valid PET counts mismatch: {effective}")
    if cache_receipt.get("status") != "COMPLETE" or cache_receipt.get("subjects") != 1857:
        raise RuntimeError("Full persistent cache receipt is not complete")
    if completion.get("status") != "COMPLETE_TWO_FOLD_OOF_RECONSTRUCTION" or completion.get("primary_epoch") != 165:
        raise RuntimeError("Full epoch-165 OOF completion receipt is invalid")
    metrics_path = report / "oof_summary/per_subject_metrics.csv"
    summary_path = report / "oof_summary/overall_summary.csv"
    if not metrics_path.is_file() or sha256(metrics_path) != completion["per_subject_sha256"]:
        raise RuntimeError("Full epoch-165 per-subject OOF metrics hash mismatch")
    if not summary_path.is_file() or sha256(summary_path) != completion.get("summary_sha256"):
        raise RuntimeError("Full OOF summary hash mismatch")
    hashes = {
        "full_config": sha256(full_config_path),
        "cohort": sha256(report / "cohort.json"),
        "split_manifest": sha256(report / "split_manifest.csv"),
        "split_receipt": sha256(report / "split_receipt.json"),
        "persistent_cache_receipt": sha256(report / "persistent_cache_receipt.json"),
        "full_oof_completion": sha256(completion_path),
        "full_oof_per_subject_metrics": sha256(metrics_path),
    }
    return full_cfg, cohort, manifest, {
        "report": str(report), "hashes": hashes, "fold_counts": counts,
        "effective_by_fold": effective_by_fold, "effective": effective,
        "cache_receipt": cache_receipt, "full_oof_epoch": 165,
        "cohort_size": len(cohort),
    }


def cache_status(cache_dir: Path, cohort: list[dict]) -> dict:
    expected = expected_cache_names(cohort)
    actual_paths = list(cache_dir.glob("*.pt")) if cache_dir.is_dir() else []
    actual = {path.name for path in actual_paths}
    return {
        "path": str(cache_dir), "exists": cache_dir.is_dir(),
        "expected_files": len(expected), "actual_files": len(actual),
        "missing_files": len(expected - actual), "extra_files": len(actual - expected),
        "name_set_sha256": hashlib.sha256("\n".join(sorted(actual)).encode()).hexdigest(),
        "bytes": sum(path.stat().st_size for path in actual_paths),
        "valid": actual == expected,
    }


def command_prepare(args) -> None:
    full_path = args.full_config.resolve()
    full_cfg, cohort, manifest, identity = full_identity(full_path)
    report, assets = args.out.resolve(), args.assets.resolve()
    if report.exists() or assets.exists():
        raise RuntimeError("Report or assets path exists; refusing to overwrite")
    cache_dir = args.cache_dir.resolve() if args.cache_dir else Path(identity["cache_receipt"]["cache_dir"])
    report.mkdir(parents=True)
    assets.mkdir(parents=True)
    cache = cache_status(cache_dir, cohort)
    model = {
        "implementation": "monai.networks.nets.SwinUNETR",
        "monai_api": "MONAI >= 1.5 constructor without img_size; explicit spatial_dims=3",
        "spatial_dims": 3, "in_channels": 1, "out_channels": 1,
        "feature_size": 48, "use_checkpoint": True,
        "prediction": "direct normalized PET regression from MRI only",
    }
    cfg = {
        "experiment": "swinunetr_mri_pet_2fold_oof",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "report": str(report), "assets": str(assets),
        "full_config": str(full_path), "full_report": identity["report"],
        "full_identity": identity,
        "full_config_sha256": identity["hashes"]["full_config"],
        "cohort_sha256": identity["hashes"]["cohort"],
        "split_manifest_sha256": identity["hashes"]["split_manifest"],
        "cache": cache, "cache_receipt_sha256": identity["hashes"]["persistent_cache_receipt"],
        "model": model, "model_source_sha256": sha256(HERE / "model.py"),
        "runner_sha256": sha256(Path(__file__)),
        "epochs": EPOCHS, "recovery_interval": RECOVERY_INTERVAL,
        "milestone_epochs": list(MILESTONES), "final_epoch": EPOCHS,
        "epoch_budget_provenance": "User-fixed 200 epochs; recovered historical candidate used 800 epochs, not verified as Figure 2 final run",
        "validation": "none; no held-out fold access during training",
        "learning_rate": LR, "batch_size": 1, "loss": "MSE on valid single-tracer PET only",
        "optimizer": "Adam", "amp": "CUDA autocast float16 with GradScaler",
        "activation_checkpointing": True,
        "seed_policy": "unseeded like recovered Swin and Full runs; capture and restore RNG state",
        "metrics": {"ssim": "generative.metrics.SSIMMetric spatial_dims=3 data_range=1 kernel_size=7",
                    "psnr": "MONAI PSNRMetric max_val=1.0", "mse": "torch.nn.functional.mse_loss",
                    "mae": "torch.nn.functional.l1_loss", "output_clamp": [0.0, 1.0]},
        "expected_effective": identity["effective"],
        "expected_effective_by_fold": identity["effective_by_fold"],
        "training_subjects_by_tracer_fold": {
            tracer: {str(f): identity["effective"][tracer] - identity["effective_by_fold"][str(f)][tracer]
                    for f in (1, 2)} for tracer in TRACERS
        },
        "training_seed_comparison": {
            "swin": "no fixed seed found in recovered training cells; RNG states recorded",
            "full": "training_seed=null in frozen Full config",
        },
        "status": "PREPARED_CACHE_VERIFIED" if cache["valid"] else "PREPARED_CACHE_MISSING_OR_MISMATCHED",
    }
    json_write(report / "config.json", cfg)
    json_write(report / "full_identity_receipt.json", identity)
    json_write(report / "prepare_receipt.json", {
        "status": cfg["status"], "config_sha256": sha256(report / "config.json"),
        "cache": cache,
    })
    print(json.dumps({"status": cfg["status"], "config": str(report / "config.json"),
                      "cache": cache}, ensure_ascii=False))


def load_config(path: Path) -> tuple[dict, list[dict]]:
    cfg = json.loads(path.read_text())
    report = Path(cfg["report"])
    if Path(cfg["full_config"]).is_file() is False or sha256(Path(cfg["full_config"])) != cfg["full_config_sha256"]:
        raise RuntimeError("Frozen Full config changed")
    _, cohort, _, identity = full_identity(Path(cfg["full_config"]))
    if identity["hashes"]["cohort"] != cfg["cohort_sha256"] or identity["hashes"]["split_manifest"] != cfg["split_manifest_sha256"]:
        raise RuntimeError("Full cohort/split changed after preparation")
    if sha256(HERE / "model.py") != cfg["model_source_sha256"] or sha256(Path(__file__)) != cfg["runner_sha256"]:
        raise RuntimeError("SwinUNETR implementation changed after configuration freeze")
    prepare_receipt = json.loads((report / "prepare_receipt.json").read_text())
    if sha256(report / "config.json") != prepare_receipt["config_sha256"]:
        raise RuntimeError("Frozen Swin config changed")
    return cfg, cohort


def validate_cache(cfg: dict, cohort: list[dict], *, load_sample: bool = False) -> dict:
    result = cache_status(Path(cfg["cache"]["path"]), cohort)
    if not result["valid"]:
        raise RuntimeError(f"Full cache identity check failed: {json.dumps(result)}")
    receipt = json.loads((Path(cfg["full_report"]) / "persistent_cache_receipt.json").read_text())
    if sha256(Path(cfg["full_report"]) / "persistent_cache_receipt.json") != cfg["cache_receipt_sha256"]:
        raise RuntimeError("Full cache receipt changed")
    if receipt.get("input_hashes_sha256") != cfg["full_identity"]["cache_receipt"]["input_hashes_sha256"]:
        raise RuntimeError("Full cache input hash identity mismatch")
    if load_sample:
        sample = FullCacheDataset([cohort[0]], Path(cfg["cache"]["path"]))[0]
        result["sample_ptid"] = sample["name"]
        result["sample_shapes"] = {key: list(sample[key].shape) for key in ("mri", "fdg", "av45")}
    return result


class FullCacheDataset:
    """Read tensors from the frozen Full MONAI PersistentDataset cache."""
    def __init__(self, rows: list[dict], cache_dir: Path):
        from monai.data.utils import pickle_hashing
        self.rows, self.cache_dir = rows, cache_dir
        self.paths = [cache_dir / (pickle_hashing(row).decode() + ".pt") for row in rows]
        if any(not path.is_file() for path in self.paths):
            raise RuntimeError("A required Full PersistentDataset cache entry is missing")

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        import torch
        row = self.rows[index]
        cached = torch.load(self.paths[index], map_location="cpu", weights_only=False)
        if cached.get("name") != row["name"]:
            raise RuntimeError(f"Cache PTID mismatch at {row['name']}")
        result = {"name": row["name"], "affine": np.eye(4)}
        try:
            affine = cached["mri"].affine
            result["affine"] = affine.detach().cpu().numpy() if hasattr(affine, "detach") else np.asarray(affine)
        except (AttributeError, KeyError, TypeError):
            pass
        for key in ("mri", "fdg", "av45"):
            tensor = cached[key].as_tensor() if hasattr(cached[key], "as_tensor") else cached[key]
            tensor = tensor.detach().float()
            if tuple(tensor.shape) != (1, *SHAPE) or not torch.isfinite(tensor).all():
                raise RuntimeError(f"Invalid cached tensor shape/content {row['name']}/{key}: {tuple(tensor.shape)}")
            result[key] = tensor
        return result


def command_check_config(args) -> None:
    config_path = args.config.resolve()
    try:
        cfg, cohort = load_config(config_path)
        cache = validate_cache(cfg, cohort, load_sample=True)
        result = {"status": "PASS", "subjects": len(cohort), "fold_counts": cfg["full_identity"]["fold_counts"],
                  "effective": cfg["expected_effective"], "cache": cache}
    except Exception as error:
        cfg = json.loads(config_path.read_text())
        result = {"status": "FAIL", "error": f"{type(error).__name__}: {error}", "cache": cfg.get("cache")}
        json_write(Path(cfg["report"]) / "config_check.json", result)
        print(json.dumps(result, ensure_ascii=False))
        raise
    json_write(Path(cfg["report"]) / "config_check.json", result)
    print(json.dumps(result, ensure_ascii=False))


def hardware(torch) -> dict:
    value = {"host": socket.gethostname(), "pid": os.getpid(), "python": sys.version,
             "torch": torch.__version__, "cuda": torch.version.cuda,
             "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES")}
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        props = torch.cuda.get_device_properties(0)
        value.update({"gpu": props.name, "gpu_uuid": str(getattr(props, "uuid", None)),
                      "free_bytes_at_start": free, "total_bytes": total})
    return value


def rng_state(torch) -> dict:
    return {"python": random.getstate(), "numpy": np.random.get_state(),
            "torch": torch.get_rng_state(), "cuda": torch.cuda.get_rng_state_all()}


def save_recovery(path: Path, model, optimizer, scaler, epoch: int, identity: dict, torch) -> None:
    state = {"format": 1, "model": model.state_dict(), "optimizer": optimizer.state_dict(),
             "scaler": scaler.state_dict(), "completed_epoch": epoch, "rng": rng_state(torch), **identity}
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(state, temporary)
    os.replace(temporary, path)


def restore_recovery(path: Path, model, optimizer, scaler, identity: dict, torch) -> int:
    state = torch.load(path, map_location="cpu", weights_only=False)
    if state.get("format") != 1 or any(state.get(key) != value for key, value in identity.items()):
        raise RuntimeError("Recovery file identity mismatch")
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scaler.load_state_dict(state["scaler"])
    random.setstate(state["rng"]["python"])
    np.random.set_state(state["rng"]["numpy"])
    torch.set_rng_state(state["rng"]["torch"])
    torch.cuda.set_rng_state_all(state["rng"]["cuda"])
    return int(state["completed_epoch"]) + 1


def validate_resource_receipt(path: Path, expected_host: str | None = None) -> dict:
    receipt = json.loads(path.read_text())
    status = receipt.get("allocation_status")
    if status not in ("EXCLUSIVE", "SAFE_HANDOFF"):
        raise RuntimeError("GPU receipt must establish EXCLUSIVE or SAFE_HANDOFF allocation")
    if not receipt.get("gpu_uuid") or not receipt.get("protection_id") or not receipt.get("issued_by"):
        raise RuntimeError("GPU allocation receipt lacks UUID/protection/issuer evidence")
    if expected_host and receipt.get("host") != expected_host:
        raise RuntimeError("GPU allocation host differs from current node")
    issued = datetime.fromisoformat(receipt["issued_utc"].replace("Z", "+00:00"))
    age = (datetime.now(timezone.utc) - issued).total_seconds()
    if age > 300 or age < -60:
        raise RuntimeError("GPU allocation receipt is older than five minutes")
    return receipt


def verify_device_receipt(receipt: dict, torch) -> None:
    visible = os.environ.get("CUDA_VISIBLE_DEVICES", "")
    # CUDA accepts UUIDs with the ``GPU-`` prefix, while PyTorch's device
    # properties may expose the same UUID without it. Compare canonical IDs.
    normalize_uuid = lambda value: str(value).strip().removeprefix("GPU-").lower()
    expected_uuid = normalize_uuid(receipt["gpu_uuid"])
    if normalize_uuid(visible) != expected_uuid:
        raise RuntimeError("CUDA_VISIBLE_DEVICES must bind exactly the allocated GPU UUID")
    prop_uuid = getattr(torch.cuda.get_device_properties(0), "uuid", None)
    if prop_uuid is not None and normalize_uuid(prop_uuid) != expected_uuid:
        raise RuntimeError("Visible CUDA device UUID differs from allocation receipt")


def move_batch(batch: dict, device, torch):
    return {key: (value.to(device, non_blocking=True) if isinstance(value, torch.Tensor) else value)
            for key, value in batch.items()}


def train_step(model, batch, optimizer, scaler, torch, F, *, autocast: bool = True):
    optimizer.zero_grad(set_to_none=True)
    with torch.autocast("cuda", dtype=torch.float16, enabled=autocast):
        prediction = model(batch["mri"])
        loss = F.mse_loss(prediction.float(), batch["target"].float())
    if not torch.isfinite(loss):
        raise RuntimeError("Non-finite MSE loss")
    scaler.scale(loss).backward()
    # Let GradScaler detect non-finite scaled gradients, lower its scale, and
    # skip that optimizer update as designed. Inspecting scaled gradients before
    # scaler.step() would reject recoverable AMP overflow.
    scaler.step(optimizer)
    scaler.update()
    return float(loss.detach())


def command_smoke_test(args) -> None:
    import torch
    import torch.nn.functional as F
    from torch.utils.data import DataLoader

    if args.cuda and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but unavailable")
    if args.full_sample and (not args.cuda or not args.config or not args.resource_receipt):
        raise RuntimeError("Full-size CUDA preflight requires --config and an exclusive allocation receipt")
    device = torch.device("cuda" if args.cuda else "cpu")
    cfg, cohort = load_config(args.config.resolve()) if args.config else (None, None)
    if args.full_sample:
        resource = validate_resource_receipt(args.resource_receipt, socket.gethostname())
        verify_device_receipt(resource, torch)
        validate_cache(cfg, cohort)
        fold, tracer = args.fold, args.tracer
        if fold not in (1, 2):
            raise ValueError("Full-size preflight requires fold 1 or 2")
        rows = [row for row in cohort if int(row["test_fold"]) != fold and valid_target(row, tracer)]
        dataset = FullCacheDataset(
            rows[: max(args.steps + args.warmup_steps, 2)], Path(cfg["cache"]["path"])
        )
        loader = iter(DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0, pin_memory=True))
        model = build_model(use_checkpoint=cfg["activation_checkpointing"]).to(device).train()
        optimizer = torch.optim.Adam(model.parameters(), lr=LR)
        scaler = torch.amp.GradScaler("cuda")
        torch.cuda.reset_peak_memory_stats()
        measured, losses = [], []
        amp_skipped_steps = 0
        count = args.steps + args.warmup_steps
        start = time.perf_counter()
        for index in range(count):
            item = next(loader)
            batch = {"mri": item["mri"].to(device, non_blocking=True),
                     "target": item[tracer.lower()].to(device, non_blocking=True)}
            torch.cuda.synchronize()
            step_start = time.perf_counter()
            scale_before = scaler.get_scale()
            loss = train_step(model, batch, optimizer, scaler, torch, F)
            amp_skipped_steps += int(scaler.get_scale() < scale_before)
            torch.cuda.synchronize()
            elapsed = time.perf_counter() - step_start
            losses.append(loss)
            if index >= args.warmup_steps:
                measured.append(elapsed)
        if amp_skipped_steps >= count:
            raise RuntimeError("GradScaler skipped every preflight optimizer update")
        elapsed_total = time.perf_counter() - start
        params = parameter_count(model)
        preflight_tmp_root = Path(cfg["assets"]) / "preflight_tmp"
        preflight_tmp_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=preflight_tmp_root) as temp_dir:
            model_path = Path(temp_dir) / "model.pt"
            recovery_path = Path(temp_dir) / "recovery.pt"
            torch.save(model.state_dict(), model_path)
            save_recovery(recovery_path, model, optimizer, scaler, 0, {"preflight": True}, torch)
            model_bytes, recovery_bytes = model_path.stat().st_size, recovery_path.stat().st_size
        counts = cfg["training_subjects_by_tracer_fold"]
        step_median = statistics.median(measured)
        estimates = {}
        all_seconds = 0.0
        for tr in TRACERS:
            for f in (1, 2):
                updates = int(counts[tr][str(f)]) * EPOCHS
                seconds = updates * step_median
                estimates[f"{tr}_fold{f}"] = {"updates": updates, "seconds": seconds,
                                                "hours": seconds / 3600}
                all_seconds += seconds
        milestones = len(MILESTONES) * model_bytes
        per_instance_storage = milestones + recovery_bytes
        prediction_bytes = sum(cfg["expected_effective"].values()) * int(np.prod(SHAPE)) * 4
        result = {
            "status": "PASS_NO_FORMAL_TRAINING_STATE",
            "hardware": hardware(torch), "allocation_receipt_sha256": sha256(args.resource_receipt),
            "allocation": resource, "tracer": tracer, "fold": fold,
            "sample_ptids": [row["name"] for row in rows[:len(measured) + args.warmup_steps]],
            "input_shape": [1, 1, *SHAPE], "parameters": params,
            "warmup_steps": args.warmup_steps, "measured_steps": len(measured),
            "mean_loss": float(np.mean(losses)), "all_losses_finite": True,
            "amp_skipped_steps": amp_skipped_steps, "amp_final_scale": scaler.get_scale(),
            "successful_optimizer_updates": count - amp_skipped_steps,
            "step_seconds": measured, "step_seconds_median": step_median,
            "step_seconds_mean": statistics.mean(measured), "benchmark_wall_seconds": elapsed_total,
            "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
            "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
            "model_checkpoint_bytes": model_bytes, "rolling_recovery_bytes": recovery_bytes,
            "persistent_milestone_count": len(MILESTONES),
            "estimated_per_instance_storage_bytes": per_instance_storage,
            "estimated_four_instance_storage_bytes": 4 * per_instance_storage,
            "estimated_all_oof_prediction_bytes_uncompressed": prediction_bytes,
            "estimated_four_instance_total_assets_bytes": 4 * per_instance_storage + prediction_bytes,
            "training_time_estimates": estimates,
            "fdg_fold1_estimated_hours": estimates["FDG_fold1"]["hours"],
            "all_four_estimated_hours": all_seconds / 3600,
            "heldout_accessed": False, "formal_checkpoint_written": False,
            "activation_checkpointing": cfg["activation_checkpointing"],
            "autocast": "float16", "optimizer_steps": len(measured) + args.warmup_steps,
            "config_sha256": sha256(Path(args.config)),
        }
        target = Path(cfg["report"]) / "cuda_preflight.json"
        if target.exists():
            raise RuntimeError(f"Preflight receipt exists; refusing to overwrite: {target}")
        json_write(target, result)
    else:
        model = build_model(use_checkpoint=True).to(device).eval()
        size = args.size
        if size < 64 or size % 32:
            raise ValueError("--size must be at least 64 and divisible by 32")
        image = torch.rand(1, 1, size, size, size, device=device)
        with torch.no_grad():
            prediction = model(image)
        if prediction.shape != image.shape or not torch.isfinite(prediction).all():
            raise RuntimeError("Synthetic forward output is invalid")
        result = {"status": "PASS", "device": str(device), "shape": list(image.shape),
                  "parameters": parameter_count(model), "implementation": "MONAI SwinUNETR 3D",
                  "forward_finite": True}
    print(json.dumps(result, ensure_ascii=False))


def checkpoint_identity(cfg: dict, fold: int, tracer: str) -> dict:
    return {"tracer": tracer, "fold": fold, "config_sha256": sha256(Path(cfg["report"]) / "config.json"),
            "cohort_sha256": cfg["cohort_sha256"], "split_manifest_sha256": cfg["split_manifest_sha256"],
            "model_source_sha256": cfg["model_source_sha256"], "epochs": EPOCHS}


def save_milestone(path: Path, model, epoch: int, identity: dict, torch) -> dict:
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save({"model": model.state_dict(), "epoch": epoch, **identity}, temporary)
    os.replace(temporary, path)
    receipt = {**identity, "epoch": epoch, "checkpoint_sha256": sha256(path),
               "model_sha256": state_hash(model.state_dict()), "weights_only": True}
    json_write(path.with_suffix(".json"), receipt)
    return receipt


def state_hash(state: dict) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def command_train(args) -> None:
    import torch
    import torch.nn.functional as F
    from torch.utils.data import DataLoader

    tracer = args.tracer.upper()
    if tracer not in TRACERS or args.fold not in (1, 2):
        raise ValueError("Use --tracer FDG|AV45 and --fold 1|2")
    cfg, cohort = load_config(args.config.resolve())
    allocation = validate_resource_receipt(args.resource_receipt, socket.gethostname())
    validate_cache(cfg, cohort)
    if not torch.cuda.is_available():
        raise RuntimeError("Formal training requires CUDA")
    verify_device_receipt(allocation, torch)
    preflight_path = Path(cfg["report"]) / "cuda_preflight.json"
    if not preflight_path.is_file():
        raise RuntimeError("Full-size forward/backward/optimizer preflight has not passed")
    preflight = json.loads(preflight_path.read_text())
    if (preflight.get("status") != "PASS_NO_FORMAL_TRAINING_STATE"
            or preflight.get("config_sha256") != sha256(Path(args.config))
            or preflight.get("allocation", {}).get("gpu_uuid") != allocation["gpu_uuid"]):
        raise RuntimeError("Preflight config or allocated GPU identity differs from formal training")
    if shutil.disk_usage(Path(cfg["assets"])).free < int(preflight["estimated_four_instance_total_assets_bytes"]):
        raise RuntimeError("Available asset storage is below the four-instance asset estimate")
    if args.resume:
        if args.resume.name != "recovery.pt":
            raise RuntimeError("Resume must use the isolated rolling recovery.pt")
    run_dir = Path(cfg["assets"]) / "formal" / tracer / f"fold{args.fold}"
    if args.resume:
        if not run_dir.is_dir() or args.resume.resolve() != (run_dir / "recovery.pt").resolve():
            raise RuntimeError("Recovery path does not match this tracer/fold run")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
    rows = [row for row in cohort if int(row["test_fold"]) != args.fold and valid_target(row, tracer)]
    dataset = FullCacheDataset(rows, Path(cfg["cache"]["path"]))
    loader = DataLoader(dataset, batch_size=1, shuffle=True, num_workers=0, pin_memory=True)
    model = build_model(use_checkpoint=cfg["activation_checkpointing"]).cuda().train()
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    scaler = torch.amp.GradScaler("cuda")
    identity = checkpoint_identity(cfg, args.fold, tracer)
    start_epoch = restore_recovery(args.resume, model, optimizer, scaler, identity, torch) if args.resume else 0
    start = {**identity, "status": "STARTED", "pid": os.getpid(),
             "log_path": str(args.log_path.resolve()), "hardware": hardware(torch),
             "parameters": parameter_count(model),
             "training_subjects": len(dataset), "heldout_subjects": sum(int(r["test_fold"]) == args.fold for r in cohort),
             "heldout_access_during_training": False, "seed_policy": cfg["seed_policy"],
             "start_epoch_one_based": start_epoch + 1,
             "resource_receipt_sha256": sha256(args.resource_receipt)}
    json_write(run_dir / ("resume_start.json" if args.resume else "start.json"), start)
    log_path = run_dir / "training_epochs.jsonl"
    recovery_path = run_dir / "recovery.pt"
    json_write(run_dir / "launch_receipt.json", {**start,
               "started_utc": datetime.now(timezone.utc).isoformat(),
               "recovery_path": str(recovery_path),
               "resource_receipt_sha256": sha256(args.resource_receipt)})
    for epoch in range(start_epoch, EPOCHS):
        model.train()
        losses, started = [], time.monotonic()
        amp_skipped_updates = 0
        for batch in loader:
            batch = move_batch(batch, torch.device("cuda"), torch)
            target = batch[tracer.lower()]
            if torch.all(target == 0):
                raise RuntimeError("A missing-PET placeholder reached the filtered training set")
            scale_before = scaler.get_scale()
            losses.append(train_step(model, {"mri": batch["mri"], "target": target}, optimizer,
                                     scaler, torch, F))
            amp_skipped_updates += int(scaler.get_scale() < scale_before)
        epoch_number = epoch + 1
        if epoch_number % RECOVERY_INTERVAL == 0:
            save_recovery(recovery_path, model, optimizer, scaler, epoch, identity, torch)
            event = {"epoch": epoch_number, "train_mse_mean": float(np.mean(losses)),
                     "train_subjects": len(losses), "seconds": time.monotonic() - started,
                     "amp_skipped_updates": amp_skipped_updates,
                     "recovery_sha256": sha256(recovery_path), "heldout_validation": None}
            with log_path.open("a") as stream:
                stream.write(json.dumps(event) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(json.dumps(event), flush=True)
        if epoch_number in MILESTONES:
            receipt = save_milestone(run_dir / f"checkpoint_epoch{epoch_number}.pt", model,
                                     epoch_number, identity, torch)
            if epoch_number == EPOCHS:
                json_write(run_dir / "complete.json", {**identity, **receipt,
                           "status": "TRAINING_COMPLETE_NOT_INFERRED",
                           "validation_or_test_used_for_selection": False,
                           "final_checkpoint": str(run_dir / f"checkpoint_epoch{EPOCHS}.pt")})


def command_infer(args) -> None:
    import nibabel as nib
    import torch
    import torch.nn.functional as F
    from monai.metrics import PSNRMetric
    from torch.utils.data import DataLoader
    author_root = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo"
    if str(author_root) not in sys.path:
        sys.path.insert(0, str(author_root))
    from generative.metrics import SSIMMetric

    tracer = args.tracer.upper()
    cfg, cohort = load_config(args.config.resolve())
    if tracer not in TRACERS or args.fold not in (1, 2) or args.epoch != EPOCHS:
        raise ValueError(f"Only fixed epoch {EPOCHS} and fold 1/2 are supported")
    validate_cache(cfg, cohort)
    if not torch.cuda.is_available():
        raise RuntimeError("OOF inference requires CUDA")
    rows = [row for row in cohort if int(row["test_fold"]) == args.fold and valid_target(row, tracer)]
    dataset = FullCacheDataset(rows, Path(cfg["cache"]["path"]))
    loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0, pin_memory=True)
    run_dir = Path(cfg["assets"]) / "formal" / tracer / f"fold{args.fold}"
    checkpoint = run_dir / f"checkpoint_epoch{EPOCHS}.pt"
    receipt = json.loads(checkpoint.with_suffix(".json").read_text())
    if sha256(checkpoint) != receipt["checkpoint_sha256"]:
        raise RuntimeError("Final checkpoint hash mismatch")
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    identity = checkpoint_identity(cfg, args.fold, tracer)
    if any(state.get(key) != value for key, value in identity.items()):
        raise RuntimeError("Checkpoint identity mismatch")
    model = build_model(use_checkpoint=cfg["activation_checkpointing"]).cuda().eval()
    model.load_state_dict(state["model"])
    output = Path(cfg["assets"]) / "oof" / f"epoch{EPOCHS}" / tracer / f"fold{args.fold}"
    output.mkdir(parents=True, exist_ok=False)
    ssim, psnr, metric_rows = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7), PSNRMetric(max_val=1.0), []
    with torch.no_grad():
        for batch in loader:
            sid = batch["name"][0]
            mri, target = batch["mri"].cuda(), batch[tracer.lower()].cuda()
            prediction = torch.clamp(model(mri).float(), 0.0, 1.0)
            affine = batch["affine"][0].numpy() if isinstance(batch["affine"], torch.Tensor) else np.asarray(batch["affine"][0])
            prediction_path = output / f"generated_{tracer}_{sid}.nii.gz"
            nib.save(nib.Nifti1Image(prediction.squeeze().cpu().numpy(), affine), prediction_path)
            row = {"ptid": sid, "tracer": tracer, "fold": args.fold, "epoch": EPOCHS,
                   "ssim": float(ssim(prediction, target).mean()), "psnr": float(psnr(prediction, target).mean()),
                   "mse": float(F.mse_loss(prediction, target.float())),
                   "mae": float(F.l1_loss(prediction, target.float())),
                   "prediction": str(prediction_path), "prediction_sha256": sha256(prediction_path),
                   "checkpoint_sha256": sha256(checkpoint)}
            metric_rows.append(row)
            print(json.dumps(row), flush=True)
    expected = cfg["expected_effective_by_fold"][str(args.fold)][tracer]
    if len(metric_rows) != expected:
        raise RuntimeError(f"OOF metric count mismatch: {len(metric_rows)} != {expected}")
    csv_write(output / "metrics.csv", metric_rows)
    json_write(output / "complete.json", {"status": "COMPLETE_FOLD_OOF", "fold": args.fold,
               "tracer": tracer, "epoch": EPOCHS, "metric_rows": len(metric_rows),
               "metrics_sha256": sha256(output / "metrics.csv"), "checkpoint_sha256": sha256(checkpoint),
               "prediction_policy": "held-out fold once; no metric-driven model selection"})


def command_summarize(args) -> None:
    cfg, _ = load_config(args.config.resolve())
    full_rows = read_csv(Path(cfg["full_report"]) / "oof_summary/per_subject_metrics.csv")
    full_rows = [row for row in full_rows if int(row["epoch"]) == 165]
    swin_rows = []
    for tracer in TRACERS:
        for fold in (1, 2):
            folder = Path(cfg["assets"]) / "oof" / f"epoch{EPOCHS}" / tracer / f"fold{fold}"
            receipt = json.loads((folder / "complete.json").read_text())
            if sha256(folder / "metrics.csv") != receipt["metrics_sha256"]:
                raise RuntimeError(f"Swin metric hash mismatch: {tracer}/fold{fold}")
            swin_rows.extend(read_csv(folder / "metrics.csv"))
    full_map = {(r["ptid"], r["tracer"].upper(), int(r["fold"])): r for r in full_rows}
    swin_map = {(r["ptid"], r["tracer"].upper(), int(r["fold"])): r for r in swin_rows}
    if len(swin_map) != len(swin_rows) or set(full_map) != set(swin_map):
        raise RuntimeError("Swin and Full epoch-165 OOF identities are not one-to-one")
    paired = []
    for key in sorted(swin_map):
        left, right = full_map[key], swin_map[key]
        paired.append({"ptid": key[0], "tracer": key[1], "fold": key[2],
                       "full_epoch": 165, "swin_epoch": EPOCHS,
                       **{metric: float(right[metric]) for metric in ("ssim", "psnr", "mse", "mae")},
                       **{f"full_{metric}": float(left[metric]) for metric in ("ssim", "psnr", "mse", "mae")}})
    report = Path(cfg["report"]) / "oof_summary"
    report.mkdir(parents=True, exist_ok=False)
    csv_write(report / "paired_full_epoch165.csv", paired)
    summary = []
    for tracer in TRACERS:
        group = [row for row in paired if row["tracer"] == tracer]
        item = {"tracer": tracer, "n": len(group)}
        for metric in ("ssim", "psnr", "mse", "mae"):
            item[metric] = float(np.mean([row[metric] for row in group]))
            item[f"full_{metric}"] = float(np.mean([row[f"full_{metric}"] for row in group]))
        summary.append(item)
    csv_write(report / "summary.csv", summary)
    json_write(report / "completion.json", {"status": "COMPLETE_SWINUNETR_TWO_FOLD_OOF",
               "swin_epoch": EPOCHS, "full_epoch": 165, "paired_rows": len(paired),
               "paired_sha256": sha256(report / "paired_full_epoch165.csv"),
               "summary_sha256": sha256(report / "summary.csv")})


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    sub = result.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--full-config", type=Path, default=FULL_REPORT / "config.json")
    prepare.add_argument("--cache-dir", type=Path)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--assets", type=Path, required=True)
    check = sub.add_parser("check-config")
    check.add_argument("--config", type=Path, required=True)
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--size", type=int, default=64)
    smoke.add_argument("--cuda", action="store_true")
    smoke.add_argument("--full-sample", action="store_true")
    smoke.add_argument("--config", type=Path)
    smoke.add_argument("--resource-receipt", type=Path)
    smoke.add_argument("--tracer", choices=TRACERS, default="FDG")
    smoke.add_argument("--fold", type=int, choices=(1, 2), default=1)
    smoke.add_argument("--steps", type=int, default=10)
    smoke.add_argument("--warmup-steps", type=int, default=2)
    train = sub.add_parser("train")
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--tracer", choices=TRACERS, required=True)
    train.add_argument("--fold", type=int, choices=(1, 2), required=True)
    train.add_argument("--resource-receipt", type=Path, required=True)
    train.add_argument("--log-path", type=Path, required=True)
    train.add_argument("--resume", type=Path)
    infer = sub.add_parser("infer")
    infer.add_argument("--config", type=Path, required=True)
    infer.add_argument("--tracer", choices=TRACERS, required=True)
    infer.add_argument("--fold", type=int, choices=(1, 2), required=True)
    infer.add_argument("--epoch", type=int, choices=(EPOCHS,), default=EPOCHS)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--config", type=Path, required=True)
    return result


if __name__ == "__main__":
    args = parser().parse_args()
    actions = {"prepare": command_prepare, "check-config": command_check_config,
               "smoke-test": command_smoke_test, "train": command_train,
               "infer": command_infer, "summarize": command_summarize}
    if args.action == "train":
        args.log_path = args.log_path.resolve()
        args.log_path.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if args.resume else "x"
        with args.log_path.open(mode, buffering=1) as stream:
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                actions[args.action](args)
    else:
        actions[args.action](args)
