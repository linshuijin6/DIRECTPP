from pathlib import Path
import json, hashlib, pandas as pd

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'reports/revision_evidence_night_20261102'
SPLIT='007e49835ed44c73dea69a94e390dded33c495c21033089f83d05b429519977c'
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for model,folder,ep in [('Full','original_author_reproduction_20261020',165),('ClinicalUNet','clinical_regression_unet_task_a_20261027_instance1',165),('TabularMLP','tabular_mlp_20261028_v3',165),('TracerOnly','tracer_only_control_20261027',165),('SwinUNETR','swinunetr_2fold_20261029',200)]:
    base=ROOT/'reports'/folder
    summary=base/('oof_launch_20261102T120914Z' if model=='SwinUNETR' else 'oof_summary')
    complete=json.loads((summary/'completion.json').read_text())
    p=summary/'per_subject_metrics.csv'
    key='metrics_sha256' if model=='SwinUNETR' else 'per_subject_sha256'
    assert digest(p)==complete[key], (model,key)
    data=pd.read_csv(p)
    data=data[data.epoch==ep]
    assert not data.duplicated(['ptid','tracer','fold']).any()
    assert len(data)==2963
    for (tracer,fold),s in data.groupby(['tracer','fold']):
        rows.append(dict(experiment=folder,model=model,tracer=tracer,fold=fold,epoch=ep,
            checkpoint=';'.join(s.checkpoint_sha256.unique()) if 'checkpoint_sha256' in s else 'see OOF receipt',
            split_hash=SPLIT,training_status='COMPLETE_AND_VERIFIED',inference_status='COMPLETE_AND_VERIFIED',
            prediction_count=len(s),metrics_status='COMPLETE_AND_VERIFIED' if model=='ClinicalUNet' else 'INFERENCE_DONE_SUMMARY_MISSING',
            status='COMPLETE_AND_VERIFIED' if model=='ClinicalUNet' else 'INFERENCE_DONE_SUMMARY_MISSING',missing_artifacts='none' if model=='ClinicalUNet' else 'requested final paired/distribution supplementary package',source=str(p.relative_to(ROOT))))
for n in (3,4,5,6):
    raw=OUT/'remote'/f'instance{n}_assets_v2.json'
    d=json.loads(raw.read_text())
    for r in d['files']:
        assert hashlib.sha256(r['text'].encode()).hexdigest()==r['sha256']
        p=Path(r['path'])
        category='clinical' if '/20261102_clinical/' in str(p) else f'single_instance{n}'
        rel=p.relative_to('/autodl-fs/data/DIRECTPP_classification_3fold/20261102_clinical') if category=='clinical' else Path(*p.parts[-3:])
        target=OUT/'remote'/category/rel
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(r['text'])
    task={3:'fdg_fold1',4:'fdg_fold2',5:'av45_fold1',6:'av45_fold2'}[n]
    receipt=next(json.loads(r['text']) for r in d['files'] if r['path'].endswith('checkpoint_epoch165.json'))
    finished=any(r['path'].endswith('training_complete.json') for r in d['files'])
    rows.append(dict(experiment='direct_single_2fold_20261030',model='Single',tracer=task.split('_')[0],fold=int(task[-1]),epoch=165,
        checkpoint=receipt['checkpoint_sha256'],split_hash=SPLIT,training_status='COMPLETE_AND_VERIFIED' if finished else 'PARTIAL',
        inference_status='TRAINED_INFERENCE_MISSING' if finished else 'BLOCKED',prediction_count=0,metrics_status='BLOCKED',
        status='TRAINED_INFERENCE_MISSING' if finished else 'BLOCKED',missing_artifacts='OOF165' if finished else '200-epoch training completion absent; logs stop at170; no live training; original infer refuses incomplete run',source=str(raw.relative_to(ROOT))))
for f in sorted((OUT/'remote/clinical').glob('*/**/summary.json')):
    d=json.loads(f.read_text()); print('clinical',d['task'],d['condition'],d['fold'],d.get('status'),d.get('test_evaluations'))
    rows.append(dict(experiment='clinical_baselines_20261102',model=d['condition'],tracer='NA',fold=d['fold'],epoch=d['epochs'],checkpoint=str(f.parent/'best_model.pth'),
        split_hash=d.get('splits_sha256','see run summary'),training_status='COMPLETE_AND_VERIFIED',inference_status='COMPLETE_AND_VERIFIED',prediction_count=len(pd.read_csv(f.parent/'test_predictions.csv')),
        metrics_status='INFERENCE_DONE_SUMMARY_MISSING',status='INFERENCE_DONE_SUMMARY_MISSING',missing_artifacts='final cross-fold summary and clinical comparisons/ROC',source=str(f.relative_to(ROOT))))
for fold in (1,2):
    f=ROOT/f'reports/r2_5_inference_score_removal_20261030/full/fold{fold}/complete.json'
    d=json.loads(f.read_text())
    rows.append(dict(experiment='E1_score_removal',model='E1_FullWeights_NoScores',tracer='both',fold=fold,epoch=165,checkpoint=d['checkpoint_sha256'],split_hash='E1 frozen; separate from W1',training_status='COMPLETE_AND_VERIFIED',inference_status='COMPLETE_AND_VERIFIED',prediction_count=d['volumes'],metrics_status='INFERENCE_DONE_SUMMARY_MISSING',status='INFERENCE_DONE_SUMMARY_MISSING',missing_artifacts='paired_summary',source=str(f.relative_to(ROOT))))
pd.DataFrame(rows).to_csv(OUT/'inventory.csv',index=False)
(OUT/'INVENTORY.md').write_text('# W0 verified inventory\n\nInitial inventory established before new inference. See inventory.csv and remote/*_assets_v2.json. Full/Clinical U-Net/Tabular-MLP/Tracer-only/Swin OOF already complete, metrics digests match completion receipts. Brain-mask completion and audit registered at reports/r3_11_brain_mask_metrics/run_20261102/; no masked recalculation authorized. E1 No-Scores full inference already complete. All18 clinical baseline result sets recovered. Single AV45 training complete; FDG missing200-epoch completion and no live process, blocked without training. Original files untouched.\n')
(OUT/'TASK_STATUS.md').write_text('# Task status\n\nW0 COMPLETE. W1 Single AV45 inference pending; FDG blocked. W3 clinical18 collection complete, verification/summary pending. W4 existing results located. W2/W5/W6/W7 pending. G8 OUT_OF_SCOPE.\n')
print('inventory',len(rows))
