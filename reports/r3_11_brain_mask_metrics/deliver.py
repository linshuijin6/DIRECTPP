"""Render aggregate-only supplementary drafts and independently check outputs."""
import csv
import hashlib
import json
import math
import statistics
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

OUT = Path(__file__).resolve().parent / 'run_20261102'
LABEL = {'Full': 'DIReCT++ Full (e165)', 'ClinicalUNet': 'Clinical Regression 3D U-Net (e165)', 'SwinUNETR': 'Swin-UNETR (e200; MRI only)'}
METRICS = ['ssim','psnr','mse','mae']
DECIMALS = {'ssim':5,'psnr':3,'mse':6,'mae':5}


def md_table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,row))+' |' for row in rows])


def number(metric, x):
    return f'{x:.{DECIMALS[metric]}f}'


def pformat(x):
    return '<1e-300' if x==0 else f'{x:.3g}'


def main():
    df=pd.read_csv(OUT/'per_subject_metrics.csv')
    summary=pd.read_csv(OUT/'summary_metrics.csv')
    paired=pd.read_csv(OUT/'paired_comparisons.csv')
    direction=pd.read_csv(OUT/'whole_volume_direction_comparison.csv')
    repair=json.loads((OUT/'canonical_targets/exact_patches/patch_receipts.json').read_text())
    assert repair['status']=='PASS_EXACT_LOSSLESS_TARGET_TRANSPORT' and repair['targets']==1401
    initial_manifest=json.loads((OUT/'input_manifest.json').read_text())
    excluded={r['ptid'] for r in initial_manifest['excluded']}
    repo=OUT.parents[2]
    original=pd.read_csv(repo/'reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv')
    original=original[original.epoch==165]
    available=set(zip(original.ptid,original.tracer.str.lower()))
    eligibility=[]
    for row in json.loads((repo/'reports/original_author_reproduction_20261020/cohort.json').read_text()):
        for tracer in ['fdg','av45']:
            has_pet=(row['name'],tracer) in available
            reason='no_valid_target_in_frozen_OOF' if not has_pet else ('frozen_mask_QC_exclusion' if row['name'] in excluded else 'included')
            eligibility.append({'ptid':row['name'],'tracer':tracer,'fold':row['test_fold'],'valid_frozen_target':has_pet,'included':reason=='included','reason':reason})
    pd.DataFrame(eligibility).to_csv(OUT/'eligibility_and_exclusions_internal.csv',index=False)
    eligibility_counts={t:{reason:sum(r['tracer']==t and r['reason']==reason for r in eligibility)
        for reason in ['no_valid_target_in_frozen_OOF','frozen_mask_QC_exclusion','included']} for t in ['fdg','av45']}
    assert eligibility_counts=={'fdg':{'no_valid_target_in_frozen_OOF':259,'frozen_mask_QC_exclusion':1,'included':1597},'av45':{'no_valid_target_in_frozen_OOF':492,'frozen_mask_QC_exclusion':1,'included':1364}}
    assert len(df)==8883 and len(paired)==16 and len(summary)==24
    discrepancies=[]
    for r in summary.to_dict('records'):
        a=df[(df.model==r['model'])&(df.tracer==r['tracer'])][r['metric']].tolist()
        assert len(a)==r['n']
        expected={'mean':statistics.fmean(a),'sd':statistics.stdev(a),'median':statistics.median(a),
                  'p05':float(np.percentile(a,5)),'p95':float(np.percentile(a,95))}
        for k,v in expected.items():
            discrepancies.append(abs(v-r[k]));assert math.isclose(v,r[k],rel_tol=1e-12,abs_tol=1e-14)
    for comparison,g in paired.groupby('comparison',sort=False):
        assert len(g)==8 and set(zip(g.tracer,g.metric))=={(t,m) for t in ['fdg','av45'] for m in METRICS}
        ps=g.p_raw.to_numpy();order=np.argsort(ps,kind='stable')
        adjusted=np.empty(8);adjusted[order]=np.minimum(1,np.maximum.accumulate(ps[order]*np.arange(8,0,-1)))
        assert np.allclose(adjusted,g.p_holm.to_numpy(),rtol=1e-12,atol=1e-300)
        for r in g.to_dict('records'):
            a=df[(df.model=='Full')&(df.tracer==r['tracer'])].sort_values(['fold','ptid'])
            b=df[(df.model==r['comparator'])&(df.tracer==r['tracer'])].sort_values(['fold','ptid'])
            assert list(zip(a.ptid,a.fold))==list(zip(b.ptid,b.fold))
            d=(a[r['metric']].to_numpy()-b[r['metric']].to_numpy()).tolist()
            mean=statistics.fmean(d);dz=mean/statistics.stdev(d)
            assert math.isclose(mean,r['mean_difference'],rel_tol=1e-10,abs_tol=1e-14)
            assert math.isclose(dz,r['cohen_dz'],rel_tol=1e-10,abs_tol=1e-12)
            independent=stats.ttest_1samp(d,0)
            assert math.isclose(float(independent.pvalue),r['p_raw'],rel_tol=1e-8,abs_tol=1e-300)
            sign=1 if r['metric'] in ['ssim','psnr'] else -1
            assert sum(sign*x>0 for x in d)==r['full_better_count']
    # Reload the independent index to validate all three model identities/counts.
    index=pd.read_csv(OUT/'input_index.csv')
    keys=['model','ptid','tracer','fold','epoch']
    assert set(map(tuple,index[keys].values))==set(map(tuple,df[keys].values))
    for _,g in df.groupby(['ptid','tracer','fold']):
        assert len(g)==3 and g.target_array_sha256.nunique()==1 and g.brain_mask_array_sha256.nunique()==1
        assert g.valid_ssim_centers.nunique()==g.mask_voxels.nunique()==1

    summary_rows=[];cells=[]
    for model in ['Full','ClinicalUNet','SwinUNETR']:
        for tracer in ['fdg','av45']:
            group=summary[(summary.model==model)&(summary.tracer==tracer)].set_index('metric')
            values=[f"{number(m,group.loc[m,'mean'])} ± {number(m,group.loc[m,'sd'])}" for m in METRICS]
            row=[LABEL[model],tracer.upper(),int(group.n.iloc[0]),*values]
            summary_rows.append(row)
            for m,text in zip(METRICS,values):cells.append({'table':'summary','model_or_comparison':model,'tracer':tracer,'metric':m,'display':text})
    summary_headers=['Model','Tracer','N','SSIM ↑','PSNR (dB) ↑','MSE ↓','MAE ↓']
    notes=("Values are mean ± sample SD across subjects. SSIM is unitless; PSNR is in dB; MSE and MAE use squared and unsquared [0,1] normalized-uptake units, respectively. "
           "All models use byte-identical frozen target PET arrays and identical subject-specific masks. "
           "The mask is the frozen SynthSeg nonzero-label union, including cortex, white matter, subcortical structures, cerebellum, brainstem, ventricles and CSF; it is not a pure parenchymal mask. "
           "SSIM uses the existing E1 3D Gaussian implementation (kernel 7, sigma 1.5, data range 1) and only centers whose entire 7×7×7 window lies inside the mask. "
           "The frozen mask QC exclusion removes one subject from each tracer; no new exclusions or spatial/intensity transformations were applied. "
           "Full and Clinical U-Net use epoch 165; MRI-only Swin-UNETR uses the prespecified final epoch 200. All predictions are frozen two-fold OOF outputs.")
    aggregate_md=md_table(summary_headers,summary_rows)
    (OUT/'supplementary_summary.md').write_text('# Mask-restricted PET image quality\n\n'+aggregate_md+'\n\n'+notes+'\n')
    texrows=[' & '.join(str(x).replace('DIReCT++','DIReCT++').replace(' ± ',r' $\pm$ ') for x in row)+r' \\' for row in summary_rows]
    tex='\n'.join([r'\begin{table*}[t]',r'\centering',r'\caption{Mask-restricted quality of frozen two-fold OOF PET predictions.}',r'\label{tab:r3_11_masked_summary}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{lllrrrr}',r'\hline',r'Model & Tracer & $N$ & SSIM $\uparrow$ & PSNR (dB) $\uparrow$ & MSE $\downarrow$ & MAE $\downarrow$ \\',r'\hline',*texrows,r'\hline',r'\end{tabular}}',r'\par\smallskip',r'\begin{minipage}{\textwidth}\footnotesize',notes.replace('±',r'$\pm$').replace('×',r'$\times$').replace('↑','').replace('↓',''),r'\end{minipage}',r'\end{table*}',''])
    (OUT/'supplementary_summary.tex').write_text(tex)
    paired_headers=['Comparison','Tracer','Metric','N','Mean Δ','95% bootstrap CI','t','Cohen dz','Full better (%)','Raw p','Holm p']
    paired_rows=[]
    for r in paired.to_dict('records'):
        m=r['metric'];contrast='A: Full − Clinical U-Net' if r['comparator']=='ClinicalUNet' else 'B: Full − Swin-UNETR'
        row=[contrast,r['tracer'].upper(),m.upper(),r['n'],number(m,r['mean_difference']),
             f"[{number(m,r['ci_lower'])}, {number(m,r['ci_upper'])}]",f"{r['t_statistic']:.3f}",f"{r['cohen_dz']:.3f}",f"{r['full_better_proportion']*100:.1f}",pformat(r['p_raw']),pformat(r['p_holm'])]
        paired_rows.append(row)
        for column,text in zip(paired_headers[4:],row[4:]):cells.append({'table':'paired_'+column,'model_or_comparison':r['comparison'],'tracer':r['tracer'],'metric':m,'display':str(text)})
    paired_notes=("Δ = DIReCT++ Full minus comparator on exactly matched subject, tracer and held-out fold. Positive differences favor Full for SSIM/PSNR; negative differences favor Full for MSE/MAE. "
                  "Cohen's dz uses this signed difference divided by its sample SD. Full-better proportions use strict metric-specific improvement. "
                  "Two-sided paired t-tests; 95% percentile bootstrap CIs use 10,000 paired resamples, seed 42, stratified by held-out fold with original fold sizes retained. "
                  "Holm correction is applied separately to comparison A and comparison B, with eight tests (2 tracers × 4 metrics) in each family; CIs are unadjusted. "
                  "Uncertainty concerns the frozen OOF subjects, not retraining/seed variability. Statistical significance is not clinical equivalence. "
                  "The two comparisons differ in information and endpoint: A uses matched MRI/clinical/tracer information at e165; B compares Full e165 with MRI-only Swin-UNETR e200. "
                  "A displayed p <1e-300 denotes numerical underflow of the computed p value, not an exactly zero probability.")
    paired_md=md_table(paired_headers,paired_rows)
    (OUT/'supplementary_paired.md').write_text('# Paired mask-restricted comparisons\n\n'+paired_md+'\n\n'+paired_notes+'\n')
    tr=[]
    for row in paired_rows:
        rr=[str(x).replace('−',r'$-$') for x in row]
        rr=[(r'$<10^{-300}$' if x=='<1e-300' else x) for x in rr]
        tr.append(' & '.join(rr)+r' \\')
    (OUT/'supplementary_paired.tex').write_text('\n'.join([r'\begin{table*}[t]',r'\centering',r'\caption{Paired mask-restricted PET image-quality comparisons.}',r'\label{tab:r3_11_masked_paired}',r'\resizebox{\textwidth}{!}{%',r'\begin{tabular}{lllrrrrrrrr}',r'\hline',r'Comparison & Tracer & Metric & $N$ & Mean $\Delta$ & 95\% bootstrap CI & $t$ & Cohen $d_z$ & Full better (\%) & Raw $p$ & Holm $p$ \\',r'\hline',*tr,r'\hline',r'\end{tabular}}',r'\par\smallskip',r'\begin{minipage}{\textwidth}\footnotesize',paired_notes.replace('%',r'\%').replace('Δ',r'$\Delta$').replace('×',r'$\times$').replace('<1e-300',r'$<10^{-300}$'),r'\end{minipage}',r'\end{table*}','']))
    with (OUT/'table_cells_internal.csv').open('w',newline='') as stream:
        w=csv.DictWriter(stream,fieldnames=list(cells[0]));w.writeheader();w.writerows(cells)
    # Check written Markdown and LaTeX cells against their independently read CSV values.
    md=(OUT/'supplementary_summary.md').read_text();tex=(OUT/'supplementary_summary.tex').read_text()
    for row in summary_rows:
        assert all(str(x) in md for x in row)
        assert all(str(x).replace(' ± ',r' $\pm$ ') in tex for x in row)
    md=(OUT/'supplementary_paired.md').read_text();tex=(OUT/'supplementary_paired.tex').read_text()
    for row in paired_rows:
        assert all(str(x) in md for x in row)
        assert all(str(x).replace('−',r'$-$') in tex or str(x)=='<1e-300' for x in row)
    for path in OUT.glob('supplementary_*'):
        text=path.read_text()
        import re
        assert not re.search(r'\b\d{3}_S_\d{4}\b',text),path
    assets=[json.loads(line) for line in (OUT/'subject_asset_checks.jsonl').read_text().splitlines()]
    mask_sizes=np.asarray([r['mask_voxels'] for r in assets])
    center_sizes=np.asarray([r['valid_ssim_centers'] for r in assets])
    mask_support_text=(f"原始数组每人共有 {160*192*160:,} 个体素；mask 内体素数中位数为 {int(np.median(mask_sizes)):,}"
        f"（范围 {int(mask_sizes.min()):,}–{int(mask_sizes.max()):,}），占原数组的平均比例为 {100*mask_sizes.mean()/(160*192*160):.2f}%。"
        f"完整 7×7×7 窗口的有效 SSIM 中心中位数为 {int(np.median(center_sizes)):,}"
        f"（范围 {int(center_sizes.min()):,}–{int(center_sizes.max()):,}）；全体积 valid-convolution SSIM 场共有 {154*186*154:,} 个中心。")
    labels=sorted({label for row in assets for label in row['mask_labels']})
    available={int(r['region']):r['region_name'] for r in csv.DictReader((OUT.parents[2]/'reports/e1_stage01_20261017/roi_labels.csv').open())}
    coverage=[{'label':l,'frozen_region_name':available.get(l,'unlisted'),'subjects_containing_label':sum(l in r['mask_labels'] for r in assets)} for l in labels]
    pd.DataFrame(coverage).to_csv(OUT/'mask_label_coverage.csv',index=False)
    nonbrain=[r for r in coverage if 'Ventricle' in r['frozen_region_name'] or 'Inf-Lat-Vent' in r['frozen_region_name'] or r['frozen_region_name']=='CSF']
    assert nonbrain
    nsign=int((paired.p_holm<.05).sum())
    favorable=(paired.mean_difference*np.where(paired.metric.isin(['ssim','psnr']),1,-1)>0)
    shifts=direction[~direction.direction_agrees]
    conclusion=f"16 项预定义 masked 配对比较中，{int(favorable.sum())} 项均值方向支持 Full，{nsign} 项在各自 8 项检验族内经 Holm 校正后 p<0.05。"
    if len(shifts):
        conclusion+=f"与相同 mask 交集上的 whole-volume 平均差值相比，{len(shifts)} 项方向不同；详见下表，不将背景限制后的结果概括为全面优势。"
    else:conclusion+='16 项平均差值方向与相同 mask 交集上的 whole-volume 结果一致。'
    contrast_text=[]
    for comparator,group in paired.groupby('comparator',sort=False):
        favors=group.mean_difference*np.where(group.metric.isin(['ssim','psnr']),1,-1)>0
        significant=group.p_holm<.05
        contrast_text.append(f"{LABEL[comparator]}：8 项均值差中 {int(favors.sum())} 项支持 Full，{int((favors & significant).sum())} 项同时有 Holm 校正后的配对统计支持；{int((~favors & significant).sum())} 项显著支持比较模型，{int((~significant).sum())} 项未达到该校正标准。")
    contrast_text='\n\n'.join(contrast_text)
    av45_errors=paired[(paired.comparator=='ClinicalUNet')&(paired.tracer=='av45')&paired.metric.isin(['mse','mae'])]
    effect_note=(f"优势大小随指标变化。对 Clinical U-Net 的 AV45 MSE/MAE，|Cohen's dz| 分别为 "
        f"{abs(float(av45_errors[av45_errors.metric=='mse'].cohen_dz.iloc[0])):.3f} 和 "
        f"{abs(float(av45_errors[av45_errors.metric=='mae'].cohen_dz.iloc[0])):.3f}，Full 获益比例仅约 "
        f"{100*av45_errors.full_better_proportion.min():.1f}%–{100*av45_errors.full_better_proportion.max():.1f}%。"
        "这些是很小的标准化效应；统计支持不应表述为普遍个体获益或临床上的显著改善。")
    changes=md_table(['Comparison','Tracer','Metric','Whole-volume Δ','Masked Δ','Direction agrees'],[[r['comparison'],r['tracer'].upper(),r['metric'].upper(),number(r['metric'],r['whole_volume_mean_difference_same_intersection']),number(r['metric'],r['masked_mean_difference']),str(r['direction_agrees'])] for r in direction.to_dict('records')])
    report=f'''# R3-11：冻结 OOF PET 的 SynthSeg mask 内图像质量

{conclusion}

{contrast_text}

{effect_note}

## 模型、样本与目标身份

本次只读取冻结预测与真实 PET。Full e165 来自 original_author_reproduction_20261020，Clinical Regression 3D U-Net e165 来自 task_a_20261027_instance1，Swin-UNETR e200 来自 20261102 已完成的四份两折 OOF 回执。未使用旧 E1 Full 的独立评价结果，也未使用历史 Figure 2 指标。Full 是本轮作者代码语义重建，并不证明原论文历史运行的身份。A 为相同 MRI、八项临床变量与 tracer 信息的框架比较；B 为 Full e165 对 MRI-only Swin-UNETR e200，输入信息和训练终点均不同，不能解释成严格等信息或同训练预算比较。

冻结两折不变。每模型 FDG N=1,597（fold1=791，fold2=806），AV45 N=1,364（fold1=689，fold2=675），共 2,961 个 subject-tracer 观察。内部清单逐项保存 PTID/tracer/fold、预测原路径与副本路径、预期及实际哈希、checkpoint 身份、mask 与 target 数组哈希。所有配对键以及同病例的 target/mask 数组哈希完全一致。冻结的 1,857 人队列中，FDG 259 人、AV45 492 人原本没有相应有效 OOF PET 目标，因此原始有效 OOF 为 FDG 1,598、AV45 1,365；随后两者均因 E1 冻结的同一个 MRI/mask QC 失败病例排除 1 例，无新增排除。全部纳入/未纳入原因逐项保存在 eligibility_and_exclusions_internal.csv；论文表不含受试者标识。

真实 PET 统一取 Full 已验证持久缓存中的原有 [0,1] 数组，所有模型用同一数组。E1 NPZ 仅提供冻结 mask；其 PET 不替代实际评价目标。Full 与 E1 的冻结原始输入清单在 5,571 项 MRI/FDG/AV45 的路径、字节数及记录哈希上相同；本次没有重新读取不可挂载的历史 raw-NIfTI。空间对应直接复用既有 MRI-anchored array-index 验证：不改 affine，不翻转、配准或重采样。Full 的 identity affine 只作为既有 header 记录，不作为空间匹配证明。

初次全队列合并发现 1,401 个 subject–tracer 的云端 PET 缓存与本地 canonical Full PET 的数组哈希不同，mask 哈希全部一致，因此汇总在统计检验前停止。逐值核查的最大绝对差为 {repair['max_abs_difference']:.12g}（[0,1] normalized-uptake 单位）。随后无损传递 canonical 数组的精确字节，在内存中恢复并逐数组验证 SHA-256，重新计算这 1,401 个目标对应的 2,802 条基线指标；Full 的既有 2,961 条 masked 指标保持不变。最终三个模型的同人、同 tracer、同 fold 的 target 与 mask 数组哈希全部一致。未修改任何原始缓存、真实 PET、分割或预测 NIfTI；未重新归一化或生成预测。初始结果、停止记录及逐项重算差异保留在 canonical_targets/，不混入最终统计。E1 PET 与 canonical Full PET 的逐人差异也保留为来源诊断记录。

## Mask 与指标定义

{notes}

实际出现 {len(labels)} 个非零标签（见 mask_label_coverage.csv），包括 ventricular/CSF 标签 {', '.join(str(r['label'])+' '+r['frozen_region_name'] for r in nonbrain)}。因此这里的“brain-mask”指 SynthSeg 标签并集，而非纯脑实质、仅灰质或病理 ROI。左右名称沿用冻结文件；并集计算不依赖左右标签名称。

{mask_support_text}

MAE/MSE 为 mask 内绝对/平方误差的平均，差值和累加使用 float64；PSNR = -10 log10(masked MSE)，max_val=1。SSIM 场复用仓库 generative.metrics.ssim.compute_ssim_and_cs（E1 evaluate.py 使用的同一函数），float32、Gaussian kernel=7、sigma=1.5、data_range=1。有效中心由 7×7×7 minimum filter 得到，再裁掉各方向 3 个边界体素以匹配 valid-convolution 场；只平均完整窗口在 mask 内的中心。没有把 mask 外图像置零来计算全图 SSIM。

小样本先覆盖两个 fold、两个 tracer 和三个模型：GPU masked SSIM 与 E1 CPU image_metrics 的 brain_ssim 一致至预设数值容差 2e-6；minimum-filter 中心与独立 binary erosion 完全相同；MAE/MSE 与整数组 NumPy where-mask 计算一致。通过后才运行全集。每幅预测读取前核对实际 SHA-256、shape、finite 和 [0,1]；mask NPZ 的实际哈希与冻结空间验证清单一致。

## Mean ± sample SD

{aggregate_md}

median 与第 5/95 百分位数见 [summary_metrics.csv](summary_metrics.csv)。指标按原始单位报告，不把 SSIM/MSE/MAE 隐式转换为百分数。

## 配对比较

{paired_md}

{paired_notes}

## 与 whole-volume 的区别

whole-volume 包括背景体素；本次 MAE/MSE/PSNR 仅使用 mask 内体素，SSIM 还进一步限制到完整窗口的有效中心。两个协议的绝对值不能直接当作同一指标范围比较。下表 whole-volume 差值仅从既有冻结逐人指标筛选到同一 mask 交集后重新求均值，作为既有协议的均值方向参照；其历史目标缓存含上述小量浮点数值差异，并未在本任务中改写既有 whole-volume 报告。所有 masked p 值和 CI 均在严格统一 canonical target 后重新计算，未复制任何旧 p 值。

{changes}

## 局限与验证

这些是 normalized uptake 图像指标，不是临床 SUVR，也不建立临床等效、淀粉样阳性判别或病灶特异保真。mask 包含 CSF/脑室，SSIM 排除 mask 边界附近窗口；本分析不比较其他 mask 定义，也不重建被 QC 排除病例。两折 OOF 训练集的依赖以及同一受试者的跨 tracer 相关性不能由 subject-level bootstrap 完全刻画；分层 bootstrap 保留 fold 样本量，但不估计重训练不确定性。两个预定义模型比较分别采用各含 8 项检验的 Holm 族，未做跨两个比较族的统一 16-test 校正。训练随机种子和历史临床字段填补来源的既有局限仍保留，本次不重新追查或认证。

独立重汇总全部逐人输出，核对每个 mean、sample SD、median、percentile；独立重算配对差、t 检验、dz、获益比例和 Holm 族，并重放 bootstrap；验证目标/mask 配对身份与计数、E1 小样本 SSIM 和有效中心、NumPy masked errors、表格数值与 CSV。详见 [validation.json](validation.json)、[pilot_validation.json](pilot_validation.json) 和 [statistical_validation.json](statistical_validation.json)。LaTeX 草稿需主文档提供 graphicx；本目录只提供草稿，不修改正式 supplementary。未提交或推送 Git。

论文共享草稿：[summary Markdown](supplementary_summary.md)、[summary LaTeX](supplementary_summary.tex)、[paired Markdown](supplementary_paired.md)、[paired LaTeX](supplementary_paired.tex)。这些文件不含 PTID。per_subject_metrics.csv、input_index.csv、input_manifest.json 及其他内部核查文件保留受试者/来源身份，不应直接作为公开补充材料发布。
'''
    (OUT/'REPORT.md').write_text(report)
    manifest=json.loads((OUT/'input_manifest.json').read_text())
    manifest['execution']={'status':'COMPLETE','metric_rows':len(df),'models':list(df.model.unique()),'new_exclusions':0,
        'max_e1_vs_canonical_target_difference':{t:max(r['e1_target_max_abs_difference'].get(t,0) for r in assets) for t in ['fdg','av45']},
        'actual_mask_labels':labels,'individual_actual_hashes':'per_subject_metrics.csv and subject_asset_checks.jsonl'}
    manifest['canonical_target_alignment']={'initial_disagreeing_targets':1401,'recomputed_baseline_metric_rows':2802,
        'all_final_model_target_and_mask_hashes_identical_within_pairs':True,'lossless_transport_receipt':repair,
        'initial_outputs_preserved':True,'difference_audit':'canonical_targets/exact_target_difference_audit.csv',
        'replaced_metrics_audit':'canonical_targets/replaced_metrics_audit.csv'}
    manifest['eligibility_counts']=eligibility_counts
    manifest['eligibility_details']='eligibility_and_exclusions_internal.csv'
    manifest['output_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.suffix in ['.csv','.md','.tex']}
    manifest['final_code_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in Path(__file__).parent.glob('*.py')}
    (OUT/'input_manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    validation={'status':'PASS','metric_rows':len(df),'subject_tracer_keys':2961,'summary_groups':len(summary),'paired_tests':len(paired),
        'max_summary_reaggregation_absolute_error':max(discrepancies),'pair_identity_counts_targets_masks':'PASS',
        'independent_summary_quantiles_sd':'PASS','independent_paired_ttest_dz_benefit_holm':'PASS',
        'tables_match_csv_formatted_values':'PASS','supplementary_tables_have_no_PTIDs':'PASS',
        'full_volume_direction_matches':int(direction.direction_agrees.sum()),'full_volume_direction_total':len(direction),
        'latex_compile':'Not run by this script; text/cell consistency checked',
        'limitations':'Numerical engineering checks do not establish clinical validity or retraining robustness'}
    (OUT/'validation.json').write_text(json.dumps(validation,indent=2)+'\n')
    print(conclusion)


if __name__=='__main__':main()
