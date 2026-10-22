# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _two trace_new.ipynb
# original_sha256=520a2ec0f712b2bfbb40752269db4f412cc0624c464b8481e053f41701259a3c; zero_based_cell=13
import os
import tempfile
import time
from liutuo_utils import donkey_noise_like
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn.functional as F
from monai import transforms
from monai.apps import DecathlonDataset
from monai.config import print_config
from monai.data import DataLoader
from monai.utils import set_determinism
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm
from torch.amp import GradScaler, autocast 
# 加载检查点
checkpoint_dir = '/home/data/liutuo/code/checkpoint/mri2pet _two trace_add clip_flow'
checkpoint = torch.load(f'{checkpoint_dir}/first_part_311.pth')

model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
start_epoch = checkpoint['epoch'] + 1  # 从保存的epoch之后开始

# 训练参数设置
new_epochs = 1  # 新的训练轮次
total_epochs = start_epoch + new_epochs
val_interval = 1  # 验证间隔
epoch_loss_list = []  # 初始化训练损失列表
val_epoch_loss_list = []  # 初始化验证损失列表
scaler = GradScaler()  # 自动混合精度训练

# 训练循环
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1  # 设置合适的最大值
for epoch in range(start_epoch, total_epochs):
    model.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg_fdg = data["fdg"].to(device)  # 真实分割
        seg_av45 = data["av45"].to(device)
        fdg_index = data["fdg_index"].to(device)
        av45_index = data["av45_index"].to(device)

        optimizer.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # 随机选择时间步t

        with autocast(device_type='cuda', enabled=True):
            # 时间嵌入
            time_embedding = torch.randint(
                0, 1000, (images.shape[0],), device=images.device
            ).long()

            if epoch >= 140:
                time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)

            t = time_embedding.float() / 1000  # 归一化

            x_t_fdg = t * seg_fdg + (1 - t) * images
            v_fdg_prediction = model(x=x_t_fdg, timesteps=time_embedding, context=fdg_index)
            v_fdg = seg_fdg - images
            loss_fdg = F.mse_loss(v_fdg.float(), v_fdg_prediction.float())

            x_t_av45 = t * seg_av45 + (1 - t) * images
            v_av45_prediction = model(x=x_t_av45, timesteps=time_embedding, context=av45_index)
            v_av45 = seg_av45 - images
            loss_av45 = F.mse_loss(v_av45.float(), v_av45_prediction.float())

            loss = loss_fdg + loss_av45

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        epoch_loss += loss.item()
        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})

        torch.cuda.empty_cache()

    epoch_loss_list.append(epoch_loss / (step + 1))
    if (epoch + 1) % val_interval == 0:
        model.eval()
        val_epoch_loss = 0
        for step, data_val in enumerate(val_loader):
            images = data_val["mri"].to(device)
            seg_fdg = data_val["fdg"].to(device)  # 真实分割
            seg_av45 = data_val["av45"].to(device)
            fdg_index = data_val["fdg_index"].to(device)
            av45_index = data_val["av45_index"].to(device)

            x_t = images
            N_sample = 1
            N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
            progress_bar = [(i / (N_sample)) for i in range(N_sample)]

            for t in progress_bar:  # 遍历去噪过程
                with autocast(device_type='cuda', enabled=False):
                    with torch.no_grad():
                        time_embedding = int(t * 1000)
                        v_fdg_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=fdg_index)
                        x_fdg_t = x_t + (v_fdg_output / N_sample_tensor)
                        x_fdg_t = torch.clamp(x_fdg_t, min=clip_sample_min, max=clip_sample_max)

                        v_av45_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=av45_index)
                        x_av45_t = x_t + (v_av45_output / N_sample_tensor)
                        x_av45_t = torch.clamp(x_av45_t, min=clip_sample_min, max=clip_sample_max)

            val_fdg_loss = F.mse_loss(x_fdg_t.float(), seg_fdg.float())
            val_av45_loss = F.mse_loss(x_av45_t.float(), seg_av45.float())
            val_loss = val_fdg_loss + val_av45_loss

            val_epoch_loss += val_loss.item()
            torch.cuda.empty_cache()

        print("Epoch", epoch + 1, "Validation loss", val_epoch_loss / (step + 1))
        val_epoch_loss_list.append(val_epoch_loss / (step + 1))

        # 计算SSIM和PSNR
        from generative.metrics import SSIMMetric
        from monai.metrics import PSNRMetric

        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
        psnr_metric = PSNRMetric(1.0)

        # 遍历训练集计算 SSIM 和 PSNR
        model.eval()
        for step, data_train in enumerate(train_loader):
            images = data_train["mri"].to(device)
            seg_fdg = data_train["fdg"].to(device)  # 真实分割
            seg_av45 = data_train["av45"].to(device)
            fdg_index = data_train["fdg_index"].to(device)
            av45_index = data_train["av45_index"].to(device)

            # 生成 fdg 和 av45
            with torch.no_grad():
                time_embedding = torch.randint(0, 1000, (images.shape[0],)).long().to(images.device)

                # 在 epoch >= 140 的情况下，将 time_embedding 设置为 0
                if epoch >= 140:
                    time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)

                t = time_embedding.float() / 1000  # 归一化

                # 生成 fdg 和 av45
                x_t_fdg = t * seg_fdg + (1 - t) * images
                v_fdg_prediction = model(x=x_t_fdg, timesteps=time_embedding, context=fdg_index)
                generated_fdg = seg_fdg - images + v_fdg_prediction

                x_t_av45 = t * seg_av45 + (1 - t) * images
                v_av45_prediction = model(x=x_t_av45, timesteps=time_embedding, context=av45_index)
                generated_av45 = seg_av45 - images + v_av45_prediction

            # 计算 SSIM 和 PSNR
            ssim_fdg_value = ssim_metric(seg_fdg, generated_fdg)
            psnr_fdg_value = psnr_metric(seg_fdg, generated_fdg)

            ssim_av45_value = ssim_metric(seg_av45, generated_av45)
            psnr_av45_value = psnr_metric(seg_av45, generated_av45)

            # 打印训练集的 SSIM 和 PSNR
            print(f"Train Epoch {epoch + 1}, Step {step + 1} - "
                  f"FDG SSIM: {ssim_fdg_value.mean().item():.4f}, FDG PSNR: {psnr_fdg_value.mean().item():.4f}, "
                  f"AV45 SSIM: {ssim_av45_value.mean().item():.4f}, AV45 PSNR: {psnr_av45_value.mean().item():.4f}")

        # 保存模型参数 
        print('epoch:', epoch + 1)
        print('learning rate:', optimizer.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/first_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')

