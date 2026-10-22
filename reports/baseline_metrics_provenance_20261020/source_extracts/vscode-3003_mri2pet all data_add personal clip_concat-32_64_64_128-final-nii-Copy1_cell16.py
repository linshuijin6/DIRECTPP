# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-32_64_64_128-final-nii-Copy1.ipynb
# original_sha256=b3aec5233333cd9767b4980ee63cbccc23680fa1d0eaea81dc47c2b71a07f46b; zero_based_cell=16
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from torch.amp import GradScaler, autocast  # 从 torch.amp 导入 GradScaler
import monai.transforms as mt
from generative.networks.nets import DiffusionModelUNet
from generative.networks.schedulers import DDPMScheduler,DDIMScheduler
from generative.inferers import DiffusionInferer
model= DiffusionModelUNet(
    spatial_dims=3,
    in_channels=2,#1,
    out_channels=1,
    num_channels=(32,64,64,128),
    attention_levels=(False,False,False,True),
    num_res_blocks=1,
    num_head_channels=(0,0,0, 128),
    with_conditioning=True,
    cross_attention_dim=512,
    use_flash_attention=True,
)



model.to(device)
scheduler = DDPMScheduler(prediction_type="v_prediction", num_train_timesteps=1000,schedule="scaled_linear_beta",
                          beta_start=0.0005, beta_end=0.0195)
scheduler.set_timesteps(num_inference_steps=1000)
optimizer= torch.optim.Adam(params=model.parameters(), lr=2.5e-5)
inferer = DiffusionInferer(scheduler)
import torch
import numpy as np
from tqdm import tqdm
from generative.metrics import SSIMMetric

import os
import nibabel as nib



# 加载保存的模型参数
checkpoint = torch.load('/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_concat_final/noise2image about mri2pet_method_two_second_part_180.pth')
model.load_state_dict(checkpoint['model'])
model.eval()
model.to(device)
# 定义保存路径
val_save_path = '/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/generated_PET'
label_save_path = '/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/PET_nii'

# 初始化 MONAI 的 Orientationd 转换，确保图像的方向为 LPI
orientation = mt.Orientationd(keys=["image"], axcodes="LPI")

# 获取已生成的文件名（不带扩展名 .nii）
generated_names = set([f.split('.nii')[0] for f in os.listdir(label_save_path)])

# 初始化一个列表来存储未生成的文件名
missing_names = []

# 处理 train_loader 中的每个 batch
for i, data in enumerate(tqdm(val_loader, desc="Checking train_loader")):
    names = data["name"]  # 获取名字

    # 检查哪些文件还未生成
    for j in range(len(names)):
        name = names[j]  # 获取第 j 个样本的名字
        if name not in generated_names:
            missing_names.append(name)

# 输出未生成文件的数量和名字
print(f"需要生成的文件数量: {len(missing_names)}")
print(f"未生成的文件名: {missing_names}")

# 开始处理未生成的文件
for i, data in enumerate(tqdm(val_loader, desc="Processing train_loader")):
    names = data["name"]  # 获取名字
    
    # 先检查哪些文件还未生成
    process_indices = []
    for j in range(len(names)):
        name = names[j]
        # 只处理未生成的文件
        if name in missing_names:
            process_indices.append(j)
    
    # 如果当前 batch 没有需要处理的文件，跳过
    if not process_indices:
        continue
    
    # 只处理未生成文件的相关数据
    input_img = data["mri"][process_indices].to(device)
    labels = data["pet"][process_indices].to(device)
    pet_index = data["pet_index"][process_indices].to(device)

    # 初始化随机噪声
    noise = donkey_noise_like(input_img).to(device)
    current_img = noise  # 从随机噪声开始
    combined = torch.cat((input_img, noise), dim=1)  # 拼接MR图像和噪声

    # 通过模型生成PET图像
    for t in scheduler.timesteps:  # go through the noising process
        with autocast(device_type='cuda', enabled=True):
            with torch.no_grad():
                model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device), context=pet_index)
                current_img, _ = scheduler.step(model_output, t, current_img)
                combined = torch.cat((input_img, current_img), dim=1)

    # 将生成的PET图像和labels移回CPU
    current_img = current_img.to('cpu')
    labels = labels.to('cpu')

    from generative.metrics import SSIMMetric
    from monai.metrics import (MAEMetric, MSEMetric, PSNRMetric,)
    ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=11)
    psnr_metric = PSNRMetric(1.0)

    ssim_value = ssim_metric(labels, current_img)
    psnr_value = psnr_metric(labels, current_img)

    print(f"SSIM: {ssim_value.mean().item()}")
    print(f"PSNR: {psnr_value.mean().item()}")

    # 遍历处理的样本
    for idx, j in enumerate(process_indices):
        name = names[j]

        # ========== 处理生成的 PET 图像 ==========
        pet_image_3d = current_img[idx, 0].numpy()
        pet_tensor = torch.tensor(pet_image_3d)
        pet_lpi = orientation({'image': pet_tensor})['image']
        pet_lpi_nifti = nib.Nifti1Image(pet_lpi.numpy(), affine=np.eye(4))

        # 保存生成的 PET NIfTI 图像
        pet_file_path = os.path.join(val_save_path, f"{name}.nii")
        nib.save(pet_lpi_nifti, pet_file_path)
        print(f"Saved generated PET for {name} to {pet_file_path}")

        # ========== 处理标签（labels） ==========
        label_image_3d = labels[idx, 0].numpy()
        label_tensor = torch.tensor(label_image_3d)
        label_lpi = orientation({'image': label_tensor})['image']
        label_lpi_nifti = nib.Nifti1Image(label_lpi.numpy(), affine=np.eye(4))

        # 保存标签（labels）NIfTI 图像
        label_file_path = os.path.join(label_save_path, f"{name}.nii")
        nib.save(label_lpi_nifti, label_file_path)
        print(f"Saved labels for {name} to {label_file_path}")
