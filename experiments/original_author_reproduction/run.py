"""Isolated replay of the archived DIReCT++ author training cells.

The scientific computation follows zero-based cells 1, 2, 4, 8, 9, and 11 of
``mri2pet _two trace_new-final.ipynb``.  Path mapping, receipts, resumable state,
and the reconstructed two-fold split are new engineering controls.  This file
does not import the E1 reproduction.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import shutil
import socket
import sys
import time
from pathlib import Path

import numpy as np
from report_error import email_on_error


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb"
AUTHOR_ROOT = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo"
MODEL_SOURCE = AUTHOR_ROOT / "generative/networks/nets/diffusion_model_unet.py"
BIOMEDCLIP = ROOT / "results/checkpoints/vscode-3002/home/ssddata/liutuo/BiomedCLIP"
BIOMEDCLIP_CONFIG_SOURCE = AUTHOR_ROOT / "BiomedCLIP"
DEFAULT_DATA = Path("/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45")
TRACERS = ("fdg", "av45")
SOURCE_CELLS = (1, 2, 4, 8, 9, 11)
PERSISTENT_CACHE_VERSION = 1
NOTEBOOK_SHA256 = "6ce109159da4b04758146170d0968e2b42d5f2cd79a03192da8de11f0a5edd1f"
MODEL_SOURCE_SHA256 = "b56b1956b787e85f52fc1a7f46884fea2cbfff81f9c31311db462dda7b378bcc"
BIOMEDCLIP_SHA256 = "8d6e9edd227566b056eef0c682bb13f9e501364c1c29b8ccb06986a9ffb5cfbb"
BIOMEDCLIP_CONFIG_SHA256 = {
    "config.json": "1de3d38ac5ede7babaf72d68e45c00e5bdbf5240c5b50fcec259c79375367431",
    "configuration_biomed_clip.py": "b88965dbee5b83196eef13c3adc20dc0a5c96736bee14d487cc61809a759257b",
    "modeling_biomed_clip.py": "4f4afdf5418d70a6198da6a8e4d59453cf37d3c694c793f71f5b9bdbb0b258a1",
    "preprocessor_config.json": "b73eb29108ff586ec6e81abf6149cd24132ceac0eae76ca20b3f3004e848a4c4",
    "processing_biomed_clip.py": "22fb0c0ef2324137a441081034ab0d37a95f077ab2fe3d29e29ac4eda6517e0c",
    "tokenizer.json": "defc1f91456606e7847af3a2fb4a8abb96441423aa5407a52498395ea68327ff",
    "tokenizer_config.json": "e1790949631401af1bfb6c9c7aeec7fcf612e274d73579d99f704faea40c8ba7",
}

FDG_TEXT = (
    "FDG PET is a functional brain imaging technique that visualizes the dynamic changes in glucose metabolism, "
    "directly linked to neuronal energy demands and synaptic activity. It serves as a tool to assess functional "
    "connectivity and energy utilization across brain regions. Areas with decreased metabolic activity, such as "
    "those affected by neurodegenerative diseases, should exhibit reduced signal intensity. High-intensity "
    "metabolic hotspots in gray matter (e.g., the cerebral cortex and basal ganglia) are key markers of neuronal activity. "
)
AV45_TEXT = (
    "AV45 PET is a molecular imaging technique that highlights the static distribution of amyloid-beta plaques, "
    "a critical pathological marker of Alzheimer's disease. This imaging modality provides a spatial map of amyloid "
    "deposition in cortical regions (e.g., the temporal, parietal, and frontal lobes) and can distinguish amyloid-positive "
    "areas from amyloid-negative white matter regions. The primary focus is on identifying amyloid deposition patterns "
    "to assess disease progression and pathological burden."
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def json_write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def csv_write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        raise ValueError(f"No rows for {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, path)


def assert_source_contract() -> dict:
    if sha256(NOTEBOOK) != NOTEBOOK_SHA256:
        raise RuntimeError("Archived author notebook hash changed")
    if sha256(MODEL_SOURCE) != MODEL_SOURCE_SHA256:
        raise RuntimeError("Archived DiffusionModelUNet source hash changed")
    weight = BIOMEDCLIP / "model.safetensors"
    if sha256(weight) != BIOMEDCLIP_SHA256:
        raise RuntimeError("Archived BiomedCLIP weight hash changed")
    for name, digest in BIOMEDCLIP_CONFIG_SHA256.items():
        if sha256(BIOMEDCLIP_CONFIG_SOURCE / name) != digest:
            raise RuntimeError(f"Archived BiomedCLIP configuration changed: {name}")
    notebook = json.loads(NOTEBOOK.read_text())
    source = {i: "".join(notebook["cells"][i]["source"]) for i in SOURCE_CELLS}
    required = {
        1: [FDG_TEXT.strip(), AV45_TEXT.strip(), "model.get_text_features(**inputs_optimized)"],
        2: ["test_size=1, random_state=42", "max_length=256", "model.get_text_features(text_inputs['input_ids'])"],
        4: ["HistogramNormalized(keys=[\"mri\"])", "batch_size=1, shuffle=True", "ScaleIntensityd"],
        8: ["num_channels=(32,64,64,128)", "cross_attention_dim=512", "use_flash_attention=True"],
        9: ["n_epochs = 200", "if epoch >= 140", "loss = alpha * loss_fdg + beta * loss_av45"],
        11: ["kernel_size=7", "PSNRMetric(max_val=1.0)", "checkpoint_path"],
    }
    for cell, snippets in required.items():
        for snippet in snippets:
            if snippet not in source[cell]:
                raise RuntimeError(f"Author source contract missing cell {cell}: {snippet}")
    return {
        "notebook": str(NOTEBOOK.relative_to(ROOT)),
        "notebook_sha256": NOTEBOOK_SHA256,
        "cells_zero_based": list(SOURCE_CELLS),
        "model_source": str(MODEL_SOURCE.relative_to(ROOT)),
        "model_source_sha256": MODEL_SOURCE_SHA256,
        "biomedclip": str(BIOMEDCLIP.relative_to(ROOT)),
        "biomedclip_model_sha256": BIOMEDCLIP_SHA256,
        "biomedclip_config_sha256": BIOMEDCLIP_CONFIG_SHA256,
    }


def subject_id(filename: str) -> str:
    parts = filename.split("_")
    if len(parts) < 3:
        raise ValueError(filename)
    return "_".join(parts[:3])


def build_paired_data(data_root: Path) -> list[dict]:
    import pandas as pd

    metadata = pd.read_csv(data_root / "filtered_subjects_with_description.csv")
    if metadata["Subject ID"].duplicated().any():
        raise RuntimeError("Duplicate Subject ID in metadata")
    descriptions = metadata.set_index("Subject ID")["Description"].to_dict()
    folders = {
        "mri": data_root / "mri_strip_registered",
        "av45": data_root / "PET1_AV45_strip_registered",
        "fdg": data_root / "PET2_FDG_strip_registered",
    }
    indexed = {}
    for modality, folder in folders.items():
        files = sorted(p for p in folder.iterdir() if p.name.endswith(".nii.gz"))
        mapping = {}
        for path in files:
            sid = subject_id(path.name)
            if sid in mapping:
                raise RuntimeError(f"Duplicate {modality} candidate for {sid}")
            mapping[sid] = path.resolve()
        indexed[modality] = mapping

    paired = []
    # This follows cell 2: sorted MRI filenames establish paired_data order.
    for sid, mri in indexed["mri"].items():
        if sid not in indexed["av45"] or sid not in indexed["fdg"]:
            continue
        description = descriptions.get(sid)
        if not isinstance(description, str) or not description:
            raise RuntimeError(f"Missing description for {sid}")
        index = len(paired)
        paired.append(
            {
                "name": sid,
                "mri": str(mri),
                "av45": str(indexed["av45"][sid]),
                "fdg": str(indexed["fdg"][sid]),
                "description": description,
                "fdg_index": index,
                "av45_index": index,
            }
        )
    if len(paired) != 1857 or len({r["name"] for r in paired}) != 1857:
        raise RuntimeError(f"Expected 1857 unique paired subjects, got {len(paired)}")
    return paired


def command_prepare(args) -> None:
    from sklearn.model_selection import KFold, train_test_split

    out, assets = args.out.resolve(), args.assets.resolve()
    if out.exists() or assets.exists():
        raise RuntimeError("Output/report path already exists; choose a new run identity")
    out.mkdir(parents=True)
    assets.mkdir(parents=True)
    source = assert_source_contract()
    paired = build_paired_data(args.data_root.resolve())

    historical_train, historical_val = train_test_split(paired, test_size=1, random_state=42)
    if len(historical_train) != 1856 or len(historical_val) != 1 or historical_val[0]["name"] != "011_S_4105":
        raise RuntimeError("Original 1856/1 seed/order cross-check failed")

    fold_of = {}
    split = KFold(n_splits=2, shuffle=True, random_state=42)
    for fold, (_, held_out) in enumerate(split.split(np.arange(len(paired))), 1):
        for index in held_out:
            sid = paired[int(index)]["name"]
            if sid in fold_of:
                raise RuntimeError(f"Duplicate held-out assignment: {sid}")
            fold_of[sid] = fold
    if len(fold_of) != len(paired):
        raise RuntimeError("Two-fold assignment does not cover the cohort")
    cohort = [dict(row, test_fold=fold_of[row["name"]]) for row in paired]
    counts = {str(f): sum(r["test_fold"] == f for r in cohort) for f in (1, 2)}
    if sorted(counts.values()) != [928, 929]:
        raise RuntimeError(f"Unexpected fold sizes: {counts}")

    json_write(out / "cohort.json", cohort)
    split_rows = [
        {
            "paired_index": i,
            "ptid": row["name"],
            "test_fold": row["test_fold"],
            "mri": row["mri"],
            "fdg": row["fdg"],
            "av45": row["av45"],
        }
        for i, row in enumerate(cohort)
    ]
    csv_write(out / "split_manifest.csv", split_rows)
    config = {
        "experiment": "original_author_training_reconstruction",
        "report": str(out),
        "assets": str(assets),
        "data_root": str(args.data_root.resolve()),
        "source_contract": source,
        "split_algorithm": "KFold(n_splits=2, shuffle=True, random_state=42)",
        "split_seed": 42,
        "stratified": False,
        "historical_1856_1_validation_ptid": historical_val[0]["name"],
        "training_seed": None,
        "training_seed_policy": "author_notebook_unseeded_user_selected",
        "epochs": 200,
        "primary_epoch": 165,
        "secondary_epoch": 200,
        "distill_start_epoch_zero_based": 140,
        "val_interval": 10,
        "learning_rate": 2.5e-5,
        "batch_size": 1,
        "persistent_cache_root": str((ROOT / "results/cache/original_author_reproduction").resolve()),
        "fold_counts": counts,
        "expected_effective": {"fdg": 1598, "av45": 1365},
        "minimum_gpu_total_bytes": 47 * 1024**3,
        "minimum_gpu_free_bytes": 45 * 1024**3,
        "minimum_host_available_bytes": 16 * 1024**3,
        "cohort_sha256": sha256(out / "cohort.json"),
        "split_manifest_sha256": sha256(out / "split_manifest.csv"),
        "status": "PREPARED_NOT_ENCODED_NOT_TRAINED",
    }
    json_write(out / "config.json", config)
    json_write(
        out / "split_receipt.json",
        {
            "protocol": "reconstructed author-described two-fold OOF",
            "historical_identity_claim": False,
            "fold_counts": counts,
            "unique_ptids": len(cohort),
            "held_out_union_complete": True,
            "held_out_intersection_count": 0,
            "historical_1856_1_crosscheck": {"train": len(historical_train), "val": historical_val[0]["name"]},
        },
    )
    print(json.dumps({"prepared": str(out), "assets": str(assets), "fold_counts": counts}))


def load_config(path: Path) -> tuple[dict, list[dict]]:
    cfg = json.loads(path.read_text())
    cfg["_config_sha256"] = sha256(path)
    out = Path(cfg["report"])
    if sha256(out / "cohort.json") != cfg["cohort_sha256"]:
        raise RuntimeError("Frozen cohort changed")
    if sha256(out / "split_manifest.csv") != cfg["split_manifest_sha256"]:
        raise RuntimeError("Frozen split manifest changed")
    assert_source_contract()
    return cfg, json.loads((out / "cohort.json").read_text())


def command_hash_inputs(args) -> None:
    cfg, cohort = load_config(args.config.resolve())
    out = Path(cfg["report"])
    manifest = out / "input_hashes.csv"
    receipt = out / "input_hashes_receipt.json"
    if manifest.exists() or receipt.exists():
        raise RuntimeError("Input hash receipt already exists; do not overwrite provenance")
    rows = []
    started = time.monotonic()
    for number, row in enumerate(cohort, 1):
        for modality in ("mri", "fdg", "av45"):
            path = Path(row[modality])
            stat = path.stat()
            rows.append(
                {
                    "ptid": row["name"],
                    "kind": modality,
                    "path": str(path),
                    "sha256": sha256(path),
                    "bytes": stat.st_size,
                    "mtime_ns": stat.st_mtime_ns,
                }
            )
        if number % 100 == 0:
            print(json.dumps({"hashed_subjects": number, "elapsed_seconds": time.monotonic() - started}), flush=True)
    csv_write(manifest, rows)
    json_write(
        receipt,
        {
            "files": len(rows),
            "subjects": len(cohort),
            "manifest_sha256": sha256(manifest),
            "elapsed_seconds": time.monotonic() - started,
            "direct_content_hashing": True,
        },
    )
    print(json.dumps(json.loads(receipt.read_text())))


def verify_input_receipt(cfg: dict, cohort: list[dict]) -> str:
    import pandas as pd

    out = Path(cfg["report"])
    manifest = out / "input_hashes.csv"
    receipt = out / "input_hashes_receipt.json"
    if not manifest.exists() or not receipt.exists():
        raise RuntimeError("Run hash-inputs before encoding or training")
    saved = json.loads(receipt.read_text())
    digest = sha256(manifest)
    if digest != saved["manifest_sha256"]:
        raise RuntimeError("Input hash manifest changed")
    rows = pd.read_csv(manifest)
    if len(rows) != len(cohort) * 3 or rows.duplicated(["ptid", "kind"]).any():
        raise RuntimeError("Input hash manifest identity is incomplete or duplicated")
    expected = {(r["name"], kind): r[kind] for r in cohort for kind in ("mri", "fdg", "av45")}
    for row in rows.itertuples(index=False):
        key = (row.ptid, row.kind)
        path = Path(row.path)
        stat = path.stat()
        if expected.get(key) != row.path or stat.st_size != row.bytes or stat.st_mtime_ns != row.mtime_ns:
            raise RuntimeError(f"Frozen input identity/stat changed: {key}")
    return digest


def hardware() -> dict:
    import torch

    result = {
        "host": socket.gethostname(),
        "pid": os.getpid(),
        "cuda_visible_devices": os.environ.get("CUDA_VISIBLE_DEVICES"),
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
    }
    if torch.cuda.is_available():
        free, total = torch.cuda.mem_get_info()
        gpu_uuid = getattr(torch.cuda.get_device_properties(0), "uuid", None)
        result.update(
            gpu=torch.cuda.get_device_name(0),
            gpu_uuid=str(gpu_uuid) if gpu_uuid is not None else None,
            gpu_free_bytes=free,
            gpu_total_bytes=total,
        )
    return result


def ensure_biomedclip_bundle(cfg: dict) -> Path:
    bundle = Path(cfg["assets"]) / "biomedclip"
    bundle.mkdir(exist_ok=True)
    for name, digest in BIOMEDCLIP_CONFIG_SHA256.items():
        source = BIOMEDCLIP_CONFIG_SOURCE / name
        target = bundle / name
        if not target.exists():
            shutil.copyfile(source, target)
        if sha256(target) != digest:
            raise RuntimeError(f"BiomedCLIP bundle mismatch: {name}")
    weight = bundle / "model.safetensors"
    if not weight.exists():
        weight.symlink_to((BIOMEDCLIP / "model.safetensors").resolve())
    if sha256(weight) != BIOMEDCLIP_SHA256:
        raise RuntimeError("BiomedCLIP bundle weight mismatch")
    receipt = {
        "path": str(bundle),
        "files": {name: sha256(bundle / name) for name in BIOMEDCLIP_CONFIG_SHA256},
        "model.safetensors": sha256(weight),
        "weight_link_target": str(weight.resolve()),
    }
    json_write(Path(cfg["report"]) / "biomedclip_bundle.json", receipt)
    return bundle


def encode_conditions(cfg: dict, cohort: list[dict]) -> dict:
    import gc
    import torch
    from transformers import AutoModel, AutoProcessor

    target = Path(cfg["assets"]) / "conditions.pt"
    if target.exists():
        saved = torch.load(target, map_location="cpu", weights_only=False)
        if saved["ptids"] != [r["name"] for r in cohort]:
            raise RuntimeError("Existing conditions use a different cohort order")
        return saved
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    bundle = ensure_biomedclip_bundle(cfg)
    processor = AutoProcessor.from_pretrained(str(bundle), trust_remote_code=True, local_files_only=True)
    clip = AutoModel.from_pretrained(str(bundle), trust_remote_code=True, local_files_only=True).to(device).eval()
    descriptions = [r["description"] for r in cohort]
    patient_inputs = processor(
        descriptions, padding=True, truncation=True, return_tensors="pt", max_length=256
    ).to(device)
    tracer_inputs = processor(text=[FDG_TEXT, AV45_TEXT], return_tensors="pt", padding=True).to(device)
    with torch.no_grad():
        # Preserve the different call signatures in author cells 2 and 1.
        patients = clip.get_text_features(patient_inputs["input_ids"]).cpu()
        tracers = clip.get_text_features(**tracer_inputs).cpu()
    if patients.shape != (1857, 512) or tracers.shape != (2, 512):
        raise RuntimeError(f"Unexpected conditioning shapes: {patients.shape}, {tracers.shape}")
    saved = {
        "ptids": [r["name"] for r in cohort],
        "patient": patients,
        "tracer": tracers,
        "source": "author notebook cells 1 and 2",
    }
    tmp = target.with_suffix(".tmp")
    torch.save(saved, tmp)
    os.replace(tmp, target)
    json_write(
        Path(cfg["report"]) / "conditioning_receipt.json",
        {
            "path": str(target),
            "sha256": sha256(target),
            "patient_shape": list(patients.shape),
            "tracer_shape": list(tracers.shape),
            "device": str(device),
            "biomedclip_sha256": BIOMEDCLIP_SHA256,
        },
    )
    del clip, processor, patient_inputs, tracer_inputs
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return saved


def build_transform(conditions):
    import nibabel as nib
    import monai.transforms as mt
    import torch

    patients = conditions["patient"]
    tracers = conditions["tracer"]

    def mat_load(filepath):
        return nib.load(filepath).get_fdata()

    def fdg_index_transform(index):
        return torch.cat([patients[index].unsqueeze(0), tracers[0].unsqueeze(0)], dim=0)

    def av45_index_transform(index):
        return torch.cat([patients[index].unsqueeze(0), tracers[1].unsqueeze(0)], dim=0)

    keys = ["mri", "av45", "fdg"]
    return mt.Compose(
        [
            mt.Lambdad(keys=keys, func=mat_load),
            mt.EnsureChannelFirstd(keys=keys, channel_dim="no_channel"),
            mt.Orientationd(keys=keys, axcodes="LPI"),
            mt.CropForegroundd(keys=keys, source_key="mri"),
            mt.HistogramNormalized(keys=["mri"]),
            mt.ResizeWithPadOrCropd(keys=keys, spatial_size=[160, 192, 160]),
            mt.Spacingd(keys=keys, pixdim=(1.0, 1.0, 1.0)),
            mt.NormalizeIntensityd(keys=keys),
            mt.ScaleIntensityd(keys=keys),
            mt.Lambdad(keys=["fdg_index"], func=fdg_index_transform),
            mt.Lambdad(keys=["av45_index"], func=av45_index_transform),
        ]
    )


def _ensure_attention_backend():
    try:
        import torch
        import torch.nn.functional as F
        import xformers.ops

        try:
            test_q = torch.zeros(1, 1, 1, 16, device="cuda", dtype=torch.float16)
            xformers.ops.memory_efficient_attention(test_q, test_q, test_q)
        except Exception:
            def _sdpa_fallback(query, key, value, attn_bias=None, p=0.0, scale=None):
                if attn_bias is not None:
                    return F.scaled_dot_product_attention(query, key, value, attn_mask=attn_bias, dropout_p=p, scale=scale)
                return F.scaled_dot_product_attention(query, key, value, dropout_p=p, scale=scale)

            xformers.ops.memory_efficient_attention = _sdpa_fallback
    except Exception:
        pass


def new_model():
    _ensure_attention_backend()
    if str(AUTHOR_ROOT) not in sys.path:
        sys.path.insert(0, str(AUTHOR_ROOT))
    from generative.networks.nets import DiffusionModelUNet

    return DiffusionModelUNet(
        spatial_dims=3,
        in_channels=1,
        out_channels=1,
        num_channels=(32, 64, 64, 128),
        attention_levels=(False, False, False, True),
        num_res_blocks=1,
        num_head_channels=(0, 0, 0, 128),
        with_conditioning=True,
        cross_attention_dim=512,
        use_flash_attention=True,
    )


def state_hash(state: dict) -> str:
    h = hashlib.sha256()
    for key, tensor in sorted(state.items()):
        h.update(key.encode())
        h.update(tensor.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def rng_hash() -> dict:
    import pickle
    import torch

    def digest(value):
        return hashlib.sha256(pickle.dumps(value)).hexdigest()

    return {
        "python": digest(random.getstate()),
        "numpy": digest(np.random.get_state()),
        "torch_cpu": hashlib.sha256(torch.get_rng_state().numpy().tobytes()).hexdigest(),
        "torch_cuda": [hashlib.sha256(x.cpu().numpy().tobytes()).hexdigest() for x in torch.cuda.get_rng_state_all()],
    }


def require_training_hardware(cfg: dict) -> dict:
    import torch

    if not torch.cuda.is_available():
        raise RuntimeError("Author-faithful training requires CUDA")
    info = hardware()
    if info["gpu_total_bytes"] < cfg["minimum_gpu_total_bytes"]:
        raise RuntimeError("GPU has less than the required 47 GiB total memory")
    if info["gpu_free_bytes"] < cfg["minimum_gpu_free_bytes"]:
        raise RuntimeError("GPU is not exclusively available with at least 45 GiB free")
    available_kib = int(
        next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:"))
    )
    info["host_available_bytes"] = available_kib * 1024
    if info["host_available_bytes"] < cfg["minimum_host_available_bytes"]:
        raise RuntimeError("Less than 16 GiB host memory is available for persistent-cache training")
    return info


def author_loss(model, batch, epoch: int):
    import torch
    import torch.nn.functional as F

    images = batch["mri"].cuda()
    seg_fdg = batch["fdg"].cuda()
    seg_av45 = batch["av45"].cuda()
    fdg_index = batch["fdg_index"].cuda()
    av45_index = batch["av45_index"].cuda()
    # Cell 9 performs this unused draw; retain its effect on the RNG stream.
    torch.randint(0, 1000, (len(images),), device=images.device)
    with torch.amp.autocast("cuda", enabled=True):
        time_embedding = torch.randint(0, 1000, (images.shape[0],), device=images.device).long()
        if epoch >= 140:
            time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
        t = time_embedding.float() / 1000
        has_fdg = not torch.all(seg_fdg == 0)
        has_av45 = not torch.all(seg_av45 == 0)
        loss_fdg = torch.tensor(0.0, device=images.device)
        loss_av45 = torch.tensor(0.0, device=images.device)
        if has_fdg:
            x_t_fdg = t * seg_fdg + (1 - t) * images
            v_fdg_prediction = model(x=x_t_fdg, timesteps=time_embedding, context=fdg_index)
            loss_fdg = F.mse_loss((seg_fdg - images).float(), v_fdg_prediction.float())
        if has_av45:
            x_t_av45 = t * seg_av45 + (1 - t) * images
            v_av45_prediction = model(x=x_t_av45, timesteps=time_embedding, context=av45_index)
            loss_av45 = F.mse_loss((seg_av45 - images).float(), v_av45_prediction.float())
        loss = loss_fdg + loss_av45
    return loss, int(time_embedding.item()), bool(has_fdg), bool(has_av45)


def validate(model, loader) -> float:
    import torch
    import torch.nn.functional as F

    model.eval()
    losses = []
    with torch.no_grad():
        for batch in loader:
            images = batch["mri"].cuda()
            targets = {t: batch[t].cuda() for t in TRACERS}
            contexts = {t: batch[f"{t}_index"].cuda() for t in TRACERS}
            total = torch.tensor(0.0, device="cuda")
            with torch.amp.autocast("cuda", enabled=False):
                for tracer in TRACERS:
                    if torch.all(targets[tracer] == 0):
                        continue
                    timestep = torch.tensor([0.0], device="cuda")
                    velocity = model(x=images, timesteps=timestep, context=contexts[tracer])
                    prediction = torch.clamp(images + velocity, 0, 1)
                    total = total + F.mse_loss(prediction.float(), targets[tracer].float())
            losses.append(float(total))
            torch.cuda.empty_cache()
    return float(np.mean(losses))


def checkpoint_identity(cfg: dict, fold: int) -> dict:
    return {
        "fold": fold,
        "config_sha256": cfg["_config_sha256"],
        "cohort_sha256": cfg["cohort_sha256"],
        "split_manifest_sha256": cfg["split_manifest_sha256"],
        "input_hashes_sha256": sha256(Path(cfg["report"]) / "input_hashes.csv"),
        "conditions_sha256": sha256(Path(cfg["assets"]) / "conditions.pt"),
        "training_seed": None,
    }


def save_recovery(path: Path, model, optimizer, scaler, epoch: int, identity: dict) -> None:
    import torch

    state = {
        "format": 1,
        "model": model.state_dict(),
        "optimizer": optimizer.state_dict(),
        "scaler": scaler.state_dict(),
        "epoch": epoch,
        "python_rng": random.getstate(),
        "numpy_rng": np.random.get_state(),
        "torch_rng": torch.get_rng_state(),
        "cuda_rng": torch.cuda.get_rng_state_all(),
        **identity,
    }
    tmp = path.with_suffix(".tmp")
    torch.save(state, tmp)
    os.replace(tmp, path)


def restore_recovery(path: Path, model, optimizer, scaler, identity: dict) -> int:
    import torch

    state = torch.load(path, map_location="cpu", weights_only=False)
    if state.get("format") != 1 or any(state.get(k) != v for k, v in identity.items()):
        raise RuntimeError("Recovery identity mismatch")
    model.load_state_dict(state["model"])
    optimizer.load_state_dict(state["optimizer"])
    scaler.load_state_dict(state["scaler"])
    random.setstate(state["python_rng"])
    np.random.set_state(state["numpy_rng"])
    torch.set_rng_state(state["torch_rng"])
    torch.cuda.set_rng_state_all(state["cuda_rng"])
    return int(state["epoch"]) + 1


def command_train(args) -> None:
    import torch
    from monai.data import DataLoader, PersistentDataset

    cfg, cohort = load_config(args.config.resolve())
    if args.fold not in (1, 2):
        raise ValueError("fold must be 1 or 2")
    input_digest = verify_input_receipt(cfg, cohort)
    hw = require_training_hardware(cfg)
    conditions = encode_conditions(cfg, cohort)
    transform = build_transform(conditions)
    train_rows = [r for r in cohort if r["test_fold"] != args.fold]
    held_out_rows = [r for r in cohort if r["test_fold"] == args.fold]
    if {r["name"] for r in train_rows} & {r["name"] for r in held_out_rows}:
        raise RuntimeError("Fold overlap")

    run_dir = Path(cfg["assets"]) / "formal" / f"fold{args.fold}"
    recovery = run_dir / "recovery.pt"
    if args.resume:
        if args.resume.resolve() != recovery.resolve() or not run_dir.is_dir():
            raise RuntimeError("Resume must use this fold's recovery.pt")
    else:
        run_dir.mkdir(parents=True, exist_ok=False)

    # Preprocessing is deterministic but too large for two in-memory caches.
    # Persist one shared subject cache on NAS so both folds and restarts reuse it.
    gpu_cache_stage_reservation = torch.empty(43 * 1024**3, dtype=torch.uint8, device="cuda")
    gpu_cache_stage_reservation.fill_(1)
    torch.cuda.synchronize()
    cache_started = time.monotonic()
    conditions_digest = sha256(Path(cfg["assets"]) / "conditions.pt")
    cache_namespace = f"v{PERSISTENT_CACHE_VERSION}_{input_digest[:16]}_{conditions_digest[:16]}"
    cache_dir = Path(cfg["persistent_cache_root"]) / cache_namespace
    cache_dir.mkdir(parents=True, exist_ok=True)
    train_ds = PersistentDataset(data=train_rows, transform=transform, cache_dir=cache_dir)
    held_out_ds = PersistentDataset(data=held_out_rows, transform=transform, cache_dir=cache_dir)
    cache_receipt_path = Path(cfg["report"]) / "persistent_cache_receipt.json"
    cache_receipt = json.loads(cache_receipt_path.read_text()) if cache_receipt_path.exists() else {}
    cache_complete = (
        cache_receipt.get("cache_namespace") == cache_namespace
        and cache_receipt.get("subjects") == len(cohort)
        and len(list(cache_dir.glob("*.pt"))) == len(cohort)
    )
    if not cache_complete:
        for role, dataset in (("train", train_ds), ("held_out", held_out_ds)):
            for index in range(len(dataset)):
                dataset[index]
                if index == 0 or (index + 1) % 100 == 0 or index + 1 == len(dataset):
                    print(json.dumps({"event": "persistent_cache_warm", "role": role,
                                      "completed": index + 1, "total": len(dataset)}), flush=True)
        cache_files = len(list(cache_dir.glob("*.pt")))
        if cache_files != len(cohort):
            raise RuntimeError(f"Persistent cache incomplete: {cache_files}/{len(cohort)}")
        json_write(cache_receipt_path, {
            "status": "COMPLETE", "cache_version": PERSISTENT_CACHE_VERSION,
            "cache_namespace": cache_namespace, "cache_dir": str(cache_dir),
            "subjects": len(cohort), "input_hashes_sha256": input_digest,
            "conditions_sha256": conditions_digest,
        })
    train_loader = DataLoader(train_ds, batch_size=1, shuffle=True, num_workers=0)
    held_out_loader = DataLoader(held_out_ds, batch_size=1, shuffle=False, num_workers=0)
    cache_seconds = time.monotonic() - cache_started
    del gpu_cache_stage_reservation
    torch.cuda.empty_cache()
    torch.cuda.reset_peak_memory_stats()

    startup_rng = rng_hash()
    model = new_model().cuda()
    optimizer = torch.optim.Adam(params=model.parameters(), lr=cfg["learning_rate"])
    scaler = torch.amp.GradScaler("cuda")
    identity = checkpoint_identity(cfg, args.fold)
    start_epoch = 0
    if args.resume:
        start_epoch = restore_recovery(args.resume, model, optimizer, scaler, identity)
    initial_hash = state_hash(model.state_dict())
    json_write(
        run_dir / ("resume_start.json" if args.resume else "start.json"),
        {
            **identity,
            "hardware": hw,
            "cache_seconds": cache_seconds,
            "train_subjects": len(train_rows),
            "held_out_subjects": len(held_out_rows),
            "start_epoch_zero_based": start_epoch,
            "initial_model_sha256": initial_hash,
            "startup_rng_hashes": startup_rng,
            "author_training_rng_seeded": False,
        },
    )

    trace_path = run_dir / "training_trace.jsonl"
    epochs_path = run_dir / "epochs.jsonl"
    for epoch in range(start_epoch, cfg["epochs"]):
        model.train()
        losses, order = [], []
        epoch_started = time.monotonic()
        with trace_path.open("a") as trace:
            for iteration, batch in enumerate(train_loader, 1):
                optimizer.zero_grad(set_to_none=True)
                loss, timestep, has_fdg, has_av45 = author_loss(model, batch, epoch)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
                sid = batch["name"][0]
                value = float(loss.detach())
                losses.append(value)
                order.append(sid)
                if iteration <= 5 or iteration % 100 == 0 or iteration == len(train_loader):
                    event = {
                        "epoch_zero_based": epoch,
                        "iteration": iteration,
                        "ptid": sid,
                        "timestep": timestep,
                        "loss": value,
                        "has_fdg": has_fdg,
                        "has_av45": has_av45,
                        "amp_scale": scaler.get_scale(),
                        "peak_allocated_bytes": torch.cuda.max_memory_allocated(),
                        "peak_reserved_bytes": torch.cuda.max_memory_reserved(),
                    }
                    trace.write(json.dumps(event) + "\n")
                    trace.flush()
                    print(json.dumps(event), flush=True)
                torch.cuda.empty_cache()

        epoch_number = epoch + 1
        val_loss = None
        if epoch_number % cfg["val_interval"] == 0:
            val_loss = validate(model, held_out_loader)
        should_snapshot = epoch_number % cfg["val_interval"] == 0 or epoch_number in (
            cfg["primary_epoch"],
            cfg["secondary_epoch"],
        )
        if should_snapshot:
            checkpoint = {"model": model.state_dict(), "optimizer": optimizer.state_dict(), "epoch": epoch}
            checkpoint_path = run_dir / f"first_part_{epoch_number}.pth"
            torch.save(checkpoint, checkpoint_path)
            json_write(
                checkpoint_path.with_suffix(".json"),
                {
                    **identity,
                    "epoch_one_based": epoch_number,
                    "checkpoint_sha256": sha256(checkpoint_path),
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
            "held_out_monitored_loss": val_loss,
            "seconds": time.monotonic() - epoch_started,
            "sample_order_sha256": hashlib.sha256("\n".join(order).encode()).hexdigest(),
            "rng_hashes_after_epoch": rng_hash(),
        }
        with epochs_path.open("a") as log:
            log.write(json.dumps(epoch_event) + "\n")
        print(json.dumps(epoch_event), flush=True)
    json_write(
        run_dir / "complete.json",
        {
            **identity,
            "epochs": cfg["epochs"],
            "primary_checkpoint": str(run_dir / f"first_part_{cfg['primary_epoch']}.pth"),
            "secondary_checkpoint": str(run_dir / f"first_part_{cfg['secondary_epoch']}.pth"),
            "status": "TRAINING_COMPLETE_NOT_INFERRED",
        },
    )


def command_infer(args) -> None:
    import nibabel as nib
    import torch
    import torch.nn.functional as F
    from monai.data import DataLoader, Dataset
    from monai.metrics import PSNRMetric
    try:
        from generative.metrics import SSIMMetric
    except ImportError:
        if str(AUTHOR_ROOT) not in sys.path:
            sys.path.insert(0, str(AUTHOR_ROOT))
        from generative.metrics import SSIMMetric

    cfg, cohort = load_config(args.config.resolve())
    if args.fold not in (1, 2) or args.epoch not in (cfg["primary_epoch"], cfg["secondary_epoch"]):
        raise ValueError("Only fold 1/2 and the preregistered epochs may be inferred")
    if not torch.cuda.is_available():
        raise RuntimeError("Inference requires CUDA")
    conditions = encode_conditions(cfg, cohort)
    held_out = [r for r in cohort if r["test_fold"] == args.fold]
    loader = DataLoader(Dataset(held_out, build_transform(conditions)), batch_size=1, shuffle=False, num_workers=0)
    checkpoint = Path(cfg["assets"]) / "formal" / f"fold{args.fold}" / f"first_part_{args.epoch}.pth"
    receipt = checkpoint.with_suffix(".json")
    if not checkpoint.exists() or not receipt.exists():
        raise RuntimeError("Missing completed preregistered checkpoint and receipt")
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
            image = batch["mri"].cuda()
            timestep = torch.tensor([0], device="cuda", dtype=torch.long)
            for tracer in TRACERS:
                target = batch[tracer].cuda()
                if torch.all((target == 0) | (target == 1)):
                    continue
                context = batch[f"{tracer}_index"].cuda()
                velocity = model(x=image, timesteps=timestep, context=context)
                prediction = torch.clamp(image + velocity, 0, 1).float()
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
    csv_write(output / "metrics.csv", rows)
    json_write(
        output / "complete.json",
        {
            "fold": args.fold,
            "epoch": args.epoch,
            "subjects": len(held_out),
            "metric_rows": len(rows),
            "counts": {t: sum(r["tracer"] == t for r in rows) for t in TRACERS},
            "metrics_sha256": sha256(output / "metrics.csv"),
            "checkpoint_sha256": sha256(checkpoint),
        },
    )


def command_summarize(args) -> None:
    import pandas as pd

    cfg, cohort = load_config(args.config.resolve())
    out = Path(cfg["report"]) / "oof_summary"
    out.mkdir(parents=True, exist_ok=False)
    all_rows = []
    for epoch in (cfg["primary_epoch"], cfg["secondary_epoch"]):
        for fold in (1, 2):
            folder = Path(cfg["assets"]) / "oof" / f"epoch{epoch}" / f"fold{fold}"
            complete = json.loads((folder / "complete.json").read_text())
            if sha256(folder / "metrics.csv") != complete["metrics_sha256"]:
                raise RuntimeError(f"Metric hash mismatch: epoch {epoch} fold {fold}")
            all_rows.extend(pd.read_csv(folder / "metrics.csv").to_dict("records"))
    table = pd.DataFrame(all_rows)
    if table.duplicated(["ptid", "tracer", "epoch"]).any():
        raise RuntimeError("Duplicate OOF prediction identity")
    expected = cfg["expected_effective"]
    for epoch in (cfg["primary_epoch"], cfg["secondary_epoch"]):
        for tracer in TRACERS:
            count = int(((table.epoch == epoch) & (table.tracer == tracer)).sum())
            if count != expected[tracer]:
                raise RuntimeError(f"Expected {expected[tracer]} {tracer} rows at epoch {epoch}, got {count}")
    table.to_csv(out / "per_subject_metrics.csv", index=False)
    summaries = []
    for (epoch, tracer), group in table.groupby(["epoch", "tracer"], sort=True):
        summaries.append(
            {
                "endpoint": "primary" if epoch == cfg["primary_epoch"] else "secondary",
                "epoch": int(epoch),
                "tracer": tracer,
                "n": len(group),
                "ssim": float(group.ssim.mean()),
                "ssim_percent": float(group.ssim.mean() * 100),
                "psnr": float(group.psnr.mean()),
                "mse": float(group.mse.mean()),
                "mse_percent": float(group.mse.mean() * 100),
                "mae": float(group.mae.mean()),
                "mae_percent": float(group.mae.mean() * 100),
            }
        )
    csv_write(out / "overall_summary.csv", summaries)
    json_write(
        out / "completion.json",
        {
            "status": "COMPLETE_TWO_FOLD_OOF_RECONSTRUCTION",
            "historical_fold_identity_recovered": False,
            "training_seed": None,
            "primary_epoch": cfg["primary_epoch"],
            "secondary_epoch": cfg["secondary_epoch"],
            "per_subject_sha256": sha256(out / "per_subject_metrics.csv"),
            "summary_sha256": sha256(out / "overall_summary.csv"),
            "scope": "new author-code-semantics reconstruction; not proof of the historical paper run",
        },
    )


def command_parity(args) -> None:
    source = assert_source_contract()
    cfg, cohort = load_config(args.config.resolve())
    counts = {str(f): sum(r["test_fold"] == f for r in cohort) for f in (1, 2)}
    if counts != cfg["fold_counts"] or sorted(counts.values()) != [928, 929]:
        raise RuntimeError("Split parity failed")
    result = {
        "source_contract": source,
        "split_counts": counts,
        "unique_ptids": len({r["name"] for r in cohort}),
        "training_formula": "two forward graphs; summed loss; one backward/optimizer step",
        "unused_rng_draw_preserved": True,
        "distillation_rng_draw_then_zero_preserved": True,
        "training_seed": None,
        "static_parity": "PASS",
        "cuda_numerical_parity": "NOT_RUN",
    }
    if args.cuda:
        import copy
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("--cuda requested but CUDA unavailable")
        torch.manual_seed(20261020)
        torch.cuda.manual_seed_all(20261020)
        model_a = new_model().cuda().float()
        model_b = copy.deepcopy(model_a)
        batch = {
            "mri": torch.rand(1, 1, 32, 32, 32),
            "fdg": torch.rand(1, 1, 32, 32, 32),
            "av45": torch.rand(1, 1, 32, 32, 32),
            "fdg_index": torch.rand(1, 2, 512),
            "av45_index": torch.rand(1, 2, 512),
        }
        torch.cuda.set_rng_state(torch.cuda.get_rng_state())
        state = torch.cuda.get_rng_state()
        loss_a, timestep_a, _, _ = author_loss(model_a, batch, 12)
        loss_a.backward()
        torch.cuda.set_rng_state(state)
        images, fdg, av45 = batch["mri"].cuda(), batch["fdg"].cuda(), batch["av45"].cuda()
        torch.randint(0, 1000, (1,), device="cuda")
        with torch.amp.autocast("cuda", enabled=True):
            timestep = torch.randint(0, 1000, (1,), device="cuda").long()
            t = timestep.float() / 1000
            pred_fdg = model_b(x=t * fdg + (1 - t) * images, timesteps=timestep, context=batch["fdg_index"].cuda())
            pred_av45 = model_b(x=t * av45 + (1 - t) * images, timesteps=timestep, context=batch["av45_index"].cuda())
            loss_b = torch.nn.functional.mse_loss((fdg - images).float(), pred_fdg.float())
            loss_b = loss_b + torch.nn.functional.mse_loss((av45 - images).float(), pred_av45.float())
        loss_b.backward()
        gradient_pairs = [(pa.grad, pb.grad) for pa, pb in zip(model_a.parameters(), model_b.parameters()) if pa.grad is not None]
        max_grad = max(float((ga - gb).abs().max()) for ga, gb in gradient_pairs)
        loss_abs = float((loss_a - loss_b).abs())
        close = all(torch.allclose(ga, gb, rtol=1e-3, atol=1e-5) for ga, gb in gradient_pairs)
        if timestep_a != int(timestep.item()) or loss_abs != 0.0 or not close:
            raise RuntimeError("CUDA author-formula parity failed")
        result["cuda_numerical_parity"] = "PASS"
        result["fixture_seed_only_not_formal_training"] = 20261020
        result["loss"] = float(loss_a)
        result["loss_absolute_difference"] = loss_abs
        result["max_gradient_abs_difference"] = max_grad
        result["gradient_rtol"] = 1e-3
        result["gradient_atol"] = 1e-5
        del model_a, model_b, loss_a, loss_b, batch, gradient_pairs
        del images, fdg, av45, timestep, pred_fdg, pred_av45
        torch.cuda.empty_cache()
    if args.full_sample:
        import torch

        if not args.cuda:
            raise RuntimeError("--full-sample requires --cuda")
        verify_input_receipt(cfg, cohort)
        require_training_hardware(cfg)
        conditions = encode_conditions(cfg, cohort)
        transformed = build_transform(conditions)(cohort[0])
        batch = {
            key: value.unsqueeze(0) if isinstance(value, torch.Tensor) else [value]
            for key, value in transformed.items()
        }
        torch.manual_seed(20261020)
        torch.cuda.manual_seed_all(20261020)
        torch.cuda.reset_peak_memory_stats()
        model = new_model().cuda()
        optimizer = torch.optim.Adam(model.parameters(), lr=cfg["learning_rate"])
        scaler = torch.amp.GradScaler("cuda")
        optimizer.zero_grad(set_to_none=True)
        loss, timestep, has_fdg, has_av45 = author_loss(model, batch, 0)
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        torch.cuda.synchronize()
        result["full_sample_preflight"] = "PASS"
        result["full_sample_ptid"] = cohort[0]["name"]
        result["full_sample_loss"] = float(loss.detach())
        result["full_sample_timestep"] = timestep
        result["full_sample_has_fdg"] = has_fdg
        result["full_sample_has_av45"] = has_av45
        result["full_sample_peak_allocated_bytes"] = torch.cuda.max_memory_allocated()
        result["full_sample_peak_reserved_bytes"] = torch.cuda.max_memory_reserved()
        result["full_sample_fixture_seed_only_not_formal_training"] = 20261020
    json_write(Path(cfg["report"]) / "parity_receipt.json", result)
    print(json.dumps(result, ensure_ascii=False))


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--out", type=Path, required=True)
    prepare.add_argument("--assets", type=Path, required=True)
    prepare.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    hash_inputs = sub.add_parser("hash-inputs")
    hash_inputs.add_argument("--config", type=Path, required=True)
    parity = sub.add_parser("parity-check")
    parity.add_argument("--config", type=Path, required=True)
    parity.add_argument("--cuda", action="store_true")
    parity.add_argument("--full-sample", action="store_true")
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


@email_on_error()
def main() -> None:
    args = parser().parse_args()
    actions = {
        "prepare": command_prepare,
        "hash-inputs": command_hash_inputs,
        "parity-check": command_parity,
        "train": command_train,
        "infer": command_infer,
        "summarize": command_summarize,
    }
    actions[args.action](args)


if __name__ == "__main__":
    main()
