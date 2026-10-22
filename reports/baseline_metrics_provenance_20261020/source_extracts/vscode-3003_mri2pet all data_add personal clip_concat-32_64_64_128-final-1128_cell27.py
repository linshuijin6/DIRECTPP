# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-32_64_64_128-final-1128.ipynb
# original_sha256=6adcfb9fbb7c4d635e69fce326b4c28f28a3baaf6b22164e08c1a2f87e6cc0ec; zero_based_cell=27
import torch
import numpy as np
from tqdm import tqdm
from generative.metrics import SSIMMetric

# 加载保存的模型参数
checkpoint = torch.load('/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_concat_test/noise2image about mri2pet_method_two_second_part_344.pth')
model.load_state_dict(checkpoint['model'])

# 初始化SSIM度量
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=11)

# 用于存储10次采样的SSIM值
ssim_values = []

# 使用不同输入图像进行10次采样
for i, data in enumerate(train_loader):
    if i >= 20:  # 只采样10次
        break
    
    # 获取不同的输入图像和标签
    input_img = data["mri"].to(device)
    labels = data["pet"].to(device)
    pet_index = data["pet_index"].to(device)

    # 生成随机噪声并初始化采样图像
    noise = donkey_noise_like(input_img).to(device)
    current_img = noise  # 从随机噪声开始
    combined = torch.cat((input_img, noise), dim=1)  # 拼接MR图像和噪声


    progress_bar = tqdm(scheduler.timesteps, desc=f"Sampling {i+1}")
    for t in progress_bar:  # go through the noising process
        with autocast(device_type='cuda', enabled=True):
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
    from generative.metrics import SSIMMetric
    from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
    ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=11)
    psnr_metric=PSNRMetric(1.0)

    ssim_value = ssim_metric(labels, current_img)
    psnr_value = psnr_metric(labels, current_img)

    print(f"SSIM: {ssim_value.mean().item()}")
    print(f"PSNR: {psnr_value.mean().item()}") 

# 计算SSIM的均值和方差
ssim_mean = np.mean(ssim_values)
ssim_variance = np.var(ssim_values)

# 输出结果
print(f"SSIM均值: {ssim_mean}")
print(f"SSIM方差: {ssim_variance}")
