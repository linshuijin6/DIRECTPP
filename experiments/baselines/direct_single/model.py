"""Archived 3D Single-Flow network definition, without a diffusion scheduler."""
from __future__ import annotations

import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
AUTHOR_ROOT = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo"
MODEL_SOURCE = AUTHOR_ROOT / "generative/networks/nets/diffusion_model_unet.py"
COMPAT_ROOT = Path(__file__).resolve().parent / "compat"


def ensure_attention_backend() -> None:
    # Keep use_flash_attention=True. The small local adapter supplies xformers'
    # attention call through PyTorch SDPA when xformers is absent on a node.
    if importlib.util.find_spec("xformers") is None and str(COMPAT_ROOT) not in sys.path:
        sys.path.insert(0, str(COMPAT_ROOT))
    import xformers.ops
    import torch
    from compat.xformers.ops import memory_efficient_attention as sdpa_compat
    q = torch.zeros(1, 2, 1, 16, device="cuda", dtype=torch.float16)
    try:
        xformers.ops.memory_efficient_attention(q, q, q)
    except Exception:
        xformers.ops.memory_efficient_attention = sdpa_compat


def attention_backend() -> str:
    import xformers.ops
    from compat.xformers.ops import memory_efficient_attention as sdpa_compat
    shim_path = (COMPAT_ROOT / "xformers/ops.py").resolve()
    active_path = Path(xformers.ops.__file__).resolve()
    return "torch_sdpa_compat" if active_path == shim_path or xformers.ops.memory_efficient_attention is sdpa_compat else "xformers"


def build_model():
    ensure_attention_backend()
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


def parameter_count(model) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
