"""Tracer-only control that reuses the verified author-reproduction trainer.

The only scientific change is the conditioning context:
``[patient, tracer]`` becomes ``[fixed empty-patient, tracer]``.  The Full
trainer remains the owner of preprocessing, loss, optimization, validation,
checkpointing, inference, and OOF summarization.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.original_author_reproduction import run as full  # noqa: E402


MODE = "tracer_only_fixed_empty_patient"
CONTROL_ASSET = "tracer_only_conditions.pt"
_CONTEXTS = None
_FULL_CHECKPOINT_IDENTITY = full.checkpoint_identity


def _sha(path: Path) -> str:
    return full.sha256(path)


def _tree_identity(path: Path) -> list[tuple[str, int, int]]:
    return sorted((p.name, p.stat().st_size, p.stat().st_mtime_ns) for p in path.glob("*.pt"))


def _load_control_config(path: Path) -> tuple[dict, list[dict]]:
    cfg, cohort = full.load_config(path.resolve())
    if cfg.get("condition_mode") != MODE:
        raise RuntimeError("Not a frozen tracer-only control config")
    if _sha(Path(cfg["full_config"])) != cfg["full_config_sha256"]:
        raise RuntimeError("Frozen Full config changed")
    asset = Path(cfg["assets"]) / CONTROL_ASSET
    if _sha(asset) != cfg["tracer_only_conditions_sha256"]:
        raise RuntimeError("Tracer-only condition asset changed")
    if _sha(Path(cfg["assets"]) / "conditions.pt") != cfg["full_conditions_sha256"]:
        raise RuntimeError("Full cache-binding conditions changed")
    if _sha(Path(__file__)) != cfg["tracer_only_source_sha256"]:
        raise RuntimeError("Tracer-only entrypoint changed after preparation")
    if _sha(Path(full.__file__)) != cfg["base_training_source_sha256"]:
        raise RuntimeError("Base Full trainer changed after preparation")
    return cfg, cohort


def _load_context_asset(cfg: dict) -> dict:
    import torch

    saved = torch.load(Path(cfg["assets"]) / CONTROL_ASSET, map_location="cpu", weights_only=False)
    empty, tracers = saved["empty_patient"], saved["tracer"]
    if tuple(empty.shape) != (1, 512) or tuple(tracers.shape) != (2, 512):
        raise RuntimeError("Unexpected tracer-only condition shapes")
    if not torch.isfinite(empty).all() or not torch.isfinite(tracers).all():
        raise RuntimeError("Non-finite tracer-only condition")
    if torch.equal(tracers[0], tracers[1]):
        raise RuntimeError("FDG and AV45 tracer identities are equal")
    return saved


def _control_context_from_batch(batch, tracer: str):
    import torch

    if tracer not in full.TRACERS or _CONTEXTS is None:
        raise RuntimeError("Tracer-only runtime context is not activated")
    cached = batch[f"{tracer}_index"]
    if tuple(cached.shape[-2:]) != (2, 512):
        raise RuntimeError("Unexpected cached Full context shape")
    batch_size = int(batch["mri"].shape[0])
    context = _CONTEXTS[tracer]
    if context.device.type != "cuda":
        context = context.cuda()
        _CONTEXTS[tracer] = context
    return context.expand(batch_size, -1, -1)


def _control_checkpoint_identity(cfg: dict, fold: int) -> dict:
    identity = _FULL_CHECKPOINT_IDENTITY(cfg, fold)
    identity.update(
        condition_mode=MODE,
        tracer_only_conditions_sha256=cfg["tracer_only_conditions_sha256"],
        empty_patient_sha256=cfg["empty_patient_sha256"],
        base_training_source_sha256=cfg["base_training_source_sha256"],
        tracer_only_source_sha256=cfg["tracer_only_source_sha256"],
    )
    return identity


def _activate(cfg: dict) -> dict:
    global _CONTEXTS
    import torch

    saved = _load_context_asset(cfg)
    empty, tracers = saved["empty_patient"], saved["tracer"]
    _CONTEXTS = {
        tracer: torch.stack((empty[0], tracers[index]), dim=0).unsqueeze(0)
        for index, tracer in enumerate(full.TRACERS)
    }
    full.context_from_batch = _control_context_from_batch
    full.checkpoint_identity = _control_checkpoint_identity
    return saved


def command_prepare(args) -> None:
    import torch
    from transformers import AutoModel, AutoProcessor

    full_config = args.full_config.resolve()
    full_cfg, cohort = full.load_config(full_config)
    out, assets = args.out.resolve(), args.assets.resolve()
    if out.exists() or assets.exists():
        raise RuntimeError("Tracer-only report/assets already exist; refusing to overwrite")
    out.mkdir(parents=True)
    assets.mkdir(parents=True)

    full_report = Path(full_cfg["report"])
    for name in ("cohort.json", "split_manifest.csv", "split_receipt.json", "input_hashes.csv", "input_hashes_receipt.json"):
        source = full_report / name
        if not source.exists():
            raise RuntimeError(f"Missing frozen Full artifact: {source}")
        shutil.copyfile(source, out / name)

    full_conditions = Path(full_cfg["assets"]) / "conditions.pt"
    if not full_conditions.exists():
        raise RuntimeError("Missing completed Full conditions.pt")
    (assets / "conditions.pt").symlink_to(full_conditions.resolve())
    conditions = torch.load(full_conditions, map_location="cpu", weights_only=False)
    if conditions["ptids"] != [r["name"] for r in cohort]:
        raise RuntimeError("Full condition PTID order differs from frozen cohort")

    bundle = full.ensure_biomedclip_bundle({"assets": str(assets), "report": str(out)})
    processor = AutoProcessor.from_pretrained(str(bundle), trust_remote_code=True, local_files_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    clip = AutoModel.from_pretrained(str(bundle), trust_remote_code=True, local_files_only=True).to(device).eval()
    patient_inputs = processor([""], padding=True, truncation=True, return_tensors="pt", max_length=256).to(device)
    with torch.no_grad():
        empty = clip.get_text_features(patient_inputs["input_ids"]).cpu()
    control = {
        "condition_mode": MODE,
        "empty_patient": empty,
        "tracer": conditions["tracer"].detach().cpu().clone(),
        "empty_text": "",
        "patient_encoding_call": "processor([empty], padding=True, truncation=True, max_length=256); get_text_features(input_ids)",
        "full_conditions_sha256": _sha(full_conditions),
        "biomedclip_model_sha256": full.BIOMEDCLIP_SHA256,
    }
    torch.save(control, assets / CONTROL_ASSET)
    del clip, processor, patient_inputs
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    empty_digest = hashlib.sha256(empty.contiguous().numpy().tobytes()).hexdigest()
    config = {k: v for k, v in full_cfg.items() if not k.startswith("_")}
    config.update(
        experiment="original_author_tracer_only_control",
        report=str(out),
        assets=str(assets),
        condition_mode=MODE,
        full_config=str(full_config),
        full_config_sha256=_sha(full_config),
        full_report=str(full_report),
        full_conditions_sha256=_sha(full_conditions),
        tracer_only_conditions_sha256=_sha(assets / CONTROL_ASSET),
        empty_patient_sha256=empty_digest,
        base_training_source_sha256=_sha(Path(full.__file__)),
        tracer_only_source_sha256=_sha(Path(__file__)),
        cache_policy="reuse_full_persistent_cache_and_override_context_after_read",
        status="PREPARED_NOT_TRAINED",
    )
    full.json_write(out / "config.json", config)

    cache_receipt = full_report / "persistent_cache_receipt.json"
    if not cache_receipt.exists():
        raise RuntimeError("Missing completed Full persistent-cache receipt")
    shutil.copyfile(cache_receipt, out / "persistent_cache_receipt.json")
    full.json_write(
        out / "conditioning_receipt.json",
        {
            "condition_mode": MODE,
            "empty_text": "",
            "empty_patient_shape": list(empty.shape),
            "empty_patient_sha256": empty_digest,
            "tracer_shape": list(conditions["tracer"].shape),
            "fdg_av45_equal": bool(torch.equal(conditions["tracer"][0], conditions["tracer"][1])),
            "tracer_only_conditions_sha256": _sha(assets / CONTROL_ASSET),
            "full_conditions_sha256": _sha(full_conditions),
            "full_conditions_link": str((assets / "conditions.pt").resolve()),
            "cache_context_policy": "cached Full context fields are shape-checked then ignored; runtime context is rebuilt from this asset",
        },
    )
    print(json.dumps({"config": str(out / "config.json"), "assets": str(assets), "condition_mode": MODE}))


def _static_checks(cfg: dict, cohort: list[dict]) -> dict:
    import inspect
    import torch

    full_cfg, full_cohort = full.load_config(Path(cfg["full_config"]))
    if cohort != full_cohort:
        raise RuntimeError("Tracer-only cohort differs from Full")
    for name in ("cohort.json", "split_manifest.csv", "input_hashes.csv"):
        if _sha(Path(cfg["report"]) / name) != _sha(Path(full_cfg["report"]) / name):
            raise RuntimeError(f"Tracer-only frozen artifact differs from Full: {name}")
    if cfg["epochs"] != 200 or cfg["primary_epoch"] != 165 or cfg["secondary_epoch"] != 200:
        raise RuntimeError("Training endpoints differ from Full")
    if cfg["distill_start_epoch_zero_based"] != 140 or cfg["val_interval"] != 10:
        raise RuntimeError("Training schedule differs from Full")
    if cfg["learning_rate"] != full_cfg["learning_rate"] or cfg["batch_size"] != full_cfg["batch_size"]:
        raise RuntimeError("Optimizer-facing configuration differs from Full")
    counts = {str(f): sum(r["test_fold"] == f for r in cohort) for f in (1, 2)}
    if counts != {"1": 929, "2": 928}:
        raise RuntimeError("Two-fold membership changed")

    saved = _load_context_asset(cfg)
    empty, tracers = saved["empty_patient"], saved["tracer"]
    expected_empty = hashlib.sha256(empty.contiguous().numpy().tobytes()).hexdigest()
    if expected_empty != cfg["empty_patient_sha256"]:
        raise RuntimeError("Empty-patient tensor identity changed")
    contexts = [torch.stack((empty[0], tracers[i])) for i in range(2)]
    if not torch.equal(contexts[0][0], contexts[1][0]) or torch.equal(contexts[0][1], contexts[1][1]):
        raise RuntimeError("Tracer-only token invariants failed")

    sources = {
        "author_loss": inspect.getsource(full.author_loss),
        "validate": inspect.getsource(full.validate),
        "infer": inspect.getsource(full.command_infer),
    }
    if any("context_from_batch" not in source for source in sources.values()):
        raise RuntimeError("A train/validation/inference path bypasses the context hook")
    full_parity = Path(cfg["report"]) / "parity_receipt.json"
    if not full_parity.exists():
        raise RuntimeError("Run the preserved Full CUDA parity check against the control report first")
    parity = json.loads(full_parity.read_text())
    if parity.get("static_parity") != "PASS" or parity.get("cuda_numerical_parity") != "PASS":
        raise RuntimeError("Preserved Full CUDA parity did not pass")

    cache_receipt = json.loads((Path(cfg["report"]) / "persistent_cache_receipt.json").read_text())
    expected_namespace = f"v{full.PERSISTENT_CACHE_VERSION}_{cache_receipt['input_hashes_sha256'][:16]}_{cfg['full_conditions_sha256'][:16]}"
    cache_dir = Path(cfg["persistent_cache_root"]) / expected_namespace
    files = list(cache_dir.glob("*.pt"))
    if cache_receipt.get("cache_namespace") != expected_namespace or len(files) != len(cohort):
        raise RuntimeError("Completed Full persistent cache is not reusable")
    return {
        "condition_mode": MODE,
        "subjects": len(cohort),
        "fold_counts": counts,
        "frozen_artifacts_byte_identical": True,
        "empty_patient_fixed": True,
        "tracer_tokens_distinct": True,
        "context_hook_paths": sorted(sources),
        "preserved_full_cuda_parity": "PASS",
        "cache_namespace": expected_namespace,
        "cache_dir": str(cache_dir),
        "cache_files": len(files),
    }


def command_preflight(args) -> None:
    import torch
    from monai.data import DataLoader, PersistentDataset

    cfg, cohort = _load_control_config(args.config)
    result = _static_checks(cfg, cohort)
    receipt = json.loads((Path(cfg["report"]) / "persistent_cache_receipt.json").read_text())
    cache_dir = Path(cfg["persistent_cache_root"]) / receipt["cache_namespace"]
    before = _tree_identity(cache_dir)
    conditions = full.encode_conditions(cfg, cohort)
    dataset = PersistentDataset(data=cohort, transform=full.build_transform(conditions), cache_dir=cache_dir)
    started = time.monotonic()
    batch = next(iter(DataLoader(dataset, batch_size=1, shuffle=False, num_workers=0)))
    cache_read_seconds = time.monotonic() - started
    after = _tree_identity(cache_dir)
    if before != after or len(after) != len(cohort):
        raise RuntimeError("Preflight changed or expanded the completed Full cache")
    if tuple(batch["fdg_index"].shape) != (1, 2, 512) or tuple(batch["av45_index"].shape) != (1, 2, 512):
        raise RuntimeError("Cached Full contexts have unexpected shape")

    if not args.cuda:
        result.update(cache_reuse="PASS", cache_read_seconds=cache_read_seconds, cuda_preflight="NOT_RUN")
        full.json_write(Path(cfg["report"]) / "preflight_receipt.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return
    if not torch.cuda.is_available():
        raise RuntimeError("--cuda requested but CUDA is unavailable")
    full.require_training_hardware(cfg)

    import copy as copy_module
    torch.manual_seed(20261022)
    torch.cuda.manual_seed_all(20261022)
    model_control = full.new_model().cuda().float()
    model_reference = copy_module.deepcopy(model_control)
    small = {
        "mri": torch.rand(1, 1, 32, 32, 32),
        "fdg": torch.rand(1, 1, 32, 32, 32),
        "av45": torch.rand(1, 1, 32, 32, 32),
        "fdg_index": torch.rand(1, 2, 512),
        "av45_index": torch.rand(1, 2, 512),
    }
    saved = _activate(cfg)
    state = torch.cuda.get_rng_state()
    loss_a, timestep_a, _, _ = full.author_loss(model_control, small, 12)
    loss_a.backward()
    torch.cuda.set_rng_state(state)
    images, fdg, av45 = small["mri"].cuda(), small["fdg"].cuda(), small["av45"].cuda()
    torch.randint(0, 1000, (1,), device="cuda")
    with torch.amp.autocast("cuda", enabled=True):
        timestep = torch.randint(0, 1000, (1,), device="cuda").long()
        t = timestep.float() / 1000
        contexts = {tracer: _control_context_from_batch(small, tracer) for tracer in full.TRACERS}
        pred_fdg = model_reference(x=t * fdg + (1 - t) * images, timesteps=timestep, context=contexts["fdg"])
        pred_av45 = model_reference(x=t * av45 + (1 - t) * images, timesteps=timestep, context=contexts["av45"])
        loss_b = torch.nn.functional.mse_loss((fdg - images).float(), pred_fdg.float())
        loss_b = loss_b + torch.nn.functional.mse_loss((av45 - images).float(), pred_av45.float())
    loss_b.backward()
    pairs = [(a.grad, b.grad) for a, b in zip(model_control.parameters(), model_reference.parameters()) if a.grad is not None]
    loss_difference = float((loss_a - loss_b).abs())
    gradient_difference = max(float((a - b).abs().max()) for a, b in pairs)
    if timestep_a != int(timestep.item()) or loss_difference != 0.0 or not all(torch.allclose(a, b, rtol=1e-3, atol=1e-5) for a, b in pairs):
        raise RuntimeError("Tracer-only CUDA formula parity failed")
    del model_control, model_reference, small, loss_a, loss_b, pairs, images, fdg, av45, pred_fdg, pred_av45
    torch.cuda.empty_cache()

    torch.manual_seed(20261022)
    torch.cuda.manual_seed_all(20261022)
    torch.cuda.reset_peak_memory_stats()
    model = full.new_model().cuda()
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    scaler = torch.amp.GradScaler("cuda")
    optimizer.zero_grad(set_to_none=True)
    cached_full_patient = batch["fdg_index"][:, 0].clone()
    control_context = _control_context_from_batch(batch, "fdg")
    if torch.equal(cached_full_patient, control_context[:, 0].cpu()):
        raise RuntimeError("Cached Full patient token unexpectedly equals empty-patient token")
    loss, sample_timestep, has_fdg, has_av45 = full.author_loss(model, batch, 0)
    scaler.scale(loss).backward()
    scaler.step(optimizer)
    scaler.update()
    torch.cuda.synchronize()
    peak_allocated = torch.cuda.max_memory_allocated()
    peak_reserved = torch.cuda.max_memory_reserved()
    full.validate(model, [batch])
    model.eval()
    with torch.no_grad():
        inference_context = _control_context_from_batch(batch, "fdg")
        inference_velocity = model(
            x=batch["mri"].cuda(),
            timesteps=torch.zeros(1, device="cuda", dtype=torch.long),
            context=inference_context,
        )
    if tuple(inference_velocity.shape) != tuple(batch["mri"].shape):
        raise RuntimeError("Tracer-only inference-path output shape mismatch")
    if before != _tree_identity(cache_dir):
        raise RuntimeError("CUDA preflight changed the completed Full cache")
    result.update(
        cache_reuse="PASS",
        cache_read_seconds=cache_read_seconds,
        cache_tree_unchanged=True,
        cuda_preflight="PASS",
        cuda_formula_parity="PASS",
        loss_absolute_difference=loss_difference,
        max_gradient_abs_difference=gradient_difference,
        full_sample_ptid=cohort[0]["name"],
        full_sample_loss=float(loss.detach()),
        full_sample_timestep=sample_timestep,
        full_sample_has_fdg=has_fdg,
        full_sample_has_av45=has_av45,
        full_sample_peak_allocated_bytes=peak_allocated,
        full_sample_peak_reserved_bytes=peak_reserved,
        train_path_context_override="PASS",
        validation_path_context_override="PASS",
        inference_path_context_override="PASS",
        cached_full_patient_token_rejected=True,
        fixture_seed_only_not_formal_training=20261022,
        tracer_only_asset_source=saved["patient_encoding_call"],
    )
    full.json_write(Path(cfg["report"]) / "preflight_receipt.json", result)
    print(json.dumps(result, ensure_ascii=False))


def _delegate(args, command) -> None:
    cfg, _ = _load_control_config(args.config)
    _activate(cfg)
    command(args)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--full-config", type=Path, required=True)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--assets", type=Path, required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--config", type=Path, required=True)
    preflight.add_argument("--cuda", action="store_true")
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
    return p


def main() -> None:
    args = parser().parse_args()
    if args.action == "prepare":
        command_prepare(args)
    elif args.action == "preflight":
        command_preflight(args)
    elif args.action == "train":
        _delegate(args, full.command_train)
    elif args.action == "infer":
        _delegate(args, full.command_infer)
    elif args.action == "summarize":
        _delegate(args, full.command_summarize)


if __name__ == "__main__":
    main()
