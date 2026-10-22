# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow plus concat.ipynb
# original_sha256=e10d32890a81f3855df383392d3047aaee2ad35826ad9fa67529784282e7d1d4; zero_based_cell=16
# 加载上次训练的模型和优化器状态
checkpoint = torch.load(f'{checkpoint_dir}/noise2image about mri2pet_method_two_second_part_340.pth')
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
start_epoch = checkpoint['epoch'] + 1  # 从上次停止的地方继续

# 设置新的训练参数
new_epochs =20  # 继续训练的epoch数
total_epochs = start_epoch + new_epochs
val_interval = 1  # 验证间隔仍保持不变
epoch_loss_list = []  # 初始化epoch loss列表
val_epoch_loss_list = []  # 初始化验证epoch loss列表

for epoch in range(start_epoch, total_epochs):
    model.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg = data["pet"].to(device)  # this is the ground truth segmentation
        pet_index = data["pet_index"].to(device)
        optimizer.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # pick a random time step t

        with autocast(device_type='cuda', enabled=True):
            noise = donkey_noise_like(images).to(device)
            #noise = torch.randn_like(images).to(device)
            noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
            combined = torch.cat((images, noisy_seg), dim=1)
            target = inferer.scheduler.get_velocity(seg, noise, timesteps)

            prediction = model(x=combined, timesteps=timesteps, context=pet_index)
            loss = F.mse_loss(prediction.float(), target.float())
        scaler.scale(loss).backward()
        scaler.step(optimizer)
        scaler.update()
        epoch_loss += loss.item()
        progress_bar.set_postfix({"loss": epoch_loss / (step + 1)})

    epoch_loss_list.append(epoch_loss / (step + 1))

    if (epoch + 1) % val_interval == 0:
        model.eval()
        val_epoch_loss = 0
        for step, data_val in enumerate(val_loader):
            images = data_val["mri"].to(device)
            seg = data_val["pet"].to(device)
            pet_index = data_val["pet_index"].to(device)
            timesteps = torch.randint(0, 1000, (len(images),)).to(device)

            with torch.no_grad():
                with autocast(device_type='cuda', enabled=True):
                    noise = donkey_noise_like(images).to(device)
                    noisy_seg = scheduler.add_noise(original_samples=seg, noise=noise, timesteps=timesteps)
                    combined = torch.cat((images, noisy_seg), dim=1)
                    target = inferer.scheduler.get_velocity(seg, noise, timesteps)
                    prediction = model(x=combined, timesteps=timesteps, context=pet_index)
                    val_loss = F.mse_loss(prediction.float(), target.float())
            val_epoch_loss += val_loss.item()

        print("Epoch", epoch + 1, "Validation loss", val_epoch_loss / (step + 1))
        val_epoch_loss_list.append(val_epoch_loss / (step + 1))

        # 保存模型和优化器状态
        print('epoch:', epoch + 1)
        print('learning rate:', optimizer.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/noise2image about mri2pet_method_two_second_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')
         # Saving model parameters
        print('epoch:', epoch + 1)
        print('learning rate:', optimizer.state_dict()['param_groups'][0]['lr'])
        checkpoint = {
            'model': model.state_dict(),
            'optimizer': optimizer.state_dict(),
            'epoch': epoch
        }
        torch.save(checkpoint, f'{checkpoint_dir}/noise2image about mri2pet_method_two_second_part_{epoch + 1}.pth')
        print('Saved all parameters!\n')
        
        # 采样过程
        model.eval()
        input_img = image_1.to(device)
        print(input_img.shape)
        noise= donkey_noise_like(images).to(device)
        #noise = torch.randn_like(images).to(device)
        current_img = noise  # for the segmentation mask, we start from random noise.
        combined = torch.cat((input_img, noise), dim=1)  # We concatenate the input brain MR image to add anatomical information.
        
        #scheduler.set_timesteps(num_inference_steps=1000)
        progress_bar = tqdm(scheduler.timesteps)
        for t in progress_bar:  # go through the noising process
            with autocast(device_type='cuda', enabled=True): #with autocast(device_type='cuda', enabled=False):
                with torch.no_grad():
                    model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=pet_index)
                    current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
                    combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

        current_img = current_img.to('cpu')
        labels = label_1.to('cpu')
        compare_3d([input_img,labels, current_img])
        compare_3d_jet([current_img - labels])
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=11)
        psnr_metric=PSNRMetric(1.0)

        ssim_value = ssim_metric(labels, current_img)
        psnr_value = psnr_metric(labels, current_img)

        print(f"SSIM: {ssim_value.mean().item()}")
        print(f"PSNR: {psnr_value.mean().item()}") 
