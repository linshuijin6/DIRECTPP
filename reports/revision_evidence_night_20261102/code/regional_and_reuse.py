"""Repackage already verified tables; no ROI metric or significance recomputation."""
from pathlib import Path
import json,hashlib,shutil
import pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102';D=OUT/'G4';D.mkdir(exist_ok=True)
sources=[]
def copy(source,dest):
    p=ROOT/source;t=OUT/dest;t.parent.mkdir(exist_ok=True,parents=True);shutil.copyfile(p,t)
    assert hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(t.read_bytes()).digest()
    sources.append(dict(source=source,output=dest,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
for name in ('supplementary_summary.tex','supplementary_paired.tex','summary_metrics.csv','paired_comparisons.csv','completion.json','completion_receipt_audit.json'):
    copy('reports/r3_11_brain_mask_metrics/run_20261102/'+name,'brain_mask/'+name)
copy('reports/r2_8_original_roi_stats/supplementary_tables/full_regional_statistics.csv','G4/historical_all98_allgroups.csv')
copy('reports/r2_8_original_roi_stats/supplementary_tables/overall_regional_statistics.csv','G4/historical_all98_overall.csv')
copy('reports/r3_5_effect_size/figure4_effect_sizes.csv','G4/historical_figure4_effect_sizes.csv')
copy('reports/r2_10_normalized_calibration/calibration_results.csv','G4/historical_OLS16.csv')
copy('reports/full_ot_medical_evidence/03a_per_roi_comparison.csv','G4/authorFull_OT_with_E1mask_roi_comparison.csv')
copy('reports/full_ot_medical_evidence/03b_regional_agreement.csv','G4/authorFull_OT_with_E1mask_agreement.csv')
copy('reports/full_ot_medical_evidence/03b_disease_contrast.csv','G4/authorFull_OT_with_E1mask_disease_contrast.csv')
copy('reports/full_ot_medical_evidence/03a_primary_paired_comparison.csv','G1/authorFull_OT_with_E1mask_primary_roi.csv')
for n in ('results.csv','summary.csv','verification.json'):
    if (ROOT/'experiments/r2_15_tau_adapter_ablation'/n).exists():copy('experiments/r2_15_tau_adapter_ablation/'+n,'G1/tau_'+n)
copy('experiments/r2_15_tau_adapter_ablation/tau_sensitivity.png','figures/G1_tau_sensitivity_reused.png')
for n in ('audit_alignment_results.json','audit_context_results.json','audit_infer_ablation_results.json'):
    copy('reports/full_tracer_conditioning_audit/'+n,'G1/'+n)
for n in ('bootstrap_metrics.csv','paired_comparisons.csv','delong_by_fold.csv'):
    copy('reports/r2_11_classification_3fold/statistical_comparison/'+n,'G5/existing_imaging_'+n)
copy('reports/r2_11_classification_3fold/final_summary/summary_metrics.csv','G5/existing_imaging_mean_sd.csv')
copy('reports/baseline_metrics_provenance_20261020/paper_figure2_values.csv','G7/historical84_values.csv')
hist=pd.read_csv(D/'historical_all98_overall.csv');ols=pd.read_csv(D/'historical_OLS16.csv')
merged=hist.merge(ols,on=['Tracer','ROI ID','ROI anatomical name'],suffixes=('','_OLS'),validate='one_to_one')
assert len(merged)==16
merged.to_csv(D/'historical_primary16_with_OLS.csv',index=False)
effects=pd.read_csv(D/'historical_figure4_effect_sizes.csv')
rows=[]
for r in effects.itertuples():
    s=hist[(hist.Tracer==r.tracer)&(hist['ROI ID']==r.roi_id)]
    assert len(s)==1
    rows.append(dict(panel=r.panel,panel_order=r.panel_order,**s.iloc[0].to_dict()))
panel=pd.DataFrame(rows);assert panel[(panel.panel=='E')&(panel.panel_order<=2)]['ROI ID'].tolist()==[28,60]
panel.to_csv(D/'historical_panels_CDEF_corrected_mapping.csv',index=False)
# Saved Full/OT MAE and agreement are present in distinct saved outputs; join keys retain model/source.
agree=pd.read_csv(D/'authorFull_OT_with_E1mask_agreement.csv');mae=pd.read_csv(D/'authorFull_OT_with_E1mask_roi_comparison.csv')
overall=agree[agree.scope=='overall'].copy();overall['MAE']=overall.apply(lambda r:mae[(mae.tracer==r.tracer)&(mae.roi_id==r.roi_id)].iloc[0]['full_mae_mean' if r.model=='Full' else 'ot_mae_mean'],axis=1)
overall['experiment_family']='W1 authorFull/OT predictions; E1 frozen mask/Real target protocol'
overall.to_csv(D/'authorFull_OT_overall_agreement_with_MAE.csv',index=False)
assert len(hist)==196 and len(pd.read_csv(D/'historical_all98_allgroups.csv'))==1176
assert len(effects)==20 and len(pd.read_csv(OUT/'G7/historical84_values.csv'))==21
(OUT/'audit/reused_source_manifest.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2))
(D/'REPORT.md').write_text('''# G4 regional supplementary evidence

Historical author-selected shuijin ROI CSVs are kept separate from W1 author-code Full/OT OOF evaluated with E1 frozen ROI masks and targets. All intensity quantities are normalized uptake (arbitrary units). No SUV/SUVR/Centiloid, equivalence or amyloid-status claims.

historical_all98_allgroups.csv contains1176 rows:2 tracers×98 ROI×6 original groups. historical_all98_overall.csv contains196 rows. Includes MAE, CCC, ICC(A,1), paired mean difference/t95%CI, Bland–Altman bias/LoA, raw paired p and BH q; each tracer×group has98 tests. historical_primary16_with_OLS.csv appends only the actually computed16 overall Pearson/OLS results; does not invent regression for other ROIs/groups. No verified historical OLS is available for the remaining180 overall combinations.

historical_figure4_effect_sizes.csv contains20 ROI combinations with Real/Syn AD−CN Cohen d (40 effects), disease-test p/q from392 pre-existing tests, corrected Figure4E IDs28/60. historical_panels_CDEF_corrected_mapping.csv uses these corrected labels while retrieving unchanged by-ID original regional statistics. Original R2-8 mapping mistakes remain unedited in protected source reports.

Historical overall median CCC is0.9745 AV45 and0.9450 FDG; overall98 ROI have no q<.05 Real−Syn mean differences. Across all6 groups only FDG ROI2021 original MCI has q=.0481365. These do not establish equivalence. Historical CSV source identity is fixed, but exact historical figure plotting identity remains unproven.

authorFull_OT_with_E1mask_agreement.csv contains existing overall/fold agreement values and Pearson/OLS; authorFull_OT_overall_agreement_with_MAE.csv joins saved per-ROI MAE for392 model×tracer×ROI rows. It is W1 author-code Full/OT checkpoint family (Full550ac2c4/f67e4a78), with E1 frozen masks/targets; it is not the E1 Full model (f9455190/fc69fa4e). E1-mask physical hemisphere names follow frozen correction and must not be replaced by historical segmenter names. Full/OT regional mean-bias CI was absent in the reused agreement file and is newly completed from saved regional means in authorFull_OT_complete_overall.csv; historical CIs are never borrowed. Four BH98 bias families are separate from saved model-comparison families. Full/OT ROI q in the paired-model comparison tests Full vs OT MAE, not Real vs Syn bias. W1 Full98-ROI evidence is present under this specific E1-mask/target evaluation protocol; do not conflate with canonical-target brain-mask metrics or historical ROI CSVs.

Brain-mask metrics are unchanged exact copies under ../brain_mask/. N=1597 FDG/1364 AV45, three models,16 tests in two separate Holm families of8. Mask union includes ventricular/CSF labels. Whole-volume N=1598/1365 is a distinct evaluation scope. The copied LaTeX drafts carry original footnotes and no masked recalculation was performed.
''')
print('COMPLETE regional reuse',len(sources),flush=True)
