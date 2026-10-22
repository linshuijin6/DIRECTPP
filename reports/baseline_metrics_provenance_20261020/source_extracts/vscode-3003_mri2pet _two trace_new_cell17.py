# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _two trace_new.ipynb
# original_sha256=520a2ec0f712b2bfbb40752269db4f412cc0624c464b8481e053f41701259a3c; zero_based_cell=17
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
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1.0   # 设置合适的最大值
# Load the saved checkpoint
checkpoint_path = "/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_flow/noise2image about mri2pet_method_two_second_part_141.pth"
checkpoint = torch.load(checkpoint_path)
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
model.eval()  # Set the model to evaluation mode

# Evaluation loop
with torch.no_grad():
    for step, data_val in enumerate(val_loader):
        images = data_val["mri"].to(device)
        seg = data_val["pet"].to(device)  # Ground truth segmentation
        pet_index = data_val["pet_index"].to(device)
        names = data_val["name"]  # Get subject names

        x_t = images
        N_sample = 1
        N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
        progress_bar = [(i / N_sample) for i in range(N_sample)]
        t=0
        for t in progress_bar:
            with autocast(device_type='cuda', enabled=False):
                time_embedding = torch.tensor([0], device=images.device, dtype=torch.long)
                time_embedding = int(t * 1000)
                v_output = model(x=x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device), context=pet_index)
                x_t = x_t + (v_output / N_sample_tensor)
                x_t = torch.clamp(x_t, min=clip_sample_min, max=clip_sample_max)

        # Calculate MSE loss for this batch
        val_loss = F.mse_loss(x_t.float(), seg.float())
        val_epoch_loss += val_loss.item()

        # Move data to CPU for metric calculations
        current_img = x_t.to('cpu')
        labels = seg.to('cpu')

        # Calculate metrics for the current batch
        ssim_value = ssim_metric(labels, current_img).mean().item()
        psnr_value = psnr_metric(labels, current_img).mean().item()
        mse_value = mse_metric(labels, current_img).mean().item()
        mae_value = mae_metric(labels, current_img).mean().item()

        # Accumulate metrics for averaging
        ssim_total += ssim_value
        psnr_total += psnr_value
        mse_total += mse_value
        mae_total += mae_value
        num_batches += 1

        # Print metrics for the current batch
        for idx, name in enumerate(names):
            print(f"Subject name: {name}")
            print(f"SSIM: {ssim_value}, PSNR: {psnr_value}, MSE: {mse_value}, MAE: {mae_value}")

    # Calculate and print average metrics
    avg_ssim = ssim_total / num_batches
    avg_psnr = psnr_total / num_batches
    avg_mse = mse_total / num_batches
    avg_mae = mae_total / num_batches

    print("Average metrics over all validation batches:")
    print(f"SSIM: {avg_ssim}")
    print(f"PSNR: {avg_psnr}")
    print(f"MSE: {avg_mse}")
    print(f"MAE: {avg_mae}")
    print("Validation loss:", val_epoch_loss / num_batches)
