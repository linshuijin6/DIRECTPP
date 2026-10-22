# Derived evidence only; original=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb
# original_sha256=6ce109159da4b04758146170d0968e2b42d5f2cd79a03192da8de11f0a5edd1f; zero_based_cell=9
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
from torch.amp import GradScaler, autocast  # 从 torch.amp 导入 GradScaler





n_epochs = 200
val_interval =10
epoch_loss_list = []
val_epoch_loss_list = []
scaler = GradScaler()  
total_start = time.time()
checkpoint_dir = '/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized'


# 定义裁剪的最小值和最大值
# 定义裁剪的最小值和最大值
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1   # 设置合适的最大值

# 定义模态权重
alpha = 1.0  # FDG 损失权重
beta = 1.0   # AV45 损失权重

for epoch in range(n_epochs):
    model.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg_fdg = data["fdg"].to(device)  # this is the ground truth segmentation
        seg_av45 = data["av45"].to(device)
        fdg_index = data["fdg_index"].to(device)
        av45_index = data["av45_index"].to(device)
        
        optimizer.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # pick a random time step t
        
        with autocast(device_type='cuda', enabled=True):
            # Create time_embedding
            time_embedding = torch.randint(
                0, 1000, (images.shape[0],), device=images.device
            ).long()
            
            if epoch >= 140:
                time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
            
            # Create time
            t = time_embedding.float() / 1000
            
            # 检查 FDG 数据是否为二值化（只有 0 和 1）
            has_fdg = not torch.all(seg_fdg == 0)  # 如果不是二值化数据，则参与计算
            has_av45 = not torch.all(seg_av45 == 0)  # 如果不是二值化数据，则参与计算
            
            # 默认损失为 0
            loss_fdg = torch.tensor(0.0, device=device)
            loss_av45 = torch.tensor(0.0, device=device)
            
            # 计算 FDG 损失
            if has_fdg:  # 如果不是二值化数据，计算 FDG 损失
                x_t_fdg = t * seg_fdg + (1 - t) * images
                v_fdg_prediction = model(x=x_t_fdg, timesteps=time_embedding, context=fdg_index)
                v_fdg = seg_fdg - images
                loss_fdg = F.mse_loss(v_fdg.float(), v_fdg_prediction.float())
            
            # 计算 AV45 损失
            if has_av45:  # 如果不是二值化数据，计算 AV45 损失
                x_t_av45 = t * seg_av45 + (1 - t) * images
                v_av45_prediction = model(x=x_t_av45, timesteps=time_embedding, context=av45_index)
                v_av45 = seg_av45 - images
                loss_av45 = F.mse_loss(v_av45.float(), v_av45_prediction.float())
            
            # 加权总损失
            loss = alpha * loss_fdg + beta * loss_av45

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        
        epoch_loss += loss.item()
        progress_bar.set_postfix({
            "loss": epoch_loss / (step + 1),
            # "FDG": "✓" if has_fdg else "✗",
            # "AV45": "✓" if has_av45 else "✗"
        })
        
        torch.cuda.empty_cache()
    
    epoch_loss_list.append(epoch_loss / (step + 1))
    if (epoch + 1) % val_interval == 0:
        model.eval()
        val_epoch_loss = 0
        
        for step, data_val in enumerate(val_loader):
            # 验证阶段的数据加载
            images = data_val["mri"].to(device)
            seg_fdg = data_val["fdg"].to(device)  # this is the ground truth segmentation
            seg_av45 = data_val["av45"].to(device)
            fdg_index = data_val["fdg_index"].to(device)
            av45_index = data_val["av45_index"].to(device)
 
            # 检查 FDG 和 AV45 数据是否为二值化（只有 0 和 1）
            has_fdg = not torch.all(seg_fdg == 0)  # 如果不是二值化数据，则参与计算
            has_av45 = not torch.all(seg_av45 == 0)  # 如果不是二值化数据，则参与计算
    
            x_t = images
            N_sample = 1
            N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
    
            progress_bar = [(i / N_sample) for i in range(N_sample)]
            for t in progress_bar:  # go through the noising process
                with autocast(device_type='cuda', enabled=False):
                    with torch.no_grad():
                        time_embedding = int(t * 1000)
    
                        # FDG 输出（仅当非二值化时计算）
                        if has_fdg:
                            v_fdg_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=fdg_index)
                            x_fdg_t = x_t + (v_fdg_output / N_sample_tensor)
                            x_fdg_t = torch.clamp(x_fdg_t, min=clip_sample_min, max=clip_sample_max)
                        else:
                            x_fdg_t = None  # 跳过 FDG 计算
    
                        # AV45 输出（仅当非二值化时计算）
                        if has_av45:
                            v_av45_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=av45_index)
                            x_av45_t = x_t + (v_av45_output / N_sample_tensor)
                            x_av45_t = torch.clamp(x_av45_t, min=clip_sample_min, max=clip_sample_max)
                        else:
                            x_av45_t = None  # 跳过 AV45 计算
    
            # 默认损失为 0
            val_fdg_loss = torch.tensor(0.0, device=device)
            val_av45_loss = torch.tensor(0.0, device=device)
    
            # 计算 FDG 损失（仅当非二值化时计算）
            if has_fdg and x_fdg_t is not None:
                val_fdg_loss = F.mse_loss(x_fdg_t.float(), seg_fdg.float())
    
            # 计算 AV45 损失（仅当非二值化时计算）
            if has_av45 and x_av45_t is not None:
                val_av45_loss = F.mse_loss(x_av45_t.float(), seg_av45.float())
    
            # 加权总损失
            val_loss = alpha * val_fdg_loss + beta * val_av45_loss
    
            val_epoch_loss += val_loss.item()
            torch.cuda.empty_cache()
    
        print("Epoch", epoch + 1, "Validation loss", val_epoch_loss / (step + 1))
        val_epoch_loss_list.append(val_epoch_loss / (step + 1))
    
        # Saving model parameters
        print('epoch:', epoch + 1)
        print('learning rate:', optimizer.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/first_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')
    
        # 可视化和评估指标
        current_fdg_img = x_fdg_t.to('cpu') if x_fdg_t is not None else None
        current_av45_img = x_av45_t.to('cpu') if x_av45_t is not None else None
        labels_fdg = seg_fdg.to('cpu')
        labels_av45 = seg_av45.to('cpu')
    
        # 如果存在非二值化的 FDG 或 AV45 数据，则进行可视化和评估
        if current_fdg_img is not None or current_av45_img is not None:
            compare_3d([images, labels_fdg, current_fdg_img, labels_av45, current_av45_img])
            compare_3d_jet([current_fdg_img - labels_fdg, current_av45_img - labels_av45])
    
        from generative.metrics import SSIMMetric
        from monai.metrics import MAEMetric, MSEMetric, PSNRMetric
    
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
        psnr_metric = PSNRMetric(1.0)
    
        # 计算 SSIM 和 PSNR（仅当非二值化时计算）
        if has_fdg and current_fdg_img is not None:
            ssim_fdg_value = ssim_metric(labels_fdg, current_fdg_img)
            psnr_fdg_value = psnr_metric(labels_fdg, current_fdg_img)
            print(f"FDG SSIM: {ssim_fdg_value.mean().item()}")
            print(f"FDG PSNR: {psnr_fdg_value.mean().item()}")
    
        if has_av45 and current_av45_img is not None:
            ssim_av45_value = ssim_metric(labels_av45, current_av45_img)
            psnr_av45_value = psnr_metric(labels_av45, current_av45_img)
            print(f"AV45 SSIM: {ssim_av45_value.mean().item()}")
            print(f"AV45 PSNR: {psnr_av45_value.mean().item()}")