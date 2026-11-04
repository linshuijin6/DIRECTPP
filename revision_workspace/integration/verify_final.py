"""Local engineering and traceability checks; does not certify scientific conclusions."""
from pathlib import Path
import csv,json,re,hashlib,subprocess,datetime
R=Path(__file__).resolve().parents[2];W=R/'revision_workspace/integration';V=R/'revision_workspace/verification';checks=[];issues=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def check(name,ok,detail=''):
 checks.append({'check':name,'passed':bool(ok),'detail':detail})
 if not ok:issues.append(name)
for kind,path,base in [('Notion export',R/'revision_workspace/index/source_manifest.json',R),('preserved baseline',W/'baseline/manifest.json',W/'baseline')]:
 items=json.loads(path.read_text());check(kind+' hashes',all(sha(base/x['path'])==x['sha256'] for x in items),str(len(items))+' files')
rows=list(csv.DictReader((W/'position_registry.csv').open()));check('unique final position IDs',len({x['position_id'] for x in rows})==len(rows),str(len(rows)))
for x in rows:check('final fragment '+x['position_id'],(R/x['target_file']).read_text().count((R/x['final_text_path']).read_text().rstrip('\n'))==1)
for name,count in [('candidate_disposition.csv',123),('addition_disposition.csv',17)]:
 xs=list(csv.DictReader((W/name).open()));check(name,len(xs)==count and all(set(x['final_position_ids'].split(';')).issubset({r['position_id'] for r in rows}) for x in xs),str(len(xs)))
cm=list(csv.DictReader((W/'comment_position_map.csv').open()));check('bidirectional 56-comment coverage',len({x['comment_id'] for x in cm})==56)
rs=json.loads((W/'response_source_manifest.json').read_text());check('56 preserved source responses',len(rs)==56)
for x in rs:
 s='\n'.join((R/x['source_file']).read_text().splitlines()[x['source_start']-1:x['source_end']]);check('source response '+x['id'],hashlib.sha256(s.encode()).hexdigest()==x['source_sha256'] and (W/'responses'/(x['id']+'.source.md')).read_text()==s+'\n')
 check('final response '+x['id'],hashlib.sha256((W/'responses'/(x['id']+'.final.md')).read_text().rstrip('\n').encode()).hexdigest()==x['final_sha256'])
for f,n in [('02_reviewer2.tex',20),('03_reviewer3_major.tex',15),('04_reviewer3_minor.tex',21)]:
 s=(R/'rebuttal/sections'/f).read_text();check(f+' coverage',s.count(r'\revcomment{')==n and s.count(r'\response{')==n);check(f+' English body',not re.search('[\u4e00-\u9fff]',s))
loc=json.loads((W/'location_verification.json').read_text());check('final combined-PDF identity',loc['pdf_sha256']==sha(R/'revision_workspace/build/manuscript/BMEF_main.pdf'));check('no missing printed locations',not loc['unmatched_printed_positions'])
mainaux=(R/'revision_workspace/build/manuscript/BMEF_main.aux').read_text();cleanaux=(R/'revision_workspace/build/variants/manuscript_clean.aux').read_text()
def label_pages(s):return {m[0]:int(m[2]) for m in re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]+)\}\{(\d+)\}',s) if not m[1].startswith('S')}
mp=label_pages(mainaux);cp=label_pages(cleanaux);check('clean/combined main-label pagination agrees',all(cp.get(k)==v for k,v in mp.items()),str(len(mp))+' main labels')
pdfs={}
for folder,name in [('manuscript','BMEF_main'),('rebuttal','main'),('rebuttal','cover_letter'),('variants','manuscript_clean'),('variants','supplementary_standalone'),('variants','manuscript_highlighted')]:
 folder='final_highlight' if name=='manuscript_highlighted' else folder
 filename=name
 p=R/f'revision_workspace/build/{folder}/{filename}.pdf';l=p.with_suffix('.log').read_text();info=subprocess.check_output(['pdfinfo',str(p)],text=True);pages=int(re.search(r'Pages:\s+(\d+)',info).group(1));pdfs[name]={'pages':pages,'sha256':sha(p)}
 errors=[v for v in l.splitlines() if v.startswith('!') or 'undefined references' in v or ('Reference ' in v and 'undefined' in v) or 'Float too large' in v or 'Overfull ' in v]
 check('clean build '+name,not errors,'; '.join(errors))
 check('built from current input '+name,p.stat().st_mtime>(R/'manuscript/BMEF_main.tex').stat().st_mtime if folder!='rebuttal' else p.stat().st_mtime>(R/'rebuttal/main.tex').stat().st_mtime)
# Confirm the standalone supplement page pointers against the delivered final text.
subprocess.run(['pdftotext','-layout',str(R/'revision_workspace/build/variants/supplementary_standalone.pdf'),str(V/'supplementary_final_text.txt')],check=True)
sp=[re.sub(r'[^a-z0-9]+',' ',x.lower()).split() for x in (V/'supplementary_final_text.txt').read_text().split('\f')]
locations=json.loads((W/'final_pdf_locations.json').read_text());smaux=(R/'revision_workspace/build/variants/supplementary_standalone.aux').read_text();sl={m[0]:int(m[1]) for m in re.findall(r'\\newlabel\{([^}]+)\}\{\{S[^}]+\}\{(\d+)\}',smaux)}
for key,x in locations.items():
 if not x.get('supplementary_page'):continue
 page=x['supplementary_page'];needle=x.get('matched_text');ok=needle in ' '.join(sp[page-1]) if needle else any(sl.get(l['label'])==page for l in x.get('label_locations',[]));check('standalone page '+key,ok)
abstract=(W/'submission_abstract.txt').read_text();check('plain-text abstract',not re.search(r'\\|\$|\{\}',abstract))
figmeta=json.loads((W/'figures/roi_figure_manifest.json').read_text());check('196 designated ROI CSV hashes',len(figmeta['inputs'])==196 and all('/shuijin/' in x['path'] and sha(R/x['path'])==x['sha256'] for x in figmeta['inputs']))
for name in ['figure_1','figure_4','figure_5']+['supplementary_figure_'+str(i) for i in range(1,7)]:
 p=R/'manuscript/figures/editable_sources'/(name+'.svg');check('editable text '+name,p.is_file() and '<text' in p.read_text())
check('no hypothetical extra fits', '81' in (R/'manuscript/BMEF_main.tex').read_text() and '27 task' in (R/'manuscript/BMEF_main.tex').read_text())
report={'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'passed':not issues,'checks':checks,'failed_checks':issues,'pdfs':pdfs,'scope':'Engineering/source traceability only; no new training, inference, data imputation or new inferential statistics. Scientific and author-form limitations remain explicit.','presentation_deviations':figmeta['presentation_deviations']}
(V/'FINAL_VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps({'passed':report['passed'],'checks':len(checks),'failed':issues,'pdfs':pdfs},indent=2));assert not issues
