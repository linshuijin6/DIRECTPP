"""Audit complete Full165 OOF coverage and write subject-weighted summaries."""
import csv
import json
from pathlib import Path
import sys
import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'experiments/e1_clinical_conditioning'))
from common import active_rows, check_frozen, load_config, sha, write_json


def main():
    cfg = load_config(ROOT / 'reports/e1_stage01_20261017/config.json')
    check_frozen(cfg)
    rows = active_rows(cfg, json.loads((Path(cfg['report']) / 'cohort.json').read_text()))
    expected = {(r['ptid'], r['test_fold'], t) for r in rows for t in ['fdg', 'av45'] if r['has_' + t]}
    completions = []; snapshots = []; index = []; regions = []; train_audits = []
    frames = []
    for fold, node in [(1, '3002'), (2, '3003')]:
        folder = OUT / f'fold{fold}'
        assert (OUT / f'fold{fold}.exit').read_text().strip() == '0'
        complete = json.loads((folder / 'complete.json').read_text())
        snapshot = json.loads((folder / 'snapshot.json').read_text())
        assert complete['status'] == 'COMPLETE' and complete['completed_epochs'] == snapshot['completed_epochs'] == 165
        assert sha(snapshot['checkpoint']) == complete['checkpoint_sha256'] == snapshot['checkpoint_sha256']
        assert not set(snapshot['training_ptids']) & set(snapshot['test_ptids'])
        assert set(snapshot['test_ptids']) == {r['ptid'] for r in rows if r['test_fold'] == fold}
        q = pd.read_csv(folder / 'metrics.csv')
        assert set(q.fold) == {fold} and set(q.completed_epochs) == {165}
        assert set(q.checkpoint_sha256) == {snapshot['checkpoint_sha256']}
        checks = {}
        for kernel in [7, 11]:
            for device in ['cpu', 'gpu']:
                col = f'ssim{kernel}_native_{device}_check'
                valid = q[col].notna()
                delta = abs(q.loc[valid, col] - q.loc[valid, f'ssim{kernel}'])
                assert len(delta) >= 1 and delta.max() < 5e-5
                checks[f'{kernel}_{device}'] = dict(n=int(valid.sum()), max_absdiff=float(delta.max()))
        snapshot['summary_ssim_validation'] = checks
        frames.append(q);completions.append(complete);snapshots.append(snapshot)
        ii = json.loads((folder / 'prediction_index.json').read_text())
        assert len(ii) == complete['prediction_count'] == len(q)
        index.extend(ii)
        region_records = [json.loads(line) for line in (folder / 'regions.jsonl').read_text().splitlines()]
        assert len(region_records) == len(q)
        metric_lookup = q.set_index(['ptid', 'tracer'])
        for rec in region_records:
            x = np.array(rec['real'], dtype=float); y = np.array(rec['pred'], dtype=float)
            assert len(x) == len(y) == len(rec['labels']) == 98
            valid = np.isfinite(x) & np.isfinite(y)
            assert valid.any() and np.array_equal(np.isnan(x), np.isnan(y))
            value = float(np.mean(abs(x[valid]-y[valid])))
            assert abs(value - metric_lookup.loc[(rec['ptid'], rec['tracer']), 'roi_mae']) < 1e-12
            for label, name, real, pred in zip(rec['labels'], rec['physical_names'], x, y):
                regions.append(dict(ptid=rec['ptid'], fold=fold, tracer=rec['tracer'], region=label,
                    physical_region=name, real=real, pred=pred, absolute_error=abs(real-pred)))
        log = ROOT / f'reports/e1_amp_recovery_20261018/logs/{node}_fold{fold}_Full.log'
        events = []
        for line in log.read_text().splitlines():
            try: events.append(json.loads(line))
            except ValueError: pass
        epochs = [e for e in events if e.get('event') == 'epoch_complete']
        assert [e['epoch'] for e in epochs] == list(range(165))
        updates = [e for e in events if e.get('event') == 'optimizer_step']
        assert updates[-1]['optimizer_updates'] == 153120
        pd.DataFrame(epochs).to_csv(OUT / f'fold{fold}_training_epochs.csv', index=False)
        train_audits.append(dict(fold=fold, completed_epochs=len(epochs), final_loss=epochs[-1]['loss'],
            optimizer_updates=updates[-1]['optimizer_updates'], log=str(log), log_sha256=sha(log),
            train_exit=(ROOT / f'reports/e1_amp_recovery_20261018/queues/{node}_fold{fold}/Full.exit').read_text().strip()))
    metrics = pd.concat(frames, ignore_index=True)
    actual = set(metrics[['ptid', 'fold', 'tracer']].itertuples(index=False, name=None))
    predicted = {(r['ptid'], r['fold'], r['tracer']) for r in index}
    assert actual == predicted == expected and len(metrics) == len(index) == len(expected)
    metric_names = ['psnr', 'ssim7', 'ssim11', 'mse', 'mae', 'roi_mae', 'brain_mae']
    assert np.isfinite(metrics[metric_names].to_numpy()).all()
    metrics.to_csv(OUT / 'per_subject_metrics.csv', index=False)
    pd.DataFrame(regions).to_csv(OUT / 'regions_long.csv', index=False)
    write_json(OUT / 'prediction_index.json', index)
    metrics.groupby(['fold', 'tracer'])[metric_names].agg(['count', 'mean', 'std']).to_csv(OUT / 'per_fold_summary.csv')
    metrics.groupby(['diagnosis', 'tracer'])[metric_names].agg(['count', 'mean', 'std']).to_csv(OUT / 'per_diagnosis_summary.csv')
    summaries = []
    rng = np.random.default_rng(20261020)
    for tracer, q in metrics.groupby('tracer'):
        groups = [g[metric_names].to_numpy() for _, g in q.groupby('fold')]
        draws = np.array([np.concatenate([g[rng.integers(len(g), size=len(g))] for g in groups]).mean(0) for _ in range(2000)])
        ci = np.quantile(draws, [.025, .975], axis=0)
        for j, name in enumerate(metric_names):
            summaries.append(dict(tracer=tracer, metric=name, n=len(q), mean=float(q[name].mean()),
                sd=float(q[name].std(ddof=1)), ci_low=float(ci[0,j]), ci_high=float(ci[1,j])))
    pd.DataFrame(summaries).to_csv(OUT / 'overall_summary.csv', index=False)
    write_json(OUT / 'summary.json', dict(status='COMPLETE', subjects=metrics.ptid.nunique(), volumes=len(metrics),
        expected_by_tracer={t:sum(r['has_'+t] for r in rows) for t in ['fdg','av45']},
        checkpoint_snapshots=snapshots, completion=completions, training=train_audits, metrics=summaries,
        coverage='Exact active PTID x held-out fold x available tracer; no duplicates or missing',
        aggregation='Unweighted mean over subjects within each tracer; sample SD; 2000 fold-stratified bootstrap draws seed 20261020',
        units='PSNR dB (data_range=1); SSIM7/11 dimensionless; MAE/ROI MAE normalized uptake; MSE squared normalized uptake',
        roi='Subject mean over valid frozen 98 ROIs, PET-independent validity; frozen physical hemisphere names',
        protocol='Native E1 prediction: MRI + network velocity at t=0, clipped [0,1], FP16 autocast; original 160x192x160 cache without renormalization',
        limitation='Full final165 OOF result only. No-Scores contrast pending; no clinical equivalence or historical paper reproduction claim.',
        input_config_sha256=sha(Path(cfg['report'])/'config.json'), cohort_sha256=sha(Path(cfg['report'])/'cohort.json')))
    report = ['E1 Full：最终165 epoch两折OOF推理与指标', '',
        f'状态：COMPLETE；有效受试者{metrics.ptid.nunique()}人；可用PET配对{len(metrics)}例；精确覆盖冻结留出名单，无缺失、重复。',
        '两折checkpoint均为epoch=164（已完成165 epoch），各153120次更新；模型、优化器有限且身份哈希匹配。',
        '', '按受试者汇总的均值 ± 样本标准差：']
    for tracer in ['fdg','av45']:
        q = {r['metric']:r for r in summaries if r['tracer']==tracer}
        report.append(f"{tracer.upper()} (n={q['psnr']['n']}): " + '; '.join(f"{name}={q[name]['mean']:.6f} ± {q[name]['sd']:.6f}" for name in metric_names))
    report += ['', '协议：原始160×192×160全体素网格、data_range=1，无二次归一化；SSIM为sigma=1.5的valid Gaussian窗口7与11。关闭cuDNN TF32，并在各折与原始CPU/GPU实现抽样核对，容差5e-5。',
        'ROI MAE：每人98个冻结ROI中有效ROI的绝对均值差，再按人等权汇总；采用PET无关有效性过滤与冻结物理半球命名。',
        'MSE为每人全体素平方误差均值；MAE为每人全体素绝对误差均值；brain_mae限制在冻结mask>0区域。PSNR按人计算再平均，不能由总体平均MSE倒算。',
        '', '预测文件目录（未压缩NIfTI，完整索引及SHA见prediction_index.json）：']
    report += [f"fold{fold}: {c['predictions']} ({c['prediction_count']} files)" for fold, c in enumerate(completions, 1)]
    report += ['', '证据：summary.json、overall_summary.csv（含95%分层bootstrap CI）、per_subject_metrics.csv、per_fold_summary.csv、per_diagnosis_summary.csv、regions_long.csv、两折snapshot.json/complete.json、原始日志及退出码。',
        '限制：这些是当前E1 Full最终两折OOF结果；No-Scores尚需完成后进行配对比较。所有强度仅称normalized uptake，不能写为SUVR、临床等效或历史论文协议复现。']
    (OUT / 'REPORT.md').write_text('```text\n'+'\n'.join(report)+'\n```\n')
    print(pd.DataFrame(summaries).to_string(index=False))

if __name__ == '__main__':
    main()
