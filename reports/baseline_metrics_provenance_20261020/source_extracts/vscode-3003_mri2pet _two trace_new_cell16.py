# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet _two trace_new.ipynb
# original_sha256=520a2ec0f712b2bfbb40752269db4f412cc0624c464b8481e053f41701259a3c; zero_based_cell=16
import torch
from generative.metrics import SSIMMetric
from monai.metrics import MAEMetric, MSEMetric, PSNRMetric
import torch.nn.functional as F

clip_sample_min = 0  # 设置合适的最小值
clip_sample_max = 1   # 设置合适的最大值
# 初始化指标
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
psnr_metric = PSNRMetric(1.0)
mae_metric = MAEMetric()
mse_metric = MSEMetric()

# 加载模型
checkpoint_dir = '/home/data/liutuo/code/checkpoint/mri2pet _two trace_add clip_flow'
checkpoint = torch.load(f'{checkpoint_dir}/first_part_311.pth')

model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])
epoch = checkpoint['epoch']

# 评估模式
model.eval()

# 初始化验证集的总损失和指标
val_epoch_loss = 0
val_ssim_fdg = 0
val_ssim_av45 = 0
val_psnr_fdg = 0
val_psnr_av45 = 0
val_mae_fdg = 0
val_mae_av45 = 0
val_mse_fdg = 0
val_mse_av45 = 0

# 遍历验证集
for step, data_val in enumerate(val_loader):
    images = data_val["mri"].to(device)
    seg_fdg = data_val["fdg"].to(device)  # ground truth segmentation
    seg_av45 = data_val["av45"].to(device)
    fdg_index = data_val["fdg_index"].to(device)
    av45_index = data_val["av45_index"].to(device)
    t=0
    x_t = images
    N_sample =1
    N_sample_tensor = torch.tensor(N_sample, dtype=torch.float32)
    # progress_bar = tqdm([(i / (N_sample)) for i in range(N_sample)])
    progress_bar = [(i / (N_sample)) for i in range(N_sample)]
    for t in progress_bar:  # go through the noising process
        with autocast(device_type='cuda',enabled=True):
            with torch.no_grad():
                time_embedding = int(t * 1000)
                # print(t)
                # print(time_embedding)
                v_fdg_output = model(x = x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device),context=fdg_index)
                x_fdg_t = x_t + (v_fdg_output / N_sample_tensor)
                x_fdg_t = torch.clamp(x_fdg_t, min=clip_sample_min, max=clip_sample_max)
                
                v_av45_output = model(x = x_t, timesteps=torch.Tensor((time_embedding,)).to(x_t.device),context=av45_index)
                x_av45_t = x_t + (v_av45_output / N_sample_tensor)
                x_av45_t = torch.clamp(x_av45_t, min=clip_sample_min, max=clip_sample_max)

current_fdg_img =  x_fdg_t.to('cpu')
current_av45_img =  x_av45_t.to('cpu')
labels_fdg = seg_fdg.to('cpu')
labels_av45 = seg_av45.to('cpu')

compare_3d([images,labels_fdg, current_fdg_img,labels_av45, current_av45_img])
compare_3d_jet([current_fdg_img - labels_fdg,current_av45_img - labels_av45])
