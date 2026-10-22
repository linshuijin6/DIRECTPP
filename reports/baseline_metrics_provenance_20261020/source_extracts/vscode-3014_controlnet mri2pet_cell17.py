# Original=source_archive/vscode-3014/mnt/ssd/liutuo/controlnet mri2pet.ipynb
# original_sha256=8316ad153543c7e855d652294daa58a4233152291e2fb10ee52ff9a66e4f2021; zero_based_cell=17
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
psnr_metric=PSNRMetric(1.0)

ssim_value = ssim_metric(sample, val_images)
psnr_value = psnr_metric(sample, val_images)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}") 