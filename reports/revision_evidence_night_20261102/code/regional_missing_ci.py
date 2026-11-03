"""Add missing ROI mean-bias inference from saved regional means, never images."""
from pathlib import Path
import hashlib,json
import numpy as np,pandas as pd
from scipy import stats
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102/G4'
p=ROOT/'reports/full_ot_medical_evidence/03a_regional_uptake.csv';receipt=json.loads((p.parent/'03a_analysis_receipt.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==receipt['outputs'][p.name]['sha256']
raw=pd.read_csv(p,float_precision='round_trip');valid=raw[raw.roi_valid].copy()
assert len(raw)==290178 and len(valid)==289932 and not raw.duplicated(['ptid','fold','tracer','roi_id']).any()
rows=[]
for (tracer,roi),s in valid.groupby(['tracer','roi_id']):
    for model,col in [('Full','full_uptake'),('OT','ot_uptake')]:
        v=(s[col]-s.real_uptake).to_numpy();n=len(v);mean=v.mean();se=v.std(ddof=1)/np.sqrt(n);lo,hi=stats.t.interval(.95,n-1,loc=mean,scale=se)
        t,pvalue=stats.ttest_1samp(v,0)
        rows.append(dict(tracer=tracer,roi_id=roi,model=model,n=n,paired_mean_difference=mean,mean_ci_low=lo,mean_ci_high=hi,paired_t=t,p_raw=pvalue,family=f'{tracer}_{model}_bias_98',family_size=98,source='saved 03a regional means; E1 frozen Real+mask; W1 original_author/TracerOnly checkpoints'))
new=pd.DataFrame(rows)
for _,ii in new.groupby('family').groups.items():
    assert len(ii)==98
    pv=new.loc[ii,'p_raw'].to_numpy();order=np.argsort(pv);rank=np.arange(1,len(ii)+1);q=np.minimum(1,np.minimum.accumulate((pv[order]*len(ii)/rank)[::-1])[::-1]);result=np.empty(len(ii));result[order]=q;new.loc[ii,'q_BH98_bias']=result
old=pd.read_csv(OUT/'authorFull_OT_overall_agreement_with_MAE.csv');merged=old.merge(new,on=['tracer','roi_id','model','n'],validate='one_to_one')
assert len(merged)==392
np.testing.assert_allclose(merged.signed_bias_pred_minus_real,merged.paired_mean_difference,atol=1e-10,rtol=0)
merged.to_csv(OUT/'authorFull_OT_complete_overall.csv',index=False)
new.to_csv(OUT/'authorFull_OT_added_bias_inference.csv',index=False)
(OUT/'added_bias_validation.json').write_text(json.dumps(dict(status='PASS',rows=len(merged),raw_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),families={k:int((s.q_BH98_bias<.05).sum()) for k,s in new.groupby('family')},source_precision='saved regional CSV decimal precision; no voxel re-read',method='Student t95% mean-bias CI; two-sided paired t; BH98 separately per model/tracer; no equivalence'),indent=2))
print('COMPLETE added ROI CI',flush=True)
