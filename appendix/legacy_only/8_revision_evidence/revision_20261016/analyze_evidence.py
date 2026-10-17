"""CPU-only analysis of observed records and recovered paired ROI CSVs.

Run from the repository root. No training, image generation, or source writes.
"""
import hashlib
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats
import statsmodels.api as sm
from statsmodels.stats.multitest import multipletests

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
UPSTREAM = Path('/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45')
GROUPS = ['CN', 'EMCI', 'LMCI', 'MCI', 'AD']
SCORES = ['MMSE Total Score', 'GDSCALE Total Score', 'Global CDR', 'FAQ Total Score', 'NPI-Q Total Score']


def add_q(df, p, q, by=None):
    df[q] = np.nan
    groups = df.groupby(by).groups.values() if by else [df.index]
    for ix in groups:
        ix = df.loc[ix].index[df.loc[ix, p].notna()]
        if len(ix): df.loc[ix, q] = multipletests(df.loc[ix, p], method='fdr_bh')[1]


def agreement(x, y):
    """McGraw-Wong single-measure absolute agreement ICC(A,1); Lin CCC.

    ICC absolute-agreement ANOVA formula, numerically ICC(2,1).
    Methods are fixed, so inference is confined to these Real/Syn methods.
    CCC uses empirical moments (ddof=0), recorded to remove ambiguity.
    """
    x, y = np.asarray(x), np.asarray(y)
    n = x.shape[-1]
    grand = (x.mean(-1) + y.mean(-1))/2
    msr = 2 * np.sum(((x+y)/2-grand[..., None])**2, axis=-1)/(n-1)
    msc = n * ((x.mean(-1)-grand)**2 + (y.mean(-1)-grand)**2)
    residual_x = x - (x+y)/2 - x.mean(-1)[..., None] + grand[..., None]
    residual_y = y - (x+y)/2 - y.mean(-1)[..., None] + grand[..., None]
    mse = np.sum(residual_x**2 + residual_y**2, axis=-1)/(n-1)
    icc = (msr-mse)/(msr+mse+2*(msc-mse)/n)
    cov = np.mean((x-x.mean(-1)[..., None])*(y-y.mean(-1)[..., None]), axis=-1)
    ccc = 2*cov/(x.var(-1)+y.var(-1)+(x.mean(-1)-y.mean(-1))**2)
    return icc, ccc


def paired_metrics(d, tracer, region, group, rng):
    x = d[f'real_{tracer}_mean'].to_numpy(float)
    y = d[f'syn_{tracer}_mean'].to_numpy(float)
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    n = len(x)
    if n < 3: return None
    diff = y-x
    bias, sd = diff.mean(), diff.std(ddof=1)
    icc, ccc = agreement(x, y)
    half = stats.t.ppf(.975, n-1)*sd/np.sqrt(n)
    slope = stats.linregress(x, y)
    prop = stats.linregress((x+y)/2, diff)
    # Paired subject bootstrap, equal weights within one ROI and stratum.
    b = 1000 if group == 'ALL' else 500
    bs = []
    for start in range(0, b, 50):
        ix = rng.integers(0, n, (min(50, b-start), n))
        xx, yy = x[ix], y[ix]
        bi, bc = agreement(xx, yy)
        bs.append(np.column_stack([bi, bc]))
    ci = np.nanpercentile(np.concatenate(bs), [2.5,97.5], axis=0)
    return dict(tracer=tracer, region=region, group=group, n=n, excluded_nonfinite=int((~keep).sum()),
                real_mean=x.mean(), real_sd=x.std(ddof=1), syn_mean=y.mean(), syn_sd=y.std(ddof=1),
                mae=np.mean(np.abs(diff)), rmse=np.sqrt(np.mean(diff**2)), bias_syn_minus_real=bias,
                bias_ci_low=bias-half, bias_ci_high=bias+half,
                diff_sd=sd, ba_loa_low=bias-1.96*sd, ba_loa_high=bias+1.96*sd,
                # Normal approximation CI for each limit of agreement.
                ba_low_ci_low=bias-1.96*sd-1.96*sd*np.sqrt(3/n),
                ba_low_ci_high=bias-1.96*sd+1.96*sd*np.sqrt(3/n),
                ba_high_ci_low=bias+1.96*sd-1.96*sd*np.sqrt(3/n),
                ba_high_ci_high=bias+1.96*sd+1.96*sd*np.sqrt(3/n),
                paired_t=stats.ttest_rel(y,x).statistic, paired_p=stats.ttest_rel(y,x).pvalue,
                icc_a1=float(icc), icc_ci_low=ci[0,0], icc_ci_high=ci[1,0],
                ccc=float(ccc), ccc_ci_low=ci[0,1], ccc_ci_high=ci[1,1],
                pearson_r=stats.pearsonr(x,y).statistic,
                calibration_slope=slope.slope, calibration_intercept=slope.intercept,
                calibration_slope_se=slope.stderr, proportional_bias_slope=prop.slope,
                proportional_bias_p=prop.pvalue, bootstrap_replicates=b,
                unit='normalized uptake (arbitrary units)', validation_scope='retrospective; generator exposure unresolved')


def clinical_table():
    rawp = UPSTREAM/'ADNI MRI and FDG and AV45 csv.csv'
    raw = pd.read_csv(rawp, low_memory=False)
    meta = pd.read_csv(ROOT/'5_data_splits/filtered_subjects_with_description.csv')
    # Preserve the study's chosen demographic record. Exact five-key join
    # retrieves observed scores only at that anchor, never across visits.
    keys = ['Subject ID','Sex','Weight','Research Group','Age']
    j = meta[keys].merge(raw, on=keys, how='left', indicator=True)
    assert j.loc[j._merge=='both','Subject ID'].nunique() == len(meta)
    obs = meta[keys].set_index('Subject ID')
    provenance = []
    for c in SCORES:
        grouped = j.groupby('Subject ID')[c]
        nunique = grouped.nunique(dropna=True)
        observed = grouped.agg(lambda x: x.dropna().iloc[0] if x.nunique(dropna=True)==1 else np.nan)
        obs[c] = observed
        for s in obs.index:
            value = obs.loc[s,c]
            provenance.append(dict(subject=s, variable=c, observed_value=value,
                                   status='observed_unique' if pd.notna(value) else ('conflicting' if nunique[s]>1 else 'missing_at_anchor'),
                                   filled_value=meta.set_index('Subject ID').loc[s,c]))
    invalid_weight = obs[obs.Weight <= 0].copy()
    invalid_weight.to_csv(OUT/'clinical_invalid_nonpositive_weight.csv')
    obs.loc[obs.Weight <= 0,'Weight'] = np.nan
    obs.to_csv(OUT/'clinical_observed_subjects.csv')
    pd.DataFrame(provenance).to_csv(OUT/'clinical_observed_provenance.csv', index=False)
    # Link source row/image IDs, not merely aggregate counts.
    j[keys+['Image ID','Modality']+SCORES].to_csv(OUT/'clinical_anchor_source_rows.csv', index=False)
    results=[]
    for c in ['Age','Weight']+SCORES:
        vectors=[obs.loc[obs['Research Group']==g,c].dropna().to_numpy() for g in GROUPS]
        row={'variable':c,'total_observed':sum(map(len,vectors)), 'missing':int(obs[c].isna().sum())}
        for g,v in zip(GROUPS,vectors):
            row[g+'_n']=len(v); row[g+'_mean']=np.mean(v) if len(v) else np.nan
            row[g+'_sd']=np.std(v,ddof=1) if len(v)>1 else np.nan
        if all(len(v)>1 for v in vectors):
            f,p=stats.f_oneway(*vectors);h,kp=stats.kruskal(*vectors)
            row.update(anova_f=f,anova_p=p,kruskal_h=h,kruskal_p=kp)
        else:row['status']='not_testable_empty_or_singleton_group'
        results.append(row)
    res=pd.DataFrame(results)
    add_q(res,'anova_p','anova_q_bh_available');add_q(res,'kruskal_p','kruskal_q_bh_available')
    res.to_csv(OUT/'table_s1_observed_continuous.csv',index=False)
    sex=pd.crosstab(obs['Research Group'],obs.Sex).reindex(GROUPS)
    chi,p,dof,exp=stats.chi2_contingency(sex)
    sex.to_csv(OUT/'table_s1_observed_sex_counts.csv')
    summary={'anchor':'exact Subject ID + Sex + Weight + Research Group + Age; unique observed value only',
             'clinical_source':str(rawp),'source_sha256':hashlib.sha256(rawp.read_bytes()).hexdigest(),
             'matched_subjects':len(obs),'source_matched_rows':len(j),
             'nonpositive_weight_set_missing':len(invalid_weight),
             'visit_date_unavailable':True,'chi2':chi,'sex_p':p,'sex_df':int(dof),
             'min_sex_expected_count':float(exp.min()),
             'caveat':'Image-derived clinical export has no examination date. No claim of verified baseline visit alignment. Missing observations are not filled.'}
    (OUT/'table_s1_methods.json').write_text(json.dumps(summary,indent=2))
    return obs


def regions(region_dirs=None):
    rng=np.random.default_rng(20261016)
    meta=pd.read_csv(ROOT/'5_data_splits/filtered_subjects_with_description.csv').set_index('Subject ID')
    labels=json.loads((ROOT/'4_analysis_and_figures/scripts/brain_labels.json').read_text())
    rows=[]; diseases=[]; qc=[]; adjusted=[]
    for tracer in ['av45','fdg']:
        subject_set=None
        folder = region_dirs[tracer] if region_dirs else ROOT/f'4_analysis_and_figures/statistics_{tracer}'
        for p in sorted(folder.glob('region_*.csv')):
            d=pd.read_csv(p);assert not d.subject.duplicated().any(),p
            assert set(d.subject)<=set(meta.index),p
            assert all(d['Research Group'].to_numpy()==meta.loc[d.subject,'Research Group'].to_numpy()),p
            if subject_set is None:subject_set=set(d.subject)
            assert set(d.subject)==subject_set,p
            region=int(float(p.stem.removeprefix('region_')))
            qc.append(dict(tracer=tracer,region=region,rows=len(d),missing_pairs=int(d[[f'real_{tracer}_mean',f'syn_{tracer}_mean']].isna().any(axis=1).sum()),subject_duplicates=0,label_conflicts=0))
            for group in ['ALL']+GROUPS:
                sub=d if group=='ALL' else d[d['Research Group']==group]
                row=paired_metrics(sub,tracer,region,group,rng)
                if row:row['region_name']=labels.get(str(region),'unknown');rows.append(row)
            ad=d[d['Research Group']=='AD'];cn=d[d['Research Group']=='CN']
            for method in ['real','syn']:
                a=ad[f'{method}_{tracer}_mean'].dropna().to_numpy();c=cn[f'{method}_{tracer}_mean'].dropna().to_numpy()
                t,pv=stats.ttest_ind(a,c,equal_var=False)
                diseases.append(dict(tracer=tracer,region=region,method=method,n_ad=len(a),n_cn=len(c),ad_minus_cn=a.mean()-c.mean(),welch_t=t,welch_p=pv))
            # Paired contrast: AD-CN difference in Syn-Real bias, with demographics.
            ac=d[d['Research Group'].isin(['AD','CN'])].set_index('subject').join(meta[['Age','Sex','Weight']])
            ac['AD']=(ac['Research Group']=='AD').astype(float);ac['male']=(ac.Sex=='M').astype(float)
            x=sm.add_constant(ac[['AD','Age','male','Weight']].astype(float))
            diff=ac[f'syn_{tracer}_mean']-ac[f'real_{tracer}_mean']
            for outcome,y in [('syn_minus_real',diff),('real',ac[f'real_{tracer}_mean']),('syn',ac[f'syn_{tracer}_mean'])]:
                fit=sm.OLS(y,x,missing='drop').fit(cov_type='HC3')
                ci=fit.conf_int().loc['AD']
                adjusted.append(dict(tracer=tracer,region=region,outcome=outcome,n=int(fit.nobs),ad_beta=fit.params['AD'],ad_se=fit.bse['AD'],ad_p=fit.pvalues['AD'],ad_ci_low=ci.iloc[0],ad_ci_high=ci.iloc[1],covariates='age + sex + weight',scope='descriptive; filled demographic table; exposure unresolved'))
            print(tracer,region,'done',flush=True)
    res=pd.DataFrame(rows)
    overall=res[res.group=='ALL'].copy();strata=res[res.group!='ALL'].copy()
    for d in [overall,strata]:
        add_q(d,'paired_p','paired_q_global')
        add_q(d,'paired_p','paired_q_within_tracer_group',['tracer','group'])
        add_q(d,'proportional_bias_p','proportional_bias_q_global')
    overall.to_csv(OUT/'regional_agreement_overall.csv',index=False)
    strata.to_csv(OUT/'regional_agreement_by_diagnosis.csv',index=False)
    pd.DataFrame(qc).to_csv(OUT/'regional_input_qc.csv',index=False)
    disease=pd.DataFrame(diseases);add_q(disease,'welch_p','welch_q_global392')
    disease.to_csv(OUT/'regional_AD_CN_unadjusted.csv',index=False)
    adj=pd.DataFrame(adjusted);add_q(adj,'ad_p','ad_q_within_outcome196',['outcome'])
    adj.to_csv(OUT/'regional_AD_CN_adjusted_HC3.csv',index=False)
    summ=[]
    for tracer,d in overall.groupby('tracer'):
        summ.append(dict(tracer=tracer,regions=len(d),n=int(d.n.iloc[0]),paired_p_lt05=int((d.paired_p<.05).sum()),
                         paired_global_q_lt05=int((d.paired_q_global<.05).sum()),
                         mae_median=float(d.mae.median()),mae_min=float(d.mae.min()),mae_max=float(d.mae.max()),
                         bias_min=float(d.bias_syn_minus_real.min()),bias_max=float(d.bias_syn_minus_real.max()),
                         icc_median=float(d.icc_a1.median()),icc_min=float(d.icc_a1.min()),icc_max=float(d.icc_a1.max()),
                         ccc_median=float(d.ccc.median()),ccc_min=float(d.ccc.min()),ccc_max=float(d.ccc.max())))
    (OUT/'regional_summary.json').write_text(json.dumps(summ,indent=2))


if __name__=='__main__':
    clinical_table()
    regions()
    (OUT/'analysis_environment.json').write_text(json.dumps(dict(python=sys.version,numpy=np.__version__,pandas=pd.__version__,scipy=scipy.__version__,platform=platform.platform(),seed=20261016),indent=2))
