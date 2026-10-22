"""Execute selected author notebook source, with an explicit adaptation receipt.

No E1/restored model, transform, sampler, or metric implementation is imported.
"""
import argparse
import ast
import csv
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
import time

parser = argparse.ArgumentParser()
parser.add_argument("--config", required=True)
cfg = json.loads(Path(parser.parse_args().config).read_text())
work = Path(cfg["work"])
assert not (work / "per_subject_metrics.csv").exists(), "Use a new isolated run directory"
sys.path.insert(0, cfg["original_code_root"])
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import numpy as np
import torch


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def save(name, data):
    (work / name).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


started = time.monotonic()
source_dir = work / "executed_author_cells"
source_dir.mkdir()
source_receipts = []


def cell(book_path, index):
    path = Path(book_path)
    source = "".join(json.loads(path.read_text())["cells"][index]["source"])
    key = ("metrics" if book_path == cfg["metric_notebook"] else "best152") + f"_cell{index}"
    (source_dir / (key + ".original.py")).write_text(source)
    source_receipts.append(dict(key=key, original=str(path), notebook_sha256=sha(path),
                                zero_based_cell=index, source_sha256=hashlib.sha256(source.encode()).hexdigest()))
    return key, source


g = dict(torch=torch, np=np, os=os, device=torch.device("cuda"), __name__="__author_inference__")


def execute(key, source, adaptations):
    # Fail closed if selected source accidentally includes a training update.
    tree = ast.parse(source)
    for item in ast.walk(tree):
        if isinstance(item, ast.Call) and isinstance(item.func, ast.Attribute):
            assert item.func.attr not in {"backward", "step"}, "Training is not authorized here"
    (source_dir / (key + ".executed.py")).write_text(source)
    source_receipts[-1].update(executed_sha256=hashlib.sha256(source.encode()).hexdigest(), adaptations=adaptations)
    save("source_receipt.json", source_receipts)
    save("status.json", dict(phase=key, elapsed_seconds=time.monotonic()-started))
    print("PHASE", key, flush=True)
    exec(compile(source, str(source_dir / (key + ".executed.py")), "exec"), g)


memory = subprocess.check_output([
    "nvidia-smi", "--id=" + cfg["gpu_uuid"],
    "--query-gpu=memory.free,utilization.gpu", "--format=csv,noheader,nounits"], text=True)
free, util = map(int, memory.strip().split(","))
assert free > 40000 and util < 10, "The intended GPU is no longer idle"
torch.cuda.set_device(0)
torch.set_num_threads(4)
# Keep native FP32 convolutions, including native SSIM, out of TF32 arithmetic.
torch.backends.cudnn.allow_tf32 = False
torch.backends.cuda.matmul.allow_tf32 = False
save("environment.json", dict(python=sys.executable, torch=torch.__version__, cuda=torch.version.cuda,
     visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"), gpu=torch.cuda.get_device_name(0),
     physical_gpu=cfg["gpu_physical_index"], gpu_uuid=cfg["gpu_uuid"], pid=os.getpid(),
     torch_threads=torch.get_num_threads(), cudnn_tf32=False, matmul_tf32=False,
     precision="Native float32 inference and author metrics; AMP not introduced"))
save("checkpoint_receipt.json", dict(path=cfg["checkpoint"], sha256=sha(cfg["checkpoint"]),
     selection_basis=cfg["selection_basis"], biomedclip_sha256=sha(Path(cfg["biomedclip_bundle"]) / "model.safetensors")))

key, source = cell(cfg["native_notebook"], 1)
execute(key, source.replace("/home/ssddata/liutuo/BiomedCLIP", cfg["biomedclip_bundle"]),
        ["Relocate original BiomedCLIP files to a byte-preserving isolated bundle"])

key, source = cell(cfg["native_notebook"], 2)
source = source.split("# 划分训练集和验证集")[0]
assert "train_data, val_data =" not in source
source = source.replace("/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45", cfg["data_root"])
source = source.replace("/home/ssddata/liutuo/BiomedCLIP", cfg["biomedclip_bundle"])
execute(key, source, ["Use retained original NIfTI/CSV directory", "Stop before split and JSON writes; preserve full original-cohort text encoding"])
paired = g["paired_data"]
assert len(paired) == 1857 and len({r["name"] for r in paired}) == 1857
legacy = json.loads(Path(cfg["manifest"]).read_text())
names = [r["name"] for r in legacy]
assert len(names) == len(set(names)) == cfg["expected_n"]
lookup = {r["name"]: r for r in paired}
selected = [lookup[name] for name in names]
assert all(Path(r[k]).is_file() for r in selected for k in ["mri", "fdg", "av45"])
save("native_329_input_manifest.json", selected)
save("full_text_encoding_order.json", [r["name"] for r in paired])
save("input_binding.json", dict(native_rows=selected, legacy_manifest_path=cfg["manifest"],
     legacy_manifest_sha256=sha(cfg["manifest"]), csv_sha256=sha(Path(cfg["data_root"]) / "filtered_subjects_with_description.csv"),
     scope=cfg["inference_scope"], all_modalities_present=True))
g["val_data"] = selected

key, original = cell(cfg["native_notebook"], 4)
nodes = []
for node in ast.parse(original).body:
    if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef)):
        nodes.append(node)
    elif isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in {"val_transforms", "val_ds", "val_loader"} for t in node.targets):
        nodes.append(node)
source = "\n\n".join(ast.get_source_segment(original, node) for node in nodes)
execute(key, source, ["Execute unchanged author val transforms/dataset/loader only; use fixed 329 PTIDs in recovered order", "Do not build the irrelevant training cache or read/write author split JSON"])
g["train_loader"] = g["val_loader"]  # Original evaluation cell uses this container name.

key, source = cell(cfg["native_notebook"], 7)
execute(key, source, [])
import monai
from generative.metrics import SSIMMetric
save("imported_dependencies.json", {name: dict(path=inspect.getfile(obj), sha256=sha(inspect.getfile(obj)))
     for name, obj in [("model", type(g["model"])), ("ssim", SSIMMetric), ("monai", monai)]})
torch.cuda.reset_peak_memory_stats()

metric_file = open(work / "per_subject_metrics.csv", "x", newline="")
writer = csv.DictWriter(metric_file, fieldnames=["ptid", "tracer", "ssim", "psnr", "mse", "mae"])
writer.writeheader()
records = []
seen = set()
validated = {}


def record_metrics(name, tracer, ssim, psnr, mse, mae):
    identity = (name, tracer)
    assert name in names and identity not in seen
    row = dict(ptid=name, tracer=tracer, **{k: float(v.mean().item()) for k, v in
               [("ssim", ssim), ("psnr", psnr), ("mse", mse), ("mae", mae)]})
    assert all(np.isfinite(row[k]) for k in ["ssim", "psnr", "mse", "mae"])
    if tracer not in validated:
        label = g["seg_" + tracer].detach().cpu()[None, None]
        pred = g["x_" + tracer + "_t"].detach().cpu()[None, None]
        native_cpu = float(SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)(label, pred).mean())
        difference = abs(native_cpu - row["ssim"])
        validated[tracer] = dict(ptid=name, native_gpu=row["ssim"], native_cpu=native_cpu, absolute_difference=difference)
        save("native_metric_cpu_gpu_check.json", validated)
        assert difference < 5e-5, "Native SSIM CPU/GPU check failed"
    seen.add(identity)
    records.append(row)
    writer.writerow(row)
    metric_file.flush()
    save("status.json", dict(phase="inference", metric_rows=len(records), last_ptid=name,
         elapsed_seconds=time.monotonic()-started, peak_allocated_bytes=torch.cuda.max_memory_allocated()))


g["record_metrics"] = record_metrics
key, source = cell(cfg["metric_notebook"], 7)
source = source.replace("/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized/first_part_140.pth", cfg["checkpoint"])
source = source.replace("torch.load(checkpoint_path)", "torch.load(checkpoint_path, map_location=device, weights_only=True)")
source = source.replace("/home/ssddata/liutuo/liutuo_data/test1/ddim/", str(work / "native_outputs") + "/")
for tracer in ["fdg", "av45"]:
    needle = 'f"MAE: {mae_' + tracer + '_value.mean().item():.4f}")'
    assert source.count(needle) == 1
    source = source.replace(needle, needle + f'\n            record_metrics(names[0], "{tracer}", ssim_{tracer}_value, psnr_{tracer}_value, mse_{tracer}_value, mae_{tracer}_value)')
execute(key, source, ["Use author-selected 152best from new_start cell10", "Map checkpoint storage to isolated GPU; restricted weights-only loading", "Relocate all generated and real image outputs", "Append logging of original metric tensors and a first-case native CPU/GPU check; no metric formula changes"])
metric_file.close()
assert len(list((work / "native_outputs/data_augmentation_mri").glob("*.nii.gz"))) == cfg["expected_n"]
summary = {t: dict(n=sum(r["tracer"] == t for r in records), **{
    metric: float(np.mean([r[metric] for r in records if r["tracer"] == t]))
    for metric in ["ssim", "psnr", "mse", "mae"]}) for t in ["fdg", "av45"]}
save("summary.json", dict(status="COMPLETE", subjects=cfg["expected_n"], results=summary,
     elapsed_seconds=time.monotonic()-started, peak_allocated_bytes=torch.cuda.max_memory_allocated(),
     peak_reserved_bytes=torch.cuda.max_memory_reserved(), independent_test_claim=False))
save("status.json", dict(phase="complete", subjects=cfg["expected_n"], metric_rows=len(records)))
print("NATIVE ORIGINAL-CODE INFERENCE COMPLETE", summary, flush=True)
