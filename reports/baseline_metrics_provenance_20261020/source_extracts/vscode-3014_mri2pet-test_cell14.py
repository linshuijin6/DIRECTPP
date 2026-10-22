# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet-test.ipynb
# original_sha256=6574c514d21920c800ea87d5dcaa15570538b13039dcb6cf88434e3ee0010796; zero_based_cell=14
n_epochs = 125
val_interval =10
epoch_loss_list = []
val_epoch_loss_list = []
scaler = GradScaler()
total_start = time.time()
checkpoint_dir = '/home/ssd/liutuo/checkpoint/mri2pet/test'
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
            noise = pyramid_noise_like(images).to(device)
            #noise = torch.randn_like(seg).to(device)
            noisy_seg = scheduler.add_noise(
                original_samples=seg, noise=noise, timesteps=timesteps
            )  # we only add noise to the segmentation mask
            combined = torch.cat(
                (images, noisy_seg), dim=1
            )
            #print( combined.shape)
            # we concatenate the brain MR image with the noisy segmenatation mask, to condition the generation process
            prediction = model_1(x=combined, timesteps=timesteps)
            # Get model prediction
            loss = F.mse_loss(prediction.float(), noise.float())
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
                    prediction = model_1(x=combined, timesteps=timesteps)
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
        torch.save(checkpoint, f'{checkpoint_dir}/noise2image about mri2pet_{epoch + 1}.pth')
        print('Saved all parameters!\n')
        
        # 采样过程
        model_1.eval()
        input_img = images.to(device)
        print(input_img.shape)
        noise = torch.randn_like(input_img).to(device)
        current_img = noise  # for the segmentation mask, we start from random noise.
        combined = torch.cat((input_img, noise), dim=1)  # We concatenate the input brain MR image to add anatomical information.
        
        scheduler.set_timesteps(num_inference_steps=1000)
        progress_bar = tqdm(scheduler.timesteps)
        for t in progress_bar:  # go through the noising process
            with autocast(enabled=False):
                with torch.no_grad():
                    model_output = model_1(combined, timesteps=torch.Tensor((t,)).to(current_img.device))
                    current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
                    combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

        current_img = current_img.to('cpu')
        labels = seg.to('cpu')
        compare_3d([current_img,labels,input_img])
        compare_3d_jet([current_img - labels])
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
        psnr_metric=PSNRMetric(1.0)

        ssim_value = ssim_metric(current_img, labels)
        psnr_value = psnr_metric(current_img, labels)

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