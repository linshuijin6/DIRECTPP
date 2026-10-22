# Original DB: /home/ssddata/liutuo/.ipython/profile_default/history.sqlite
# session=8; line=3; session_start_as_stored=2025-04-08 16:17:47.339829; source_sha256=73875217755193cd341bdf4929c2b3537beab52dbe5b0b5a92f775875efd0f0c
import os
import pandas as pd
from sklearn.model_selection import train_test_split
import json

# 数据目录（保持不变）
base_dir = "/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45"
mri_dir = "/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45/mri_strip_registered"
av45_dir = "/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45/PET1_AV45_strip_registered"
fdg_dir = "/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45/PET2_FDG_strip_registered"
csv_path = os.path.join(base_dir, "filtered_subjects_with_description.csv")

# JSON 文件保存路径（保持不变）
train_json_path = "/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45/train_data_with_description.json"
val_json_path = "/home/ssddata/liutuo/liutuo_data/ADNI1234_mri_fdg_av45/val_data_with_description.json"

# 加载 CSV 文件（保持不变）
csv_data = pd.read_csv(csv_path)
csv_dict = csv_data.set_index("Subject ID")["Description"].to_dict()

# 获取文件列表（保持不变）
mri_files = sorted(os.listdir(mri_dir))
av45_files = sorted(os.listdir(av45_dir))
fdg_files = sorted(os.listdir(fdg_dir))

def get_subject_id(filename):
    """从文件名中提取统一的 subject ID（前三个部分，如 '002_S_0295'）"""
    parts = filename.split('_')
    return f"{parts[0]}_{parts[1]}_{parts[2]}"

# 使用统一的 get_subject_id 处理所有文件（保持不变）
mri_dict = {get_subject_id(f): os.path.join(mri_dir, f) for f in mri_files}
av45_dict = {get_subject_id(f): os.path.join(av45_dir, f) for f in av45_files}
fdg_dict = {get_subject_id(f): os.path.join(fdg_dir, f) for f in fdg_files}

# 修改后的匹配逻辑：MRI必须存在，AV45或FDG至少存在一个
paired_data = []
for patient_id, mri_file in mri_dict.items():
    has_av45 = patient_id in av45_dict
    has_fdg = patient_id in fdg_dict
    
    # 检查是否至少有一个 PET 数据（AV45 或 FDG）
    if has_av45 or has_fdg:
        description = csv_dict.get(patient_id, None)
        
        # 构建数据条目（AV45 和 FDG 可能为 None）
        paired_data.append({
            "name": patient_id,
            "mri": mri_file,
            "av45": av45_dict[patient_id] if has_av45 else None,
            "fdg": fdg_dict[patient_id] if has_fdg else None,
            "description": description,
            "av45_index": len(paired_data) if has_av45 else None,  # 仅当存在 AV45 时记录索引
            "fdg_index": len(paired_data) if has_fdg else None   # 仅当存在 FDG 时记录索引
        })

# 新增代码：确保 fdg_index 和 av45_index 是整数或 None
for data in paired_data:
    data["fdg_index"] = int(data["fdg_index"]) if data["fdg_index"] is not None else None
    data["av45_index"] = int(data["av45_index"]) if data["av45_index"] is not None else None

# 打印调试信息
print(f"First few entries of paired_data:")
for i in range(min(5, len(paired_data))):  # 打印前 5 条数据
    print(paired_data[i])

# 划分训练集和验证集
train_data, val_data = train_test_split(paired_data, test_size=1, random_state=42)

print(f"Training set size: {len(train_data)}")
print(f"Validation set size: {len(val_data)}")



import torch
from transformers import AutoTokenizer, AutoModel

# 示例：假设已经加载 BiomedCLIP 模型和处理器
# 这里替换为您实际使用的 BiomedCLIP 模型和 tokenizer
local_model_path = "/home/ssddata/liutuo/BiomedCLIP"
processor = AutoProcessor.from_pretrained(local_model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(local_model_path, trust_remote_code=True)

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
model.to(device)
model.eval()


# 假设 paired_data 已经加载
modal_information = [data["description"] for data in paired_data if data["description"] is not None]

# 对描述信息进行 Tokenizer 编码
text_inputs = processor(
    modal_information,
    padding=True,
    truncation=True,
    return_tensors="pt",
    max_length=256 # 根据模型输入限制选择合适的 max_length
).to(device)

# 转化为 BiomedCLIP 嵌入
with torch.no_grad():
    desc_text_features = model.get_text_features(text_inputs['input_ids'])  # 使用模型方法提取嵌入
    print(f"Shape of features: {desc_text_features.shape}, Dtype: {desc_text_features.dtype}")

# 划分训练集和验证集
train_data, val_data = train_test_split(paired_data, test_size=1, random_state=42)

print(f"Training set size: {len(train_data)}")
print(f"Validation set size: {len(val_data)}")

# 保存到 JSON 文件
with open(train_json_path, "w") as f:
    json.dump(train_data, f, indent=4)

with open(val_json_path, "w") as f:
    json.dump(val_data, f, indent=4)

print(f"Saved train data to: {train_json_path}")
print(f"Saved validation data to: {val_json_path}")