"""Bounded final checks; no image-metric or bootstrap recomputation."""
from pathlib import Path
import json,hashlib,ast,re,subprocess
import numpy as np,pandas as pd
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102'
checks=[]
def check(name,condition):
    checks.append(dict(check=name,status='PASS' if condition else 'FAIL'))
    if not condition:raise AssertionError(name)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
required=['INVENTORY.md','inventory.csv','TASK_STATUS.md','EXECUTION_REPORT.md','G1_G8_EVIDENCE_MATRIX.md','SUPPLEMENTARY_TABLE_INDEX.md','FIGURE_INDEX.md','UNRESOLVED.md']
for f in required:check('required:'+f,(OUT/f).is_file() and (OUT/f).stat().st_size>0)
for p in (OUT/'code').glob('*.py'):ast.parse(p.read_text())
check('evaluation code syntax',True)
for r in json.loads((OUT/'audit/reused_source_manifest.json').read_text()):
    check('reused source:'+r['output'],sha(ROOT/r['source'])==r['sha256'] and sha(OUT/r['output'])==r['sha256'])
for p in (OUT/'G3').glob('sources.json'):
    for r in json.loads(p.read_text()):check('generation frozen metrics:'+r['model'],sha(Path(r['path']))==r['sha256'])
full=pd.read_csv(ROOT/'reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv');full=full[full.epoch==165];keys=['ptid','tracer','fold'];single=[]
for p in sorted((OUT/'remote/single_results').glob('*/metrics.csv')):
    d=pd.read_csv(p);r=json.loads(p.with_name('completion.json').read_text())
    check('Single receipt:'+p.parent.name,len(d)==r['metric_rows'] and sha(p)==r['metrics_sha256'] and set(d.checkpoint_sha256)=={r['checkpoint_sha256']} and set(d.epoch)=={165})
    check('Single finite metrics:'+p.parent.name,np.isfinite(d[['ssim','psnr','mse','mae']]).all().all());single.append(d)
s=pd.concat(single);check('Single exact full OOF key coverage',len(s)==2963 and set(s[keys].itertuples(index=False,name=None))==set(full[keys].itertuples(index=False,name=None)) and not s.duplicated(keys).any())
paired=pd.read_csv(OUT/'G3/paired_comparisons.csv')
check('40 paired endpoints',len(paired)==40 and set(paired.groupby('model').size())=={8})
check('signed dz/t consistency',np.allclose(paired.cohen_dz*np.sqrt(paired.n),paired.t_stat,atol=1e-10,rtol=1e-10))
check('Holm never smaller than raw p',(paired.p_holm>=paired.p_raw-1e-15).all())
check('paired benefit proportions valid',paired.full_better_proportion.between(0,1).all())
roi=pd.read_csv(OUT/'G4/authorFull_OT_complete_overall.csv')
check('ROI392 unique keys',len(roi)==392 and not roi.duplicated(['tracer','roi_id','model']).any())
check('ROI CI contains own mean',((roi.mean_ci_low<=roi.paired_mean_difference)&(roi.mean_ci_high>=roi.paired_mean_difference)).all())
check('ROI q valid',roi.q_BH98_bias.between(0,1).all())
cp=pd.read_csv(OUT/'G5/clinical_paired_comparisons.csv');check('clinical new60 CI endpoints',len(cp)==60)
check('clinical metadata source18',len(json.loads((OUT/'remote/clinical18_metadata.json').read_text()))==18)
check('clinical36 withinfold DeLong',len(pd.read_csv(OUT/'G5/clinical_delong_by_fold.csv'))==36)
check('original18 withinfold DeLong reused',len(pd.read_csv(OUT/'G5/existing_imaging_delong_by_fold.csv'))==18)
bands=pd.read_csv(OUT/'G5/roc_curves_and_bands.csv')
check('ROC3x5x201 rows',len(bands)==3015 and len(bands.groupby(['task','condition']))==15)
check('ROC probability limits',bands[['fpr','mean_tpr','ci_low','ci_high']].ge(0).all().all() and bands[['fpr','mean_tpr','ci_low','ci_high']].le(1+1e-14).all().all())
check('ROC ordered bands',(bands.ci_low<=bands.ci_high).all())
manifest=json.loads((OUT/'audit/table_manifest.json').read_text());check('23 table drafts',len(manifest)==23)
for r in manifest:
    p=OUT/r['latex'];text=p.read_text();check('table file:'+r['id'],p.is_file() and (OUT/r['csv']).is_file())
    check('table row count:'+r['id'],len(pd.read_csv(OUT/r['csv']))==r['rows'])
    stack=[]
    for kind,env in re.findall(r'\\(begin|end)\{([^{}]+)\}',text):
        if kind=='begin':stack.append(env)
        else:check('LaTeX environment:'+r['id']+':'+env,bool(stack) and stack.pop()==env)
    check('LaTeX balanced environments:'+r['id'],not stack)
    balance=0
    for token in re.findall(r'(?<!\\)[{}]',text):
        balance+=1 if token=='{' else -1
        if balance<0:break
    check('LaTeX balanced braces:'+r['id'],balance==0)
figs=sorted((OUT/'figures').glob('*.png'));check('11 scientific PNGs',len(figs)==11)
for p in figs:
    im=Image.open(p);im.verify();im=Image.open(p).convert('RGB')
    check('PNG nonempty:'+p.name,im.width>=800 and im.height>=600 and np.asarray(im).std()>10)
selection=OUT/'G3_cases/selection_manifest_internal.csv';check('case selection frozen',sha(selection)==json.loads((OUT/'G3_cases/selection_frozen.json').read_text())['sha256'])
check('six cases no reselection',len(pd.read_csv(selection))==6)
official=ROOT/'manuscript/BMEF_main.tex';receipt=json.loads((ROOT/'reports/full_ot_medical_evidence/03b_analysis_receipt.json').read_text())
check('official manuscript matches existing source receipt',sha(official)==receipt['source_hashes']['manuscript/BMEF_main.tex'])
git=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True);(OUT/'audit/git_status_final.txt').write_text(git)
tracked=subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines();check('tracked changes scoped to report or initial remote documents',all(p.startswith('reports/revision_evidence_night_20261102/') or p in {'REMOTE_INSTANCE_1.md','REMOTE_INSTANCE_2.md'} for p in tracked))
for p in (OUT/'G2/split_and_source_hashes.csv',):
    for r in pd.read_csv(p).itertuples():check('preserved source hash:'+r.path,sha(ROOT/r.path)==r.sha256)
result=dict(status='PASS',checks=len(checks),check_results=checks,scope='file identity, coverage, statistical algebra, source preservation, LaTeX structure and PNG integrity; no paper compile or scientific metric recomputation',rendered_review='all11 at contact-sheet scale; native-scale ROC AD/CN and EMCI/LMCI, forest, representative case; layout repairs verified',limitations='LaTeX layout not compiled; source limitations remain in UNRESOLVED.md')
(OUT/'audit/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(OUT/'VALIDATION.md').write_text('# 交付核验\n\nPASS：'+str(len(checks))+'项有界检查。原始复用文件哈希一致；Single四折身份/2963行覆盖完整；40配对终点、多重校正代数、临床18来源、逐折DeLong18+36、ROC3×5曲线、23表草稿与11张PNG均核对。选例清单SHA冻结；稿件与已有source receipt一致。\n\nPNG已做接触表整体目视检查，并对ROC/森林图/病例原尺寸抽查；修复病例底部标注和森林图MSE刻度拥挤。LaTeX仅环境/括号/行数结构校验，未编译论文或独立表，不能将此工程检查称为科学验证。科学证据边界见UNRESOLVED.md。\n')
print('PASS',len(checks),flush=True)
