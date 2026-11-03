# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 27.
# Source SHA-256: f88234b1ae460333cdb1fc4097bd351a078538447cf9bee4caa078d62b682ccd

import pandas as pd

# 定义生成描述的函数
def generate_description(row):
    # 提取所需字段
    age = row.get('Age', 'N/A')
    sex = row.get('Sex', 'N/A')
    weight = row.get('Weight ', 'N/A')
    cdr_global = row.get('Global CDR', 'N/A')
    mmse = row.get('MMSE Total Score', 'N/A')
    gds = row.get('GDSCALE Total Score', 'N/A')
    faq = row.get('FAQ Total Score', 'N/A')
    npi_q = row.get('NPI-Q Total Score', 'N/A')
    
    # 构建描述文本
    description = (
        f"Subject is a {age}-year-old {sex.lower()} with a weight of {weight} kg. "
        f"The global Clinical Dementia Rating (CDR) score, which assesses dementia severity "
        f"(0: no dementia to 3: severe dementia), is {cdr_global}. "
        f"The Mini-Mental State Examination (MMSE) score, assessing cognitive function "
        f"(0: severe impairment to 30: normal), is {mmse}. "
        f"The Geriatric Depression Scale (GDS) score, screening depression "
        f"(0: no depression to 15: severe depression), is {gds}. "
        f"The Functional Activities Questionnaire (FAQ) score, assessing daily activity impairment "
        f"(0: no impairment to 30: severe impairment), is {faq}. "
        f"The Neuropsychiatric Inventory Questionnaire (NPI-Q) Total Score, assessing neuropsychiatric symptom burden "
        f"(0: no symptoms to higher scores indicating greater burden), is {npi_q}."
    )
    return description

# 主函数
if __name__ == "__main__":
    # 指定文件路径
    input_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_filled.csv"
    output_file = "/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/filtered_subjects_with_description.csv"
    
    # 加载 CSV 文件
    df = pd.read_csv(input_file)
    
    # 确保必要列存在
    required_columns = [
        'Age', 'Sex', 'Weight (kg)', 'CDR Global Score', 
        'MMSE Total Score', 'GDS Total Score', 'FAQ Total Score', 'NPI-Q Total Score'
    ]
    if not all(col in df.columns for col in required_columns):
        missing_cols = [col for col in required_columns if col not in df.columns]
        raise ValueError(f"CSV 文件缺少以下必要列: {missing_cols}")
    
    # 生成 Description 列
    df['Description'] = df.apply(generate_description, axis=1)
    
    # 保存更新后的数据到新文件
    df.to_csv(output_file, index=False)
    print(f"已保存更新后的数据到 {output_file}")