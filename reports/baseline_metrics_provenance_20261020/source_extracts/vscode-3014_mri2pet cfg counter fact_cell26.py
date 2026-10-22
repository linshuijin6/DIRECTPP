# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet cfg counter fact.ipynb
# original_sha256=0b443a3348c735cebca17b5a1c4b5aa70de04a0551f05c3a246f28aa0b68bb36; zero_based_cell=26
latent_space_depth =400
mri_test = mri_test_original.to(device)
pet_test = pet_test_original.to(device)
scheduler.clip_sample = False
class_embedding = embed(torch.zeros(1).long().to(device)).unsqueeze(1).to(device)
progress_bar = tqdm(range(latent_space_depth))

for i in progress_bar:  # go through the noising process
    t = i
    with torch.no_grad():
        timesteps_tensor = torch.Tensor([t]).to(device)
        model_output = model(mri_test, timesteps=timesteps_tensor, context=class_embedding)
        mri_test, _ = scheduler.reversed_step(model_output, t, mri_test)
        
        model_output_1 = model(pet_test, timesteps=timesteps_tensor, context=class_embedding)
        pet_test, _ = scheduler.reversed_step(model_output_1, t, pet_test)

latent_mri_test = mri_test
latent_pet_test = pet_test



ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
psnr_metric=PSNRMetric(1.0)

ssim_value = ssim_metric(latent_mri_test, latent_pet_test)
psnr_value = psnr_metric(latent_mri_test, latent_pet_test)

print(f"SSIM: {ssim_value.mean().item()}")
print(f"PSNR: {psnr_value.mean().item()}")   
compare_3d([latent_mri_test,latent_pet_test])
