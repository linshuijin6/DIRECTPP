"""Copy only completed frozen prediction files using disjoint file lists."""
import csv
import json
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
SWIN = ROOT / 'reports/swinunetr_2fold_20261029/oof_launch_20261102T120914Z'
PORTS = [44919, 22299, 15055, 51712]
TRANSFER = OUT / 'transfer'
TRANSFER.mkdir(exist_ok=True)
tasks = []
with (ROOT / 'reports/clinical_regression_unet_task_a_20261027_instance1/oof_summary/per_subject_metrics.csv').open() as stream:
    unet = [r for r in csv.DictReader(stream) if int(r['epoch']) == 165 and r['ptid'] != '016_S_4952']
base = '/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027/oof/epoch165/'
for shard in range(16):
    names = [str(Path('fold'+r['fold']) / Path(r['prediction']).name) for r in unet[shard::16]]
    tasks.append(('unet_'+str(shard), PORTS[shard % 4], base, OUT / 'inputs/clinical_unet_epoch165', names, shard%2))
assert (SWIN / 'completion.json').is_file(), 'Require completed Swin OOF; never infer here'
with (SWIN / 'per_subject_metrics.csv').open() as stream:
    swin = [r for r in csv.DictReader(stream) if r['ptid'] != '016_S_4952']
for index, (tracer, fold) in enumerate([('FDG',1),('FDG',2),('AV45',1),('AV45',2)]):
    group = [r for r in swin if r['tracer']==tracer and int(r['fold'])==fold]
    for shard in range(4):
        base = str(Path(group[0]['prediction']).parent) + '/'
        tasks.append(('swin_'+str(index)+'_'+str(shard), PORTS[index], base,
                      OUT / 'inputs/swinunetr_epoch200' / (tracer.lower()+'_fold'+str(fold)),
                      [Path(r['prediction']).name for r in group[shard::4]], shard%2))


def copy(task):
    name, port, source, destination, names, proxy = task
    destination.mkdir(parents=True, exist_ok=True)
    files = TRANSFER / (name+'.files.txt')
    files.write_text('\n'.join(names)+'\n')
    ssh = 'ssh -o BatchMode=yes -o ConnectTimeout=12 -p '+str(port)
    if proxy:
        ssh += ' -o "ProxyCommand=ssh -o BatchMode=yes 3002 -W %h:%p"'
    command = ['rsync','-a','--ignore-existing','--files-from='+str(files),'-e',ssh,
               'root@connect.westb.seetacloud.com:'+source,str(destination)+'/']
    started = time.time()
    with (TRANSFER/(name+'.log')).open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        receipt = {'name':name,'pid':process.pid,'source':source,'destination':str(destination),
                   'files':len(names),'started_epoch':started,'command':command}
        (TRANSFER/(name+'.start.json')).write_text(json.dumps(receipt,indent=2)+'\n')
        result = process.wait()
    receipt.update(returncode=result,finished_epoch=time.time())
    (TRANSFER/(name+'.exit.json')).write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'shard':name,'returncode':result,'seconds':time.time()-started}),flush=True)
    return receipt


with ThreadPoolExecutor(max_workers=32) as pool:
    results=list(pool.map(copy,tasks))
(TRANSFER/'completion.json').write_text(json.dumps({'all_successful':all(r['returncode']==0 for r in results),'shards':results},indent=2)+'\n')
assert all(r['returncode']==0 for r in results), 'Transfer failure; inspect per-shard logs'
