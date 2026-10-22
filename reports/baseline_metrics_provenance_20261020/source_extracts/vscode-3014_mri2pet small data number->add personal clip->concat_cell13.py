# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet small data number->add personal clip->concat.ipynb
# original_sha256=b3a6916e1c4e86e7fa46045973b520bc8b3160b7725f5025dafa5ac6164d5a38; zero_based_cell=13
import torch
import numpy as np
from tqdm import tqdm
from generative.metrics import SSIMMetric

# 加载保存的模型参数
checkpoint = torch.load('/home/ssd/liutuo/checkpoint/mri2pet/mri2pet small data number->add personal clip->concat/noise2image about mri2pet_method_two_second_part_140.pth')
model.load_state_dict(checkpoint['model'])

# 初始化SSIM度量
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)

# 用于存储10次采样的SSIM值
ssim_values = []

# 使用不同输入图像进行10次采样
for i, data in enumerate(val_loader):
    if i >= 10:  # 只采样10次
        break
    
    # 获取不同的输入图像和标签
    input_img = data["mri"].to(device)
    labels = data["pet"].to(device)
    pet_index = data["pet_index"].to(device)

    # 生成随机噪声并初始化采样图像
    noise = donkey_noise_like(input_img).to(device)
    current_img = noise  # 从随机噪声开始
    combined = torch.cat((input_img, noise), dim=1)  # 拼接MR图像和噪声


    progress_bar = tqdm(scheduler.timesteps, desc=f"Sampling {i+1}/10")
    for t in progress_bar:  # go through the noising process
        with autocast(enabled=False):
            with torch.no_grad():
                model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=pet_index)
                current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
                combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information


    # 将结果移回CPU
    current_img = current_img.to('cpu')
    labels = labels.to('cpu')

    # 计算当前采样的SSIM并存储
    ssim_value = ssim_metric(labels, current_img)
    ssim_values.append(ssim_value.mean().item())

    # 可视化采样结果
    compare_3d([input_img, labels, current_img])
    compare_3d_jet([current_img - labels])

# 计算SSIM的均值和方差
ssim_mean = np.mean(ssim_values)
ssim_variance = np.var(ssim_values)

# 输出结果
print(f"SSIM均值: {ssim_mean}")
print(f"SSIM方差: {ssim_variance}")
