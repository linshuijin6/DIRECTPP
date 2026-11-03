"""Observe the four authorized remote jobs and collect completed OOF metrics.

This script never launches, restarts, or terminates GPU work. Prediction images
stay on their respective instances; only metrics and receipts are collected.
"""
import concurrent.futures
import csv
import hashlib
import io
import json
import math
import shlex
import statistics
import subprocess
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
JOBS = json.loads((HERE / 'launch.json').read_text())
FULL = ROOT / 'reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv'
EXPECTED = {3: 792, 4: 806, 5: 690, 6: 675}
METRICS = ('ssim', 'psnr', 'mse', 'mae')


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def remote_status(job):
    code = '''import json,time,hashlib
from pathlib import Path
folder=Path(FOLDER)
start=json.loads((folder/'start.json').read_text())
output=Path(start['output'])
log=(folder/'infer.log').read_text()
rows=[]
for line in log.splitlines():
 try:
  row=json.loads(line)
  if 'ptid' in row:rows.append(row)
 except (ValueError,TypeError):pass
times=sorted(p.stat().st_mtime for p in output.glob('generated_*.nii.gz'))
exit_record=json.loads((folder/'exit.json').read_text()) if (folder/'exit.json').exists() else None
result={'observed_time':time.time(),'start':start,'exit':exit_record,'completed_subjects':len(rows),'prediction_files':len(times),'seconds_per_subject':(times[-1]-times[0])/(len(times)-1) if len(times)>1 else None,'error_tail':log.splitlines()[-15:] if exit_record and exit_record['returncode'] else []}
if exit_record and exit_record['returncode']==0:
 receipt=json.loads((output/'complete.json').read_text())
 data=(output/'metrics.csv').read_bytes()
 assert hashlib.sha256(data).hexdigest()==receipt['metrics_sha256']
 assert receipt['status']=='COMPLETE_FOLD_OOF'
 assert receipt['epoch']==200
 for row in rows:
  prediction=Path(row['prediction'])
  assert prediction.is_file() and prediction.stat().st_size>0
 result.update(receipt=receipt,metrics_csv=data.decode(),predictions_exist=True)
print(json.dumps(result))
'''.replace('FOLDER', repr(job['remote_folder']))
    result = subprocess.run(
        ['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=12', '-p',
         str(job['port']), 'root@connect.westb.seetacloud.com',
         '/root/miniconda3/bin/python -c ' + shlex.quote(code)],
        capture_output=True, text=True, timeout=35,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip())
    return {'instance': job['instance'], 'tracer': job['tracer'],
            'fold': job['fold'], 'expected_subjects': EXPECTED[job['instance']],
            **json.loads(result.stdout)}


def key(row):
    return row['ptid'], row['tracer'].upper(), int(row['fold'])


def write_csv(path, rows):
    with path.open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def finalize():
    full_rows = [r for r in csv.DictReader(FULL.open()) if int(r['epoch']) == 165]
    reference = {key(row): row for row in full_rows}
    assert len(reference) == len(full_rows)
    all_rows = []
    for job in JOBS:
        folder = HERE / ('instance' + str(job['instance']))
        receipt = json.loads((folder / 'complete.json').read_text())
        data = (folder / 'metrics.csv').read_bytes()
        assert hashlib.sha256(data).hexdigest() == receipt['metrics_sha256']
        rows = list(csv.DictReader(io.StringIO(data.decode())))
        assert len(rows) == receipt['metric_rows'] == EXPECTED[job['instance']]
        for row in rows:
            assert row['tracer'] == job['tracer'] and int(row['fold']) == job['fold']
            assert int(row['epoch']) == 200
            assert row['checkpoint_sha256'] == receipt['checkpoint_sha256']
            assert all(math.isfinite(float(row[m])) for m in METRICS)
        all_rows.extend(rows)
    identities = {key(row) for row in all_rows}
    assert len(identities) == len(all_rows) and identities == set(reference)
    all_rows.sort(key=key)
    write_csv(HERE / 'per_subject_metrics.csv', all_rows)
    summary = []
    for tracer in ('FDG', 'AV45'):
        for fold in (1, 2, 'all'):
            group = [r for r in all_rows if r['tracer'] == tracer
                     and (fold == 'all' or int(r['fold']) == fold)]
            row = {'tracer': tracer, 'fold': fold, 'n': len(group)}
            for metric in METRICS:
                values = [float(r[metric]) for r in group]
                row[metric + '_mean'] = statistics.mean(values)
                row[metric + '_sd'] = statistics.stdev(values)
            summary.append(row)
    write_csv(HERE / 'summary.csv', summary)
    save_json(HERE / 'completion.json', {
        'status': 'COMPLETE_SWINUNETR_TWO_FOLD_OOF',
        'completed_utc': datetime.now(timezone.utc).isoformat(),
        'epoch': 200, 'metric_rows': len(all_rows),
        'identity_reference': str(FULL), 'identity_reference_epoch': 165,
        'one_to_one_reference_identity_match': True,
        'metrics_sha256': hashlib.sha256((HERE / 'per_subject_metrics.csv').read_bytes()).hexdigest(),
        'summary_sha256': hashlib.sha256((HERE / 'summary.csv').read_bytes()).hexdigest(),
        'prediction_images': 'Retained on original remote instances; existence and nonzero size checked; image hashes not rechecked by collector',
        'summary_policy': 'Subject-weighted means; sample standard deviations; raw metric scale',
    })


def main():
    collected = {}
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline:
        statuses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = {pool.submit(remote_status, j): j for j in JOBS if j['instance'] not in collected}
            for future, job in futures.items():
                try:
                    status = future.result()
                except Exception as error:
                    status = {'instance': job['instance'], 'connection_error': str(error)}
                if status.get('exit') and status['exit']['returncode']:
                    save_json(HERE / 'failure.json', status)
                    raise RuntimeError('Remote inference failed: instance ' + str(job['instance']))
                if 'metrics_csv' in status:
                    folder = HERE / ('instance' + str(job['instance']))
                    folder.mkdir(exist_ok=False)
                    (folder / 'metrics.csv').write_bytes(status.pop('metrics_csv').encode())
                    save_json(folder / 'complete.json', status['receipt'])
                    save_json(folder / 'collection.json', status)
                    collected[job['instance']] = status
                statuses.append(status)
        statuses.extend(v for k, v in collected.items() if k not in {s['instance'] for s in statuses})
        save_json(HERE / 'status.json', {'observed_utc': datetime.now(timezone.utc).isoformat(), 'instances': sorted(statuses, key=lambda x: x['instance'])})
        if len(collected) == 4:
            finalize()
            return
        time.sleep(25)
    raise TimeoutError('Collection exceeded two hours; remote jobs were not stopped')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        (HERE / 'collector_error.txt').write_text(traceback.format_exc())
        raise
