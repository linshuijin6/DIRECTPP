"""Generate full 56-point rebuttal from indexed author responses and implemented positions.
Preserve source snippets and record every substantive response amendment separately.
"""
from edit_registry import ROOT,WORK,apply
import re,csv,json,hashlib,difflib
OUT=ROOT/'rebuttal';records=json.loads((ROOT/'revision_workspace/index/comment_index.json').read_text());register={r['comment_id']:r for r in csv.DictReader((ROOT/'reports/source_reports/review_comment_register.csv').open())};positions=list(csv.DictReader((WORK/'position_registry.csv').open()));bypos={r['position_id']:r for r in positions};changes=[]
def digest(t):return hashlib.sha256(t.encode()).hexdigest()
def response(c):
 ls=(ROOT/c['response_source']).read_text().splitlines();return '\n'.join(ls[c['response_start']-1:c['response_end']])
def modify(cid,s):
 reasons=[]
 if cid=='R3-1':
  a='This finding suggests that DIReCT++ can maintain comparable PET synthesis quality even without cognitive-score conditioning. One possible explanation is that the rectified flow framework jointly leverages anatomical information from MRI and adapted tracer-specific guidance, potentially reducing its dependence on cognitive-score conditioning.'
  b='This fixed-weight input intervention assesses inference-time sensitivity; it is not a retrained No-Scores ablation.'
  assert s.count(a)==1;s=s.replace(a,b,1);reasons.append('Stage 1: retain score-removal observations and separate E1 identity; remove unsupported score-independent performance and mechanism attribution.')
 if cid=='R3-12':
  a='Knowledge distillation begins at epoch 140, as specified in the original implementation.'
  b='In the recovered implementation, t=0 from epoch 140 onward, and the same supervised objective fits the PET-minus-MRI endpoint residual. This stage is called one-step distillation in the framework; no separate teacher trajectory or teacher-step schedule was recovered.'
  assert s.count(a)==1;s=s.replace(a,b,1);reasons.append('Stage 1: align the distillation name with the recovered t=0 endpoint-residual fitting described in current Methods; retain the teacher-record limitation.')
 if cid=='R3-13':
  a='Regarding clinical conditioning, we will clarify the available clinical variables, participant selection criteria, and handling of missing information in the OASIS-3 cohort.'
  b='The retained external cohort comprised PUP-processed AV45-PET data from CN and AD participants, with no MCI participants. Complete run-specific records of the clinical prompt fields and missing-field handling were not retained, limiting reproducibility of that historical evaluation.'
  assert s.count(a)==1;s=s.replace(a,b,1);reasons.append('Stage 1: replace an unsupported completed prompt-handling claim with the retained PUP/AV45/CN-AD selection and unrecovered run-specific prompt records from current Methods.')
 if cid=='R3-9':
  a='Second, to evaluate the independent contribution of patient-specific clinical information, we conducted a training-level comparison between the Full and Only-tracer configurations, which retains tracer guidance while excluding the patient clinical condition.'
  b='Second, we conducted a training-level comparison between the Full and Only-tracer configurations; the latter retains tracer guidance while excluding patient-specific clinical conditioning.'
  assert s.count(a)==1;s=s.replace(a,b,1);reasons.append('Stage 1: retain the Full/Only-tracer training-level configuration comparison without claiming an isolated causal contribution.')
 if cid=='R3-2':
  a='We will examine the missingness of individual variables across diagnostic groups using the available original clinical records and revise the presentation and interpretation of the corresponding statistics in Table S1, explicitly distinguishing observed from simulated values. Where historical missingness information cannot be reliably recovered from the available records, we will acknowledge this limitation rather than make unsupported assumptions.'
  b='We have now recovered the historical first-record selection and diagnosis-conditioned filling rules. Of 9,285 score cells in 1,857 prepared records, 1,751 were observed and preserved and 7,534 were missing in the selected source records. Group-specific missing counts and rates are reported in the Supplementary Materials. Direct recomputation corrected four Table S1 summaries: EMCI GDSCALE is 1.00 ± 0.00; LMCI GDSCALE is 3.00 ± 0.00, CDR 0.50 ± 0.00, and NPI-Q 4.00 ± 0.00. Clinical-score group-comparison p-values have been removed. CN weight SD (24.13 kg) is reproducible from the source values, but the retained 0–227 kg range includes unresolved validity issues. No participants were removed and no values were replaced or newly imputed.'
  assert a in s;s=s.replace(a,b);reasons.append('Replace pending missingness review with recovered records, actual table corrections and unresolved weight validity; retain group-conditioned-filling limitation.')
 if cid=='R3-6':
  a='Importantly, we confirm that the synthetic PET images used for downstream classification were obtained from these original OOF predictions, ensuring that each subject’s synthetic PET was generated by a model that had not been trained on that subject.'
  b='The classification analysis retained the existing author-provided synthetic PET inputs under this intended two-fold OOF design. The actual revised classifier partitions and saved outer-test predictions were verified, but the correspondence between these historical synthetic images and the checkpoints used in the reconstructed Full generation comparisons could not be independently established. We therefore report the classification analysis as a separate input-asset family rather than a new downstream validation of those reconstructed generator comparisons.'
  assert a in s;s=s.replace(a,b);reasons.append('Conform execution-identity claim to G2 bounded evidence without reopening or inferring upstream leakage.')
 if cid=='R3-9':
  a='To further examine sensitivity to text conditioning, we propose evaluating the trained Full model with the text condition removed at inference while keeping the network parameters fixed. Such an intervention assesses dependence on the conditioning input but is not equivalent to training a text-free model.'
  b='Fixed-weight patient-conditioning interventions, including empty or mismatched patient features, demonstrate output sensitivity to the supplied context. They are not a retrained text-free model or a complete no-text ablation; a nonzero output response alone does not establish clinical benefit.'
  assert a in s;s=s.replace(a,b)
  a='For one-step distillation versus multi-step ODE sampling, we prioritize comparisons using available model checkpoints to assess image quality and computational efficiency across the sampling strategies.'
  b='For one-step versus multi-step ODE sampling, the available validated measurements cover single-step generation only; no matched multi-step quality/latency comparison is claimed. The recovered training code fixes t=0 from epoch 140 and fits the PET-minus-MRI endpoint residual without a separately recovered teacher trajectory.'
  assert a in s;s=s.replace(a,b)
  a='The original manuscript reports approximately 138 GPU-hours for a complete model training run. Given this computational cost, we have prioritized training-level comparisons for clinical conditioning and the representation of clinical variables, while using existing baselines and targeted inference analyses where appropriate.'
  b='The historical estimate of approximately 138 GPU-hours was not independently verified. The revised computational description therefore uses measured single-step forward latency, parameter count and memory, and does not infer a speedup from step counts or claim a completed equal-protocol FLOP/runtime ranking. We distinguish independently trained model comparisons from fixed-weight inference interventions and feature-level adapter analyses.'
  assert a in s;s=s.replace(a,b);reasons.append('Preserve reconstructed English source identity while replace unperformed-experiment proposals with actual bounded evidence and explicit unavailable comparisons.')
 if cid in ['R2-5','R3-1']:
  s+='\n\nThe fixed-weight score-removal experiment used the separate E1 Full checkpoint family. It cannot remove information already learned from diagnosis-conditioned filled inputs during training. In the completed classification analysis, Clinical-only and MRI+Clinical AUC exceeded MRI+synthetic dual PET in all three tasks; we do not claim independent incremental diagnostic value of the synthetic PET over those clinical fields.'
  reasons.append('Add completed clinical comparison and separate E1 provenance; preserve original small-effect sensitivity findings without treating them as exclusion of circularity.')
 if cid in ['R2-14','R3-8']:
  s+='\n\nFor clarity, the revised manuscript distinguishes the affine-adapter formulation and representation-level analyses from the reconstructed Full generator, which used original fixed tracer-text vectors. The BiomedCLIP backbone is frozen in both cases. We do not attribute the reconstructed Full generator performance to affine adaptation or claim a controlled generator-level frozen-versus-adapted gain.'
  reasons.append('Make actual raw-tracer Full configuration explicit while retaining the confirmed affine-adapter method description.')
 if cid=='R3-8':
  n=0;out=[]
  for l in s.splitlines():
   if l.startswith('1. '):n+=1;l=str(n)+l[1:]
   out.append(l)
  s='\n'.join(out)
 if cid=='R3-11':
  # Complete source response is kept; clarify the finalized worst-QC-passed examples.
  s+='\n\nThe final supplementary examples include the median, 10th-percentile and worst QC-passed subject for each tracer, selected using the saved whole-volume SSIM ranking in the same QC-passed set. The originally flagged MRI/mask failure is not substituted into that set. The original Figure 2 absolute-value table is placed in the main Results; new OOF and masked statistics remain distinct.'
  reasons.append('Align finalized quantile/worst-QC-passed figures and table placement with implemented artifacts.')
 # Change only implemented-document wording; future studies, sharing and submission remain future.
 before=s
 if cid!='M20':
  verbs='clarify|revise|remove|replace|correct|describe|distinguish|incorporate|unify|provide|use|refer|merge|avoid|review'
  s=re.sub(r'\b(We|we) will (?=(?:(?:also|therefore|consistently|more clearly|further) )?(?:'+verbs+r')\b)',r'\1 now ',s)
  s=s.replace('will be discussed together with','is discussed together with')
  s=s.replace('and will report the settings','and report the settings')
 if cid=='M17':s=s.replace('Element-wise Addition','Residual Addition')
 if s!=before:reasons.append('Align completed document edits with final present-tense wording; preserve future studies, data sharing and online submission; match M17 to the actual Residual Addition label.')
 return s,reasons
# Markdown/LaTeX bridge: protect actual math/links, escape prose; never interpret source as code.
UNICODE={'₀':r'\textsubscript{0}','κ':r'\ensuremath{\kappa}','σ':r'\ensuremath{\sigma}','ρ':r'\ensuremath{\rho}','δ':r'\ensuremath{\delta}','μ':r'\ensuremath{\mu}','₂':r'\textsubscript{2}','₁':r'\textsubscript{1}','τ':r'\ensuremath{\tau}','θ':r'\ensuremath{\theta}','α':r'\ensuremath{\alpha}','β':r'\ensuremath{\beta}','λ':r'\ensuremath{\lambda}','Δ':r'\ensuremath{\Delta}','≥':r'\ensuremath{\geq}','≤':r'\ensuremath{\leq}','±':r'\ensuremath{\pm}','×':r'\ensuremath{\times}','−':r'\ensuremath{-}','≈':r'\ensuremath{\approx}','→':r'\ensuremath{\rightarrow}','°':r'\ensuremath{^{\circ}}','¹':r'\textsuperscript{1}','⁸':r'\textsuperscript{8}'}
ESC={'\\':r'\textbackslash{}','&':r'\&','%':r'\%','$':r'\$','#':r'\#','_':r'\_','{':r'\{','}':r'\}','~':r'\textasciitilde{}','^':r'\textasciicircum{}','<':r'\textless{}','>':r'\textgreater{}'}
def escape(s):return ''.join(UNICODE.get(c,ESC.get(c,c)) for c in s)
def latex(s):
 s=re.sub(r'<a\s+href=[\"\']([^\"\']+)[\"\']>(.*?)</a>',r'[\2](\1)',s,flags=re.I)
 tokens=[]
 def protect(value):tokens.append(value);return f'ZZPROTECTED{len(tokens)-1}ZZ'
 s=re.sub(r'\\\(.*?\\\)|\\\[.*?\\\]|\$[^$\n]+\$',lambda m:protect(m.group(0)),s,flags=re.S)
 s=re.sub(r'\[([^\]]+)\]\((https?://[^\s)]+)\)',lambda m:protect(r'\href{'+m.group(2).replace('%',r'\%').replace('#',r'\#').replace('_',r'\_')+'}{'+escape(m.group(1))+'}'),s)
 s=re.sub(r'https?://[^\s<>}]+',lambda m:protect(r'\url{'+m.group(0).rstrip('.,;')+'}')+m.group(0)[len(m.group(0).rstrip('.,;')):],s)
 s=re.sub(r'`([^`]+)`',lambda m:protect(r'\texttt{'+escape(m.group(1))+'}'),s)
 s=re.sub(r'\*\*([^*]+)\*\*',lambda m:protect(r'\textbf{'+escape(m.group(1))+'}'),s)
 s=escape(s)
 for i,t in reversed(list(enumerate(tokens))):s=s.replace(f'ZZPROTECTED{i}ZZ',t)
 return s
citations={'R2-14':['zhang2025multimodal'],'R3-14':['jack2024revised','hansson2023blood'],'R3-15':['liu2025direct'],'M7':['synthseg'],'M8':['Freesurfer'],'M9':['synthseg'],'M10':['synthseg'],'M11':['Xing2022'],'M12':['spm','friston1995spatial'],'M13':['mosconi2005reduced','he2015meta','strom2022cortical'],'M14':['song2021ddim','pinaya2023generative']}
# Keep the existing preamble/macros and author information; replace only content sections.
sections={'02_reviewer2.tex':r'\reviewersec{Response to Reviewer 2}'+'\n','03_reviewer3_major.tex':r'\reviewersec{Response to Reviewer 3: Major Comments}'+'\n','04_reviewer3_minor.tex':r'\reviewersec{Response to Reviewer 3: Minor Comments}'+'\n'}
def location(row):
 t=row['section_or_label']
 if re.search('[\u4e00-\u9fff]',t):
  if row['position_id'].startswith('G4-CORE-'):return ('Results: regional uptake analysis' if int(row['position_id'].split('-')[-1])<5 else 'Methods: regional statistical analysis')
  return 'Revised manuscript: '+', '.join(row['groups'].split(';'))
 return t
# Later final PDF mapping is read if available, avoiding invented page/line references.
locations=json.loads((WORK/'final_pdf_locations.json').read_text()) if (WORK/'final_pdf_locations.json').exists() else {}
review_source_receipts=[]
for c in records:
 cid=c['id'];original=response(c);final,reasons=modify(cid,original);p=WORK/'responses'/(cid+'.source.md')
 if p.exists():assert p.read_text()==original+'\n',f'{cid}: source changed; preserve old source snapshot first'
 else:p.write_text(original+'\n')
 (WORK/'responses'/(cid+'.final.md')).write_text(final+'\n')
 review_source_receipts.append({'id':cid,'source_file':c['response_source'],'source_start':c['response_start'],'source_end':c['response_end'],'source_sha256':c['response_sha256'],'final_sha256':digest(final),'provenance_note':c.get('response_provenance_note','')})
 if reasons:
  changes.append({'comment_id':cid,'source_sha256':digest(original),'final_sha256':digest(final),'reason':' | '.join(reasons)})
  (WORK/'responses'/(cid+'.diff.txt')).write_text(''.join(difflib.unified_diff((original+'\n').splitlines(True),(final+'\n').splitlines(True),fromfile='source',tofile='final')))
 key='R3-minor-'+cid[1:].zfill(2) if cid.startswith('M') else cid
 quote=register[key]['original_text'];part='02_reviewer2.tex' if cid.startswith('R2-') else '03_reviewer3_major.tex' if cid.startswith('R3-') else '04_reviewer3_minor.tex'
 body='\n\\subsection*{'+cid+(' (Reviewer 3 Minor '+cid[1:]+')' if cid.startswith('M') else '')+'}\n'
 body+=r'\revcomment{'+cid+'}{'+latex(quote)+'}\n\n'+r'\response{'+latex(final)
 if cid in citations:body+='\n\nRelevant references: '+r'\cite{'+','.join(citations[cid])+'}.'
 body+='}\n\n'
 pp=[r for r in positions if cid in r['related_comments'].split(';')]
 if cid in ['R2-1','R2-2']:action='We thank the reviewer for this positive assessment. No separate manuscript change was required for this comment.'
 elif cid=='M20':action='The submission-system abstract is supplied as plain text without literal LaTeX commands. The authors will use this text when entering the revised submission in Editorial Manager.'
 else:
  descriptions=[]
  for r in pp:
   title=location(r);pg=locations.get(r['position_id'],{})
   if pg.get('supplementary_page'):title+=' (Supplementary Materials, p. '+str(pg['supplementary_page'])+'; combined reference copy p. '+str(pg['page'])+')'
   elif pg.get('page'):title+=' (p. '+str(pg['page'])+((', lines '+str(pg['line_start'])+'--'+str(pg['line_end'])) if pg.get('line_start') and pg.get('line_end') else '')+')'
   if title not in descriptions:descriptions.append(title)
  action='The corresponding changes are implemented in the following final manuscript locations:\n'+r'\begin{itemize}[leftmargin=1.5em,itemsep=2pt]'+'\n'+''.join(r'\item '+latex(t)+'.\n' for t in descriptions)+r'\end{itemize}'
 body+=r'\actiontaken{'+action+'}\n'
 # One representative verbatim final excerpt, limited in length for reviewer readability.
 eligible=[r for r in pp if r['target_file']=='manuscript/BMEF_main.tex' and r['position_id'] not in ['G7-ABSTRACT','G7-TITLE','G7-PDF-TITLE','G7-DISCUSSION-MERGED']]
 if eligible:
  text=(ROOT/eligible[0]['final_text_path']).read_text().strip()
  if not text.startswith('\\'):
   excerpt=re.split(r'(?<=[.!?])\s+(?=[A-Z])',text)[0]
   if len(excerpt)<1100 and '\\begin{' not in excerpt:
    aux=(ROOT/'revision_workspace/build/manuscript/BMEF_main.aux').read_text()
    labels=dict(re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}',aux))
    excerpt=re.sub(r'\\ref\{([^}]+)\}',lambda m:labels[m.group(1)],excerpt)
    body+='\n'+r'\changedtext{'+latex(location(eligible[0]))+'}{'+excerpt+'}\n'
 sections[part]+=body
for name,new in sections.items():
 target='rebuttal/sections/'+name;old=(ROOT/target).read_text();p=WORK/'rebuttal_generated';p.mkdir(exist_ok=True);(p/name).write_text(new)
 if not any(r['position_id']=='REBUTTAL-'+name for r in positions):apply('REBUTTAL-'+name,target,old,new,[],['REBUTTAL'],['revision_workspace/index/comment_index.json','revision_workspace/integration/comment_position_map.csv'],'Rebuild from full indexed author responses, retain exact reviewer comments, record substantive response amendments and point to actual final positions',section=name)
 else:
  # Regeneration after final page/line mapping is a deliberate same-position amendment.
  from edit_registry import amend
  if old!=new:amend('REBUTTAL-'+name,new,decision='Refresh final verified manuscript locations without changing source response content.')
with (WORK/'response_changes.csv').open('w') as f:
 w=csv.DictWriter(f,fieldnames=['comment_id','source_sha256','final_sha256','reason']);w.writeheader();w.writerows(changes)
(WORK/'response_source_manifest.json').write_text(json.dumps(review_source_receipts,ensure_ascii=False,indent=2)+'\n')
print('Generated all 56 reviewer responses; source-derived response amendments (including completed-document tense):',[r['comment_id'] for r in changes])
