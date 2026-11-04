from edit_registry import ROOT,WORK,apply
import re,shutil
import pandas as pd
base=ROOT/'reports/revision_evidence_night_20261102/G5';ev=[str((base/'REPORT.md').relative_to(ROOT)),'reports/r2_11_classification_3fold/final_summary/REPORT.md','reports/r2_11_classification_3fold/statistical_comparison/REPORT.md']
main=(ROOT/'manuscript/BMEF_main.tex').read_text();start=main.index(r'\subsection{Precise Prognostic');end=main.index(r'\section{Discussion}',start);old=main[start:end].rstrip()
new=r'''\subsection{Diagnostic Classification and MCI Stage Discrimination}
Classification used independent subject-level three-fold evaluation for AD versus CN ($n=470$), EMCI+LMCI versus CN ($n=741$), and EMCI versus LMCI ($n=436$). The MCI/CN task includes EMCI and LMCI, while MCI-U is excluded. The completed analysis comprises 63 imaging and 18 clinical fits (27 task--input configurations, three folds each). Results are reported as the equally weighted fold mean $\pm$ sample s.d., alongside conditional bootstrap 95\% CIs (Table~\ref{tab:classification_summary}). This is cross-sectional MCI stage discrimination, not future conversion or longitudinal prognostic prediction.

For AD/CN, MRI+Syn-FDG+Syn-AV45 achieved ACC $88.08\pm2.06\%$ and AUC $93.82\pm3.21\%$, compared with MRI-only ACC $79.56\pm6.20\%$ and AUC $87.02\pm5.44\%$ (Fig.~\ref{fig:5}A). The paired AUC difference was $+6.80$ percentage points (95\% CI $[+3.39,+10.22]$). For MCI/CN, MRI+Syn-both had ACC $65.45\pm1.64\%$ and AUC $69.46\pm1.34\%$, versus MRI-only $67.48\pm0.23\%$ and $71.59\pm1.80\%$; the paired AUC difference was $-2.13$ points (95\% CI $[-6.30,+2.10]$; Fig.~\ref{fig:5}B). Thus the synthetic combination did not improve all tasks.

For EMCI/LMCI, MRI+Syn-both had ACC $65.82\pm2.06\%$ and AUC $66.33\pm0.54\%$, compared with MRI-only $64.90\pm3.09\%$ and $62.81\pm2.50\%$. Its balanced-ACC difference favored the synthetic combination by $6.91$ points (95\% CI $[2.02,11.98]$), while the ACC and AUC difference CIs crossed zero (Fig.~\ref{fig:5}C). The Syn-minus-Real dual-PET AUC intervals crossed zero for all three tasks, which does not establish equivalence or interchangeability (Table~\ref{tab:classification_comparisons}).

Clinical-only AUC was $100.00\pm0.00\%$ for AD/CN, $98.93\pm0.70\%$ for MCI/CN, and $99.94\pm0.08\%$ for EMCI/LMCI. MRI+Clinical AUC was $99.17\pm0.96\%$, $93.07\pm6.10\%$, and $89.60\pm9.08\%$, respectively. MRI+Syn-both AUC was below both clinical baselines in each task, with the specified paired intervals below zero. These observations do not support independent incremental diagnostic value over the clinical variables, which include diagnosis-related scores and diagnosis-conditioned fills. The zero observed AD/CN error for Clinical-only and its degenerate empirical bootstrap CI do not establish perfect population generalization.

\begin{figure}[htbp]
\centering
\includegraphics[width=\textwidth]{figure_5}
\caption{\textbf{Cross-sectional classification under the revised three-fold protocol.} Panels A--C correspond to AD/CN, EMCI+LMCI/CN and EMCI/LMCI. Each panel compares nine input conditions: MRI; MRI+Real FDG; MRI+Syn FDG; MRI+Real AV45; MRI+Syn AV45; MRI+Real-both; MRI+Syn-both; Clinical-only; and MRI+Clinical. Values are equally weighted three-fold means; error bars show sample s.d. in percentage points, not 95\% CIs. ACC, AUC, SEN, SPE and balanced ACC are reported with their CIs in Table~\ref{tab:classification_summary}. The results do not demonstrate longitudinal prognosis, PET equivalence or benefit independent of diagnosis-related clinical inputs.}
\label{fig:5}
\end{figure}

Supplemental ROC curves use fold-wise averaging and pointwise confidence bands (Fig.~\ref{fig:classification_roc}). Paired DeLong tests are reported by outer fold with their raw and family-specific Holm-adjusted $p$ values (Table~\ref{tab:classification_delong}); they are not combined into a three-fold overall DeLong test. All comparisons are conditional on the fixed trained models and splits.
'''
apply('G5-RESULTS-AND-FIGURE5','manuscript/BMEF_main.tex',old,new,['R2-5','R2-11','R2-12','R2-16','R3-1','R3-3','R3-6','R3-7','R3-9'],['G5','G7'],ev,'Replace historical classification claims with completed 81-fit evidence, report adverse tasks and clinical baselines; figure source redraw follows',section='Results / classification and fig:5')
main=(ROOT/'manuscript/BMEF_main.tex').read_text();start=main.index(r'\subsubsection{Diagnosis and Prognostic');end=main.index(r'\subsection{Implementation Details}',start);old=main[start:end].rstrip()
new=r'''\subsubsection{Diagnostic Classification and MCI Stage Discrimination}
Image-based classifiers used a DenseNet121 backbone~\cite{huang2017densely} to evaluate three cross-sectional tasks: AD/CN; EMCI+LMCI/CN; and EMCI/LMCI. Positive classes were AD, EMCI+LMCI and LMCI, respectively. The task-specific cohorts contained 470, 741 and 436 participants, excluding MCI-U. Seven imaging conditions used MRI alone or MRI combined with real/synthetic FDG, AV45 or both tracers. Two further conditions were Clinical-only (an 18-parameter linear classifier) and MRI+Clinical. Both clinical baselines used the same eight clinical variables as the conditioning inputs; their information content is diagnosis-related and affected by historical group-conditioned filling.

All conditions used the same task-specific subject-level stratified three-fold outer splits (seed 42). Within each outer training set, a fixed stratified 15\% validation subset selected the checkpoint by validation ACC; the outer test was evaluated once after reloading that checkpoint. Imaging models used Adam (learning rate $10^{-4}$), batch size 5, up to 200 epochs and validation every two epochs. Clinical and combined-model settings are retained separately in the reproducibility records rather than assumed identical to every imaging model. Thresholded metrics use 0.5; AUC uses continuous positive-class scores. We report ACC, AUC, SEN, SPE and balanced ACC as equally weighted means across the three folds with sample s.d.

Bootstrap CIs use 5,000 paired resamples within each fold-by-class stratum (seed 20261102); each condition shares participant multiplicities within a resample. Metrics are recalculated by fold and averaged equally, rather than pooling differently trained model scores. Paired differences use the same resamples. The 95\% percentile intervals are marginal and unadjusted for simultaneous coverage; they condition on the trained models, class proportions and fixed splits and do not estimate retraining variability or eliminate dependence from overlapping training sets. DeLong tests compare matched predictions separately within each outer fold. The 18 original imaging comparisons and 36 additional clinical comparisons form separate Holm families; raw $p$ values are retained. No overall three-fold DeLong $p$ value is reported. ROC curves average fold-specific TPR over an FPR grid with step 0.005; pointwise 95\% bands use 2,000 fold-by-class resamples. The legend AUC is the mean empirical fold AUC, not pooled AUC or an integral of the finite grid.

Similar observed Real/Syn performance or a non-significant difference does not establish biological fidelity, equivalence or clinical interchangeability. Clinical-only and MRI+Clinical comparisons assess whether the reported synthetic-image classifier adds information beyond the provided clinical fields; they do not resolve label circularity introduced by diagnostic-group-conditioned simulated inputs.'''
apply('G5-CLASSIFICATION-METHODS','manuscript/BMEF_main.tex',old,new,['R2-5','R2-11','R2-12','R3-1','R3-6','R3-7','R3-9'],['G5'],ev+['experiments/classification_3fold/run.py'],'Merge actual 9-condition completed protocol with conditional uncertainty, explicit DeLong families and limitations',section='Methods / classification')
# Compact 27-condition table; no subject identifiers or pooled-score substitution.
a=pd.read_csv(base/'existing_imaging_bootstrap_metrics.csv');b=pd.read_csv(base/'clinical_summary.csv')
conditions=['mri','mri_real_fdg','mri_syn_fdg','mri_real_av45','mri_syn_av45','mri_real_both','mri_syn_both','clinical','mri_clinical'];names=['MRI','MRI+Real FDG','MRI+Syn FDG','MRI+Real AV45','MRI+Syn AV45','MRI+Real both','MRI+Syn both','Clinical-only','MRI+Clinical'];tasks=['ad_cn','mci_cn','emci_lmci'];tnames=['AD/CN','EMCI+LMCI/CN','EMCI/LMCI'];metrics=['ACC','AUC','SEN','SPE','balanced_ACC']
tex=r'''\begin{landscape}
\begingroup\small\setlength{\tabcolsep}{5pt}
\begin{longtable}{lccccc}
\caption{Three-fold classification results: mean $\pm$ sample s.d.; [conditional 95\% CI].}\label{tab:classification_summary}\\
\toprule
Input & ACC & AUC & SEN & SPE & Balanced ACC \\
\midrule\endfirsthead
\toprule Input & ACC & AUC & SEN & SPE & Balanced ACC \\\midrule\endhead
'''
for task,title in zip(tasks,tnames):
 tex+=r'\multicolumn{6}{l}{\textbf{'+title+r'}} \\'+ '\n'
 for condition,name in zip(conditions,names):
  vals=[]
  for metric in metrics:
   if condition not in ['clinical','mri_clinical']:
    r=a[(a.task==task)&(a.condition==condition)].iloc[0];v,sd,lo,hi=[r[metric+k] for k in ['_original_mean_pct','_original_fold_sd_pp','_ci_lower_pct','_ci_upper_pct']]
   else:
    r=b[(b.task==task)&(b.condition==condition)&(b.metric==metric)].iloc[0];v,sd,lo,hi=[100*r[k] for k in ['mean','sample_sd','ci_low','ci_high']]
   vals.append(r'\shortstack{'+f'{v:.2f} $\\pm$ {sd:.2f}'+r'\\'+f'[{lo:.2f}, {hi:.2f}]'+'}')
  tex+=name+' & '+' & '.join(vals)+r' \\'+'\n'
 tex+=r'\midrule'+'\n'
tex+=r'''\bottomrule
\end{longtable}
\noindent\footnotesize All metrics are percentages; s.d. is in percentage points. CIs use 5,000 paired fold-by-class bootstrap resamples of frozen predictions and three-fold equal weighting. Intervals are marginal, unadjusted and conditional on the fixed models and splits. Clinical-only AD/CN's zero empirical errors yield a degenerate [100,100] bootstrap interval, not a population guarantee. Clinical inputs include diagnosis-conditioned fills. Sample sizes are AD/CN=470, EMCI+LMCI/CN=741 and EMCI/LMCI=436; MCI-U is excluded.
\endgroup
\end{landscape}
'''
folder=ROOT/'manuscript/supplementary/tables';(folder/'classification_summary.tex').write_text(tex)
# Reuse completed comparison and DeLong fragments with publication labels, not rerun statistics.
inputs=[('S-N14_existing_imaging_paired_classification.tex','classification_imaging_comparisons.tex','tab:s-n14','tab:classification_comparisons','Existing imaging paired classification','Paired imaging classification differences'),('S-N15_new_clinical_paired_classification.tex','classification_clinical_comparisons.tex','tab:s-n15','tab:classification_clinical_comparisons','New clinical paired classification','Paired comparisons with clinical baselines'),('S-N16_classification_paired_delong_by_fold.tex','classification_delong.tex','tab:s-n16','tab:classification_delong','Classification paired DeLong by fold','Paired DeLong comparisons by outer fold')]
for src,dest,l1,l2,t1,t2 in inputs:
 p=ROOT/'reports/revision_evidence_night_20261102/tables'/src;s=p.read_text().replace(l1,l2).replace(t1,t2);(folder/dest).write_text(s)
roc=''
for task,title in zip(tasks,tnames):
 p=ROOT/f'reports/revision_evidence_night_20261102/figures/G5_ROC_{task}.png';shutil.copy2(p,ROOT/f'manuscript/figures/revision_roc_{task}.png')
 roc+=r'\includegraphics[width=0.32\textwidth]{revision_roc_'+task+'}\n'
tex=r'''\begin{figure}[p]\centering
'''+roc+r'''\caption{\textbf{Cross-sectional classification ROC curves for AD/CN, EMCI+LMCI/CN and EMCI/LMCI (left to right).} Curves average three fold-specific TPRs at a fixed FPR grid; shaded regions are pointwise conditional 95\% bootstrap bands, not simultaneous confidence bands. Legend AUC values are equally weighted empirical fold AUC means. Comparisons include MRI, MRI+Real both, MRI+Syn both, Clinical-only and MRI+Clinical. The clinical fields include diagnosis-related scores and historical group-conditioned fills; high clinical AUC is not evidence of independent synthetic-PET benefit.}
\label{fig:classification_roc}
\end{figure}
'''
(folder/'classification_roc.tex').write_text(tex)
p=ROOT/'manuscript/supplementary/supplementary.tex';old=r'\input{supplementary/tables/generation_cases}';new=old+'\n'+'\n'.join(r'\input{supplementary/tables/'+f+'}' for f in ['classification_summary','classification_imaging_comparisons','classification_clinical_comparisons','classification_delong','classification_roc'])
apply('G5-SUPPLEMENTARY-INPUTS','manuscript/supplementary/supplementary.tex',old,new,['R2-11','R2-12','R3-1','R3-7','R3-11'],['G5'],ev,'Add complete 27-condition mean/SD/CI table, paired comparisons, per-fold DeLong and existing ROC artifacts',section='Supplementary classification tables and ROC')
