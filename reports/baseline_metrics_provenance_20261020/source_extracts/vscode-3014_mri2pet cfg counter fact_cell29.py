# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet cfg counter fact.ipynb
# original_sha256=0b443a3348c735cebca17b5a1c4b5aa70de04a0551f05c3a246f28aa0b68bb36; zero_based_cell=29
import torch
from tqdm import tqdm
from monai.metrics import SSIMMetric, PSNRMetric

# 设定范围
latent_space_depth_range = range(100, 501)

# 初始化保存最佳SSIM和PSNR值及对应步数
best_ssim_value = -1
best_psnr_value = -1
best_ssim_depth = 0
best_psnr_depth = 0

# 初始化SSIM和PSNR Metric
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0)
psnr_metric = PSNRMetric(1.0)

# 保存初始状态的数据
mri_test_initial = mri_test.to(device)
pet_test_initial = pet_test.to(device)

# 只使用一个总进度条
overall_progress_bar = tqdm(total=len(latent_space_depth_range), desc="Overall Progress", ncols=100)

for latent_space_depth in latent_space_depth_range:
    # 恢复到初始状态
    mri_test = mri_test_initial.clone()
    pet_test = pet_test_initial.clone()
    
    scheduler.clip_sample = False
    class_embedding = embed(torch.zeros(1).long().to(device)).unsqueeze(1).to(device)
    
    for t in range(latent_space_depth):
        with torch.no_grad():
            timesteps_tensor = torch.Tensor([t]).to(device)
            
            # 处理MRI数据
            model_output_mri = model(mri_test, timesteps=timesteps_tensor, context=class_embedding)
            mri_test, _ = scheduler.reversed_step(model_output_mri, t, mri_test)
            
            # 处理PET数据
            model_output_pet = model(pet_test, timesteps=timesteps_tensor, context=class_embedding)
            pet_test, _ = scheduler.reversed_step(model_output_pet, t, pet_test)
    
    latent_mri_test = mri_test
    latent_pet_test = pet_test

    # 计算SSIM和PSNR值
    ssim_value = ssim_metric(latent_mri_test, latent_pet_test).mean().item()
    psnr_value = psnr_metric(latent_mri_test, latent_pet_test).mean().item()

    # 更新最佳SSIM值及对应步数
    if ssim_value > best_ssim_value:
        best_ssim_value = ssim_value
        best_ssim_depth = latent_space_depth

    # 更新最佳PSNR值及对应步数
    if psnr_value > best_psnr_value:
        best_psnr_value = psnr_value
        best_psnr_depth = latent_space_depth

    # 更新总体进度条
    overall_progress_bar.update(1)

# 关闭总体进度条
overall_progress_bar.close()

# 输出结果
print(f"最佳SSIM值: {best_ssim_value}, 对应步数: {best_ssim_depth}")
print(f"最佳PSNR值: {best_psnr_value}, 对应步数: {best_psnr_depth}")
