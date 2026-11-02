"""MONAI 3D SwinUNETR adapted for direct MRI-to-PET regression."""
from __future__ import annotations

from monai.networks.nets import SwinUNETR


def build_model(*, use_checkpoint: bool = True) -> SwinUNETR:
    """Build the frozen 3D, single-channel SwinUNETR baseline.

    MONAI 1.5 removed the constructor's historical ``img_size`` argument.
    Input sizes are checked by the runner and remain 160x192x160.
    """
    return SwinUNETR(
        spatial_dims=3,
        in_channels=1,
        out_channels=1,
        feature_size=48,
        drop_rate=0.0,
        attn_drop_rate=0.0,
        dropout_path_rate=0.0,
        use_checkpoint=use_checkpoint,
    )


def parameter_count(model: SwinUNETR | None = None) -> int:
    if model is None:
        model = build_model()
    return sum(parameter.numel() for parameter in model.parameters())
