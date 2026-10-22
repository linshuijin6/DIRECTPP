# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet-test.ipynb
# original_sha256=6574c514d21920c800ea87d5dcaa15570538b13039dcb6cf88434e3ee0010796; zero_based_cell=17
from generative.metrics import SSIMMetric
from monai.metrics import (
    MAEMetric,
    MSEMetric,
    #MultiScaleSSIMMetric,
    PSNRMetric,
)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
psnr_metric=PSNRMetric(1.0)

ssim_value = ssim_metric(current_img, labels)
psnr_value = psnr_metric(current_img, labels)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}")