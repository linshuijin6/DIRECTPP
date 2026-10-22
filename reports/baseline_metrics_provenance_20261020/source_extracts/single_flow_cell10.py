# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb
# original_sha256=6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a; zero_based_cell=10
def mri_index_transform(x):
    return torch.cat([desc_text_features[x].unsqueeze(0), c_mri], dim=0)

def pet_index_transform(x):
    return torch.cat([desc_text_features[x].unsqueeze(0), c_pet], dim=0)

from monai.data import CacheDataset, DataLoader
from monai.data import CacheNTransDataset
import monai.data as md
from monai.data import CacheDataset, DataLoader
from monai.data import CacheNTransDataset
import monai.data as md
train_transforms=mt.Compose([
    mt.Lambdad(keys=["pet","mri"],func=mat_load),
    mt.EnsureChannelFirstd(keys=["pet","mri"],channel_dim='no_channel'),
    mt.Orientationd(keys=["pet","mri"],axcodes="LPI"),
    mt.CropForegroundd(keys=["pet","mri"],source_key="mri"),
    #mt.NormalizeIntensityd(keys=["pet","mri"]),
    mt.HistogramNormalized(keys=["pet","mri"]),
    mt.ResizeWithPadOrCropd(keys=["pet","mri"],spatial_size=(160,192,160)),
    mt.Spacingd(keys=["pet","mri"],pixdim=(1.0,1.0,1.0), mode=("bilinear")),
    mt.NormalizeIntensityd(keys=["pet","mri"]),
    mt.ScaleIntensityd(keys=["pet","mri"],minv=0,maxv=1),
    mt.Lambdad(keys=["mri_index"], func=mri_index_transform),
    mt.Lambdad(keys=["pet_index"], func=pet_index_transform),
#     mt.Lambdad(keys=["pet_index"],func=lambda x:paired_all_with_desc[x]),
])
val_transforms=mt.Compose([
    mt.Lambdad(keys=["pet","mri"],func=mat_load),
    mt.EnsureChannelFirstd(keys=["pet","mri"],channel_dim='no_channel'),
    mt.Orientationd(keys=["pet","mri"],axcodes="LPI"),
    mt.CropForegroundd(keys=["pet","mri"],source_key="mri"),
    mt.HistogramNormalized(keys=["pet","mri"]),
    mt.ResizeWithPadOrCropd(keys=["pet","mri"],spatial_size=(160,192,160)),
    mt.Spacingd(keys=["pet","mri"],pixdim=(1.0,1.0,1.0), mode=("bilinear")),
    mt.NormalizeIntensityd(keys=["pet","mri"]),
    mt.ScaleIntensityd(keys=["pet","mri"],minv=0,maxv=1),
    mt.Lambdad(keys=["mri_index"], func=mri_index_transform),
    mt.Lambdad(keys=["pet_index"], func=pet_index_transform),

])


train_ds = CacheDataset(data=train_data, transform=train_transforms,num_workers=20)
train_loader = DataLoader(train_ds, batch_size=1, shuffle=True, num_workers=0)    

val_ds = CacheDataset(data=val_data, transform=val_transforms,num_workers=20)
val_loader = DataLoader(val_ds,  batch_size=1,shuffle=False, num_workers=0)