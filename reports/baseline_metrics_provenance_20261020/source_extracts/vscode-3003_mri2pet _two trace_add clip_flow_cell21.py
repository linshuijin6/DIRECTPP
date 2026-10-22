# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _two trace_add clip_flow.ipynb
# original_sha256=16687592c30d51b9fa01d7d2e7b533e1149224e25c7006dfcee0070739f3275b; zero_based_cell=21
import torch
from torch import autocast
from generative.metrics import SSIMMetric
from monai.metrics import PSNRMetric

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

# 加载模型权重
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
model.eval()  # 设置模型为评估模式

# 将模型转移到正确的设备
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model.to(device)

# 逐步处理数据
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1.0  # 设置合适的最大值

# 遍历整个训练集
for batch in train_loader:
    # 获取该样本的 MRI 输入图像和 PET 标签
    image_mri = batch["mri"].to(device)
    seg_fdg = batch["fdg"].to(device)  # 这是地面真值分割
    seg_av45 = batch["av45"].to(device)
    fdg_index = batch["fdg_index"].to(device)
    av45_index = batch["av45_index"].to(device)

    # 初始化样本数据
    x_t = image_mri
    N_sample = 1  # 使用较小的样本数量
    N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
    progress_bar = [(i / N_sample) for i in range(N_sample)]

    # 分步计算，减少一次性计算占用的内存
    for t in progress_bar:
        with autocast(device_type='cuda', enabled=True):  # 开启自动混合精度以减少内存占用
            time_embedding = torch.tensor([0], device=x_t.device, dtype=torch.long)
            time_embedding = int(t * 1000)

            # 处理FDG图像
            v_fdg_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=fdg_index)
            x_fdg_t = x_t + (v_fdg_output / N_sample_tensor)
            x_fdg_t = torch.clamp(x_fdg_t, min=clip_sample_min, max=clip_sample_max)

            # 处理AV45图像
            v_av45_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=av45_index)
            x_av45_t = x_t + (v_av45_output / N_sample_tensor)
            x_av45_t = torch.clamp(x_av45_t, min=clip_sample_min, max=clip_sample_max)

    # 将结果移到CPU
    current_fdg_img = x_fdg_t.to('cpu')
    current_av45_img = x_av45_t.to('cpu')
    labels_fdg = seg_fdg.to('cpu')
    labels_av45 = seg_av45.to('cpu')

    # 计算SSIM和PSNR
    ssim_fdg_value = ssim_metric(labels_fdg, current_fdg_img)
    ssim_av45_value = ssim_metric(labels_av45, current_av45_img)

    psnr_fdg_value = psnr_metric(labels_fdg, current_fdg_img)
    psnr_av45_value = psnr_metric(labels_av45, current_av45_img)

    # 存储每批次的结果
    ssim_fdg_values.append(ssim_fdg_value.mean().item())
    ssim_av45_values.append(ssim_av45_value.mean().item())
    psnr_fdg_values.append(psnr_fdg_value.mean().item())
    psnr_av45_values.append(psnr_av45_value.mean().item())

    # 手动释放不再使用的变量，释放GPU内存
    del x_fdg_t, x_av45_t, v_fdg_output, v_av45_output
    torch.cuda.empty_cache()  # 清理GPU缓存

# 输出训练集上的SSIM和PSNR
print(f"fdg SSIM values: {ssim_fdg_values}")
print(f"av45 SSIM values: {ssim_av45_values}")
print(f"fdg PSNR values: {psnr_fdg_values}")
print(f"av45 PSNR values: {psnr_av45_values}")
