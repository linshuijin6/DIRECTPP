"""Bind interim metrics and paper references; require full held-out coverage."""
import csv
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
sys.path.insert(0, str(ROOT / 'experiments/e1_clinical_conditioning'))
from common import active_rows, load_config, sha, write_json


def main():
    cfg = load_config(ROOT / 'reports/e1_stage01_20261017/config.json')
    cohort = active_rows(cfg, json.loads((Path(cfg['report']) / 'cohort.json').read_text()))
    convergence = []
    for fold, node in [(1, '3002'), (2, '3003')]:
        log = ROOT / f'reports/e1_amp_recovery_20261018/logs/{node}_fold{fold}_Full.log'
        log_snapshot = OUT / f'fold{fold}_training_at_summary.log'
        log_snapshot.write_text(log.read_text())
        events = []
        for line in log_snapshot.read_text().splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
        epochs = [r for r in events if r.get('event') == 'epoch_complete']
        with (OUT / f'fold{fold}_training_epochs.csv').open('w') as f:
            writer = csv.DictWriter(f, fieldnames=list(epochs[0]))
            writer.writeheader()
            writer.writerows(epochs)
        last = float(np.mean([r['loss'] for r in epochs[-10:]]))
        previous = float(np.mean([r['loss'] for r in epochs[-20:-10]]))
        convergence.append(dict(fold=fold, node=node, completed_epochs=len(epochs),
                                latest_loss=epochs[-1]['loss'], previous10_mean=previous,
                                latest10_mean=last, loss_reduction_percent=100 * (previous-last)/previous,
                                latest20_slope=float(np.polyfit([r['epoch'] for r in epochs[-20:]],
                                                                [r['loss'] for r in epochs[-20:]], 1)[0]),
                                epoch_seconds_median=float(np.median([r['seconds'] for r in epochs[-10:]])),
                                overflow_retries=sum(e.get('event') == 'amp_overflow_retry' for e in events),
                                live_log=str(log), log_snapshot=str(log_snapshot), log_sha256=sha(log_snapshot),
                                conclusion='still improving; no held-out validation trajectory; endpoint t=0 phase not reached'))
    write_json(OUT / 'convergence.json', convergence)
    completion = [json.loads((OUT / f'fold{fold}/complete.json').read_text()) for fold in [1, 2]]
    snapshots = [json.loads((OUT / f'fold{fold}/snapshot.json').read_text()) for fold in [1, 2]]
    metrics = pd.concat([pd.read_csv(OUT / f'fold{fold}/metrics.csv') for fold in [1, 2]], ignore_index=True)
    expected = {(r['ptid'], r['test_fold'], tracer) for r in cohort for tracer in ['fdg', 'av45'] if r['has_' + tracer]}
    actual = set(metrics[['ptid', 'fold', 'tracer']].itertuples(index=False, name=None))
    assert actual == expected and len(metrics) == len(expected)
    for snapshot in snapshots:
        assert sha(snapshot['checkpoint']) == snapshot['checkpoint_sha256']
        subset = metrics[metrics.fold == snapshot['identity']['fold']]
        assert set(subset.checkpoint_sha256) == {snapshot['checkpoint_sha256']}
    metrics.to_csv(OUT / 'per_subject_metrics.csv', index=False)
    paper_file = ROOT / 'reports/history_audit_20261017/paper_generation_plot_values.csv'
    paper = pd.read_csv(paper_file)
    comparisons = []
    rng = np.random.default_rng(20261019)
    metric_names = ['ssim7', 'ssim11', 'psnr', 'mse', 'mae', 'roi_mae', 'brain_mae']
    for tracer, q in metrics.groupby('tracer'):
        ref = paper[(paper.cohort == 'ADNI') & (paper.tracer.str.lower() == tracer) & (paper.method == 'Ours')].iloc[0]
        means = q[metric_names].mean()
        # Each tracer has one observation per subject; preserve each outer fold's size.
        groups = [g[metric_names].to_numpy() for _, g in q.groupby('fold')]
        draws = np.array([np.concatenate([g[rng.integers(len(g), size=len(g))] for g in groups]).mean(0)
                          for _ in range(2000)])
        low, high = np.quantile(draws, [.025, .975], axis=0)
        for j, metric in enumerate(metric_names):
            key = {'ssim7': 'SSIM_percent', 'ssim11': 'SSIM_percent', 'psnr': 'PSNR',
                   'mse': 'MSE_percent', 'mae': 'MAE_percent'}.get(metric)
            factor = 100 if metric in ['ssim7', 'ssim11', 'mse', 'mae'] else 1
            paper_value = float(ref[key]) if key else None
            current = float(means[metric]) * factor
            comparisons.append(dict(tracer=tracer, n=len(q), metric=metric,
                 unit='percent' if factor == 100 else ('dB' if metric == 'psnr' else 'normalized uptake'),
                 current=current, current_ci_low=float(low[j])*factor, current_ci_high=float(high[j])*factor,
                 paper=paper_value, delta=None if paper_value is None else current-paper_value))
    pd.DataFrame(comparisons).to_csv(OUT / 'paper_comparison.csv', index=False)
    metrics.groupby(['fold', 'tracer'])[metric_names].agg(['count', 'mean', 'std']).to_csv(OUT / 'per_fold_summary.csv')
    metrics.groupby(['diagnosis', 'tracer'])[metric_names].agg(['count', 'mean', 'std']).to_csv(OUT / 'per_diagnosis_summary.csv')
    write_json(OUT / 'summary.json', dict(status='COMPLETE', subjects=metrics.ptid.nunique(),
               volumes=len(metrics), convergence=convergence, snapshots=snapshots, completion=completion,
               comparison=comparisons, paper_source=str(paper_file), paper_source_sha256=sha(paper_file),
               cohort_sha256=sha(Path(cfg['report']) / 'cohort.json'),
               coverage='exact active PTID x held-out fold x available tracer; zero duplicates or missing',
               interpretation='interim E1 Full OOF descriptive comparison to historical paper numbers; cohort and SSIM window binding to paper unresolved'))
    print(pd.DataFrame(comparisons).to_string(index=False))


if __name__ == '__main__':
    main()
