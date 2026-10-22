# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-ddpm ddim.ipynb
# original_sha256=08513920dcb07f4ecfe20f56393afab040fd35cc826b4b3bb55308aff72afbbe; zero_based_cell=29
import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from torch.amp import GradScaler, autocast  # 从 torch.amp 导入 GradScaler

from generative.networks.nets import DistributedDiffusionModelUNet,DiffusionModelUNet
from generative.networks.schedulers import DDPMScheduler,DDIMScheduler
from generative.inferers import DiffusionInferer
model= DiffusionModelUNet(
    # device_ids = [2, 5],
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
scheduler = DDIMScheduler(prediction_type="v_prediction", num_train_timesteps=1000,schedule="scaled_linear_beta",
                          beta_start=0.0005, beta_end=0.0195)
scheduler.set_timesteps(num_inference_steps=20)
optimizer= torch.optim.Adam(params=model.parameters(), lr=2.5e-5)
inferer = DiffusionInferer(scheduler)

# scheduler = DDIMScheduler(prediction_type='v_prediction',num_train_timesteps=1000,
#                            schedule="scaled_linear_beta",beta_start=0.0005, beta_end=0.0195)
# scheduler.set_timesteps(num_inference_steps=50)
# inferer = DiffusionInferer(scheduler)
# optimizer_1 = torch.optim.Adam(params=model_1.parameters(), lr=2.5e-5)