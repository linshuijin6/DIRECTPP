# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb
# original_sha256=6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a; zero_based_cell=3
import os
import pandas as pd
import torch
from transformers import AutoProcessor, AutoModel
import scipy.io as sio

# 读取CSV文件并创建Subject到Description和Group的映射
label_path1 = "/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/ADNI1_imdb_with_meta_description.csv"
label_path2 = "/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/ADNI2_imdb_with_meta_description.csv"

label1 = pd.read_csv(label_path1)
label2 = pd.read_csv(label_path2)

label1_dict = dict(zip(label1["Subject"], label1["Group"]))
label2_dict = dict(zip(label2["Subject"], label2["Group"]))

label1_desc_dict = dict(zip(label1["Subject"], label1["description"]))
label2_desc_dict = dict(zip(label2["Subject"], label2["description"]))

# 使用本地路径加载处理器和模型
local_model_path = "/home/data/liutuo/code/BiomedCLIP"
processor = AutoProcessor.from_pretrained(local_model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(local_model_path, trust_remote_code=True)

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
model.to(device)
model.eval()

# 定义函数以读取.mat文件
def mat_load(mat_file_dir):
    mat = sio.loadmat(mat_file_dir)
    image = mat["IMG"]
    return image

# 获取路径中的数据列表
def get_data_list_from_path(path):
    data_list = [os.path.join(path, data) for data in os.listdir(path)]
    return data_list

# 获取路径中的数据并创建映射
def get_data_from_path(path, label_dict):
    data_all = []
    for data in os.listdir(path):
        image = os.path.join(path, data)
        name = data[:-4]
        try:
            label = label_dict[name]
        except KeyError:
            continue
        data_all.append({"image": image, "name": name, "label": label})
    return data_all

# 获取配对数据并附加Description
def get_data_from_path_paired_with_description(path, label_dict, label_desc_dict, mri_name_image_dict):
    data_all = []
    for data in os.listdir(path):
        pet = os.path.join(path, data)
        name = data[:-4]
        try:
            mri = mri_name_image_dict[name]
            label = label_dict[name]
            description = label_desc_dict[name]
        except KeyError:
            continue
        data_all.append({
            "pet": pet,
            "mri": mri,
            "name": name,
            "label": label,
            "description": description,
        })
    return data_all

# 设置路径
mri_path = "/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/MRI"
pet_path = "/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/PET"

# 获取MRI数据并创建映射
data_all = get_data_from_path(mri_path, label1_dict)
data_all_adni2 = get_data_from_path(mri_path, label2_dict)

mri_name_image_dict = dict(zip([data["name"] for data in data_all],
                               [data["image"] for data in data_all]))
mri_name_image_dict_adni2 = dict(zip([data["name"] for data in data_all_adni2],
                                     [data["image"] for data in data_all_adni2]))

# 获取配对数据并附加Description
paired_all_with_desc1 = get_data_from_path_paired_with_description(pet_path, label1_dict, label1_desc_dict, mri_name_image_dict)
paired_all_with_desc2 = get_data_from_path_paired_with_description(pet_path, label2_dict, label2_desc_dict, mri_name_image_dict_adni2)

# 合并两个数据集
paired_all_with_desc = paired_all_with_desc1 + paired_all_with_desc2

# 将Description转化为BiomedCLIP嵌入
modal_information = [data["description"] for data in paired_all_with_desc]
text_inputs = processor.tokenizer(modal_information, padding=True, truncation=True, return_tensors="pt", max_length=256).to(device)

with torch.no_grad():
    desc_text_features = model.get_text_features(text_inputs['input_ids'])  # 使用实际的特征提取方法
    print(desc_text_features.shape, desc_text_features.dtype)
