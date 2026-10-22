# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-32_64_64_128-final-nii-Copy1.ipynb
# original_sha256=b3aec5233333cd9767b4980ee63cbccc23680fa1d0eaea81dc47c2b71a07f46b; zero_based_cell=13
import torch
import numpy as np
from tqdm import tqdm
from generative.metrics import SSIMMetric
for batch in train_loader:
    names = batch["name"]  # 提取样本名称

    # 查找名称为 "130_S_0460" 的样本
    if "041_S_1412" not in names:
        continue  # 如果没有找到该样本，继续下一个 batch
    image_1 = batch["mri"]
    label_1 = batch["pet"]
   



    compare_3d([image_1, label_1])
    break  # Uncomment to compare only the first batch

# 加载保存的模型参数
checkpoint = torch.load('/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_concat_final/noise2image about mri2pet_method_two_second_part_180.pth')
model.load_state_dict(checkpoint['model'])
model.eval()
model.to(device)

# 初始化SSIM度量
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=11)

# 遍历数据集，查找特定样本名称
for batch in train_loader:
    names = batch["name"]  # 提取样本名称

    # 查找名称为 "130_S_0460" 的样本
    if "041_S_1412" not in names:
        continue  # 如果没有找到该样本，继续下一个 batch

    # 获取该样本的 MRI 输入图像和 PET 标签
    input_img = batch["mri"].to(device)
    labels = batch["pet"].to(device)
    pet_index = batch["pet_index"].to(device)

    # 生成随机噪声并初始化采样图像
    noise = donkey_noise_like(input_img).to(device)
    current_img = noise  # 从随机噪声开始
    combined = torch.cat((input_img, noise), dim=1)  # 拼接MR图像和噪声

    # 采样过程
    progress_bar = tqdm(scheduler.timesteps, desc=f"Sampling")
    for t in progress_bar:
        with autocast(device_type='cuda', enabled=True):
            with torch.no_grad():
                model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device), context=pet_index)
                current_img, _ = scheduler.step(model_output, t, current_img)
                combined = torch.cat((input_img, current_img), dim=1)  # 每一步都拼接MR图像

    # 将结果移回CPU
    current_img = current_img.to('cpu')
    labels = labels.to('cpu')
    from generative.metrics import SSIMMetric
    from monai.metrics import (MAEMetric, MSEMetric, PSNRMetric,)

    # 计算当前采样的SSIM
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

    # 找到并处理完 "130_S_0460" 样本后，退出循环
    break
