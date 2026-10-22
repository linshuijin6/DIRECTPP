"""Read-only targeted author history and data-directory metadata collection."""
from pathlib import Path
import json
import subprocess

OUT = Path(__file__).resolve().parent
REMOTE = r'''
import os,json,sqlite3,hashlib
from pathlib import Path
node=NODE
home=Path(HOME)
result={'node':node,'home':str(home),'directories':[]}
for path in [home,home/'liutuo_data',home/'liutuo_data/test1']:
 record={'path':str(path),'exists':path.exists()}
 try:
  entries=list(path.iterdir())
  record['children']=[{'name':p.name,'is_dir':p.is_dir(),'is_symlink':p.is_symlink()} for p in sorted(entries)]
 except Exception as e:record['error']=str(e)
 result['directories'].append(record)
history=home/'.ipython/profile_default/history.sqlite'
if not history.exists() and (home.parent/'.ipython/profile_default/history.sqlite').exists():
 history=home.parent/'.ipython/profile_default/history.sqlite'
result['history_path']=str(history)
try:
 db=sqlite3.connect('file:'+str(history)+'?mode=ro&immutable=1',uri=True)
 sql="""SELECT h.session,h.line,h.source_raw,s.start FROM history h
 LEFT JOIN sessions s ON h.session=s.session WHERE
 h.source_raw LIKE '%PSNRMetric%' OR h.source_raw LIKE '%structural_similarity%'
 OR h.source_raw LIKE '%mean_psnr%' OR h.source_raw LIKE '%67.82%'
 OR h.source_raw LIKE '%59.56%' OR h.source_raw LIKE '%40.27%'"""
 rows=[dict(zip(['session','input_line','source_raw','start_as_stored'],r)) for r in db.execute(sql)]
 for r in rows:r['source_sha256']=hashlib.sha256(r['source_raw'].encode()).hexdigest()
 result['history_matches']=rows
 result['history_bytes']=history.stat().st_size
 result['history_sha256']=hashlib.sha256(history.read_bytes()).hexdigest()
 result['wal_exists']=Path(str(history)+'-wal').exists()
 db.close()
except Exception as e:result['history_error']=str(e)
print(json.dumps(result,ensure_ascii=False))
'''

for node, home in [('3002','/home/ssddata/liutuo'),('3003','/home/data/liutuo/code')]:
    source = REMOTE.replace('node=NODE',f'node={node!r}').replace('Path(HOME)',f'Path({home!r})')
    completed = subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10',node,'python3 -'],
                               input=source,text=True,capture_output=True,timeout=90)
    if completed.returncode:
        print(node,completed.stderr[-1500:])
        continue
    result=json.loads(completed.stdout)
    (OUT/f'{node}_author_metric_history_and_roots.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(node,'matched_inputs',len(result.get('history_matches',[])),result.get('history_error',''))
    for directory in result['directories']:
        print(directory['path'],[x['name'] for x in directory.get('children',[]) if x['is_dir']])
