# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-ddpm ddim.ipynb
# original_sha256=08513920dcb07f4ecfe20f56393afab040fd35cc826b4b3bb55308aff72afbbe; zero_based_cell=16
checkpoint_dir = '/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_concat_compare'
checkpoint = torch.load(f'{checkpoint_dir}/noise2image about mri2pet_method_two_second_part_160.pth')
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])

model.eval()
input_img = image_1.to(device)
print(input_img.shape)
noise= donkey_noise_like(images).to(device)
current_img = noise  # for the segmentation mask, we start from random noise.
combined = torch.cat((input_img, noise), dim=1)  # We concatenate the input brain MR image to add anatomical information.

#scheduler.set_timesteps(num_inference_steps=1000)
progress_bar = tqdm(scheduler.timesteps)
for t in progress_bar:  # go through the noising process
    with autocast(device_type='cuda', enabled=True):
        with torch.no_grad():
            model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device))
            current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
            combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information

current_img = current_img.to('cpu')
labels = label_1.to('cpu')
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