# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet large data number->add unique clip->pre-training of mri->concat.ipynb
# original_sha256=ffcb2c32728b4295b3049bcd2d346286fc845f0ba011fbcd68c6641253020b94; zero_based_cell=16
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
psnr_metric=PSNRMetric(1.0)


ssim_value = ssim_metric(labels, current_img)
psnr_value = psnr_metric(labels, current_img)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}") 