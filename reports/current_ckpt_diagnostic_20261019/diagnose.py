"""Read-only training checkpoint snapshot and interim held-out quality audit.

This is an interim diagnostic, separate from fixed-epoch E1 formal OOF outputs.
Run on each fold's training node with the matching E1_ASSETS_ROOT and GPU UUID.
"""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor

import nibabel as nib
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "experiments/e1_clinical_conditioning"))
from common import CODE, active_rows, check_frozen, load_config, new_model, seed_all, sha, write_json, TRACERS
from run import checkpoint_identity, contexts, get_data, hardware, load_adapter, prediction
from evaluate import apply_validity, regional, roi_context
sys.path.insert(0, str(CODE))
from generative.metrics.ssim import compute_ssim_and_cs
from ssim_fast import ssim


def load_cpu(row):
    assert sha(row['cache']) == row['cache_sha256'], row['ptid']
    with np.load(row['cache']) as z:
        return {k: z[k] for k in ['mri', 'fdg', 'av45', 'mask', 'affine']}


def prefetched(rows):
    # Two bounded CPU reads overlap GPU work; no training cache is changed.
    with ThreadPoolExecutor(max_workers=2) as pool:
        pending = {}
        for i in range(min(2, len(rows))):
            pending[i] = pool.submit(load_cpu, rows[i])
        for i, row in enumerate(rows):
            arrays = pending.pop(i).result()
            if i+2 < len(rows):
                pending[i+2] = pool.submit(load_cpu, rows[i+2])
            yield row, arrays


@torch.inference_mode()
def image_metrics(real, pred, brain, validate=False, validate_cpu=False):
    assert real.shape == pred.shape == (160, 192, 160)
    assert np.isfinite(real).all() and np.isfinite(pred).all()
    diff = real.astype(np.float64) - pred
    mse = float(np.mean(diff ** 2))
    result = dict(mse=mse, mae=float(np.mean(abs(diff))), psnr=float(-10 * np.log10(mse)),
                  brain_mae=float(np.mean(abs(diff[brain]))))
    x = torch.from_numpy(real.copy())[None, None].cuda()
    y = torch.from_numpy(pred.copy())[None, None].cuda()
    # Same valid Gaussian SSIM equation; both known historical windows, no resizing.
    for kernel in [7, 11]:
        result[f"ssim{kernel}"] = ssim(x, y, kernel)
        if validate:
            field, cs = compute_ssim_and_cs(x, y, spatial_dims=3, data_range=1.0,
                                          kernel_size=(kernel,) * 3, kernel_sigma=(1.5,) * 3)
            native = float(field.mean())
            del field, cs
            assert abs(native-result[f"ssim{kernel}"]) < 5e-5
            result[f"ssim{kernel}_native_gpu_check"] = native
        if validate_cpu:
            field, cs = compute_ssim_and_cs(x.cpu(), y.cpu(), spatial_dims=3, data_range=1.0,
                                          kernel_size=(kernel,) * 3, kernel_sigma=(1.5,) * 3)
            native = float(field.mean())
            del field, cs
            assert abs(native-result[f"ssim{kernel}"]) < 5e-5
            result[f"ssim{kernel}_native_cpu_check"] = native
    assert all(np.isfinite(v) for v in result.values())
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fold", type=int, choices=[1, 2], required=True)
    p.add_argument("--config", type=Path, default=ROOT / "reports/e1_stage01_20261017/config.json")
    a = p.parse_args()
    out = Path(__file__).resolve().parent / f"fold{a.fold}"
    out.mkdir(exist_ok=True)
    cfg = load_config(a.config)
    check_frozen(cfg)
    assert cfg['evaluation_laterality_gate_pass'] and cfg['evaluation_mri_mask_gate_pass']
    rows = active_rows(cfg, json.loads((Path(cfg['report']) / 'cohort.json').read_text()))
    held = [r for r in rows if r['test_fold'] == a.fold]
    train_ids = {r['ptid'] for r in rows if r['test_fold'] != a.fold}
    assert len(held) == len(train_ids) == 928
    assert train_ids.isdisjoint(r['ptid'] for r in held)
    source = Path(cfg['assets']) / 'formal' / f'fold{a.fold}_Full/recovery.pt'
    # An opened source descriptor retains the complete inode through atomic replacement.
    checkpoint = out / 'checkpoint.pt'
    if checkpoint.exists():
        previous = json.loads((out / 'snapshot.tf32_unvalidated.json').read_text())
        assert sha(checkpoint) == previous['checkpoint_sha256']
        source_inode = previous['source_inode']
    else:
        with source.open('rb') as src, checkpoint.open('xb') as dst:
            before = os.fstat(src.fileno())
            shutil.copyfileobj(src, dst, 8 * 1024 ** 2)
            after = os.fstat(src.fileno())
            assert (before.st_ino, before.st_size, before.st_mtime_ns) == (after.st_ino, after.st_size, after.st_mtime_ns)
            source_inode = before.st_ino
    ck = torch.load(checkpoint, map_location='cpu', weights_only=False)
    identity = checkpoint_identity(cfg, a.fold, 'Full')
    assert ck['stage'] == 'formal' and ck['checkpoint_format'] == 2
    assert all(ck.get(k) == v for k, v in identity.items())
    assert ck['optimizer_updates'] == (ck['epoch'] + 1) * len(train_ids)
    assert all(torch.isfinite(t).all() for t in ck['model'].values())
    assert all(not torch.is_tensor(t) or torch.isfinite(t).all()
               for state in ck['optimizer']['state'].values() for t in state.values())
    torch.set_num_threads(4)
    seed_all(cfg['seed'] + a.fold)
    torch.backends.cudnn.allow_tf32 = False
    ctx = contexts(cfg, 'Full')
    adapter = load_adapter(cfg, rows, a.fold)
    model = new_model().cuda().eval()
    model.load_state_dict(ck['model'], strict=True)
    labels = np.genfromtxt(Path(cfg['report']) / 'roi_labels.csv', delimiter=',', names=True,
                          dtype=None, encoding='utf-8')['region'].astype(int)
    invalid, physical = roi_context(cfg, labels)
    cksha = sha(checkpoint)
    manifest = dict(timestamp=datetime.now(timezone(timedelta(hours=8))).isoformat(),
                    source=str(source), source_inode=source_inode, checkpoint=str(checkpoint),
                    checkpoint_sha256=cksha, epoch_zero_based=ck['epoch'],
                    completed_epochs=ck['epoch'] + 1, planned_epochs=cfg['epochs'],
                    endpoint_stage_reached=ck['epoch'] >= cfg['endpoint_epoch_zero_based'],
                    optimizer_updates=ck['optimizer_updates'], scaler=ck['scaler'],
                    model_optimizer_finite=True, identity=identity, hardware=hardware(),
                    training_ptids=sorted(train_ids), test_ptids=sorted(r['ptid'] for r in held),
                    outer_test_overlap=0, script_sha256=sha(__file__),
                    ssim_implementation_sha256=sha(Path(__file__).with_name('ssim_fast.py')),
                    ssim_cudnn_allow_tf32=False, ssim_native_validation_tolerance=5e-5,
                    purpose='interim held-out diagnostic; not fixed-epoch E1 formal OOF',
                    metrics='full 160x192x160 grid, range=1, separable FP32 Gaussian SSIM7/11 checked against native CPU/GPU; per-subject means; no renormalization')
    write_json(out / 'snapshot.json', manifest)
    # Seeded random order yields an early check without selecting by performance.
    ordered = [held[i] for i in np.random.default_rng(20261019 + a.fold).permutation(len(held))]
    write_json(out / 'evaluation_order.json', [r['ptid'] for r in ordered])
    example_ids = {next(r['ptid'] for r in sorted(held, key=lambda r: r['ptid']) if r['diagnosis'] == dx)
                   for dx in sorted({r['diagnosis'] for r in held})}
    metrics_path = out / 'metrics.jsonl'
    results = [json.loads(line) for line in metrics_path.read_text().splitlines()] if metrics_path.exists() else []
    assert all(r['checkpoint_sha256'] == cksha for r in results)
    done = {(r['ptid'], r['tracer']) for r in results}
    complete_ids = {r['ptid'] for r in held if all((r['ptid'], t) in done for t in TRACERS if r['has_'+t])}
    # A stopped process may have written only one tracer for its final subject.
    results = [r for r in results if r['ptid'] in complete_ids]
    remaining = [r for r in ordered if r['ptid'] not in complete_ids]
    started = time.monotonic()
    with metrics_path.open('w', buffering=1) as stream:
        for entry in results:
            stream.write(json.dumps(entry)+'\n')
        for index, (row, arrays) in enumerate(prefetched(remaining), len(complete_ids)+1):
            data = {'mri':torch.from_numpy(arrays['mri'])[None,None].cuda()}
            mask, affine = arrays['mask'], arrays['affine']
            for i, tracer in enumerate(TRACERS):
                if not row['has_' + tracer]:
                    continue
                pred = prediction(model, data, ctx[row['ptid']].cuda(), adapter[i])
                real = arrays[tracer]
                values = image_metrics(real, pred, mask > 0, validate=index<=3 or index%100==0,
                                       validate_cpu=index==1)
                target_roi = apply_validity(regional(real, mask, labels), labels, invalid.get(row['ptid'], set()))
                pred_roi = apply_validity(regional(pred, mask, labels), labels, invalid.get(row['ptid'], set()))
                values['roi_mae'] = float(np.nanmean(abs(target_roi - pred_roi)))
                entry = dict(ptid=row['ptid'], diagnosis=row['diagnosis'], fold=a.fold, tracer=tracer,
                             completed_epochs=ck['epoch'] + 1, checkpoint_sha256=cksha,
                             cache_sha256=row['cache_sha256'], **values)
                results.append(entry)
                stream.write(json.dumps(entry) + '\n')
                if row['ptid'] in example_ids:
                    examples = out / 'examples'
                    examples.mkdir(exist_ok=True)
                    target = examples / f"{row['ptid']}_{tracer}.nii.gz"
                    nib.save(nib.Nifti1Image(pred, affine), target)
                    write_json(target.with_suffix('.json'), dict(ptid=row['ptid'], tracer=tracer,
                               checkpoint_sha256=cksha, prediction_sha256=sha(target),
                               cache=row['cache'], cache_sha256=row['cache_sha256']))
            if index <= 3 or index % 10 == 0 or index == len(held):
                print(json.dumps(dict(subjects_done=index, total_subjects=len(held), volumes=len(results),
                                      seconds=time.monotonic() - started,
                                      peak_gpu_gib=torch.cuda.max_memory_allocated() / 1024**3)), flush=True)
                write_json(out / 'progress.json', dict(subjects_done=index, total_subjects=len(held),
                           volumes=len(results), seconds=time.monotonic() - started))
    fields = list(dict.fromkeys(k for row in results for k in row))
    with (out / 'metrics.csv').open('x') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(results)
    expected = {(r['ptid'], t) for r in held for t in TRACERS if r['has_' + t]}
    actual = {(r['ptid'], r['tracer']) for r in results}
    assert actual == expected and len(results) == len(actual)
    write_json(out / 'complete.json', dict(status='COMPLETE', subjects=len(held), volumes=len(results),
               completed_epochs=ck['epoch'] + 1, checkpoint_sha256=cksha,
               seconds=time.monotonic() - started, hardware=hardware()))


if __name__ == '__main__':
    main()
