from edit_registry import ROOT,WORK,apply,amend
import pandas as pd
import shutil
folder=ROOT/'manuscript/supplementary/tables'
# The E1 fixed-weight experiment is a separate frozen checkpoint family.
p=ROOT/'reports/revision_evidence_night_20261102/tables/S-N17_e1_fixed_weight_score_removal.csv';d=pd.read_csv(p);print('E1 columns',list(d.columns))
labels={'roi_mae':'ROI MAE','brain_mae':'Masked MAE','psnr':'PSNR','ssim7':'SSIM (7)','ssim11':'SSIM (11)','full_vs_no_scores_voxel_mae':'Output difference'}
tex=r'''\begin{table}[p]\centering\small
\caption{\textbf{E1 fixed-weight score-removal sensitivity.} Differences are No-Scores minus Full, except the nonnegative output difference between predictions. This is a distinct E1 Full checkpoint family, not the reconstructed Full used in the generator-comparison tables.}
\label{tab:e1_score_removal}
\begin{tabularx}{\textwidth}{llrXrrr}
\toprule
Tracer & Metric & N & Mean $\Delta$ & CI lower & CI upper & Holm $p$ \\
\midrule
'''
for _,r in d.iterrows():
 h=r['p_holm_within_endpoint_two_tracers'];h='--' if pd.isna(h) else f'{h:.5g}'
 tex+=' & '.join([r.tracer.upper(),labels[r.metric],str(r['n']),f"{r['mean']:.6g}",f'{r.ci_low:.6g}',f'{r.ci_high:.6g}',h])+r' \\'+'\n'
tex+=r'''\bottomrule
\end{tabularx}
\par\smallskip\footnotesize
The MRI, tracer context and model weights are fixed; the eight-field patient token is replaced with a frozen Age+Sex+Weight token, not an empty token. No model is retrained. ROI/masked MAE use normalized-intensity units, PSNR is dB, and SSIM is unitless. CIs use 10,000 within-fold paired bootstrap resamples (seed 20261017). ROI and masked MAE are the primary endpoints: paired sign-permutation tests use 10,000 permutations and Holm correction across the two tracers separately within each endpoint. Other intervals are descriptive. The full-reference measurements were reused; whole-cohort Full predictions were not replayed anew. Nonzero output sensitivity and small error changes do not prove independent clinical value.
\end{table}
'''
(folder/'e1_score_removal.tex').write_text(tex)
src=ROOT/'reports/r2_16_demographic_stratification/supplementary_tables.tex';shutil.copy2(src,folder/'demographic_stratification.tex')
old=(WORK/'final_text/G1-RESULTS-CONDITIONING.tex').read_text().rstrip()
new=old+r'''

A separate E1 fixed-weight sensitivity analysis replaced the clinical-score portion of the patient prompt while retaining age, sex and weight, MRI, tracer and model parameters (Table~\ref{tab:e1_score_removal}). Removing scores increased ROI MAE by approximately 0.000036 for FDG and 0.000079 for AV45, with statistical support under the endpoint-specific two-tracer Holm families but very small absolute changes. SSIM increased while PSNR decreased, and the average absolute prediction change was approximately 0.001019/0.001105 for FDG/AV45. These observations show conditional output sensitivity; they are not a retrained No-Scores ablation or proof of independent diagnostic benefit.'''
amend('G1-RESULTS-CONDITIONING',new,comments=['R2-5','R3-1'],sources=['reports/revision_evidence_night_20261102/G1_E1/REPORT.md',str(p.relative_to(ROOT))],decision='Include completed E1 score-removal results under their own checkpoint identity and sensitivity-only scope')
old=(WORK/'final_text/G5-RESULTS-AND-FIGURE5.tex').read_text().rstrip()
new=old+r'''

Age ($<75$ versus $\geq75$ years) and sex were analyzed separately using existing classification predictions (Tables~\ref{tab:r2-16-ad-cn},\ref{tab:r2-16-mci-cn},\ref{tab:r2-16-emci-lmci}). For AD/CN, MRI+Syn-both minus MRI balanced-ACC differences ranged from 7.45 to 10.97 percentage points across the four subgroups. EMCI/LMCI point differences were positive in all four subgroups, including 9.64 points for age $\geq75$ (95\% CI $[1.23,18.05]$); MCI/CN did not show consistent gains. The subgroup intervals are marginal and unadjusted. These stratified descriptions do not remove demographic confounding or establish age/sex interactions.'''
amend('G5-RESULTS-AND-FIGURE5',new,comments=['R2-16'],sources=['reports/r2_16_demographic_stratification/REPORT.md','reports/r2_16_demographic_stratification/paired_comparisons.csv'],decision='Include completed author-confirmed age/sex subgroup findings without interaction/confounding-elimination claims')
old=(WORK/'final_text/G5-CLASSIFICATION-METHODS.tex').read_text().rstrip()
new=old+r'''

Demographic sensitivity analyses separately stratified recorded age at 75 years and sex (F/M), without crossing the strata or changing thresholds/checkpoints. Each task, fold, subgroup and true-class stratum was resampled 5,000 times (seed 20261103); seven imaging inputs shared resample multiplicities, and fold metrics were averaged equally. These unadjusted marginal subgroup CIs were not used to infer interactions. Recorded ages could not be verified as MRI-visit ages because the available demographic export lacked visit dates. Age and sex were not mutually adjusted, and clinical-score or residual within-group confounding was not eliminated.'''
amend('G5-CLASSIFICATION-METHODS',new,comments=['R2-16'],sources=['reports/r2_16_demographic_stratification/REPORT.md'],decision='Document actual subgroup protocol and conditioning/visit alignment limits')
q=ROOT/'manuscript/supplementary/supplementary.tex';old=r'\input{supplementary/tables/classification_roc}';new=old+'\n'+r'\input{supplementary/tables/e1_score_removal}'+'\n'+r'\input{supplementary/tables/demographic_stratification}'
apply('EVIDENCE-SENSITIVITY-TABLE-INPUTS',str(q.relative_to(ROOT)),old,new,['R2-5','R2-16','R3-1'],['G1','G5'],['reports/revision_evidence_night_20261102/G1_E1/REPORT.md','reports/r2_16_demographic_stratification/REPORT.md'],'Include finished sensitivity and subgroup evidence referenced by confirmed responses',section='Supplementary clinical score sensitivity and demographic stratification')
