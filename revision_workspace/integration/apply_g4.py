from edit_registry import ROOT,WORK,apply
import re,json
import pandas as pd
candidates=json.loads((ROOT/'revision_workspace/index/revision_candidates.json').read_text())
g4=next(p for p in (ROOT/'rebuttal/BMEF_from_notion/BMEF审稿回复').glob('G4修改正文*.md'))
ls=g4.read_text().splitlines()
def fenced(marker):
 t='\n'.join(ls[marker:]).lstrip();return re.match(r'```[^\n]*\n(.*?)\n```',t,re.S).group(1)
ev=[str(g4.relative_to(ROOT)),'reports/r2_8_original_roi_stats/REPORT.md','reports/r2_10_normalized_calibration/REPORT.md','reports/r3_5_effect_size/REPORT.md']
main=(ROOT/'manuscript/BMEF_main.tex').read_text()
for idx in range(1,8):
 r=next(x for x in candidates if x['id']==f'V{idx:03}');old=fenced(r['original_marker']);new=fenced(r['revised_marker'])
 if idx==1:
  first=r'''To assess regional uptake patterns, the corresponding T1-weighted MRI scans were parcellated using SynthSeg~\cite{synthseg}, and the resulting Desikan--Killiany and \textit{aseg} ROI masks were applied to spatially aligned real and synthetic PET images. '''
  new=first+new[new.index('This approach yielded'):]
  new=new.replace('demonstrating strong regional consistency between synthetic and real images, as well as clear distinctions between syntheses from different diagnostic groups','illustrating regional patterns in these selected cases')
 if idx==2:
  new += ' Figure~\\ref{fig:4}A,B uses the pooled available subjects without diagnostic-group stratification; panels C--F compare AD and CN only.'
 if idx==3:
  new += ' Non-significant mean differences do not establish formal equivalence or clinical interchangeability. These historical regional-CSV results are separate from the reconstructed Full generation comparisons.'
 if idx==4:
  new += r''' The AD--CN comparison illustrates representative differences between two diagnostic states rather than all diagnostic-group contrasts. MCI was evaluated separately through MCI-versus-CN and EMCI-versus-LMCI classification (Fig.~\ref{fig:5}B,C); the regional paired analysis also includes the original MCI categories.'''
 comments={1:['R2-8','R3-5','M3','M7'],2:['R2-8','M5','M18'],3:['R2-8','R2-10','R3-4'],4:['R2-9','R3-5','M18'],5:['R2-8','R2-10','R3-4','M5'],6:['R2-9','R3-5'],7:['R2-8','R2-9','R3-5']}[idx]
 apply(f'G4-CORE-{idx}','manuscript/BMEF_main.tex',old,new,comments,['G4'],ev,'Adopt G4 explicitly merged core; preserve M7 MRI masking, M18 scope and non-equivalence limits where overlapping',section=r['location'],candidates=r['id'])
main=(ROOT/'manuscript/BMEF_main.tex').read_text();old=next(l for l in main.splitlines() if l.startswith('To evaluate the clinical validity of synthesized PET'))
new=r'''Regional analysis used 98 SynthSeg ROIs defined on T1-weighted MRI. Representative regions shown in Fig.~\ref{fig:4}C,D were selected for disease-related comparisons. FDG regions included the bilateral hippocampus, isthmus cingulate cortex and supramarginal gyrus (atlas labels \texttt{Left-Hippocampus}, \texttt{Right-Hippocampus}, and the \texttt{ctx-lh-}/\texttt{ctx-rh-} labels with suffixes \texttt{isthmuscingulate} and \texttt{supramarginal})~\cite{mosconi2005reduced,he2015meta,strom2022cortical}. AV45 regions included bilateral precuneus and inferior, middle, superior and transverse temporal gyri (the corresponding \texttt{ctx-lh-}/\texttt{ctx-rh-} labels)~\cite{wong2010in}. Atlas-defined names are used rather than the ambiguous temporoparietal-junction label.'''
apply('G4-ROI-NAMES','manuscript/BMEF_main.tex',old,new,['M6','M13','M7'],['G4'],ev+['rebuttal/BMEF_from_notion/BMEF审稿回复 3d295d43b2dd8300b74601d792205677.md'],'Use explicitly merged M6/M13 atlas labels and intended citations; bibliography verification follows',section='Regional Group-Wise Comparison / ROI definitions')
# Extract final explicitly merged Figure 4 and S1--S6 candidates, whose payloads have no fences.
r=next(x for x in candidates if x['id']=='V015');tail='\n'.join(ls[r['revised_marker']:]);new=re.search(r'\\begin\{figure\}.*?\\end\{figure\}',tail,re.S).group(0)
new=new.replace('Statistical significance was assessed for each region.','Panels A,B summarize the pooled available subjects without diagnostic stratification. Non-significant differences are not evidence of equivalence.')
main=(ROOT/'manuscript/BMEF_main.tex').read_text();old=next(x.group(0) for x in re.finditer(r'\\begin\{figure\}.*?\\end\{figure\}',main,re.S) if r'\label{fig:4}' in x.group(0))
apply('G4-FIGURE4-CAPTION','manuscript/BMEF_main.tex',old,new,['R2-9','R3-5','M18','M19'],['G4'],ev,'Adopt explicitly merged M19 caption with pooled-subject and non-equivalence clarification; actual artwork pending source-based revision',section='fig:4 caption',candidates='V015')
# Figure 3 caption keeps layout but avoids extrapolation from representative cases.
main=(ROOT/'manuscript/BMEF_main.tex').read_text();old=next(x.group(0) for x in re.finditer(r'\\caption\{.*?\\label\{fig:3\}',main,re.S) if 'Detailed regional visualization' in x.group(0))
# A non-greedy match can begin at an earlier caption; keep only the last caption start.
old=old[old.rfind('\\caption{'):]
new=old.replace('Each row corresponds to a distinct brain region, demonstrating strong regional consistency between synthetic and real PET, and clear differences between diagnostic groups.','Each row corresponds to a distinct brain region. Displayed uptake values are arbitrary units after per-image min--max normalization, without anatomical reference-region normalization. These selected cases illustrate regional appearance and do not establish population-level agreement or clinical SUV/SUVR calibration.')
apply('G4-FIGURE3-CAPTION','manuscript/BMEF_main.tex',old,new,['R3-5','M19','R2-10'],['G4'],ev,'Normalize quantitative meaning and avoid population claims from two cases',section='fig:3 caption')
r=next(x for x in candidates if x['id']=='V016');tail='\n'.join(ls[r['revised_marker']:]);newfigs=re.findall(r'\\begin\{figure\}.*?\\end\{figure\}',tail,re.S);assert len(newfigs)==6
for i,new in enumerate(newfigs,1):
 p=ROOT/'manuscript/supplementary/supplementary.tex';txt=p.read_text();old=next(m.group(0) for m in re.finditer(r'\\begin\{figure\}.*?\\end\{figure\}',txt,re.S) if f'{{supplementary_figure_{i}}}' in m.group(0))
 apply(f'G4-SUPP-FIGURE-{i}','manuscript/supplementary/supplementary.tex',old,new,['M19','R3-5'],['G4'],ev,'Adopt G4 modification17 normalization clarification; plot-axis correction pending artwork stage',section=f'Supplementary figure {i}')
# Build exactly the 16 primary combinations, not the grouped primary-region CSV.
p1=ROOT/'reports/r2_8_original_roi_stats/supplementary_tables/overall_regional_statistics.csv';p2=ROOT/'reports/r2_10_normalized_calibration/calibration_results.csv';p3=ROOT/'reports/r3_5_effect_size/figure4_effect_sizes.csv'
a=pd.read_csv(p1);b=pd.read_csv(p2);assert len(b)==16 and not b.duplicated(['Tracer','ROI ID']).any()
d=b.merge(a,on=['Tracer','ROI ID','ROI anatomical name','N'],validate='one_to_one');assert len(d)==16 and (d['Diagnostic group']=='overall').all()
# Supplementary 16-row table contains all required fields; linebreaks within cells keep it legible.
def num(v,n=4):return f'{v:.{n}f}'
def ci(v,lo,hi,n=4):return r'\shortstack{'+num(v,n)+r'\\{}['+num(lo,n)+', '+num(hi,n)+']}'
def roi(t):return t.replace('ctx-lh-','L ').replace('ctx-rh-','R ').replace('-',' ')
tex=r'''\begin{landscape}
\begin{table}[p]
\caption{\textbf{Regional normalized uptake agreement and descriptive regression for the 16 representative tracer--ROI combinations in Figure~\ref{fig:4}A,B.} Overall cohorts from the author-designated historical ROI CSVs; N can vary by ROI.}
\label{tab:regional_agreement}
\centering\scriptsize\setlength{\tabcolsep}{2pt}
\resizebox{\linewidth}{!}{\begin{tabular}{llrccccccccc}
\toprule
Tracer & ROI (ID) & N & Mean diff. [95\% CI] & MAE & CCC & ICC(A,1) & BA bias [95\% LoA] & $p$ & $q$ & OLS slope [95\% CI] & Intercept [95\% CI] \\
\midrule
'''
for _,r in d.iterrows():
 vals=[r['Tracer'],roi(r['ROI anatomical name'])+f" ({r['ROI ID']})",str(int(r['N'])),ci(r['Mean paired difference (Syn - Real)'],r['95% CI lower'],r['95% CI upper'],5),num(r['MAE']),num(r['CCC']),num(r['ICC(A,1)']),ci(r['Bland-Altman bias'],r['Bland-Altman lower LoA'],r['Bland-Altman upper LoA']),num(r['Raw paired t-test p']),num(r['BH-FDR q']),ci(r['OLS slope'],r['Slope 95% CI lower'],r['Slope 95% CI upper']),ci(r['OLS intercept'],r['Intercept 95% CI lower'],r['Intercept 95% CI upper'])]
 tex+=' & '.join(vals)+r' \\'+'\n'
tex+=r'''\bottomrule
\end{tabular}}
\par\smallskip\footnotesize
Differences and Bland--Altman (BA) bias are synthetic minus real uptake (arbitrary units after per-image min--max normalization). Mean-difference confidence intervals and individual BA limits of agreement are distinct. CCC is Lin's concordance correlation and ICC(A,1) is a two-way absolute-agreement single-measure coefficient. Paired two-sided $t$-test $p$ values are raw; BH-FDR $q$ values use all 98 ROIs within each tracer's overall cohort. OLS regresses synthetic on real uptake and gives unadjusted descriptive 95\% CIs. Non-significant differences and slopes close to one do not establish equivalence, clinical SUV/SUVR calibration or interchangeable biological measurements.
\end{table}
\end{landscape}
'''
path=ROOT/'manuscript/supplementary/tables/regional_agreement.tex';assert not path.exists();path.write_text(tex)
e=pd.read_csv(p3);assert len(e)==20
tex=r'''\begin{table}[p]
\caption{\textbf{AD--CN regional effect sizes and BH-FDR-adjusted comparisons for Figure~\ref{fig:4}C--F.} Cohen's $d$ is AD minus CN divided by the pooled within-group sample s.d.}
\label{tab:regional_effect_sizes}
\centering\scriptsize\setlength{\tabcolsep}{3pt}
\begin{tabularx}{\textwidth}{llXrrrrrr}
\toprule
Panel & Tracer & ROI (ID) & $N_{AD}$ & $N_{CN}$ & Real $d$ & Syn $d$ & Real $q$ & Syn $q$ \\
\midrule
'''
def sci(v):
 if v>=0.001:return f'{v:.4f}'
 s=f'{v:.2e}';a,b=s.split('e');return f'${a}\\times10^{{{int(b)}}}$'
for _,r in e.iterrows():tex+=' & '.join([r.panel,r.tracer,roi(r.roi_name)+f' ({r.roi_id})',str(r.N_AD),str(r.N_CN),f'{r.d_real:.4f}',f'{r.d_syn:.4f}',sci(r.r2_9_real_q),sci(r.r2_9_syn_q)])+r' \\'+'\n'
tex+=r'''\bottomrule
\end{tabularx}
\par\smallskip\footnotesize
Separate two-sided Student's $t$-tests compare AD and CN for each tracer and PET type. BH-FDR correction uses all 98 ROIs within each of four tracer-by-PET-type families, rather than just the displayed regions. Positive $d$ indicates higher uptake in AD. All values are derived from min--max-normalized regional intensities, not SUV/SUVR. Preserved significance or similar effect sizes do not establish clinical equivalence.
\end{table}
'''
path=ROOT/'manuscript/supplementary/tables/regional_effect_sizes.tex';assert not path.exists();path.write_text(tex)
p=ROOT/'manuscript/supplementary/supplementary.tex';anchor=r'\input{supplementary/tables/conditioning}'
apply('G4-REGIONAL-TABLE-INPUTS','manuscript/supplementary/supplementary.tex',anchor,anchor+'\n'+r'\input{supplementary/tables/regional_agreement}'+'\n'+r'\input{supplementary/tables/regional_effect_sizes}',['R2-8','R2-9','R2-10','R3-4','R3-5'],['G4'],ev+[str(p.relative_to(ROOT)) for p in [p1,p2,p3]],'Publish only confirmed compact 16/20-row tables, generated by exact one-to-one joins, retaining full internal CSVs privately',section='tab:regional_agreement; tab:regional_effect_sizes')
d.to_csv(WORK/'regional_agreement_join_checked.csv',index=False)
print('Regional joins:',len(d),len(e))
