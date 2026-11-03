"""Shared R3-11 metric calculation using the repository's existing SSIM."""
import math
import numpy as np
import torch
from generative.metrics.ssim import compute_ssim_and_cs


def metric_values(real, prediction, brain, valid, device):
    difference = prediction[brain].astype(np.float64) - real[brain].astype(np.float64)
    mse = float(np.mean(difference**2))
    x = torch.from_numpy(real.copy())[None, None].to(device)
    y = torch.from_numpy(prediction.copy())[None, None].to(device)
    with torch.no_grad():
        field, _ = compute_ssim_and_cs(x, y, spatial_dims=3, data_range=1.0,
            kernel_size=(7, 7, 7), kernel_sigma=(1.5, 1.5, 1.5))
    field = field.cpu().numpy().squeeze()
    assert field.shape == valid.shape
    return {'ssim': float(field[valid].mean()), 'psnr': -10 * math.log10(mse),
            'mse': mse, 'mae': float(np.mean(np.abs(difference)))}, float(field.mean())
