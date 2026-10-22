# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet cfg counter fact.ipynb
# original_sha256=0b443a3348c735cebca17b5a1c4b5aa70de04a0551f05c3a246f28aa0b68bb36; zero_based_cell=27
import torch
import numpy as np
from generative.metrics import SSIMMetric
from monai.metrics import PSNRMetric
from tqdm import tqdm

device = torch.device("cuda")
embedding_dimension = 64
model = DiffusionModelUNet(
    spatial_dims=3,
    in_channels=1,
    out_channels=1,
    num_channels=(64, 64, 128),
    attention_levels=(False, True, True),
    num_res_blocks=1,
    num_head_channels=(0, 64, 128),
    with_conditioning=True,
    cross_attention_dim=embedding_dimension,
    use_flash_attention=True,
).to(device)
embed = torch.nn.Embedding(num_embeddings=3, embedding_dim=embedding_dimension, padding_idx=0).to(device)


scheduler = DDIMScheduler(prediction_type='v_prediction',num_train_timesteps=1000,
                           schedule="scaled_linear_beta",beta_start=0.0005, beta_end=0.0195)
scheduler.set_timesteps(num_inference_steps=1000)
inferer = DiffusionInferer(scheduler)
optimizer = torch.optim.Adam(params=list(model.parameters()) + list(embed.parameters()), lr=2.5e-5)


checkpoint_path = '/home/ssd/liutuo/checkpoint/mri2pet cfg counter fact/mri2pet cfg counter fact_150.pth'
checkpoint = torch.load(checkpoint_path, map_location=device)
model.load_state_dict(checkpoint['model'])
optimizer.load_state_dict(checkpoint['optimizer'])

model.eval()