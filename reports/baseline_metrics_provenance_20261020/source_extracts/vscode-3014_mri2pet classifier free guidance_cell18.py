# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet classifier free guidance.ipynb
# original_sha256=73401a5c9b161afd3a80e3f2f705cc3dbc872d2e6ced7bf440aee41cc892eef2; zero_based_cell=18
device = torch.device("cuda")
import torch
import time
from tqdm import tqdm
from torch.cuda.amp import GradScaler, autocast
import torch.nn.functional as F

n_epochs =150
val_interval =30
epoch_loss_list = []
val_epoch_loss_list = []

scaler = GradScaler()
total_start = time.time()
for epoch in range(n_epochs):
    controlnet.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, batch in progress_bar:
        images = batch["pet"].to(device)
        masks = batch["mri"].to(device)
        #print(images.shape)
        optimizer.zero_grad(set_to_none=True)

        with autocast(enabled=True):
            # Generate random noise
            #noise = torch.randn_like(images).to(device)
            noise = donkey_noise_like(images).to(device)

            # Create timesteps
            timesteps = torch.randint(
                0, inferer.scheduler.num_train_timesteps, (images.shape[0],), device=images.device
            ).long()
            
            #noise = torch.randn_like(seg).to(device)
            noisy_seg = scheduler.add_noise(
                original_samples=seg, noise=noise, timesteps=timesteps
            )  # we only add noise to the segmentation mask
            combined = torch.cat(
                (images, noisy_seg), dim=1
            )

            noise_pred = controlnet_inferer(inputs = combined, diffusion_model = model_1, 
                                            controlnet = controlnet, noise = noise, 
                                            timesteps = timesteps,
                                           cn_cond = masks, )

            loss = F.mse_loss(noise_pred.float(), noise.float())

        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()

        epoch_loss += loss.item()

        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})
    epoch_loss_list.append(epoch_loss / (step + 1))

    if (epoch + 1) % val_interval == 0:
        controlnet.eval()
        val_epoch_loss = 0
        for step, batch in enumerate(val_loader):
            images = batch["pet"].to(device)
            masks = batch["mri"].to(device)

            with torch.no_grad():
                with autocast(enabled=True):
                    noise = torch.randn_like(images).to(device)
                    timesteps = torch.randint(
                        0, controlnet_inferer.scheduler.num_train_timesteps, (images.shape[0],), device=images.device
                    ).long()
                    noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)  
                    # we only add noise to the segmentation mask
                    combined = torch.cat((images, noisy_seg), dim=1)
                    
                    noise_pred = controlnet_inferer(inputs = combined, diffusion_model = model_1, 
                                            controlnet = controlnet, noise = noise, 
                                            timesteps = timesteps,
                                           cn_cond = masks, )
                    val_loss = F.mse_loss(noise_pred.float(), noise.float())


            val_epoch_loss += val_loss.item()

            progress_bar.set_postfix({"val_loss": val_epoch_loss / (step + 1)})
            break

        val_epoch_loss_list.append(val_epoch_loss / (step + 1))

        # Saving model parameters
        print('epoch:', epoch + 1)
        print('learning rate:', optimizer.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model_1.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint,  f'{checkpoint_dir}/controlnet mri2pet_second_part_test_{epoch + 1}.pth')
        print('Saved all parameters!\n')

        # Sampling image during training with controlnet conditioning
        controlnet.eval()
        with torch.no_grad():
            with autocast(enabled=True):
                noise = donkey_noise_like(images).to(device)
                input_img = images.to(device)
                combined = torch.cat((input_img, noise), dim=1)
                sample = controlnet_inferer.sample(
                    input_noise=combined,
                    diffusion_model=model_1,
                    controlnet=controlnet,
                    cn_cond=masks[0, None, ...],
                    scheduler=scheduler,
                )
        print(sample.shape)
        images = images.to('cpu')
        pet_sample = sample.to('cpu')
        compare_3d([masks, images, pet_sample])
        compare_3d_jet([images - pet_sample])
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
        psnr_metric=PSNRMetric(1.0)

        ssim_value = ssim_metric(pet_sample, images)
        psnr_value = psnr_metric(pet_sample, images)

        print(f"SSIM: {ssim_value.mean().item()}")
        print(f"PSNR: {psnr_value.mean().item()}")    


total_time = time.time() - total_start
print(f"train completed, total time: {total_time}.")