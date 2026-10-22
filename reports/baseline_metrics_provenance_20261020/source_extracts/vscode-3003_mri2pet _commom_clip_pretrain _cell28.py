# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _commom_clip_pretrain .ipynb
# original_sha256=3ac3eaad3376c070436bbfd1308f86c86b78400fe58bafb3c15514970497c016; zero_based_cell=28
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





n_epochs = 140
val_interval =10
epoch_loss_list = []
val_epoch_loss_list = []
scaler = GradScaler()  
total_start = time.time()
checkpoint_dir = '/home/data/liutuo/code/checkpoint/mri2pet-pretrain pet-mri2pet/second part'

# 定义裁剪的最小值和最大值
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1   # 设置合适的最大值

for epoch in range(n_epochs):
    model_1.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg = data["pet"].to(device) # this is the ground truth segmentation
        pet_index=data["pet_index"].to(device)
        optimizer_1.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # pick a random time step t
        
        
        with autocast(device_type='cuda', enabled=True):
        
    
            # Create time_embedding
            time_embedding = torch.randint(
                0, 1000, (images.shape[0],), device=images.device
            ).long()
            
            if epoch >=100:
               time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
            # Create time
            t = time_embedding.float() / 1000

            # Get the v-prediction
            # print(t)
            # print(time_embedding)
            x_t = t * seg + (1 - t) * images
            v_prediction = model_1(x=x_t, timesteps=time_embedding,context=pet_index)
            
            

            # Get the loss
            # print(t)
            # print(time_embedding)
            v = seg - images
            loss = F.mse_loss(v.float(), v_prediction.float())
        scaler.scale(loss).backward()
        scaler.step(optimizer_1)
        scaler.update()
        epoch_loss += loss.item()
        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})
        
        torch.cuda.empty_cache()
    
    epoch_loss_list.append(epoch_loss / (step + 1))
    if (epoch + 1) % val_interval == 0:
        model_1.eval()
        val_epoch_loss = 0
        for step, data_val in enumerate(val_loader):
            images = data_val["mri"].to(device)
            seg = data_val["pet"].to(device)  # this is the ground truth segmentation
            pet_index=data["pet_index"].to(device)
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
                        v_output = model_1(x = x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device),context=pet_index)
                        x_t = x_t + (v_output / N_sample_tensor)
                        x_t = torch.clamp(x_t, min=clip_sample_min, max=clip_sample_max)
                
            
            val_loss = F.mse_loss(x_t.float(),  seg.float())
            val_epoch_loss += val_loss.item()
            torch.cuda.empty_cache()
        print("Epoch", epoch + 1, "Validation loss", val_epoch_loss / (step + 1))
        val_epoch_loss_list.append(val_epoch_loss / (step + 1))
         # Saving model parameters
        print('epoch:', epoch + 1)
        print('learning rate:', optimizer_1.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model_1.state_dict(),
            'optimizer': optimizer_1.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/second_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')
        
        current_img =  x_t.to('cpu')
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