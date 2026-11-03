"""Finish exact target transport, baseline metric rechecks, and final statistics."""
import concurrent.futures,hashlib,importlib.util,json,shlex,subprocess,time,traceback
from pathlib import Path
OUT=Path(__file__).resolve().parent;RUN=OUT.parent;ROOT=OUT.parents[3]
PYTHON='/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python'
SHARED='/root/autodl-fs/DIRECTPP_r3_11_brain_mask_metrics/run_20261102'
JOBS=[('fdg',1,44919),('fdg',2,22299),('av45',1,15055),('av45',2,51712)]


def stage(name):
    print(time.strftime('%Y-%m-%d %H:%M:%S'),name,flush=True)
    temp=OUT/'stage_status.tmp';temp.write_text(json.dumps({'stage':name,'epoch':time.time()},indent=2)+'\n');temp.replace(OUT/'stage_status.json')


def command(args):subprocess.run(args,check=True,cwd=ROOT)


def ssh(port,code):
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-p',str(port),'root@connect.westb.seetacloud.com',code],capture_output=True,text=True,timeout=30)
    if r.returncode:raise RuntimeError(r.stderr)
    return r.stdout


def upload(paths,destination):
    command(['scp','-q','-o','BatchMode=yes','-P','44919',*[str(p) for p in paths],
             'root@connect.westb.seetacloud.com:'+destination+'/'])


def run():
    stage('Waiting for lossless reference block requests')
    while not (OUT/'requests/request_summary.json').is_file():time.sleep(5)
    stage('Exporting exact exceptional reference blocks')
    ssh(44919,'mkdir -p '+SHARED+'/canonical_requests '+SHARED+'/canonical_patches')
    upload(sorted((OUT/'requests').glob('requests_*.zip')),SHARED+'/canonical_requests')
    command([PYTHON,str(OUT/'transport_control.py'),'launch','exceptions'])
    command([PYTHON,str(OUT/'transport_control.py'),'fetch','exceptions'])
    stage('Verifying all original reference and canonical target array hashes')
    command([PYTHON,str(OUT/'reference_transport.py'),'finalize'])
    stage('Transferring exact canonical target payloads')
    upload(sorted((OUT/'exact_patches').glob('patches_*.zip'))+[OUT/'exact_patches/patch_receipts.json'],SHARED+'/canonical_patches')
    stage('Recomputing 2802 baseline metric rows with exact canonical targets')
    records=[]
    for tracer,fold,port in JOBS:
        task=tracer+'_fold'+str(fold);folder='/root/autodl-tmp/DIRECTPP_r3_11_canonical/'+task+'_recheck'
        args=['/root/miniconda3/bin/python','-u',SHARED+'/code/canonical_recheck.py',
              '--tracer',tracer,'--fold',str(fold),'--inputs',SHARED+'/inputs',
              '--patches',SHARED+'/canonical_patches','--out',folder+'/results']
        supervisor=f'''import subprocess,os,json,time
from pathlib import Path
p=Path({folder!r});env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
with (p/'evaluate.log').open('x') as log:
 child=subprocess.Popen({args!r},env=env,stdout=log,stderr=subprocess.STDOUT)
 (p/'start.json').write_text(json.dumps({{'pid':child.pid,'started_epoch':time.time(),'scope':'Metrics only, frozen predictions and exact canonical target bytes'}}))
 rc=child.wait()
(p/'exit.json').write_text(json.dumps({{'returncode':rc,'finished_epoch':time.time()}}))
'''
        starter=f'''import subprocess,json
from pathlib import Path
p=Path({folder!r});p.mkdir(parents=True,exist_ok=False);(p/'supervisor.py').write_text({supervisor!r})
with (p/'supervisor.log').open('x') as log:q=subprocess.Popen(['/root/miniconda3/bin/python',str(p/'supervisor.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({{'supervisor_pid':q.pid}}))
'''
        result=json.loads(ssh(port,'/root/miniconda3/bin/python -c '+shlex.quote(starter)))
        records.append({'task':task,'port':port,'folder':folder,**result})
    (OUT/'recheck_launch.json').write_text(json.dumps(records,indent=2)+'\n')
    def fetch(r):
        while True:
            try:result=json.loads(ssh(r['port'],'cat '+r['folder']+'/exit.json'))
            except (RuntimeError,subprocess.TimeoutExpired):time.sleep(10);continue
            assert result['returncode']==0,(r,result)
            break
        folder=OUT/'recheck_results'/r['task'];folder.mkdir(parents=True,exist_ok=False)
        for name in ['complete.json','metrics.csv','asset_checks.jsonl']:
            command(['scp','-q','-o','BatchMode=yes','-P',str(r['port']),
                     'root@connect.westb.seetacloud.com:'+r['folder']+'/results/'+name,str(folder/name)])
        receipt=json.loads((folder/'complete.json').read_text())
        for name,key in [('metrics.csv','metrics_sha256'),('asset_checks.jsonl','asset_checks_sha256')]:
            assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==receipt[key]
        (folder/'exit.json').write_text(json.dumps(result,indent=2)+'\n')
        print('Recheck complete:',r['task'],receipt['metric_rows'],flush=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(fetch,records))
    stage('Assembling strictly matched data and computing paired statistics')
    spec=importlib.util.spec_from_file_location('collection',RUN/'collect_and_analyze.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    module.assemble(corrections=True)
    command([PYTHON,str(RUN.parent/'analysis.py'),'summarize'])
    command([PYTHON,str(RUN.parent/'deliver.py')])
    stage('COMPLETE numerical analysis and draft tables; ready for final rendered verification')


if __name__=='__main__':
    try:run()
    except Exception:
        (OUT/'continuation_failure.txt').write_text(traceback.format_exc());raise
