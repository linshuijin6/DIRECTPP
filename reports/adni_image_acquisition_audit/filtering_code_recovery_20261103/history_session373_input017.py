# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 17.
# Source SHA-256: c4b9310f536222eecb0e8be2a6b2621454fb2fa72127d8f8fca31cb23c46ce75

import os
import pandas as pd

# 步骤 1: 提取目录中的文件名并去掉后缀
def extract_file_names(directory):
    file_names = []
    for file in os.listdir(directory):
        if file.endswith("_MRI.nii.gz"):
            # 去掉后缀 "_MRI.nii.gz"
            file_name = file.replace("_MRI.nii.gz", "")
            file_names.append(file_name)
    return file_names

# 步骤 2: 匹配 CSV 文件中的 Subject ID 并去重
def filter_subject_ids(csv_file, file_names):
    # 读取 CSV 文件
    df = pd.read_csv(csv_file)
    
    # 确保 CSV 文件中有 'Subject ID' 列
    if 'Subject ID' not in df.columns:
        raise ValueError("CSV 文件中缺少 'Subject ID' 列")
    
    # 创建一个字典来存储唯一的 Subject ID
    unique_subjects = {}
    
    # 遍历文件名列表
    for file_name in file_names:
        # 在 CSV 中查找匹配的行
        matched_rows = df[df['Subject ID'].astype(str) == file_name]
        if not matched_rows.empty:
            # 只保留第一个匹配的记录
            unique_subjects[file_name] = matched_rows.iloc[0]['Subject ID']
    
    # 返回结果
    return list(unique_subjects.values())

# 主函数
if __name__ == "__main__":
    # 指定目录和 CSV 文件路径
    directory = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/mri_strip"
    csv_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/ADNI MRI and FDG and AV45 csv.csv"  # 替换为实际 CSV 文件路径
    
    # 提取文件名
    file_names = extract_file_names(directory)
    print(f"提取到 {len(file_names)} 个文件名")
    
    # 过滤 Subject ID
    subject_ids = filter_subject_ids(csv_file, file_names)
    print(f"匹配到 {len(subject_ids)} 个唯一 Subject ID")
    
    # 输出结果
    print(subject_ids)