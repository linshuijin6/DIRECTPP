"""Isolated Single-Tracer DIReCT rectified-flow, frozen Full two-fold protocol."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import shutil
import socket
import statistics
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
from common import (ROOT, SHAPE, TRACERS, FULL_REPORT, FullCacheDataset, cache_status,
                    csv_write, full_identity, hardware, json_write, read_csv,
                    restore_recovery, save_recovery, sha256, state_hash, valid_target,
                    validate_cache, validate_resource_receipt, verify_device_receipt)
from model import AUTHOR_ROOT, MODEL_SOURCE, attention_backend, build_model, parameter_count

SINGLE_NOTEBOOK = ROOT / "source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb"
FULL_RUNNER = ROOT / "experiments/original_author_reproduction/run.py"
FULL_CONDITIONS_RECEIPT = FULL_REPORT / "conditioning_receipt.json"
BIOMEDCLIP_RECEIPT = FULL_REPORT / "biomedclip_bundle.json"
SINGLE_NOTEBOOK_SHA256 = "6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a"
MODEL_SOURCE_SHA256 = "b56b1956b787e85f52fc1a7f46884fea2cbfff81f9c31311db462dda7b378bcc"
EPOCHS = 200
PRIMARY_EPOCH = 165
RECOVERY_INTERVAL = 10
LR = 2.5e-5
TASKS = ("fdg_fold1", "fdg_fold2", "av45_fold1", "av45_fold2")


def task_parts(task: str) -> tuple[str, int]:
    if task not in TASKS:
        raise ValueError(f"Unknown task: {task}")
    tracer, fold = task.split("_fold")
    return tracer.upper(), int(fold)


def frozen_texts() -> tuple[list[str], str]:
    if sha256(SINGLE_NOTEBOOK) != SINGLE_NOTEBOOK_SHA256:
        raise RuntimeError("Archived Single-Flow notebook identity changed")
    notebook = json.loads(SINGLE_NOTEBOOK.read_text())
    source = "".join(notebook["cells"][2]["source"])
    for statement in ast.parse(source).body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "modal_information"
                                                       for t in statement.targets):
            texts = ast.literal_eval(statement.value)
            if len(texts) == 3 and "FDG" in texts[1] and "MRI" in texts[0] and "CT" in texts[2]:
                break
    else:
        raise RuntimeError("Cannot recover historical FDG c_pet text")
    # This is the Full author's AV45-specific description, re-encoded by the
    # historical Single mechanism; no Full optimized feature tensor is loaded.
    for statement in ast.parse(FULL_RUNNER.read_text()).body:
        if isinstance(statement, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "AV45_TEXT"
                                                       for t in statement.targets):
            av45 = ast.literal_eval(statement.value)
            break
    else:
        raise RuntimeError("Cannot recover Full author AV45_TEXT")
    if "AV45" not in av45 or "amyloid" not in av45:
        raise RuntimeError("AV45 tracer text is not tracer-specific")
    return texts, av45


def condition_data(path: Path, receipt_path: Path, cohort: list[dict]) -> dict:
    import torch
    receipt = json.loads(receipt_path.read_text())
    if sha256(path) != receipt["conditions_sha256"]:
        raise RuntimeError("Single condition tensor hash mismatch")
    data = torch.load(path, map_location="cpu", weights_only=False)
    if data["ptids"] != [row["name"] for row in cohort]:
        raise RuntimeError("Single patient condition order differs from Full cohort")
    if tuple(data["patient"].shape) != (1857, 512) or tuple(data["tracer"].shape) != (2, 512):
        raise RuntimeError("Single condition shape mismatch")
    if not torch.isfinite(data["patient"]).all() or not torch.isfinite(data["tracer"]).all():
        raise RuntimeError("Single conditions contain non-finite values")
    return data


def command_prepare_conditions(args) -> None:
    import torch
    from transformers import AutoModel, AutoProcessor

    _, cohort, _, full = full_identity(args.full_config.resolve())
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)
    target, receipt_path = root / "conditions.pt", root / "conditions_receipt.json"
    if target.exists() or receipt_path.exists():
        raise RuntimeError("Frozen Single conditions already exist")
    texts, av45_text = frozen_texts()
    full_condition_receipt = json.loads(FULL_CONDITIONS_RECEIPT.read_text())
    full_condition_path = Path(full_condition_receipt["path"])
    if sha256(full_condition_path) != full_condition_receipt["sha256"]:
        raise RuntimeError("Full patient embedding receipt mismatch")
    original = torch.load(full_condition_path, map_location="cpu", weights_only=False)
    if original["ptids"] != [row["name"] for row in cohort] or tuple(original["patient"].shape) != (1857, 512):
        raise RuntimeError("Full patient vectors do not match frozen cohort")
    bundle_receipt = json.loads(BIOMEDCLIP_RECEIPT.read_text())
    bundle = Path(bundle_receipt["path"])
    for filename, digest in {**bundle_receipt["files"], "model.safetensors": bundle_receipt["model.safetensors"]}.items():
        if sha256(bundle / filename) != digest:
            raise RuntimeError(f"Frozen BiomedCLIP bundle mismatch: {filename}")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    processor = AutoProcessor.from_pretrained(str(bundle), trust_remote_code=True, local_files_only=True)
    clip = AutoModel.from_pretrained(str(bundle), trust_remote_code=True, local_files_only=True).to(device).eval()
    def encode(batch: list[str]):
        inputs = processor.tokenizer(batch, padding=True, truncation=True, return_tensors="pt", max_length=256)
        with torch.no_grad():
            return clip.get_text_features(inputs["input_ids"].to(device)).detach().float().cpu()
    # Encode the original three-item batch exactly; for AV45 only replace PET
    # wording at the same index, retaining the Single tokenizer/call signature.
    fdg = encode(texts)[1]
    av45 = encode([texts[0], av45_text, texts[2]])[1]
    data = {"ptids": original["ptids"], "patient": original["patient"].float(),
            "tracer": torch.stack([fdg, av45])}
    temporary = target.with_suffix(".pt.tmp")
    torch.save(data, temporary)
    os.replace(temporary, target)
    receipt = {
        "status": "FROZEN", "conditions_sha256": sha256(target),
        "patient_source": "Full frozen Description -> Full BiomedCLIP patient embedding, same input_ids call as Single",
        "full_conditions_sha256": full_condition_receipt["sha256"],
        "full_cohort_sha256": full["hashes"]["cohort"],
        "biomedclip_weight_sha256": bundle_receipt["model.safetensors"],
        "biomedclip_bundle_files": bundle_receipt["files"],
        "single_notebook_sha256": SINGLE_NOTEBOOK_SHA256,
        "fdg_source": "Single-Flow notebook cell 2 modal_information[1], cell 5 c_pet=text_features[1]",
        "fdg_encoder_batch": texts,
        "av45_source": "Full original_author_reproduction/run.py AV45_TEXT; Single encoding mechanism, not Full adapted embedding",
        "av45_encoder_batch": [texts[0], av45_text, texts[2]],
        "encoding": "processor.tokenizer(padding=True,truncation=True,max_length=256).input_ids -> get_text_features",
        "patient_shape": list(data["patient"].shape), "tracer_shape": list(data["tracer"].shape),
        "patient_tensor_sha256": hashlib.sha256(data["patient"].contiguous().numpy().tobytes()).hexdigest(),
        "fdg_tensor_sha256": hashlib.sha256(fdg.contiguous().numpy().tobytes()).hexdigest(),
        "av45_tensor_sha256": hashlib.sha256(av45.contiguous().numpy().tobytes()).hexdigest(),
    }
    json_write(receipt_path, receipt)
    print(json.dumps({"status": "FROZEN", "path": str(target), "receipt": str(receipt_path),
                      "conditions_sha256": receipt["conditions_sha256"]}))


def command_prepare(args) -> None:
    tracer, fold = task_parts(args.task)
    full_path = args.full_config.resolve()
    _, cohort, _, identity = full_identity(full_path)
    report = args.out.resolve() / args.task
    assets = args.assets_root.resolve() / args.task
    if report.exists() or assets.exists():
        raise RuntimeError("Isolated report/assets task path already exists")
    conditions = args.conditions.resolve()
    condition_receipt = args.condition_receipt.resolve()
    condition_data(conditions, condition_receipt, cohort)
    cache_dir = args.cache_dir.resolve()
    cache = cache_status(cache_dir, cohort)
    if not cache["valid"]:
        raise RuntimeError("Frozen Full cache key set differs from cohort")
    report.mkdir(parents=True)
    assets.mkdir(parents=True)
    runner_sha, common_sha, model_sha = (sha256(path) for path in (HERE / "run.py", HERE / "common.py", HERE / "model.py"))
    heldout = identity["effective_by_fold"][str(fold)][tracer]
    train_count = identity["effective"][tracer] - heldout
    cfg = {
        "experiment": "direct_single_2fold_oof", "task": args.task,
        "tracer": tracer, "fold": fold, "report": str(report), "assets": str(assets),
        "full_config": str(full_path), "full_config_sha256": sha256(full_path),
        "full_report": identity["report"], "full_identity": identity,
        "cohort_sha256": identity["hashes"]["cohort"],
        "split_manifest_sha256": identity["hashes"]["split_manifest"],
        "input_hashes_sha256": identity["cache_receipt"]["input_hashes_sha256"],
        "cache_receipt_sha256": identity["hashes"]["persistent_cache_receipt"],
        "cache": cache, "conditions": str(conditions), "condition_receipt": str(condition_receipt),
        "conditions_sha256": sha256(conditions), "condition_receipt_sha256": sha256(condition_receipt),
        "runner_sha256": runner_sha, "common_sha256": common_sha, "model_sha256": model_sha,
        "attention_compat_sha256": sha256(HERE / "compat/xformers/ops.py"),
        "author_model_sha256": MODEL_SOURCE_SHA256,
        "epochs": EPOCHS, "primary_epoch": PRIMARY_EPOCH, "secondary_epoch": EPOCHS,
        "learning_rate": LR, "batch_size": 1, "optimizer": "Adam",
        "loss": "MSE(PET-MRI, v_theta((1-t)MRI+tPET,t,context))",
        "time": "integer Uniform[0,1000) / 1000 until zero-based epoch 139; t=0 from epoch 140",
        "inference": "MRI + v_theta(MRI,t=0,context), clamp [0,1]",
        "amp": "CUDA float16 autocast + GradScaler", "seed_policy": "unseeded; record and restore RNG state",
        "train_subjects": train_count, "heldout_metric_rows": heldout,
        "validation": "none; no held-out fold access during training",
        "created_utc": datetime.now(timezone.utc).isoformat(),
    }
    json_write(report / "config.json", cfg)
    json_write(report / "prepare_receipt.json", {"status": "PREPARED", "config_sha256": sha256(report / "config.json"),
                                                  "cache": cache, "train_subjects": train_count,
                                                  "heldout_metric_rows": heldout})
    print(json.dumps({"status": "PREPARED", "task": args.task, "config": str(report / "config.json")}))


def load_config(path: Path):
    cfg = json.loads(path.read_text())
    report = Path(cfg["report"])
    if sha256(path) != json.loads((report / "prepare_receipt.json").read_text())["config_sha256"]:
        raise RuntimeError("Single task config changed")
    for key, filename in (("runner_sha256", "run.py"), ("common_sha256", "common.py"), ("model_sha256", "model.py")):
        if sha256(HERE / filename) != cfg[key]:
            raise RuntimeError(f"Single implementation changed: {filename}")
    if sha256(HERE / "compat/xformers/ops.py") != cfg["attention_compat_sha256"]:
        raise RuntimeError("Attention compatibility code changed")
    if sha256(MODEL_SOURCE) != cfg["author_model_sha256"]:
        raise RuntimeError("Archived author model source changed")
    if sha256(Path(cfg["full_config"])) != cfg["full_config_sha256"]:
        raise RuntimeError("Frozen Full config changed")
    _, cohort, _, identity = full_identity(Path(cfg["full_config"]))
    if identity["hashes"]["cohort"] != cfg["cohort_sha256"] or identity["hashes"]["split_manifest"] != cfg["split_manifest_sha256"]:
        raise RuntimeError("Full cohort/split changed")
    if identity["cache_receipt"]["input_hashes_sha256"] != cfg["input_hashes_sha256"]:
        raise RuntimeError("Full input hash identity changed")
    input_manifest = Path(cfg["full_report"]) / "input_hashes.csv"
    if sha256(input_manifest) != cfg["input_hashes_sha256"]:
        raise RuntimeError("Frozen Full input hash manifest changed")
    if sha256(Path(cfg["condition_receipt"])) != cfg["condition_receipt_sha256"]:
        raise RuntimeError("Single condition receipt changed")
    condition_data(Path(cfg["conditions"]), Path(cfg["condition_receipt"]), cohort)
    return cfg, cohort


def context_for(batch, conditions, tracer: str):
    import torch
    index = conditions["lookup"][batch["name"][0]]
    tracer_index = 0 if tracer == "FDG" else 1
    return torch.stack((conditions["patient"][index], conditions["tracer"][tracer_index]), dim=0).unsqueeze(0).cuda()


def prepared_conditions(cfg, cohort):
    data = condition_data(Path(cfg["conditions"]), Path(cfg["condition_receipt"]), cohort)
    data["lookup"] = {sid: i for i, sid in enumerate(data["ptids"])}
    return data


def command_check_config(args) -> None:
    cfg, cohort = load_config(args.config.resolve())
    cache = validate_cache(cfg, cohort, load_sample=True)
    condition = prepared_conditions(cfg, cohort)
    if tuple(condition["patient"].shape) != (1857, 512):
        raise RuntimeError("Patient vector shape invalid")
    result = {"status": "PASS", "task": cfg["task"], "cohort": len(cohort),
              "train_subjects": cfg["train_subjects"], "heldout_metric_rows": cfg["heldout_metric_rows"],
              "cache": cache, "conditions_sha256": cfg["conditions_sha256"]}
    json_write(Path(cfg["report"]) / "config_check.json", result)
    print(json.dumps(result))


def train_step(model, mri, pet, context, optimizer, scaler, epoch: int):
    import torch
    import torch.nn.functional as F
    optimizer.zero_grad(set_to_none=True)
    timestep = torch.randint(0, 1000, (mri.shape[0],), device=mri.device, dtype=torch.long)
    if epoch >= 140:
        timestep.zero_()
    t = timestep.float().view(-1, 1, 1, 1, 1) / 1000.0
    with torch.autocast("cuda", dtype=torch.float16):
        x_t = (1.0 - t) * mri + t * pet
        velocity = model(x=x_t, timesteps=timestep, context=context)
        loss = F.mse_loss((pet - mri).float(), velocity.float())
    if not torch.isfinite(loss):
        raise RuntimeError("Non-finite velocity loss")
    scale_before = scaler.get_scale()
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
    return float(loss.detach()), int(scaler.get_scale() < scale_before)


def command_smoke_test(args) -> None:
    import torch
    from torch.utils.data import DataLoader

    if not torch.cuda.is_available():
        raise RuntimeError("Full-size Single preflight requires CUDA")
    cfg, cohort = load_config(args.config.resolve())
    resource = validate_resource_receipt(args.resource_receipt.resolve(), socket.gethostname())
    verify_device_receipt(resource, torch)
    validate_cache(cfg, cohort)
    conditions = prepared_conditions(cfg, cohort)
    tracer, fold = cfg["tracer"], cfg["fold"]
    rows = [r for r in cohort if int(r["test_fold"]) != fold and valid_target(r, tracer)]
    count = args.warmup_steps + args.steps
    if count < 2 or len(rows) < count:
        raise ValueError("Need at least two full-size steps and enough training subjects")
    dataset = FullCacheDataset(rows[:count], Path(cfg["cache"]["path"]))
    loader = DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0, pin_memory=True)
    model = build_model().cuda().train()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scaler = torch.amp.GradScaler("cuda")
    seconds, losses, skipped = [], [], 0
    torch.cuda.reset_peak_memory_stats()
    for index, batch in enumerate(loader):
        mri, pet = batch["mri"].cuda(), batch[tracer.lower()].cuda()
        if torch.all(pet == 0):
            raise RuntimeError("A missing-PET placeholder reached the preflight training sample")
        context = context_for(batch, conditions, tracer)
        if tuple(mri.shape) != (1, 1, *SHAPE) or tuple(context.shape) != (1, 2, 512):
            raise RuntimeError("Full-size image or context shape mismatch")
        torch.cuda.synchronize()
        start = time.perf_counter()
        loss, overflow = train_step(model, mri, pet, context, optimizer, scaler, 0)
        torch.cuda.synchronize()
        losses.append(loss)
        skipped += overflow
        if index >= args.warmup_steps:
            seconds.append(time.perf_counter() - start)
    if skipped == count:
        raise RuntimeError("Every AMP optimizer step was skipped")
    with tempfile.TemporaryDirectory(dir=cfg["assets"]) as temporary:
        model_path, recovery_path = Path(temporary) / "model.pt", Path(temporary) / "recovery.pt"
        torch.save(model.state_dict(), model_path)
        save_recovery(recovery_path, model, optimizer, scaler, 0, {"preflight": True}, torch)
        model_bytes, recovery_bytes = model_path.stat().st_size, recovery_path.stat().st_size
    median = statistics.median(seconds)
    by_task = {}
    for task in TASKS:
        tr, f = task_parts(task)
        train_n = cfg["full_identity"]["effective"][tr] - cfg["full_identity"]["effective_by_fold"][str(f)][tr]
        updates = train_n * EPOCHS
        by_task[task] = {"updates": updates, "hours": updates * median / 3600.0}
    prediction_bytes = cfg["heldout_metric_rows"] * int(np.prod(SHAPE)) * 4
    asset_estimate = 2 * model_bytes + recovery_bytes + prediction_bytes
    result = {
        "status": "PASS_NO_FORMAL_TRAINING_STATE", "task": cfg["task"],
        "hardware": hardware(torch), "allocation": resource,
        "allocation_receipt_sha256": sha256(args.resource_receipt),
        "config_sha256": sha256(args.config), "parameters": parameter_count(model),
        "attention_backend": attention_backend(),
        "input_shape": [1, 1, *SHAPE], "context_shape": [1, 2, 512],
        "condition_receipt_sha256": cfg["condition_receipt_sha256"],
        "warmup_steps": args.warmup_steps, "measured_steps": args.steps,
        "step_seconds": seconds, "step_seconds_median": median,
        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
        "losses": losses, "amp_skipped_steps": skipped,
        "successful_optimizer_updates": count - skipped,
        "checkpoint_bytes": model_bytes, "recovery_bytes": recovery_bytes,
        "estimated_task_assets_bytes": asset_estimate,
        "training_time_estimates": by_task,
        "all_four_gpu_hours_estimate": sum(x["hours"] for x in by_task.values()),
        "heldout_accessed": False, "formal_state_written": False,
    }
    if by_task[cfg["task"]]["hours"] > 72:
        result["status"] = "BLOCKED_ESTIMATE_OVER_72_HOURS"
    target = Path(cfg["report"]) / "cuda_preflight.json"
    if target.exists():
        raise RuntimeError("Preflight receipt already exists")
    json_write(target, result)
    print(json.dumps(result))


def checkpoint_identity(cfg):
    return {"task": cfg["task"], "config_sha256": sha256(Path(cfg["report"]) / "config.json"),
            "cohort_sha256": cfg["cohort_sha256"], "split_manifest_sha256": cfg["split_manifest_sha256"],
            "conditions_sha256": cfg["conditions_sha256"], "runner_sha256": cfg["runner_sha256"],
            "model_sha256": cfg["model_sha256"], "epochs": EPOCHS}


def save_milestone(path, model, epoch, identity, torch):
    temporary = path.with_suffix(".pt.tmp")
    torch.save({"model": model.state_dict(), "epoch": epoch, **identity}, temporary)
    os.replace(temporary, path)
    json_write(path.with_suffix(".json"), {**identity, "epoch": epoch,
               "checkpoint_sha256": sha256(path), "model_state_sha256": state_hash(model.state_dict())})


def command_train(args) -> None:
    import torch
    from torch.utils.data import DataLoader

    cfg, cohort = load_config(args.config.resolve())
    resource = validate_resource_receipt(args.resource_receipt.resolve(), socket.gethostname())
    verify_device_receipt(resource, torch)
    validate_cache(cfg, cohort)
    preflight = json.loads((Path(cfg["report"]) / "cuda_preflight.json").read_text())
    if preflight["status"] != "PASS_NO_FORMAL_TRAINING_STATE" or preflight["config_sha256"] != sha256(args.config):
        raise RuntimeError("Full-size preflight did not pass for this config")
    if preflight["allocation"]["gpu_uuid"] != resource["gpu_uuid"]:
        raise RuntimeError("Preflight and training GPU differ")
    if shutil.disk_usage(cfg["assets"]).free < preflight["estimated_task_assets_bytes"]:
        raise RuntimeError("Insufficient task asset storage")
    conditions = prepared_conditions(cfg, cohort)
    tracer, fold = cfg["tracer"], cfg["fold"]
    rows = [r for r in cohort if int(r["test_fold"]) != fold and valid_target(r, tracer)]
    if len(rows) != cfg["train_subjects"]:
        raise RuntimeError("Training target count changed")
    loader = DataLoader(FullCacheDataset(rows, Path(cfg["cache"]["path"])), batch_size=1,
                        shuffle=True, num_workers=0, pin_memory=True)
    model = build_model().cuda().train()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scaler = torch.amp.GradScaler("cuda")
    assets = Path(cfg["assets"])
    formal, recovery = assets / "formal", assets / "formal" / "recovery.pt"
    identity = checkpoint_identity(cfg)
    if args.resume:
        if args.resume.resolve() != recovery.resolve() or not recovery.is_file():
            raise RuntimeError("Resume must use this task's own recovery.pt")
        start_epoch = restore_recovery(recovery, model, optimizer, scaler, identity, torch)
    else:
        formal.mkdir(parents=True, exist_ok=False)
        start_epoch = 0
    start = {**identity, "status": "STARTED", "pid": os.getpid(), "host": socket.gethostname(),
             "gpu": hardware(torch), "parameters": parameter_count(model),
             "started_utc": datetime.now(timezone.utc).isoformat(),
             "train_subjects": len(rows), "log_path": str(args.log_path.resolve()),
             "checkpoint_dir": str(formal), "recovery_path": str(recovery),
             "resource_receipt_sha256": sha256(args.resource_receipt)}
    json_write(Path(cfg["report"]) / ("resume_launch.json" if args.resume else "launch.json"), start)
    print(json.dumps(start), flush=True)
    for epoch in range(start_epoch, EPOCHS):
        losses, skipped = [], 0
        began = time.monotonic()
        model.train()
        for batch in loader:
            mri, pet = batch["mri"].cuda(non_blocking=True), batch[tracer.lower()].cuda(non_blocking=True)
            if torch.all(pet == 0):
                raise RuntimeError("A missing-PET placeholder reached the training loader")
            context = context_for(batch, conditions, tracer)
            loss, overflow = train_step(model, mri, pet, context, optimizer, scaler, epoch)
            losses.append(loss)
            skipped += overflow
        number = epoch + 1
        if number % RECOVERY_INTERVAL == 0 or number in (PRIMARY_EPOCH, EPOCHS):
            save_recovery(recovery, model, optimizer, scaler, epoch, identity, torch)
            event = {"task": cfg["task"], "epoch": number, "train_velocity_mse": float(np.mean(losses)),
                     "seconds": time.monotonic() - began, "amp_skipped_updates": skipped,
                     "recovery_sha256": sha256(recovery), "heldout_validation": None}
            with (Path(cfg["report"]) / "training_epochs.jsonl").open("a") as stream:
                stream.write(json.dumps(event) + "\n")
                stream.flush()
                os.fsync(stream.fileno())
            print(json.dumps(event), flush=True)
        if number in (PRIMARY_EPOCH, EPOCHS):
            save_milestone(formal / f"checkpoint_epoch{number}.pt", model, number, identity, torch)
    json_write(Path(cfg["report"]) / "training_complete.json", {**identity,
               "status": "TRAINING_COMPLETE_NOT_INFERRED", "completed_utc": datetime.now(timezone.utc).isoformat(),
               "primary_checkpoint": str(formal / f"checkpoint_epoch{PRIMARY_EPOCH}.pt"),
               "secondary_checkpoint": str(formal / f"checkpoint_epoch{EPOCHS}.pt")})


def command_infer(args) -> None:
    import nibabel as nib
    import torch
    import torch.nn.functional as F
    from monai.metrics import PSNRMetric
    from torch.utils.data import DataLoader

    if args.epoch not in (PRIMARY_EPOCH, EPOCHS):
        raise ValueError("Only preregistered epochs 165 and 200 may be inferred")
    cfg, cohort = load_config(args.config.resolve())
    validate_cache(cfg, cohort)
    if not (Path(cfg["report"]) / "training_complete.json").is_file():
        raise RuntimeError("Training must complete before OOF inference")
    conditions = prepared_conditions(cfg, cohort)
    tracer, fold = cfg["tracer"], cfg["fold"]
    checkpoint = Path(cfg["assets"]) / "formal" / f"checkpoint_epoch{args.epoch}.pt"
    receipt = json.loads(checkpoint.with_suffix(".json").read_text())
    if sha256(checkpoint) != receipt["checkpoint_sha256"]:
        raise RuntimeError("Fixed checkpoint hash mismatch")
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    identity = checkpoint_identity(cfg)
    if any(state.get(k) != v for k, v in identity.items()):
        raise RuntimeError("Checkpoint configuration/data identity mismatch")
    model = build_model().cuda().eval()
    model.load_state_dict(state["model"])
    if str(AUTHOR_ROOT) not in sys.path:
        sys.path.insert(0, str(AUTHOR_ROOT))
    from generative.metrics import SSIMMetric
    rows = [r for r in cohort if int(r["test_fold"]) == fold and valid_target(r, tracer)]
    loader = DataLoader(FullCacheDataset(rows, Path(cfg["cache"]["path"])), batch_size=1,
                        shuffle=False, num_workers=0, pin_memory=True)
    output = Path(cfg["assets"]) / f"oof_epoch{args.epoch}"
    output.mkdir(parents=True, exist_ok=False)
    ssim, psnr, metric_rows = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7), PSNRMetric(max_val=1.0), []
    with torch.no_grad():
        for batch in loader:
            sid = batch["name"][0]
            mri, target = batch["mri"].cuda(), batch[tracer.lower()].cuda()
            context = context_for(batch, conditions, tracer)
            velocity = model(x=mri, timesteps=torch.zeros(1, device="cuda", dtype=torch.long), context=context)
            prediction = torch.clamp(mri + velocity.float(), 0, 1)
            affine = batch["affine"][0].numpy() if isinstance(batch["affine"], torch.Tensor) else np.asarray(batch["affine"][0])
            image_path = output / f"generated_{tracer}_{sid}.nii.gz"
            nib.save(nib.Nifti1Image(prediction.squeeze().cpu().numpy(), affine), image_path)
            metric_rows.append({"ptid": sid, "tracer": tracer.lower(), "fold": fold, "epoch": args.epoch,
                "ssim": float(ssim(prediction, target).mean()), "psnr": float(psnr(prediction, target).mean()),
                "mse": float(F.mse_loss(prediction, target.float())),
                "mae": float(F.l1_loss(prediction, target.float())),
                "prediction": str(image_path), "prediction_sha256": sha256(image_path),
                "checkpoint_sha256": receipt["checkpoint_sha256"]})
    if len(metric_rows) != cfg["heldout_metric_rows"]:
        raise RuntimeError("OOF metric row count mismatch")
    csv_write(Path(cfg["report"]) / f"metrics_epoch{args.epoch}.csv", metric_rows)
    json_write(Path(cfg["report"]) / f"oof_epoch{args.epoch}_complete.json", {
        "status": "COMPLETE_FOLD_OOF", "task": cfg["task"], "epoch": args.epoch,
        "metric_rows": len(metric_rows), "metrics_sha256": sha256(Path(cfg["report"]) / f"metrics_epoch{args.epoch}.csv"),
        "checkpoint_sha256": receipt["checkpoint_sha256"]})


def command_summarize(args) -> None:
    root = args.out.resolve()
    if (root / "oof_summary").exists():
        raise RuntimeError("Global OOF summary already exists")
    full_cfg, _, _, full_identity_receipt = full_identity(args.full_config.resolve())
    full_metrics = Path(full_identity_receipt["report"]) / "oof_summary/per_subject_metrics.csv"
    complete = json.loads((Path(full_identity_receipt["report"]) / "oof_summary/completion.json").read_text())
    if sha256(full_metrics) != complete["per_subject_sha256"]:
        raise RuntimeError("Full OOF metric identity changed")
    full_rows = [r for r in read_csv(full_metrics) if int(r["epoch"]) == PRIMARY_EPOCH]
    full_map = {(r["ptid"], r["tracer"].upper(), int(r["fold"])): r for r in full_rows}
    if len(full_map) != len(full_rows):
        raise RuntimeError("Duplicate Full OOF identity")
    summary_rows, paired = [], []
    for epoch in (PRIMARY_EPOCH, EPOCHS):
        single_rows = []
        for task in TASKS:
            report = root / task
            cfg, _ = load_config(report / "config.json")
            receipt = json.loads((report / f"oof_epoch{epoch}_complete.json").read_text())
            metrics = report / f"metrics_epoch{epoch}.csv"
            if receipt["status"] != "COMPLETE_FOLD_OOF" or sha256(metrics) != receipt["metrics_sha256"]:
                raise RuntimeError(f"Incomplete or changed Single OOF: {task}/epoch{epoch}")
            single_rows.extend(read_csv(metrics))
        single_map = {(r["ptid"], r["tracer"].upper(), int(r["fold"])): r for r in single_rows}
        if len(single_map) != len(single_rows) or set(single_map) != set(full_map):
            raise RuntimeError(f"Single/Full OOF subject identities differ at epoch {epoch}")
        for key in sorted(single_map):
            single, full = single_map[key], full_map[key]
            paired.append({"ptid": key[0], "tracer": key[1], "fold": key[2], "single_epoch": epoch,
                           "full_epoch": PRIMARY_EPOCH,
                           **{f"single_{m}": float(single[m]) for m in ("ssim", "psnr", "mse", "mae")},
                           **{f"full_{m}": float(full[m]) for m in ("ssim", "psnr", "mse", "mae")}})
        for tracer in TRACERS:
            group = [r for r in paired if r["single_epoch"] == epoch and r["tracer"] == tracer]
            result = {"tracer": tracer, "single_epoch": epoch, "full_epoch": PRIMARY_EPOCH, "n": len(group)}
            for metric in ("ssim", "psnr", "mse", "mae"):
                result[f"single_{metric}"] = float(np.mean([r[f"single_{metric}"] for r in group]))
                result[f"full_{metric}"] = float(np.mean([r[f"full_{metric}"] for r in group]))
                result[f"delta_{metric}"] = result[f"single_{metric}"] - result[f"full_{metric}"]
            summary_rows.append(result)
    out = root / "oof_summary"
    out.mkdir(parents=True, exist_ok=False)
    csv_write(out / "paired_full_epoch165.csv", paired)
    csv_write(out / "summary.csv", summary_rows)
    json_write(out / "completion.json", {"status": "COMPLETE_DIRECT_SINGLE_TWO_FOLD_OOF",
               "paired_rows": len(paired), "paired_sha256": sha256(out / "paired_full_epoch165.csv"),
               "summary_sha256": sha256(out / "summary.csv")})


def parser():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    c = sub.add_parser("prepare-conditions")
    c.add_argument("--full-config", type=Path, default=FULL_REPORT / "config.json")
    c.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("prepare")
    c.add_argument("--task", choices=TASKS, required=True)
    c.add_argument("--full-config", type=Path, default=FULL_REPORT / "config.json")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--assets-root", type=Path, required=True)
    c.add_argument("--cache-dir", type=Path, required=True)
    c.add_argument("--conditions", type=Path, required=True)
    c.add_argument("--condition-receipt", type=Path, required=True)
    c = sub.add_parser("check-config")
    c.add_argument("--config", type=Path, required=True)
    c = sub.add_parser("smoke-test")
    c.add_argument("--config", type=Path, required=True)
    c.add_argument("--resource-receipt", type=Path, required=True)
    c.add_argument("--warmup-steps", type=int, default=2)
    c.add_argument("--steps", type=int, default=10)
    c = sub.add_parser("train")
    c.add_argument("--config", type=Path, required=True)
    c.add_argument("--resource-receipt", type=Path, required=True)
    c.add_argument("--log-path", type=Path, required=True)
    c.add_argument("--resume", type=Path)
    c = sub.add_parser("infer")
    c.add_argument("--config", type=Path, required=True)
    c.add_argument("--epoch", type=int, choices=(PRIMARY_EPOCH, EPOCHS), required=True)
    c = sub.add_parser("summarize")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--full-config", type=Path, default=FULL_REPORT / "config.json")
    return p


if __name__ == "__main__":
    args = parser().parse_args()
    {"prepare-conditions": command_prepare_conditions, "prepare": command_prepare,
     "check-config": command_check_config, "smoke-test": command_smoke_test,
     "train": command_train, "infer": command_infer, "summarize": command_summarize}[args.action](args)
