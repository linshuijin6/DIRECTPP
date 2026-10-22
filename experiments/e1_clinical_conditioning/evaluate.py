"""E1 normalized-space metrics and lightweight CPU controls.

Pilot checks validate arithmetic and I/O only. Scientific OOF evaluation is
blocked until the spatial gate passes and formal training is authorized.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from scipy import stats

from common import TRACERS, active_rows, check_frozen, load_config, sha, write_json


def regional(a,mask,labels):
    assert a.shape==mask.shape and np.isfinite(a).all()
    sums=np.bincount(mask.ravel(),weights=a.ravel(),minlength=2036)
    counts=np.bincount(mask.ravel(),minlength=2036)
    return np.array([sums[r]/counts[r] if counts[r] else np.nan for r in labels])


def roi_context(cfg,labels):
    """PET-independent ROI validity and frozen physical-hemisphere names."""
    invalid={k:set(v) for k,v in json.loads(Path(cfg["roi_validity"]).read_text())["invalid_rois"].items()}
    names=json.loads(Path(cfg["hemisphere_label_map"]).read_text())["labels"]
    physical={int(l):names[str(int(l))]["physical_name"] for l in labels}
    assert len(set(physical.values()))==len(labels),"Duplicate physical ROI names"
    assert all(bad<=set(map(int,labels)) for bad in invalid.values()),"Unknown invalid ROI label"
    return invalid,physical


def apply_validity(values,labels,bad):
    return np.array([np.nan if int(l) in bad else v for l,v in zip(labels,values)])


def agreement(x,y):
    """CCC and two-way absolute single-measure ICC(A,1), across subjects."""
    valid=np.isfinite(x)&np.isfinite(y);x=x[valid];y=y[valid];n=len(x)
    if n<3:return dict(n=n,mae=None,bias=None,ccc=None,icc_a1=None)
    diff=y-x;vx=x.var(ddof=1);vy=y.var(ddof=1);cov=np.cov(x,y,ddof=1)[0,1]
    ccc=2*cov/(vx+vy+(x.mean()-y.mean())**2)
    mat=np.column_stack([x,y]);grand=mat.mean();row=mat.mean(1);col=mat.mean(0)
    msr=2*np.sum((row-grand)**2)/(n-1)
    msc=n*np.sum((col-grand)**2)
    mse=np.sum((mat-row[:,None]-col[None,:]+grand)**2)/(n-1)
    icc=(msr-mse)/(msr+mse+2*(msc-mse)/n)
    return dict(n=n,mae=float(np.mean(abs(diff))),bias=float(diff.mean()),ccc=float(ccc),icc_a1=float(icc),
                loa_low=float(diff.mean()-1.96*diff.std(ddof=1)),loa_high=float(diff.mean()+1.96*diff.std(ddof=1)))


def paired_bootstrap(values,folds,statistic,reps=10000,seed=20261017):
    """One shared subject index per draw, retaining outer fold sizes."""
    rng=np.random.default_rng(seed);groups=[np.flatnonzero(folds==f) for f in np.unique(folds)]
    observed=statistic(*values);samples=[]
    for _ in range(reps):
        ids=np.concatenate([rng.choice(g,len(g),replace=True) for g in groups])
        samples.append(statistic(*(v[ids] for v in values)))
    a=np.asarray(samples)
    return observed,np.nanquantile(a,[.025,.975],axis=0)


def image_metrics(real,pred,brain=None):
    import sys
    from common import CODE
    sys.path.insert(0,str(CODE))
    import torch
    from generative.metrics.ssim import compute_ssim_and_cs
    mse=float(np.mean((real-pred)**2,dtype=np.float64))
    psnr=float(-10*np.log10(mse)) if mse>0 else float("inf")
    x=torch.from_numpy(real.copy())[None,None];y=torch.from_numpy(pred.copy())[None,None]
    with torch.no_grad():
        field,_=compute_ssim_and_cs(x,y,spatial_dims=3,data_range=1.0,kernel_size=(7,7,7),kernel_sigma=(1.5,1.5,1.5))
    result=dict(psnr=psnr,ssim=float(field.mean()))
    if brain is not None:
        from scipy.ndimage import minimum_filter
        valid=minimum_filter(brain.astype(np.uint8),size=7,mode="constant",cval=0)[3:-3,3:-3,3:-3]>0
        result["brain_ssim"]=float(field.numpy().squeeze()[valid].mean()) if valid.any() else np.nan
    return result


def agreement_vector(real,full,no_scores):
    a=agreement(real,full);b=agreement(real,no_scores)
    return np.array([a["bias"],b["bias"],b["bias"]-a["bias"],
                     a["ccc"],b["ccc"],b["ccc"]-a["ccc"],
                     a["icc_a1"],b["icc_a1"],b["icc_a1"]-a["icc_a1"]])


def pipeline_check(cfg,rows):
    labels=pd.read_csv(Path(cfg["report"])/"roi_labels.csv").region.to_numpy(int)
    invalid,physical=roi_context(cfg,labels)
    active={r["ptid"] for r in rows}
    assert set(invalid)<=active and len(physical)==len(labels)
    for sid,bad in invalid.items():
        fixture=apply_validity(np.ones(len(labels)),labels,bad)
        assert set(map(int,labels[np.isnan(fixture)]))==bad
    for key in cfg["key_rois"].values():
        names={physical[int(l)] for l in key}
        assert len(names)==len(key)
    # Meaningful numerical fixtures, independent of the implementation's saved
    # output: exact match, known constant offset, known mask means.
    x=np.linspace(.1,.8,30);ident=agreement(x,x);offset=agreement(x,x+.05)
    assert abs(ident["ccc"]-1)<1e-12 and abs(ident["icc_a1"]-1)<1e-12
    assert abs(offset["mae"]-.05)<1e-12 and abs(offset["bias"]-.05)<1e-12
    assert offset["ccc"]<1 and offset["icc_a1"]<1
    test=regional(np.array([[[1.,3.,8.]]]),np.array([[[17,17,53]]]),np.array([17,53,1025]))
    assert test[0]==2 and test[1]==8 and np.isnan(test[2])
    index={r["ptid"]:r for r in rows};checks=[]
    for folder in sorted((Path(cfg["assets"])/"pilot").glob("fold*")):
        receipt=json.loads((folder/"receipt.json").read_text());fold=receipt["fold"]
        for path in folder.glob("pilot_*.nii.gz"):
            tracer,sid=path.name.removesuffix(".nii.gz").removeprefix("pilot_").split("_",1)
            row=index[sid];assert row["test_fold"]!=fold
            with np.load(row["cache"]) as z:
                target=z[tracer];mask=z["mask"];aff=z["affine"]
            im=nib.load(path);pred=im.get_fdata(dtype=np.float32)
            assert pred.shape==target.shape and np.allclose(im.affine,aff,atol=1e-5)
            t=regional(target,mask,labels);p=regional(pred,mask,labels)
            assert np.isfinite(p[np.isfinite(t)]).all()
            exact=image_metrics(target,target)
            assert np.isinf(exact["psnr"]) and abs(exact["ssim"]-1)<1e-5
            checks.append(dict(ptid=sid,fold=fold,condition=receipt["condition"],tracer=tracer,
                grid_pass=True,roi_arithmetic_pass=True,identity_image_metric_pass=True,
                nonempty_rois=int(np.isfinite(t).sum()),source_sha256=sha(path)))
    write_json(Path(cfg.get("execution_report",cfg["report"]))/"evaluation_pipeline_check.json",dict(checks=checks,
        numerical_fixtures_pass=True,scientific_evaluation_authorized=False,
        roi_validity_filter_pass=True,physical_name_map_pass=True,
        active_subjects=len(rows),invalid_subjects=len(invalid),
        laterality_gate_pass=cfg["evaluation_laterality_gate_pass"],
        interpretation="Engineering fixtures and historical training-side output I/O only; pilot quality is not an E1 result. Current ROI validity/name mapping checked independently."))


def collect(cfg,rows):
    if not cfg["formal_training_authorized"] or not cfg["evaluation_laterality_gate_pass"] or not cfg["evaluation_mri_mask_gate_pass"]:
        raise RuntimeError("Scientific OOF evaluation blocked: formal authorization / anatomical gate")
    labels=pd.read_csv(Path(cfg["report"])/"roi_labels.csv").region.to_numpy(int)
    records=[];seen=set();images=[]
    invalid,physical=roi_context(cfg,labels)
    lookup={r["ptid"]:r for r in rows}
    for condition in cfg["conditions"]:
        for fold in [1,2]:
            folder=Path(cfg["assets"])/"oof"/condition/f"fold{fold}"
            for rec in json.loads((folder/"index.json").read_text()):
                sid,tracer=rec["ptid"],rec["tracer"];r=lookup[sid]
                key=(condition,sid,tracer);assert key not in seen;seen.add(key)
                assert r["test_fold"]==fold and rec["fold"]==fold and sha(rec["path"])==rec["sha256"]
                with np.load(r["cache"]) as z:real=z[tracer];mask=z["mask"];aff=z["affine"]
                im=nib.load(rec["path"]);pred=im.get_fdata(dtype=np.float32)
                assert pred.shape==real.shape and np.allclose(im.affine,aff,atol=1e-5)
                metrics=image_metrics(real,pred,brain=mask>0)
                brain=mask>0;brain_mse=np.mean((real[brain]-pred[brain])**2,dtype=np.float64)
                images.append(dict(ptid=sid,fold=fold,tracer=tracer,condition=condition,**metrics,
                                   brain_psnr=float(-10*np.log10(brain_mse)) if brain_mse>0 else np.inf))
                bad=invalid.get(sid,set())
                tv=apply_validity(regional(real,mask,labels),labels,bad);pv=apply_validity(regional(pred,mask,labels),labels,bad)
                for label,t,p in zip(labels,tv,pv):records.append(dict(condition=condition,ptid=sid,fold=fold,
                    tracer=tracer,region=label,physical_region=physical[int(label)],real=t,pred=p,unit="normalized uptake (arbitrary units)"))
    expected={(c,r["ptid"],t) for c in cfg["conditions"] for r in rows for t in TRACERS if r["has_"+t]}
    assert seen==expected
    d=pd.DataFrame(records);out=Path(cfg["report"])/"formal_evaluation";out.mkdir(exist_ok=False)
    d.to_csv(out/"regions_long.csv",index=False)
    pd.DataFrame(images).to_csv(out/"image_metrics.csv",index=False)
    subject=[];agreement_rows=[];region_tests=[];complete_cases=[]
    for tracer in TRACERS:
        q=d[d.tracer==tracer]
        pivot=q.pivot(index=["ptid","fold","region"],columns="condition",values="pred")
        real=q[q.condition=="Full"].set_index(["ptid","fold","region"]).real
        valid=real.notna() & pivot["Full"].notna() & pivot["No-Scores"].notna()
        real=real[valid];pivot=pivot.loc[valid]
        errors=pivot.sub(real,axis=0).abs();per_subject=errors.groupby(["ptid","fold"]).mean()
        delta=(per_subject["No-Scores"]-per_subject["Full"]).to_numpy();folds=per_subject.index.get_level_values("fold").to_numpy()
        observed,ci=paired_bootstrap([delta],folds,lambda z:z.mean())
        p=stats.permutation_test((delta,),lambda z:z.mean(),permutation_type="samples",n_resamples=10000,
                                 alternative="two-sided",random_state=20261017).pvalue
        subject.append(dict(tracer=tracer,n=len(delta),full_mean=float(per_subject.Full.mean()),
            no_scores_mean=float(per_subject["No-Scores"].mean()),delta=float(observed),ci_low=float(ci[0]),ci_high=float(ci[1]),p=float(p)))
        per_subject.to_csv(out/f"subject_roi_mae_{tracer}.csv")
        roi_counts=errors.groupby(["ptid","fold"]).size();roi_counts.to_csv(out/f"subject_roi_counts_{tracer}.csv")
        complete=per_subject.loc[roi_counts==len(labels)]
        if len(complete)>2:
            cd=(complete["No-Scores"]-complete.Full).to_numpy();cf=complete.index.get_level_values("fold").to_numpy()
            cv,cc=paired_bootstrap([cd],cf,lambda z:z.mean())
            complete_cases.append(dict(tracer=tracer,n=len(complete),delta=float(cv),ci_low=float(cc[0]),ci_high=float(cc[1])))
        import statsmodels.formula.api as smf
        demographic=pd.DataFrame([dict(ptid=r["ptid"],age=r["age"],sex=r["sex"],weight=r["weight"]) for r in rows])
        reg=per_subject.reset_index().merge(demographic,on="ptid",validate="one_to_one")
        reg["delta"]=reg["No-Scores"]-reg.Full;reg["age_centered"]=reg.age-reg.age.mean()
        for name,subset,formula in [("age_sex",reg,"delta ~ age_centered + C(sex) + C(fold)"),
                                     ("positive_weight",reg[reg.weight>0],"delta ~ age_centered + C(sex) + C(fold) + weight")]:
            fit=smf.ols(formula,data=subset).fit(cov_type="HC3");ci=fit.conf_int()
            pd.DataFrame(dict(term=fit.params.index,coefficient=fit.params.values,se=fit.bse.values,p=fit.pvalues.values,
                              ci_low=ci[0].values,ci_high=ci[1].values,n=int(fit.nobs))).to_csv(out/f"e1_gain_{tracer}_{name}_HC3.csv",index=False)
        for region in labels:
            mask_idx=real.index.get_level_values("region")==region;x=real[mask_idx].to_numpy();pred=pivot.loc[mask_idx]
            f=real.index.get_level_values("fold")[mask_idx].to_numpy()
            if len(x)<3:continue
            for c in cfg["conditions"]:
                yy=pred[c].to_numpy();metrics=agreement(x,yy)
                cal=stats.linregress(x,yy)
                agreement_rows.append(dict(tracer=tracer,region=int(region),condition=c,**metrics,
                    calibration_slope=float(cal.slope),calibration_intercept=float(cal.intercept)))
            a,b=pred.Full.to_numpy(),pred["No-Scores"].to_numpy();dr=abs(b-x)-abs(a-x)
            av,ac=paired_bootstrap([x,a,b],f,agreement_vector)
            names=["bias_full","bias_no_scores","delta_bias","ccc_full","ccc_no_scores","delta_ccc",
                   "icc_full","icc_no_scores","delta_icc"]
            for name,value,lo,hi in zip(names,av,ac[0],ac[1]):
                agreement_rows.append(dict(tracer=tracer,region=int(region),quantity=name,
                                           estimate=float(value),ci_low=float(lo),ci_high=float(hi)))
            dm,dc=paired_bootstrap([dr],f,lambda z:z.mean())
            pv=stats.permutation_test((dr,),lambda z:z.mean(),permutation_type="samples",n_resamples=10000,random_state=20261017).pvalue
            region_tests.append(dict(tracer=tracer,region=int(region),delta=float(dm),ci_low=float(dc[0]),ci_high=float(dc[1]),p=float(pv)))
    import statsmodels.stats.multitest as multi
    s=pd.DataFrame(subject);s["p_holm"]=multi.multipletests(s.p,method="holm")[1];s.to_csv(out/"primary.csv",index=False)
    r=pd.DataFrame(region_tests);r["q_bh_196"]=multi.multipletests(r.p,method="fdr_bh")[1];r.to_csv(out/"roi_delta.csv",index=False)
    pd.concat([r[(r.tracer==t)&r.region.isin(cfg["key_rois"][t])] for t in TRACERS]).to_csv(out/"prespecified_key_roi_delta.csv",index=False)
    pd.DataFrame(complete_cases).to_csv(out/"complete98_sensitivity.csv",index=False)
    pd.DataFrame(agreement_rows).to_csv(out/"agreement.csv",index=False)
    metric_contrasts=[]
    image_df=pd.DataFrame(images)
    for tracer in TRACERS:
        for metric in ["psnr","ssim","brain_psnr","brain_ssim"]:
            table=image_df[image_df.tracer==tracer].pivot(index=["ptid","fold"],columns="condition",values=metric)
            table=table.replace([np.inf,-np.inf],np.nan).dropna()
            delta=(table["No-Scores"]-table.Full).to_numpy();folds=table.index.get_level_values("fold").to_numpy()
            v,ci=paired_bootstrap([delta],folds,lambda z:z.mean())
            metric_contrasts.append(dict(tracer=tracer,metric=metric,n=len(delta),delta=float(v),ci_low=float(ci[0]),ci_high=float(ci[1])))
    pd.DataFrame(metric_contrasts).to_csv(out/"image_metric_contrasts.csv",index=False)


def clinical_only(cfg,rows):
    if not cfg["evaluation_laterality_gate_pass"] or not cfg["evaluation_mri_mask_gate_pass"]:
        raise RuntimeError("Clinical-only ROI evaluation blocked by anatomical label gate")
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import Ridge
    from sklearn.model_selection import GridSearchCV,KFold
    from common import SCORES
    meta=pd.read_csv(Path(cfg["report"])/"metadata.csv").set_index("Subject ID")
    labels=pd.read_csv(Path(cfg["report"])/"roi_labels.csv").region.to_numpy(int)
    output=[]
    invalid,physical=roi_context(cfg,labels)
    for fold in [1,2]:
        for tracer in TRACERS:
            rr=[r for r in rows if r["has_"+tracer]];y=[]
            for row in rr:
                with np.load(row["cache"]) as z:y.append(apply_validity(regional(z[tracer],z["mask"],labels),labels,invalid.get(row["ptid"],set())))
            y=np.asarray(y)
            x=np.asarray([[round(r["age"]),float(r["sex"]=="M"),r["weight"]]+meta.loc[r["ptid"],SCORES].tolist() for r in rr],float)
            train=np.array([r["test_fold"]!=fold for r in rr]);test=~train
            for condition,nfeatures in [("demographics-only",3),("clinical-only",8)]:
                for j,label in enumerate(labels):
                    valid=np.isfinite(y[:,j]);tr=train&valid;te=test&valid
                    model=GridSearchCV(make_pipeline(StandardScaler(),Ridge()),{"ridge__alpha":[.1,1.,10.,100.]},
                        cv=KFold(3,shuffle=True,random_state=42),scoring="neg_mean_absolute_error",n_jobs=1)
                    model.fit(x[tr,:nfeatures],y[tr,j]);pred=model.predict(x[te,:nfeatures])
                    for k,prediction in zip(np.flatnonzero(te),pred):output.append(dict(ptid=rr[k]["ptid"],fold=fold,
                        tracer=tracer,region=int(label),physical_region=physical[int(label)],condition=condition,real=y[k,j],pred=prediction,
                        alpha=model.best_params_["ridge__alpha"]))
    pd.DataFrame(output).to_csv(Path(cfg["report"])/"clinical_only_oof.csv",index=False)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["pipeline-check","collect","clinical-only"])
    p.add_argument("--config",type=Path,required=True);a=p.parse_args()
    cfg=load_config(a.config);check_frozen(cfg);rows=json.loads((Path(cfg["report"])/"cohort.json").read_text())
    rows=active_rows(cfg,rows)
    import torch
    torch.set_num_threads(4)
    if a.action=="pipeline-check":pipeline_check(cfg,rows)
    elif a.action=="collect":collect(cfg,rows)
    elif a.action=="clinical-only":clinical_only(cfg,rows)
