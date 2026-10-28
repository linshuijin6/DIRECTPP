#!/usr/bin/env python3
"""Frozen manifest and imaging input handling for Stage 4D classification."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import nibabel as nib
import numpy as np
import torch
from torch.utils.data import Dataset


REPO_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TASK_SUBJECTS = {"ad_cn": 469, "mci_cn": 740, "lmci_emci": 436}
CONDITION_CHANNELS = {"mri": 1, "mri_real": 3, "mri_full": 3, "mri_ot": 3}
SYN_CONDITIONS = {"mri_full": "full", "mri_ot": "ot"}


class ProtocolError(RuntimeError):
    pass


def absolute(path: str | Path) -> Path:
    path = Path(path)
    return path if path.is_absolute() else REPO_ROOT / path


def sha256_file(path: str | Path, chunk_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open() as handle:
        return json.load(handle)


def read_csv(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open(newline="") as handle:
        return list(csv.DictReader(handle))


def atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_torch_save(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    os.close(fd)
    try:
        torch.save(payload, tmp)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def write_csv(path: Path, rows: Iterable[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _find_receipt_output(receipt: dict[str, Any], filename: str) -> dict[str, Any] | None:
    """Find a receipt entry for filename without accepting an unbound path."""
    stack: list[Any] = [receipt]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                if Path(str(key)).name == filename and isinstance(value, dict):
                    return value
                stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    return None


def _receipt_is_complete(receipt: dict[str, Any]) -> bool:
    status = str(receipt.get("status", "")).upper()
    if any(token in status for token in ("FAIL", "BLOCK", "PARTIAL", "RUNNING")):
        return False
    return "COMPLETE" in status or status in {"PASS", "PASS_COMPLETE"}


def _validate_bound_output(receipt: dict[str, Any], path: Path, expected_rows: int | None = None) -> str:
    if not path.is_file():
        raise ProtocolError(f"required Stage 4C-4 output is missing: {path}")
    entry = _find_receipt_output(receipt, path.name)
    if not entry or not entry.get("sha256"):
        raise ProtocolError(f"Stage 4C-4 receipt does not bind {path.name} to a SHA-256")
    actual = sha256_file(path)
    if actual != entry["sha256"]:
        raise ProtocolError(f"Stage 4C-4 output SHA mismatch: {path.name}")
    if expected_rows is not None:
        rows = read_csv(path)
        if len(rows) != expected_rows:
            raise ProtocolError(f"{path.name}: expected {expected_rows} rows, found {len(rows)}")
        if entry.get("rows") is not None and int(entry["rows"]) != expected_rows:
            raise ProtocolError(f"{path.name}: receipt row count is not {expected_rows}")
    return actual


@dataclass(frozen=True)
class InputRecord:
    task: str
    outer_fold: int
    ptid: str
    diagnosis: str
    label: int
    generator_fold: int
    role: str
    e1_cache_path: Path
    e1_cache_sha256: str
    mri_key: str
    real_fdg_key: str
    real_av45_key: str
    fdg_path: Path | None = None
    fdg_sha256: str = ""
    av45_path: Path | None = None
    av45_sha256: str = ""

    def identity(self) -> tuple[str, int, str]:
        return self.task, self.outer_fold, self.ptid


class ProtocolInputs:
    def __init__(self, config_path: str | Path):
        self.config_path = absolute(config_path)
        self.config = read_json(self.config_path)
        self.manifest_receipt_path = absolute(self.config["manifest_receipt"])
        self.manifest_receipt = read_json(self.manifest_receipt_path)
        self.manifests: dict[str, list[dict[str, str]]] = {}
        self.manifest_hashes: dict[str, str] = {}
        self.asset_rows: dict[tuple[str, int, str], dict[str, str]] | None = None
        self.stage4c4_hashes: dict[str, str] = {}
        self._verified_synthetic: set[tuple[str, str]] = set()
        self._verified_e1: set[tuple[str, str]] = set()
        self._validate_frozen_manifests()

    def _validate_frozen_manifests(self) -> None:
        outputs = self.manifest_receipt.get("outputs", {})
        for task, raw_path in self.config["manifests"].items():
            path = absolute(raw_path)
            expected = outputs.get(path.name)
            if not expected or not expected.get("sha256"):
                raise ProtocolError(f"4B receipt does not bind frozen manifest: {path.name}")
            actual = sha256_file(path)
            if actual != expected["sha256"]:
                raise ProtocolError(f"frozen manifest SHA mismatch: {path}")
            rows = read_csv(path)
            if len(rows) != int(expected["rows"]):
                raise ProtocolError(f"frozen manifest row mismatch: {path}")
            if len(rows) != 2 * EXPECTED_TASK_SUBJECTS[task]:
                raise ProtocolError(f"unexpected task population in {path}")
            self.manifests[task] = rows
            self.manifest_hashes[task] = actual

    def _load_stage4c4(self) -> None:
        if self.asset_rows is not None:
            return
        spec = self.config["stage4c4"]
        receipt_path = absolute(spec["receipt"])
        if not receipt_path.is_file():
            raise ProtocolError("Stage 4C-4 receipt is not available; synthetic-PET fits remain blocked")
        receipt = read_json(receipt_path)
        if not _receipt_is_complete(receipt):
            raise ProtocolError(f"Stage 4C-4 receipt is not COMPLETE: status={receipt.get('status')!r}")
        prediction_path = absolute(spec["prediction_manifest"])
        asset_path = absolute(spec["classification_asset_index"])
        pred_sha = _validate_bound_output(receipt, prediction_path, int(spec["expected_predictions"]))
        asset_sha = _validate_bound_output(receipt, asset_path)
        asset_rows = read_csv(asset_path)
        required = {
            "task", "outer_fold", "ptid", "diagnosis", "label", "generator_fold",
            "outer_role", "e1_cache_path", "e1_cache_sha256",
            "full_fdg_path", "full_fdg_sha256", "full_av45_path", "full_av45_sha256",
            "ot_fdg_path", "ot_fdg_sha256", "ot_av45_path", "ot_av45_sha256",
        }
        if not asset_rows:
            raise ProtocolError("Stage 4C-4 classification asset index is empty")
        missing = required - set(asset_rows[0])
        if missing:
            raise ProtocolError(f"Stage 4C-4 classification asset index lacks columns: {sorted(missing)}")
        keyed: dict[tuple[str, int, str], dict[str, str]] = {}
        for row in asset_rows:
            key = (row["task"], int(row["outer_fold"]), row["ptid"])
            if key in keyed:
                raise ProtocolError(f"duplicate Stage 4C-4 asset row: {key}")
            keyed[key] = row
        expected_keys = {
            (task, int(row["outer_fold"]), row["ptid"])
            for task, rows in self.manifests.items() for row in rows
        }
        if set(keyed) != expected_keys:
            missing_keys = expected_keys - set(keyed)
            extra_keys = set(keyed) - expected_keys
            raise ProtocolError(
                f"Stage 4C-4 asset index identity mismatch: missing={len(missing_keys)}, extra={len(extra_keys)}"
            )
        self.asset_rows = keyed
        self.stage4c4_hashes = {
            "receipt": sha256_file(receipt_path),
            "prediction_manifest": pred_sha,
            "classification_asset_index": asset_sha,
        }

    @staticmethod
    def _validate_manifest_row(row: dict[str, str], task: str, outer_fold: int) -> None:
        if row["task"] != task or int(row["outer_fold"]) != outer_fold:
            raise ProtocolError("frozen manifest task/fold identity mismatch")
        generator_fold = int(row["generator_fold"])
        expected_role = "outer_test" if generator_fold == outer_fold else "outer_train"
        if row["outer_role"] != expected_role:
            raise ProtocolError(f"generator-anchored role mismatch for {row['ptid']}")
        if expected_role == "outer_test" and row["inner_role"] != "outer_test":
            raise ProtocolError(f"outer-test subject has non-test inner role: {row['ptid']}")
        if expected_role == "outer_train" and row["inner_role"] not in {"inner_train", "inner_validation"}:
            raise ProtocolError(f"outer-train subject has invalid inner role: {row['ptid']}")

    def records(self, task: str, outer_fold: int, condition: str) -> list[InputRecord]:
        if task not in self.manifests:
            raise ProtocolError(f"unknown task: {task}")
        if outer_fold not in (1, 2):
            raise ProtocolError(f"unknown outer fold: {outer_fold}")
        if condition not in CONDITION_CHANNELS:
            raise ProtocolError(f"unknown condition: {condition}")
        if condition in SYN_CONDITIONS:
            self._load_stage4c4()

        selected = [r for r in self.manifests[task] if int(r["outer_fold"]) == outer_fold]
        if len(selected) != EXPECTED_TASK_SUBJECTS[task]:
            raise ProtocolError(f"frozen task/fold population mismatch: {task}/fold{outer_fold}")
        records: list[InputRecord] = []
        for row in selected:
            self._validate_manifest_row(row, task, outer_fold)
            base = dict(
                task=task,
                outer_fold=outer_fold,
                ptid=row["ptid"],
                diagnosis=row["diagnosis"],
                label=int(row["label"]),
                generator_fold=int(row["generator_fold"]),
                role=row["inner_role"],
                e1_cache_path=Path(row["e1_cache_path"]),
                e1_cache_sha256=row["e1_cache_sha256"],
                mri_key=row["mri_array_key"],
                real_fdg_key=row["real_fdg_array_key"],
                real_av45_key=row["real_av45_array_key"],
            )
            if condition not in SYN_CONDITIONS:
                records.append(InputRecord(**base))
                continue
            assert self.asset_rows is not None
            asset = self.asset_rows[(task, outer_fold, row["ptid"])]
            for key in ("diagnosis", "label", "generator_fold", "outer_role", "e1_cache_path", "e1_cache_sha256"):
                if str(asset[key]) != str(row[key]):
                    raise ProtocolError(f"Stage 4C-4/frozen-manifest mismatch for {row['ptid']}: {key}")
            model = SYN_CONDITIONS[condition]
            fdg_path = Path(asset[f"{model}_fdg_path"])
            av45_path = Path(asset[f"{model}_av45_path"])
            fdg_sha = asset[f"{model}_fdg_sha256"]
            av45_sha = asset[f"{model}_av45_sha256"]
            if not fdg_sha or not av45_sha:
                raise ProtocolError(f"missing synthetic prediction SHA for {row['ptid']}")
            if row["outer_role"] == "outer_test":
                if str(fdg_path) != row[f"{model}_fdg_existing_oof_path"] or fdg_sha != row[f"{model}_fdg_existing_oof_sha256"]:
                    raise ProtocolError(f"outer-test FDG is not frozen G_f OOF for {row['ptid']}")
                if str(av45_path) != row[f"{model}_av45_existing_oof_path"] or av45_sha != row[f"{model}_av45_existing_oof_sha256"]:
                    raise ProtocolError(f"outer-test AV45 is not frozen G_f OOF for {row['ptid']}")
            else:
                forbidden = {
                    row[f"{model}_fdg_existing_oof_path"], row[f"{model}_av45_existing_oof_path"],
                }
                if str(fdg_path) in forbidden or str(av45_path) in forbidden:
                    raise ProtocolError(f"cross-OOF was selected for outer-train subject {row['ptid']}")
            records.append(InputRecord(**base, fdg_path=fdg_path, fdg_sha256=fdg_sha,
                                       av45_path=av45_path, av45_sha256=av45_sha))

        identities = [r.ptid for r in records]
        if len(set(identities)) != len(identities):
            raise ProtocolError(f"duplicate subject in task/fold: {task}/fold{outer_fold}")
        for role in ("inner_train", "inner_validation", "outer_test"):
            labels = {r.label for r in records if r.role == role}
            if labels != {0, 1}:
                raise ProtocolError(f"{task}/fold{outer_fold}/{role} lacks both classes")
        return records

    def verify_files(self, records: list[InputRecord], condition: str, full_sha: bool) -> dict[str, int]:
        checked = 0
        sha_checked = 0
        e1_sha_checked = 0
        for record in records:
            if not record.e1_cache_path.is_file():
                raise ProtocolError(f"missing E1 cache: {record.e1_cache_path}")
            checked += 1
            if full_sha:
                key = (str(record.e1_cache_path), record.e1_cache_sha256)
                if key not in self._verified_e1:
                    if sha256_file(record.e1_cache_path) != record.e1_cache_sha256:
                        raise ProtocolError(f"E1 cache SHA mismatch: {record.e1_cache_path}")
                    self._verified_e1.add(key)
                    e1_sha_checked += 1
            if condition in SYN_CONDITIONS:
                for path, expected in ((record.fdg_path, record.fdg_sha256), (record.av45_path, record.av45_sha256)):
                    assert path is not None
                    if not path.is_file():
                        raise ProtocolError(f"missing synthetic PET: {path}")
                    checked += 1
                    if full_sha:
                        key = (str(path), expected)
                        if key not in self._verified_synthetic:
                            if sha256_file(path) != expected:
                                raise ProtocolError(f"synthetic PET SHA mismatch: {path}")
                            self._verified_synthetic.add(key)
                            sha_checked += 1
        return {"files_present": checked, "e1_sha_verified": e1_sha_checked,
                "synthetic_sha_verified": sha_checked}


def _validate_array(array: np.ndarray, name: str, expected_shape: tuple[int, int, int]) -> np.ndarray:
    array = np.asarray(array, dtype=np.float32)
    if array.shape != expected_shape:
        raise ProtocolError(f"{name} shape {array.shape} != {expected_shape}")
    if not np.isfinite(array).all():
        raise ProtocolError(f"{name} contains non-finite values")
    minimum, maximum = float(array.min()), float(array.max())
    if minimum < -1e-6 or maximum > 1.000001:
        raise ProtocolError(f"{name} outside normalized [0,1] range: [{minimum}, {maximum}]")
    return array


class ClassificationDataset(Dataset):
    def __init__(self, records: list[InputRecord], condition: str, expected_shape: tuple[int, int, int],
                 cache_in_memory: bool = True):
        self.records = records
        self.condition = condition
        self.expected_shape = expected_shape
        self.cache_in_memory = cache_in_memory
        self._cache: dict[int, dict[str, Any]] = {}

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> dict[str, Any]:
        if index in self._cache:
            return self._cache[index]
        record = self.records[index]
        with np.load(record.e1_cache_path, allow_pickle=False) as cached:
            mri = _validate_array(cached[record.mri_key], f"MRI/{record.ptid}", self.expected_shape)
            arrays = [mri]
            if self.condition == "mri_real":
                arrays.extend([
                    _validate_array(cached[record.real_fdg_key], f"Real-FDG/{record.ptid}", self.expected_shape),
                    _validate_array(cached[record.real_av45_key], f"Real-AV45/{record.ptid}", self.expected_shape),
                ])
        if self.condition in SYN_CONDITIONS:
            assert record.fdg_path is not None and record.av45_path is not None
            fdg = _validate_array(np.asanyarray(nib.load(record.fdg_path).dataobj),
                                  f"Syn-FDG/{record.ptid}", self.expected_shape)
            av45 = _validate_array(np.asanyarray(nib.load(record.av45_path).dataobj),
                                   f"Syn-AV45/{record.ptid}", self.expected_shape)
            arrays.extend([fdg, av45])
        image = np.stack(arrays, axis=0).astype(np.float32, copy=False)
        result = {
            "image": torch.from_numpy(image),
            "label": torch.tensor(record.label, dtype=torch.long),
            "ptid": record.ptid,
            "diagnosis": record.diagnosis,
        }
        if self.cache_in_memory:
            self._cache[index] = result
        return result


def record_rows(records: list[InputRecord], condition: str) -> list[dict[str, Any]]:
    return [{
        "task": r.task,
        "outer_fold": r.outer_fold,
        "ptid": r.ptid,
        "diagnosis": r.diagnosis,
        "label": r.label,
        "generator_fold": r.generator_fold,
        "role": r.role,
        "condition": condition,
        "e1_cache_path": str(r.e1_cache_path),
        "e1_cache_sha256": r.e1_cache_sha256,
        "mri_array_key": r.mri_key,
        "real_fdg_array_key": r.real_fdg_key,
        "real_av45_array_key": r.real_av45_key,
        "fdg_path": str(r.fdg_path or ""),
        "fdg_sha256": r.fdg_sha256,
        "av45_path": str(r.av45_path or ""),
        "av45_sha256": r.av45_sha256,
    } for r in records]
