"""Tabular-MLP clinical-token ablation on the completed Full DIReCT++ pipeline.

Only the patient-specific token is replaced.  The archived Full generator,
tracer token, preprocessing cache, loss, optimizer settings, schedule,
checkpoint cadence, inference, and metrics remain owned by
``experiments.original_author_reproduction.run``.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import types
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# ``report_error`` is an operator-local notification helper, not a scientific
# dependency.  Some portable replicas intentionally omit it; preserve the Full
# entrypoint's decorator interface without making training depend on email.
try:
    import report_error  # noqa: F401
except ModuleNotFoundError:
    notification = types.ModuleType("report_error")

    def _email_on_error(*_args, **_kwargs):
        return lambda function: function

    notification.email_on_error = _email_on_error
    sys.modules["report_error"] = notification

from experiments.original_author_reproduction import run as full  # noqa: E402


MODE = "tabular_mlp"
FEATURES = ("age", "sex", "weight", "cdr", "mmse", "gds", "faq", "npiq")
CONTINUOUS = ("age", "weight", "cdr", "mmse", "gds", "faq", "npiq")
SEX_ENCODING = {"female": 0.0, "male": 1.0}
MLP_HIDDEN_DIM = 128
MLP_OUTPUT_DIM = 512
SMOKE_MAX_STEPS = 8
_FULL_NEW_MODEL = full.new_model
_FULL_CHECKPOINT_IDENTITY = full.checkpoint_identity
_FULL_LOAD_CONFIG = full.load_config
_FULL_VERIFY_INPUT_RECEIPT = full.verify_input_receipt
_ACTIVE_MODEL = None
_ACTIVE_FOLD = None
_FEATURE_BY_PTID = None
_NORMALIZATION = None
_TRACERS = None


def _sha(path: Path) -> str:
    return full.sha256(path)


def _json_digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def _write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"No rows for {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary, path)


def parse_description(text: str) -> dict[str, float]:
    """Parse exactly the eight values rendered in the frozen Full prompt."""
    patterns = {
        "head": r"^Subject is a (?P<age>[-+0-9.]+)-year-old (?P<sex>male|female) with a weight of (?P<weight>[-+0-9.]+) kg\.",
        "cdr": r"Clinical Dementia Rating \(CDR\).*? is (?P<cdr>[-+0-9.]+)\. The Mini-Mental",
        "mmse": r"Mini-Mental State Examination \(MMSE\).*? is (?P<mmse>[-+0-9.]+)\. The Geriatric",
        "gds": r"Geriatric Depression Scale \(GDS\).*? is (?P<gds>[-+0-9.]+)\. The Functional",
        "faq": r"Functional Activities Questionnaire \(FAQ\).*? is (?P<faq>[-+0-9.]+)\. The Neuropsychiatric",
        "npiq": r"Neuropsychiatric Inventory Questionnaire \(NPI-Q\).*? is (?P<npiq>[-+0-9.]+)\.$",
    }
    values: dict[str, str] = {}
    for label, pattern in patterns.items():
        match = re.search(pattern, text)
        if match is None:
            raise ValueError(f"Description does not match the frozen Full template at {label}")
        values.update(match.groupdict())
    sex = values.pop("sex")
    parsed = {name: float(value) for name, value in values.items()}
    parsed["sex"] = SEX_ENCODING[sex]
    if set(parsed) != set(FEATURES) or not all(np.isfinite(value) for value in parsed.values()):
        raise ValueError("Missing or non-finite clinical value in frozen Full prompt")
    return {name: parsed[name] for name in FEATURES}


def fold_normalization(features: list[dict], held_out_fold: int) -> dict:
    training = [row for row in features if int(row["test_fold"]) != held_out_fold]
    held_out = [row for row in features if int(row["test_fold"]) == held_out_fold]
    if {row["ptid"] for row in training} & {row["ptid"] for row in held_out}:
        raise RuntimeError("Subject overlap while fitting clinical normalization")
    continuous = {}
    for name in CONTINUOUS:
        values = np.asarray([float(row[name]) for row in training], dtype=np.float64)
        mean = float(values.mean())
        scale = float(values.std(ddof=0))
        if not np.isfinite(mean) or not np.isfinite(scale):
            raise RuntimeError(f"Non-finite fold statistics for {name}")
        if scale == 0.0:
            scale = 1.0
        continuous[name] = {"mean": mean, "scale": scale}
    return {
        "fit_ptids": sorted(row["ptid"] for row in training),
        "held_out_ptids": sorted(row["ptid"] for row in held_out),
        "continuous": continuous,
        "sex_encoding": {"female": 0, "male": 1},
    }


def standardized_vector(feature: dict, normalization: dict) -> np.ndarray:
    values = []
    for name in FEATURES:
        value = float(feature[name])
        if name in CONTINUOUS:
            stats = normalization["continuous"][name]
            value = (value - float(stats["mean"])) / float(stats["scale"])
        values.append(value)
    result = np.asarray(values, dtype=np.float32)
    if result.shape != (8,) or not np.isfinite(result).all():
        raise RuntimeError("Invalid standardized clinical vector")
    return result


def _portable_load_config(path: Path) -> tuple[dict, list[dict]]:
    """Load frozen copied artifacts without requiring the 748 MB CLIP weight.

    Remote training consumes the already-created Full conditioning tensor and
    persistent cache.  Their identities, plus the archived notebook/model
    hashes recorded by the verified Full config, are checked directly.
    """
    cfg = json.loads(path.read_text())
    cfg["_config_sha256"] = _sha(path)
    report = Path(cfg["report"])
    checks = {
        report / "cohort.json": cfg["cohort_sha256"],
        report / "split_manifest.csv": cfg["split_manifest_sha256"],
        report / "input_hashes.csv": cfg["input_hashes_sha256"],
        report / "clinical_features.csv": cfg["clinical_features_sha256"],
        Path(cfg["assets"]) / "conditions.pt": cfg["full_conditions_sha256"],
        Path(__file__): cfg["tabular_source_sha256"],
        Path(full.__file__): cfg["base_training_source_sha256"],
        full.NOTEBOOK: cfg["source_contract"]["notebook_sha256"],
        full.MODEL_SOURCE: cfg["source_contract"]["model_source_sha256"],
    }
    for artifact, digest in checks.items():
        if not artifact.is_file() or _sha(artifact) != digest:
            raise RuntimeError(f"Frozen Tabular-MLP artifact changed or missing: {artifact}")
    cohort = json.loads((report / "cohort.json").read_text())
    if len(cohort) != 1857:
        raise RuntimeError("Expected the frozen 1,857-subject Full cohort")
    return cfg, cohort


def _cache_bound_input_receipt(cfg: dict, cohort: list[dict]) -> str:
    """Verify the Full input manifest and exact completed cache identity.

    This permits a remote fold to train from the byte-identical completed Full
    cache when the source NIfTI tree is not copied to that instance.
    """
    report = Path(cfg["report"])
    manifest = report / "input_hashes.csv"
    receipt = json.loads((report / "input_hashes_receipt.json").read_text())
    if _sha(manifest) != cfg["input_hashes_sha256"] or receipt["manifest_sha256"] != cfg["input_hashes_sha256"]:
        raise RuntimeError("Frozen Full input manifest identity changed")
    cache_receipt = json.loads((report / "persistent_cache_receipt.json").read_text())
    expected_namespace = f"v{full.PERSISTENT_CACHE_VERSION}_{cfg['input_hashes_sha256'][:16]}_{cfg['full_conditions_sha256'][:16]}"
    cache_dir = Path(cfg["persistent_cache_root"]) / expected_namespace
    files = list(cache_dir.glob("*.pt"))
    if (
        cache_receipt.get("cache_namespace") != expected_namespace
        or cache_receipt.get("subjects") != len(cohort)
        or len(files) != len(cohort)
    ):
        raise RuntimeError("Completed Full persistent cache identity is incomplete")
    return cfg["input_hashes_sha256"]


def _load_tabular_config(path: Path) -> tuple[dict, list[dict]]:
    cfg, cohort = _portable_load_config(path.resolve())
    if cfg.get("clinical_encoder") != MODE:
        raise RuntimeError("Not a frozen Tabular-MLP config")
    features = _read_csv(Path(cfg["report"]) / "clinical_features.csv")
    if len(features) != len(cohort):
        raise RuntimeError("Clinical feature table length differs from Full cohort")
    for subject, feature in zip(cohort, features):
        if subject["name"] != feature["ptid"] or int(subject["test_fold"]) != int(feature["test_fold"]):
            raise RuntimeError("Clinical feature identity/order differs from Full cohort")
        parsed = parse_description(subject["description"])
        if any(float(feature[name]) != parsed[name] for name in FEATURES):
            raise RuntimeError(f"Clinical feature differs from Full prompt: {subject['name']}")
    for fold in (1, 2):
        expected = fold_normalization(features, fold)
        if expected != cfg["fold_normalization"][str(fold)]:
            raise RuntimeError(f"Fold {fold} normalization is not training-fold-only")
    return cfg, cohort


def command_prepare(args) -> None:
    import torch

    full_config = args.full_config.resolve()
    full_cfg = json.loads(full_config.read_text())
    full_report = full_config.parent
    out, assets = args.out.resolve(), args.assets.resolve()
    conditions_source = args.conditions.resolve()
    cache_root = args.cache_root.resolve()
    if not re.fullmatch(r"[0-9a-f]{40}", args.commit):
        raise ValueError("--commit must be the deployed 40-character Git SHA")
    if out.exists() or assets.exists():
        raise RuntimeError("Tabular-MLP report/assets already exist; refusing to overwrite")
    required = ("cohort.json", "split_manifest.csv", "split_receipt.json", "input_hashes.csv", "input_hashes_receipt.json")
    for name in required:
        if not (full_report / name).is_file():
            raise RuntimeError(f"Missing frozen Full artifact: {full_report / name}")
    if _sha(full_report / "cohort.json") != full_cfg["cohort_sha256"]:
        raise RuntimeError("Frozen Full cohort hash mismatch")
    if _sha(full_report / "split_manifest.csv") != full_cfg["split_manifest_sha256"]:
        raise RuntimeError("Frozen Full split hash mismatch")
    input_receipt = json.loads((full_report / "input_hashes_receipt.json").read_text())
    if _sha(full_report / "input_hashes.csv") != input_receipt["manifest_sha256"]:
        raise RuntimeError("Frozen Full input manifest hash mismatch")
    conditions = torch.load(conditions_source, map_location="cpu", weights_only=False)
    cohort = json.loads((full_report / "cohort.json").read_text())
    if conditions.get("ptids") != [row["name"] for row in cohort]:
        raise RuntimeError("Full condition PTID order differs from cohort")
    if tuple(conditions["patient"].shape) != (1857, 512) or tuple(conditions["tracer"].shape) != (2, 512):
        raise RuntimeError("Unexpected Full condition tensor shape")
    if not torch.isfinite(conditions["tracer"]).all() or torch.equal(conditions["tracer"][0], conditions["tracer"][1]):
        raise RuntimeError("Invalid Full tracer tokens")

    features = []
    for index, subject in enumerate(cohort):
        parsed = parse_description(subject["description"])
        features.append({"paired_index": index, "ptid": subject["name"], "test_fold": subject["test_fold"], **parsed})
    normalizations = {str(fold): fold_normalization(features, fold) for fold in (1, 2)}
    out.mkdir(parents=True)
    assets.mkdir(parents=True)
    for name in required:
        shutil.copyfile(full_report / name, out / name)
    parity = full_report / "parity_receipt.json"
    if parity.is_file():
        shutil.copyfile(parity, out / "full_parity_receipt.json")
    _write_csv(out / "clinical_features.csv", features)
    shutil.copyfile(conditions_source, assets / "conditions.pt")
    conditions_digest = _sha(assets / "conditions.pt")
    if conditions_digest != _sha(conditions_source):
        raise RuntimeError("Copied Full conditions changed")

    full_cache_receipt = args.cache_receipt.resolve()
    cache_receipt = json.loads(full_cache_receipt.read_text())
    expected_namespace = f"v{full.PERSISTENT_CACHE_VERSION}_{input_receipt['manifest_sha256'][:16]}_{conditions_digest[:16]}"
    cache_dir = cache_root / expected_namespace
    cache_files = list(cache_dir.glob("*.pt"))
    if cache_receipt.get("cache_namespace") != expected_namespace or len(cache_files) != len(cohort):
        raise RuntimeError("The supplied cache is not the exact completed Full cache")
    shutil.copyfile(full_cache_receipt, out / "persistent_cache_receipt.json")

    config = {key: value for key, value in full_cfg.items() if not key.startswith("_")}
    config.update(
        experiment="directpp_tabular_mlp_ablation",
        report=str(out),
        assets=str(assets),
        persistent_cache_root=str(cache_root),
        input_hashes_sha256=input_receipt["manifest_sha256"],
        clinical_encoder=MODE,
        clinical_fields=list(FEATURES),
        continuous_fields=list(CONTINUOUS),
        categorical_encoding={"sex": {"female": 0, "male": 1}},
        missing_value_policy="reject: all eight values must be present and finite in the frozen Full prompt",
        clinical_provenance_limit="historical filled fields; upstream imputation and diagnosis dependence not recovered",
        fold_normalization=normalizations,
        clinical_features_sha256=_sha(out / "clinical_features.csv"),
        full_config=str(full_config),
        full_config_sha256=_sha(full_config),
        full_conditions_sha256=conditions_digest,
        tracer_token_source="byte-identical Full conditions.pt tracer tensor (actual Full uses raw BiomedCLIP text features)",
        tracer_adapter_claim=False,
        cache_input_policy="exact completed Full persistent cache bound to frozen input-manifest and condition hashes",
        git_commit=args.commit,
        mlp={"input_dim": 8, "hidden_dim": MLP_HIDDEN_DIM, "output_dim": MLP_OUTPUT_DIM,
             "layers": "Linear(8,128), GELU, Linear(128,512)", "clinical_tokens": 1},
        base_training_source_sha256=_sha(Path(full.__file__)),
        tabular_source_sha256=_sha(Path(__file__)),
        status="PREPARED_NOT_TRAINED",
    )
    full.json_write(out / "config.json", config)
    full.json_write(
        out / "prepare_receipt.json",
        {
            "status": "PASS",
            "subjects": len(cohort),
            "fold_counts": config["fold_counts"],
            "clinical_fields": list(FEATURES),
            "missing_values": 0,
            "diagnosis_input": False,
            "pet_input": False,
            "fold_input": False,
            "full_split_reused_not_regenerated": True,
            "full_conditions_sha256": conditions_digest,
            "tracer_shape": list(conditions["tracer"].shape),
            "cache_namespace": expected_namespace,
            "cache_files": len(cache_files),
            "git_commit": args.commit,
            "config_sha256": _sha(out / "config.json"),
        },
    )
    print(json.dumps({"config": str(out / "config.json"), "assets": str(assets), "status": "PASS"}))


def _tabular_new_model():
    global _ACTIVE_MODEL
    import torch
    from torch import nn

    class TabularConditionedGenerator(nn.Module):
        def __init__(self):
            super().__init__()
            # Instantiate the generator first so its RNG consumption and initial
            # weights remain identical to a Full model created from the same RNG.
            self.generator = _FULL_NEW_MODEL()
            self.clinical_encoder = nn.Sequential(
                nn.Linear(len(FEATURES), MLP_HIDDEN_DIM),
                nn.GELU(),
                nn.Linear(MLP_HIDDEN_DIM, MLP_OUTPUT_DIM),
            )

        def forward(self, *args, **kwargs):
            return self.generator(*args, **kwargs)

    _ACTIVE_MODEL = TabularConditionedGenerator()
    return _ACTIVE_MODEL


def _tabular_context_from_batch(batch, tracer: str):
    import torch

    if tracer not in full.TRACERS or any(value is None for value in (_ACTIVE_MODEL, _FEATURE_BY_PTID, _NORMALIZATION, _TRACERS)):
        raise RuntimeError("Tabular-MLP runtime context is not activated")
    cached = batch[f"{tracer}_index"]
    if tuple(cached.shape[-2:]) != (2, 512):
        raise RuntimeError("Unexpected cached Full context shape")
    names = list(batch["name"])
    device = next(_ACTIVE_MODEL.parameters()).device
    clinical = torch.from_numpy(
        np.stack([standardized_vector(_FEATURE_BY_PTID[name], _NORMALIZATION) for name in names])
    ).to(device)
    patient = _ACTIVE_MODEL.clinical_encoder(clinical).unsqueeze(1)
    index = full.TRACERS.index(tracer)
    tracer_token = _TRACERS[index].to(device).expand(len(names), 1, -1)
    cached_tracer = cached[:, 1].detach().cpu()
    if not torch.equal(cached_tracer, _TRACERS[index].expand(len(names), -1)):
        raise RuntimeError("Cached tracer token differs from frozen Full tracer token")
    context = torch.cat((patient, tracer_token), dim=1)
    if tuple(context.shape) != (len(names), 2, 512) or not torch.isfinite(context).all():
        raise RuntimeError("Invalid Tabular-MLP cross-attention context")
    return context


def _tabular_checkpoint_identity(cfg: dict, fold: int) -> dict:
    identity = _FULL_CHECKPOINT_IDENTITY(cfg, fold)
    identity.update(
        clinical_encoder=MODE,
        clinical_features_sha256=cfg["clinical_features_sha256"],
        fold_normalization_sha256=_json_digest(cfg["fold_normalization"][str(fold)]),
        full_conditions_sha256=cfg["full_conditions_sha256"],
        base_training_source_sha256=cfg["base_training_source_sha256"],
        tabular_source_sha256=cfg["tabular_source_sha256"],
    )
    return identity


def _activate(cfg: dict, fold: int) -> None:
    global _ACTIVE_FOLD, _FEATURE_BY_PTID, _NORMALIZATION, _TRACERS
    import torch

    if fold not in (1, 2):
        raise ValueError("fold must be 1 or 2")
    features = _read_csv(Path(cfg["report"]) / "clinical_features.csv")
    _FEATURE_BY_PTID = {row["ptid"]: row for row in features}
    _NORMALIZATION = cfg["fold_normalization"][str(fold)]
    _ACTIVE_FOLD = fold
    conditions = torch.load(Path(cfg["assets"]) / "conditions.pt", map_location="cpu", weights_only=False)
    _TRACERS = conditions["tracer"].detach().float().clone()
    if tuple(_TRACERS.shape) != (2, 512) or not torch.isfinite(_TRACERS).all():
        raise RuntimeError("Invalid frozen Full tracer tensor")
    full.new_model = _tabular_new_model
    full.context_from_batch = _tabular_context_from_batch
    full.checkpoint_identity = _tabular_checkpoint_identity
    full.load_config = _portable_load_config
    full.verify_input_receipt = _cache_bound_input_receipt


def _static_checks(cfg: dict, cohort: list[dict]) -> dict:
    import inspect
    import torch

    features = _read_csv(Path(cfg["report"]) / "clinical_features.csv")
    counts = {str(fold): sum(int(row["test_fold"]) == fold for row in cohort) for fold in (1, 2)}
    if counts != cfg["fold_counts"] or counts != {"1": 929, "2": 928}:
        raise RuntimeError("Full two-fold membership changed")
    for fold in (1, 2):
        normalization = cfg["fold_normalization"][str(fold)]
        train = set(normalization["fit_ptids"])
        test = set(normalization["held_out_ptids"])
        expected_train = {row["name"] for row in cohort if int(row["test_fold"]) != fold}
        expected_test = {row["name"] for row in cohort if int(row["test_fold"]) == fold}
        if train != expected_train or test != expected_test or train & test:
            raise RuntimeError(f"Fold {fold} train/test or normalization membership mismatch")
        if fold_normalization(features, fold) != normalization:
            raise RuntimeError(f"Fold {fold} normalization leakage check failed")
    if cfg["learning_rate"] != 2.5e-5 or cfg["batch_size"] != 1 or cfg["epochs"] != 200:
        raise RuntimeError("Training budget differs from completed Full")
    if cfg["primary_epoch"] != 165 or cfg["secondary_epoch"] != 200 or cfg["distill_start_epoch_zero_based"] != 140:
        raise RuntimeError("Training schedule differs from completed Full")
    sources = {name: inspect.getsource(function) for name, function in {
        "author_loss": full.author_loss, "validate": full.validate, "infer": full.command_infer}.items()}
    if any("context_from_batch" not in source for source in sources.values()):
        raise RuntimeError("A train/validation/inference path bypasses the context hook")
    conditions = torch.load(Path(cfg["assets"]) / "conditions.pt", map_location="cpu", weights_only=False)
    if _sha(Path(cfg["assets"]) / "conditions.pt") != cfg["full_conditions_sha256"]:
        raise RuntimeError("Full condition tensor changed")
    _cache_bound_input_receipt(cfg, cohort)
    return {
        "status": "PASS",
        "subjects": len(cohort),
        "fold_counts": counts,
        "clinical_fields": list(FEATURES),
        "clinical_input_shape": [1, 8],
        "patient_token_shape": [1, 1, 512],
        "tracer_token_shape": [1, 1, 512],
        "cross_attention_shape": [1, 2, 512],
        "missing_values": 0,
        "normalization_train_fold_only": True,
        "fold_train_test_overlap": {"1": 0, "2": 0},
        "tracer_tensor_sha256": hashlib.sha256(conditions["tracer"].contiguous().numpy().tobytes()).hexdigest(),
        "tracer_tokens_byte_identical_to_full": True,
        "base_full_trainer_sha256": cfg["base_training_source_sha256"],
        "base_full_trainer_unmodified": _sha(Path(full.__file__)) == cfg["base_training_source_sha256"],
        "context_hook_paths": sorted(sources),
        "cache_verification": "PASS",
    }


def command_preflight(args) -> None:
    import torch

    cfg, cohort = _load_tabular_config(args.config)
    result = _static_checks(cfg, cohort)
    _activate(cfg, args.fold)
    if not args.cuda:
        result.update(fold=args.fold, cuda_smoke="NOT_RUN")
        full.json_write(Path(cfg["report"]) / f"preflight_fold{args.fold}.json", result)
        print(json.dumps(result, ensure_ascii=False))
        return
    if not torch.cuda.is_available():
        raise RuntimeError("--cuda requested but CUDA is unavailable")
    full.require_training_hardware(cfg)
    seed = 20261028 + args.fold
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    reference = _FULL_NEW_MODEL().cuda().eval()
    reference_hash = full.state_hash(reference.state_dict())
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    model = full.new_model().cuda().train()
    generator_hash = full.state_hash(model.generator.state_dict())
    if reference_hash != generator_hash:
        raise RuntimeError("Tabular wrapper changed same-seed Full generator initialization")
    del reference
    torch.cuda.empty_cache()

    parameter_counts = {
        "generator": sum(parameter.numel() for parameter in model.generator.parameters()),
        "clinical_mlp": sum(parameter.numel() for parameter in model.clinical_encoder.parameters()),
        "total": sum(parameter.numel() for parameter in model.parameters()),
    }
    expected_mlp = 8 * 128 + 128 + 128 * 512 + 512
    if parameter_counts["clinical_mlp"] != expected_mlp:
        raise RuntimeError("Unexpected Clinical MLP parameter count")
    sid = cfg["fold_normalization"][str(args.fold)]["fit_ptids"][0]
    tracer = _TRACERS
    small = {
        "name": [sid],
        "mri": torch.rand(1, 1, 32, 32, 32),
        "fdg": torch.rand(1, 1, 32, 32, 32),
        "av45": torch.rand(1, 1, 32, 32, 32),
        "fdg_index": torch.stack((_TRACERS[0], _TRACERS[0])).unsqueeze(0),
        "av45_index": torch.stack((_TRACERS[1], _TRACERS[1])).unsqueeze(0),
    }
    optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
    scaler = torch.amp.GradScaler("cuda")
    gradient_l2_by_step = []
    first_nonzero_step = None
    for smoke_step in range(1, SMOKE_MAX_STEPS + 1):
        optimizer.zero_grad(set_to_none=True)
        loss, timestep, has_fdg, has_av45 = full.author_loss(model, small, 0)
        scaler.scale(loss).backward()
        scaler.unscale_(optimizer)
        gradients = [parameter.grad for parameter in model.clinical_encoder.parameters()]
        if not gradients or any(gradient is None or not torch.isfinite(gradient).all() for gradient in gradients):
            raise RuntimeError("Clinical MLP has missing or non-finite gradients")
        gradient_l2 = float(torch.sqrt(sum((gradient.float() ** 2).sum() for gradient in gradients)))
        gradient_l2_by_step.append(gradient_l2)
        # The Full generator has a zero-initialized output layer, so step 1 may
        # legitimately produce zero conditioning gradients.  Apply the same
        # optimizer update as formal training and require a later non-zero MLP
        # gradient before allowing launch.
        scaler.step(optimizer)
        scaler.update()
        if gradient_l2 > 0:
            first_nonzero_step = smoke_step
            break
    if first_nonzero_step is None:
        raise RuntimeError(f"Clinical MLP gradient remained zero after {SMOKE_MAX_STEPS} optimizer steps")
    model.eval()
    with torch.no_grad():
        context_before = _tabular_context_from_batch(small, "fdg")
        prediction_before = model(
            x=small["mri"].cuda(), timesteps=torch.zeros(1, device="cuda", dtype=torch.long), context=context_before
        ).float().cpu()
    if not torch.equal(context_before[:, 1].cpu(), tracer[0].unsqueeze(0)):
        raise RuntimeError("Tracer token changed in Tabular-MLP context")

    with tempfile.TemporaryDirectory(dir=cfg["report"]) as temporary:
        checkpoint = Path(temporary) / "smoke.pt"
        torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(), "fold": args.fold}, checkpoint)
        state = torch.load(checkpoint, map_location="cpu", weights_only=False)
        reloaded = full.new_model().cuda().eval()
        reloaded.load_state_dict(state["model"])
        reloaded_optimizer = torch.optim.Adam(reloaded.parameters(), lr=cfg["learning_rate"])
        reloaded_optimizer.load_state_dict(state["optimizer"])
        with torch.no_grad():
            context_after = _tabular_context_from_batch(small, "fdg")
            prediction_after = reloaded(
                x=small["mri"].cuda(), timesteps=torch.zeros(1, device="cuda", dtype=torch.long), context=context_after
            ).float().cpu()
        reload_max_abs = float((prediction_before - prediction_after).abs().max())
        checkpoint_sha256 = _sha(checkpoint)
    if reload_max_abs != 0.0:
        raise RuntimeError("Checkpoint reload changed inference output")
    result.update(
        fold=args.fold,
        cuda_smoke="PASS",
        fixture_seed_only_not_formal_training=seed,
        parameters=parameter_counts,
        same_seed_full_generator_initialization="PASS",
        patient_token_shape=list(context_before[:, :1].shape),
        tracer_token_shape=list(context_before[:, 1:].shape),
        cross_attention_shape=list(context_before.shape),
        mlp_gradient_l2=gradient_l2,
        mlp_gradient_l2_by_step=gradient_l2_by_step,
        mlp_first_nonzero_step=first_nonzero_step,
        mlp_gradient_nonzero_finite=True,
        loss=float(loss.detach()),
        timestep=timestep,
        has_fdg=has_fdg,
        has_av45=has_av45,
        optimizer_step="PASS",
        checkpoint_reload="PASS",
        checkpoint_sha256=checkpoint_sha256,
        inference_reload_max_abs=reload_max_abs,
        tracer_unchanged_in_runtime_context=True,
        inference_uses_same_fold_normalization=True,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(),
        peak_reserved_bytes=torch.cuda.max_memory_reserved(),
    )
    full.json_write(Path(cfg["report"]) / f"preflight_fold{args.fold}.json", result)
    print(json.dumps(result, ensure_ascii=False))


def _delegate(args, command) -> None:
    cfg, _ = _load_tabular_config(args.config)
    _activate(cfg, args.fold)
    command(args)


def command_summarize(args) -> None:
    cfg, _ = _load_tabular_config(args.config)
    # Summary needs no model/context activation and remains the Full evaluator.
    saved_loader = full.load_config
    full.load_config = _portable_load_config
    try:
        full.command_summarize(args)
    finally:
        full.load_config = saved_loader
    completion = Path(cfg["report"]) / "oof_summary/completion.json"
    saved = json.loads(completion.read_text())
    saved.update(experiment=cfg["experiment"], clinical_encoder=MODE,
                 full_vs_mlp_only_scientific_difference="subject patient token encoder")
    full.json_write(completion, saved)


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--full-config", type=Path, required=True)
    prepare.add_argument("--conditions", type=Path, required=True)
    prepare.add_argument("--cache-root", type=Path, required=True)
    prepare.add_argument("--cache-receipt", type=Path, required=True)
    prepare.add_argument("--commit", required=True)
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--assets", type=Path, required=True)
    preflight = sub.add_parser("preflight")
    preflight.add_argument("--config", type=Path, required=True)
    preflight.add_argument("--fold", type=int, required=True)
    preflight.add_argument("--cuda", action="store_true")
    train = sub.add_parser("train")
    train.add_argument("--config", type=Path, required=True)
    train.add_argument("--fold", type=int, required=True)
    train.add_argument("--resume", type=Path)
    infer = sub.add_parser("infer")
    infer.add_argument("--config", type=Path, required=True)
    infer.add_argument("--fold", type=int, required=True)
    infer.add_argument("--epoch", type=int, required=True)
    infer.add_argument("--cache-dir", type=Path)
    summarize = sub.add_parser("summarize")
    summarize.add_argument("--config", type=Path, required=True)
    return parser


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
        command_summarize(args)


if __name__ == "__main__":
    main()
