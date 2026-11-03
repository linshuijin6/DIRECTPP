# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 21.
# Source SHA-256: ba6d128d3cc39965d961e30210e8903ff6367ba529d7be9748bb07e97c132f9a

import pandas as pd

# 主函数
def fill_missing_mmse(filtered_csv, original_csv, output_csv):
    # 加载 filtered_subjects.csv 文件
    filtered_df = pd.read_csv(filtered_csv)
    
    # 加载原始 CSV 文件
    original_df = pd.read_csv(original_csv)
    
    # 确保两份文件中都有 'Subject ID' 和 'MMSE Total Score' 列
    if 'Subject ID' not in filtered_df.columns or 'MMSE Total Score' not in filtered_df.columns:
        raise ValueError("filtered_subjects.csv 缺少 'Subject ID' 或 'MMSE Total Score' 列")
    if 'Subject ID' not in original_df.columns or 'MMSE Total Score' not in original_df.columns:
        raise ValueError("ADNI MRI and FDG and AV45 csv.csv 缺少 'Subject ID' 或 'MMSE Total Score' 列")
    
    # 找到 filtered_subjects.csv 中 MMSE Total Score 为空的记录
    missing_mmse_ids = filtered_df[filtered_df['MMSE Total Score'].isnull()]['Subject ID']
    print(f"找到 {len(missing_mmse_ids)} 个 MMSE Total Score 缺失的 Subject ID")
    
    # 遍历缺失的 Subject ID，在原始 CSV 中查找对应的 MMSE Total Score
    filled_count = 0
    for subject_id in missing_mmse_ids:
        # 在原始 CSV 中查找该 Subject ID 的 MMSE Total Score
        match = original_df[original_df['Subject ID'] == subject_id]
        if not match.empty and not pd.isnull(match.iloc[0]['MMSE Total Score']):
            # 如果找到有效值，则填充到 filtered_subjects.csv 中
            mmse_score = match.iloc[0]['MMSE Total Score']
            filtered_df.loc[filtered_df['Subject ID'] == subject_id, 'MMSE Total Score'] = mmse_score
            filled_count += 1
    
    print(f"成功填充了 {filled_count} 个 MMSE Total Score 值")
    
    # 保存更新后的 filtered_subjects.csv 文件
    filtered_df.to_csv(output_csv, index=False)
    print(f"已保存更新后的文件到 {output_csv}")

# 主程序入口
if __name__ == "__main__":
    # 指定文件路径
    filtered_csv = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects.csv"
    original_csv = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/ADNI MRI and FDG and AV45 csv.csv"
    output_csv = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    
    # 调用函数填充缺失值
    fill_missing_mmse(filtered_csv, original_csv, output_csv)