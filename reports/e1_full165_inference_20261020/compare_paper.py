"""Recheck Full165 metrics and compare to directly verified ADNI figure inputs."""
import csv
import hashlib
import json
import math
from pathlib import Path
from collections import defaultdict

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main():
    cfg_path = ROOT / 'reports/e1_stage01_20261017/config.json'
    cfg = json.loads(cfg_path.read_text())
    cohort_path = Path(cfg['report']) / 'cohort.json'
    excluded = {r['ptid'] for r in json.loads(Path(cfg['qc_exclusions']).read_text())['excluded']}
    cohort = [r for r in json.loads(cohort_path.read_text()) if r['ptid'] not in excluded]
    expected = {(r['ptid'], str(r['test_fold']), t) for r in cohort for t in ['fdg', 'av45'] if r['has_' + t]}
    metrics_path = OUT / 'per_subject_metrics.csv'
    with metrics_path.open() as f: rows = list(csv.DictReader(f))
    actual = {(r['ptid'], r['fold'], r['tracer']) for r in rows}
    assert actual == expected and len(rows) == len(expected)
    assert (OUT / 'summary.exit').read_text().strip() == '0'
    summary = json.loads((OUT / 'summary.json').read_text())
    assert sha(cfg_path) == summary['input_config_sha256'] and sha(cohort_path) == summary['cohort_sha256']
    checkpoints = []
    for fold in [1, 2]:
        assert (OUT / f'fold{fold}.exit').read_text().strip() == '0'
        snap = json.loads((OUT / f'fold{fold}/snapshot.json').read_text())
        complete = json.loads((OUT / f'fold{fold}/complete.json').read_text())
        assert snap['completed_epochs'] == complete['completed_epochs'] == 165
        assert snap['optimizer_updates'] == 153120
        assert sha(snap['checkpoint']) == snap['checkpoint_sha256'] == complete['checkpoint_sha256']
        assert set(r['checkpoint_sha256'] for r in rows if int(r['fold']) == fold) == {snap['checkpoint_sha256']}
        checkpoints.append(dict(fold=fold, sha256=snap['checkpoint_sha256']))
    psnr_error = max(abs(float(r['psnr']) + 10*math.log10(float(r['mse']))) for r in rows)
    assert psnr_error < 1e-10
    ref_path = ROOT / 'reports/current_ckpt_diagnostic_20261019/paper_reference_verified.json'
    ref = json.loads(ref_path.read_text())
    assert sha(ref['source']) == ref['source_sha256']
    nb = json.loads(Path(ref['source']).read_text())
    reference = {}
    for rec in ref['entries']:
        source = ''.join(nb['cells'][rec['cell_zero_based']]['source'])
        assert hashlib.sha256(source.encode()).hexdigest() == rec['cell_source_sha256']
        assert rec['source_line'] in source
        reference[rec['tracer']] = dict(zip(['ssim7','psnr','mse','mae'], rec['values_SSIMP_PSNR_MSEP_MAEP']))
    comparison = []
    for tracer in ['fdg','av45']:
        subset = [r for r in rows if r['tracer'] == tracer]
        for metric in ['ssim7','ssim11','psnr','mse','mae']:
            factor = 1 if metric == 'psnr' else 100
            name = 'ssim7' if metric == 'ssim11' else metric
            paper = reference[tracer][name]
            current = factor*sum(float(r[metric]) for r in subset)/len(subset)
            old = next(r for r in summary['metrics'] if r['tracer'] == tracer and r['metric'] == metric)
            assert abs(current/factor-old['mean']) < 1e-12
            delta = current-paper
            comparison.append(dict(tracer=tracer, n=len(subset), metric=metric,
                paper=paper, current=current, delta_current_minus_paper=delta,
                relative_change_percent=100*delta/paper, sd=old['sd']*factor,
                current_ci_low=old['ci_low']*factor, current_ci_high=old['ci_high']*factor,
                numerically_better=(delta>0 if metric in ['ssim7','ssim11','psnr'] else delta<0),
                unit='dB' if metric=='psnr' else ('SSIM x100' if metric.startswith('ssim') else metric.upper()+' x100'),
                reference_scope='Historical Fig.2 plotting input; original per-subject fold/cohort/aggregation binding unresolved'))
    with (OUT / 'paper_comparison.csv').open('w') as f:
        writer=csv.DictWriter(f, fieldnames=list(comparison[0]));writer.writeheader();writer.writerows(comparison)
    report = [
        'Full最终165 epoch与原文ADNI汇总值的核对', '',
        '结论：PSNR均低于原文；FDG其他三项数值更好，AV45的SSIM与MAE更差、MSE略好。因此不能概括为所有指标下降，也不能据此宣称同协议复现。', '',
        '已核实：两折推理与自动汇总退出码均为0；有效队列1856人、2961个PTID×tracer配对；FDG 1597例、AV45 1364例。精确核对冻结PTID×held-out fold×available tracer集合，无缺失、重复。两折均为完成165 epoch的checkpoint，各153120次更新，checkpoint SHA与逐人结果绑定一致。逐人重算均值与汇总一致；PSNR=-10log10(MSE)，最大差异'+f'{psnr_error:.3g} dB。', '',
        '比较单位：SSIM、MSE、MAE均乘100，与历史绘图输入对齐；PSNR为dB。delta=当前−原文。SSIM差值为百分点，MSE/MAE差值为对应误差乘100单位。',
        '示踪剂  指标       原文       当前        delta        数值方向',
    ]
    for r in comparison:
        report.append(f"{r['tracer'].upper():<6} {r['metric']:<9} {r['paper']:>8.4f} {r['current']:>10.4f} {r['delta_current_minus_paper']:>+11.4f}   {'更好' if r['numerically_better'] else '更差'}")
    report += ['',
        '主要PSNR差距：FDG 28.72→27.23177 dB，下降1.48823 dB；AV45 28.09→24.91077 dB，下降3.17923 dB。',
        '当前PSNR的95%分层bootstrap CI：FDG [27.12887,27.33290]，AV45 [24.79731,25.03327]。这些CI仅描述本次队列的不确定性，不是与原文的配对差值CI或显著性检验。',
        'FDG：SSIM7提高1.04262个百分点，MSE降低33.39386%，MAE降低17.44327%。AV45：SSIM7降低1.81722个百分点，MSE降低4.88992%，MAE升高16.35507%。相对变化精确值以CSV为准。', '',
        '折间核查：FDG fold1/fold2 PSNR为27.23120/27.23234 dB；AV45为24.96351/24.85880 dB。两折均低于各自原文PSNR，差距不是由单折单独造成。',
        'SSIM窗口敏感性：FDG窗口7/11为90.98262/91.30750；AV45为86.39278/86.22594。更换这两个窗口不会改变与原文的差异方向，也不会影响PSNR。', '',
        '解释边界：PSNR按人取log后平均，MSE直接按人平均，因此平均MSE更低但平均PSNR更低在数学上可以同时成立。该现象值得核对原文逐人误差分布与汇总绑定，不能直接判定当前计算或原文数值错误。',
        '原文依据：BMEF_main.tex:106明确写ADNI AV45 PSNR=28.09；四指标完整数值来自核心绘图notebook的零起算cells 9（FDG）、10（AV45），本轮重新核对原文件及cell SHA。该notebook把SSIM/MSE/MAE标为百分数；比较使用雷达图归一化之前的data输入。',
        '协议已知：当前在160×192×160全体素网格、data_range=1上按人计算，无二次归一化；原生E1单步预测后clip[0,1]；SSIM sigma=1.5、valid Gaussian窗口7/11、cuDNN TF32关闭并抽样与原始CPU/GPU实现核对。',
        'SSIM比较口径限制：表中窗口7是参照可见历史评估示例选取，窗口11为敏感性分析；尚未证明Fig.2实际使用哪个窗口。',
        '历史评估示例：四指标notebook cell7声明SSIM窗口7、PSNR max_val=1，并用MONAI MSE/MAE；但该cell加载140 epoch权重并遍历train_loader，不能把它当作Fig.2最终165 epoch OOF结果的执行证明。',
        '尚未对齐：原文四指标的逐人测试名单、实际fold/checkpoint绑定及聚合链。原文总队列1857人，当前按冻结QC排除016_S_4952后1856人；这一已知差异不足以确定指标差距的原因。',
        '稿件文案：BMEF_main.tex:102写生成评估3-fold，与作者当前确认的生成器两折OOF→分类器三折设计不一致；本次按既定两折执行，没有据此更改实验或稿件。',
        '当前结果可作为本次E1 Full基线；Full/No-Scores的结论应基于同队列配对结果，不能沿用原文汇总值作为本次Full结果，也不能用不同协议的历史基线宣称排名或显著性。', '',
        '本轮仅核对并新增对照报告/CSV/收据；未启动新实验、修改权重、队列、稿件或历史资产。',
    ]
    # Derive percentages directly from the validated table rather than hand-rounded prose.
    fdg={r['metric']:r for r in comparison if r['tracer']=='fdg'}
    av45={r['metric']:r for r in comparison if r['tracer']=='av45'}
    report=[line if not line.startswith('FDG：SSIM7提高') else f"FDG：SSIM7提高{fdg['ssim7']['delta_current_minus_paper']:.5f}个百分点，MSE降低{-fdg['mse']['relative_change_percent']:.5f}%，MAE降低{-fdg['mae']['relative_change_percent']:.5f}%。AV45：SSIM7降低{-av45['ssim7']['delta_current_minus_paper']:.5f}个百分点，MSE降低{-av45['mse']['relative_change_percent']:.5f}%，MAE升高{av45['mae']['relative_change_percent']:.5f}%。" for line in report]
    (OUT / 'PAPER_COMPARISON.md').write_text('```text\n'+'\n'.join(report)+'\n```\n')
    receipt=dict(status='PASS',subjects=len(cohort),volumes=len(rows),checkpoints=checkpoints,
        exact_coverage=True,no_duplicates=True,means_recomputed=True,max_psnr_formula_error=psnr_error,
        source_sha256={str(p):sha(p) for p in [Path(__file__),metrics_path,cfg_path,cohort_path,ref_path,Path(ref['source']),ROOT/'manuscript/BMEF_main.tex',ROOT/'source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_reflow_test or fanhua.ipynb']},
        comparison_scope='Descriptive historical summary comparison; no matched original sample or significance claim')
    (OUT/'paper_comparison_verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    print('\n'.join(report[:20]))

if __name__=='__main__':main()
