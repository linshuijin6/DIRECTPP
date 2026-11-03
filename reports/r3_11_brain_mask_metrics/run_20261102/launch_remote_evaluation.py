"""Launch only masked evaluation of existing frozen baseline predictions."""
import argparse
import json
import shlex
import subprocess
import time
from pathlib import Path

OUT=Path(__file__).resolve().parent
REMOTE='/root/autodl-fs/DIRECTPP_r3_11_brain_mask_metrics/run_20261102'
p=argparse.ArgumentParser();p.add_argument('phase',choices=['pilot','full']);p.add_argument('--attempt',type=int,default=1);args=p.parse_args()
phase=args.phase if args.attempt==1 else args.phase+'_attempt'+str(args.attempt)
records=[]
for port,tracer,fold in [(44919,'fdg',1),(22299,'fdg',2),(15055,'av45',1),(51712,'av45',2)]:
    control=REMOTE+'/'+phase+'/'+tracer+'_fold'+str(fold)
    command=['/root/miniconda3/bin/python','-u',REMOTE+'/code/remote_evaluate.py',
        '--tracer',tracer,'--fold',str(fold),'--inputs',REMOTE+'/inputs','--output',control+'/results']
    if args.phase=='pilot':command.append('--pilot')
    supervisor=f'''import subprocess,os,json,time
from pathlib import Path
folder=Path({control!r})
env=os.environ.copy();env.update(CUDA_VISIBLE_DEVICES='0',OMP_NUM_THREADS='2',MKL_NUM_THREADS='2')
with (folder/'evaluate.log').open('x') as log:
 child=subprocess.Popen({command!r},env=env,stdout=log,stderr=subprocess.STDOUT)
 (folder/'start.json').write_text(json.dumps({{'pid':child.pid,'started_epoch':time.time(),'command':{command!r},'scope':'Frozen-image metrics only; no model forward/generation'}},indent=2)+'\\n')
 rc=child.wait()
(folder/'exit.json').write_text(json.dumps({{'returncode':rc,'finished_epoch':time.time()}},indent=2)+'\\n')
'''
    launch=f'''from pathlib import Path
import subprocess,json,time
folder=Path({control!r});folder.mkdir(parents=True,exist_ok=False)
(folder/'supervisor.py').write_text({supervisor!r})
with (folder/'supervisor.log').open('x') as log:
 p=subprocess.Popen(['/root/miniconda3/bin/python',str(folder/'supervisor.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
print(json.dumps({{'control':str(folder),'supervisor_pid':p.pid}}))
'''
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-p',str(port),
        'root@connect.westb.seetacloud.com','/root/miniconda3/bin/python -c '+shlex.quote(launch)],capture_output=True,text=True,timeout=25)
    assert r.returncode==0,r.stderr
    records.append({'port':port,'tracer':tracer,'fold':fold,**json.loads(r.stdout)})
    print(json.dumps(records[-1]),flush=True)
(OUT/('remote_'+phase+'_launch.json')).write_text(json.dumps(records,indent=2)+'\n')
