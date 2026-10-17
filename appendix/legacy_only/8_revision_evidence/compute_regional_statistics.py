import os, glob, json
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

with open('4_analysis_and_figures/scripts/brain_labels.json') as f:
    brain_dict = json.load(f)

def calc_ccc(y_true, y_pred):
    cov = np.cov(y_true, y_pred)[0, 1]
    var_true = np.var(y_true, ddof=1)
    var_pred = np.var(y_pred, ddof=1)
    mean_true = np.mean(y_true)
    mean_pred = np.mean(y_pred)
    sd_true = np.std(y_true, ddof=1)
    sd_pred = np.std(y_pred, ddof=1)
    cor = np.corrcoef(y_true, y_pred)[0, 1]
    numerator = 2 * cor * sd_true * sd_pred
    denominator = var_true + var_pred + (mean_true - mean_pred)**2
    return numerator / denominator if denominator != 0 else 0.0

def calc_icc_2_1(y_true, y_pred):
    n = len(y_true)
    k = 2
    Y = np.column_stack([y_true, y_pred])
    row_means = np.mean(Y, axis=1)
    col_means = np.mean(Y, axis=0)
    grand_mean = np.mean(Y)
    
    SS_total = np.sum((Y - grand_mean)**2)
    SS_rows = k * np.sum((row_means - grand_mean)**2)
    SS_cols = n * np.sum((col_means - grand_mean)**2)
    SS_error = SS_total - SS_rows - SS_cols
    
    MS_rows = SS_rows / (n - 1)
    MS_cols = SS_cols / (k - 1)
    MS_error = SS_error / ((n - 1) * (k - 1))
    
    denom = MS_rows + (k - 1) * MS_error + (k / n) * (MS_cols - MS_error)
    return (MS_rows - MS_error) / denom if denom != 0 else 0.0

def tost_paired(diff, bound):
    # TOST for paired differences
    # H01: mean <= -bound vs H11: mean > -bound
    # H02: mean >= bound vs H12: mean < bound
    n = len(diff)
    mean_diff = np.mean(diff)
    se = np.std(diff, ddof=1) / np.sqrt(n)
    
    t1 = (mean_diff - (-bound)) / se
    p1 = 1 - stats.t.cdf(t1, df=n-1)
    
    t2 = (mean_diff - bound) / se
    p2 = stats.t.cdf(t2, df=n-1)
    
    return max(p1, p2)

def process_tracer(tracer_name, folder_path):
    files = glob.glob(os.path.join(folder_path, 'region_*.csv'))
    rows = []
    
    for f in sorted(files):
        df = pd.read_csv(f)
        real_col = f'real_{tracer_name}_mean'
        syn_col = f'syn_{tracer_name}_mean'
        
        if real_col not in df.columns or syn_col not in df.columns:
            continue
            
        valid = df[[real_col, syn_col]].dropna()
        if len(valid) < 10:
            continue
            
        y_real = valid[real_col].values
        y_syn = valid[syn_col].values
        diff = y_syn - y_real  # signed bias (Syn - Real)
        
        region_code = os.path.basename(f).replace('region_', '').replace('.csv', '').replace('.0', '')
        region_name = brain_dict.get(region_code, f'Region_{region_code}')
        
        n = len(valid)
        real_mean = np.mean(y_real)
        real_sd = np.std(y_real, ddof=1)
        syn_mean = np.mean(y_syn)
        syn_sd = np.std(y_syn, ddof=1)
        
        mae = np.mean(np.abs(diff))
        mape = np.mean(np.abs(diff) / np.maximum(y_real, 1e-6)) * 100
        mean_bias = np.mean(diff)
        sd_diff = np.std(diff, ddof=1)
        loa_lower = mean_bias - 1.96 * sd_diff
        loa_upper = mean_bias + 1.96 * sd_diff
        
        t_stat, p_val = stats.ttest_rel(y_syn, y_real)
        r_val, _ = stats.pearsonr(y_real, y_syn)
        ccc_val = calc_ccc(y_real, y_syn)
        icc_val = calc_icc_2_1(y_real, y_syn)
        
        # TOST with 5% of ground truth mean as standard physiological equivalence bound
        bound_5pct = 0.05 * real_mean
        p_tost_5pct = tost_paired(diff, bound_5pct)
        bound_10pct = 0.10 * real_mean
        p_tost_10pct = tost_paired(diff, bound_10pct)
        
        rows.append({
            'Tracer': tracer_name.upper(),
            'Region_Code': region_code,
            'Region_Name': region_name,
            'N': n,
            'Real_Mean': real_mean,
            'Real_SD': real_sd,
            'Syn_Mean': syn_mean,
            'Syn_SD': syn_sd,
            'MAE': mae,
            'MAPE_pct': mape,
            'Mean_Bias': mean_bias,
            'SD_Diff': sd_diff,
            'BA_Lower_LoA': loa_lower,
            'BA_Upper_LoA': loa_upper,
            'Paired_t_stat': t_stat,
            'Paired_t_pval': p_val,
            'Pearson_r': r_val,
            'Lin_CCC': ccc_val,
            'ICC_2_1': icc_val,
            'TOST_p_5pct': p_tost_5pct,
            'TOST_p_10pct': p_tost_10pct,
        })
        
    res_df = pd.DataFrame(rows)
    # Apply Benjamini-Hochberg FDR
    reject, qvals, _, _ = multipletests(res_df['Paired_t_pval'].values, method='fdr_bh')
    res_df['FDR_qval'] = qvals
    res_df['Sig_FDR_005'] = reject
    
    return res_df

df_fdg = process_tracer('fdg', '4_analysis_and_figures/statistics_fdg')
df_av45 = process_tracer('av45', '4_analysis_and_figures/statistics_av45')

df_fdg.to_csv('8_revision_evidence/regional_statistical_metrics_fdg_all98.csv', index=False)
df_av45.to_csv('8_revision_evidence/regional_statistical_metrics_av45_all98.csv', index=False)

print(f'Processed FDG: {len(df_fdg)} regions')
print(f'Processed AV45: {len(df_av45)} regions')

