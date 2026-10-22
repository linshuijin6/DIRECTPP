# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-32_64_64_128-final-nii-Copy1.ipynb
# original_sha256=b3aec5233333cd9767b4980ee63cbccc23680fa1d0eaea81dc47c2b71a07f46b; zero_based_cell=15
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric, MSEMetric, PSNRMetric,)
ssim_value = ssim_metric(labels, current_img)

# 可视化采样结果
compare_3d([input_img, labels, current_img])
compare_3d_jet([current_img - labels])

# 计算并输出PSNR和SSIM
psnr_metric = PSNRMetric(1.0)
ssim_value = ssim_metric(labels, current_img)
psnr_value = psnr_metric(labels, current_img)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}")
