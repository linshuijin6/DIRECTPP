# Derived source excerpt; historical notebook was not executed.
# Original: 3003:/home/data/liutuo/code/chu li shu ju.ipynb
# Original file SHA-256: f74728f83e3a1a9554f84c8080371652430bf868fa5322a052c8af250911a97b
# Notebook cell (zero-based): 6
# Source SHA-256: ac88e30391a3a348a0a7d172b274f1acf40ed0908737d25607404dde5258ddc6

import pandas as pd

# 定义生成描述的函数
def generate_description(row):
    # 提取需要的字段
    subject_id = row['Subject ID']
    sex = "male" if row['Sex'] == 'M' else "female"
    weight = row['Weight']
    age = row['Age']
    mmse_score = row['MMSE Total Score']
    gds_score = row['GDSCALE Total Score']
    global_cdr = row['Global CDR']
    faq_score = row['FAQ Total Score']
    npi_q_score = row['NPI-Q Total Score']
    
    # 构建描述字符串
    description = (
        f"Subject is a {age:.0f}-year-old {sex} with a weight of {weight:.1f} kg. "
        f"The global Clinical Dementia Rating (CDR) score, which assesses dementia severity (0: no dementia to 3: severe dementia), is {global_cdr:.1f}. "
        f"The Mini-Mental State Examination (MMSE) score, assessing cognitive function (0: severe impairment to 30: normal), is {mmse_score:.0f}. "
        f"The Geriatric Depression Scale (GDS) score, screening depression (0: no depression to 15: severe depression), is {gds_score:.0f}. "
        f"The Functional Activities Questionnaire (FAQ) score, assessing daily activity impairment (0: no impairment to 30: severe impairment), is {faq_score:.0f}. "
        f"The Neuropsychiatric Inventory Questionnaire (NPI-Q) Total Score, assessing neuropsychiatric symptom burden (0: no symptoms to higher scores indicating greater burden), is {npi_q_score:.0f}."
    )
    return description

# 主函数
if __name__ == "__main__":
    # 指定文件路径
    input_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    output_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_with_description.csv"
    
    # 加载 CSV 文件
    df = pd.read_csv(input_file)
    
    # 确保所需列存在
    required_columns = [
        'Subject ID', 'Sex', 'Weight', 'Age',
        'MMSE Total Score', 'GDSCALE Total Score',
        'Global CDR', 'FAQ Total Score', 'NPI-Q Total Score'
    ]
    if not all(col in df.columns for col in required_columns):
        raise ValueError(f"CSV 文件缺少必要列: {required_columns}")
    
    # 生成 Description 列
    df['Description'] = df.apply(generate_description, axis=1)
    
    # 保存更新后的数据到新文件
    df.to_csv(output_file, index=False)
    print(f"已保存更新后的数据到 {output_file}")