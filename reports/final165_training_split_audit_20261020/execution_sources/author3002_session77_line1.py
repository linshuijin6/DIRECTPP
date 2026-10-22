# Original DB=/home/ssddata/liutuo/.ipython/profile_default/history.sqlite
# session=77; line=1; session_start_as_stored=2025-04-23 08:55:00.460977
# source_sha256=d88c1c010dffdfb8918804ae57d6f36d08c9259500efac5d0fc60fa079098c0b
import torch
import os
import monai.transforms as mt
import monai.data as md
import scipy.io as sio
import numpy as np
from liutuo_utils import compare_3d_jet,compare_3d,donkey_noise_like
import matplotlib.pyplot as plt
import pandas as pd


device_id =3
# 设置 PyTorch 的默认 CUDA 设备
torch.cuda.set_device(device_id)

# 确认当前默认 CUDA 设备
current_device = torch.cuda.current_device()
print(f"Switched to CUDA device: {current_device}")