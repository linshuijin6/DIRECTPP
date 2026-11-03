# R3-11：冻结 OOF PET 的 SynthSeg mask 内图像质量

16 项预定义 masked 配对比较中，16 项均值方向支持 Full，16 项在各自 8 项检验族内经 Holm 校正后 p<0.05。16 项平均差值方向与相同 mask 交集上的 whole-volume 结果一致。

Clinical Regression 3D U-Net (e165)：8 项均值差中 8 项支持 Full，8 项同时有 Holm 校正后的配对统计支持；0 项显著支持比较模型，0 项未达到该校正标准。

Swin-UNETR (e200; MRI only)：8 项均值差中 8 项支持 Full，8 项同时有 Holm 校正后的配对统计支持；0 项显著支持比较模型，0 项未达到该校正标准。

优势大小随指标变化。对 Clinical U-Net 的 AV45 MSE/MAE，|Cohen's dz| 分别为 0.071 和 0.076，Full 获益比例仅约 56.4%–57.8%。这些是很小的标准化效应；统计支持不应表述为普遍个体获益或临床上的显著改善。

## 模型、样本与目标身份

本次只读取冻结预测与真实 PET。Full e165 来自 original_author_reproduction_20261020，Clinical Regression 3D U-Net e165 来自 task_a_20261027_instance1，Swin-UNETR e200 来自 20261102 已完成的四份两折 OOF 回执。未使用旧 E1 Full 的独立评价结果，也未使用历史 Figure 2 指标。Full 是本轮作者代码语义重建，并不证明原论文历史运行的身份。A 为相同 MRI、八项临床变量与 tracer 信息的框架比较；B 为 Full e165 对 MRI-only Swin-UNETR e200，输入信息和训练终点均不同，不能解释成严格等信息或同训练预算比较。

冻结两折不变。每模型 FDG N=1,597（fold1=791，fold2=806），AV45 N=1,364（fold1=689，fold2=675），共 2,961 个 subject-tracer 观察。内部清单逐项保存 PTID/tracer/fold、预测原路径与副本路径、预期及实际哈希、checkpoint 身份、mask 与 target 数组哈希。所有配对键以及同病例的 target/mask 数组哈希完全一致。冻结的 1,857 人队列中，FDG 259 人、AV45 492 人原本没有相应有效 OOF PET 目标，因此原始有效 OOF 为 FDG 1,598、AV45 1,365；随后两者均因 E1 冻结的同一个 MRI/mask QC 失败病例排除 1 例，无新增排除。全部纳入/未纳入原因逐项保存在 eligibility_and_exclusions_internal.csv；论文表不含受试者标识。

真实 PET 统一取 Full 已验证持久缓存中的原有 [0,1] 数组，所有模型用同一数组。E1 NPZ 仅提供冻结 mask；其 PET 不替代实际评价目标。Full 与 E1 的冻结原始输入清单在 5,571 项 MRI/FDG/AV45 的路径、字节数及记录哈希上相同；本次没有重新读取不可挂载的历史 raw-NIfTI。空间对应直接复用既有 MRI-anchored array-index 验证：不改 affine，不翻转、配准或重采样。Full 的 identity affine 只作为既有 header 记录，不作为空间匹配证明。

初次全队列合并发现 1,401 个 subject–tracer 的云端 PET 缓存与本地 canonical Full PET 的数组哈希不同，mask 哈希全部一致，因此汇总在统计检验前停止。逐值核查的最大绝对差为 2.38418579102e-07（[0,1] normalized-uptake 单位）。随后无损传递 canonical 数组的精确字节，在内存中恢复并逐数组验证 SHA-256，重新计算这 1,401 个目标对应的 2,802 条基线指标；Full 的既有 2,961 条 masked 指标保持不变。最终三个模型的同人、同 tracer、同 fold 的 target 与 mask 数组哈希全部一致。未修改任何原始缓存、真实 PET、分割或预测 NIfTI；未重新归一化或生成预测。初始结果、停止记录及逐项重算差异保留在 canonical_targets/，不混入最终统计。E1 PET 与 canonical Full PET 的逐人差异也保留为来源诊断记录。

## Mask 与指标定义

Values are mean ± sample SD across subjects. SSIM is unitless; PSNR is in dB; MSE and MAE use squared and unsquared [0,1] normalized-uptake units, respectively. All models use byte-identical frozen target PET arrays and identical subject-specific masks. The mask is the frozen SynthSeg nonzero-label union, including cortex, white matter, subcortical structures, cerebellum, brainstem, ventricles and CSF; it is not a pure parenchymal mask. SSIM uses the existing E1 3D Gaussian implementation (kernel 7, sigma 1.5, data range 1) and only centers whose entire 7×7×7 window lies inside the mask. The frozen mask QC exclusion removes one subject from each tracer; no new exclusions or spatial/intensity transformations were applied. Full and Clinical U-Net use epoch 165; MRI-only Swin-UNETR uses the prespecified final epoch 200. All predictions are frozen two-fold OOF outputs.

实际出现 98 个非零标签（见 mask_label_coverage.csv），包括 ventricular/CSF 标签 4 Left-Lateral-Ventricle, 5 Left-Inf-Lat-Vent, 14 3rd-Ventricle, 15 4th-Ventricle, 24 CSF, 43 Right-Lateral-Ventricle, 44 Right-Inf-Lat-Vent。因此这里的“brain-mask”指 SynthSeg 标签并集，而非纯脑实质、仅灰质或病理 ROI。左右名称沿用冻结文件；并集计算不依赖左右标签名称。

原始数组每人共有 4,915,200 个体素；mask 内体素数中位数为 1,844,503（范围 1,701,253–2,081,938），占原数组的平均比例为 37.58%。完整 7×7×7 窗口的有效 SSIM 中心中位数为 1,478,356（范围 1,182,155–1,670,577）；全体积 valid-convolution SSIM 场共有 4,411,176 个中心。

MAE/MSE 为 mask 内绝对/平方误差的平均，差值和累加使用 float64；PSNR = -10 log10(masked MSE)，max_val=1。SSIM 场复用仓库 generative.metrics.ssim.compute_ssim_and_cs（E1 evaluate.py 使用的同一函数），float32、Gaussian kernel=7、sigma=1.5、data_range=1。有效中心由 7×7×7 minimum filter 得到，再裁掉各方向 3 个边界体素以匹配 valid-convolution 场；只平均完整窗口在 mask 内的中心。没有把 mask 外图像置零来计算全图 SSIM。

小样本先覆盖两个 fold、两个 tracer 和三个模型：GPU masked SSIM 与 E1 CPU image_metrics 的 brain_ssim 一致至预设数值容差 2e-6；minimum-filter 中心与独立 binary erosion 完全相同；MAE/MSE 与整数组 NumPy where-mask 计算一致。通过后才运行全集。每幅预测读取前核对实际 SHA-256、shape、finite 和 [0,1]；mask NPZ 的实际哈希与冻结空间验证清单一致。

## Mean ± sample SD

| Model | Tracer | N | SSIM ↑ | PSNR (dB) ↑ | MSE ↓ | MAE ↓ |
| --- | --- | --- | --- | --- | --- | --- |
| DIReCT++ Full (e165) | FDG | 1597 | 0.91844 ± 0.04026 | 23.954 ± 2.271 | 0.004763 ± 0.004028 | 0.05257 ± 0.01921 |
| DIReCT++ Full (e165) | AV45 | 1364 | 0.86999 ± 0.06048 | 21.803 ± 2.602 | 0.007959 ± 0.005469 | 0.06845 ± 0.02394 |
| Clinical Regression 3D U-Net (e165) | FDG | 1597 | 0.90208 ± 0.04256 | 23.373 ± 2.019 | 0.005262 ± 0.003889 | 0.05509 ± 0.01795 |
| Clinical Regression 3D U-Net (e165) | AV45 | 1364 | 0.86098 ± 0.05868 | 21.529 ± 2.363 | 0.008237 ± 0.005320 | 0.06976 ± 0.02276 |
| Swin-UNETR (e200; MRI only) | FDG | 1597 | 0.89237 ± 0.03938 | 23.565 ± 2.013 | 0.004997 ± 0.003300 | 0.05404 ± 0.01672 |
| Swin-UNETR (e200; MRI only) | AV45 | 1364 | 0.83615 ± 0.05878 | 21.273 ± 2.429 | 0.008791 ± 0.005652 | 0.07228 ± 0.02363 |

median 与第 5/95 百分位数见 [summary_metrics.csv](summary_metrics.csv)。指标按原始单位报告，不把 SSIM/MSE/MAE 隐式转换为百分数。

## 配对比较

| Comparison | Tracer | Metric | N | Mean Δ | 95% bootstrap CI | t | Cohen dz | Full better (%) | Raw p | Holm p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A: Full − Clinical U-Net | FDG | SSIM | 1597 | 0.01636 | [0.01577, 0.01699] | 51.477 | 1.288 | 95.7 | <1e-300 | <1e-300 |
| A: Full − Clinical U-Net | FDG | PSNR | 1597 | 0.581 | [0.529, 0.634] | 21.474 | 0.537 | 72.3 | 4.55e-90 | 3.18e-89 |
| A: Full − Clinical U-Net | FDG | MSE | 1597 | -0.000499 | [-0.000572, -0.000425] | -13.116 | -0.328 | 72.3 | 2.13e-37 | 1.28e-36 |
| A: Full − Clinical U-Net | FDG | MAE | 1597 | -0.00253 | [-0.00295, -0.00210] | -11.670 | -0.292 | 66.9 | 2.96e-30 | 1.18e-29 |
| A: Full − Clinical U-Net | AV45 | SSIM | 1364 | 0.00901 | [0.00754, 0.01051] | 11.881 | 0.322 | 69.0 | 4.79e-31 | 2.39e-30 |
| A: Full − Clinical U-Net | AV45 | PSNR | 1364 | 0.273 | [0.178, 0.370] | 5.585 | 0.151 | 57.8 | 2.82e-08 | 8.45e-08 |
| A: Full − Clinical U-Net | AV45 | MSE | 1364 | -0.000278 | [-0.000488, -0.000066] | -2.609 | -0.071 | 57.8 | 0.00917 | 0.00962 |
| A: Full − Clinical U-Net | AV45 | MAE | 1364 | -0.00131 | [-0.00223, -0.00040] | -2.824 | -0.076 | 56.4 | 0.00481 | 0.00962 |
| B: Full − Swin-UNETR | FDG | SSIM | 1597 | 0.02607 | [0.02553, 0.02663] | 92.200 | 2.307 | 99.0 | <1e-300 | <1e-300 |
| B: Full − Swin-UNETR | FDG | PSNR | 1597 | 0.389 | [0.337, 0.443] | 14.239 | 0.356 | 66.8 | 2.11e-43 | 1.26e-42 |
| B: Full − Swin-UNETR | FDG | MSE | 1597 | -0.000233 | [-0.000311, -0.000151] | -5.733 | -0.143 | 66.8 | 1.18e-08 | 1.18e-08 |
| B: Full − Swin-UNETR | FDG | MAE | 1597 | -0.00148 | [-0.00191, -0.00105] | -6.681 | -0.167 | 63.3 | 3.26e-11 | 6.52e-11 |
| B: Full − Swin-UNETR | AV45 | SSIM | 1364 | 0.03383 | [0.03274, 0.03493] | 59.128 | 1.601 | 95.2 | <1e-300 | <1e-300 |
| B: Full − Swin-UNETR | AV45 | PSNR | 1364 | 0.530 | [0.451, 0.609] | 13.216 | 0.358 | 65.1 | 1.3e-37 | 6.52e-37 |
| B: Full − Swin-UNETR | AV45 | MSE | 1364 | -0.000832 | [-0.001003, -0.000658] | -9.563 | -0.259 | 65.1 | 5.15e-21 | 1.55e-20 |
| B: Full − Swin-UNETR | AV45 | MAE | 1364 | -0.00383 | [-0.00459, -0.00309] | -10.003 | -0.271 | 64.1 | 8.81e-23 | 3.52e-22 |

Δ = DIReCT++ Full minus comparator on exactly matched subject, tracer and held-out fold. Positive differences favor Full for SSIM/PSNR; negative differences favor Full for MSE/MAE. Cohen's dz uses this signed difference divided by its sample SD. Full-better proportions use strict metric-specific improvement. Two-sided paired t-tests; 95% percentile bootstrap CIs use 10,000 paired resamples, seed 42, stratified by held-out fold with original fold sizes retained. Holm correction is applied separately to comparison A and comparison B, with eight tests (2 tracers × 4 metrics) in each family; CIs are unadjusted. Uncertainty concerns the frozen OOF subjects, not retraining/seed variability. Statistical significance is not clinical equivalence. The two comparisons differ in information and endpoint: A uses matched MRI/clinical/tracer information at e165; B compares Full e165 with MRI-only Swin-UNETR e200. A displayed p <1e-300 denotes numerical underflow of the computed p value, not an exactly zero probability.

## 与 whole-volume 的区别

whole-volume 包括背景体素；本次 MAE/MSE/PSNR 仅使用 mask 内体素，SSIM 还进一步限制到完整窗口的有效中心。两个协议的绝对值不能直接当作同一指标范围比较。下表 whole-volume 差值仅从既有冻结逐人指标筛选到同一 mask 交集后重新求均值，作为既有协议的均值方向参照；其历史目标缓存含上述小量浮点数值差异，并未在本任务中改写既有 whole-volume 报告。所有 masked p 值和 CI 均在严格统一 canonical target 后重新计算，未复制任何旧 p 值。

| Comparison | Tracer | Metric | Whole-volume Δ | Masked Δ | Direction agrees |
| --- | --- | --- | --- | --- | --- |
| Full_vs_ClinicalUNet | FDG | SSIM | 0.02102 | 0.01636 | True |
| Full_vs_ClinicalUNet | FDG | PSNR | 0.614 | 0.581 | True |
| Full_vs_ClinicalUNet | FDG | MSE | -0.000253 | -0.000499 | True |
| Full_vs_ClinicalUNet | FDG | MAE | -0.00178 | -0.00253 | True |
| Full_vs_ClinicalUNet | AV45 | SSIM | 0.02424 | 0.00901 | True |
| Full_vs_ClinicalUNet | AV45 | PSNR | 0.332 | 0.273 | True |
| Full_vs_ClinicalUNet | AV45 | MSE | -0.000193 | -0.000278 | True |
| Full_vs_ClinicalUNet | AV45 | MAE | -0.00155 | -0.00131 | True |
| Full_vs_SwinUNETR | FDG | SSIM | 0.00299 | 0.02607 | True |
| Full_vs_SwinUNETR | FDG | PSNR | 0.381 | 0.389 | True |
| Full_vs_SwinUNETR | FDG | MSE | -0.000122 | -0.000233 | True |
| Full_vs_SwinUNETR | FDG | MAE | -0.00012 | -0.00148 | True |
| Full_vs_SwinUNETR | AV45 | SSIM | 0.01043 | 0.03383 | True |
| Full_vs_SwinUNETR | AV45 | PSNR | 0.463 | 0.530 | True |
| Full_vs_SwinUNETR | AV45 | MSE | -0.000344 | -0.000832 | True |
| Full_vs_SwinUNETR | AV45 | MAE | -0.00118 | -0.00383 | True |

## 局限与验证

这些是 normalized uptake 图像指标，不是临床 SUVR，也不建立临床等效、淀粉样阳性判别或病灶特异保真。mask 包含 CSF/脑室，SSIM 排除 mask 边界附近窗口；本分析不比较其他 mask 定义，也不重建被 QC 排除病例。两折 OOF 训练集的依赖以及同一受试者的跨 tracer 相关性不能由 subject-level bootstrap 完全刻画；分层 bootstrap 保留 fold 样本量，但不估计重训练不确定性。两个预定义模型比较分别采用各含 8 项检验的 Holm 族，未做跨两个比较族的统一 16-test 校正。训练随机种子和历史临床字段填补来源的既有局限仍保留，本次不重新追查或认证。

独立重汇总全部逐人输出，核对每个 mean、sample SD、median、percentile；独立重算配对差、t 检验、dz、获益比例和 Holm 族，并重放 bootstrap；验证目标/mask 配对身份与计数、E1 小样本 SSIM 和有效中心、NumPy masked errors、表格数值与 CSV。详见 [validation.json](validation.json)、[pilot_validation.json](pilot_validation.json) 和 [statistical_validation.json](statistical_validation.json)。LaTeX 草稿需主文档提供 graphicx；本目录只提供草稿，不修改正式 supplementary。未提交或推送 Git。

论文共享草稿：[summary Markdown](supplementary_summary.md)、[summary LaTeX](supplementary_summary.tex)、[paired Markdown](supplementary_paired.md)、[paired LaTeX](supplementary_paired.tex)。这些文件不含 PTID。per_subject_metrics.csv、input_index.csv、input_manifest.json 及其他内部核查文件保留受试者/来源身份，不应直接作为公开补充材料发布。

最终交付核验：4 个经目标统一重算的病例另行用本地 canonical PET、冻结原始 mask 和原预测副本做直接 NumPy MSE/MAE/PSNR 与 E1 CPU SSIM 检查，全部通过。两份 LaTeX 草稿经 pdflatex 两遍编译、逐页视觉检查通过，未出现警告或裁切；独立解析已保存的 LaTeX 表格确认汇总数值与 CSV 一致。所请求的两个模型比较、两个示踪剂及全部 16 项统计已完成，无未完成分析项。
