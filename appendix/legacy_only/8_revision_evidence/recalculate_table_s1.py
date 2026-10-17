import pandas as pd
import numpy as np
from scipy import stats

df = pd.read_csv('5_data_splits/filtered_subjects_with_description.csv')
groups = ['CN', 'EMCI', 'LMCI', 'MCI', 'AD']

print(f'Total subjects: {len(df)}')

results = []

# 1. Sample counts
counts = [len(df[df['Research Group'] == g]) for g in groups]
row_n = {'Variable': 'n'}
for g, c in zip(groups, counts):
    row_n[g] = str(c)
row_n['P_value'] = '-'
row_n['Test'] = '-'
results.append(row_n)

# 2. Continuous variables
continuous_vars = [
    ('Age', 'Age (years)'),
    ('Weight', 'Weight (kg)'),
    ('MMSE Total Score', 'MMSE'),
    ('GDSCALE Total Score', 'GDSCALE'),
    ('Global CDR', 'Global CDR'),
    ('FAQ Total Score', 'FAQ'),
    ('NPI-Q Total Score', 'NPI-Q'),
]

for col, name in continuous_vars:
    row = {'Variable': name}
    group_data = []
    for g in groups:
        vals = df[df['Research Group'] == g][col].dropna()
        group_data.append(vals.values)
        row[g] = f'{vals.mean():.2f} ± {vals.std():.2f}'
    
    # One-way ANOVA
    f_stat, p_anova = stats.f_oneway(*group_data)
    # Kruskal-Wallis as non-parametric reference
    h_stat, p_kruskal = stats.kruskal(*group_data)
    
    row['F_stat'] = f'{f_stat:.4f}'
    row['P_value'] = f'{p_anova:.4e}' if p_anova < 0.001 else f'{p_anova:.4f}'
    row['P_display'] = '<0.001' if p_anova < 0.001 else f'{p_anova:.4f}'
    row['Kruskal_P'] = f'{p_kruskal:.4e}' if p_kruskal < 0.001 else f'{p_kruskal:.4f}'
    row['Test'] = 'One-way ANOVA'
    results.append(row)

# 3. Categorical variable: Sex
row_sex = {'Variable': 'Sex (M/F)'}
sex_table = []
for g in groups:
    sub = df[df['Research Group'] == g]
    m_count = (sub['Sex'] == 'M').sum()
    f_count = (sub['Sex'] == 'F').sum()
    sex_table.append([m_count, f_count])
    row_sex[g] = f'{m_count}/{f_count}'

chi2_stat, p_chi2, dof, _ = stats.chi2_contingency(np.array(sex_table))
row_sex['F_stat'] = f'Chi2={chi2_stat:.4f}'
row_sex['P_value'] = f'{p_chi2:.4e}' if p_chi2 < 0.001 else f'{p_chi2:.4f}'
row_sex['P_display'] = '<0.001' if p_chi2 < 0.001 else f'{p_chi2:.4f}'
row_sex['Kruskal_P'] = '-'
row_sex['Test'] = 'Chi-square'
results.append(row_sex)

res_df = pd.DataFrame(results)
res_df.to_csv('8_revision_evidence/table_s1_recalculated_real_data.csv', index=False)

print('=== Recalculated Table S1 (Real Patient Data) ===')
cols_display = ['Variable', 'CN', 'EMCI', 'LMCI', 'MCI', 'AD', 'P_display', 'Test']
print(res_df[cols_display].to_string(index=False))
