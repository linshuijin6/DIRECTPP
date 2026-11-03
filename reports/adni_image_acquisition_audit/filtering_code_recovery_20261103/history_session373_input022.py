# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 22.
# Source SHA-256: fff122c7a0dcfb1d3f7496d001ad70e21d5360f4763704091bb16496ac7286fe

import pandas as pd
import random

# 定义随机填充值的规则
def random_fill_mmse(research_group):
    if research_group == "CN":  # 正常对照组
        return random.choice([30, 29])
    elif research_group == "EMCI":  # 早期轻度认知障碍
        return random.choice([28, 27])
    elif research_group == "MCI":  # 轻度认知障碍
        return random.choice([26, 27])
    elif research_group == "LMCI":  # 晚期轻度认知障碍
        return random.choice([24, 25])
    elif research_group == "AD":  # 阿尔茨海默病
        return random.choice([20, 21, 19])
    else:
        return None  # 如果 Research Group 不属于上述类别，返回 None

# 主函数
if __name__ == "__main__":
    # 指定文件路径
    input_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects.csv"
    output_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"

    # 读取 CSV 文件
    df = pd.read_csv(input_file)

    # 检查是否包含 MMSE Total Score 和 Research Group 列
    if "MMSE Total Score" not in df.columns or "Research Group" not in df.columns:
        raise ValueError("CSV 文件中缺少 'MMSE Total Score' 或 'Research Group' 列")

    # 找到 MMSE Total Score 列为空的行
    missing_mask = df["MMSE Total Score"].isna()

    # 根据 Research Group 的值随机填充
    for idx in df[missing_mask].index:
        research_group = df.loc[idx, "Research Group"]
        df.loc[idx, "MMSE Total Score"] = random_fill_mmse(research_group)

    # 保存更新后的 CSV 文件
    df.to_csv(output_file, index=False)
    print(f"已保存填充后的数据到 {output_file}")