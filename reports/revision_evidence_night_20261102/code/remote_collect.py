"""Read-only, bounded collection of existing final results; run over SSH stdin."""
import sys, json, hashlib, subprocess
from pathlib import Path
instance = int(sys.argv[1])
task = {3:'fdg_fold1',4:'fdg_fold2',5:'av45_fold1',6:'av45_fold2'}[instance]
root = Path('/root/autodl-tmp/DIRECTPP')
single = Path('/root/autodl-tmp/DIRECTPP_direct_single/20261030') / task
clinical = Path('/autodl-fs/data/DIRECTPP_classification_3fold/20261102_clinical')
files = []
if instance == 3:
    for name in ('summary.json','test_metrics.json','test_predictions.csv','clinical_preprocessing.json'):
        files.extend(clinical.glob('*/**/' + name))
files.extend(single.glob('**/complete.json'))
files.extend(single.glob('**/metrics.csv'))
files.extend(single.glob('formal/*.json'))
report = root / 'reports/direct_single_2fold_20261030' / task
for pattern in ('*complete.json','metrics_epoch*.csv','*exit*.json'):
    files.extend(report.glob(pattern))
for name in ('config.json','prepare_receipt.json'):
    files.append(root / 'reports/direct_single_2fold_20261030' / task / name)
records=[]
for p in sorted(set(files)):
    if p.is_file():
        b=p.read_bytes()
        records.append(dict(path=str(p),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b),text=b.decode()))
checkpoints=[dict(path=str(p),bytes=p.stat().st_size) for p in single.glob('formal/**/*') if p.suffix in ('.pt','.pth')]
print(json.dumps(dict(instance=instance,files=records,checkpoints=checkpoints,
    report_listing=[p.name for p in report.iterdir()] if report.exists() else [],
    train_tail=(report/'train.log').read_text()[-2000:] if (report/'train.log').exists() else '',
    processes=subprocess.check_output(['ps','-eo','pid,etime,args'],text=True),
    single_exists=single.exists())))
