# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _clip_pretrain .ipynb
# original_sha256=a63b643b453712b031750a230cb4c85366b37487a881bf3f4360fc7c49d0295e; zero_based_cell=24
from generative.metrics import SSIMMetric
from monai.metrics import MAEMetric, MSEMetric, PSNRMetric
import torch.nn.functional as F
# Initialize metrics
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
psnr_metric = PSNRMetric(1.0)
mae_metric = MAEMetric()
mse_metric = MSEMetric()

# Initialize accumulators for average metrics
ssim_total = 0
psnr_total = 0
mse_total = 0
mae_total = 0
val_epoch_loss = 0
num_batches = 0

# Load the saved checkpoint
checkpoint_path = "/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_flow/noise2image about mri2pet_method_two_second_part_10.pth"
checkpoint = torch.load(checkpoint_path)
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
model.eval()  # Set the model to evaluation mode
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1.0   # 设置合适的最大值

# Evaluation loop
with torch.no_grad():
    for step, data_val in enumerate(train_loader):
        if step >= 5:  # Stop after processing the first 20 batches
            break

        images = data_val["mri"].to(device)
        seg = data_val["pet"].to(device)  # Ground truth segmentation
        pet_index = data_val["pet_index"].to(device)
        names = data_val["name"]  # Get subject names
        time_embedding = torch.randint(0, 1000, (images.shape[0],), device=images.device).long()
        time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
        t = time_embedding.float() / 1000  # Convert time to float scale
        time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)

        x_t = images
        N_sample =1
        N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
        progress_bar = [(i / N_sample) for i in range(N_sample)]
        
        for t in progress_bar:
            with autocast(device_type='cuda', enabled=False):

                time_embedding = int(t * 1000)
                time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)

                v_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=pet_index)
                x_t = x_t + (v_output / N_sample_tensor)
                x_t = torch.clamp(x_t, min=clip_sample_min, max=clip_sample_max)

        # Calculate MSE loss for this batch
        val_loss = F.mse_loss(x_t.float(), seg.float())
        val_epoch_loss += val_loss.item()


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