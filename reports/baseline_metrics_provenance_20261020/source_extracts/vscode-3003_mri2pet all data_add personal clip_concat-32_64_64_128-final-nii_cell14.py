# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-32_64_64_128-final-nii.ipynb
# original_sha256=e82521b13192c0a68c5d47e5e056a54aee18fa578763884e200515f58d49af0c; zero_based_cell=14
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from torch.amp import GradScaler, autocast  # 从 torch.amp 导入 GradScaler

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

# 加载保存的模型参数
checkpoint = torch.load('/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_concat_final/noise2image about mri2pet_method_two_second_part_200.pth')
model.load_state_dict(checkpoint['model'])
model.eval()
model.to(device)

# 定义保存路径
train_save_path = '/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/generated_PET/train'
label_save_path = '/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/PET_nii'

# 初始化 MONAI 的 Orientationd 转换，确保图像的方向为 LPI
orientation = Orientationd(keys=["image"], axcodes="LPI")

# 获取已生成的文件名（不带扩展名 .nii）
generated_names = set([f.split('.nii')[0] for f in os.listdir(label_save_path)])

# 已经生成的文件数量计数器
generated_file_count = len(generated_names)
print(f"已经生成的文件数量: {generated_file_count}")

# 处理 train_loader 中的每个 batch
for i, data in enumerate(tqdm(train_loader, desc="Processing train_loader")):
    # 获取MRI图像、名字和其他信息
    input_img = data["mri"].to(device)
    labels = data["pet"].to(device)
    names = data["name"]  # 获取名字
    pet_index = data["pet_index"].to(device)

    # 初始化随机噪声
    noise = donkey_noise_like(input_img).to(device)
    current_img = noise  # 从随机噪声开始
    combined = torch.cat((input_img, noise), dim=1)  # 拼接MR图像和噪声

    # 通过模型生成PET图像
    for t in scheduler.timesteps:  # go through the noising process
        with autocast(device_type='cuda', enabled=True):
            with torch.no_grad():
                model_output = model(combined, timesteps=torch.Tensor((t,)).to(current_img.device),context=pet_index)
                current_img, _ = scheduler.step(model_output, t, current_img)  # this is the prediction x_t at the time step t
                combined = torch.cat((input_img, current_img), dim=1)  # in every step during the denoising process, the brain MR image is concatenated to add anatomical information


    # 将生成的PET图像和labels移回CPU
    current_img = current_img.to('cpu')
    labels = labels.to('cpu')
    # compare_3d([input_img,labels, current_img])
    # compare_3d_jet([current_img - labels])
    from generative.metrics import SSIMMetric
    from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
    ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0,kernel_size=11)
    psnr_metric=PSNRMetric(1.0)

    ssim_value = ssim_metric(labels, current_img)
    psnr_value = psnr_metric(labels, current_img)

    print(f"SSIM: {ssim_value.mean().item()}")
    print(f"PSNR: {psnr_value.mean().item()}") 
    # 对每个batch中的每个样本进行处理和保存
    for j in range(len(names)):
        name = names[j]  # 获取第 j 个样本的名字

        # 检查该文件是否已经生成
        if name in generated_names:
            print(f"{name}.nii 已经存在，跳过生成。")
            continue

        # ========== 处理生成的 PET 图像 ==========
        # 获取并去掉批次和通道维度
        pet_image_3d = current_img[j, 0].numpy()

        # 创建 NIfTI 图像并设置仿射矩阵
        pet_nifti = nib.Nifti1Image(pet_image_3d, affine=np.eye(4))

        # 将 NIfTI 图像转换为 torch.Tensor 以应用方向转换
        pet_tensor = torch.tensor(pet_image_3d)

        # 确保方向为 LPI
        pet_lpi = orientation({'image': pet_tensor})['image']

        # 将 LPI 方向的张量转换回 NIfTI 并保存
        pet_lpi_nifti = nib.Nifti1Image(pet_lpi.numpy(), affine=np.eye(4))

        # 保存生成的 PET NIfTI 图像
        pet_file_path = os.path.join(train_save_path, f"{name}.nii")
        nib.save(pet_lpi_nifti, pet_file_path)
        print(f"Saved generated PET for {name} to {pet_file_path}")

        # ========== 处理标签（labels） ==========
        # 获取并去掉批次和通道维度
        label_image_3d = labels[j, 0].numpy()

        # 创建 NIfTI 图像并设置仿射矩阵
        label_nifti = nib.Nifti1Image(label_image_3d, affine=np.eye(4))

        # 将 NIfTI 图像转换为 torch.Tensor 以应用方向转换
        label_tensor = torch.tensor(label_image_3d)

        # 确保方向为 LPI
        label_lpi = orientation({'image': label_tensor})['image']

        # 将 LPI 方向的张量转换回 NIfTI 并保存
        label_lpi_nifti = nib.Nifti1Image(label_lpi.numpy(), affine=np.eye(4))

        # 保存标签（labels）NIfTI 图像
        label_file_path = os.path.join(label_save_path, f"{name}.nii")
        nib.save(label_lpi_nifti, label_file_path)
        print(f"Saved labels for {name} to {label_file_path}")

        # 更新已生成的文件数量
        generated_file_count += 1
        print(f"当前已生成的文件数量: {generated_file_count}")
