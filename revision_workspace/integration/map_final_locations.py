"""Record verified PDF pages/printed lines; preserve evidence for every match."""
from pathlib import Path
import re,json,csv,subprocess,xml.etree.ElementTree as ET,unicodedata,hashlib
W=Path(__file__).resolve().parent;ROOT=W.parents[1];V=ROOT/'revision_workspace/verification';pdf=ROOT/'revision_workspace/build/manuscript/BMEF_main.pdf'
subprocess.run(['pdftotext','-bbox-layout',str(pdf),str(V/'manuscript_bbox.html')],check=True)
ns={'h':'http://www.w3.org/1999/xhtml'};tree=ET.ElementTree(ET.fromstring(re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '',(V/'manuscript_bbox.html').read_text())));pages=[]
def norm(s):return re.findall(r'[a-z0-9]+',unicodedata.normalize('NFKD',s).lower())
for number,page in enumerate(tree.findall('.//h:page',ns),1):
 words=[];margins=[]
 for word in page.findall('.//h:word',ns):
  text=word.text or '';x=float(word.get('xMin'));y=float(word.get('yMin'))
  if x<82 and text.isdigit():margins.append((y,int(text)));continue
  for token in norm(text):words.append((token,y))
 pages.append({'page':number,'words':words,'margins':margins})
aux=(ROOT/'revision_workspace/build/manuscript/BMEF_main.aux').read_text();labels={m[0]:{'number':m[1],'page':int(m[2])} for m in re.findall(r'\\newlabel\{([^}]+)\}\{\{([^}]*)\}\{(\d+)\}',aux)}
def plain(s):
 s=re.sub(r'%[^\n]*','',s)
 s=re.sub(r'\\(?:label|ref|cite|input|includegraphics|begin|end|setcounter|renewcommand|usepackage|addbibresource)(?:\[[^\]]*\])?\{[^}]*\}', ' ',s)
 s=re.sub(r'\\[a-zA-Z]+\*?(?:\[[^\]]*\])?',' ',s)
 return norm(s)
rows=list(csv.DictReader((W/'position_registry.csv').open()));result={};unmatched=[]
for row in rows:
 pid=row['position_id'];target=ROOT/row['target_file'];fragment=(ROOT/row['final_text_path']).read_text().rstrip('\n');text=target.read_text();assert text.count(fragment)==1,(pid,'registered fragment mismatch',text.count(fragment))
 source_line=text[:text.index(fragment)].count('\n')+1
 entry={'target_file':row['target_file'],'source_line_start':source_line,'source_line_end':source_line+fragment.count('\n'),'location_basis':'not a printed manuscript paragraph'}
 if row['target_file'].startswith('rebuttal/') or row['section_or_label']=='Preamble' or pid.startswith('BUILD-') or pid in ['G7-PDF-TITLE','TYPESETTING-LINE-FIT','PDF-TEXT-ENCODING']:result[pid]=entry;continue
 needles=plain(fragment);hits=[]
 # Require at least eight consecutive normalized words and a unique page.
 for start in range(min(max(len(needles)-7,0),180)):
  q=needles[start:start+8]
  if len(q)<8:continue
  matches=[]
  for page in pages:
   ws=[x[0] for x in page['words']]
   for i in range(len(ws)-7):
    if ws[i:i+8]==q:matches.append((page,i))
  if len(matches)==1:
   page,i=matches[0];ys=[y for t,y in page['words'][i:i+8]];nearest=[]
   for y in ys:
    close=[(abs(my-y),ln) for my,ln in page['margins'] if abs(my-y)<7]
    if close:nearest.append(min(close)[1])
   entry.update(page=page['page'],location_basis='unique 8-word PDF match',matched_text=' '.join(q))
   if nearest:entry.update(line_start=min(nearest),line_end=max(nearest),line_scope='matched phrase only')
   hits=[1];break
 if not hits and len(needles) in range(4,8):
  short=[p for p in pages if ' '.join(needles) in ' '.join(t for t,y in p['words'])]
  if len(short)==1:entry.update(page=short[0]['page'],location_basis='unique short heading PDF match',matched_text=' '.join(needles));hits=[1]
 if not hits:
  labs=re.findall(r'\\label\{([^}]+)\}',fragment)
  labs+=re.findall(r'(?:fig|tab|eq):[A-Za-z0-9_:-]+',row['section_or_label'])
  for input_name in re.findall(r'\\input\{([^}]+)\}',fragment):
   p=ROOT/'manuscript'/(input_name+'.tex')
   if p.exists():labs+=re.findall(r'\\label\{([^}]+)\}',p.read_text())
  refs=[dict(label=l,**labels[l]) for l in dict.fromkeys(labs) if l in labels]
  if refs:entry.update(page=refs[0]['page'],location_basis='final LaTeX aux label',label_locations=refs)
  elif pid.startswith('BIB-'):
   entry.update(location_basis='bibliography source; see References in clean manuscript')
  elif pid in ['G7-TITLE']:entry.update(page=1,location_basis='PDF title, visually verified')
  else:unmatched.append(pid)
 result[pid]=entry
# Standalone supplementary pagination is independently verified, not inferred by offset.
saux=(ROOT/'revision_workspace/build/variants/supplementary_standalone.aux').read_text()
slabels={m[0]:int(m[1]) for m in re.findall(r'\\newlabel\{([^}]+)\}\{\{S[^}]+\}\{(\d+)\}',saux)}
subprocess.run(['pdftotext','-layout',str(ROOT/'revision_workspace/build/variants/supplementary_standalone.pdf'),str(V/'supplementary_text.txt')],check=True)
spages=[norm(x) for x in (V/'supplementary_text.txt').read_text().split('\f')]
for entry in result.values():
 if entry.get('matched_text'):
  q=entry['matched_text'];matches=[i+1 for i,p in enumerate(spages) if q in ' '.join(p)]
  if len(matches)==1:entry['supplementary_page']=matches[0]
 if not entry.get('supplementary_page'):
  for l in entry.get('label_locations',[]):
   if l['label'] in slabels:entry['supplementary_page']=slabels[l['label']];break
(W/'final_pdf_locations.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(W/'location_verification.json').write_text(json.dumps({'pdf_sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'positions':len(rows),'mapped_to_pdf':sum('page'in x for x in result.values()),'unmatched_printed_positions':unmatched,'page_scope':'final combined manuscript, 54 pages; standalone supplementary uses its own pagination','line_scope':'only matched visible phrase; no inferred whole-paragraph line ranges'},indent=2)+'\n')
print('Mapped',sum('page'in x for x in result.values()),'of',len(rows),'positions; unmatched printed positions:',unmatched)
# Refresh 56-comment bidirectional map from actual final positions.
comments=json.loads((ROOT/'revision_workspace/index/comment_index.json').read_text());out=[]
for c in comments:
 pp=[r for r in rows if c['id'] in r['related_comments'].split(';') and not r['target_file'].startswith('rebuttal/')]
 if c['id'] in ['R2-1','R2-2']:pp=[None]
 if c['id']=='M20':pp=[None]
 for r in pp:
  loc=result.get(r['position_id'],{}) if r else {};place='p. '+str(loc['page']) if 'page'in loc else ''
  if loc.get('line_start'):place+=', lines '+str(loc['line_start'])+'-'+str(loc['line_end'])+' (matched phrase)'
  out.append({'comment_id':c['id'],'response_source':c['response_source'],'response_start':c['response_start'],'response_end':c['response_end'],'response_sha256':c['response_sha256'],'position_id':r['position_id'] if r else '', 'evidence_file':r['evidence_paths'] if r else ('revision_workspace/integration/submission_abstract.txt' if c['id']=='M20' else ''),'manuscript_label':r['section_or_label'] if r else '', 'final_page_lines':place,'disposition':'implemented_and_built' if r else ('plain_text_abstract_prepared' if c['id']=='M20' else 'no_change_positive_comment')})
assert len({x['comment_id'] for x in out})==56
with (W/'comment_position_map.csv').open('w') as f:
 writer=csv.DictWriter(f,fieldnames=list(out[0]));writer.writeheader();writer.writerows(out)
