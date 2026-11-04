from edit_registry import ROOT,WORK,apply
import re,shutil
main=(ROOT/'manuscript/BMEF_main.tex').read_text()
def para(prefix):return next(l for l in main.splitlines() if l.startswith(prefix))
ev=['reports/revision_evidence_night_20261102/G3/REPORT.md','reports/r3_11_brain_mask_metrics/run_20261102/REPORT.md','reports/revision_evidence_night_20261102/R3_11_final_figures/REPORT.md','rebuttal/BMEF_from_notion/BMEF审稿回复/G4修改正文 40c95d43b2dd8081b5b3ea02e06e0964.md']
old=para('We rigorously evaluated the multi-tracer')
new=r'''PET synthesis was evaluated using structural similarity (SSIM), peak signal-to-noise ratio (PSNR), mean squared error (MSE) and mean absolute error (MAE). Figure~\ref{fig:2} retains the historical comparisons with CycleGAN~\cite{zhu2017unpaired}, Swin-UNet~\cite{Cao2021swin}, segmentation-guided diffusion~\cite{konz2024anatomically}, 3D DDIM~\cite{song2021ddim,pinaya2023generative}, 3D rectified flow~\cite{Xing2022} and single-tracer DIReCT~\cite{liu2025direct}. Absolute historical aggregate values are given in Table~\ref{tab:historical_generation}; subject-level statistics were not recoverable for every historical method and are not reconstructed from these aggregates.'''
apply('G3-RESULTS-INTRO','manuscript/BMEF_main.tex',old,new,['R2-17','R3-10','R3-11','M14'],['G3'],ev,'Separate historical aggregates from new subject-level evidence and correct DDIM citation target',section='Results / generation introduction')
old=para('Models were trained on the ADNI dataset')
new='PET synthesis used two-fold ADNI evaluation; historical external evaluation used OASIS-3 AV45 only. The reconstructed OOF comparisons and their statistical protocols are reported separately from the historical Figure~\\ref{fig:2} summaries.'
apply('G3-EVALUATION-SCOPE','manuscript/BMEF_main.tex',old,new,['R2-3','R2-7','R3-11','R3-13'],['G3','G2'],ev,'Clarify PET synthesis two-fold protocol and AV45-only external scope',section='Results / generation evaluation scope')
old=para('On internal evaluation, DIReCT')
new=r'''The reconstructed OOF evaluation does not support a uniform advantage of Full over all alternatives (Tables~\ref{tab:whole_volume_generation},\ref{tab:paired_generation}). Full outperformed the clinically conditioned regression U-Net across the four whole-volume metrics for both tracers, while the magnitude of the AV45 MSE effect was small ($|d_z|=0.075$). Relative to TabularMLP, Full had higher SSIM but lower PSNR and higher MSE for both tracers; MAE did not differ after the specified Holm correction. TracerOnly had better FDG results on all four metrics and higher AV45 SSIM than Full. Single-tracer DIReCT had higher FDG SSIM, whereas Full had better FDG PSNR/MSE and AV45 SSIM. These independently trained models differ in initialization, conditioning or implementation, so the comparisons do not isolate a single causal component or prove multi-tracer synergy.

In the masked evaluation (Tables~\ref{tab:r3_11_masked_summary},\ref{tab:r3_11_masked_paired}), Full had higher mean SSIM/PSNR and lower mean MSE/MAE than Clinical U-Net and MRI-only Swin-UNETR for both tracers; all 16 predefined comparisons met $p_{\mathrm{Holm}}<0.05$ within their two separate eight-test families. The masked cohort contained 1,597 FDG and 1,364 AV45 observations after the existing MRI/mask QC exclusion. For Clinical U-Net AV45 MSE/MAE, the standardized effects were small ($|d_z|=0.071/0.076$), and only 56.4--57.8\% of subjects favored Full. Thus statistical support does not imply uniform individual or clinical benefit. Full/Clinical U-Net used epoch 165, while MRI-only Swin-UNETR used epoch 200; information and training endpoints differ.

Separate whole-volume and masked summaries are retained because background exclusion changes the metric definitions and values. Supplemental FDG and AV45 examples use the median, 10th-percentile and worst QC-passed subjects selected by saved whole-volume SSIM, and show MRI, real PET, synthetic PET and absolute-error maps (Figs.~\ref{fig:cases_fdg},\ref{fig:cases_av45}).'''
apply('G3-RESULTS-COMPARISONS','manuscript/BMEF_main.tex',old,new,['R2-17','R3-8','R3-9','R3-10','R3-11','R3-12','R3-15'],['G3','G1'],ev,'Report supported mean effects and adverse comparisons, distinguish mask protocol and independent initialization',section='Results / reconstructed generation evidence')
old=para('External validation on the OASIS cohort')
new=r'''The historical OASIS-3 evaluation reports AV45 PSNR of 26.79 dB, compared with 28.09 dB for historical internal ADNI AV45 evaluation (Fig.~\ref{fig:2}A; Table~\ref{tab:historical_generation}). The cross-dataset examples in Fig.~\ref{fig:2}C illustrate CN/AD AV45 synthesis. These aggregate and illustrative results do not provide subject-level confidence intervals, FDG external evidence or external MCI-stage validation, and should not be combined with the reconstructed OOF statistics as a single experiment.'''
apply('G3-EXTERNAL-RESULTS','manuscript/BMEF_main.tex',old,new,['R2-7','R3-11','R3-13'],['G3','G7'],ev,'Restrict historical external claims and do not fabricate uncertainty for unrecovered subject outputs',section='Results / external AV45 synthesis')
old=next(m.group(0) for m in re.finditer(r'\\begin\{figure\}.*?\\end\{figure\}',main,re.S) if r'\label{fig:2}' in m.group(0))
new=r'''\begin{figure}[htbp]
\centering
\includegraphics[width=0.85\textwidth]{figure_2}
\caption{\textbf{Historical PET synthesis comparisons and illustrative examples.} (A) Radar plots summarize the historical aggregate SSIM, MSE, MAE and PSNR values for ADNI FDG/AV45 and OASIS-3 AV45. Metric values are displayed relative to the best value among methods; absolute aggregate values and scaling conventions are listed in Table~\ref{tab:historical_generation}. These aggregates are separate from the reconstructed OOF and masked analyses. (B) Illustrative ADNI CN, MCI and AD examples with MRI, competing synthesis outputs and real PET; paired subrows show FDG and AV45. (C) Historical CN/AD OASIS-3 examples are limited to AV45. The historical examples were not selected by the supplemental quantile-based procedure and do not establish population-level superiority.}
\label{fig:2}
\end{figure}'''
apply('G3-FIGURE2-CAPTION','manuscript/BMEF_main.tex',old,new,['R2-7','R3-11','R2-17'],['G3'],ev,'Clearly label historical aggregates and non-quantile illustrative case selection',section='fig:2 caption')
old=para('To rigorously benchmark the performance')
new='To benchmark DIReCT$++$, six historical baseline methods were adapted to PET synthesis as described below. Reconstructed comparisons additionally used Clinical Regression 3D U-Net, MRI-only Swin-UNETR, TracerOnly, TabularMLP and separately trained Single models. Their input conditions, training endpoints and implementation differences are retained; the comparisons are not treated as uniformly optimized, equal-budget or single-component ablations.'
apply('G3-BASELINE-SCOPE','manuscript/BMEF_main.tex',old,new,['R2-17','R3-9','R3-10','R3-15'],['G3'],ev,'Remove unsupported claim of identical hyperparameter optimization and all-variable fairness',section='Competing Methods / scope')
old=next(l.strip() for l in main.splitlines() if l.strip().startswith(r'\item \textbf{SegGuidedDiff}'))
new=r'\item \textbf{SegGuidedDiff}~\cite{konz2024anatomically}: A segmentation-guided diffusion model adapted for 2D slice-based PET synthesis using anatomical segmentation maps as guidance.'
apply('G3-SEGGUIDED-2D','manuscript/BMEF_main.tex',old,new,['R3-10'],['G3'],ev,'Apply confirmed 2D baseline clarification',section='Competing Methods / SegGuidedDiff')
old=next(l.strip() for l in main.splitlines() if l.strip().startswith(r'\item \textbf{3D Rectified Flow'))
new=old.replace(' This ablation model isolates the contribution of our BiomedCLIP-enhanced guidance module.','')
apply('G3-RF-BASELINE','manuscript/BMEF_main.tex',old,new,['R3-9'],['G3'],['rebuttal/BMEF_from_notion/BMEF审稿回复/G5修改正文 40d95d43b2dd8050b224d3f96fa506f8.md'],'Apply same final R3-9/G5 scheme once at shared baseline position',section='Competing Methods / 3D RF')
old=next(l.strip() for l in main.splitlines() if l.strip().startswith(r'\item \textbf{DIReCT (Single'))
new=r'''\item \textbf{DIReCT (Single-Modality Variant)}~\cite{liu2025direct}: Separate tracer-specific models synthesize one PET tracer per forward pass, while DIReCT$++$ uses a shared network conditioned on the target tracer. The comparison includes other implementation differences and does not isolate joint-training synergy.'''
apply('G3-SINGLE-BASELINE','manuscript/BMEF_main.tex',old,new,['R3-9','R3-15'],['G3'],ev,'Merge R3-9 correction of simultaneous output and unsupported synergy inference',section='Competing Methods / Single')
old=next(l.strip() for l in main.splitlines() if l.strip().startswith(r'\item \textbf{3D DDIM}'))
new=old.replace('\\cite{Graf2023}',r'\cite{song2021ddim,pinaya2023generative}').replace('included to assess DIReCT$++$’s computational efficiency and sampling quality relative to accelerated diffusion approaches','implemented using a 3D diffusion-model U-Net and a DDIM scheduler for the historical synthesis comparison')
apply('G3-DDIM-REFERENCE','manuscript/BMEF_main.tex',old,new,['M14','R2-18'],['G3'],ev,'Align baseline description and reference with actual DDIM implementation; no equal-protocol runtime claim',section='Competing Methods / 3D DDIM')
main=(ROOT/'manuscript/BMEF_main.tex').read_text();old='\\end{enumerate}\n\n\\subsection{Statistical Analysis}';assert old in main
new=r'''\end{enumerate}

The 3D Swin-UNETR was adapted to PET intensity regression with a continuous single-channel output and MSE loss, using MRI alone. Clinical Regression 3D U-Net used MRI and the same eight clinical variables with target-tracer information, providing a clinically matched framework comparison. TracerOnly excluded patient-specific conditioning while retaining target-tracer guidance; TabularMLP replaced the clinical text representation with a structured-variable encoder. Separate Single models were trained per tracer. The principal comparison endpoint was epoch 165, except the prespecified Swin-UNETR endpoint of epoch 200. These independently initialized training runs were not designed to estimate variability over training seeds or to isolate every module as a single-factor causal ablation.

\subsection{Statistical Analysis}
\subsubsection{Image-Quality Evaluation}
Whole-volume metrics include background; masked metrics use the frozen SynthSeg nonzero-label union, which includes ventricles and CSF and is not a pure brain-parenchymal mask. MSE/MAE average squared/absolute errors within that mask, and PSNR uses data range 1. Masked 3D SSIM uses a Gaussian $7\times7\times7$ kernel ($\sigma=1.5$) and averages only centers whose complete window lies inside the mask; outside-mask voxels were not set to zero and included in a whole-image SSIM average. The masked comparison uses identical target and mask arrays across models. The existing MRI/mask QC exclusion removes one subject per tracer, yielding FDG $n=1,597$ and AV45 $n=1,364$; this exclusion is specific to the masked analysis and case selection and is not imposed on the classification cohort.

Metrics are reported as across-subject mean $\pm$ sample s.d. Paired two-sided $t$-tests and 10,000 paired bootstrap resamples stratified by held-out fold (seed 42) assess the frozen generation predictions. For each model comparison, Holm correction covers eight tests (two tracers $\times$ four metrics); bootstrap 95\% percentile CIs are unadjusted. Whole-volume and masked results use their respective subject sets and target protocols. These intervals do not estimate retraining or split variability. Supplemental cases are selected within each tracer's QC-passed cohort by saved whole-volume SSIM: nearest subject to the median or 10th percentile (linear quantiles), or the minimum for the worst case; ties are resolved by stable participant-ID ordering, without visual selection.'''
apply('G3-IMAGE-QUALITY-METHODS','manuscript/BMEF_main.tex',old,new,['R2-17','R3-9','R3-10','R3-11','R3-12'],['G3'],ev,'Combine clinical-matched baseline scope, mask definitions, paired statistics, QC denominators and frozen nonvisual case selection',section='Competing Methods / details; Image-Quality Evaluation')
# Adopt source-backed, already validated fragments while giving publication labels/captions.
folder=ROOT/'manuscript/supplementary/tables'
tables=[('S-N01_whole_volume_generation_metrics.tex','whole_volume_generation.tex','tab:s-n01','tab:whole_volume_generation','Whole volume generation metrics','Whole-volume OOF generation metrics (mean $\\pm$ sample s.d.)'),('S-N03_paired_generation_comparisons.tex','paired_generation.tex','tab:s-n03','tab:paired_generation','Paired generation comparisons','Paired whole-volume generation comparisons'),('S-N20_historical_figure2_absolute_summaries.tex','historical_generation.tex','tab:s-n20','tab:historical_generation','Historical Figure2 absolute summaries','Absolute historical Figure 2 summary values')]
for src,dest,oldlab,newlab,oldtitle,newtitle in tables:
 s=(ROOT/'reports/revision_evidence_night_20261102/tables'/src).read_text().replace(oldlab,newlab).replace(oldtitle,newtitle)
 s=s.replace('% Draft only. Requires longtable, booktabs; wide tables also pdflscape.','% Source-backed publication fragment; source records retained independently.')
 (folder/dest).write_text(s)
for src,dest in [('supplementary_summary.tex','masked_summary.tex'),('supplementary_paired.tex','masked_paired.tex')]:
 s=(ROOT/'reports/r3_11_brain_mask_metrics/run_20261102'/src).read_text();(folder/dest).write_text(s)
# Reuse existing final cases, without image edits or regenerated statistics.
figdir=ROOT/'manuscript/figures'
for tracer in ['FDG','AV45']:
 src=ROOT/f'reports/revision_evidence_night_20261102/R3_11_final_figures/R3_11_{tracer}_cases.pdf';shutil.copy2(src,figdir/f'revision_cases_{tracer.lower()}.pdf')
case=''
for tracer in ['fdg','av45']:
 case+=r'''\begin{figure}[p]
\centering
\includegraphics[width=\textwidth]{revision_cases_TRACER}
\caption{\textbf{TRACERUP synthesis in median, 10th-percentile and worst QC-passed cases.} Rows follow the frozen whole-volume SSIM selection; columns show MRI, real PET, synthetic PET and absolute-error maps. PET intensities and errors use the displayed [0,1] normalized-intensity scales. Selection is within the existing QC-passed set, without new exclusions or visual replacement; rankings use whole-volume SSIM rather than masked SSIM.}
\label{fig:cases_TRACER}
\end{figure}
'''.replace('TRACERUP',tracer.upper()).replace('TRACER',tracer)
(folder/'generation_cases.tex').write_text(case)
p=ROOT/'manuscript/supplementary/supplementary.tex';anchor=r'\input{supplementary/tables/regional_effect_sizes}'
new=anchor+'\n'+'\n'.join(r'\input{supplementary/tables/'+f+'}' for f in ['historical_generation','whole_volume_generation','paired_generation','masked_summary','masked_paired','generation_cases'])
apply('G3-SUPPLEMENTARY-INPUTS','manuscript/supplementary/supplementary.tex',anchor,new,['R2-17','R3-9','R3-10','R3-11','R3-12'],['G3'],ev,'Reuse completed source-backed table/case artifacts, preserving numerical protocols and separate historical/reconstructed identities',section='Supplementary generation tables and cases')
