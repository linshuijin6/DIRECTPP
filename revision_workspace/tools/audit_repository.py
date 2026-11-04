from pathlib import Path
import json,re,hashlib,csv,shutil,subprocess
R=Path(__file__).resolve().parents[2]; O=R/'revision_workspace/index'
paths=set()
for d in ['manuscript','rebuttal/sections']:
 for p in (R/d).rglob('*'):
  if p.is_file():paths.add(p)
for f in ['rebuttal/main.tex','rebuttal/references.bib','rebuttal/BMEF_respose_and_revision_details.md','CORE_CODE.md','AGENTS.md','reports/source_reports/REVIEW_REQUIREMENTS.md','reports/source_reports/review_comment_register.csv']:paths.add(R/f)
for d in (R/'experiments').iterdir():
 if d.is_dir():
  for p in d.glob('*.md'):paths.add(p)
for f in [
'reports/revision_evidence_night_20261102/completion.json',
'reports/revision_evidence_night_20261102/G1_G8_EVIDENCE_MATRIX.csv',
'reports/revision_evidence_night_20261102/SUPPLEMENTARY_TABLE_INDEX.md',
'reports/revision_evidence_night_20261102/UNRESOLVED.md',
'reports/revision_evidence_night_20261102/VALIDATION.md',
'reports/revision_evidence_night_20261102/R3_11_final_figures/REPORT.md',
'reports/revision_evidence_night_20261102/R3_11_final_figures/figure_manifest.json',
'reports/r3_11_brain_mask_metrics/run_20261102/REPORT.md',
'reports/r3_11_brain_mask_metrics/run_20261102/completion.json',
'reports/r3_11_brain_mask_metrics/run_20261102/validation.json',
'reports/r2_11_classification_3fold/final_summary/REPORT.md',
'reports/r2_11_classification_3fold/statistical_comparison/REPORT.md',
'reports/r2_8_original_roi_stats/REPORT.md','reports/r2_8_original_roi_stats/FIGURE4_SOURCE_CHECK.md',
'reports/r2_10_normalized_calibration/REPORT.md','reports/r3_5_effect_size/REPORT.md',
'reports/adni_image_acquisition_audit/filtering_code_recovery_20261103/REPORT.md',
'reports/adni_image_acquisition_audit/metadata_1103_review/REPORT.md',
'reports/adni_image_acquisition_audit/filled_information_restoration_20261103/REPORT.md']:
 paths.add(R/f)
for g in ['G1','G1_E1','G2','G3','G4','G5','G6','G7']:paths.add(R/f'reports/revision_evidence_night_20261102/{g}/REPORT.md')
records=[dict(path=str(p.relative_to(R)),exists=p.is_file(),bytes=p.stat().st_size if p.is_file() else None,sha256=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None) for p in sorted(paths)]
(O/'repository_assets.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
checks={}
for folder,entry in [('manuscript','BMEF_main.tex'),('rebuttal','main.tex')]:
 d=R/folder; tex='\n'.join(p.read_text() for p in [d/entry]+list((d/'sections').glob('*.tex'))+list((d/'supplementary').glob('*.tex')))
 bib=(d/'references.bib').read_text();keys=re.findall(r'@\w+\s*\{\s*([^,]+),',bib);cites=[k.strip() for m in re.finditer(r'\\(?:cite\w*)\*?(?:\[[^\]]*\])*\{([^}]+)\}',tex) for k in m.group(1).split(',')]
 checks[folder]=dict(bib_entries=len(keys),duplicate_keys=sorted(k for k in set(keys) if keys.count(k)>1),missing_citation_keys=sorted(set(cites)-set(keys)),labels=len(re.findall(r'\\label\{',tex)),response_blocks=len(re.findall(r'\\response\{',tex)),revcomment_blocks=len(re.findall(r'\\revcomment\{',tex)))
section_tex='\n'.join(p.read_text() for p in (R/'rebuttal/sections').glob('*.tex'))
ids=re.findall(r'\\(?:revcomment|minorcomment)\{([^}]+)\}',section_tex)
checks['rebuttal']['comment_ids']=ids
checks['rebuttal']['reviewer_comment_count']=sum(i.startswith(('R2-','R3-')) for i in ids)
checks['rebuttal']['minorcomment_blocks']=len(re.findall(r'\\minorcomment\{',section_tex))
checks['tools']={s:shutil.which(s) for s in ['pdflatex','biber','bibtex','latexmk','latexdiff','pdfinfo']}
checks['git_head']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=R,text=True).strip()
checks['initial_git_status']='?? rebuttal/BMEF_from_notion/ (git status --short at task start); tracked changes: none'
(O/'repository_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2)+'\n');print(json.dumps(checks,ensure_ascii=False,indent=2));print('asset_count',len(records),'missing',[x['path'] for x in records if not x['exists']])
