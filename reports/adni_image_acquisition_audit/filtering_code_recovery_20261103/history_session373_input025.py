# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 25.
# Source SHA-256: 97c4bf5b7b14470cde93ba8904b9af37e78506ad02809b6a6f8b526ba77403d4

import pandas as pd
import numpy as np
import random

# 定义填充函数
def fill_faq_score(row):
    if pd.isna(row['FAQ Total Score']):
        research_group = row['Research Group']
        if research_group == 'CN':
            return random.choice([0, 1])  # CN 填 0 或 1
        elif research_group == 'EMCI':
            return random.randint(3, 5)  # EMCI 随机填 3, 4, 5
        elif research_group == 'MCI':
            return random.randint(4, 7)  # MCI 填 4 到 7 之间的随机整数
        elif research_group == 'LMCI':
            return random.randint(7, 11)  # LMCI 填 7 到 11 之间的随机整数
        elif research_group == 'AD':
            return random.randint(17, 24)  # AD 填 17 到 24 之间的随机整数
    return row['FAQ Total Score']  # 如果不是空值，保持原值

# 主函数
if __name__ == "__main__":
    # 指定文件路径
    input_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    output_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    
    # 加载 CSV 文件
    df = pd.read_csv(input_file)
    
    # 确保列名正确
    required_columns = ['FAQ Total Score', 'Research Group']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"CSV 文件中缺少以下列: {required_columns}")
    
    # 填充 FAQ Total Score 列
    df['FAQ Total Score'] = df.apply(fill_faq_score, axis=1)
    
    # 保存结果到新文件
    df.to_csv(output_file, index=False)
    print(f"已保存填充后的数据到 {output_file}")