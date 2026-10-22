# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _two trace_add clip_flow.ipynb
# original_sha256=16687592c30d51b9fa01d7d2e7b533e1149224e25c7006dfcee0070739f3275b; zero_based_cell=23
import torch
from torch import autocast
from generative.metrics import SSIMMetric
from monai.metrics import PSNRMetric
from torch.utils.data import DataLoader
import os

# 设置 PyTorch CUDA 内存分配配置
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True'
# 初始化SSIM和PSNR指标
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
psnr_metric = PSNRMetric(1.0)

# 用于存储所有批次的 SSIM 和 PSNR 值
ssim_fdg_values = []
ssim_av45_values = []
psnr_fdg_values = []
psnr_av45_values = []

# 加载模型
checkpoint_path = '/home/data/liutuo/code/checkpoint/mri2pet _two trace_add clip_flow/first_part_300.pth'
checkpoint = torch.load(checkpoint_path)

# 加载模型权重和优化器状态
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
model.eval()  # 设置模型为评估模式

clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1.0  # 设置合适的最大值

# 遍历整个训练集
for batch in train_loader:
    # 数据转移到GPU
    image_mri = batch["mri"].to(device)
    seg_fdg = batch["fdg"].to(device)
    seg_av45 = batch["av45"].to(device)
    fdg_index = batch["fdg_index"].to(device)
    av45_index = batch["av45_index"].to(device)

    # 禁用梯度计算
    with torch.no_grad():
        x_t = image_mri
        N_sample = 1
        progress_bar = [(i / N_sample) for i in range(N_sample)]
        
        for t in progress_bar:
            with autocast(device_type='cuda', enabled=True):
                # time_embedding = int(t * 1000)
                time_embedding = torch.tensor([0], device=x_t.device, dtype=torch.long)
                # 处理FDG
                v_fdg_output = model(x=x_t, timesteps=torch.Tensor([time_embedding]).to(device), context=fdg_index)
                x_fdg_t = x_t + (v_fdg_output / N_sample)
                x_fdg_t = torch.clamp(x_fdg_t, clip_sample_min, clip_sample_max)
                # 处理AV45
                v_av45_output = model(x=x_t, timesteps=torch.Tensor([time_embedding]).to(device), context=av45_index)
                x_av45_t = x_t + (v_av45_output / N_sample)
                x_av45_t = torch.clamp(x_av45_t, clip_sample_min, clip_sample_max)

    # 结果转移到CPU并计算指标
    current_fdg_img = x_fdg_t.cpu()
    current_av45_img = x_av45_t.cpu()
    labels_fdg = seg_fdg.cpu()
    labels_av45 = seg_av45.cpu()

    # 释放GPU变量
    del x_t, x_fdg_t, x_av45_t, v_fdg_output, v_av45_output
    torch.cuda.empty_cache()

# 输出训练集上的SSIM和PSNR
print(f"fdg SSIM values: {ssim_fdg_values}")
print(f"av45 SSIM values: {ssim_av45_values}")
print(f"fdg PSNR values: {psnr_fdg_values}")
print(f"av45 PSNR values: {psnr_av45_values}")
