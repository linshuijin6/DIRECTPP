from pathlib import Path
import importlib.util,json,hashlib
import numpy as np,pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102';DEST=OUT/'G3';DEST.mkdir(exist_ok=True)
src=ROOT/'reports/clinical_regression_unet_e165_paired_analysis_20261028/analysis.py'
spec=importlib.util.spec_from_file_location('existing_generation_statistics',src);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
paths={'Full':'original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv','ClinicalUNet':'clinical_regression_unet_task_a_20261027_instance1/oof_summary/per_subject_metrics.csv','SwinUNETR':'swinunetr_2fold_20261029/oof_launch_20261102T120914Z/per_subject_metrics.csv','TabularMLP':'tabular_mlp_20261028_v3/oof_summary/per_subject_metrics.csv','TracerOnly':'tracer_only_control_20261027/oof_summary/per_subject_metrics.csv'}
tables={};sources=[]
for model,path in paths.items():
    p=ROOT/'reports'/path;d=pd.read_csv(p,float_precision='round_trip');d=d[d.epoch==(200 if model=='SwinUNETR' else 165)].copy()
    d['tracer']=d.tracer.str.lower()
    assert len(d)==2963 and not d.duplicated(['ptid','tracer','fold']).any();assert np.isfinite(d[list(old.METRICS)]).all().all()
    tables[model]=d;sources.append(dict(model=model,path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
single_files=list((OUT/'remote/single_results').glob('*/metrics.csv'))
if len(single_files)==4:
    d=pd.concat([pd.read_csv(p,float_precision='round_trip') for p in single_files]);assert len(d)==2963 and set(d.tracer)=={'av45','fdg'}
    for p in single_files:
        r=json.loads(p.with_name('completion.json').read_text());assert hashlib.sha256(p.read_bytes()).hexdigest()==r['metrics_sha256']
        s=pd.read_csv(p);assert len(s)==r['metric_rows'] and set(s.checkpoint_sha256)=={r['checkpoint_sha256']}
    tables['Single']=d
full=tables['Full'];key=['ptid','tracer','fold'];pairs=[];dist=[];foldrows=[]
for model,data in tables.items():
    for (tracer,fold),s in data.groupby(['tracer','fold']):
        for metric in old.METRICS:
            foldrows.append(dict(model=model,tracer=tracer,fold=fold,metric=metric,n=len(s),mean=s[metric].mean(),sample_sd=s[metric].std(ddof=1)))
    for tracer,s in data.groupby('tracer'):
        for m in old.METRICS:
            q=np.quantile(s[m],[.05,.5,.95]);dist.append(dict(model=model,tracer=tracer,epoch=int(s.epoch.iloc[0]),metric=m,n=len(s),mean=s[m].mean(),sample_sd=s[m].std(ddof=1),p05=q[0],median=q[1],p95=q[2]))
    if model=='Full':continue
    result=DEST/f'paired_{model}.csv'
    if result.exists():pairs.extend(pd.read_csv(result).to_dict('records'));continue
    joined=full.merge(data,on=key,suffixes=('_full','_baseline'),validate='one_to_one')
    assert len(joined)==len(data)
    rows=[]
    for ti,tracer in enumerate(('fdg','av45')):
        s=joined[joined.tracer==tracer].sort_values(['fold','ptid']);n=len(s)
        if n==0:continue
        for mi,m in enumerate(old.METRICS):
            a=s[m+'_full'].to_numpy();b=s[m+'_baseline'].to_numpy();delta=a-b;folds=s.fold.to_numpy()
            row=dict(model=model,tracer=tracer,metric=m,n=n,mean_delta=delta.mean(),cohen_dz=delta.mean()/delta.std(ddof=1),full_better_proportion=np.mean(delta>0 if m in ('ssim','psnr') else delta<0),fold1_mean_delta=delta[folds==1].mean(),fold2_mean_delta=delta[folds==2].mean())
            if model=='ClinicalUNet':
                native=pd.read_csv(ROOT/'reports/clinical_regression_unet_e165_paired_analysis_20261028/paired_statistics_full.csv');r=native[(native.tracer==tracer.upper())&(native.metric==m.upper())].iloc[0]
                row.update(mean_delta=r.mean_delta,cohen_dz=r.cohen_dz,ci_low=r.bootstrap_ci_lower,ci_high=r.bootstrap_ci_upper,t_stat=r.t_statistic,p_raw=r.p_raw,p_holm=r.p_holm,stat_source='reused verified complete ClinicalUNet statistics')
                np.testing.assert_allclose(delta.mean(),r.mean_delta,atol=1e-14)
            else:
                lo,hi=old.stratified_bootstrap_ci(delta,folds,ti*4+mi,10000)
                if model=='TracerOnly':
                    native=pd.read_csv(ROOT/'reports/tracer_only_control_20261027/oof_summary/paired_comparison_summary.csv');r=native[(native.epoch==165)&(native.tracer==tracer)&(native.metric==m.upper())].iloc[0]
                    row.update(t_stat=-r.paired_t_stat,p_raw=r.p_value,cohen_dz=-r.cohen_d,stat_source='existing t-test/dz reused with sign conversion; bootstrap newly supplemented')
                    np.testing.assert_allclose(delta.mean(),-r.diff_mean,atol=1e-14)
                else:
                    t=stats.ttest_rel(a,b);row.update(t_stat=t.statistic,p_raw=t.pvalue,stat_source='new missing pair; native fold bootstrap')
                row.update(ci_low=lo,ci_high=hi)
            row.update(bootstrap_repeats=10000,bootstrap_seed=42,delta_definition='Full minus baseline',family_size=8)
            rows.append(row)
    if model!='ClinicalUNet':
        pp=old.holm_adjust([r['p_raw'] for r in rows])
        for r,p in zip(rows,pp):r['p_holm']=p
    pd.DataFrame(rows).to_csv(result,index=False);pairs.extend(rows);print('COMPLETE',model,flush=True)
pd.DataFrame(dist).to_csv(DEST/'distribution_summary.csv',index=False);pd.DataFrame(foldrows).to_csv(DEST/'fold_summary.csv',index=False);pd.DataFrame(pairs).to_csv(DEST/'paired_comparisons.csv',index=False)
(DEST/'sources.json').write_text(json.dumps(sources,indent=2))
