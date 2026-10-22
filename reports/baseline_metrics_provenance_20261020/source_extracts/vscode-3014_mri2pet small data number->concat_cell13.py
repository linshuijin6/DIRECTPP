# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet small data number->concat.ipynb
# original_sha256=07393787a08da1928ed9b69fcb610d74139a4f0e7f71ac3db9fbc917cfe7b255; zero_based_cell=13
model.eval()
input_img = image_1.to(device)
print(input_img.shape)
noise= donkey_noise_like(images).to(device)
current_img = noise  # for the segmentation mask, we start from random noise.
combined = torch.cat((input_img, noise), dim=1)  # We concatenate the input brain MR image to add anatomical information.

#scheduler.set_timesteps(num_inference_steps=1000)
progress_bar = tqdm(scheduler.timesteps)
for t in progress_bar:  # go through the noising process
    with autocast(enabled=False):
        with torch.no_grad():
            model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=c_pet)
            current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
            combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

current_img = current_img.to('cpu')
labels = labels.to('cpu')
compare_3d([input_img,labels, current_img],fixed=False)
compare_3d_jet([current_img - labels],fixed=False)
from generative.metrics import SSIMMetric
from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
ssim_metric = SSIMMetric(spatial_dims=3, data_range=2.0,kernel_size=7)
psnr_metric=PSNRMetric(2.0)

ssim_value = ssim_metric(labels, current_img)
psnr_value = psnr_metric(labels, current_img)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}") 