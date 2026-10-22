# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet small data number->concat.ipynb
# original_sha256=07393787a08da1928ed9b69fcb610d74139a4f0e7f71ac3db9fbc917cfe7b255; zero_based_cell=14
current_img = current_img.to('cpu')
labels = label_1.to('cpu')
compare_3d([input_img,labels, current_img],fixed=False)
compare_3d_jet([current_img - labels],fixed=False)
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=7)
psnr_metric=PSNRMetric(1.0)

ssim_value = ssim_metric(labels, current_img)
psnr_value = psnr_metric(labels, current_img)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}") 