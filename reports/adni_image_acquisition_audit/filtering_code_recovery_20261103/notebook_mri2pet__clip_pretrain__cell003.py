# Derived source excerpt; historical notebook was not executed.
# Original: 3003:/home/data/liutuo/code/mri2pet _clip_pretrain .ipynb
# Original file SHA-256: a63b643b453712b031750a230cb4c85366b37487a881bf3f4360fc7c49d0295e
# Notebook cell (zero-based): 3
# Source SHA-256: ad04ba05df8a1e7d2bd2830c5f966838d9627de75d7573d763a9920b136459bc

import os
import pandas as pd
import json
from transformers import AutoProcessor, AutoModel
import torch

# 数据目录
base_dir = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45"
mri_dir = os.path.join(base_dir, "mri_strip_registered")
av45_dir = os.path.join(base_dir, "PET1_AV45_strip_registered")
fdg_dir = os.path.join(base_dir, "PET2_FDG_strip_registered")
csv_path = os.path.join(base_dir, "filtered_subjects_with_description.csv")

# JSON 文件保存路径
train_json_path = os.path.join(base_dir, "train_data_with_description.json")
val_json_path = os.path.join(base_dir, "val_data_with_description.json")

# 加载 CSV 文件
csv_data = pd.read_csv(csv_path)
csv_dict = csv_data.set_index("Subject ID")["Description"].to_dict()

# 获取文件列表
mri_files = sorted(os.listdir(mri_dir))
av45_files = sorted(os.listdir(av45_dir))
fdg_files = sorted(os.listdir(fdg_dir))

def get_subject_id(filename):
    """从文件名中提取统一的 subject ID"""
    parts = filename.split('_')
    return f"{parts[0]}_{parts[1]}_{parts[2]}"

# 构建文件路径字典
mri_dict = {get_subject_id(f): os.path.join(mri_dir, f) for f in mri_files}
av45_dict = {get_subject_id(f): os.path.join(av45_dir, f) for f in av45_files}
fdg_dict = {get_subject_id(f): os.path.join(fdg_dir, f) for f in fdg_files}

# 匹配文件并加入描述信息
paired_data = []
for patient_id, mri_file in mri_dict.items():
    if patient_id in av45_dict and patient_id in fdg_dict:
        description = csv_dict.get(patient_id, None)
        paired_data.append({
            "name": patient_id,
            "mri": os.path.join(mri_dir, mri_file),
            "av45": os.path.join(av45_dir, av45_dict[patient_id]),
            "fdg": os.path.join(fdg_dir, fdg_dict[patient_id]),
            "description": description,
            "fdg_index": len(paired_data),  # 直接添加索引
            "av45_index": len(paired_data)
        })

print(f"Total matched pairs with description: {len(paired_data)}")

# 加载BiomedCLIP模型
local_model_path = "/home/data/liutuo/code/BiomedCLIP"
processor = AutoProcessor.from_pretrained(local_model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(local_model_path, trust_remote_code=True)
device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
model.to(device)
model.eval()

# 处理描述信息
modal_information = [data["description"] for data in paired_data if data["description"] is not None]
text_inputs = processor(
    modal_information,
    padding=True,
    truncation=True,
    return_tensors="pt",
    max_length=256
).to(device)

with torch.no_grad():
    desc_text_features = model.get_text_features(text_inputs['input_ids'])
    print(f"Shape of features: {desc_text_features.shape}, Dtype: {desc_text_features.dtype}")

# 全部数据作为训练集
train_data = paired_data
val_data = []

print(f"Training set size: {len(train_data)}")
print("No validation set used")

# 保存数据
with open(train_json_path, "w") as f:
    json.dump(train_data, f, indent=4)

with open(val_json_path, "w") as f:
    json.dump(val_data, f, indent=4)

print(f"Saved train data to: {train_json_path}")
print(f"Saved empty validation data to: {val_json_path}")