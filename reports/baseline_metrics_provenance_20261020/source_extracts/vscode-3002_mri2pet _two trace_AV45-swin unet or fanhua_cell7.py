# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_AV45-swin unet or fanhua.ipynb
# original_sha256=0755c31eeb8f628ec6f73a11e91a75577a8211337e8d5729d3a13deabef59489; zero_based_cell=7
from torch.cuda.amp import GradScaler, autocast
import os

import matplotlib.pyplot as plt
import torch
import json
import torch.nn as nn

import torch.nn.functional as F
from monai import transforms
from monai.config import print_config
from monai import data
from monai.utils import first, set_determinism
from torch.cuda.amp import GradScaler, autocast
from monai.data import CacheDataset, DataLoader
from monai.networks.nets import ViT, ViTAutoEnc, SwinUNETR
from tqdm import tqdm

from generative.inferers import DiffusionInferer
from generative.networks.nets import AutoencoderKL, DiffusionModelUNet
from generative.networks.schedulers import DDPMScheduler, DDIMScheduler
import random
import time
import matplotlib.pyplot as plt
import numpy as np

from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
checkpoint_dir = '/home/ssddata/liutuo/checkpoint/swinunter_fdg'
n_epochs = 13
val_interval = 1 #10
epoch_loss_list = []
val_epoch_loss_list = []
val_epoch_loss = 0
start_epoch = 0
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=7)
psnr_metric=PSNRMetric(1.0)
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1.0   # 设置合适的最大值

scaler = GradScaler()


for epoch in range(start_epoch, n_epochs):
    epoch
    model.train()
    epoch_loss = 0

    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")

    for step, data in progress_bar:
        images = data["mri"].to(device)  
        targets = data["fdg"].to(device)  

 

        optimizer.zero_grad(set_to_none=True)
    
        with autocast(enabled=True):

            t1ce_pre = model(images)
            loss = F.mse_loss(targets.float(), t1ce_pre.float())

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        epoch_loss += loss.item()

        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})

    epoch_loss_list.append(epoch_loss / (step + 1))
    
    if (epoch) % val_interval == 0 or (epoch == 0):
        model.eval()
        ssim_values = []
        psnr_values = []

        with torch.no_grad():
            for step, batch in enumerate(val_loader):
                images = data["mri"].to(device)  # 确保将张量加载到 GPU
                targets = data["fdg"].to(device)  # 确保目标也在 GPU

                t1ce_pre= model(images)
                t1ce_pre= torch.clamp(t1ce_pre, min=clip_sample_min, max=clip_sample_max)
                val_loss =F.mse_loss(targets.float(), t1ce_pre.float())
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
            torch.save(checkpoint, f'{checkpoint_dir}/swinunter_{epoch + 1}.pth')
            print('Saved all parameters!\n')
        

            ssim_value = ssim_metric(targets, t1ce_pre)
            psnr_value = psnr_metric(targets, t1ce_pre)
            # print(f"SSIM: {ssim_value.mean().item()}")
            # print(f"PSNR: {psnr_value.mean().item()}") 
            # 将当前批次的 SSIM 和 PSNR 值添加到列表中
            ssim_values.append(ssim_value)
            psnr_values.append(psnr_value)
            current_img =  t1ce_pre.to('cpu')
            labels = targets.to('cpu')
            compare_3d([images,labels, current_img])
            compare_3d_jet([current_img - labels])



        # 计算平均 SSIM 和 PSNR 值
        average_ssim = sum(ssim_values) / len(ssim_values)
        average_psnr = sum(psnr_values) / len(psnr_values)

        print(f"Average SSIM: {average_ssim}")
        print(f"Average PSNR: {average_psnr}")