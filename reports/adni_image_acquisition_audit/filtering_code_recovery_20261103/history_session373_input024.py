# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 24.
# Source SHA-256: 4e5a3ec63b0de92559cfabb43b43995594ab4a7176b4fc59710d38a6489a7a49

import pandas as pd
import numpy as np

# 定义填充规则
def fill_global_cdr(row):
    if pd.isna(row['Global CDR']):  # 检查是否为空
        research_group = row['Research Group']
        if research_group == "CN":
            return 0
        elif research_group == "EMCI":
            return np.random.choice([0, 0.5], p=[0.7, 0.3])
        elif research_group == "MCI":
            return np.random.choice([0, 0.5], p=[0.3, 0.7])
        elif research_group == "LMCI":
            return 0.5
        elif research_group == "AD":
            return 1
    return row['Global CDR']  # 如果不为空，保持原值

# 主函数
if __name__ == "__main__":
    # 指定文件路径
    input_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    output_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"

    # 读取 CSV 文件
    df = pd.read_csv(input_file)

    # 确保列名正确
    required_columns = ['Global CDR', 'Research Group']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"CSV 文件中缺少以下列: {required_columns}")

    # 填充 Global CDR 列
    df['Global CDR'] = df.apply(fill_global_cdr, axis=1)

    # 保存到新的 CSV 文件
    df.to_csv(output_file, index=False)
    print(f"已保存填充后的数据到 {output_file}")