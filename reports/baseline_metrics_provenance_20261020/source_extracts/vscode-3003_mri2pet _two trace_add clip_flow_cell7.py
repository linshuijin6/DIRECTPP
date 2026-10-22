# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _two trace_add clip_flow.ipynb
# original_sha256=16687592c30d51b9fa01d7d2e7b533e1149224e25c7006dfcee0070739f3275b; zero_based_cell=7
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
checkpoint_dir = '/home/data/liutuo/code/checkpoint/mri2pet _two trace_add clip_flow'


# 定义裁剪的最小值和最大值
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1   # 设置合适的最大值

for epoch in range(n_epochs):
    model.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg_fdg = data["fdg"].to(device) # this is the ground truth segmentation
        seg_av45 = data["av45"].to(device)
        fdg_index=data["fdg_index"].to(device)
        av45_index=data["av45_index"].to(device)
        
        optimizer.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # pick a random time step t
        
        
        with autocast(device_type='cuda', enabled=True):
        
    
            # Create time_embedding
            time_embedding = torch.randint(
                0, 1000, (images.shape[0],), device=images.device
            ).long()
            
            if epoch >=140:
               time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
            # Create time
            t = time_embedding.float() / 1000

            # Get the v-prediction
            # print(t)
            # print(time_embedding)
            x_t_fdg = t * seg_fdg + (1 - t) * images
            v_fdg_prediction = model(x=x_t_fdg, timesteps=time_embedding,context=fdg_index)
            v_fdg = seg_fdg - images
            loss_fdg = F.mse_loss(v_fdg.float(), v_fdg_prediction.float())
            
            x_t_av45 = t * seg_av45 + (1 - t) * images
            v_av45_prediction = model(x=x_t_av45, timesteps=time_embedding,context=av45_index)
            v_av45 = seg_av45 - images
            loss_av45= F.mse_loss(v_av45.float(), v_av45_prediction.float())
            loss = loss_fdg + loss_av45  # 或使用加权：loss = alpha * loss_fdg + beta * loss_av45

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
            images = data["mri"].to(device)
            seg_fdg = data["fdg"].to(device) # this is the ground truth segmentation
            seg_av45 = data["av45"].to(device)
            fdg_index=data["fdg_index"].to(device)
            av45_index=data["av45_index"].to(device)
            # timesteps = torch.randint(0, 1000, (len(images),)).to(device)
            
            x_t = images
            N_sample = 1
            N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
            # progress_bar = tqdm([(i / (N_sample)) for i in range(N_sample)])
            progress_bar = [(i / (N_sample)) for i in range(N_sample)]
            for t in progress_bar:  # go through the noising process
                with autocast(device_type='cuda',enabled=False):
                    with torch.no_grad():
                        time_embedding = int(t * 1000)
                        # print(t)
                        # print(time_embedding)
                        v_fdg_output = model(x = x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device),context=fdg_index)
                        x_fdg_t = x_t + (v_fdg_output / N_sample_tensor)
                        x_fdg_t = torch.clamp(x_fdg_t, min=clip_sample_min, max=clip_sample_max)
                        
                        v_av45_output = model(x = x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device),context=av45_index)
                        x_av45_t = x_t + (v_av45_output / N_sample_tensor)
                        x_av45_t = torch.clamp(x_av45_t, min=clip_sample_min, max=clip_sample_max)
                
            
            val_fdg_loss = F.mse_loss(x_fdg_t.float(),  seg_fdg.float())
            val_av45_loss = F.mse_loss(x_av45_t.float(),  seg_av45.float())
            val_loss = val_fdg_loss + val_av45_loss
            
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
        
        current_fdg_img =  x_fdg_t.to('cpu')
        current_av45_img =  x_av45_t.to('cpu')
        labels_fdg = seg_fdg.to('cpu')
        labels_av45 = seg_av45.to('cpu')
        
        compare_3d([images,labels_fdg, current_fdg_img,labels_av45, current_av45_img])
        compare_3d_jet([current_fdg_img - labels_fdg,current_av45_img - labels_av45])
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=7)
        psnr_metric=PSNRMetric(1.0)

        ssim_fdg_value = ssim_metric(labels_fdg, current_fdg_img)
        ssim_av45_value = ssim_metric(labels_av45, current_av45_img)
        
        psnr_fdg_value = psnr_metric(labels_fdg, current_fdg_img)
        psnr_av45_value = psnr_metric(labels_av45, current_av45_img)

        print(f"fdg SSIM: {ssim_fdg_value.mean().item()}")
        print(f"av45 SSIM: {ssim_av45_value.mean().item()}")
        print(f"fdg PSNR: {psnr_fdg_value.mean().item()}") 
        print(f"av45 PSNR: {psnr_av45_value.mean().item()}") 

# total_time = time.time() - total_start
# print(f"train diffusion completed, total time: {total_time}.")
# plt.style.use("seaborn-bright")
# plt.title("Learning Curves Diffusion Model", fontsize=20)
# plt.plot(np.linspace(1, n_epochs, n_epochs), epoch_loss_list, color="C0", linewidth=2.0, label="Train")
# plt.plot(
#     np.linspace(val_interval, n_epochs, int(n_epochs / val_interval)),
#     val_epoch_loss_list,
#     color="C1",
#     linewidth=2.0,
#     label="Validation",
# )
# plt.yticks(fontsize=12)
# plt.xticks(fontsize=12)
# plt.xlabel("Epochs", fontsize=16)
# plt.ylabel("Loss", fontsize=16)
# plt.legend(prop={"size": 14})
# plt.show()