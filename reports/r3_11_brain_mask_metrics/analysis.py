"""R3-11: evaluate frozen OOF arrays; never train or generate predictions."""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import importlib.util
import io
import json
import math
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
import torch
from scipy import ndimage, stats

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent / 'run_20261102'
E1 = ROOT / 'reports/e1_stage01_20261017'
FULL = ROOT / 'reports/original_author_reproduction_20261020'
UNET = ROOT / 'reports/clinical_regression_unet_task_a_20261027_instance1'
SWIN = ROOT / 'reports/swinunetr_2fold_20261029/oof_launch_20261102T120914Z'
METRICS = ('ssim', 'psnr', 'mse', 'mae')
SHAPE = (160, 192, 160)
sys.path.insert(0, str(ROOT / 'experiments/e1_clinical_conditioning'))
sys.path.insert(0, str(ROOT / 'source_archive/vscode-3002/home/ssddata/liutuo'))
from evaluate import image_metrics as e1_image_metrics
from generative.metrics.ssim import compute_ssim_and_cs
from masked_metrics import metric_values


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


prior = load_module('prior_paired', ROOT / 'reports/clinical_regression_unet_e165_paired_analysis_20261028/analysis.py')


def sha(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b''):
            value.update(block)
    return value.hexdigest()


def jread(path):
    return json.loads(Path(path).read_text())


def jsave(path, value):
    path = Path(path)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n')
    temporary.replace(path)


def csvread(path):
    with Path(path).open(newline='') as stream:
        return list(csv.DictReader(stream))


def csvsave(path, rows):
    with Path(path).open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def identity(r):
    return r['ptid'], r['tracer'].lower(), int(r['fold'])


def prepare():
    OUT.mkdir(exist_ok=True, parents=True)
    _, audit = prior.audit_and_join(ROOT, prior.resolve_inputs(ROOT))
    jsave(OUT / 'prior_matched_input_audit.json', audit)
    config = jread(E1 / 'config.json')
    frozen = config['frozen_files']
    checks = {}
    for name in ('cohort.json', 'input_hashes_final.csv', 'qc_exclusions.json', 'roi_labels.csv'):
        path = E1 / name
        actual = sha(path)
        assert actual == frozen[str(path)], name
        checks[str(path)] = actual
    full_inputs = {(r['ptid'], r['kind']): (r['path'], r['sha256'], r['bytes']) for r in csvread(FULL / 'input_hashes.csv')}
    e1_inputs = {(r['ptid'], r['kind']): (r['path'], r['sha256'], r['bytes']) for r in csvread(E1 / 'input_hashes_final.csv')}
    overlap = set(full_inputs) & set(e1_inputs)
    assert len(overlap) == 5571 and all(full_inputs[k] == e1_inputs[k] for k in overlap)
    exclusions = jread(E1 / 'qc_exclusions.json')['excluded']
    excluded = {r['ptid'] for r in exclusions}
    subjects = csvread(ROOT / 'reports/full_ot_medical_evidence/02_spatial_subject_checks.csv')
    assert len(subjects) == 1856 and all(r['pass'] == 'True' for r in subjects)
    subjects = {r['ptid']: r for r in subjects}
    cohort = {r['name']: r for r in jread(FULL / 'cohort.json')}
    e1cohort = {r['ptid']: r for r in jread(E1 / 'cohort.json')}
    definitions = [('Full', 165, FULL / 'oof_summary/per_subject_metrics.csv'),
                   ('ClinicalUNet', 165, UNET / 'oof_summary/per_subject_metrics.csv')]
    missing = []
    if (SWIN / 'completion.json').exists():
        completion = jread(SWIN / 'completion.json')
        assert completion['status'] == 'COMPLETE_SWINUNETR_TWO_FOLD_OOF'
        assert sha(SWIN / 'per_subject_metrics.csv') == completion['metrics_sha256']
        definitions.append(('SwinUNETR', 200, SWIN / 'per_subject_metrics.csv'))
    else:
        missing.append({'model': 'SwinUNETR', 'reason': 'Complete two-fold OOF receipt not yet available at preparation; no inference launched by this analysis', 'observed_status': jread(SWIN / 'status.json')})
    rows = []
    baseline_keys = None
    sources = {}
    for model, epoch, source in definitions:
        selected = [r for r in csvread(source) if int(r['epoch']) == epoch]
        keys = {identity(r) for r in selected}
        assert len(keys) == len(selected) == 2963
        if baseline_keys is None:
            baseline_keys = keys
        assert keys == baseline_keys
        sources[model] = {'epoch': epoch, 'metrics_path': str(source), 'metrics_sha256': sha(source), 'before_mask_intersection': len(selected)}
        for r in selected:
            ptid, tracer, fold = identity(r)
            assert cohort[ptid]['test_fold'] == fold
            assert bool(e1cohort[ptid]['has_' + tracer])
            if ptid in excluded:
                continue
            s = subjects[ptid]
            assert int(s['fold']) == fold and s['e1_cache'] == e1cohort[ptid]['cache']
            path = Path(r['prediction'])
            if model == 'ClinicalUNet':
                path = OUT / 'inputs/clinical_unet_epoch165' / ('fold' + str(fold)) / path.name
            elif model == 'SwinUNETR':
                path = OUT / 'inputs/swinunetr_epoch200' / (tracer + '_fold' + str(fold)) / path.name
            rows.append({'model': model, 'ptid': ptid, 'tracer': tracer, 'fold': fold,
                         'epoch': epoch, 'prediction_original': r['prediction'], 'prediction': str(path),
                         'prediction_sha256_expected': r['prediction_sha256'], 'checkpoint_sha256': r['checkpoint_sha256'],
                         'target_cache': s['full_cache'], 'mask_cache': s['e1_cache'],
                         'mask_cache_sha256_expected': s['e1_cache_sha256_expected'],
                         **{'whole_' + m: float(r[m]) for m in METRICS}})
    csvsave(OUT / 'input_index.csv', rows)
    counts = {model: dict(Counter(r['tracer'] for r in rows if r['model'] == model)) for model, _, _ in definitions}
    assert all(c == {'fdg': 1597, 'av45': 1364} for c in counts.values())
    evidence = [ROOT / 'reports/full_ot_medical_evidence/02_spatial_compatibility_report.md',
                ROOT / 'reports/full_ot_medical_evidence/02_spatial_subject_checks.csv',
                ROOT / 'reports/full_ot_medical_evidence/02_spatial_validation_results.json',
                ROOT / 'experiments/e1_clinical_conditioning/evaluate.py',
                ROOT / 'source_archive/vscode-3002/home/ssddata/liutuo/generative/metrics/ssim.py',
                Path(prior.__file__), Path(__file__)]
    jsave(OUT / 'input_manifest.json', {
        'prepared_utc': datetime.now(timezone.utc).isoformat(),
        'models': sources, 'coverage_after_frozen_mask_intersection': counts,
        'excluded': exclusions, 'additional_exclusions': [], 'unavailable_models': missing,
        'mask': 'Frozen SynthSeg nonzero-label union (mask > 0), including ventricles and CSF; not pure brain parenchyma',
        'mask_qc_subjects': len(subjects), 'raw_input_identity_matches': len(overlap),
        'target': 'Canonical frozen Full persistent-cache PET array, identical target array used for all models; no renormalization',
        'space': 'Direct array-index binding under existing MRI-anchored Full/E1 spatial gate; no affine edits, flips, registration or resampling',
        'input_index': {'path': str(OUT / 'input_index.csv'), 'sha256': sha(OUT / 'input_index.csv')},
        'frozen_e1_metadata': checks, 'source_evidence': {str(p): sha(p) for p in evidence},
        'bootstrap': {'iterations': 10000, 'seed': 42, 'strata': 'held-out fold, original fold sizes retained'},
        'holm': 'Separate 8-test family for each Full-versus-comparator contrast (2 tracers x 4 metrics)',
        'privacy': 'PTIDs confined to internal analysis/index/pilot files; supplementary tables contain aggregates only',
    })
    print(json.dumps({'models': list(sources), 'counts': counts}), flush=True)


def load_subject(rows):
    first = rows[0]
    # Downloads use rsync's atomic final rename. Wait only for this task's input
    # copies, never substitute a checkpoint-generated or partial prediction.
    deadline = time.monotonic() + 14400
    for row in rows:
        while not Path(row['prediction']).is_file():
            if time.monotonic() > deadline:
                raise TimeoutError('Frozen prediction copy unavailable: '+row['prediction'])
            time.sleep(5)
    mask_bytes = Path(first['mask_cache']).read_bytes()
    mask_sha = hashlib.sha256(mask_bytes).hexdigest()
    assert mask_sha == first['mask_cache_sha256_expected']
    cache_bytes = Path(first['target_cache']).read_bytes()
    cache_sha = hashlib.sha256(cache_bytes).hexdigest()
    item = torch.load(io.BytesIO(cache_bytes), map_location='cpu', weights_only=False)
    assert item['name'] == first['ptid'] and int(item['test_fold']) == int(first['fold'])
    with np.load(io.BytesIO(mask_bytes), allow_pickle=False) as saved:
        mask = saved['mask'].copy()
        e1targets = {t: saved[t].copy() for t in {r['tracer'] for r in rows}}
    assert mask.shape == SHAPE and np.isfinite(mask).all() and np.array_equal(mask, np.rint(mask))
    brain = mask > 0
    valid = ndimage.minimum_filter(brain.astype(np.uint8), size=7, mode='constant', cval=0)[3:-3, 3:-3, 3:-3] > 0
    assert brain.any() and valid.any()
    targets = {t: item[t].detach().cpu().numpy().squeeze().copy() for t in e1targets}
    info = {'ptid': first['ptid'], 'fold': int(first['fold']), 'mask_voxels': int(brain.sum()),
            'valid_ssim_centers': int(valid.sum()), 'mask_labels': sorted(int(v) for v in np.unique(mask) if v > 0),
            'target_cache_sha256': cache_sha, 'mask_cache_sha256': mask_sha,
            'brain_mask_array_sha256': hashlib.sha256(brain.tobytes()).hexdigest()}
    loaded = []
    for row in rows:
        path = Path(row['prediction'])
        actual_sha = sha(path)
        assert actual_sha == row['prediction_sha256_expected'], str(path)
        image = nib.load(path)
        prediction = np.asarray(image.dataobj, dtype=np.float32)
        real = targets[row['tracer']]
        assert prediction.shape == real.shape == SHAPE
        assert np.isfinite(prediction).all() and np.isfinite(real).all()
        assert 0 <= prediction.min() <= prediction.max() <= 1
        assert 0 <= real.min() <= real.max() <= 1
        loaded.append((row, real, prediction, actual_sha, image.affine.tolist()))
    info['target_array_sha256'] = {t: hashlib.sha256(a.tobytes()).hexdigest() for t, a in targets.items()}
    info['e1_target_max_abs_difference'] = {t: float(np.max(np.abs(a - e1targets[t]))) for t, a in targets.items()}
    return brain, valid, loaded, info


def calculate(pilot, device, model=None, resume=False, shard=None, shards=1, skip_metrics=None):
    torch.set_num_threads(2)
    torch.backends.cudnn.allow_tf32 = False
    torch.backends.cuda.matmul.allow_tf32 = False
    rows = csvread(OUT / 'input_index.csv')
    if model:
        rows = [r for r in rows if r['model']==model]
    by_subject = {}
    for row in rows:
        by_subject.setdefault(row['ptid'], []).append(row)
    if pilot:
        candidates = []
        for fold in (1, 2):
            selected = next(rs for rs in by_subject.values() if int(rs[0]['fold']) == fold and {r['tracer'] for r in rs} == {'fdg', 'av45'})
            candidates.append(selected)
    else:
        assert jread(OUT / 'pilot_validation.json')['status'] == 'PASS'
        candidates = list(by_subject.values())
    suffix=''
    if shard is not None:
        assert not pilot and model and 0<=shard<shards
        candidates=[rs for i,rs in enumerate(candidates) if i%shards==shard]
        suffix='_part'+str(shard)
    if skip_metrics:
        done=csvread(skip_metrics)
        counts=Counter(r['ptid'] for r in done)
        complete={p for p,rs in by_subject.items() if counts[p]==len(rs)}
        candidates=[rs for rs in candidates if rs[0]['ptid'] not in complete]
    metric_path = OUT / ('pilot_metrics.csv' if pilot else ('metrics_'+model+suffix+'.csv' if model else 'per_subject_metrics.csv'))
    asset_path = OUT / ('pilot_asset_checks.jsonl' if pilot else 'subject_asset_checks'+suffix+'.jsonl')
    results, validation = [], []
    old_assets = []
    if resume:
        assert not pilot and model and metric_path.exists()
        old = csvread(metric_path)
        complete = {ptid for ptid, rs in by_subject.items()
                    if sum(r['ptid']==ptid for r in old)==len(rs)}
        results = [r for r in old if r['ptid'] in complete]
        old_assets = [json.loads(line) for line in asset_path.read_text().splitlines()
                      if line.strip() and json.loads(line)['ptid'] in complete]
        stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        metric_path.rename(metric_path.with_name(metric_path.stem+'_before_resume_'+stamp+'.csv'))
        asset_path.rename(asset_path.with_name(asset_path.stem+'_before_resume_'+stamp+'.jsonl'))
        candidates=[rs for rs in candidates if rs[0]['ptid'] not in complete]
        print(json.dumps({'resumed_complete_subjects':len(complete),'preserved_metric_rows':len(results)}),flush=True)
    start = time.time()
    # Limit prefetch to three subjects to keep CPU RAM and NFS traffic bounded.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool, metric_path.open('x', newline='') as stream, asset_path.open('x') as assets:
        pending = {}
        cursor = 0
        for i in range(min(3, len(candidates))):
            pending[i] = pool.submit(load_subject, candidates[i])
            cursor += 1
        writer = None
        if results:
            writer=csv.DictWriter(stream,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results);stream.flush()
        for info in old_assets:assets.write(json.dumps(info)+'\n')
        assets.flush()
        for i in range(len(candidates)):
            brain, valid, loaded, info = pending.pop(i).result()
            if cursor < len(candidates):
                pending[cursor] = pool.submit(load_subject, candidates[cursor])
                cursor += 1
            assets.write(json.dumps(info) + '\n'); assets.flush()
            if pilot:
                independent = ndimage.binary_erosion(brain, structure=np.ones((7, 7, 7), bool), border_value=0)[3:-3, 3:-3, 3:-3]
                assert np.array_equal(valid, independent)
            for row, real, pred, actual_sha, affine in loaded:
                values, whole_ssim = metric_values(real, pred, brain, valid, device)
                output = {'model': row['model'], 'ptid': row['ptid'], 'tracer': row['tracer'],
                    'fold': int(row['fold']), 'epoch': int(row['epoch']), **values,
                    'mask_voxels': info['mask_voxels'], 'valid_ssim_centers': info['valid_ssim_centers'],
                    'prediction': row['prediction'], 'prediction_sha256': actual_sha,
                    'checkpoint_sha256': row['checkpoint_sha256'],
                    'target_array_sha256': info['target_array_sha256'][row['tracer']],
                    'brain_mask_array_sha256': info['brain_mask_array_sha256']}
                if writer is None:
                    writer = csv.DictWriter(stream, fieldnames=list(output)); writer.writeheader()
                writer.writerow(output); stream.flush()
                if pilot:
                    reference = e1_image_metrics(real, pred, brain=brain)
                    ssim_error = abs(reference['brain_ssim'] - values['ssim'])
                    assert ssim_error < 2e-6
                    diff = pred.astype(np.float64) - real.astype(np.float64)
                    direct_mse = float(np.sum(np.square(diff), where=brain) / np.count_nonzero(brain))
                    direct_mae = float(np.sum(np.abs(diff), where=brain) / np.count_nonzero(brain))
                    assert abs(direct_mse - values['mse']) < 1e-14
                    assert abs(direct_mae - values['mae']) < 1e-14
                    validation.append({'model': row['model'], 'ptid': row['ptid'], 'tracer': row['tracer'], 'fold': row['fold'],
                        'e1_cpu_masked_ssim': reference['brain_ssim'], 'gpu_masked_ssim': values['ssim'], 'ssim_absolute_error': ssim_error,
                        'direct_numpy_mse_error': abs(direct_mse-values['mse']), 'direct_numpy_mae_error': abs(direct_mae-values['mae']),
                        'valid_centers_independent_erosion_equal': True, 'whole_ssim_recomputed': whole_ssim,
                        'whole_ssim_frozen': row['whole_ssim'], 'affine': affine})
                results.append(output)
            if i % 20 == 0 or i == len(candidates)-1:
                print(json.dumps({'subjects': i+1, 'total_subjects': len(candidates), 'metric_rows': len(results), 'seconds': time.time()-start}), flush=True)
    if pilot:
        jsave(OUT / 'pilot_validation.json', {'status': 'PASS', 'checks': validation, 'device': device,
            'ssim_tolerance': 2e-6, 'purpose_of_tolerance': 'Numerical CPU/GPU SSIM agreement; not a scientific effect or equivalence margin',
            'ssim_protocol': 'E1 Gaussian float32 SSIM field, kernel 7, sigma 1.5, range 1; unchanged image arrays; mean over complete-mask windows only'})


def summarize():
    df = pd.read_csv(OUT / 'per_subject_metrics.csv')
    index = pd.read_csv(OUT / 'input_index.csv')
    key = ['model', 'ptid', 'tracer', 'fold', 'epoch']
    assert not df.duplicated(key).any() and set(map(tuple, df[key].values)) == set(map(tuple, index[key].values))
    assert np.isfinite(df[list(METRICS)].to_numpy()).all()
    summary = []
    for (model, tracer), group in df.groupby(['model', 'tracer'], sort=False):
        for metric in METRICS:
            x = group[metric].to_numpy()
            q05, median, q95 = np.quantile(x, [.05, .5, .95])
            summary.append({'model': model, 'epoch': int(group.epoch.iloc[0]), 'tracer': tracer, 'metric': metric,
                'n': len(x), 'mean': float(x.mean()), 'sd': float(x.std(ddof=1)), 'median': float(median), 'p05': float(q05), 'p95': float(q95)})
    csvsave(OUT / 'summary_metrics.csv', summary)
    comparisons = []
    validations = []
    whole_rows = []
    for comparator in [m for m in df.model.unique() if m != 'Full']:
        join = df[df.model == 'Full'].merge(df[df.model == comparator], on=['ptid', 'tracer', 'fold'], suffixes=('_full', '_other'), validate='one_to_one')
        assert len(join) == 2961
        assert (join.target_array_sha256_full == join.target_array_sha256_other).all()
        assert (join.brain_mask_array_sha256_full == join.brain_mask_array_sha256_other).all()
        family = []
        for ti, tracer in enumerate(('fdg', 'av45')):
            group = join[join.tracer == tracer].sort_values(['fold', 'ptid'])
            for mi, metric in enumerate(METRICS):
                a = group[metric+'_full'].to_numpy(); b = group[metric+'_other'].to_numpy(); delta = a-b
                folds = group.fold.to_numpy(); combo = ti*4+mi
                low, high = prior.stratified_bootstrap_ci(delta, folds, combo, 10000)
                independent_ci = prior.stratified_bootstrap_ci_independent(delta, folds, combo, 10000)
                assert np.allclose([low,high],independent_ci,rtol=0,atol=1e-12)
                t = stats.ttest_rel(a,b); check = stats.ttest_1samp(delta,0)
                assert np.allclose([t.statistic,t.pvalue],[check.statistic,check.pvalue],rtol=1e-10,atol=1e-12)
                mean = statistics.fmean(delta); sd = statistics.stdev(delta)
                better = delta > 0 if metric in ('ssim','psnr') else delta < 0
                result = {'comparison': 'Full_vs_'+comparator, 'comparator': comparator, 'tracer': tracer, 'metric': metric,
                    'n': len(delta), 'full_epoch':165, 'comparator_epoch': int(group.epoch_other.iloc[0]),
                    'difference_definition':'Full minus comparator', 'mean_difference': mean,
                    'ci_lower': low, 'ci_upper': high, 't_statistic':float(t.statistic), 'p_raw':float(t.pvalue),
                    'cohen_dz':mean/sd, 'full_better_count':int(better.sum()), 'full_better_proportion':float(better.mean()),
                    'fold1_n':int(sum(folds==1)), 'fold2_n':int(sum(folds==2)),
                    'fold1_mean_difference':float(delta[folds==1].mean()), 'fold2_mean_difference':float(delta[folds==2].mean()),
                    'holm_family_size':8, 'bootstrap_iterations':10000, 'bootstrap_seed':42}
                family.append(result)
                left = index[(index.model=='Full')&(index.tracer==tracer)].set_index(['ptid','fold'])
                right = index[(index.model==comparator)&(index.tracer==tracer)].set_index(['ptid','fold'])
                shared = left.index.intersection(right.index)
                wd = left.loc[shared,'whole_'+metric].to_numpy()-right.loc[shared,'whole_'+metric].to_numpy()
                whole_rows.append({'comparison':result['comparison'],'tracer':tracer,'metric':metric,'n':len(wd),
                    'whole_volume_mean_difference_same_intersection':float(wd.mean()),'masked_mean_difference':mean,
                    'direction_agrees':bool((wd.mean()>0)==(mean>0))})
        assert len(family)==8
        adjusted=prior.holm_adjust([r['p_raw'] for r in family])
        independent=prior.holm_adjust_independent([r['p_raw'] for r in family])
        assert np.allclose(adjusted,independent,rtol=0,atol=1e-15)
        for r,p in zip(family,adjusted):r['p_holm']=p
        comparisons.extend(family)
        validations.append({'comparison':'Full_vs_'+comparator,'n':len(join),'bootstrap_independent_replay':'PASS','ttest_and_dz_independent_check':'PASS','holm_family_8':'PASS','identical_target_and_mask_arrays':'PASS'})
    csvsave(OUT/'paired_comparisons.csv',comparisons)
    csvsave(OUT/'whole_volume_direction_comparison.csv',whole_rows)
    jsave(OUT/'statistical_validation.json',{'status':'PASS','comparisons':validations})
    print(json.dumps({'rows':len(df),'tests':len(comparisons),'summary_rows':len(summary)}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['prepare','pilot','calculate','summarize'])
    parser.add_argument('--device',default='cuda:2')
    parser.add_argument('--model',choices=['Full','ClinicalUNet','SwinUNETR'])
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--shard',type=int)
    parser.add_argument('--shards',type=int,default=1)
    parser.add_argument('--skip-metrics',type=Path)
    args=parser.parse_args()
    if args.action=='prepare':prepare()
    elif args.action in ('pilot','calculate'):calculate(args.action=='pilot',args.device,args.model,args.resume,args.shard,args.shards,args.skip_metrics)
    else:summarize()
