# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb
# original_sha256=6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a; zero_based_cell=6
# 修改后的函数，用于获取配对数据并附加Description和text_mri, text_pet
def get_data_from_path_paired_with_description(path, label_dict, label_desc_dict, mri_name_image_dict):
    data_all = []
    for i, data in enumerate(os.listdir(path)):
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
            "mri_index": i,
            "pet_index": i,
        })
    return data_all

# 使用新的函数生成配对数据
paired_all_with_desc1 = get_data_from_path_paired_with_description(
    pet_path, label1_dict, label1_desc_dict, mri_name_image_dict
)
paired_all_with_desc2 = get_data_from_path_paired_with_description(
    pet_path, label2_dict, label2_desc_dict, mri_name_image_dict_adni2
)

# 合并两个数据集
paired_all_with_desc = paired_all_with_desc1 + paired_all_with_desc2

# # 过滤掉label不是CN或AD的样本
# paired_all_with_desc = [data for data in paired_all_with_desc if data["label"] in ["CN", "AD"]]

# 输出检查
print(paired_all_with_desc[0].keys())  # 检查新的key是否成功加入
print(paired_all_with_desc[0].values()) 
print(len(paired_all_with_desc))
for new_index, data in enumerate(paired_all_with_desc):
    data['index'] = new_index
