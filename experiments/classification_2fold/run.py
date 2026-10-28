#!/usr/bin/env python3
"""Generator-anchored 2-fold DenseNet121 classification for Stage 4D.

Formal training is fail-closed and requires an explicit authorization token.  MRI
and MRI+Real can be run before Stage 4C-4 completes; synthetic-PET conditions
require the completed, SHA-bound Stage 4C-4 receipt and classification index.
"""

from __future__ import annotations

import argparse
import gc
import json
import random
import socket
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
import torch
from monai.networks.nets import DenseNet121
from sklearn.metrics import confusion_matrix, roc_auc_score, roc_curve
from torch.utils.data import DataLoader

from protocol import (
    CONDITION_CHANNELS,
    ClassificationDataset,
    InputRecord,
    ProtocolError,
    ProtocolInputs,
    atomic_json,
    atomic_torch_save,
    record_rows,
    sha256_file,
    write_csv,
)


DEFAULT_CONFIG = Path(__file__).with_name("config.json")
FORMAL_AUTHORIZATION = "RUN_STAGE_4D_24_FITS"
INPUT_FIELDS = [
    "task", "outer_fold", "ptid", "diagnosis", "label", "generator_fold", "role", "condition",
    "e1_cache_path", "e1_cache_sha256", "mri_array_key", "real_fdg_array_key", "real_av45_array_key",
    "fdg_path", "fdg_sha256", "av45_path", "av45_sha256",
]
PREDICTION_FIELDS = ["ptid", "diagnosis", "label", "probability", "prediction", "threshold", "role"]


def set_determinism(seed: int, deterministic: bool) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = deterministic
    torch.use_deterministic_algorithms(deterministic, warn_only=True)


def fit_seed(config: dict[str, Any], task: str, outer_fold: int) -> int:
    # Condition-independent by design: Full and OT share initialization/shuffle rules.
    return int(config["seed"]) + config["tasks"].index(task) * 100 + outer_fold


def make_model(condition: str, device: torch.device) -> torch.nn.Module:
    return DenseNet121(
        spatial_dims=3,
        in_channels=CONDITION_CHANNELS[condition],
        out_channels=2,
    ).to(device)


def make_loader(dataset: ClassificationDataset, training: dict[str, Any],
                shuffle: bool, seed: int) -> DataLoader:
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=int(training["batch_size"]),
        shuffle=shuffle,
        num_workers=int(training["num_workers"]),
        pin_memory=torch.cuda.is_available(),
        persistent_workers=int(training["num_workers"]) > 0,
        generator=generator,
    )


def infer(model: torch.nn.Module, loader: DataLoader, device: torch.device, amp: bool) -> list[dict[str, Any]]:
    model.eval()
    rows: list[dict[str, Any]] = []
    with torch.no_grad():
        for batch in loader:
            images = batch["image"].to(device, non_blocking=True)
            with torch.amp.autocast("cuda", enabled=amp):
                logits = model(images)
            probabilities = torch.softmax(logits.float(), dim=1)[:, 1].cpu().numpy()
            labels = batch["label"].cpu().numpy()
            for i, probability in enumerate(probabilities):
                rows.append({
                    "ptid": batch["ptid"][i],
                    "diagnosis": batch["diagnosis"][i],
                    "label": int(labels[i]),
                    "probability": float(probability),
                })
    return rows


def select_threshold(labels: np.ndarray, probabilities: np.ndarray) -> float:
    fpr, tpr, thresholds = roc_curve(labels, probabilities)
    finite = np.isfinite(thresholds)
    fpr, tpr, thresholds = fpr[finite], tpr[finite], thresholds[finite]
    scores = tpr - fpr
    best = np.flatnonzero(np.isclose(scores, scores.max(), atol=1e-12, rtol=0))
    candidates = sorted((float(thresholds[i]) for i in best), key=lambda x: (abs(x - 0.5), x))
    return candidates[0]


def metric_values(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = (probabilities >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(labels, predictions, labels=[0, 1]).ravel()
    return {
        "auc": float(roc_auc_score(labels, probabilities)),
        "accuracy": float((tp + tn) / (tp + tn + fp + fn)),
        "sensitivity": float(tp / (tp + fn)),
        "specificity": float(tn / (tn + fp)),
        "balanced_accuracy": float(0.5 * (tp / (tp + fn) + tn / (tn + fp))),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def stratified_bootstrap_ci(labels: np.ndarray, probabilities: np.ndarray, threshold: float,
                            replicates: int, seed: int) -> dict[str, list[float]]:
    rng = np.random.default_rng(seed)
    by_class = [np.flatnonzero(labels == label) for label in (0, 1)]
    values: dict[str, list[float]] = {k: [] for k in
        ("auc", "accuracy", "sensitivity", "specificity", "balanced_accuracy")}
    for _ in range(replicates):
        sample = np.concatenate([rng.choice(indices, size=len(indices), replace=True) for indices in by_class])
        metrics = metric_values(labels[sample], probabilities[sample], threshold)
        for key in values:
            values[key].append(float(metrics[key]))
    return {key: [float(np.quantile(v, 0.025)), float(np.quantile(v, 0.975))] for key, v in values.items()}


def split_records(records: list[InputRecord]) -> tuple[list[InputRecord], list[InputRecord], list[InputRecord]]:
    train = [r for r in records if r.role == "inner_train"]
    validation = [r for r in records if r.role == "inner_validation"]
    test = [r for r in records if r.role == "outer_test"]
    if not train or not validation or not test:
        raise ProtocolError("frozen inner_train/inner_validation/outer_test split is incomplete")
    return train, validation, test


def identity_payload(inputs: ProtocolInputs, task: str, outer_fold: int, condition: str,
                     seed: int) -> dict[str, Any]:
    payload = {
        "protocol_version": inputs.config["protocol_version"],
        "runner_sha256": sha256_file(Path(__file__)),
        "protocol_code_sha256": sha256_file(Path(__file__).with_name("protocol.py")),
        "config_path": str(inputs.config_path),
        "config_sha256": sha256_file(inputs.config_path),
        "manifest_sha256": inputs.manifest_hashes[task],
        "manifest_receipt_sha256": sha256_file(inputs.manifest_receipt_path),
        "task": task,
        "outer_fold": outer_fold,
        "condition": condition,
        "seed": seed,
    }
    if condition in {"mri_full", "mri_ot"}:
        payload["stage4c4"] = inputs.stage4c4_hashes
    return payload


def _completed_matches(path: Path, identity: dict[str, Any]) -> bool:
    if not path.is_file():
        return False
    try:
        complete = json.loads(path.read_text())
    except Exception:
        return False
    return complete.get("identity") == identity and complete.get("status") == "COMPLETE"


def run_fit(inputs: ProtocolInputs, task: str, outer_fold: int, condition: str,
            output_root: Path, resume: bool, verify_asset_sha: bool) -> dict[str, Any]:
    config = inputs.config
    training = config["training"]
    seed = fit_seed(config, task, outer_fold)
    records = inputs.records(task, outer_fold, condition)
    checks = inputs.verify_files(records, condition, verify_asset_sha)
    train_records, validation_records, test_records = split_records(records)
    identity = identity_payload(inputs, task, outer_fold, condition, seed)
    fit_dir = output_root / task / f"outer_fold{outer_fold}" / condition
    complete_path = fit_dir / "complete.json"
    if _completed_matches(complete_path, identity):
        return {"status": "SKIPPED_COMPLETE", "fit_dir": str(fit_dir), "identity": identity}
    if fit_dir.exists() and not resume:
        raise ProtocolError(f"fit directory exists without matching COMPLETE; use --resume: {fit_dir}")
    fit_dir.mkdir(parents=True, exist_ok=True)
    write_csv(fit_dir / "input_manifest.csv", record_rows(records, condition), INPUT_FIELDS)
    atomic_json(fit_dir / "resolved_config.json", {
        "identity": identity,
        "model": config["model"],
        "training": training,
        "counts": {"inner_train": len(train_records), "inner_validation": len(validation_records),
                   "outer_test": len(test_records)},
        "input_checks": checks,
    })

    if not torch.cuda.is_available():
        raise ProtocolError("formal DenseNet training requires CUDA")
    device = torch.device("cuda")
    set_determinism(seed, bool(training["deterministic"]))
    torch.cuda.reset_peak_memory_stats(device)
    model = make_model(condition, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(training["learning_rate"]))
    criterion = torch.nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler("cuda", enabled=bool(training["amp"]))
    start_epoch, best_auc, best_epoch = 1, float("-inf"), None
    history: list[dict[str, Any]] = []
    last_path = fit_dir / "last_state.pth"
    if resume and last_path.is_file():
        state = torch.load(last_path, map_location=device, weights_only=False)
        if state.get("identity") != identity:
            raise ProtocolError("resume checkpoint identity does not match current fit")
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scaler.load_state_dict(state["scaler"])
        start_epoch = int(state["epoch"]) + 1
        best_auc = float(state["best_auc"])
        best_epoch = state["best_epoch"]
        history = list(state["history"])

    shape = tuple(int(x) for x in config["model"]["input_shape"])
    train_dataset = ClassificationDataset(train_records, condition, shape, bool(training["cache_in_memory"]))
    validation_dataset = ClassificationDataset(
        validation_records, condition, shape, bool(training["cache_in_memory"])
    )
    validation_loader = make_loader(validation_dataset, training, False, seed)
    started = time.time()
    for epoch in range(start_epoch, int(training["max_epochs"]) + 1):
        model.train()
        train_loader = make_loader(train_dataset, training, True, seed + epoch)
        total_loss, batches = 0.0, 0
        for batch in train_loader:
            images = batch["image"].to(device, non_blocking=True)
            labels = batch["label"].to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.amp.autocast("cuda", enabled=bool(training["amp"])):
                logits = model(images)
                loss = criterion(logits, labels)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            total_loss += float(loss.detach().cpu())
            batches += 1
        row: dict[str, Any] = {"epoch": epoch, "train_loss": total_loss / batches, "validation_auc": ""}
        if epoch % int(training["validation_interval"]) == 0:
            validation = infer(model, validation_loader, device, bool(training["amp"]))
            labels = np.asarray([r["label"] for r in validation])
            probabilities = np.asarray([r["probability"] for r in validation])
            auc = float(roc_auc_score(labels, probabilities))
            row["validation_auc"] = auc
            if auc > best_auc + 1e-12:
                best_auc, best_epoch = auc, epoch
                atomic_torch_save(fit_dir / "best_model.pth", {
                    "identity": identity, "epoch": epoch, "validation_auc": auc,
                    "model": model.state_dict(),
                })
        history.append(row)
        atomic_torch_save(last_path, {
            "identity": identity, "epoch": epoch, "model": model.state_dict(),
            "optimizer": optimizer.state_dict(), "scaler": scaler.state_dict(),
            "best_auc": best_auc, "best_epoch": best_epoch, "history": history,
        })
        write_csv(fit_dir / "history.csv", history, ["epoch", "train_loss", "validation_auc"])

    best = torch.load(fit_dir / "best_model.pth", map_location=device, weights_only=False)
    if best.get("identity") != identity:
        raise ProtocolError("best checkpoint identity mismatch")
    model.load_state_dict(best["model"])
    validation = infer(model, validation_loader, device, bool(training["amp"]))
    val_labels = np.asarray([r["label"] for r in validation])
    val_probabilities = np.asarray([r["probability"] for r in validation])
    threshold = select_threshold(val_labels, val_probabilities)
    for row in validation:
        row.update({"prediction": int(row["probability"] >= threshold), "threshold": threshold,
                    "role": "inner_validation"})
    test_dataset = ClassificationDataset(test_records, condition, shape, bool(training["cache_in_memory"]))
    test_loader = make_loader(test_dataset, training, False, seed)
    test = infer(model, test_loader, device, bool(training["amp"]))
    for row in test:
        row.update({"prediction": int(row["probability"] >= threshold), "threshold": threshold,
                    "role": "outer_test"})
    test_labels = np.asarray([r["label"] for r in test])
    test_probabilities = np.asarray([r["probability"] for r in test])
    metrics = metric_values(test_labels, test_probabilities, threshold)
    metrics["bootstrap_95_ci"] = stratified_bootstrap_ci(
        test_labels, test_probabilities, threshold, int(training["bootstrap_replicates"]), seed + 9000
    )
    metrics.update({
        "threshold": threshold, "threshold_source": "inner_validation",
        "best_epoch": best_epoch, "best_inner_validation_auc": best_auc,
        "outer_test_n": len(test),
    })
    write_csv(fit_dir / "inner_validation_predictions.csv", validation, PREDICTION_FIELDS)
    write_csv(fit_dir / "outer_test_predictions.csv", test, PREDICTION_FIELDS)
    atomic_json(fit_dir / "metrics.json", metrics)
    complete = {
        "status": "COMPLETE", "identity": identity, "metrics": metrics,
        "runtime_seconds": time.time() - started,
        "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated(device)),
        "host": socket.gethostname(),
        "outputs": {
            name: {"sha256": sha256_file(fit_dir / name), "bytes": (fit_dir / name).stat().st_size}
            for name in ("best_model.pth", "history.csv", "inner_validation_predictions.csv",
                         "outer_test_predictions.csv", "metrics.json", "input_manifest.csv")
        },
    }
    atomic_json(complete_path, complete)
    del model, optimizer, scaler
    gc.collect()
    torch.cuda.empty_cache()
    return complete


def command_preflight(args: argparse.Namespace) -> None:
    inputs = ProtocolInputs(args.config)
    conditions = args.conditions or inputs.config["conditions"]
    result: dict[str, Any] = {"status": "PASS", "fits": [], "stage4c4": "not_required"}
    for task in inputs.config["tasks"]:
        for fold in inputs.config["outer_folds"]:
            for condition in conditions:
                records = inputs.records(task, int(fold), condition)
                checks = inputs.verify_files(records, condition, args.verify_asset_sha)
                train, validation, test = split_records(records)
                result["fits"].append({
                    "task": task, "outer_fold": fold, "condition": condition,
                    "counts": [len(train), len(validation), len(test)], **checks,
                })
    if any(c in {"mri_full", "mri_ot"} for c in conditions):
        result["stage4c4"] = inputs.stage4c4_hashes
    if args.output:
        atomic_json(Path(args.output), result)
    print(json.dumps(result, indent=2))


def command_fit(args: argparse.Namespace) -> None:
    if args.authorization != FORMAL_AUTHORIZATION:
        raise ProtocolError("formal fit authorization is missing or incorrect")
    inputs = ProtocolInputs(args.config)
    result = run_fit(inputs, args.task, args.outer_fold, args.condition,
                     Path(args.output_root or inputs.config["output_root"]), args.resume, args.verify_asset_sha)
    print(json.dumps(result, indent=2, default=str))


def command_all(args: argparse.Namespace) -> None:
    if args.authorization != FORMAL_AUTHORIZATION:
        raise ProtocolError("formal all-fit authorization is missing or incorrect")
    inputs = ProtocolInputs(args.config)
    output_root = Path(args.output_root or inputs.config["output_root"])
    results = []
    for task in inputs.config["tasks"]:
        for fold in inputs.config["outer_folds"]:
            for condition in inputs.config["conditions"]:
                result = run_fit(inputs, task, int(fold), condition, output_root, True, args.verify_asset_sha)
                results.append({"task": task, "outer_fold": fold, "condition": condition,
                                "status": result["status"]})
    atomic_json(output_root / "all_fits_status.json", {"status": "COMPLETE", "fits": results})
    print(json.dumps(results, indent=2))


def _one_per_class(records: list[InputRecord], role: str) -> list[InputRecord]:
    selected = []
    for label in (0, 1):
        options = sorted((r for r in records if r.role == role and r.label == label), key=lambda r: r.ptid)
        if not options:
            raise ProtocolError(f"smoke selection lacks class {label} in {role}")
        selected.append(options[0])
    return selected


def command_smoke(args: argparse.Namespace) -> None:
    inputs = ProtocolInputs(args.config)
    config, condition = inputs.config, args.condition
    if condition not in {"mri", "mri_real"}:
        raise ProtocolError("smoke validation is intentionally limited to MRI or MRI+Real")
    all_records = inputs.records(args.task, args.outer_fold, condition)
    train_records = _one_per_class(all_records, "inner_train")
    validation_records = _one_per_class(all_records, "inner_validation")
    output_dir = Path(args.output_dir or config["smoke_output_root"])
    if output_dir.exists():
        raise ProtocolError(f"smoke output exists; refusing overwrite: {output_dir}")
    output_dir.mkdir(parents=True)
    if not torch.cuda.is_available():
        raise ProtocolError("smoke validation requires CUDA")
    training = config["training"]
    seed = fit_seed(config, args.task, args.outer_fold)
    set_determinism(seed, bool(training["deterministic"]))
    device = torch.device("cuda")
    torch.cuda.reset_peak_memory_stats(device)
    model = make_model(condition, device)
    optimizer = torch.optim.Adam(model.parameters(), lr=float(training["learning_rate"]))
    criterion = torch.nn.CrossEntropyLoss()
    scaler = torch.amp.GradScaler("cuda", enabled=bool(training["amp"]))
    shape = tuple(config["model"]["input_shape"])
    smoke_training = {**training, "batch_size": 1}
    train_dataset = ClassificationDataset(train_records, condition, shape, True)
    loader = make_loader(train_dataset, smoke_training, True, seed)
    started = time.time()
    model.train()
    batch = next(iter(loader))
    images, labels = batch["image"].to(device), batch["label"].to(device)
    optimizer.zero_grad(set_to_none=True)
    with torch.amp.autocast("cuda", enabled=bool(training["amp"])):
        logits = model(images)
        loss = criterion(logits, labels)
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
    validation_dataset = ClassificationDataset(validation_records, condition, shape, True)
    validation_loader = make_loader(validation_dataset, smoke_training, False, seed)
    validation = infer(model, validation_loader, device, bool(training["amp"]))
    labels_np = np.asarray([r["label"] for r in validation])
    probabilities = np.asarray([r["probability"] for r in validation])
    auc = float(roc_auc_score(labels_np, probabilities))
    identity = identity_payload(inputs, args.task, args.outer_fold, condition, seed)
    checkpoint = output_dir / "smoke_checkpoint.pth"
    atomic_torch_save(checkpoint, {"identity": identity, "model": model.state_dict(), "optimizer": optimizer.state_dict()})
    receipt = {
        "status": "PASS_SMOKE", "scientific_result": False, "identity": identity,
        "host": socket.gethostname(), "device": torch.cuda.get_device_name(device),
        "torch_version": torch.__version__, "monai_model": "DenseNet121_3D",
        "condition": condition, "channels": CONDITION_CHANNELS[condition],
        "input_shape": list(images.shape), "forward_shape": list(logits.shape),
        "loss": float(loss.detach().cpu()), "two_subject_validation_auc_engineering_only": auc,
        "train_ptids": [r.ptid for r in train_records],
        "validation_ptids": [r.ptid for r in validation_records],
        "runtime_seconds": time.time() - started,
        "peak_gpu_memory_bytes": int(torch.cuda.max_memory_allocated(device)),
        "checkpoint": {"path": str(checkpoint), "sha256": sha256_file(checkpoint),
                       "bytes": checkpoint.stat().st_size},
        "checks": ["actual_E1_loader", "forward", "cross_entropy", "backward", "adam_step",
                   "validation_forward", "checkpoint_atomic_save"],
    }
    atomic_json(output_dir / "smoke_receipt.json", receipt)
    print(json.dumps(receipt, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="validate frozen identities and enumerate fits; no training")
    preflight.add_argument("--conditions", nargs="*", choices=list(CONDITION_CHANNELS))
    preflight.add_argument("--verify-asset-sha", action=argparse.BooleanOptionalAction, default=True)
    preflight.add_argument("--output", type=Path)
    preflight.set_defaults(handler=command_preflight)

    fit = sub.add_parser("fit", help="run one task/fold/condition fit")
    fit.add_argument("--task", required=True, choices=["ad_cn", "mci_cn", "lmci_emci"])
    fit.add_argument("--outer-fold", required=True, type=int, choices=[1, 2])
    fit.add_argument("--condition", required=True, choices=list(CONDITION_CHANNELS))
    fit.add_argument("--output-root", type=Path)
    fit.add_argument("--resume", action="store_true")
    fit.add_argument("--verify-asset-sha", action=argparse.BooleanOptionalAction, default=True)
    fit.add_argument("--authorization", required=True)
    fit.set_defaults(handler=command_fit)

    all_fits = sub.add_parser("all", help="run/continue the frozen 24 fits sequentially")
    all_fits.add_argument("--output-root", type=Path)
    all_fits.add_argument("--verify-asset-sha", action=argparse.BooleanOptionalAction, default=True)
    all_fits.add_argument("--authorization", required=True)
    all_fits.set_defaults(handler=command_all)

    smoke = sub.add_parser("smoke", help="one real forward/backward/checkpoint engineering validation")
    smoke.add_argument("--task", default="ad_cn", choices=["ad_cn", "mci_cn", "lmci_emci"])
    smoke.add_argument("--outer-fold", default=1, type=int, choices=[1, 2])
    smoke.add_argument("--condition", default="mri", choices=["mri", "mri_real"])
    smoke.add_argument("--output-dir", type=Path)
    smoke.set_defaults(handler=command_smoke)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.handler(args)
        return 0
    except ProtocolError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
