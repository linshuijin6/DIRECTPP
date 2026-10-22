# Original DB: /home/ssddata/liutuo/.ipython/profile_default/history.sqlite
# session=111; line=9; session_start_as_stored=2025-05-13 16:04:39.346646; source_sha256=c8947a590d2f78287edfa756cea9d3712c544a5486f05df6fd7e3cc69b9beb1a
import os
import torch
from monai.metrics import MAEMetric, MSEMetric, PSNRMetric
from generative.metrics import SSIMMetric
from tqdm import tqdm
import numpy as np
import nibabel as nib  # 用于保存 NIfTI 格式的图像
import monai.transforms as mt

# 加载检查点
checkpoint_path = '/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized/first_part_90.pth'
checkpoint = torch.load(checkpoint_path)

# 初始化模型和优化器
model.load_state_dict(checkpoint['model'])
model.eval()  # 设置为推理模式
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# 定义评估指标
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
psnr_metric = PSNRMetric(max_val=1.0)
mse_metric = MSEMetric()
mae_metric = MAEMetric()

# 推理过程
clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1  # 设置合适的最大值

# 创建保存目录
output_dirs = {
    "mri": "/home/ssddata/liutuo/liutuo_data/test/ours single/data_augmentation_mri",
    "fdg": "/home/ssddata/liutuo/liutuo_data/test/ours single/data_augmentation_fdg",
    "av45": "/home/ssddata/liutuo/liutuo_data/test/ours single/data_augmentation_av45",
    "generated_fdg": "/home/ssddata/liutuo/liutuo_data/test/ours single/data_augmentation_fdg_generated",
    "generated_av45": "/home/ssddata/liutuo/liutuo_data/test/ours single/data_augmentation_av45_generated"
}
for dir_path in output_dirs.values():
    os.makedirs(dir_path, exist_ok=True)

# 数据增强变换
orientation_transform = mt.Orientationd(keys=["mri", "av45", "fdg"], axcodes="LPI")

with torch.no_grad():
    for step, data_val in enumerate(tqdm(train_loader, desc="Inference")):
        # 数据增强处理
        data_val = data_val  # data_val = orientation_transform(data_val)

        images = data_val["mri"].to(device)
        seg_fdg = data_val["fdg"].to(device)  # Ground truth FDG
        seg_av45 = data_val["av45"].to(device)  # Ground truth AV45
        fdg_index = data_val["fdg_index"].to(device)
        av45_index = data_val["av45_index"].to(device)
        names = data_val["name"]
        # 检查 FDG 和 AV45 数据是否为二值化（只有 0 和 1）
        has_fdg = not torch.all((seg_fdg == 0) | (seg_fdg == 1))  # 如果不是二值化数据，则参与计算
        has_av45 = not torch.all((seg_av45 == 0) | (seg_av45 == 1))  # 如果不是二值化数据，则参与计算

        # 固定 time_embedding 和 t
        time_embedding = torch.tensor([0], device=device, dtype=torch.long)
        t = time_embedding.float() / 1000  # t = 0

        # FDG 输出（仅当非二值化时计算）
        if has_fdg:
            v_fdg_output = model(
                x=images,
                timesteps=time_embedding,
                context=fdg_index
            )
            x_fdg_t = images + (v_fdg_output)  # t = 0，因此 x_fdg_t = images
            x_fdg_t = torch.clamp(x_fdg_t, min=clip_sample_min, max=clip_sample_max)

            # 检查形状并保存生成的 FDG 图像
            if x_fdg_t.shape == (1, 1, 160, 192, 160):
                x_fdg_t = x_fdg_t.squeeze()  # 去掉前两个维度 (1, 1)，得到 [160, 192, 160]
                x_fdg_np = x_fdg_t.cpu().numpy()  # 转换为 NumPy 数组
                output_path = os.path.join(output_dirs["generated_fdg"], f'generated_fdg_{names[0]}.nii.gz')  # 保存路径
                nib.save(nib.Nifti1Image(x_fdg_np, affine=np.eye(4)), output_path)  # 保存为 NIfTI 文件
                print(f"Saved generated FDG image to {output_path}")

        # AV45 输出（仅当非二值化时计算）
        if has_av45:
            v_av45_output = model(
                x=images,
                timesteps=time_embedding,
                context=av45_index
            )
            x_av45_t = images + (v_av45_output)  # t = 0，因此 x_av45_t = images
            x_av45_t = torch.clamp(x_av45_t, min=clip_sample_min, max=clip_sample_max)

            # 检查形状并保存生成的 AV45 图像
            if x_av45_t.shape == (1, 1, 160, 192, 160):
                x_av45_t = x_av45_t.squeeze()  # 去掉前两个维度 (1, 1)，得到 [160, 192, 160]
                x_av45_np = x_av45_t.cpu().numpy()  # 转换为 NumPy 数组
                output_path = os.path.join(output_dirs["generated_av45"], f'generated_av45_{names[0]}.nii.gz')  # 保存路径
                nib.save(nib.Nifti1Image(x_av45_np, affine=np.eye(4)), output_path)  # 保存为 NIfTI 文件
                print(f"Saved generated AV45 image to {output_path}")

        # 保存真实的 MRI、FDG 和 AV45 图像
        if images.shape == (1, 1, 160, 192, 160):
            images = images.squeeze()  # 去掉前两个维度 (1, 1)，得到 [160, 192, 160]
            images_np = images.cpu().numpy()  # 转换为 NumPy 数组
            output_path = os.path.join(output_dirs["mri"], f'real_mri_{names[0]}.nii.gz')  # 保存路径
            nib.save(nib.Nifti1Image(images_np, affine=np.eye(4)), output_path)  # 保存为 NIfTI 文件
            print(f"Saved real MRI image to {output_path}")

        if seg_fdg.shape == (1, 1, 160, 192, 160):
            seg_fdg = seg_fdg.squeeze()  # 去掉前两个维度 (1, 1)，得到 [160, 192, 160]
            seg_fdg_np = seg_fdg.cpu().numpy()  # 转换为 NumPy 数组
            output_path = os.path.join(output_dirs["fdg"], f'real_fdg_{names[0]}.nii.gz')  # 保存路径
            nib.save(nib.Nifti1Image(seg_fdg_np, affine=np.eye(4)), output_path)  # 保存为 NIfTI 文件
            print(f"Saved real FDG image to {output_path}")

        if seg_av45.shape == (1, 1, 160, 192, 160):
            seg_av45 = seg_av45.squeeze()  # 去掉前两个维度 (1, 1)，得到 [160, 192, 160]
            seg_av45_np = seg_av45.cpu().numpy()  # 转换为 NumPy 数组
            output_path = os.path.join(output_dirs["av45"], f'real_av45_{names[0]}.nii.gz')  # 保存路径
            nib.save(nib.Nifti1Image(seg_av45_np, affine=np.eye(4)), output_path)  # 保存为 NIfTI 文件
            print(f"Saved real AV45 image to {output_path}")

        # 计算 SSIM、PSNR、MSE 和 MAE（仅当非二值化时计算）
        if has_fdg and x_fdg_t is not None:
            ssim_fdg_value = ssim_metric(seg_fdg.unsqueeze(0).unsqueeze(0), x_fdg_t.unsqueeze(0).unsqueeze(0))
            psnr_fdg_value = psnr_metric(seg_fdg.unsqueeze(0).unsqueeze(0), x_fdg_t.unsqueeze(0).unsqueeze(0))
            mse_fdg_value = mse_metric(seg_fdg.unsqueeze(0).unsqueeze(0), x_fdg_t.unsqueeze(0).unsqueeze(0))
            mae_fdg_value = mae_metric(seg_fdg.unsqueeze(0).unsqueeze(0), x_fdg_t.unsqueeze(0).unsqueeze(0))
            print(f"[FDG] SSIM: {ssim_fdg_value.mean().item():.4f}, "
                  f"PSNR: {psnr_fdg_value.mean().item():.4f}, "
                  f"MSE: {mse_fdg_value.mean().item():.4f}, "
                  f"MAE: {mae_fdg_value.mean().item():.4f}")

        if has_av45 and x_av45_t is not None:
            ssim_av45_value = ssim_metric(seg_av45.unsqueeze(0).unsqueeze(0), x_av45_t.unsqueeze(0).unsqueeze(0))
            psnr_av45_value = psnr_metric(seg_av45.unsqueeze(0).unsqueeze(0), x_av45_t.unsqueeze(0).unsqueeze(0))
            mse_av45_value = mse_metric(seg_av45.unsqueeze(0).unsqueeze(0), x_av45_t.unsqueeze(0).unsqueeze(0))
            mae_av45_value = mae_metric(seg_av45.unsqueeze(0).unsqueeze(0), x_av45_t.unsqueeze(0).unsqueeze(0))
            print(f"[AV45] SSIM: {ssim_av45_value.mean().item():.4f}, "
                  f"PSNR: {psnr_av45_value.mean().item():.4f}, "
                  f"MSE: {mse_av45_value.mean().item():.4f}, "
                  f"MAE: {mae_av45_value.mean().item():.4f}")