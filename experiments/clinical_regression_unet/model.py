"""Deterministic clinical/tracer-conditioned 3D regression U-Net."""
from __future__ import annotations

import torch
from monai.networks.blocks import Convolution
from torch import nn


def _groups(channels: int) -> int:
    for groups in (8, 4, 2, 1):
        if channels % groups == 0:
            return groups
    return 1


class ResidualBlock3D(nn.Module):
    """Two-convolution residual block using the MONAI convolution primitive."""

    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.norm1 = nn.GroupNorm(_groups(in_channels), in_channels)
        self.norm2 = nn.GroupNorm(_groups(out_channels), out_channels)
        self.act = nn.SiLU()
        self.conv1 = Convolution(
            spatial_dims=3,
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=3,
            padding=1,
            conv_only=True,
        )
        self.conv2 = Convolution(
            spatial_dims=3,
            in_channels=out_channels,
            out_channels=out_channels,
            kernel_size=3,
            padding=1,
            conv_only=True,
        )
        self.skip = (
            nn.Identity()
            if in_channels == out_channels
            else nn.Conv3d(in_channels, out_channels, kernel_size=1)
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = self.skip(x)
        x = self.conv1(self.act(self.norm1(x)))
        x = self.conv2(self.act(self.norm2(x)))
        return x + residual


class Downsample3D(nn.Module):
    def __init__(self, in_channels: int, out_channels: int) -> None:
        super().__init__()
        self.conv = Convolution(
            spatial_dims=3,
            in_channels=in_channels,
            out_channels=out_channels,
            kernel_size=3,
            strides=2,
            padding=1,
            conv_only=True,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.conv(x)


class ClinicalRegressionUNet3D(nn.Module):
    """A one-pass U-Net that directly regresses normalized PET from MRI.

    Clinical inputs contain eight fixed fields.  The two-element tracer one-hot
    is concatenated with them and used only for bottleneck FiLM modulation.
    """

    clinical_features = 8
    tracer_features = 2

    def __init__(self, channels: tuple[int, int, int, int] = (32, 64, 64, 128)) -> None:
        super().__init__()
        c0, c1, c2, c3 = channels
        self.channels = channels
        self.enc0 = ResidualBlock3D(1, c0)
        self.down1 = Downsample3D(c0, c1)
        self.enc1 = ResidualBlock3D(c1, c1)
        self.down2 = Downsample3D(c1, c2)
        self.enc2 = ResidualBlock3D(c2, c2)
        self.down3 = Downsample3D(c2, c3)
        self.bottleneck = ResidualBlock3D(c3, c3)

        self.condition = nn.Sequential(
            nn.Linear(self.clinical_features + self.tracer_features, 64),
            nn.SiLU(),
            nn.Linear(64, 2 * c3),
        )

        self.up2 = nn.ConvTranspose3d(c3, c2, kernel_size=2, stride=2)
        self.dec2 = ResidualBlock3D(c2 + c2, c2)
        self.up1 = nn.ConvTranspose3d(c2, c1, kernel_size=2, stride=2)
        self.dec1 = ResidualBlock3D(c1 + c1, c1)
        self.up0 = nn.ConvTranspose3d(c1, c0, kernel_size=2, stride=2)
        self.dec0 = ResidualBlock3D(c0 + c0, c0)
        self.out = nn.Sequential(
            nn.GroupNorm(_groups(c0), c0),
            nn.SiLU(),
            nn.Conv3d(c0, 1, kernel_size=1),
        )

    def forward(
        self,
        mri: torch.Tensor,
        clinical: torch.Tensor,
        tracer: torch.Tensor,
    ) -> torch.Tensor:
        if mri.ndim != 5 or mri.shape[1] != 1:
            raise ValueError(f"MRI must have shape [B,1,D,H,W], got {tuple(mri.shape)}")
        if clinical.ndim != 2 or clinical.shape != (mri.shape[0], self.clinical_features):
            raise ValueError(f"clinical must have shape [B,8], got {tuple(clinical.shape)}")
        if tracer.ndim != 2 or tracer.shape != (mri.shape[0], self.tracer_features):
            raise ValueError(f"tracer must have shape [B,2], got {tuple(tracer.shape)}")

        s0 = self.enc0(mri)
        s1 = self.enc1(self.down1(s0))
        s2 = self.enc2(self.down2(s1))
        x = self.bottleneck(self.down3(s2))

        gamma, beta = self.condition(torch.cat([clinical, tracer], dim=1)).chunk(2, dim=1)
        gamma = gamma[:, :, None, None, None]
        beta = beta[:, :, None, None, None]
        x = x * (1.0 + gamma) + beta

        x = self.dec2(torch.cat([self.up2(x), s2], dim=1))
        x = self.dec1(torch.cat([self.up1(x), s1], dim=1))
        x = self.dec0(torch.cat([self.up0(x), s0], dim=1))
        return self.out(x)


def parameter_count(model: nn.Module) -> int:
    return sum(parameter.numel() for parameter in model.parameters())
