"""Collect18 frozen clinical fits, add missing paired statistics and ROC bands."""
from pathlib import Path
import importlib.util,json,hashlib
import numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score,roc_curve
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3]; OUT=ROOT/'reports/revision_evidence_night_20261102'; DEST=OUT/'G5'
DEST.mkdir(exist_ok=True)
src=ROOT/'reports/r2_11_classification_3fold/statistical_comparison/analyze.py'
spec=importlib.util.spec_from_file_location('existing_classification_statistics',src); old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
conditions=['mri','mri_real_both','mri_syn_both','clinical','mri_clinical']
pairs=[('mri_syn_both','clinical'),('mri_syn_both','mri_clinical'),('mri_clinical','mri'),('clinical','mri')]
frames=[]; runs=[]; checks=[]
splits=pd.read_csv(ROOT/'reports/r2_11_classification_3fold/splits.csv');test=splits[splits.split=='test']
for f in sorted((OUT/'remote/clinical').glob('*/**/summary.json')):
    d=json.loads(f.read_text()); assert d['status']=='complete' and d['epochs']==200 and d['test_evaluations']==1 and not d['pilot_only']
    pr=pd.read_csv(f.parent/'test_predictions.csv',float_precision='round_trip')
    task,condition,fold=d['task'],d['condition'],d['fold']
    want=test[(test.task==task)&(test.fold==fold)].sort_values('PTID')
    pr=pr.sort_values('PTID');assert pr.PTID.tolist()==want.PTID.tolist() and np.array_equal(pr.y_true,want.y_true)
    assert set(pr.condition)=={condition} and set(pr.fold)=={fold} and set(pr.task)=={task}
    assert np.isfinite(pr.p_positive).all() and pr.p_positive.between(0,1).all()
    assert np.array_equal(pr.y_pred,(pr.p_positive>=.5).astype(int))
    m=old.weighted_metrics(pr.y_true.to_numpy(),pr.p_positive.to_numpy(),pr.y_pred.to_numpy(),np.ones((1,len(pr)),int))[0]
    np.testing.assert_allclose(m,[d['test_metrics'][k] for k in old.METRICS],atol=1e-12)
    row=dict(task=task,condition=condition,fold=fold,n=len(pr),parameters=d['parameters'],best_epoch=d['best_epoch'],source=str(f.relative_to(ROOT)))
    row.update(dict(zip(old.METRICS,m))); runs.append(row);frames.append(pr)
assert len(runs)==18
clinical=pd.concat(frames,ignore_index=True);assert not clinical.duplicated(['task','condition','PTID']).any()
clinical.to_csv(DEST/'clinical_oof_predictions_internal.csv',index=False);pd.DataFrame(runs).to_csv(DEST/'clinical_fold_metrics.csv',index=False)
imaging=pd.read_csv(ROOT/'reports/r2_11_classification_3fold/final_summary/oof_predictions.csv',float_precision='round_trip')
allpred=pd.concat([imaging,clinical],ignore_index=True)
summaries=[];comparisons=[];delong=[];rocrows=[]
rng=np.random.default_rng(20261102);reps=5000;band_reps=2000;grid=np.linspace(0,1,201)
colors=['#2864A5','#B8860B','#D55E00','#6B7537','#B75183'];styles=['-','--','-.',':',(0,(5,1,1,1))]
names=['MRI','MRI + Real dual PET','MRI + Syn dual PET','Clinical-only','MRI + Clinical']
for task,(_,title) in old.TASKS.items():
    draws=np.empty((reps,3,5,5));actual=np.empty((3,5,5)); rocpoint=np.empty((3,5,201));rocboot=np.empty((band_reps,3,5,201))
    for fold in (1,2,3):
        w=test[(test.task==task)&(test.fold==fold)].sort_values('PTID');y=w.y_true.to_numpy(int);ids=w.PTID.tolist()
        weights=np.zeros((reps,len(ids)),dtype=np.int64)
        for label in (0,1):
            ii=np.flatnonzero(y==label);sampled=ii[rng.integers(len(ii),size=(reps,len(ii)))]
            weights+=np.bincount((np.arange(reps)[:,None]*len(ids)+sampled).ravel(),minlength=reps*len(ids)).reshape(weights.shape)
        scores={}
        for ci,c in enumerate(conditions):
            pp=allpred[(allpred.task==task)&(allpred.condition==c)&(allpred.fold==fold)].sort_values('PTID')
            assert pp.PTID.tolist()==ids and np.array_equal(pp.y_true,y)
            score=pp.p_positive.to_numpy();pred=pp.y_pred.to_numpy();scores[c]=score
            actual[fold-1,ci]=old.weighted_metrics(y,score,pred,np.ones((1,len(ids)),int))[0]
            draws[:,fold-1,ci]=old.weighted_metrics(y,score,pred,weights)
            # Check genuine data with sklearn and explicit repeated subjects.
            for b in (0,reps-1):
                ix=np.repeat(np.arange(len(ids)),weights[b]);np.testing.assert_allclose(draws[b,fold-1,ci,1],roc_auc_score(y[ix],score[ix]),atol=1e-12)
            fpr,tpr,_=roc_curve(y,score,drop_intermediate=False)
            rocpoint[fold-1,ci]=np.interp(grid,fpr,tpr)
            for b in range(band_reps):
                # sample_weight follows exactly the fold/class paired draws.
                fpr,tpr,_=roc_curve(y,score,sample_weight=weights[b],drop_intermediate=False)
                rocboot[b,fold-1,ci]=np.interp(grid,fpr,tpr)
        for target,reference in pairs:
            row=dict(task=task,target=target,reference=reference,fold=fold,n=len(ids),family='36 new clinical comparisons',family_size=36)
            try:
                aa,dd,se,z,p=old.paired_delong(y,scores[target],scores[reference]);row.update(delta_AUC=dd,se=se,z=z,p_raw=p,status='computed')
            except ValueError as e: row.update(delta_AUC=actual[fold-1,conditions.index(target),1]-actual[fold-1,conditions.index(reference),1],p_raw=np.nan,status=str(e))
            delong.append(row)
    means=actual.mean(0);boots=draws.mean(1)
    for ci,c in enumerate(conditions):
        if c not in ('clinical','mri_clinical'):continue
        for mi,m in enumerate(old.METRICS):
            low,high=np.percentile(boots[:,ci,mi],[2.5,97.5]);summaries.append(dict(task=task,condition=c,metric=m,n_subjects=old.TASKS[task][0],n_folds=3,mean=means[ci,mi],sample_sd=actual[:,ci,mi].std(ddof=1),ci_low=low,ci_high=high,bootstrap_repeats=reps,seed=20261102))
    for target,reference in pairs:
        ti,ri=conditions.index(target),conditions.index(reference)
        for mi,m in enumerate(old.METRICS):
            dd=boots[:,ti,mi]-boots[:,ri,mi];lo,hi=np.percentile(dd,[2.5,97.5])
            comparisons.append(dict(task=task,target=target,reference=reference,metric=m,delta=means[ti,mi]-means[ri,mi],ci_low=lo,ci_high=hi,multiplicity='marginal95% CI; no simultaneous coverage',bootstrap_repeats=reps,seed=20261102))
    meanroc=rocpoint.mean(0);lower,upper=np.percentile(rocboot.mean(1),[2.5,97.5],axis=0)
    fig,ax=plt.subplots(figsize=(7.3,6.3))
    for ci,c in enumerate(conditions):
        ax.plot(grid,meanroc[ci],color=colors[ci],linestyle=styles[ci],lw=1.9,label=f'{names[ci]} (mean AUC {means[ci,1]:.3f})')
        ax.fill_between(grid,lower[ci],upper[ci],color=colors[ci],alpha=.10,lw=0)
        for i,x in enumerate(grid):rocrows.append(dict(task=task,condition=c,fpr=x,mean_tpr=meanroc[ci,i],ci_low=lower[ci,i],ci_high=upper[ci,i],band='pointwise95% fold/class bootstrap;2000',mean_fold_auc=means[ci,1]))
    ax.plot([0,1],[0,1],color='.4',ls='--',lw=1);ax.set(xlim=(0,1),ylim=(0,1.01),xlabel='False positive rate',ylabel='True positive rate',title=title)
    ax.legend(loc='lower right',fontsize=8.3,frameon=False);ax.spines[['top','right']].set_visible(False)
    fig.text(.5,.01,'Mean of 3 outer-test ROC curves; shading: pointwise 95% conditional bootstrap CI.\nPositive class: '+{'ad_cn':'AD','mci_cn':'EMCI+LMCI (MCI-U excluded)','emci_lmci':'LMCI'}[task],ha='center',fontsize=8)
    fig.tight_layout(rect=(0,.055,1,1));fig.savefig(OUT/f'figures/G5_ROC_{task}.png',dpi=220);plt.close(fig)
    print('COMPLETE',task,flush=True)
def holm(p):
    order=np.argsort(p);result=np.empty(len(p));result[order]=np.minimum(1,np.maximum.accumulate(np.array(p)[order]*(len(p)-np.arange(len(p)))));return result
dd=pd.DataFrame(delong);dd['p_holm']=holm(dd.p_raw.fillna(1));dd.loc[dd.p_raw.isna(),'p_holm']=np.nan
pd.DataFrame(summaries).to_csv(DEST/'clinical_summary.csv',index=False)
pd.DataFrame(comparisons).to_csv(DEST/'clinical_paired_comparisons.csv',index=False);dd.to_csv(DEST/'clinical_delong_by_fold.csv',index=False)
pd.DataFrame(rocrows).to_csv(DEST/'roc_curves_and_bands.csv',index=False)
# Multiplicity of the existing18 imaging DeLong tests is made explicit without rerunning.
ddold=pd.read_csv(ROOT/'reports/r2_11_classification_3fold/statistical_comparison/delong_by_fold.csv')
ddold['p_holm_family18']=holm(ddold.p_value_unadjusted_twosided.to_numpy());ddold.to_csv(DEST/'existing_imaging_delong_holm.csv',index=False)
(DEST/'validation.json').write_text(json.dumps(dict(status='PASS',clinical_fits=18,clinical_prediction_rows=len(clinical),new_summary_rows=len(summaries),new_comparison_rows=len(comparisons),new_delong_rows=len(dd),source_statistics_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),positive_classes=['AD','EMCI+LMCI','LMCI'],no_inference=True),indent=2))
