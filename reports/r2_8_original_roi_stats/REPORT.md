# R2-8 原稿区域摄取值配对重算

## 来源与口径

仅读取原作者保留的两个 `*_adjust` 目录中的 `region_*.csv`：

- AV45: `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/statistics_of_regions_av45_adjust`；98 个文件，每文件原始 1365–1365 行，有效配对 1363–1365 人。
- FDG: `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/statistics_of_regions_fdg_adjust`；98 个文件，每文件原始 1598–1598 行，有效配对 1592–1598 人。

原始 `Research Group` 标签：`AD`, `CN`, `EMCI`, `LMCI`, `MCI`。`overall` 是所有有效配对，分组逐个保留原标签；未合并 MCI 子类。
两示踪剂队列分别分析，不跨示踪剂合并受试者。指标单位为逐图 min–max 归一化的区域摄取值（任意单位）。

## 输入审计

- AV45: 共 133770 个原始 ROI 行、133765 个有效 ROI 配对，排除 5 行；ROI 间原始受试者集合交集/并集 1365/1365。重复 ID 0 行，单侧不完整配对 0 行，空/非数值双侧测量 5 行；保留但标记区间外数值 1 行。
  相对首个 ROI 的原始受试者缺失/额外记录分别为 0/0；共同受试者的分组标签不一致 0 项。
- FDG: 共 156604 个原始 ROI 行、156590 个有效 ROI 配对，排除 14 行；ROI 间原始受试者集合交集/并集 1598/1598。重复 ID 0 行，单侧不完整配对 0 行，空/非数值双侧测量 14 行；保留但标记区间外数值 1 行。
  相对首个 ROI 的原始受试者缺失/额外记录分别为 0/0；共同受试者的分组标签不一致 0 项。

每个文件的完整路径、SHA-256、原始行数、分组人数、排除行号与受试者 ID、异常值见 `input_audit.csv`。有限的区间外数值参与计算，没有裁剪或插补。

## 方法

每个 tracer × ROI 分别在 overall 和每个原始诊断组内以同一受试者的 `d = Syn − Real` 计算。SD 使用样本标准差（ddof=1）；95% 均值差 CI 为 `mean(d) ± t(0.975,N−1) × SD(d)/√N`；双侧配对 t 检验使用 SciPy `ttest_rel`。MAE 为 `mean(|d|)`，RMSE 为 `sqrt(mean(d²))`。
Lin CCC = `2 cov(Real,Syn) / [var(Real)+var(Syn)+(mean(Real)−mean(Syn))²]`，其中 cov/var 使用 N 分母；ICC(A,1) 为双因素绝对一致性单次测量 ANOVA 公式。Bland–Altman 均值偏倚等于 `mean(d)`，95% 一致性界限为 `mean(d) ± 1.96 × SD(d)`（描述性正态近似，非置信区间）。
每个 tracer × analysis_group 的所有可计算 ROI 双侧配对 t 检验 p 值构成一个事先固定的比较族；SciPy `false_discovery_control(method='bh')` 实施 Benjamini–Hochberg FDR，显著性阈值 q < 0.05。未做 TOST，也未指定等效界值。

## 结果

| 示踪剂 | 分组 | ROI 检验数 | q < 0.05 | q ≥ 0.05 |
|---|---|---:|---:|---:|
| AV45 | overall | 98 | 0 | 98 |
| AV45 | AD | 98 | 0 | 98 |
| AV45 | CN | 98 | 0 | 98 |
| AV45 | EMCI | 98 | 0 | 98 |
| AV45 | LMCI | 98 | 0 | 98 |
| AV45 | MCI | 98 | 0 | 98 |
| FDG | overall | 98 | 0 | 98 |
| FDG | AD | 98 | 0 | 98 |
| FDG | CN | 98 | 0 | 98 |
| FDG | EMCI | 98 | 0 | 98 |
| FDG | LMCI | 98 | 0 | 98 |
| FDG | MCI | 98 | 1 | 97 |

校正后显著的完整条目：

| 示踪剂 | ROI ID | 分组 | N | 均值差 (Syn−Real) | 95% CI | p | q |
|---|---:|---|---:|---:|---|---:|---:|
| FDG | 2021 | MCI | 483 | -0.003126 | [-0.004876, -0.001376] | 0.000491189 | 0.0481365 |

以下分布均跨对应示踪剂的 98 个 **overall ROI**，不是受试者分布：

- AV45: MAE 中位数 0.0160，四分位范围 [0.0157, 0.0162]，最小–最大 [0.0150, 0.0168]；CCC 中位数 0.9745，四分位范围 [0.9549, 0.9804]，最小–最大 [0.9218, 0.9887]；ICC(A,1) 中位数 0.9745，四分位范围 [0.9550, 0.9804]，最小–最大 [0.9218, 0.9887]。
  Bland–Altman 下界 中位数 -0.0391，四分位范围 [-0.0399, -0.0385]，最小–最大 [-0.0413, -0.0366]；上界 中位数 0.0393，四分位范围 [0.0387, 0.0400]，最小–最大 [0.0356, 0.0416]。
- FDG: MAE 中位数 0.0159，四分位范围 [0.0157, 0.0162]，最小–最大 [0.0151, 0.0167]；CCC 中位数 0.9450，四分位范围 [0.9389, 0.9531]，最小–最大 [0.8991, 0.9648]；ICC(A,1) 中位数 0.9450，四分位范围 [0.9390, 0.9532]，最小–最大 [0.8991, 0.9648]。
  Bland–Altman 下界 中位数 -0.0392，四分位范围 [-0.0398, -0.0386]，最小–最大 [-0.0417, -0.0371]；上界 中位数 0.0393，四分位范围 [0.0386, 0.0399]，最小–最大 [0.0363, 0.0410]。

## 原图 Figure 4 的核验 ROI

图中标签按 `manuscript/figures/figure_4.pdf` 目视抄录；ROI ID 用现有 `/mnt/nfsdata/nfsdata/linshuijin/freesurfer/FreeSurferColorLUT.txt` 核对，并确认相应原始 CSV 存在。E 面板的 `Left-Cblm-WM` 按图注缩写与 LUT `Left-Cerebellum-White-Matter` 对应。C–F 是疾病组间图；表内 p/q 仍仅为本次 Real–Syn overall 配对重算，不能解释为 C–F 的组间检验。

| 示踪剂 | 图 4 面板 | 原图标签 / LUT 标签 | ROI ID | overall N | overall p | overall q |
|---|---|---|---:|---:|---:|---:|
| AV45 | A,C | ctx-lh-precuneus | 1025 | 1365 | 0.344 | 0.979 |
| AV45 | A | ctx-rh-precuneus | 2025 | 1365 | 0.685 | 0.979 |
| AV45 | A | ctx-lh-frontalpole | 1032 | 1365 | 0.538 | 0.979 |
| AV45 | A | ctx-rh-frontalpole | 2032 | 1364 | 0.475 | 0.979 |
| AV45 | A | ctx-lh-temporalpole | 1033 | 1365 | 0.877 | 0.979 |
| AV45 | A | ctx-rh-temporalpole | 2033 | 1365 | 0.567 | 0.979 |
| AV45 | A | ctx-lh-superiorfrontal | 1028 | 1365 | 0.51 | 0.979 |
| AV45 | A | ctx-rh-superiorfrontal | 2028 | 1365 | 0.235 | 0.979 |
| FDG | B | ctx-lh-precuneus | 1025 | 1598 | 0.943 | 0.977 |
| FDG | B | ctx-rh-precuneus | 2025 | 1598 | 0.843 | 0.977 |
| FDG | B | ctx-lh-frontalpole | 1032 | 1598 | 0.627 | 0.941 |
| FDG | B | ctx-rh-frontalpole | 2032 | 1597 | 0.516 | 0.941 |
| FDG | B | ctx-lh-temporalpole | 1033 | 1598 | 0.49 | 0.941 |
| FDG | B | ctx-rh-temporalpole | 2033 | 1598 | 0.175 | 0.941 |
| FDG | B | ctx-lh-superiorfrontal | 1028 | 1598 | 0.0657 | 0.941 |
| FDG | B | ctx-rh-superiorfrontal | 2028 | 1598 | 0.105 | 0.941 |
| AV45 | C | ctx-lh-inferiortemporal | 1009 | 1365 | 0.969 | 0.979 |
| AV45 | C | ctx-lh-middletemporal | 1015 | 1365 | 0.746 | 0.979 |
| AV45 | C | ctx-lh-superiortemporal | 1030 | 1365 | 0.016 | 0.393 |
| AV45 | C | ctx-lh-transversetemporal | 1034 | 1365 | 0.576 | 0.979 |
| FDG | D | ctx-lh-isthmuscingulate | 1010 | 1598 | 0.343 | 0.941 |
| FDG | D | ctx-rh-isthmuscingulate | 2010 | 1598 | 0.325 | 0.941 |
| FDG | D | ctx-lh-supramarginal | 1031 | 1598 | 0.0874 | 0.941 |
| FDG | D | Left-Hippocampus | 17 | 1597 | 0.452 | 0.941 |
| FDG | D | Right-Hippocampus | 53 | 1598 | 0.922 | 0.977 |
| AV45 | E | Left-Lateral-Ventricle | 4 | 1365 | 0.24 | 0.979 |
| AV45 | E | Right-Lateral-Ventricle | 43 | 1365 | 0.215 | 0.979 |
| AV45 | E | Right-Hippocampus | 53 | 1365 | 0.966 | 0.979 |
| AV45 | E | Left-Cblm-WM → Left-Cerebellum-White-Matter | 7 | 1364 | 0.445 | 0.979 |
| AV45 | E | Left-Hippocampus | 17 | 1365 | 0.964 | 0.979 |
| FDG | F | Left-Thalamus | 10 | 1598 | 0.73 | 0.977 |
| FDG | F | Right-Thalamus | 49 | 1598 | 0.967 | 0.977 |
| FDG | F | ctx-lh-parsorbitalis | 1019 | 1598 | 0.748 | 0.977 |
| FDG | F | ctx-lh-lateraloccipital | 1011 | 1598 | 0.339 | 0.941 |
| FDG | F | ctx-rh-lingual | 2013 | 1598 | 0.642 | 0.941 |

## 与原稿表述及限制

原稿称 Figure 4 A/B 的主要区域在 CN/MCI/AD 均 `p > 0.05`。本次在 A/B 对应 8 个 ROI × 3 个原始分组 × 2 示踪剂中有 3 项原始 p < 0.05、0 项 q < 0.05（各组及精确 p/q 见统计 CSV），因此该笼统断言与保存的逐人 CSV 重算不一致。注意原稿图示可能使用不同子集或处理流程；目前未证实其实际绘图输入与这些 CSV 完全相同。
具体原始 p < 0.05 条目：AV45 ROI 1028 / AD p=0.0473716, q=0.832924；AV45 ROI 2033 / CN p=0.0172593, q=0.402694；FDG ROI 1032 / CN p=0.0286966, q=0.645289。

均值偏倚与配对 t 检验只评估平均差异；MAE、CCC、ICC 和一致性界限提供个体误差与一致性的补充视角。不同 ROI 的观测相关，FDR 仅控制所声明比较族的多重检验；分组大小与缺失测量按原始文件决定。未核实参考区比值归一化，因此不得称 SUV/SUVR。**不显著（包括 p > 0.05 或 q ≥ 0.05）不证明等效、高保真或个体级精度。**

## 独立核验

`verify.py` 从原始 CSV 逐行重读并校验 196 个 SHA-256、原始/排除行数；用 NumPy/SciPy 的独立表达式复算全部 1176 行统计量，以排序及反向累计最小值独立核对全部 1176 个 BH q 值。指定输入目录检查通过，输出没有 E1 测量来源。原稿 Figure 4 的实际绘图输入身份与这些 CSV 的一致性仍未核实。
