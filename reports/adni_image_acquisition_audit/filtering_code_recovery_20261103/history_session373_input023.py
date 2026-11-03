# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 23.
# Source SHA-256: ef3b756fd5397a3f934daf4634c6d7d44517b1b3a671b18dcebcf7de7aa64902

import pandas as pd

# 定义填充规则
def fill_gdscale(row):
    if pd.isna(row['GDSCALE Total Score']):  # 检查是否为空
        research_group = row['Research Group']
        if research_group == 'CN':
            return 0
        elif research_group == 'EMCI':
            return 1
        elif research_group == 'MCI':
            return 2
        elif research_group == 'LMCI':
            return 3
        elif research_group == 'AD':
            return 5
        else:
            return None  # 如果 Research Group 不在上述类别中，保持为空
    else:
        return row['GDSCALE Total Score']  # 如果不为空，保持原值

# 主函数
if __name__ == "__main__":
    # 指定文件路径
    input_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    output_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"

    # 加载 CSV 文件
    df = pd.read_csv(input_file)

    # 确保列名正确
    required_columns = ['GDSCALE Total Score', 'Research Group']
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"CSV 文件缺少必要的列: {required_columns}")

    # 填充 GDSCALE Total Score 列
    df['GDSCALE Total Score'] = df.apply(fill_gdscale, axis=1)

    # 保存更新后的数据到新文件
    df.to_csv(output_file, index=False)
    print(f"已填充空缺值并保存到 {output_file}")