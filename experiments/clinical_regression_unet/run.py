"""Independent two-fold clinical-conditioned 3D PET regression baseline."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import re
import shutil
import socket
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from model import ClinicalRegressionUNet3D, parameter_count  # noqa: E402


TRACERS = ("fdg", "av45")
FEATURES = ("age", "sex", "weight", "cdr", "mmse", "gds", "faq", "npiq")
CONTINUOUS = ("age", "weight", "cdr", "mmse", "gds", "faq", "npiq")
TRACER_ONE_HOT = {"fdg": (1.0, 0.0), "av45": (0.0, 1.0)}
MODEL_CHANNELS = (32, 64, 64, 128)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(temporary, path)


def csv_write(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_description(text: str) -> dict[str, float]:
    patterns = {
        "head": r"^Subject is a (?P<age>[-+0-9.]+)-year-old (?P<sex>male|female) with a weight of (?P<weight>[-+0-9.]+) kg\.",
        "cdr": r"Clinical Dementia Rating \(CDR\).*? is (?P<cdr>[-+0-9.]+)\. The Mini-Mental",
        "mmse": r"Mini-Mental State Examination \(MMSE\).*? is (?P<mmse>[-+0-9.]+)\. The Geriatric",
        "gds": r"Geriatric Depression Scale \(GDS\).*? is (?P<gds>[-+0-9.]+)\. The Functional",
        "faq": r"Functional Activities Questionnaire \(FAQ\).*? is (?P<faq>[-+0-9.]+)\. The Neuropsychiatric",
        "npiq": r"Neuropsychiatric Inventory Questionnaire \(NPI-Q\).*? is (?P<npiq>[-+0-9.]+)\.$",
    }
    values: dict[str, float | str] = {}
    for label, pattern in patterns.items():
        match = re.search(pattern, text)
        if match is None:
            raise ValueError(f"Description does not match the frozen Full template at {label}")
        values.update(match.groupdict())
    sex = values.pop("sex")
    result = {name: float(value) for name, value in values.items()}
    result["sex"] = 1.0 if sex == "male" else 0.0
    if not all(np.isfinite(value) for value in result.values()):
        raise ValueError("Non-finite clinical value in Full description")
    return {name: result[name] for name in FEATURES}


def verify_metadata(row: dict, description: str, parsed: dict[str, float]) -> None:
    required = {
        "Subject ID", "Sex", "Weight", "Age", "MMSE Total Score", "GDSCALE Total Score",
        "Global CDR", "FAQ Total Score", "NPI-Q Total Score", "Description",
    }
    if not required.issubset(row) or any(row[name].strip() == "" for name in required):
        raise RuntimeError("Frozen clinical table has a missing required field")
    if row["Description"] != description:
        raise RuntimeError(f"Clinical Description mismatch for {row['Subject ID']}")
    expected = {
        "age": float(f"{float(row['Age']):.0f}"),
        "sex": 1.0 if row["Sex"] == "M" else 0.0 if row["Sex"] == "F" else np.nan,
        "weight": float(f"{float(row['Weight']):.1f}"),
        "cdr": float(f"{float(row['Global CDR']):.1f}"),
        "mmse": float(f"{float(row['MMSE Total Score']):.0f}"),
        "gds": float(f"{float(row['GDSCALE Total Score']):.0f}"),
        "faq": float(f"{float(row['FAQ Total Score']):.0f}"),
        "npiq": float(f"{float(row['NPI-Q Total Score']):.0f}"),
    }
    if not all(np.isfinite(value) for value in expected.values()):
        raise RuntimeError(f"Invalid sex or numeric value for {row['Subject ID']}")
    if parsed != expected:
        raise RuntimeError(f"Rendered Full values differ from the frozen table for {row['Subject ID']}")


def expected_cache_names(cohort: list[dict]) -> set[str]:
    from monai.data.utils import pickle_hashing

    return {pickle_hashing(row).decode() + ".pt" for row in cohort}


def validate_cache(cache_dir: Path, cohort: list[dict]) -> dict:
    expected = expected_cache_names(cohort)
    actual_paths = list(cache_dir.glob("*.pt"))
    actual = {path.name for path in actual_paths}
    if actual != expected:
        raise RuntimeError(
            f"Full cache mismatch: expected={len(expected)} actual={len(actual)} "
            f"missing={len(expected - actual)} extra={len(actual - expected)}"
        )
    return {
        "cache_dir": str(cache_dir.resolve()),
        "files": len(actual_paths),
        "bytes": sum(path.stat().st_size for path in actual_paths),
        "cache_name_set_sha256": hashlib.sha256("\n".join(sorted(actual)).encode()).hexdigest(),
    }


def fold_normalization(features: list[dict], held_out_fold: int) -> dict:
    training = [row for row in features if int(row["test_fold"]) != held_out_fold]
    result = {}
    for name in CONTINUOUS:
        values = np.asarray([float(row[name]) for row in training], dtype=np.float64)
        mean, scale = float(values.mean()), float(values.std(ddof=0))
        if scale == 0.0:
            scale = 1.0
        result[name] = {"mean": mean, "scale": scale}
    return {"fit_subjects": len(training), "continuous": result, "sex_encoding": {"F": 0, "M": 1}}


def command_prepare(args) -> None:
    full_config_path = args.full_config.resolve()
    full_report = full_config_path.parent
    clinical_table = args.clinical_table.resolve()
    cache_dir = args.cache_dir.resolve()
    out, assets = args.out.resolve(), args.assets.resolve()
    if out.exists() or assets.exists():
        raise RuntimeError("Report/assets path already exists; refusing to overwrite")

    full_cfg = json.loads(full_config_path.read_text())
    cohort_path = full_report / "cohort.json"
    manifest_path = full_report / "split_manifest.csv"
    input_hashes_path = full_report / "input_hashes.csv"
    if sha256(cohort_path) != full_cfg["cohort_sha256"]:
        raise RuntimeError("Frozen Full cohort hash mismatch")
    if sha256(manifest_path) != full_cfg["split_manifest_sha256"]:
        raise RuntimeError("Frozen Full split manifest hash mismatch")
    cohort = json.loads(cohort_path.read_text())
    manifest = read_csv(manifest_path)
    if len(cohort) != 1857 or len(manifest) != 1857:
        raise RuntimeError("Task A requires exactly 1857 Full subjects")
    for index, (subject, split) in enumerate(zip(cohort, manifest)):
        if (
            int(split["paired_index"]) != index
            or split["ptid"] != subject["name"]
            or int(split["test_fold"]) != int(subject["test_fold"])
        ):
            raise RuntimeError(f"Full split order mismatch at row {index}")
    fold_counts = {str(fold): sum(int(row["test_fold"]) == fold for row in cohort) for fold in (1, 2)}
    if fold_counts != {"1": 929, "2": 928}:
        raise RuntimeError(f"Unexpected Full fold counts: {fold_counts}")

    metadata_rows = read_csv(clinical_table)
    if len(metadata_rows) != 1857:
        raise RuntimeError("Clinical table does not contain 1857 rows")
    metadata = {row["Subject ID"]: row for row in metadata_rows}
    if len(metadata) != 1857:
        raise RuntimeError("Duplicate Subject ID in clinical table")
    feature_rows = []
    for index, subject in enumerate(cohort):
        sid = subject["name"]
        if sid not in metadata:
            raise RuntimeError(f"Missing clinical row for {sid}")
        parsed = parse_description(subject["description"])
        verify_metadata(metadata[sid], subject["description"], parsed)
        feature_rows.append({"paired_index": index, "ptid": sid, "test_fold": subject["test_fold"], **parsed})

    cache_receipt = validate_cache(cache_dir, cohort)
    effective_by_fold = {}
    for fold in (1, 2):
        rows = [row for row in manifest if int(row["test_fold"]) == fold]
        effective_by_fold[str(fold)] = {
            tracer: sum(not Path(row[tracer]).name.endswith("_zero.nii.gz") for row in rows)
            for tracer in TRACERS
        }
    effective = {
        tracer: sum(effective_by_fold[str(fold)][tracer] for fold in (1, 2))
        for tracer in TRACERS
    }
    if effective != {"fdg": 1598, "av45": 1365}:
        raise RuntimeError(f"Unexpected effective tracer counts: {effective}")

    out.mkdir(parents=True)
    assets.mkdir(parents=True)
    csv_write(out / "clinical_features.csv", feature_rows)
    source_status = ROOT / "reports/e1_stage01_20261017/clinical_source_receipt.json"
    config = {
        "experiment": "clinical_regression_unet_task_a",
        "report": str(out),
        "assets": str(assets),
        "full_config": str(full_config_path),
        "full_report": str(full_report),
        "full_config_sha256": sha256(full_config_path),
        "cohort_sha256": sha256(cohort_path),
        "split_manifest_sha256": sha256(manifest_path),
        "input_hashes_sha256": sha256(input_hashes_path),
        "clinical_table": str(clinical_table),
        "clinical_table_sha256": sha256(clinical_table),
        "clinical_source_status": str(source_status),
        "clinical_source_status_sha256": sha256(source_status),
        "clinical_features_sha256": sha256(out / "clinical_features.csv"),
        "clinical_fields": list(FEATURES),
        "clinical_value_policy": "values rendered in the actual frozen Full Description",
        "clinical_provenance_limit": "historical filled fields; upstream imputation method not recovered",
        "fold_normalization": {str(fold): fold_normalization(feature_rows, fold) for fold in (1, 2)},
        "cache": cache_receipt,
        "fold_counts": fold_counts,
        "expected_effective_by_fold": effective_by_fold,
        "expected_effective": effective,
        "model": {
            "name": "ClinicalRegressionUNet3D",
            "channels": list(MODEL_CHANNELS),
            "condition": "8 clinical + 2 tracer one-hot -> MLP(10,64,256) -> bottleneck FiLM",
            "prediction": "direct normalized PET regression",
            "model_source_sha256": sha256(HERE / "model.py"),
        },
        "runner_sha256": sha256(Path(__file__)),
        "seed": 42,
        "epochs": 200,
        "primary_epoch": 165,
        "secondary_epoch": 200,
        "val_interval": 10,
        "learning_rate": 2.5e-5,
        "batch_size": 1,
        "loss": "sum of valid-tracer direct PET MSE; sequential backward; one optimizer step",
        "amp": True,
        "minimum_output_free_bytes": 50 * 1024**3,
        "status": "PREPARED_NOT_TRAINED",
    }
    json_write(out / "config.json", config)
    json_write(
        out / "prepare_receipt.json",
        {
            "status": "PASS",
            "subjects": len(cohort),
            "fold_counts": fold_counts,
            "expected_effective": effective,
            "split_manifest_reused_not_regenerated": True,
            "diagnosis_used": False,
            "biomedclip_used": False,
            "cache_copied": False,
            "config_sha256": sha256(out / "config.json"),
        },
    )
    print(json.dumps({"config": str(out / "config.json"), "assets": str(assets), "status": "PASS"}))


def load_config(path: Path) -> tuple[dict, list[dict], list[dict]]:
    cfg = json.loads(path.read_text())
    cfg["_config_sha256"] = sha256(path)
    out = Path(cfg["report"])
    full_report = Path(cfg["full_report"])
    checks = {
        Path(cfg["full_config"]): cfg["full_config_sha256"],
        full_report / "cohort.json": cfg["cohort_sha256"],
        full_report / "split_manifest.csv": cfg["split_manifest_sha256"],
        full_report / "input_hashes.csv": cfg["input_hashes_sha256"],
        Path(cfg["clinical_table"]): cfg["clinical_table_sha256"],
        Path(cfg["clinical_source_status"]): cfg["clinical_source_status_sha256"],
        out / "clinical_features.csv": cfg["clinical_features_sha256"],
        HERE / "model.py": cfg["model"]["model_source_sha256"],
        Path(__file__): cfg["runner_sha256"],
    }
    for artifact, digest in checks.items():
        if not artifact.exists() or sha256(artifact) != digest:
            raise RuntimeError(f"Frozen Task A artifact changed or missing: {artifact}")
    cohort = json.loads((full_report / "cohort.json").read_text())
    features = read_csv(out / "clinical_features.csv")
    if len(cohort) != len(features) or any(row["name"] != feature["ptid"] for row, feature in zip(cohort, features)):
        raise RuntimeError("Clinical feature order differs from Full cohort")
    return cfg, cohort, features


def standardized_vector(feature: dict, normalization: dict) -> np.ndarray:
    values = []
    for name in FEATURES:
        value = float(feature[name])
        if name in CONTINUOUS:
            stats = normalization["continuous"][name]
            value = (value - float(stats["mean"])) / float(stats["scale"])
        values.append(value)
    return np.asarray(values, dtype=np.float32)


class FullCacheDataset:
    """Read only the frozen Full tensors and deliberately discard cached contexts."""

    def __init__(self, rows: list[dict], features: list[dict], cache_dir: Path, normalization: dict) -> None:
        from monai.data.utils import pickle_hashing

        self.rows = rows
        by_ptid = {row["ptid"]: row for row in features}
        self.features = by_ptid
        self.normalization = normalization
        self.paths = [cache_dir / (pickle_hashing(row).decode() + ".pt") for row in rows]
        if any(not path.is_file() for path in self.paths):
            raise RuntimeError("A required frozen Full cache entry is missing")

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, index: int) -> dict:
        import torch

        row = self.rows[index]
        cached = torch.load(self.paths[index], map_location="cpu", weights_only=False)
        sid = row["name"]
        if cached.get("name") != sid:
            raise RuntimeError(f"Cache identity mismatch for {sid}")
        result = {"name": sid}
        for key in ("mri", "fdg", "av45"):
            tensor = cached[key].as_tensor() if hasattr(cached[key], "as_tensor") else cached[key]
            tensor = tensor.detach().float()
            if tuple(tensor.shape) != (1, 160, 192, 160) or not torch.isfinite(tensor).all():
                raise RuntimeError(f"Invalid cached tensor for {sid}/{key}")
            result[key] = tensor
        result["clinical"] = torch.from_numpy(standardized_vector(self.features[sid], self.normalization))
        return result


def new_model():
    return ClinicalRegressionUNet3D(channels=MODEL_CHANNELS)


def seed_all(seed: int) -> None:
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def hardware() -> dict:
    import torch

    result = {
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "python": sys.version,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
    }
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        props = torch.cuda.get_device_properties(0)
        result.update(
            gpu=props.name,
            gpu_uuid=str(getattr(props, "uuid", None)),
            gpu_free_bytes=free,
            gpu_total_bytes=total,
        )
    return result


def state_hash(state: dict) -> str:
    digest = hashlib.sha256()
    for key, tensor in sorted(state.items()):
        digest.update(key.encode())
        digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def rng_state() -> dict:
    import torch

    return {
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def checkpoint_identity(cfg: dict, fold: int) -> dict:
    return {
        "format": 1,
        "experiment": cfg["experiment"],
        "fold": fold,
        "config_sha256": cfg["_config_sha256"],
        "cohort_sha256": cfg["cohort_sha256"],
        "split_manifest_sha256": cfg["split_manifest_sha256"],
        "clinical_features_sha256": cfg["clinical_features_sha256"],
        "model_source_sha256": cfg["model"]["model_source_sha256"],
    }


def save_recovery(path: Path, model, optimizer, scaler, epoch: int, identity: dict) -> None:
    import torch

    state = {
        **identity,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "epoch": epoch,
        **rng_state(),
    }
    temporary = path.with_suffix(".tmp")
    torch.save(state, temporary)
    os.replace(temporary, path)


def restore_recovery(path: Path, model, optimizer, scaler, identity: dict) -> int:
    import torch

    state = torch.load(path, map_location="cpu", weights_only=False)
    if any(state.get(key) != value for key, value in identity.items()):
        raise RuntimeError("Recovery checkpoint identity mismatch")
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scaler.load_state_dict(state["scaler"])
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    torch.set_rng_state(state["torch_rng"])
    torch.cuda.set_rng_state_all(state["cuda_rng"])
    return int(state["epoch"]) + 1


def tracer_condition(tracer: str, batch_size: int, device):
    import torch

    return torch.tensor(TRACER_ONE_HOT[tracer], device=device).expand(batch_size, -1)


def direct_losses(model, batch, device, backward_scaler=None) -> tuple[float, dict[str, bool]]:
    import torch
    import torch.nn.functional as F

    mri = batch["mri"].to(device, non_blocking=True)
    clinical = batch["clinical"].to(device, non_blocking=True)
    total = 0.0
    valid = {}
    for tracer in TRACERS:
        target = batch[tracer].to(device, non_blocking=True)
        valid[tracer] = not bool(torch.all(target == 0))
        if not valid[tracer]:
            continue
        condition = tracer_condition(tracer, mri.shape[0], device)
        with torch.amp.autocast("cuda", enabled=device.type == "cuda"):
            prediction = model(mri, clinical, condition)
            loss = F.mse_loss(prediction.float(), target.float())
        if backward_scaler is not None:
            backward_scaler.scale(loss).backward()
        total += float(loss.detach())
        del prediction, loss, target, condition
    if not any(valid.values()):
        raise RuntimeError(f"Subject has no valid PET target: {batch['name'][0]}")
    return total, valid


def validate(model, loader, device) -> float:
    import torch
    import torch.nn.functional as F

    model.eval()
    losses = []
    with torch.no_grad():
        for batch in loader:
            mri = batch["mri"].to(device)
            clinical = batch["clinical"].to(device)
            total = 0.0
            for tracer in TRACERS:
                target = batch[tracer].to(device)
                if torch.all(target == 0):
                    continue
                condition = tracer_condition(tracer, mri.shape[0], device)
                with torch.amp.autocast("cuda", enabled=False):
                    prediction = torch.clamp(model(mri, clinical, condition).float(), 0, 1)
                    total += float(F.mse_loss(prediction, target.float()))
            losses.append(total)
    return float(np.mean(losses))


def datasets_for_fold(cfg: dict, cohort: list[dict], features: list[dict], fold: int):
    normalization = cfg["fold_normalization"][str(fold)]
    cache_dir = Path(cfg["cache"]["cache_dir"])
    train_rows = [row for row in cohort if int(row["test_fold"]) != fold]
    held_rows = [row for row in cohort if int(row["test_fold"]) == fold]
    if {row["name"] for row in train_rows} & {row["name"] for row in held_rows}:
        raise RuntimeError("Fold overlap")
    return (
        FullCacheDataset(train_rows, features, cache_dir, normalization),
        FullCacheDataset(held_rows, features, cache_dir, normalization),
    )


def command_check_config(args) -> None:
    import torch

    cfg, cohort, features = load_config(args.config.resolve())
    cache = validate_cache(Path(cfg["cache"]["cache_dir"]), cohort)
    sample_ds = FullCacheDataset(
        [cohort[0]], features, Path(cfg["cache"]["cache_dir"]), cfg["fold_normalization"]["1"]
    )
    sample = sample_ds[0]
    result = {
        "status": "PASS",
        "subjects": len(cohort),
        "unique_ptids": len({row["name"] for row in cohort}),
        "fold_counts": cfg["fold_counts"],
        "split_manifest_sha256": cfg["split_manifest_sha256"],
        "cache": cache,
        "sample_ptid": sample["name"],
        "sample_shapes": {key: list(sample[key].shape) for key in ("mri", "fdg", "av45")},
        "clinical_shape": list(sample["clinical"].shape),
        "cached_condition_keys_exposed": False,
        "diagnosis_field_present": any("diagnosis" in row or "Research Group" in row for row in features),
        "torch": torch.__version__,
    }
    if result["diagnosis_field_present"]:
        raise RuntimeError("Forbidden diagnosis field found in clinical features")
    if not args.no_write:
        json_write(Path(cfg["report"]) / "config_check.json", result)
    print(json.dumps(result, ensure_ascii=False))


def command_smoke_test(args) -> None:
    import torch
    import torch.nn.functional as F

    device = torch.device("cuda" if args.cuda else "cpu")
    if args.cuda and not torch.cuda.is_available():
        raise RuntimeError("CUDA smoke test requested but CUDA is unavailable")
    seed_all(20261027)
    model = new_model().to(device).eval()
    mri = torch.rand(1, 1, args.size, args.size, args.size, device=device)
    clinical = torch.rand(1, 8, device=device)
    outputs = {}
    for tracer in TRACERS:
        condition = tracer_condition(tracer, 1, device)
        prediction_a = model(mri, clinical, condition)
        prediction_b = model(mri, clinical, condition)
        if prediction_a.shape != mri.shape or not torch.isfinite(prediction_a).all():
            raise RuntimeError("Synthetic forward output is invalid")
        if not torch.equal(prediction_a, prediction_b):
            raise RuntimeError("Repeated evaluation forward is not deterministic")
        outputs[tracer] = float(prediction_a.mean())
    model.train()
    target = torch.rand_like(mri)
    prediction = model(mri, clinical, tracer_condition("fdg", 1, device))
    loss = F.mse_loss(prediction, target)
    loss.backward()
    if not all(parameter.grad is None or torch.isfinite(parameter.grad).all() for parameter in model.parameters()):
        raise RuntimeError("Synthetic backward produced non-finite gradients")

    with tempfile.TemporaryDirectory() as folder:
        checkpoint = Path(folder) / "roundtrip.pt"
        torch.save(model.state_dict(), checkpoint)
        restored = new_model()
        restored.load_state_dict(torch.load(checkpoint, map_location="cpu", weights_only=True))
        if state_hash(restored.state_dict()) != state_hash(model.state_dict()):
            raise RuntimeError("Checkpoint roundtrip changed model state")

    result = {
        "status": "PASS",
        "device": str(device),
        "synthetic_shape": list(mri.shape),
        "outputs": outputs,
        "loss": float(loss.detach()),
        "parameters": parameter_count(model),
        "direct_pet_regression": True,
        "biomedclip": False,
        "attention": False,
        "time_or_flow": False,
        "checkpoint_roundtrip": "PASS",
    }
    if args.full_sample:
        if not args.config or device.type != "cuda":
            raise RuntimeError("--full-sample requires --config and --cuda")
        cfg, cohort, features = load_config(args.config.resolve())
        dataset = FullCacheDataset(
            [cohort[0]], features, Path(cfg["cache"]["cache_dir"]), cfg["fold_normalization"]["1"]
        )
        sample = dataset[0]
        batch = {
            key: value.unsqueeze(0) if isinstance(value, torch.Tensor) else [value]
            for key, value in sample.items()
        }
        model = new_model().cuda().train()
        torch.cuda.reset_peak_memory_stats()
        model.zero_grad(set_to_none=True)
        full_loss, valid = direct_losses(model, batch, torch.device("cuda"), torch.amp.GradScaler("cuda"))
        torch.cuda.synchronize()
        result.update(
            full_sample="PASS_NO_OPTIMIZER_STEP",
            full_sample_ptid=sample["name"],
            full_sample_loss=full_loss,
            full_sample_valid=valid,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_reserved_bytes=torch.cuda.max_memory_reserved(),
        )
        json_write(Path(cfg["report"]) / "cuda_preflight.json", result)
    print(json.dumps(result, ensure_ascii=False))


def command_train(args) -> None:
    import torch
    from torch.utils.data import DataLoader

    cfg, cohort, features = load_config(args.config.resolve())
    if args.fold not in (1, 2):
        raise ValueError("fold must be 1 or 2")
    if not torch.cuda.is_available():
        raise RuntimeError("Formal training requires CUDA")
    if shutil.disk_usage(Path(cfg["assets"])).free < cfg["minimum_output_free_bytes"]:
        raise RuntimeError("Less than 50 GiB free at the isolated output path")
    validate_cache(Path(cfg["cache"]["cache_dir"]), cohort)
    seed_all(cfg["seed"])
    train_ds, held_ds = datasets_for_fold(cfg, cohort, features, args.fold)
    train_loader = DataLoader(train_ds, batch_size=1, shuffle=True, num_workers=0, pin_memory=True)
    held_loader = DataLoader(held_ds, batch_size=1, shuffle=False, num_workers=0, pin_memory=True)

    run_dir = Path(cfg["assets"]) / "formal" / f"fold{args.fold}"
    recovery = run_dir / "recovery.pt"
    if args.resume:
        if args.resume.resolve() != recovery.resolve() or not run_dir.is_dir():
            raise RuntimeError("Resume must use this fold's isolated recovery.pt")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)
    device = torch.device("cuda")
    model = new_model().to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    scaler = torch.amp.GradScaler("cuda")
    identity = checkpoint_identity(cfg, args.fold)
    start_epoch = restore_recovery(args.resume, model, optimizer, scaler, identity) if args.resume else 0
    json_write(
        run_dir / ("resume_start.json" if args.resume else "start.json"),
        {
            **identity,
            "hardware": hardware(),
            "train_subjects": len(train_ds),
            "held_out_subjects": len(held_ds),
            "start_epoch_zero_based": start_epoch,
            "initial_model_sha256": state_hash(model.state_dict()),
            "parameters": parameter_count(model),
        },
    )

    trace_path = run_dir / "training_trace.jsonl"
    epochs_path = run_dir / "epochs.jsonl"
    for epoch in range(start_epoch, cfg["epochs"]):
        model.train()
        losses, order = [], []
        started = time.monotonic()
        with trace_path.open("a") as trace:
            for iteration, batch in enumerate(train_loader, 1):
                optimizer.zero_grad(set_to_none=True)
                loss, valid = direct_losses(model, batch, device, scaler)
                scaler.step(optimizer)
                scaler.update()
                losses.append(loss)
                sid = batch["name"][0]
                order.append(sid)
                if iteration <= 5 or iteration % 100 == 0 or iteration == len(train_loader):
                    event = {
                        "epoch_zero_based": epoch,
                        "iteration": iteration,
                        "ptid": sid,
                        "loss": loss,
                        "has_fdg": valid["fdg"],
                        "has_av45": valid["av45"],
                        "amp_scale": scaler.get_scale(),
                        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                    }
                    trace.write(json.dumps(event) + "\n")
                    trace.flush()
                    print(json.dumps(event), flush=True)

        epoch_number = epoch + 1
        held_loss = validate(model, held_loader, device) if epoch_number % cfg["val_interval"] == 0 else None
        should_snapshot = epoch_number % cfg["val_interval"] == 0 or epoch_number in (
            cfg["primary_epoch"], cfg["secondary_epoch"]
        )
        if should_snapshot:
            checkpoint = run_dir / f"checkpoint_epoch{epoch_number}.pt"
            torch.save(
                {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "epoch": epoch, **identity},
                checkpoint,
            )
            json_write(
                checkpoint.with_suffix(".json"),
                {
                    **identity,
                    "epoch_one_based": epoch_number,
                    "checkpoint_sha256": sha256(checkpoint),
                    "model_sha256": state_hash(model.state_dict()),
                    "fixed_endpoint": epoch_number in (cfg["primary_epoch"], cfg["secondary_epoch"]),
                    "validation_used_for_selection": False,
                },
            )
        save_recovery(recovery, model, optimizer, scaler, epoch, identity)
        epoch_event = {
            "epoch_zero_based": epoch,
            "epoch_one_based": epoch_number,
            "train_loss": float(np.mean(losses)),
            "held_out_monitored_loss": held_loss,
            "seconds": time.monotonic() - started,
            "sample_order_sha256": hashlib.sha256("\n".join(order).encode()).hexdigest(),
        }
        with epochs_path.open("a") as log:
            log.write(json.dumps(epoch_event) + "\n")
        print(json.dumps(epoch_event), flush=True)
    json_write(
        run_dir / "complete.json",
        {
            **identity,
            "epochs": cfg["epochs"],
            "primary_checkpoint": str(run_dir / f"checkpoint_epoch{cfg['primary_epoch']}.pt"),
            "secondary_checkpoint": str(run_dir / f"checkpoint_epoch{cfg['secondary_epoch']}.pt"),
            "status": "TRAINING_COMPLETE_NOT_INFERRED",
        },
    )


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

    cfg, cohort, features = load_config(args.config.resolve())
    if args.fold not in (1, 2) or args.epoch not in (cfg["primary_epoch"], cfg["secondary_epoch"]):
        raise ValueError("Only fold 1/2 and preregistered endpoint epochs may be inferred")
    if not torch.cuda.is_available():
        raise RuntimeError("Inference requires CUDA")
    _, held_ds = datasets_for_fold(cfg, cohort, features, args.fold)
    loader = DataLoader(held_ds, batch_size=1, shuffle=False, num_workers=0, pin_memory=True)
    checkpoint = Path(cfg["assets"]) / "formal" / f"fold{args.fold}" / f"checkpoint_epoch{args.epoch}.pt"
    receipt = checkpoint.with_suffix(".json")
    if not checkpoint.is_file() or not receipt.is_file():
        raise RuntimeError("Missing fixed-endpoint checkpoint or receipt")
    if sha256(checkpoint) != json.loads(receipt.read_text())["checkpoint_sha256"]:
        raise RuntimeError("Checkpoint hash mismatch")
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = new_model().cuda().eval()
    model.load_state_dict(state["model"])
    output = Path(cfg["assets"]) / "oof" / f"epoch{args.epoch}" / f"fold{args.fold}"
    output.mkdir(parents=True, exist_ok=False)
    ssim = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
    psnr = PSNRMetric(max_val=1.0)
    rows = []
    with torch.no_grad():
        for batch in loader:
            sid = batch["name"][0]
            mri = batch["mri"].cuda(non_blocking=True)
            clinical = batch["clinical"].cuda(non_blocking=True)
            for tracer in TRACERS:
                target = batch[tracer].cuda(non_blocking=True)
                if torch.all(target == 0):
                    continue
                prediction = torch.clamp(
                    model(mri, clinical, tracer_condition(tracer, 1, mri.device)).float(), 0, 1
                )
                path = output / f"generated_{tracer}_{sid}.nii.gz"
                nib.save(nib.Nifti1Image(prediction.squeeze().cpu().numpy(), np.eye(4)), path)
                row = {
                    "ptid": sid,
                    "tracer": tracer,
                    "fold": args.fold,
                    "epoch": args.epoch,
                    "ssim": float(ssim(prediction, target).mean()),
                    "psnr": float(psnr(prediction, target).mean()),
                    "mse": float(F.mse_loss(prediction, target.float())),
                    "mae": float(F.l1_loss(prediction, target.float())),
                    "prediction": str(path),
                    "prediction_sha256": sha256(path),
                    "checkpoint_sha256": sha256(checkpoint),
                }
                rows.append(row)
                print(json.dumps(row), flush=True)
    expected = cfg["expected_effective_by_fold"][str(args.fold)]
    counts = {tracer: sum(row["tracer"] == tracer for row in rows) for tracer in TRACERS}
    if counts != expected:
        raise RuntimeError(f"OOF effective counts differ from Full: {counts} != {expected}")
    csv_write(output / "metrics.csv", rows)
    json_write(
        output / "complete.json",
        {
            "fold": args.fold,
            "epoch": args.epoch,
            "held_out_subjects": len(held_ds),
            "metric_rows": len(rows),
            "counts": counts,
            "metrics_sha256": sha256(output / "metrics.csv"),
            "checkpoint_sha256": sha256(checkpoint),
            "postprocessing": "clamp [0,1] only; no target-derived calibration",
        },
    )


def command_summarize(args) -> None:
    cfg, _, _ = load_config(args.config.resolve())
    out = Path(cfg["report"]) / "oof_summary"
    out.mkdir(parents=True, exist_ok=False)
    rows = []
    for epoch in (cfg["primary_epoch"], cfg["secondary_epoch"]):
        for fold in (1, 2):
            folder = Path(cfg["assets"]) / "oof" / f"epoch{epoch}" / f"fold{fold}"
            receipt = json.loads((folder / "complete.json").read_text())
            if sha256(folder / "metrics.csv") != receipt["metrics_sha256"]:
                raise RuntimeError(f"Metrics hash mismatch: epoch {epoch}, fold {fold}")
            rows.extend(read_csv(folder / "metrics.csv"))
    identities = [(row["ptid"], row["tracer"], int(row["epoch"])) for row in rows]
    if len(identities) != len(set(identities)):
        raise RuntimeError("Duplicate OOF subject/tracer/endpoint identity")
    expected_rows = sum(cfg["expected_effective"].values()) * 2
    if len(rows) != expected_rows:
        raise RuntimeError(f"Expected {expected_rows} OOF metric rows, got {len(rows)}")
    csv_write(out / "per_subject_metrics.csv", rows)

    summaries = []
    by_fold = []
    metrics = ("ssim", "psnr", "mse", "mae")
    for epoch in (cfg["primary_epoch"], cfg["secondary_epoch"]):
        for tracer in TRACERS:
            group = [row for row in rows if int(row["epoch"]) == epoch and row["tracer"] == tracer]
            summary = {
                "endpoint": "primary" if epoch == cfg["primary_epoch"] else "secondary",
                "epoch": epoch,
                "tracer": tracer,
                "n": len(group),
            }
            for metric in metrics:
                values = np.asarray([float(row[metric]) for row in group])
                summary[metric] = float(values.mean())
                summary[metric + "_sd"] = float(values.std(ddof=1))
            summaries.append(summary)
            for fold in (1, 2):
                fold_group = [row for row in group if int(row["fold"]) == fold]
                item = {"epoch": epoch, "fold": fold, "tracer": tracer, "n": len(fold_group)}
                for metric in metrics:
                    item[metric] = float(np.mean([float(row[metric]) for row in fold_group]))
                by_fold.append(item)
    csv_write(out / "overall_summary.csv", summaries)
    csv_write(out / "by_fold_summary.csv", by_fold)
    json_write(
        out / "completion.json",
        {
            "status": "COMPLETE_TWO_FOLD_OOF_CLINICAL_REGRESSION_UNET",
            "primary_epoch": cfg["primary_epoch"],
            "secondary_epoch": cfg["secondary_epoch"],
            "per_subject_sha256": sha256(out / "per_subject_metrics.csv"),
            "overall_sha256": sha256(out / "overall_summary.csv"),
            "by_fold_sha256": sha256(out / "by_fold_summary.csv"),
        },
    )


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--full-config", type=Path, required=True)
    prepare.add_argument("--clinical-table", type=Path, required=True)
    prepare.add_argument("--cache-dir", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--assets", type=Path, required=True)
    check = sub.add_parser("check-config")
    check.add_argument("--config", type=Path, required=True)
    check.add_argument("--no-write", action="store_true")
    smoke = sub.add_parser("smoke-test")
    smoke.add_argument("--size", type=int, default=32)
    smoke.add_argument("--cuda", action="store_true")
    smoke.add_argument("--full-sample", action="store_true")
    smoke.add_argument("--config", type=Path)
    train = sub.add_parser("train")
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--fold", type=int, required=True)
    train.add_argument("--resume", type=Path)
    infer = sub.add_parser("infer")
    infer.add_argument("--config", type=Path, required=True)
    infer.add_argument("--fold", type=int, required=True)
    infer.add_argument("--epoch", type=int, required=True)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--config", type=Path, required=True)
    return parser


def main() -> None:
    args = parser().parse_args()
    actions = {
        "prepare": command_prepare,
        "check-config": command_check_config,
        "smoke-test": command_smoke_test,
        "train": command_train,
        "infer": command_infer,
        "summarize": command_summarize,
    }
    actions[args.action](args)


if __name__ == "__main__":
    main()
