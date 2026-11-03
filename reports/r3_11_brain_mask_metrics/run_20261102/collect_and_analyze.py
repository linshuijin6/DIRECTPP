"""Collect metric-only jobs, require complete identities, then analyze results."""
import concurrent.futures
import csv
import hashlib
import json
import shlex
import subprocess
import time
from pathlib import Path

import pandas as pd

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[2]
PYTHON='/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python'
REMOTE='/root/autodl-fs/DIRECTPP_r3_11_brain_mask_metrics/run_20261102/full'
TASKS=['fdg_fold1','fdg_fold2','av45_fold1','av45_fold2']


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def remote_probe():
    code='''import json,hashlib
from pathlib import Path
root=Path(ROOT)
result=[]
for name in TASKS:
 folder=root/name
 record={'task':name,'exit':json.loads((folder/'exit.json').read_text()) if (folder/'exit.json').exists() else None}
 log=(folder/'evaluate.log').read_text() if (folder/'evaluate.log').exists() else ''
 record['log_tail']=log.splitlines()[-2:]
 path=folder/'results/metrics.csv'
 record['metric_rows']=max(0,len(path.read_text().splitlines())-1) if path.exists() else 0
 if record['exit'] and record['exit']['returncode']==0:
  receipt=json.loads((folder/'results/complete.json').read_text())
  metrics=path.read_bytes();assets=(folder/'results/asset_checks.jsonl').read_bytes()
  assert hashlib.sha256(metrics).hexdigest()==receipt['metrics_sha256']
  assert hashlib.sha256(assets).hexdigest()==receipt['asset_checks_sha256']
  record.update(receipt=receipt,metrics_csv=metrics.decode(),asset_checks=assets.decode())
 result.append(record)
print(json.dumps(result))
'''.replace('ROOT',repr(REMOTE)).replace('TASKS',repr(TASKS))
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=12','-p','44919',
        'root@connect.westb.seetacloud.com','/root/miniconda3/bin/python -c '+shlex.quote(code)],capture_output=True,text=True,timeout=40)
    assert r.returncode==0,r.stderr
    return json.loads(r.stdout)


def assemble(corrections=False):
    frames=[pd.read_csv(OUT/'metrics_Full_seed.csv')]
    assets=[json.loads(line) for line in (OUT/'subject_asset_checks_seed.jsonl').read_text().splitlines()]
    for shard in range(4):
        receipt=json.loads((OUT/f'full_part{shard}_exit.json').read_text())
        assert receipt['returncode']==0
        frames.append(pd.read_csv(OUT/f'metrics_Full_part{shard}.csv'))
        assets.extend(json.loads(line) for line in (OUT/f'subject_asset_checks_part{shard}.jsonl').read_text().splitlines())
    assert len(assets)==1856 and len({r['ptid'] for r in assets})==1856
    for task in TASKS:
        folder=OUT/'remote_results'/task
        receipt=json.loads((folder/'complete.json').read_text())
        assert sha(folder/'metrics.csv')==receipt['metrics_sha256']
        assert sha(folder/'asset_checks.jsonl')==receipt['asset_checks_sha256']
        assert receipt['input_index_sha256']==sha(OUT/'input_index.csv')
        assert receipt['evaluator_sha256']==sha(OUT/'source_snapshots/remote_evaluate_initial.py')
        assert receipt['shared_metrics_sha256']==sha(OUT.parent/'masked_metrics.py')
        frames.append(pd.read_csv(folder/'metrics.csv'))
    df=pd.concat(frames,ignore_index=True)
    index=pd.read_csv(OUT/'input_index.csv')
    key=['model','ptid','tracer','fold','epoch']
    assert len(df)==8883 and not df.duplicated(key).any()
    assert set(map(tuple,df[key].values))==set(map(tuple,index[key].values))
    if corrections:
        corrected=[]
        for task in TASKS:
            folder=OUT/'canonical_targets/recheck_results'/task
            receipt=json.loads((folder/'complete.json').read_text())
            assert receipt['status']=='COMPLETE_EXACT_CANONICAL_TARGET_RECHECK'
            assert sha(folder/'metrics.csv')==receipt['metrics_sha256']
            assert sha(folder/'asset_checks.jsonl')==receipt['asset_checks_sha256']
            assert receipt['evaluator_sha256']==sha(OUT.parent/'canonical_recheck.py')
            corrected.append(pd.read_csv(folder/'metrics.csv'))
        replacement=pd.concat(corrected,ignore_index=True)
        assert len(replacement)==2802 and not replacement.duplicated(key).any()
        original=df.set_index(key)
        update=replacement.set_index(key)
        assert set(update.index)<=set(original.index)
        assert (original.loc[update.index,'prediction_sha256']==update.prediction_sha256).all()
        assert (original.loc[update.index,'checkpoint_sha256']==update.checkpoint_sha256).all()
        assert (original.loc[update.index,'brain_mask_array_sha256']==update.brain_mask_array_sha256).all()
        audit=original.loc[update.index].join(update,lsuffix='_initial',rsuffix='_canonical')
        audit.to_csv(OUT/'canonical_targets/replaced_metrics_audit.csv')
        original.loc[update.index,update.columns]=update
        df=original.reset_index()
        assert len(df)==8883
    matched=df.merge(index,on=key,validate='one_to_one',suffixes=('_actual','_index'))
    assert (matched.prediction_sha256==matched.prediction_sha256_expected).all()
    assert (matched.checkpoint_sha256_actual==matched.checkpoint_sha256_index).all()
    for _,g in df.groupby(['ptid','tracer','fold']):
        assert len(g)==3 and g.target_array_sha256.nunique()==1 and g.brain_mask_array_sha256.nunique()==1
    df['model']=pd.Categorical(df.model,categories=['Full','ClinicalUNet','SwinUNETR'],ordered=True)
    df.sort_values(['model','tracer','fold','ptid']).to_csv(OUT/'per_subject_metrics.csv',index=False)
    matched.to_csv(OUT/'evaluation_input_manifest.csv',index=False)
    old=OUT/'subject_asset_checks.jsonl'
    if old.exists():old.rename(OUT/'subject_asset_checks_before_assemble.jsonl')
    (OUT/'subject_asset_checks.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in sorted(assets,key=lambda r:r['ptid'])))
    print('Assembled 8883 exact matched model/tracer/fold rows',flush=True)


def main():
    collected=set()
    deadline=time.monotonic()+10800
    while time.monotonic()<deadline:
        try:remote=remote_probe()
        except Exception as error:
            print('Probe error:',str(error),flush=True);time.sleep(25);continue
        for r in remote:
            if r['exit'] and r['exit']['returncode']:
                (OUT/'remote_failure.json').write_text(json.dumps(r,indent=2)+'\n')
                raise RuntimeError('Remote evaluation failed: '+r['task'])
            if 'receipt' in r:
                folder=OUT/'remote_results'/r['task']
                if r['task'] not in collected:
                    folder.mkdir(parents=True,exist_ok=False)
                    (folder/'metrics.csv').write_text(r['metrics_csv'])
                    (folder/'asset_checks.jsonl').write_text(r['asset_checks'])
                    (folder/'complete.json').write_text(json.dumps(r['receipt'],indent=2)+'\n')
                    (folder/'exit.json').write_text(json.dumps(r['exit'],indent=2)+'\n')
                    collected.add(r['task'])
                del r['metrics_csv'];del r['asset_checks']
        full=[];ready=True
        for shard in range(4):
            exitpath=OUT/f'full_part{shard}_exit.json'
            record=json.loads(exitpath.read_text()) if exitpath.exists() else None
            if record:assert record['returncode']==0,record
            else:ready=False
            path=OUT/f'metrics_Full_part{shard}.csv'
            count=max(0,len(path.read_text().splitlines())-1) if path.exists() else 0
            full.append({'shard':shard,'metric_rows':count,'exit':record})
        status={'observed_epoch':time.time(),'full_seed_rows':len(pd.read_csv(OUT/'metrics_Full_seed.csv')),'full_shards':full,'remote':remote}
        temporary=OUT/'progress.tmp';temporary.write_text(json.dumps(status,indent=2)+'\n');temporary.replace(OUT/'progress.json')
        print(json.dumps({'full_rows':status['full_seed_rows']+sum(r['metric_rows'] for r in full),'baseline_rows':sum(r['metric_rows'] for r in remote),'remote_complete_tasks':len(collected)}),flush=True)
        if ready and len(collected)==4:
            assemble()
            for command in [[PYTHON,str(OUT.parent/'analysis.py'),'summarize'],[PYTHON,str(OUT.parent/'deliver.py')]]:
                subprocess.run(command,check=True,cwd=ROOT)
            return
        time.sleep(25)
    raise TimeoutError('Timed out observing metrics; no source/GPU jobs stopped')


if __name__=='__main__':
    try:main()
    except Exception:
        import traceback
        (OUT/'collection_failure.txt').write_text(traceback.format_exc())
        raise
