from pathlib import Path
import json,re,hashlib,subprocess
from urllib.parse import unquote,urlsplit
root=Path(__file__).resolve().parents[2];o=root/'revision_workspace/index';issues=[];checks=[]
manifest=json.loads((o/'source_manifest.json').read_text());comments=json.loads((o/'comment_index.json').read_text());revs=json.loads((o/'revision_candidates.json').read_text())
for x in manifest:
 p=root/x['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'];checks.append('hash '+x['path'])
 if p.suffix=='.md':
  fence=[n for n,l in enumerate(p.read_text().splitlines(),1) if re.match(r'^\s*(```|~~~)',l)]
  if len(fence)%2:issues.append({'source':x['path'],'issue':'odd fence marker count','lines':fence})
for c in comments:
 p=root/c['response_source'];ls=p.read_text().splitlines();body='\n'.join(ls[c['response_start']-1:c['response_end']]);assert hashlib.sha256(body.encode()).hexdigest()==c['response_sha256'];assert c['response_words']>10;checks.append('response '+c['id'])
for r in revs:
 ls=(root/r['source']).read_text().splitlines();assert 'revised' in ls[r['revised_marker']-1].lower();assert r['revised_marker']<=r['section_end']<=len(ls);checks.append('revision '+r['id'])
bad=[];nlinks=0
for p in (root/'revision_workspace').rglob('*.md'):
 if '/integration/toolchain/root/' in str(p):continue  # extracted third-party package documentation, not authored workspace material
 for m in re.finditer(r'\[[^\]\n]*\]\(([^\n]*?)\)',p.read_text()):
  url=urlsplit(m.group(1))
  if url.scheme or not url.path:continue
  q=(p.parent/unquote(url.path)).resolve();nlinks+=1
  if not q.is_file():bad.append(dict(source=str(p.relative_to(root)),target=m.group(1)))
by={}
for c in comments:
 ls=(root/c['response_source']).read_text().splitlines()
 text=' '.join(' '.join(ls[c['response_start']-1:c['response_end']]).split())
 by.setdefault(text,[]).append(c['id'])
dups=[v for v in by.values() if len(v)>1]
content_findings=['Duplicate English response: '+', '.join(v) for v in dups]
for c in comments:
 if c.get('response_provenance_note'):content_findings.append(c['id']+': '+c['response_provenance_note'])
pdf=root/'rebuttal/BMEF_from_notion/BMEF审稿回复/BMEF_main.pdf'
info=subprocess.check_output(['pdfinfo',str(pdf)],text=True)
report=dict(workspace_link_scope_excludes=['integration/toolchain/root (third-party package documentation)'],check_count=len(checks),export_hashes_verified=len(manifest),comments=56,response_pointer_hashes_verified=len(comments),revision_pointers_verified=len(revs),workspace_markdown_file_links_checked=nlinks,broken_workspace_links=bad,source_fence_findings=issues,pdf_pages=int(re.search(r'Pages:\s+(\d+)',info).group(1)),source_content_findings=content_findings,duplicate_response_groups=dups,english_coverage=bool(len(comments)==56 and not dups),r3_14_revision_count=sum(r['comment']=='R3-14' for r in revs),scientific_results_recomputed=False)
(o/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,ensure_ascii=False,indent=2));assert not bad
