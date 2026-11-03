# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 18.
# Source SHA-256: 8bf575b976d924e099d6962df32a343af548db70954b0c21686fbb5ff7c2110a

import pandas as pd

# 步骤 1: 加载原始 CSV 文件
def load_csv(csv_file):
    return pd.read_csv(csv_file)

# 步骤 2: 筛选包含指定 Subject ID 的行
def filter_csv_by_subject_ids(df, subject_ids):
    # 确保 Subject ID 列存在
    if 'Subject ID' not in df.columns:
        raise ValueError("CSV 文件中缺少 'Subject ID' 列")
    
    # 筛选出包含指定 Subject ID 的行
    filtered_df = df[df['Subject ID'].isin(subject_ids)]
    return filtered_df

# 步骤 3: 保存为新的 CSV 文件
def save_filtered_csv(filtered_df, output_file):
    filtered_df.to_csv(output_file, index=False)
    print(f"已保存新的 CSV 文件到 {output_file}")

# 主函数
if __name__ == "__main__":
    # 指定原始 CSV 文件路径和输出文件路径
    csv_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/ADNI MRI and FDG and AV45 csv.csv"  # 替换为实际 CSV 文件路径
    output_file = "filtered_ADNI_data.csv"  # 输出文件名
    
    # 提取的 1857 个 Subject ID（假设已经提取并存储在列表中）
    subject_ids = [...]  # 将你的 1857 个 Subject ID 列表放在这里

    # 加载原始 CSV 文件
    df = load_csv(csv_file)
    
    # 筛选包含指定 Subject ID 的行
    filtered_df = filter_csv_by_subject_ids(df, subject_ids)
    
    # 保存为新的 CSV 文件
    save_filtered_csv(filtered_df, output_file)