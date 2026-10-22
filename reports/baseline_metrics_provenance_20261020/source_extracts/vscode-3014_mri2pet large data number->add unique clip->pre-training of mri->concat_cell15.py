# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet large data number->add unique clip->pre-training of mri->concat.ipynb
# original_sha256=ffcb2c32728b4295b3049bcd2d346286fc845f0ba011fbcd68c6641253020b94; zero_based_cell=15
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

import torch





# checkpoint_path = '/home/ssd/liutuo/checkpoint/mri2pet/noise2image about mri2pet_donkey_150.pth'
# source_weight = torch.load(checkpoint_path)["model"]
# model_state_dict = model_1.state_dict()

# for key in model_state_dict.keys():
#     if key in source_weight:
#         if model_state_dict[key].shape == source_weight[key].shape:
#             model_state_dict[key] = source_weight[key]
#         else:
#             # 处理形状不匹配的情况
#             print(f"{key} shape mismatch: source {source_weight[key].shape}, target {model_state_dict[key].shape}")
#             source_shape = source_weight[key].shape
#             target_shape = model_state_dict[key].shape

#             # 假设我们只处理卷积层的情况
#             if len(source_shape) == len(target_shape) == 5:  # 3D卷积层
#                 if source_shape[1] < target_shape[1]:
#                     # 输入通道数不同，通过重复的方式扩展
#                     repeats = target_shape[1] // source_shape[1]
#                     source_weight_expanded = source_weight[key].repeat(1, repeats, 1, 1, 1)
#                     source_weight_expanded = source_weight_expanded[:, :target_shape[1], :, :, :]
#                 elif source_shape[1] > target_shape[1]:
#                     # 输入通道数过多，截断
#                     source_weight_expanded = source_weight[key][:, :target_shape[1], :, :, :]

#                 if source_shape[0] < target_shape[0]:
#                     # 输出通道数不同，通过重复的方式扩展
#                     repeats = target_shape[0] // source_shape[0]
#                     source_weight_expanded = source_weight_expanded.repeat(repeats, 1, 1, 1, 1)
#                     source_weight_expanded = source_weight_expanded[:target_shape[0], :, :, :, :]
#                 elif source_shape[0] > target_shape[0]:
#                     # 输出通道数过多，截断
#                     source_weight_expanded = source_weight_expanded[:target_shape[0], :, :, :, :]

#                 model_state_dict[key] = source_weight_expanded
#             else:
#                 print(f"Skipping parameter {key} due to incompatible shapes.")
#     else:
#         print(f"Parameter {key} not found in source model.")

# model_1.load_state_dict(model_state_dict)
# model_1.to(device)


checkpoint_path = '/home/ssd/liutuo/checkpoint/mri2pet/noise2image about mri2pet_donkey_150.pth'
#model.load_state_dict(torch.load(checkpoint_path)['model'])
#load model_1 form ckpt_path with shape dismatch

# def reinitialize_training_components(model):
#     optimizer = torch.optim.Adam(params=model.parameters(), lr=2.5e-5)
#     scheduler = DDIMScheduler(prediction_type='v_prediction',num_train_timesteps=1000,
#                            schedule="scaled_linear_beta",beta_start=0.0005, beta_end=0.0195)  # 根据需要重新初始化调度器
#     scaler = GradScaler()
#     return optimizer, scheduler, scaler


source_weight=torch.load(checkpoint_path)["model"]
model_state_dict=model_1.state_dict()
for key in model_state_dict.keys():
    #if key in target_weight.keys():
    if model_state_dict[key].shape==source_weight[key].shape:
        model_state_dict[key]=source_weight[key]
    else:
        # expand dims with copied value
        print(f"{key} shape dismatch: source {model_state_dict[key].shape}, target {source_weight[key].shape}")
        repeat_times=[yy//xx for yy,xx in zip(model_state_dict[key].shape,source_weight[key].shape)]
        model_state_dict[key]=source_weight[key].repeat(repeat_times)

model_1.load_state_dict(model_state_dict)
model_1.to(device)
#optimizer, scheduler, scaler=reinitialize_training_components(model_1)

n_epochs = 150
val_interval =30
epoch_loss_list = []
val_epoch_loss_list = []
scaler = GradScaler()
total_start = time.time()
checkpoint_dir = '/home/ssd/liutuo/checkpoint/mri2pet'

c = text_features[1].unsqueeze(0).unsqueeze(0).to(dtype=torch.float32).to(device)
for epoch in range(n_epochs):
    model_1.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg = data["pet"].to(device)  # this is the ground truth segmentation
        optimizer_1.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # pick a random time step t

        with autocast(enabled=True):
            # Generate random noise
            noise= donkey_noise_like(images).to(device)
            #noise = torch.randn_like(seg).to(device)
            noisy_seg = scheduler.add_noise(
                original_samples=seg, noise=noise, timesteps=timesteps
            )  # we only add noise to the segmentation mask
            combined = torch.cat(
                (images, noisy_seg), dim=1
            )
            #print( combined.shape)
            # we concatenate the brain MR image with the noisy segmenatation mask, to condition the generation process
            target = inferer.scheduler.get_velocity(seg, noise, timesteps)
            
            
            
            prediction = model_1(x=combined, timesteps=timesteps,context=c)
            # Get model prediction
            loss = F.mse_loss(prediction.float(), target.float())
        scaler.scale(loss).backward()
        scaler.step(optimizer_1)
        scaler.update()
        epoch_loss += loss.item()
        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})
    
    epoch_loss_list.append(epoch_loss / (step + 1))
    if (epoch + 1) % val_interval == 0:
        model_1.eval()
        val_epoch_loss = 0
        for step, data_val in enumerate(val_loader):
            images = data_val["mri"].to(device)
            seg = data_val["pet"].to(device)  # this is the ground truth segmentation
            timesteps = torch.randint(0, 1000, (len(images),)).to(device)
            with torch.no_grad():
                with autocast(enabled=True):
                    noise = torch.randn_like(seg).to(device)
                    noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
                    combined = torch.cat((images, noisy_seg), dim=1)
                    target = inferer.scheduler.get_velocity(seg, noise, timesteps)
                    prediction = model_1(x=combined, timesteps=timesteps,context=c)
                    
                    val_loss = F.mse_loss(prediction.float(), noise.float())
            val_epoch_loss += val_loss.item()
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
        torch.save(checkpoint, f'{checkpoint_dir}/mri2pet small data number->pre-training of mri->concat_second_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')
        
        # 采样过程
        model_1.eval()
        input_img = images.to(device)
        print(input_img.shape)
        noise= donkey_noise_like(images).to(device)
        current_img = noise  # for the segmentation mask, we start from random noise.
        combined = torch.cat((input_img, noise), dim=1)  # We concatenate the input brain MR image to add anatomical information.
        
        #scheduler.set_timesteps(num_inference_steps=1000)
        progress_bar = tqdm(scheduler.timesteps)
        for t in progress_bar:  # go through the noising process
            with autocast(enabled=False):
                with torch.no_grad():
                    model_output = model_1(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=c)
                    current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
                    combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

        current_img = current_img.to('cpu')
        labels = seg.to('cpu')
        compare_3d([labels, current_img])
        compare_3d_jet([current_img - labels])
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
        psnr_metric=PSNRMetric(1.0)
        

        ssim_value = ssim_metric(labels, current_img)
        psnr_value = psnr_metric(labels, current_img)

        print(f"SSIM: {ssim_value.mean().item()}")
        print(f"PSNR: {psnr_value.mean().item()}") 
torch.save(model_1.state_dict(), "./noise2image about mri2pet.pth")
total_time = time.time() - total_start
print(f"train diffusion completed, total time: {total_time}.")
plt.style.use("seaborn-bright")
plt.title("Learning Curves Diffusion Model", fontsize=20)
plt.plot(np.linspace(1, n_epochs, n_epochs), epoch_loss_list, color="C0", linewidth=2.0, label="Train")
plt.plot(
    np.linspace(val_interval, n_epochs, int(n_epochs / val_interval)),
    val_epoch_loss_list,
    color="C1",
    linewidth=2.0,
    label="Validation",
)
plt.yticks(fontsize=12)
plt.xticks(fontsize=12)
plt.xlabel("Epochs", fontsize=16)
plt.ylabel("Loss", fontsize=16)
plt.legend(prop={"size": 14})
plt.show()