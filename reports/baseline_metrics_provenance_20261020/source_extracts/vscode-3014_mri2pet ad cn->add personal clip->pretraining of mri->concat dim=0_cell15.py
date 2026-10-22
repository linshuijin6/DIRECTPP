# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet ad cn->add personal clip->pretraining of mri->concat dim=0.ipynb
# original_sha256=4c4b13b6cac632299ab15de33f38820cbc3b5e926b9993e3c153ce5458a5b4c4; zero_based_cell=15
import torch
import os
import time
from torch.cuda.amp import GradScaler, autocast
from tqdm import tqdm
import matplotlib.pyplot as plt
import numpy as np

# 假设你已经定义并初始化了你的模型model_1、优化器optimizer_1、scheduler和其他相关对象

# 设置加载检查点的路径
checkpoint_path = '/home/ssd/liutuo/checkpoint/mri2pet/mri2pet ad cn->add personal clip->pretraining of mri->concat dim=0/noise2image about mri2pet_method_two_second_part_150.pth'

# 加载检查点
checkpoint = torch.load(checkpoint_path)
model_1.load_state_dict(checkpoint['model'])
optimizer_1.load_state_dict(checkpoint['optimizer'])

# 设置训练参数
n_epochs = 160  # 你希望训练到第150个epoch
val_interval = 1
epoch_loss_list = []
val_epoch_loss_list = []
scaler = GradScaler()
total_start = time.time()
checkpoint_dir = '/home/ssd/liutuo/checkpoint/mri2pet/mri2pet ad cn->add personal clip->pretraining of mri->concat'

# 从141个epoch开始继续训练
for epoch in range(141, n_epochs + 1):  # 从141到150
    model_1.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg = data["pet"].to(device)
        pet_index = data["pet_index"].to(device)
        optimizer_1.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)
        
        with autocast(enabled=True):
            noise = donkey_noise_like(images).to(device)
            noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
            combined = torch.cat((images, noisy_seg), dim=1)
            target = inferer.scheduler.get_velocity(seg, noise, timesteps)
            prediction = model_1(x=combined, timesteps=timesteps, context=pet_index)
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
            seg = data_val["pet"].to(device)
            pet_index = data_val["pet_index"].to(device)
            timesteps = torch.randint(0, 1000, (len(images),)).to(device)
            
            with torch.no_grad():
                with autocast(enabled=True):
                    noise = torch.randn_like(seg).to(device)
                    noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
                    combined = torch.cat((images, noisy_seg), dim=1)
                    target = inferer.scheduler.get_velocity(seg, noise, timesteps)
                    prediction = model_1(x=combined, timesteps=timesteps, context=pet_index)
                    val_loss = F.mse_loss(prediction.float(), target.float())
            val_epoch_loss += val_loss.item()
        
        print("Epoch", epoch + 1, "Validation loss", val_epoch_loss / (step + 1))
        val_epoch_loss_list.append(val_epoch_loss / (step + 1))

        # 保存模型参数
        checkpoint = {
            'model': model_1.state_dict(),
            'optimizer': optimizer_1.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/noise2image_about_mri2pet_method_two_second_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')

        # 采样过程 (在验证过程中进行, 这部分代码在此省略, 因为它已经在原始代码中包含)
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
                    model_output = model_1(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=pet_index)
                    current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
                    combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

        current_img = current_img.to('cpu')
        labels = seg.to('cpu')
        compare_3d([input_img,labels, current_img])
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
