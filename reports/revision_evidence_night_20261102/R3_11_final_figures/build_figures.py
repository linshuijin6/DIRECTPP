"""R3-11 display only: select first, then render frozen arrays. No metric evaluation.

Run with the project xiaochou interpreter: build_figures.py select | render.
The existing cases.py is monolithic; its original loading block is executed
verbatim, without importing its selection/rendering side effects.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
import textwrap

import numpy as np
import pandas as pd

DEST = Path(__file__).resolve().parent
ROOT = DEST.parents[2]
BASE = DEST.parent
REPRO = ROOT / 'reports/original_author_reproduction_20261020'
QC = ROOT / 'reports/r3_11_brain_mask_metrics/run_20261102'
SOURCE = BASE / 'code/cases.py'
LABELS = {'median': 'Median', 'p10': '10th percentile', 'worst': 'Worst QC-passed'}
COLS = ['MRI', 'Real PET', 'Synthetic PET', 'Absolute error']


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def ahash(array):
    return hashlib.sha256(array.tobytes()).hexdigest()


def read(path):
    return pd.read_csv(path, float_precision='round_trip')


def dump(path, value):
    Path(path).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def select():
    assert not (DEST / 'selection_manifest_internal.csv').exists(), 'Selection already frozen'
    metrics = read(REPRO / 'oof_summary/per_subject_metrics.csv')
    metrics = metrics[metrics.epoch == 165]
    eligibility = read(QC / 'eligibility_and_exclusions_internal.csv')
    exclusion = json.loads((ROOT / 'reports/e1_stage01_20261017/qc_exclusions.json').read_text())
    assert [x['ptid'] for x in exclusion['excluded']] == ['016_S_4952']
    joined = metrics.merge(eligibility, on=['ptid', 'tracer', 'fold'], validate='one_to_one')
    assert len(joined) == len(metrics) == 2963
    assert set(joined[~joined.included].ptid) == {'016_S_4952'}
    valid = joined[joined.included].copy()
    assert valid.groupby('tracer').size().to_dict() == {'av45': 1364, 'fdg': 1597}
    assert valid.ssim.notna().all()
    old = read(BASE / 'G3_cases/selection_manifest_internal.csv')
    old_render = read(BASE / 'G3_cases/render_manifest_internal.csv')
    spatial = read(ROOT / 'reports/full_ot_medical_evidence/02_spatial_subject_checks.csv')
    idx = read(QC / 'input_index.csv'); idx = idx[idx.model == 'Full']
    split = read(REPRO / 'split_manifest.csv').set_index('ptid')
    rows = []
    for tracer in ('fdg', 'av45'):
        s = valid[valid.tracer == tracer].sort_values(['ssim', 'ptid'], kind='stable')
        for rule, q in [('median', .5), ('p10', .1), ('worst', 0.)]:
            target = float(s.ssim.quantile(q, interpolation='linear'))
            chosen = s.assign(distance=abs(s.ssim-target)).sort_values(['distance', 'ptid'], kind='stable').iloc[0]
            row = chosen.drop('distance').to_dict()
            prior = old[(old.tracer == tracer) & (old.selection == rule)].iloc[0]
            same = chosen.ptid == prior.ptid
            asset = idx[(idx.ptid == chosen.ptid) & (idx.tracer == tracer)]
            assert len(asset) == 1
            asset = asset.iloc[0]
            for col in ['fold', 'epoch', 'checkpoint_sha256']:
                assert asset[col] == chosen[col]
            assert asset.prediction_sha256_expected == chosen.prediction_sha256
            assert asset.prediction_original == chosen.prediction
            gate = spatial[spatial.ptid == chosen.ptid]
            assert len(gate) == 1 and bool(gate.iloc[0]['pass'])
            assert int(split.loc[chosen.ptid, 'test_fold']) == chosen.fold
            row.update(selection=rule, quantile=q, target_ssim=target, ranking_N=len(s),
                       selection_rule='nearest linear empirical SSIM quantile within existing QC-valid set; tie by PTID',
                       qc_status='passed existing frozen QC', qc_reason=chosen.reason,
                       spatial_gate_pass=True, target_cache=asset.target_cache,
                       previous_ptid=prior.ptid, previous_ssim=prior.ssim,
                       previous_selection_still_valid=bool(same),
                       change_reason=('unchanged under QC-valid ranking' if same else
                                      'excluded pre-existing QC failure before all three selections; quantile/rank changed'),
                       detail_action=('reuse existing PNG' if same else 'new PNG for changed case'))
            if same:
                record = old_render[(old_render.tracer == tracer) & (old_render.selection == rule)].iloc[0]
                row['reused_detail_source'] = str(BASE / record.figure)
            else:
                row['reused_detail_source'] = ''
            rows.append(row)
    readme_sources = [REPRO / 'oof_summary/per_subject_metrics.csv', REPRO / 'oof_summary/analysis_manifest.json',
                      REPRO / 'cohort.json', REPRO / 'split_manifest.csv', QC / 'input_index.csv',
                      QC / 'eligibility_and_exclusions_internal.csv', QC / 'input_manifest.json',
                      QC / 'subject_asset_checks.jsonl',
                      ROOT / 'reports/e1_stage01_20261017/qc_exclusions.json',
                      ROOT / 'reports/full_ot_medical_evidence/02_spatial_subject_checks.csv', SOURCE,
                      BASE / 'G3_cases/selection_manifest_internal.csv', BASE / 'G3_cases/render_manifest_internal.csv',
                      BASE / 'G3_cases/selection_frozen.json', BASE / 'G3_cases/REPORT.md', BASE / 'FIGURE_INDEX.md']
    readme_sources += sorted((BASE / 'figures').glob('G3_case_*.png'))
    pd.DataFrame(rows).to_csv(DEST / 'selection_manifest_internal.csv', index=False)
    valid.sort_values(['tracer', 'ssim', 'ptid'], kind='stable')[
        ['ptid', 'tracer', 'fold', 'epoch', 'ssim', 'included', 'reason']
    ].to_csv(DEST / 'eligible_ranking_internal.csv', index=False)
    dump(DEST / 'selection_frozen.json', dict(
        frozen_at_utc=datetime.now(timezone.utc).isoformat(),
        manifest_sha256=sha(DEST / 'selection_manifest_internal.csv'),
        ranking_sha256=sha(DEST / 'eligible_ranking_internal.csv'),
        images_loaded_in_this_task_before_freeze=False,
        source_sha256={str(p): sha(p) for p in readme_sources},
        display_protocol=dict(composite_grid_axis=2, composite_index=80,
                              detail_axes=[0, 1, 2], detail_indices=[80, 96, 80],
                              display_rotation='np.rot90, identical to cases.py; no new anatomical reorientation',
                              pet_range=[0, 1], error_range=[0, 1], mri_range=[0, 1],
                              pet_cmap='magma', error_cmap='inferno', dpi=400)))
    print(read(DEST / 'selection_manifest_internal.csv')[['tracer', 'selection', 'ptid', 'fold', 'ssim', 'detail_action']].to_string(index=False))
    print('FROZEN', sha(DEST / 'selection_manifest_internal.csv'), flush=True)


def render():
    import torch
    import nibabel as nib
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.cm import ScalarMappable
    from matplotlib.colors import Normalize
    from matplotlib.text import Text
    from PIL import Image

    frozen = json.loads((DEST / 'selection_frozen.json').read_text())
    assert sha(DEST / 'selection_manifest_internal.csv') == frozen['manifest_sha256']
    assert sha(DEST / 'eligible_ranking_internal.csv') == frozen['ranking_sha256']
    for path, expected in frozen['source_sha256'].items():
        assert sha(path) == expected, path
    selected = read(DEST / 'selection_manifest_internal.csv')
    idx = read(QC / 'input_index.csv'); idx = idx[idx.model == 'Full']
    cohort = {r['name']: r for r in json.loads((REPRO / 'cohort.json').read_text())}
    cache_root = ROOT / 'results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup'
    # Verbatim existing reader, cases.py lines 25–35; no old top-level code runs.
    loader = textwrap.dedent('\n'.join(SOURCE.read_text().splitlines()[24:35]))
    assert loader.startswith('hit=idx[') and loader.endswith('error=np.abs(pred-real)')
    loader_code = compile(loader, str(SOURCE) + ':25-35', 'exec')
    audit = {x['ptid']: x for x in map(json.loads, (QC / 'subject_asset_checks.jsonl').read_text().splitlines())}
    receipts = {}
    for fold in (1, 2):
        path = Path(selected[selected.fold == fold].iloc[0].prediction).parent / 'complete.json'
        receipts[fold] = json.loads(path.read_text())
        assert sha(path.parent / 'metrics.csv') == receipts[fold]['metrics_sha256']
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11,
                         'pdf.fonttype': 42, 'axes.linewidth': .6, 'savefig.facecolor': 'white'})
    details = DEST / 'details'; details.mkdir(exist_ok=True)
    records, exports = [], []

    def draw(ax, array, axis, col):
        # Same slice extraction, display rotation, colormaps and interpolation as cases.py.
        sl = np.rot90(np.take(array, array.shape[axis]//2, axis=axis))
        im = ax.imshow(sl, cmap=['gray', 'magma', 'magma', 'inferno'][col],
                       vmin=0, vmax=1, interpolation='nearest', aspect='equal')
        ax.set_xticks([]); ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        assert np.array_equal(np.asarray(im.get_array()), sl)
        assert im.get_clim() == (0, 1)

    def bars(fig, detailed=False):
        y = .080 if not detailed else .074
        for rect, cmap, label in [([.18, y, .15, .014], 'gray', 'MRI intensity (a.u.)'),
                                  ([.40, y, .24, .014], 'magma', 'PET normalized uptake (a.u.)'),
                                  ([.73, y, .21, .014], 'inferno', 'Absolute error (a.u.)')]:
            cb = fig.colorbar(ScalarMappable(norm=Normalize(0, 1), cmap=cmap),
                              cax=fig.add_axes(rect), orientation='horizontal', ticks=[0, .5, 1])
            cb.ax.tick_params(labelsize=9, length=2, pad=2)
            cb.set_label(label, fontsize=10, labelpad=3)

    def save(fig, stem):
        fig.canvas.draw()
        renderer = fig.canvas.get_renderer()
        outside = []
        for t in fig.findobj(Text):
            if t.get_visible() and t.get_text():
                b = t.get_window_extent(renderer)
                if b.x0 < -1 or b.y0 < -1 or b.x1 > fig.bbox.width+1 or b.y1 > fig.bbox.height+1:
                    outside.append(t.get_text())
                assert not any(r.ptid in t.get_text() for r in selected.itertuples())
                assert '/mnt/' not in t.get_text()
        assert not outside, outside
        for suffix in ('.png', '.pdf'):
            path = DEST / (stem + suffix)
            fig.savefig(path, dpi=400)  # Fixed canvas; no bounding-box crop.
            info = dict(path=str(path.relative_to(DEST)), sha256=sha(path), text_bounds_pass=True)
            if suffix == '.png':
                with Image.open(path) as image:
                    info.update(pixels=list(image.size), dpi=list(image.info['dpi']))
                    assert min(image.info['dpi']) >= 300 and min(image.size) >= 3000
            exports.append(info)

    for tracer in ('fdg', 'av45'):
        fig, axes = plt.subplots(3, 4, figsize=(12, 10.4))
        fig.subplots_adjust(left=.19, right=.97, top=.885, bottom=.155, wspace=.035, hspace=.06)
        fig.suptitle(f'{tracer.upper()} | DIReCT++ Full', fontsize=18, fontweight='bold', y=.975)
        fig.text(.58, .932, 'Frozen two-fold OOF predictions · Epoch 165', ha='center', fontsize=11)
        for col, title in enumerate(COLS):
            axes[0, col].set_title(f'{chr(65+col)}  {title}', fontsize=12, fontweight='bold', pad=10)
        for ri, row in enumerate(selected[selected.tracer == tracer].itertuples()):
            env = dict(idx=idx, cohort=cohort, cache_root=cache_root, row=row,
                       Path=Path, torch=torch, hashlib=hashlib, nib=nib, np=np)
            exec(loader_code, env)
            mri, real, pred, error, cache, data = [env[k] for k in ('mri', 'real', 'pred', 'error', 'cache', 'data')]
            assert str(cache) == row.target_cache
            assert int(cohort[row.ptid]['test_fold']) == row.fold
            assert int(data['test_fold']) == row.fold
            assert receipts[row.fold]['epoch'] == 165
            assert receipts[row.fold]['checkpoint_sha256'] == row.checkpoint_sha256
            assert Path(row.prediction).name == f'generated_{tracer}_{row.ptid}.nii.gz'
            assert Path(row.prediction).parent.name == f'fold{row.fold}'
            assert sha(cache) == audit[row.ptid]['target_cache_sha256']
            assert ahash(real) == audit[row.ptid]['target_array_sha256'][tracer]
            assert np.array_equal(error, np.maximum(pred-real, real-pred))
            arrays = [mri, real, pred, error]
            assert all(float(a.min()) >= 0 and float(a.max()) <= 1 for a in arrays)
            for col, arr in enumerate(arrays):
                draw(axes[ri, col], arr, 2, col)
            label = LABELS[row.selection]
            if row.selection == 'worst':
                label = 'Worst\nQC-passed'
            pos = axes[ri, 0].get_position()
            fig.text(.035, pos.y0+pos.height/2, f'{label}\nSSIM = {row.ssim:.4f}',
                     va='center', ha='left', fontsize=12, linespacing=1.6)
            detail_path = details / f'R3_11_{tracer.upper()}_{row.selection}_orthogonal.png'
            if row.previous_selection_still_valid:
                original = Path(row.reused_detail_source)
                if not detail_path.is_symlink():
                    assert not detail_path.exists()
                    detail_path.symlink_to(Path('../../figures') / original.name)
                assert sha(detail_path) == sha(original)
                old = read(BASE / 'G3_cases/render_manifest_internal.csv')
                old = old[(old.tracer == tracer) & (old.selection == row.selection)].iloc[0]
                assert old.real_array_sha256 == ahash(real)
                action = 'reused original 200-dpi optional detail by relative symlink; no regeneration'
            else:
                df, da = plt.subplots(3, 4, figsize=(12, 10.4))
                df.subplots_adjust(left=.15, right=.97, top=.87, bottom=.15, wspace=.035, hspace=.06)
                df.suptitle(f'{tracer.upper()} | {LABELS[row.selection]} | SSIM = {row.ssim:.4f}', fontsize=16, y=.973)
                df.text(.56, .930, 'DIReCT++ Full · Frozen two-fold OOF · Epoch 165', ha='center', fontsize=11)
                for ai, axrow in enumerate(da):
                    for col, (ax, arr) in enumerate(zip(axrow, arrays)):
                        draw(ax, arr, ai, col)
                        if ai == 0:
                            ax.set_title(f'{chr(65+col)}  {COLS[col]}', fontsize=12, pad=10)
                    da[ai, 0].set_ylabel(f'Grid axis {ai}\nIndex {arrays[0].shape[ai]//2}', fontsize=11)
                bars(df, detailed=True)
                df.text(.56, .014, 'Frozen array grid; no anatomical left/right labels. Fixed scales 0–1; no clipping.', ha='center', fontsize=9)
                save(df, str(detail_path.with_suffix('').relative_to(DEST))); plt.close(df)
                action = 'new detail for selection changed by uniform QC-valid ranking'
            records.append(dict(ptid=row.ptid, tracer=tracer, fold=row.fold, epoch=165,
                                selection=row.selection, ssim=row.ssim, displayed_ssim=f'{row.ssim:.4f}',
                                prediction=row.prediction, prediction_sha256=sha(row.prediction),
                                checkpoint_sha256=row.checkpoint_sha256,
                                target_cache=str(cache), target_cache_sha256=sha(cache),
                                mri_array_sha256=ahash(mri), real_array_sha256=ahash(real),
                                synthetic_array_sha256=ahash(pred), error_array_sha256=ahash(error),
                                array_ranges={name: [float(a.min()), float(a.max())] for name, a in zip(COLS, arrays)},
                                error_verified_by_independent_maximum_identity=True,
                                error_above_display_max_voxels=int(np.count_nonzero(error > 1)),
                                qc='included in existing eligibility AND spatial gate pass',
                                shape=list(real.shape), detail=str(detail_path.relative_to(DEST)),
                                detail_sha256=sha(detail_path), detail_action=action,
                                plotted_arrays_verified_exact=True))
            print('READ/VERIFIED', tracer, row.selection, row.ptid, flush=True)
        bars(fig)
        fig.text(.58, .015, 'Central slice: grid axis 2, index 80. Fixed scales 0–1; no clipping.', ha='center', fontsize=10)
        save(fig, f'R3_11_{tracer.upper()}_cases'); plt.close(fig)
    for path, expected in frozen['source_sha256'].items():
        assert sha(path) == expected, path
    dump(DEST / 'figure_manifest.json', dict(
        created_at_utc=datetime.now(timezone.utc).isoformat(), model='original_author_reproduction DIReCT++ Full',
        epoch=165, selection_manifest_sha256=frozen['manifest_sha256'],
        loading_source=dict(path=str(SOURCE), sha256=sha(SOURCE), lines=[25, 35],
                            block_sha256=hashlib.sha256(loader.encode()).hexdigest(),
                            method='verbatim loading block; no original top-level selection/render side effects'),
        display=frozen['display_protocol'], metric_scope='saved whole-volume SSIM; no SSIM/PSNR or brain-mask metrics recomputed',
        interpolation='nearest', aspect='equal in existing array grid', clipping=False,
        sources_unchanged_after_render=True, records=records, exports=exports,
        visual_inspection=dict(status='pending actual image viewing')))


if __name__ == '__main__':
    {'select': select, 'render': render}[sys.argv[1]]()
