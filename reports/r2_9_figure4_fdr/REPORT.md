# R2-9：Student 检验与 Figure 4C–F 的 FDR 核验

按当前授权新复算392项 AD/CN Student 检验，分为4个各98项的 BH-FDR 族。图示40条结果中，36条与原图的显著/不显著分类一致，4条不一致。**历史绘图程序尚未完全复现；本次 p/q 是新复算值，不是已恢复的历史绘图 p/q。**

四条不一致全部来自 E 面板：AV45 左、右侧脑室（ROI 4、43）的 Real/Syn 均为 q<0.05，原图却均标 ns。C/D 的20条均显著，E/F 的其余16条均不显著。

## 本地旧结果检查

2026-11-02 检查 Git 未提交文件、`reports/` 与 `scripts/` 的文件名和脚本/报告内容；在这两个目录包含隐藏和被忽略文件，按 R2-9、FDR、Figure 4、392项与 equal_var=True 定向检索。另按相关文件名补查 `appendix/legacy_only/8_revision_evidence/`。未找到 R2-9 专用报告、脚本或392项结果，仅命中审稿要求、R2-8 来源核验和上一轮 R3-5 文件。这是上述范围内未定位，并非已证明全盘不存在；未做全仓库历史扫描。

因此执行用户授权的补算。此前 R3-5 的“未定位”结论保留为前一轮核查记录，本报告提供新生成的可追溯统计证据。

## 数据与统计口径

仅使用作者确认的两个目录：

- `source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/statistics_of_regions_av45_adjust/`
- `source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/statistics_of_regions_fdg_adjust/`

每种示踪剂恰好98个 ROI 文件；文件集合、SHA-256、有效行数及排除数均与 R2-8 `input_audit.csv` 一致。外层同名 abandon 目录未读取。复用 R2-8 的只读 `load_roi()` 边界：空/重复 PTID 或 Real/Syn 任一测量非有限则整行排除；保留原始 `Research Group` 和 PTID，只取精确 AD/CN 标签。每个 ROI 的 Real/Syn 使用同一有效受试者集合，不同 ROI 保留各自有效人数，不取跨 ROI 交集，不重新归一化、裁剪、插补或混组。

`scipy.stats.ttest_ind(AD, CN, equal_var=True, alternative='two-sided')`；方向为 AD−CN，df=N_AD+N_CN−2。采用样本量加权合并样本方差的 Student 检验；没有根据结果选择 Student/Welch，也未以方差检验决定方法。

四个独立比较族为 AV45×Real、AV45×Syn、FDG×Real、FDG×Syn，各含全部98 ROI 的原始双侧 p。每族单独做 Benjamini–Hochberg 校正，显著阈值 q<0.05；没有合并成392项一族，也没有在图示40条或各面板内重新校正。

[完整392项](all_392_student_fdr.csv) 保留检验身份、p/q、人数、均值/SD、t/df、来源哈希、组别身份集合哈希及排除明细。[图示40条](figure4_cf_40_verification.csv) 从已校正全表筛出，继承其原始 p/q 与98项 family，并加入图面标注、二元核验结论和已有 R3-5 效应量。

## 四个98项比较族

| 比较族 | 检验数 | p<0.05 | q<0.05 |
|---|---:|---:|---:|
| AV45_real_AD_vs_CN_98 | 98 | 91 | 91 |
| AV45_syn_AD_vs_CN_98 | 98 | 90 | 90 |
| FDG_real_AD_vs_CN_98 | 98 | 87 | 86 |
| FDG_syn_AD_vs_CN_98 | 98 | 87 | 87 |

## Figure 4C–F 全部40条核验

ROI ID、名称、tracer 和图面顺序沿用已核验的 [R3-5 映射](../r3_5_effect_size/REPORT.md)，并逐项与同一源文件哈希、AD/CN人数和PTID/组别集合核对。C/E=AV45，D/F=FDG；C/D 的 Real/Syn 均标 `****`，E/F 均标 `ns`。下表只核对显著/不显著二元分类；未确认原绘图程序的星号阈值，故不声称复现了四星级别。

| 面板/示踪剂 | ROI ID / 解剖名 | PET | N_AD/N_CN | 原图 | Student p | BH q（98 ROI） | q<0.05 | 与图二元一致 |
|---|---|---|---:|---|---:|---:|---|---|
| C/AV45 | 1025 ctx-lh-precuneus | real | 179/511 | **** | 8.6737349e-67 | 7.7275092e-66 | 是 | 是 |
| C/AV45 | 1025 ctx-lh-precuneus | syn | 179/511 | **** | 1.2753061e-64 | 1.2498e-63 | 是 | 是 |
| C/AV45 | 1009 ctx-lh-inferiortemporal | real | 179/511 | **** | 4.2989746e-67 | 4.6811057e-66 | 是 | 是 |
| C/AV45 | 1009 ctx-lh-inferiortemporal | syn | 179/511 | **** | 5.3204125e-64 | 4.7400038e-63 | 是 | 是 |
| C/AV45 | 1015 ctx-lh-middletemporal | real | 179/511 | **** | 6.6722438e-65 | 4.6705707e-64 | 是 | 是 |
| C/AV45 | 1015 ctx-lh-middletemporal | syn | 179/511 | **** | 2.2751972e-63 | 1.7151487e-62 | 是 | 是 |
| C/AV45 | 1030 ctx-lh-superiortemporal | real | 179/511 | **** | 1.4957444e-60 | 5.6378057e-60 | 是 | 是 |
| C/AV45 | 1030 ctx-lh-superiortemporal | syn | 179/511 | **** | 1.9966357e-58 | 8.5074042e-58 | 是 | 是 |
| C/AV45 | 1034 ctx-lh-transversetemporal | real | 179/511 | **** | 1.3635809e-56 | 2.8432112e-56 | 是 | 是 |
| C/AV45 | 1034 ctx-lh-transversetemporal | syn | 179/511 | **** | 1.5447537e-57 | 5.6068837e-57 | 是 | 是 |
| D/FDG | 1010 ctx-lh-isthmuscingulate | real | 303/371 | **** | 5.4986324e-50 | 2.6943299e-48 | 是 | 是 |
| D/FDG | 1010 ctx-lh-isthmuscingulate | syn | 303/371 | **** | 4.2791858e-45 | 2.0968011e-43 | 是 | 是 |
| D/FDG | 2010 ctx-rh-isthmuscingulate | real | 303/371 | **** | 1.1999642e-59 | 1.1759649e-57 | 是 | 是 |
| D/FDG | 2010 ctx-rh-isthmuscingulate | syn | 303/371 | **** | 1.983934e-54 | 1.9442553e-52 | 是 | 是 |
| D/FDG | 1031 ctx-lh-supramarginal | real | 303/371 | **** | 6.8456153e-10 | 2.1441856e-09 | 是 | 是 |
| D/FDG | 1031 ctx-lh-supramarginal | syn | 303/371 | **** | 3.8234525e-08 | 1.102054e-07 | 是 | 是 |
| D/FDG | 17 Left-Hippocampus | real | 302/371 | **** | 7.8346565e-16 | 4.2655352e-15 | 是 | 是 |
| D/FDG | 17 Left-Hippocampus | syn | 302/371 | **** | 2.4565186e-14 | 1.2670465e-13 | 是 | 是 |
| D/FDG | 53 Right-Hippocampus | real | 303/371 | **** | 6.0863911e-21 | 4.5882025e-20 | 是 | 是 |
| D/FDG | 53 Right-Hippocampus | syn | 303/371 | **** | 2.2050688e-19 | 1.5435481e-18 | 是 | 是 |
| E/AV45 | 4 Left-Lateral-Ventricle | real | 179/511 | ns | 0.00030318421 | 0.00033013392 | 是 | **否** |
| E/AV45 | 4 Left-Lateral-Ventricle | syn | 179/511 | ns | 0.00048502801 | 0.00052814161 | 是 | **否** |
| E/AV45 | 43 Right-Lateral-Ventricle | real | 179/511 | ns | 5.5841909e-05 | 6.1488844e-05 | 是 | **否** |
| E/AV45 | 43 Right-Lateral-Ventricle | syn | 179/511 | ns | 0.00010973102 | 0.00012082742 | 是 | **否** |
| E/AV45 | 53 Right-Hippocampus | real | 179/511 | ns | 0.93732858 | 0.93732858 | 否 | 是 |
| E/AV45 | 53 Right-Hippocampus | syn | 179/511 | ns | 0.99493243 | 0.99493243 | 否 | 是 |
| E/AV45 | 7 Left-Cerebellum-White-Matter | real | 179/511 | ns | 0.39142223 | 0.39957686 | 否 | 是 |
| E/AV45 | 7 Left-Cerebellum-White-Matter | syn | 179/511 | ns | 0.24517778 | 0.25292023 | 否 | 是 |
| E/AV45 | 17 Left-Hippocampus | real | 179/511 | ns | 0.41979483 | 0.42412262 | 否 | 是 |
| E/AV45 | 17 Left-Hippocampus | syn | 179/511 | ns | 0.1565388 | 0.16674785 | 否 | 是 |
| F/FDG | 10 Left-Thalamus | real | 303/371 | ns | 0.90075507 | 0.90075507 | 否 | 是 |
| F/FDG | 10 Left-Thalamus | syn | 303/371 | ns | 0.45241485 | 0.46670163 | 否 | 是 |
| F/FDG | 49 Right-Thalamus | real | 303/371 | ns | 0.38829047 | 0.39637985 | 否 | 是 |
| F/FDG | 49 Right-Thalamus | syn | 303/371 | ns | 0.49402968 | 0.49912277 | 否 | 是 |
| F/FDG | 1019 ctx-lh-parsorbitalis | real | 303/371 | ns | 0.095069449 | 0.10352007 | 否 | 是 |
| F/FDG | 1019 ctx-lh-parsorbitalis | syn | 303/371 | ns | 0.2389233 | 0.25063299 | 否 | 是 |
| F/FDG | 1011 ctx-lh-lateraloccipital | real | 303/371 | ns | 0.10996446 | 0.11713606 | 否 | 是 |
| F/FDG | 1011 ctx-lh-lateraloccipital | syn | 303/371 | ns | 0.20699244 | 0.22291493 | 否 | 是 |
| F/FDG | 2013 ctx-rh-lingual | real | 303/371 | ns | 0.52491277 | 0.53032424 | 否 | 是 |
| F/FDG | 2013 ctx-rh-lingual | syn | 303/371 | ns | 0.57444151 | 0.57444151 | 否 | 是 |

## 与 R3-5 效应量合看

图示20个 tracer×ROI 中，12个在 Real/Syn 中均 q<0.05。以下按 |d_syn|−|d_real| 的绝对值列出其中幅度变化最大的三项，仅为描述排序，不设置事后“较大”或临床容许阈值：

| 面板/示踪剂 | ROI ID / 解剖名 | d_real | d_syn | abs_d_difference |
|---|---|---:|---:|---:|
| D/FDG | 2010 ctx-rh-isthmuscingulate | -1.397180 | -1.320097 | -0.077082 |
| D/FDG | 1010 ctx-lh-isthmuscingulate | -1.253072 | -1.177431 | -0.075640 |
| D/FDG | 1031 ctx-lh-supramarginal | -0.484757 | -0.430784 | -0.053973 |

AV45 右海马（53）与 FDG 左丘脑（10）的效应量符号改变均发生在近零效应；其 Real/Syn 各自的 p/q 见完整核验表。显著性保持不能证明效应量精确保持，非显著也不证明等效。原稿 precisely preserved 的宽泛表述仍缺少足够支持。

## 历史流程与解释边界

**历史绘图程序尚未完全复现。**尚未确定 C–F 的精确脚本、实际输入版本、受试者子集、星号规则及原图是否实际使用 FDR。新计算与图面不一致只说明：在当前确认的 CSV 和固定 Student/98项BH口径下不能复现相应图示分类；不据此认定某个历史绘图环节的根因。同样，分类一致也不能证明历史实际做过 FDR。

这里分析 normalized uptake（任意单位），参考区归一化与 SUV/SUVR 标定仍未核实。组内分布、等方差和样本代表性没有新增检验；equal_var=True 是本次固定分析口径，不意味着等方差已得到证实。R2-8 的 Real/Syn配对 q 与这里的 AD/CN独立组 q 不混用。

## 复现与完整性

运行：`/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python reports/r2_9_figure4_fdr/analyze.py`。环境版本：NumPy 1.26.4、pandas 2.3.3、SciPy 1.15.2。仅写本目录的两个CSV和本报告；不修改原始CSV、稿件、图件、既有 R2-8/10 或 R3-5 文件，不启动训练/推理，不操作 Notion，不提交或推送 Git。

脚本对全部392个 t 值作合并SD公式核对，并对196个源文件及依赖文件做运行前后哈希检查。另以标准库csv逐源行独立重读、离均差平方和和t分布尾概率复核392项 p，以排序/反向累计最小值独立核对四族全部392项 q；核验记录见本次交付。

| 关键只读依赖 | SHA-256 |
|---|---|
| `reports/r2_8_original_roi_stats/analyze.py` | `c89bb1331338f42e84495b5a69c8f2ae8d7be7f0cc22f8119efdb4fcef38b88c` |
| `reports/r2_8_original_roi_stats/input_audit.csv` | `c92459670d2a6591ed52f314d3f4155f2674c428d7576a700ea8e40fb2b2c47c` |
| `reports/r3_5_effect_size/figure4_effect_sizes.csv` | `0de54891d2341ac84f6a0df6f177d3b07a634057a717b83842e476fc815724a2` |
| `manuscript/figures/figure_4.pdf` | `14c65aeaff839fd47feb4308dd86bccf48f057f651cb41ce4bc6b54d1d8f0c74` |
| `manuscript/BMEF_main.tex` | `28670f1cb86478acc5be8fe58ba5a5d93c6bf03c05d501489b8877d4ef5e28ba` |
