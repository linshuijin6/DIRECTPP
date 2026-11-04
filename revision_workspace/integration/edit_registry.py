"""Apply explicitly composed text to a unique current anchor; retain before/after and source map."""
from pathlib import Path
import csv,json,hashlib
ROOT=Path(__file__).resolve().parents[2]; WORK=ROOT/'revision_workspace/integration'
FIELDS=['position_id','target_file','section_or_label','original_anchor_sha256','source_candidates','related_comments','groups','final_text_path','evidence_paths','decision_basis','status']
def digest(s):return hashlib.sha256(s.encode()).hexdigest()
def apply(pid,target,old,new,comments,groups,sources,decision,section='',candidates=''):
 p=ROOT/target;txt=p.read_text();registry=WORK/'position_registry.csv'
 rows=list(csv.DictReader(registry.open())) if registry.exists() else []
 existing=[r for r in rows if r['position_id']==pid]
 if existing:
  assert new in txt,f'{pid} registered but final text no longer matches';return
 assert old and txt.count(old)==1,f'{pid}: expected one exact anchor, got {txt.count(old)}'
 dest=WORK/'final_text'/f'{pid}.tex';dest.parent.mkdir(exist_ok=True);dest.write_text(new+'\n')
 (WORK/'final_text'/f'{pid}.original.txt').write_text(old+'\n')
 p.write_text(txt.replace(old,new,1))
 rows.append(dict(position_id=pid,target_file=target,section_or_label=section,original_anchor_sha256=digest(old),source_candidates=candidates,related_comments=';'.join(comments),groups=';'.join(groups),final_text_path=str(dest.relative_to(ROOT)),evidence_paths=';'.join(sources),decision_basis=decision,status='implemented_pending_full_build_and_review'))
 with registry.open('w') as f:
  w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
 print('APPLIED',pid,target)

def amend(pid,new,comments=(),sources=(),decision=''):
 registry=WORK/'position_registry.csv';rows=list(csv.DictReader(registry.open()));row=next(r for r in rows if r['position_id']==pid)
 fragment=ROOT/row['final_text_path'];old=fragment.read_text().rstrip('\n');p=ROOT/row['target_file'];txt=p.read_text();assert txt.count(old)==1,f'{pid}: current registered block must be unique before amendment'
 archive=WORK/'amendments';archive.mkdir(exist_ok=True);n=len(list(archive.glob(pid+'.*.tex')))+1;(archive/f'{pid}.{n:03}.tex').write_text(old+'\n')
 p.write_text(txt.replace(old,new,1));fragment.write_text(new+'\n')
 row['related_comments']=';'.join(dict.fromkeys(row['related_comments'].split(';')+list(comments)))
 row['evidence_paths']=';'.join(dict.fromkeys(row['evidence_paths'].split(';')+list(sources)))
 row['decision_basis']+=' | Amendment: '+decision
 with registry.open('w') as f:
  w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader();w.writerows(rows)
 print('AMENDED',pid)
