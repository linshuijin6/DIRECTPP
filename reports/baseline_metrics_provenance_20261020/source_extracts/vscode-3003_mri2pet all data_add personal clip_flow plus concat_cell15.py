# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow plus concat.ipynb
# original_sha256=e10d32890a81f3855df383392d3047aaee2ad35826ad9fa67529784282e7d1d4; zero_based_cell=15
# Load the checkpoint
checkpoint = torch.load(f'{checkpoint_dir}/noise2image about mri2pet_method_two_second_part_20.pth')
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
start_epoch = checkpoint['epoch'] + 1  # Start from the next epoch after the last saved one

# Set new training parameters
new_epochs = 250  # Number of additional epochs to train
total_epochs = start_epoch + new_epochs
val_interval = 10  # Keep validation interval unchanged
epoch_loss_list = []  # Initialize epoch loss list
val_epoch_loss_list = []  # Initialize validation epoch loss list

# Training loop
for epoch in range(start_epoch, total_epochs):  # Start from `start_epoch`
    model.train()
    epoch_loss = 0
    progress_bar = tqdm(enumerate(train_loader), total=len(train_loader), ncols=70)
    progress_bar.set_description(f"Epoch {epoch}")
    for step, data in progress_bar:
        images = data["mri"].to(device)
        seg = data["pet"].to(device)  # Ground truth segmentation
        pet_index = data["pet_index"].to(device)
        optimizer.zero_grad(set_to_none=True)
        timesteps = torch.randint(0, 1000, (len(images),)).to(device)  # Random time step t
        
        with autocast(device_type='cuda', enabled=True):
            # Create time_embedding
            time_embedding = torch.randint(0, 1000, (images.shape[0],), device=images.device).long()
            if epoch > 150:
               time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
            
            t = time_embedding.float() / 1000  # Convert time to float scale

            # Get the v-prediction
            x_t = t * seg + (1 - t) * images
            v_prediction = model(x=x_t, timesteps=time_embedding, context=pet_index)

            # Calculate the loss
            v = seg - images
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
            
            x_t = images
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
