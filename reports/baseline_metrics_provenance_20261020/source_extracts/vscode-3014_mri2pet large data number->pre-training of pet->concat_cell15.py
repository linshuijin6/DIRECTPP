# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet large data number->pre-training of pet->concat.ipynb
# original_sha256=e062758eb42566ef2b639d0ecaffadd6e9a63d7fa9a8548af0e2d3dce191fdee; zero_based_cell=15
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
psnr_metric=PSNRMetric(1.0)


ssim_value = ssim_metric(labels, current_img)
psnr_value = psnr_metric(labels, current_img)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}") 