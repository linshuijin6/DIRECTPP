# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb
# original_sha256=6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a; zero_based_cell=18
import torch
import numpy as np
from tqdm import tqdm
from generative.metrics import SSIMMetric

# 加载保存的模型参数
checkpoint_path = "/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_flow/noise2image about mri2pet_method_two_second_part_10.pth"
checkpoint = torch.load(checkpoint_path)
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
model.eval()  # Set the model to evaluation mode
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1.0   # 设置合适的最大值
model.to(device)

# 初始化SSIM度量
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=11)

# 遍历数据集，查找特定样本名称
for batch in train_loader:
    names = batch["name"]  # 提取样本名称

    # 查找名称为 "130_S_0460" 的样本
    if "002_S_2010" not in names:
        continue  # 如果没有找到该样本，继续下一个 batch

    # 获取该样本的 MRI 输入图像和 PET 标签
    images= batch["mri"].to(device)
    labels = batch["pet"].to(device)
    pet_index = batch["pet_index"].to(device)
    time_embedding = torch.randint(0, 1000, (images.shape[0],), device=images.device).long()
    time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
    t = time_embedding.float() / 1000  # Convert time to float scale
    time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)

    x_t = images
    N_sample =1
    N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
    progress_bar = [(i / N_sample) for i in range(N_sample)]
    
    for t in progress_bar:
        with autocast(device_type='cuda', enabled=False):

            time_embedding = int(t * 1000)
            time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)

            v_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=pet_index)
            x_t = x_t + (v_output / N_sample_tensor)
            x_t = torch.clamp(x_t, min=clip_sample_min, max=clip_sample_max)
    # 将结果移回CPU
    current_img = x_t.to('cpu')
    labels = labels.to('cpu')
    from generative.metrics import SSIMMetric
    from monai.metrics import (MAEMetric, MSEMetric, PSNRMetric,)

    # 计算当前采样的SSIM
    ssim_value = ssim_metric(labels, current_img)

    # 可视化采样结果
    compare_3d([images, labels, current_img])
    compare_3d_jet([images, labels, current_img])
    compare_3d_jet([current_img - labels])

    # 计算并输出PSNR和SSIM
    psnr_metric = PSNRMetric(1.0)
    ssim_value = ssim_metric(labels, current_img)
    psnr_value = psnr_metric(labels, current_img)

    print(f"SSIM: {ssim_value.mean().item()}")
    print(f"PSNR: {psnr_value.mean().item()}")

    # 找到并处理完 "130_S_0460" 样本后，退出循环
    break