from pathlib import Path
import csv,json,hashlib,re
import pandas as pd
from scipy.stats import f_oneway,chi2_contingency
from edit_registry import ROOT,WORK,apply
base=ROOT/'reports/adni_image_acquisition_audit/filtering_code_recovery_20261103'
source=base/'filled_restored_by_historical_selection.csv';df=pd.read_csv(source)
assert len(df)==1857 and df['Subject ID'].is_unique
GROUPS=['CN','EMCI','LMCI','MCI','AD'];fields=['Age','Weight','MMSE Total Score','GDSCALE Total Score','Global CDR','FAQ Total Score','NPI-Q Total Score'];names=['Age (years)','Weight (kg)','MMSE','GDSCALE','Global CDR','FAQ','NPI-Q'];clinical=fields[2:]
assert not df[fields+['Sex','Research Group']].isna().any().any()
summary=[];missing=[]
for group in GROUPS:
 d=df[df['Research Group']==group]
 for field in fields:
  summary.append(dict(group=group,field=field,n=len(d),mean=d[field].mean(),sample_sd=d[field].std(ddof=1),minimum=d[field].min(),maximum=d[field].max(),zero_count=(d[field]==0).sum()))
 for field in clinical:
  observed=d['source_observed__'+field].notna();assert (d.loc[observed,field]==d.loc[observed,'source_observed__'+field]).all()
  missing.append(dict(group=group,field=field,n=len(d),observed=int(observed.sum()),missing=int((~observed).sum()),missing_percent=100*(~observed).mean()))
assert sum(x['missing'] for x in missing)==7534
reference=pd.read_csv(base/'score_provenance_by_group.csv')
for x in missing:
 row=reference[(reference.research_group==x['group'])&(reference.variable==x['field'])].iloc[0];assert row.source_missing==x['missing'] and row.source_observed==x['observed']
for fn,data in [('g8_summary_checked.csv',summary),('g8_missingness_checked.csv',missing)]:pd.DataFrame(data).to_csv(WORK/fn,index=False)
original=(WORK/'baseline/manuscript/supplementary/supplementary.tex').read_text();table=re.search(r'\\begin\{table\}.*?\\label\{tab:supp_adni\}.*?\\end\{table\}',original,re.S).group(0)
# The first table environment follows the original six figures; no earlier table exists.
corrections=[]
for field,name in zip(fields,names):
 line=next(l for l in table.splitlines() if l.startswith(name+' &'))
 cells=line.split(' & ');actual=[]
 for i,g in enumerate(GROUPS):
  row=next(x for x in summary if x['group']==g and x['field']==field);actual.append(f"{row['mean']:.2f} $\\pm$ {row['sample_sd']:.2f}")
  oldnums=[float(n) for n in re.findall(r'\d+\.\d+',cells[i+1])]
  if oldnums!=[round(row['mean'],2),round(row['sample_sd'],2)]:corrections.append(dict(group=g,field=field,old=cells[i+1],new=actual[-1]))
 for i,value in enumerate(actual):cells[i+1]=value
 if field in clinical:cells[-1]=r'-- \\'
 table=table.replace(line,' & '.join(cells))
assert len(corrections)==4,corrections
caption=re.search(r'\\caption\{.*?\}\n\\label',table,re.S).group(0)
newcaption=r'''\caption{\textbf{Demographic characteristics and prepared clinical inputs of ADNI.} Data are mean $\pm$ sample s.d., except counts. Demographic $P$ values use one-way ANOVA (age, weight) or a chi-square test (sex). Clinical summaries combine observed and diagnostic-group-conditioned filled scores; their group-comparison $P$ values are omitted because the distributions are not independent clinical evidence. Source missingness is reported in Table~\ref{tab:clinical_missingness}. CDR: Clinical Dementia Rating; MMSE: Mini-Mental State Examination.}
\label'''
table=table.replace(caption,newcaption)
table=table.replace('MCI = Mild Cognitive Impairment;', 'MCI = the remaining MCI participants not assigned to EMCI or LMCI (MCI-U in the text);')
table=table.replace('AD = Alzheimer’s dementia.','AD = Alzheimer’s dementia. Zero standard deviations reflect constant prepared scores, including diagnosis-conditioned fills; they do not establish absence of clinical variability. The original CN weight entries span 0--227 kg and are retained without exclusions or replacements; their clinical validity and the meaning of zero entries remain unresolved.')
apply('G8-TABLE-S1','manuscript/supplementary/supplementary.tex',re.search(r'\\begin\{table\}.*?\\label\{tab:supp_adni\}.*?\\end\{table\}',original,re.S).group(0),table,['R3-2','R2-16','R3-1'],['G8'],[str(source.relative_to(ROOT)),str((base/'score_provenance_by_group.csv').relative_to(ROOT))],'R3-2 confirmed scheme; direct source verification corrects four mismatched mean/SD cells and documents weight validity gap',section='tab:supp_adni')
rows=[]
for field,name in zip(clinical,names[2:]):
 values=[]
 for g in GROUPS:
  x=next(x for x in missing if x['group']==g and x['field']==field);values.append(f"{x['missing']}/{x['n']} ({x['missing_percent']:.1f}\\%)")
 rows.append(name+' & '+' & '.join(values)+r' \\')
tex=r'''\begin{table}[htbp]
\caption{\textbf{Missing clinical scores in the source records before historical filling.} Each cell gives missing count / group size (percentage); missingness is defined relative to the first source CSV record selected for each participant, not all ADNI visits.}
\label{tab:clinical_missingness}
\centering\small
\begin{tabularx}{\textwidth}{l*{5}{>{\centering\arraybackslash}X}}
\toprule
Score & CN & EMCI & LMCI & MCI-U & AD \\
\midrule
'''+ '\n'.join(rows)+r'''
\bottomrule
\end{tabularx}
\par\smallskip\footnotesize
Source records contain 1,751 observed and 7,534 missing score cells across 1,857 participants and five scores. All available scores were retained. Historical filling used diagnostic-group rules: MMSE values were drawn from group-specific integer sets; GDSCALE and NPI-Q used group-specific fixed values; FAQ used fixed values or group-specific integer sets/ranges; and CDR used fixed values or a group-specific Bernoulli choice for EMCI/MCI-U. These are simulated inputs, not clinical observations or group-mean imputation. Their use can encode diagnostic-group information. The original random states were not recovered, and no re-imputation was performed. Age, sex and weight have no blank entries in the prepared table, which does not establish the clinical validity of every entry. The clinical source row's Image ID does not identify the actual MRI/PET acquisition used by the model.
\end{table}
'''
q=ROOT/'manuscript/supplementary/tables/clinical_missingness.tex';q.parent.mkdir(exist_ok=True)
assert not q.exists();q.write_text(tex)
# Append after existing tables to preserve their original labels and ordering.
p=ROOT/'manuscript/supplementary/supplementary.tex';old=p.read_text().rstrip().splitlines()[-1]
assert old==r'\end{table}'
# Use the unique software table as insertion anchor, not a nonunique end-table token.
txt=p.read_text();anchor=re.search(r'\\begin\{table\}.*?\\label\{tab:supp_software\}.*?\\end\{table\}',txt[txt.index(r'\begin{table}',txt.index(r'\label{tab:supp_oasis}')):],re.S).group(0)
apply('G8-MISSINGNESS-INPUT','manuscript/supplementary/supplementary.tex',anchor,anchor+'\n\n'+r'\input{supplementary/tables/clinical_missingness}',['R3-2','R3-1','R2-5'],['G8'],[str(source.relative_to(ROOT))],'Add verified group-wise source missingness without changing cohorts or simulated values',section='tab:clinical_missingness')
main=(ROOT/'manuscript/BMEF_main.tex').read_text();old=next(l for l in main.splitlines() if l.startswith('A consistent gradient in disease severity'))
new=r'''In the prepared clinical inputs, mean Mini-Mental State Examination (MMSE) scores decreased from 29.40 in CN to 20.84 in AD; other clinical scores also varied across diagnostic groups (Table~\ref{tab:supp_adni}). Clinical information was selected by participant identity, taking the first record in the source CSV order, rather than the nearest or earliest imaging visit. Missing MMSE, GDSCALE, Global CDR, FAQ and NPI-Q scores were filled using diagnostic-group-conditioned rules. Of 9,285 score cells, 1,751 were observed and retained, while 7,534 were missing in those source records and had values consistent with the recovered filling rules. The resulting score distributions include simulated inputs and should not be interpreted as independent evidence of between-group clinical differences. Group-wise missingness is reported in Table~\ref{tab:clinical_missingness}; no new imputation was performed for the revised analyses. The prepared weight data retain unresolved source-value issues, including CN entries ranging from 0 to 227 kg.'''
apply('G8-CLINICAL-METHODS','manuscript/BMEF_main.tex',old,new,['R3-2','R3-1','R2-5','R2-16','R3-6'],['G8','G2'],[str((base/'REPORT.md').relative_to(ROOT)),str(source.relative_to(ROOT))],'Merge confirmed R3-2 description with recovered first-record and missingness evidence; remove inferential clinical p-value claims',section='Materials and Data Preprocessing / clinical inputs')
report={'source':str(source.relative_to(ROOT)),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'subjects':len(df),'unit':'one participant per prepared row; five source-score cells per participant','unique_subjects':bool(df['Subject ID'].is_unique),'observed_score_cells':1751,'source_missing_score_cells':7534,'corrected_summary_cells':corrections,'cn_weight_range':[float(df.loc[df['Research Group']=='CN','Weight'].min()),float(df.loc[df['Research Group']=='CN','Weight'].max())],'no_subject_exclusions':True,'no_imputation':True,'scientific_limit':'Diagnosis-conditioned fills can encode group membership; source weight validity unresolved; no proof of independent diagnostic value.'}
(WORK/'g8_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2))
