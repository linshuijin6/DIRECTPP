"""Launch/fetch read-only frozen target-reference transport jobs."""
import argparse,concurrent.futures,hashlib,json,shlex,subprocess,time
from pathlib import Path
OUT=Path(__file__).resolve().parent
SHARED='/root/autodl-fs/DIRECTPP_r3_11_brain_mask_metrics/run_20261102'
JOBS=[('fdg',1,44919),('fdg',2,22299),('av45',1,15055),('av45',2,51712)]
p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','fetch']);p.add_argument('phase',choices=['crc','exceptions']);a=p.parse_args()
if a.action=='launch':
    records=[]
    for tracer,fold,port in JOBS:
        task=tracer+'_fold'+str(fold);folder='/root/autodl-tmp/DIRECTPP_r3_11_canonical/'+task+'_'+a.phase
        command=['/root/miniconda3/bin/python','-u',SHARED+'/code/export_target_blocks.py','--index',SHARED+'/inputs/mismatch_index.csv','--tracer',tracer,'--fold',str(fold),'--out',folder+'/results']
        if a.phase=='exceptions':command+=['--requests',SHARED+'/canonical_requests/requests_'+task+'.zip']
        supervisor=f'''import subprocess,json,time
from pathlib import Path
p=Path({folder!r})
with (p/'export.log').open('x') as log:
 child=subprocess.Popen({command!r},stdout=log,stderr=subprocess.STDOUT)
 (p/'start.json').write_text(json.dumps({{'pid':child.pid}}))
 rc=child.wait()
(p/'exit.json').write_text(json.dumps({{'returncode':rc,'finished_epoch':time.time()}}))
'''
        code=f'''import subprocess,json
from pathlib import Path
p=Path({folder!r});p.mkdir(parents=True,exist_ok=False)
(p/'supervisor.py').write_text({supervisor!r})
with (p/'supervisor.log').open('x') as log:q=subprocess.Popen(['/root/miniconda3/bin/python',str(p/'supervisor.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({{'supervisor_pid':q.pid}}))
'''
        r=subprocess.run(['ssh','-o','BatchMode=yes','-p',str(port),'root@connect.westb.seetacloud.com','/root/miniconda3/bin/python -c '+shlex.quote(code)],capture_output=True,text=True,timeout=25)
        assert r.returncode==0,r.stderr
        records.append({'task':task,'port':port,'remote_folder':folder,**json.loads(r.stdout)})
    (OUT/(a.phase+'_launch.json')).write_text(json.dumps(records,indent=2)+'\n');print('Launched',a.phase,flush=True)
else:
    records=json.loads((OUT/(a.phase+'_launch.json')).read_text())
    def fetch(r):
        folder=OUT/a.phase/r['task'];folder.mkdir(parents=True,exist_ok=False)
        ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-p',str(r['port']),'root@connect.westb.seetacloud.com']
        while True:
            q=subprocess.run(ssh+['cat '+r['remote_folder']+'/exit.json'],capture_output=True,text=True,timeout=25)
            if q.returncode==0:
                assert json.loads(q.stdout)['returncode']==0,q.stdout
                break
            time.sleep(10)
        for name in ['complete.json',('block_crc.zip' if a.phase=='crc' else 'exceptions.zip')]:
            q=subprocess.run(['scp','-q','-o','BatchMode=yes','-P',str(r['port']),'root@connect.westb.seetacloud.com:'+r['remote_folder']+'/results/'+name,str(folder/name)],capture_output=True,text=True)
            assert q.returncode==0,q.stderr
        receipt=json.loads((folder/'complete.json').read_text())
        assert hashlib.sha256((folder/receipt['payload']).read_bytes()).hexdigest()==receipt['sha256']
        print(json.dumps({'task':r['task'],'bytes':receipt['bytes']}),flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,records))
