"""Small shared utilities for the isolated E1 stage 0--1 preparation."""
from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CODE = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo"
SCORES = ["MMSE Total Score", "GDSCALE Total Score", "Global CDR", "FAQ Total Score", "NPI-Q Total Score"]
TRACERS = ["fdg", "av45"]


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    os.replace(tmp, path)


def load_config(path):
    return json.loads(Path(path).read_text())


def seed_all(seed):
    import numpy as np
    import torch
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True


def tensor_hash(state):
    h = hashlib.sha256()
    for k, v in sorted(state.items()):
        h.update(k.encode())
        h.update(v.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def check_frozen(config):
    for name, digest in config["frozen_files"].items():
        if sha(name) != digest:
            raise RuntimeError(f"Frozen input changed: {name}")


def active_rows(config, rows):
    """Apply the frozen pre-specified QC exclusions (cohort.json itself stays unchanged).

    Rule: a subject whose MRI replay does not bind the historical MRI/mask grid
    (mri_mask_grid_pass False, i.e. saved MRI replay maxabs > 2e-6) is excluded
    from both training and evaluation. Other subjects keep their fold; no re-split.
    """
    path = config.get("qc_exclusions")
    if not path:
        return rows
    excluded = {e["ptid"] for e in json.loads(Path(path).read_text())["excluded"]}
    for r in rows:
        if r["ptid"] in excluded and r.get("mri_mask_grid_pass", True):
            raise RuntimeError(f"QC exclusion does not match frozen rule: {r['ptid']}")
    return [r for r in rows if r["ptid"] not in excluded]


def capture_execution(config,entry,action):
    """Snapshot new entrypoint/config bytes before an authorized computation."""
    from datetime import datetime, timezone, timedelta
    import shutil
    stamp=datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%dT%H%M%S%f%z")
    path=Path(config["assets"])/"code_snapshots"/(action+"_"+stamp)
    path.mkdir(parents=True,exist_ok=False)
    sources=[Path(__file__),Path(entry),Path(config["report"])/"config.json"]
    for source in sources:shutil.copyfile(source,path/source.name)
    write_json(path/"receipt.json",dict(action=action,pid=os.getpid(),
        source_files={str(p):sha(p) for p in sources},
        generator_source_sha256=sha(CODE/"generative/networks/nets/diffusion_model_unet.py")))


def new_model():
    import sys
    sys.path.insert(0, str(CODE))
    from generative.networks.nets import DiffusionModelUNet
    return DiffusionModelUNet(
        spatial_dims=3, in_channels=1, out_channels=1,
        num_channels=(32, 64, 64, 128),
        attention_levels=(False, False, False, True), num_res_blocks=1,
        num_head_channels=(0, 0, 0, 128), with_conditioning=True,
        cross_attention_dim=512, use_flash_attention=True,
    )
