from pathlib import Path
import json,hashlib,shutil
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102/G2';OUT.mkdir(exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
paths=['reports/original_author_reproduction_20261020/split_manifest.csv','reports/original_author_reproduction_20261020/cohort.json','reports/original_author_reproduction_20261020/config.json','reports/original_author_reproduction_20261020/input_hashes.csv','reports/r2_11_classification_3fold/splits.csv','reports/r2_11_classification_subjects.csv','experiments/classification_3fold/run.py']
pd.DataFrame([dict(path=p,sha256=sha(ROOT/p)) for p in paths]).to_csv(OUT/'split_and_source_hashes.csv',index=False)
cohort=pd.read_csv(ROOT/paths[0]);assert len(cohort)==1857 and cohort.ptid.nunique()==1857
full=pd.read_csv(ROOT/'reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv');full=full[full.epoch==165]
assert set(full.ptid)==set(cohort.ptid)
joined=full.merge(cohort[['ptid','test_fold']],on='ptid',validate='many_to_one');assert (joined.fold==joined.test_fold).all()
gen=[]
for fold in (1,2):
    test=set(cohort[cohort.test_fold==fold].ptid);train=set(cohort[cohort.test_fold!=fold].ptid)
    gen.append(dict(generator='W1 author-code Full',fold=fold,n_train=len(train),n_heldout=len(test),train_test_overlap=len(test&train),oof_subjects=full[full.fold==fold].ptid.nunique(),fdg_rows=len(full[(full.fold==fold)&(full.tracer=='fdg')]),av45_rows=len(full[(full.fold==fold)&(full.tracer=='av45')])))
pd.DataFrame(gen).to_csv(OUT/'generator_oof_coverage.csv',index=False)
split=pd.read_csv(ROOT/'reports/r2_11_classification_3fold/splits.csv');subjects=pd.read_csv(ROOT/'reports/r2_11_classification_subjects.csv');pred=pd.read_csv(ROOT/'reports/r2_11_classification_3fold/final_summary/oof_predictions.csv')
rows=[]
for (task,fold),s in split.groupby(['task','fold']):
    sets={k:set(v.PTID) for k,v in s.groupby('split')}
    assert not (sets['train']&sets['test'] or sets['validation']&sets['test'] or sets['train']&sets['validation'])
    rows.append(dict(task=task,fold=fold,train=len(sets['train']),validation=len(sets['validation']),test=len(sets['test']),train_test_overlap=0,val_test_overlap=0,n_outer_test_generator_cohort=len(sets['test']&set(cohort.ptid))))
    for condition,p in pred[(pred.task==task)&(pred.fold==fold)].groupby('condition'):
        assert set(p.PTID)==sets['test'] and len(p)==len(sets['test'])
assert not pred.duplicated(['task','condition','PTID']).any()
assert set(split[split.task=='mci_cn'].diagnosis_original)=={'CN','EMCI','LMCI'}
pd.DataFrame(rows).to_csv(OUT/'classification_outer_test_identity.csv',index=False)
(OUT/'REPORT.md').write_text('''# G2 split and reproducibility scope

W1 Full generation:1857 unique subjects, frozen two-fold929/928; training and each corresponding held-out set disjoint. OOF2963 valid subject–tracer rows (1598 FDG/1365 AV45), each fold agrees with the frozen manifest. The existing input manifest and completion/audit receipts are reused; no historical audit reopened. Split seed42; Full, TracerOnly, TabularMLP and Single use recorded unseeded training policy; no deterministic repeated-training claim.

Classification:63 imaging and18 clinical fits share task-specific fixed3-fold outer tests, internal15% validation. All9 task/fold train/validation/test role intersections are zero. Imaging11529 rows and clinical3294 rows have exact one-subject-one-condition outer-test coverage; positive classes AD, EMCI+LMCI, LMCI; original MCI/MCI-U excluded. Original QC subject016_S_4952 remains in this classification input, as frozen. Classification split seed42; fit seed42+100×task_index+fold. Validation ACC selects checkpoint, final test once, fixed200epochs; these are classification settings, not the generator endpoint.

The classification input source is reports/r2_11_classification_subjects.csv, referring to five historical data_augmentation_* directories. Existing report describes author-supplied two-fold OOF Syn-PET. This bounded check verifies actual classifier splits/predictions and file-source references, but does not bind those historical synthetic volumes to W1 reconstructed Full165 checkpoint hashes or independently recover their historical generator folds. Consequently this63-fit classification experiment is retained as its own input-asset family; it must not be presented as a new downstream test of the W1 generation comparison. The author's2-fold→3-fold design is respected, while execution-identity limitations remain explicit. Do not infer absence or presence of upstream leakage from shared subject names alone. Longitudinal visit-level matching and upstream clinical filling are not reassessed; G8 is out of scope.

Full/OT ROI analysis under full_ot_medical_evidence does bind W1 Full550ac2c4/f67e4a78 and TracerOnly573778ad/32b89214 predictions to E1 masks/targets. E1 score-removal instead binds f9455190/fc69fa4e. These checkpoint families are separate. No result is silently promoted from one family to the other.
''')
print('COMPLETE reproducibility',flush=True)
