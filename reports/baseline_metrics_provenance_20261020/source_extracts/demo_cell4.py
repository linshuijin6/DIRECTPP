# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_reflow_test or fanhua.ipynb
# original_sha256=d09273e006ccafe9bfe267192192c5b48cd10c34b8da2e22a1c5c37ad3eebcf2; zero_based_cell=4
from monai.transforms import Compose, LoadImaged, Lambdad, EnsureChannelFirstd, Orientationd, CropForegroundd, \
    HistogramNormalized, ResizeWithPadOrCropd, Spacingd, NormalizeIntensityd, ScaleIntensityd
from monai.data import CacheDataset, DataLoader
import nibabel as nib
import numpy as np
import json

import monai.transforms as mt

# 定义 transform 函数
def fdg_index_transform(x):
    return torch.cat([desc_text_features[x].unsqueeze(0), fdg_feature_optimized], dim=0)

def av45_index_transform(x):
    return torch.cat([desc_text_features[x].unsqueeze(0), av45_feature_optimized], dim=0)


# 自定义加载函数
def mat_load(filepath):
    """
    使用 nibabel 加载 NIfTI 文件，并转换为 NumPy 数组。
    """
    return nib.load(filepath).get_fdata()

# 加载 JSON 文件
train_json_path = "/home/ssddata/liutuo/liutuo_data/test1/train_data_with_description.json"
val_json_path = "/home/ssddata/liutuo/liutuo_data/test1/val_data_with_description.json"

# 加载 JSON 文件
with open(train_json_path, "r") as f:
    train_data = json.load(f)

with open(val_json_path, "r") as f:
    val_data = json.load(f)

# 转换数据格式
train_data = [
    {
        "name": item["name"],
        "mri": item["mri"],
        "av45": item["av45"],
        "fdg": item["fdg"],
        "description": item.get("description", {}),  # 确保 description 存在
        "fdg_index": item.get("fdg_index"),  # 保留 fdg_index
        "av45_index": item.get("av45_index"),  # 保留 av45_index
    }
    for item in train_data
]

val_data = [
    {
        "name": item["name"],
        "mri": item["mri"],
        "av45": item["av45"],
        "fdg": item["fdg"],
        "description": item.get("description", {}),  # 确保 description 存在
        "fdg_index": item.get("fdg_index"),  # 保留 fdg_index
        "av45_index": item.get("av45_index"),  # 保留 av45_index
    }
    for item in val_data
]



# 构建数据增强 pipeline
# 定义训练集数据增强流程
train_transforms = mt.Compose([
    mt.Lambdad(keys=["mri", "fdg","av45"], func=mat_load),  # 加载 NIfTI 文件
    mt.EnsureChannelFirstd(keys=["mri", "fdg","av45"],channel_dim='no_channel'),
    mt.Orientationd(keys=["mri", "fdg","av45"], axcodes="LPI"),
    mt.CropForegroundd(keys=["mri", "fdg","av45"], source_key="mri"),
    mt.HistogramNormalized(keys=["mri"]),
    mt.ResizeWithPadOrCropd(keys=["mri", "fdg","av45"], spatial_size=[160, 192, 160]),
    mt.Spacingd(keys=["mri", "fdg","av45"], pixdim=(1.0, 1.0, 1.0)),
    mt.NormalizeIntensityd(keys=["mri", "fdg","av45"]),
    mt.ScaleIntensityd(keys=["mri", "fdg","av45"]),
    mt.Lambdad(keys=["fdg_index"], func=fdg_index_transform),  # 添加 fdg_index 转换
    mt.Lambdad(keys=["av45_index"], func=av45_index_transform),  # 添加 av45_index 转换
])

# 定义验证集数据增强流程（通常与训练集一致，但不含随机性增强）
val_transforms = mt.Compose([
    mt.Lambdad(keys=["mri", "fdg","av45"], func=mat_load),  # 加载 NIfTI 文件
    mt.EnsureChannelFirstd(keys=["mri", "fdg","av45"],channel_dim='no_channel'),
    mt.Orientationd(keys=["mri", "fdg","av45"], axcodes="LPI"),
    mt.CropForegroundd(keys=["mri", "fdg","av45"], source_key="mri"),
    mt.HistogramNormalized(keys=["mri"]),
    mt.ResizeWithPadOrCropd(keys=["mri", "fdg","av45"], spatial_size=[160, 192, 160]),
    mt.Spacingd(keys=["mri", "fdg","av45"], pixdim=(1.0, 1.0, 1.0)),
    mt.NormalizeIntensityd(keys=["mri", "fdg","av45"]),
    mt.ScaleIntensityd(keys=["mri", "fdg","av45"]),
    mt.Lambdad(keys=["fdg_index"], func=fdg_index_transform),  # 添加 fdg_index 转换
    mt.Lambdad(keys=["av45_index"], func=av45_index_transform),  # 添加 av45_index 转换
])


# 构建 CacheDataset
train_ds = CacheDataset(data=train_data, transform=train_transforms, num_workers=0, )
train_loader = DataLoader(train_ds, batch_size=1, shuffle=True, num_workers=0)    #shuffle=True

val_ds = CacheDataset(data=val_data, transform=val_transforms, num_workers=0, )
val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, num_workers=0)

# 测试 DataLoader
for batch_data in train_loader:
    print("MRI shape:", batch_data["mri"].shape)
    print("AV45 shape:", batch_data["av45"].shape)
    print("FDG shape:", batch_data["fdg"].shape)
    print("description:", train_data[0]["description"])  # 从原始数据访问描述信息
    break