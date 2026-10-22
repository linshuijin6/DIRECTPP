# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow plus concat.ipynb
# original_sha256=e10d32890a81f3855df383392d3047aaee2ad35826ad9fa67529784282e7d1d4; zero_based_cell=13
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
val_interval =10 #10
epoch_loss_list = []
val_epoch_loss_list = []
scaler = GradScaler()  
total_start = time.time()
checkpoint_dir = '/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_flow plus concat'

for epoch in range(n_epochs):  # Start from start_epoch
    model.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg = data["pet"].to(device)  # Ground truth segmentation
        pet_index = data["pet_index"].to(device)
        
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # pick a random time step t    
        noise = donkey_noise_like(images).to(device)
        #noise = torch.randn_like(images).to(device)
        noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
        optimizer.zero_grad(set_to_none=True)
        
        with autocast(device_type='cuda', enabled=True):
            # 创建时间嵌入
            time_embedding = torch.randint(0, 1000, (images.shape[0],), device=images.device).long()
            if epoch > 150:
                time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
            
            t = time_embedding.float() / 1000  # 将时间转换为浮动范围 [0, 1]

            # 拼接 MRI 和带噪声的 PET 为 x0，拼接 MRI 和干净的 PET 为 x1
            x_0 = torch.cat((images, noisy_seg), dim=1)  # 拼接：MRI + noisy PET
            x_1 = torch.cat((images, seg), dim=1)  # 拼接：MRI + clean PET

            # 计算 x_t
            x_t = t* x_1 + (1 - t) * x_0  # 对 x1 和 x0 进行插值

            # 获取 v 的预测
            v_prediction = model(x=x_t, timesteps=time_embedding, context=pet_index)

            # 计算损失
            v = x_1 - x_0
            loss = F.mse_loss(v.float(), v_prediction.float())
        
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        epoch_loss += loss.item()
        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})
        
        torch.cuda.empty_cache()
    
    epoch_loss_list.append(epoch_loss / (step + 1))


    # Validation
    if (epoch + 1) % val_interval == 0:
        model.eval()
        val_epoch_loss = 0
        for step, data_val in enumerate(val_loader):
            images = data_val["mri"].to(device)
            seg = data_val["pet"].to(device)  # Ground truth segmentation
            pet_index = data["pet_index"].to(device)
            noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
            
            x_t = torch.cat((images, noisy_seg), dim=1)
            N_sample = 1
            N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
            progress_bar = [(i / N_sample) for i in range(N_sample)]
            for t in progress_bar:  # Iterate through noising process
                with autocast(device_type='cuda', enabled=False):
                    with torch.no_grad():
                        time_embedding = int(t * 1000)
                        v_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=pet_index)
                        x_t = x_t + (v_output / N_sample_tensor)
                
            val_loss = F.mse_loss(x_t.float(), seg.float())
            val_epoch_loss += val_loss.item()
            torch.cuda.empty_cache()
        
        print("Epoch", epoch + 1, "Validation loss", val_epoch_loss / (step + 1))
        val_epoch_loss_list.append(val_epoch_loss / (step + 1))
        
        # Save model parameters
        print('Epoch:', epoch + 1)
        print('Learning rate:', optimizer.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/noise2image about mri2pet_method_two_second_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')
    

        
        mri_image = x_t[:, 0:1, :, :, :]  # 提取 MRI 图像（第一通道）
        generated_pet = x_t[:, 1:2, :, :, :]  # 提取生成的 PET 图像（第二通道）
        # # 采样过程
        # model.eval()
        # input_img = image_1.to(device)
        # print(input_img.shape)
        # noise= donkey_noise_like(images).to(device)
        # current_img = noise  # for the segmentation mask, we start from random noise.
        # combined = torch.cat((input_img, noise), dim=1)  # We concatenate the input brain MR image to add anatomical information.
        
        # #scheduler.set_timesteps(num_inference_steps=1000)
        # progress_bar = tqdm(scheduler.timesteps)
        # for t in progress_bar:  # go through the noising process
        #     with autocast(device_type='cuda', enabled=True):
        #         with torch.no_grad():
        #             model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=pet_index)
        #             current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
        #             combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

        current_img = generated_pet.to('cpu')
        labels = seg.to('cpu')
        compare_3d([images,labels, current_img])
        compare_3d_jet([current_img - labels])
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=7)
        psnr_metric=PSNRMetric(1.0)

        ssim_value = ssim_metric(labels, current_img)
        psnr_value = psnr_metric(labels, current_img)

        print(f"SSIM: {ssim_value.mean().item()}")
        print(f"PSNR: {psnr_value.mean().item()}") 

total_time = time.time() - total_start
print(f"train diffusion completed, total time: {total_time}.")
