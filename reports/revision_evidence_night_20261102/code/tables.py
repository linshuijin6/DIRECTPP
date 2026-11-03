"""Generate LaTeX/CSV supplementary drafts exclusively from reviewed result files."""
from pathlib import Path
import json,shutil
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102';DEST=OUT/'tables';DEST.mkdir(exist_ok=True)
index=[]
def esc(value):
    text=str(value)
    for a,b in [ ('\\',r'\textbackslash{}'),('&',r'\&'),('%',r'\%'),('$',r'\$'),('#',r'\#'),('_',r'\_'),('{',r'\{'),('}',r'\}'),('~',r'\textasciitilde{}'),('^',r'\textasciicircum{}')]:text=text.replace(a,b)
    return text.replace('±',r'\(\pm\)').replace('−','-').replace('–','--')
def number(x):
    if pd.isna(x):return 'NA'
    if isinstance(x,(float,np.floating)):return f'{x:.6g}'
    return str(x)
def export(id,title,frame,note,source,wide=False):
    stem=f'{id}_{title.lower().replace(" ","_").replace("/","_")}'
    frame.to_csv(DEST/(stem+'.csv'),index=False)
    headers=[esc(x) for x in frame.columns];n=len(headers)
    lines=['% Draft only. Requires longtable, booktabs; wide tables also pdflscape.','% Source: '+source]
    if wide:lines.append(r'\begin{landscape}')
    lines += [r'\begingroup',r'\footnotesize',r'\setlength{\tabcolsep}{4pt}',r'\begin{longtable}{'+'l'*n+'}',r'\caption{'+esc(title)+r'}\label{tab:'+id.lower()+r'}\\',r'\toprule',' & '.join(headers)+r' \\',r'\midrule',r'\endfirsthead',r'\toprule',' & '.join(headers)+r' \\',r'\midrule',r'\endhead',r'\bottomrule',r'\endfoot']
    for row in frame.itertuples(index=False,name=None):lines.append(' & '.join(esc(number(v)) for v in row)+r' \\')
    lines += [r'\end{longtable}',r'\noindent\parbox{\linewidth}{\footnotesize '+esc(note)+'}',r'\endgroup']
    if wide:lines.append(r'\end{landscape}')
    (DEST/(stem+'.tex')).write_text('\n'.join(lines)+'\n')
    index.append(dict(id=id,title=title,rows=len(frame),csv='tables/'+stem+'.csv',latex='tables/'+stem+'.tex',source=source,note=note))
def read(s):return pd.read_csv(OUT/s)

dist=read('G3/distribution_summary.csv');rows=[]
for (model,tracer),s in dist.groupby(['model','tracer'],sort=False):
    row={'Model':model,'Tracer':tracer.upper(),'N':int(s.n.iloc[0])}
    for m in ('ssim','psnr','mse','mae'):
        r=s[s.metric==m].iloc[0];row[m.upper()]=f'{r["mean"]:.6g} ± {r.sample_sd:.6g}'
    rows.append(row)
export('S-N01','Whole volume generation metrics',pd.DataFrame(rows),'Mean plus/minus sample SD. Whole-volume frozen OOF; FDG1598, AV451365. Full165, ClinicalUNet165, Swin200 MRI-only, Single165, TabularMLP165, TracerOnly165. SSIM unitless; PSNR dB; MSE squared and MAE unsquared normalized-intensity arbitrary units. Independent training realizations; reconstructed runs, not historical Figure2.','G3/distribution_summary.csv',True)
export('S-N02','Generation distributions',dist[['model','tracer','metric','n','median','p05','p95']],'Percentiles across frozen OOF subjects, not confidence limits. All intensities normalized, not SUV/SUVR.','G3/distribution_summary.csv')
pair=read('G3/paired_comparisons.csv');v=pair[['model','tracer','metric','n','mean_delta','ci_low','ci_high','cohen_dz','full_better_proportion','p_raw','p_holm']].copy();v['full_better_proportion']*=100
v=v.rename(columns={'full_better_proportion':'Full better pct'})
export('S-N03','Paired generation comparisons',v,'Delta=Full minus comparator; positive favors Full for SSIM/PSNR and negative for MSE/MAE. Cohen dz signed.10000 paired resamples within frozen folds, seed42; percentile95% CIs unadjusted. Two-sided paired t; separate Holm8-test family per comparator (2tracers x4metrics). ClinicalUNet statistics reused; TracerOnly t/dz reused and missing bootstrap supplemented. CIs do not estimate training/seed variability. MRI-only Swin inputs and endpoint differ.','G3/paired_comparisons.csv',True)
for id,src,title in [('S-N04','brain_mask/supplementary_summary.tex','Brain-mask metrics unchanged'),('S-N05','brain_mask/supplementary_paired.tex','Brain-mask paired comparisons unchanged')]:
    target=DEST/(id+'_brain_mask_reused.tex');shutil.copyfile(OUT/src,target)
    index.append(dict(id=id,title=title,rows=24 if id=='S-N04' else 16,csv='brain_mask/summary_metrics.csv' if id=='S-N04' else 'brain_mask/paired_comparisons.csv',latex=str(target.relative_to(OUT)),source='reports/r3_11_brain_mask_metrics/run_20261102',note='Exact copy. No masked recalculation. FDG1597/AV451364; SynthSeg union includes CSF; canonical target arrays identical across models; two Holm8 families.'))
h=read('G4/historical_all98_overall.csv')
cols=['Tracer','ROI ID','ROI anatomical name','N','MAE','CCC','ICC(A,1)']
export('S-N06','Historical98 ROI agreement',h[cols],'Author-selected shuijin historical ROI CSVs only. Normalized uptake arbitrary units; not W1 Full OOF. Exact figure plotting identity not fully recovered.','G4/historical_all98_overall.csv',True)
allh=read('G4/historical_all98_allgroups.csv')
cols=['Tracer','ROI ID','Diagnostic group','N','Mean paired difference (Syn - Real)','95% CI lower','95% CI upper','Raw paired t-test p','BH-FDR q']
export('S-N07','Historical98 ROI paired inference by group',allh[cols],'Student t95% paired-mean CI; Real/Syn matched subjects. BH98 within each tracer x original diagnostic group. MCI is the exact historical CSV label, not pooled EMCI/LMCI or automatically MCI-U. Non-significant q does not establish equivalence.','G4/historical_all98_allgroups.csv',True)
export('S-N08','Historical98 ROI Bland Altman',h[['Tracer','ROI ID','N','Bland-Altman bias','Bland-Altman lower LoA','Bland-Altman upper LoA']],'Bias=Syn-Real; limits=mean difference +/-1.96 sample SD, descriptive normal approximation, not CI. All normalized uptake arbitrary units.','G4/historical_all98_overall.csv')
ols=read('G4/historical_OLS16.csv');export('S-N09','Historical16 ROI Pearson OLS',ols[['Tracer','ROI ID','N','Pearson r','R-squared','OLS slope','Slope 95% CI lower','Slope 95% CI upper','OLS intercept','Intercept 95% CI lower','Intercept 95% CI upper']],'Overall only, Syn=intercept+slope xReal. Unadjusted marginal95% OLS intervals; asymmetric descriptive regression. No clinical SUV/SUVR calibration. No invented OLS values for other ROIs or diagnostic groups.','G4/historical_OLS16.csv',True)
effect=read('G4/historical_figure4_effect_sizes.csv');export('S-N10','Historical Figure4 disease effect sizes',effect[['panel','panel_order','tracer','roi_id','roi_name','N_AD','N_CN','d_real','d_syn','delta_d','r2_9_real_p','r2_9_real_q','r2_9_syn_p','r2_9_syn_q']],'AD-CN Cohen d uses pooled sample SD; distinct from paired Cohen dz. Original AD/CN labels. Figure4E first2 ROIs are Left/Right-VentralDC28/60. Existing disease-test BH98 per tracer xReal/Syn; no tests rerun. High agreement or non-significance does not prove equivalence or precise preservation.','G4/historical_figure4_effect_sizes.csv',True)
fullroi=read('G4/authorFull_OT_complete_overall.csv')
export('S-N11','Full OT OOF98 ROI agreement',fullroi[['tracer','roi_id','physical_name','model','n','MAE','ccc','icc_a1','pearson_r','calibration_slope','calibration_intercept']],'W1 Full/TracerOnly165 checkpoints; frozen E1 masks and Real regional arrays, not E1 generator. Physical hemisphere names follow frozen E1 mask correction. Saved MAE/CCC/ICC/Pearson/OLS reused. Invalid ROIs removed jointly, not zero-filled. Intensity is normalized uptake arbitrary units.','G4/authorFull_OT_complete_overall.csv',True)
export('S-N12','Full OT OOF98 ROI bias inference',fullroi[['tracer','roi_id','model','n','paired_mean_difference','mean_ci_low','mean_ci_high','loa_low','loa_high','p_raw','q_BH98_bias']],'New missing mean-bias inference from saved regional means, without reading or recalculating image metrics. Delta=prediction-Real. Student t95% mean CI, paired two-sided t, BH98 separately per tracer xmodel (4families). LoA are reused descriptive1.96SD limits. q here tests Real-Syn bias, not the existing Full-vs-OT MAE comparison.','G4/authorFull_OT_complete_overall.csv',True)

image=read('G5/existing_imaging_bootstrap_metrics.csv');cls=[]
for r in image.to_dict('records'):
    for m in ('ACC','AUC','SEN','SPE','balanced_ACC'):
        cls.append(dict(task=r['task'],condition=r['condition'],N=r['n_subjects'],metric=m,mean_pct=r[m+'_point_pct'],sample_sd_pp=r[m+'_original_fold_sd_pp'],ci_low_pct=r[m+'_ci_lower_pct'],ci_high_pct=r[m+'_ci_upper_pct']))
for r in read('G5/clinical_summary.csv').to_dict('records'):
    cls.append(dict(task=r['task'],condition=r['condition'],N=r['n_subjects'],metric=r['metric'],mean_pct=r['mean']*100,sample_sd_pp=r['sample_sd']*100,ci_low_pct=r['ci_low']*100,ci_high_pct=r['ci_high']*100))
export('S-N13','Classification27 conditions five metrics',pd.DataFrame(cls),'81completed fits:3tasks x9conditions x3folds. Metrics are equal-weight fold means and sample SD, not pooled AUC.5000 fold xclass paired bootstrap95% CIs, seed20261102, fixed models/splits. Positive classes AD, EMCI+LMCI, LMCI; MCI-U excluded. Degenerate100% empirical intervals do not prove zero population error. Clinical variables include diagnosis-related scales; independent clinical value not established.','G5/existing_imaging_bootstrap_metrics.csv;G5/clinical_summary.csv',True)
ip=[]
for r in read('G5/existing_imaging_paired_comparisons.csv').to_dict('records'):
    for m in ('ACC','AUC','SEN','SPE','balanced_ACC'):
        ip.append(dict(task=r['task'],target='mri_syn_both',reference=r['reference'],metric=m,delta_pp=r['delta_'+m+'_pp'],ci_low_pp=r['delta_'+m+'_ci_lower_pp'],ci_high_pp=r['delta_'+m+'_ci_upper_pp']))
export('S-N14','Existing imaging paired classification',pd.DataFrame(ip),'Original6 prespecified comparisons reused; Syn dual PET minus MRI orReal dual PET. Marginal95%5000 fold/class bootstrap CI, uncorrected for multiplicity. No overall DeLong claim and no equivalence inference.','G5/existing_imaging_paired_comparisons.csv',True)
cp=read('G5/clinical_paired_comparisons.csv')[['task','target','reference','metric','delta','ci_low','ci_high']];cp[['delta','ci_low','ci_high']]*=100;cp=cp.rename(columns={'delta':'delta_pp','ci_low':'ci_low_pp','ci_high':'ci_high_pp'})
export('S-N15','New clinical paired classification',cp,'12prespecified comparisons x5metrics. Delta target-reference; equal-weight3fold means.5000 paired fold/class bootstrap95% CI, seed20261102. Marginal intervals without simultaneous coverage. Does not estimate repeated-training variation.','G5/clinical_paired_comparisons.csv',True)
de=read('G5/existing_imaging_delong_holm.csv');drows=[]
for r in de.to_dict('records'):drows.append(dict(task=r['task'],fold=r['fold'],target=r['target'],reference=r['reference'],delta_AUC_pp=r['delta_AUC_pp'],p_raw=r['p_value_unadjusted_twosided'],p_Holm=r['p_holm_family18'],family='existing18'))
for r in read('G5/clinical_delong_by_fold.csv').to_dict('records'):drows.append(dict(task=r['task'],fold=r['fold'],target=r['target'],reference=r['reference'],delta_AUC_pp=r['delta_AUC']*100,p_raw=r['p_raw'],p_Holm=r['p_holm'],family='new36'))
export('S-N16','Classification paired DeLong by fold',pd.DataFrame(drows),'Two-sided paired DeLong only within each outer test fold. Holm separately for original18 and new36 test families. No pooled/combined/mean p-value or three-fold overall significance is asserted. Undefined variance would remain NA and count conservatively in family size.','G5/existing_imaging_delong_holm.csv;G5/clinical_delong_by_fold.csv',True)
e=read('G1_E1/paired_summary/contrasts.csv');export('S-N17','E1 fixed weight score removal',e[['tracer','metric','n','mean','ci_low','ci_high','p_permutation','p_holm_within_endpoint_two_tracers']],'Separate E1 Full checkpoints f9455190/fc69fa4e,165epochs; not W1 Full. Delta=No-Scores-Full, except output voxel MAE is nonnegative Full-vs-No-Scores difference. Primary ROI/brain MAE normalized units; PSNR dB; SSIM unitless.10000 within-fold bootstrap;10000 paired sign permutations for primary endpoints; Holm2 across tracers within endpoint. Fixed-weight inference sensitivity, not retrained ablation.','G1_E1/paired_summary/contrasts.csv',True)
export('S-N18','E1 score removal by fold',read('G1_E1/fold_differences.csv'),'Fold-wise descriptive differences and sample SD. No additional fold p-values or CIs invented; the formal overall CI is S-N17. Same metric directions and units as S-N17.','G1_E1/fold_differences.csv')
tau=read('G1/tau_results.csv');export('S-N19','Adapter sensitivity existing results',tau[['group','fold','tau','cross_weight','fdg_alignment','av45_alignment','heldout_fdg_alignment','heldout_av45_alignment','cross_tracer_similarity','total_loss','actual_tau_deviation']],'All10 existing adapter fits reused; no new optimization. Representation-layer measurements only; not generator quality or downstream clinical benefit. Tau is a squared soft target, not hard constraint or performance-optimized threshold. T000 removes cross-tracer penalty. Full source hashes are retained in G1/tau_results.csv.','experiments/r2_15_tau_adapter_ablation/results.csv',True)
hist=read('G7/historical84_values.csv');export('S-N20','Historical Figure2 absolute summaries',hist[['cohort','method','SSIM_percent','PSNR','MSE_percent','MAE_percent']],'21method/cohort rows x4metrics =84historical values. SSIM/MSE/MAE retain source percent scales, PSNR dB. OASIS is AV45 only. No recovered common per-subject final inputs: SD, CI and paired p unavailable. These are not the fixed W1 OOF experiment and are not paired with it. Original radar figure unchanged.','reports/baseline_metrics_provenance_20261020/paper_figure2_values.csv')
tim=read('G6/summary.csv').copy();tim['allocated_GiB']=tim.peak_allocated_bytes/2**30;tim['reserved_GiB']=tim.peak_reserved_bytes/2**30
export('S-N21','Full measured inference efficiency',tim[['tracer','n','parameters','mean_s','sample_sd_s','median_s','p05_s','p95_s','allocated_GiB','reserved_GiB']],'Full fold1 epoch165, real resident3D MRI[1,1,160,192,160], cached condition tokens, FP32, RTX409024GB.10warmup then50synchronized forward samples per tracer. One tracer per forward; excludes text encoding, preprocessing, I/O and transfers. Generator parameters only. Peak PyTorch allocated/reserved is not whole-card occupancy. FLOPs unavailable.','G6/summary.csv;G6/receipt.json',True)
export('S-N22','Classification split identity',read('G2/classification_outer_test_identity.csv'),'Fixed subject-level outer-test and internal validation roles; disjoint within task/fold. Actual source paths point to historical classification input assets. This table does not establish linkage to W1 Full checkpoint identities or longitudinal visit matching.','G2/classification_outer_test_identity.csv')
export('S-N23','Generator OOF split coverage',read('G2/generator_oof_coverage.csv'),'Frozen1857-subject two-fold manifest929/928; valid targets1598FDG/1365AV45. Subjectwise held-out identity verified. Unseeded training policy is separate from split seed42.','G2/generator_oof_coverage.csv')
(OUT/'SUPPLEMENTARY_TABLE_INDEX.md').write_text('# 补充表格草稿索引\n\nS-N编号为本次内部草稿编号，不修改正式supplementary.tex，不占用G8 Table S1。LaTeX为longtable片段，需longtable/booktabs；横向表另需pdflscape。未编译论文。\n\n'+pd.DataFrame(index)[['id','title','rows','csv','latex']].to_markdown(index=False)+'\n\n指标定义、多重比较族与来源边界随每份LaTeX表保留；完整可复算说明见各G组REPORT.md及code/PROTOCOL.md。\n')
(OUT/'audit/table_manifest.json').write_text(json.dumps(index,ensure_ascii=False,indent=2))
print('COMPLETE tables',len(index),flush=True)
