"""Frozen Full data/cache and GPU receipt helpers for the DIReCT Single baseline.

Copied from the isolated SwinUNETR baseline; changes belong here, never upstream.
"""
from __future__ import annotations
import csv
import hashlib
import json
import os
import random
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
TRACERS = ("FDG", "AV45")
SHAPE = (160, 192, 160)
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


def state_hash(state: dict) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


