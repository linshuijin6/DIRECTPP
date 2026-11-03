# G5 分类正式测试、临床基线与ROC

本次收集并核验18/18临床fit（200epochs、非pilot、test_evaluations=1、outer-test名单/标签/阈值一致），复用63项影像fit及其既存bootstrap/逐折DeLong，不重训、不重推理。三任务N=470/741/436，正类AD/EMCI+LMCI/LMCI，MCI-U未纳入。18项临床预测共3294行；影像11529行。全部81fit均完整，无按结果删折。Clinical-only是18参数线性分类器；MRI+Clinical为11244690参数模型，名称不表示Tabular-MLP生成消融。

## 临床结果（3折mean±sample SD，百分数/百分点）

| task      | condition    | ACC           | AUC           | SEN           | SPE           | balanced_ACC   |
|:----------|:-------------|:--------------|:--------------|:--------------|:--------------|:---------------|
| ad_cn     | clinical     | 100.00 ± 0.00 | 100.00 ± 0.00 | 100.00 ± 0.00 | 100.00 ± 0.00 | 100.00 ± 0.00  |
| ad_cn     | mri_clinical | 94.89 ± 3.54  | 99.17 ± 0.96  | 92.12 ± 4.20  | 96.39 ± 3.44  | 94.26 ± 3.65   |
| emci_lmci | clinical     | 99.08 ± 0.40  | 99.94 ± 0.08  | 98.67 ± 2.31  | 99.31 ± 0.60  | 98.99 ± 0.85   |
| emci_lmci | mri_clinical | 85.32 ± 13.80 | 89.60 ± 9.08  | 85.90 ± 12.00 | 85.07 ± 18.35 | 85.49 ± 12.24  |
| mci_cn    | clinical     | 94.87 ± 2.60  | 98.93 ± 0.70  | 93.59 ± 4.17  | 96.72 ± 1.14  | 95.15 ± 2.27   |
| mci_cn    | mri_clinical | 85.16 ± 8.58  | 93.07 ± 6.10  | 88.51 ± 12.11 | 80.35 ± 18.35 | 84.43 ± 9.22   |

Clinical-only在AD/CN三折观察到零错误，经验bootstrap CI退化为[100,100]，这不证明总体错误率为0或完美泛化。输入8项临床变量包含Global CDR、MMSE等与诊断相关量表；高性能不能证明Syn-PET提供独立增量临床价值，也不能据此解决诊断循环性、上游填补/来源等未核实问题（G8不处理）。MRI+Clinical也明显高于MRI/Syn双PET，但在某些任务折间SD很大。

## 已有影像配对结果（Syn双PET−参照，百分点）

| task      | reference     | AUC                   | balanced_ACC          |
|:----------|:--------------|:----------------------|:----------------------|
| ad_cn     | mri           | +6.80 [+3.39, +10.22] | +9.06 [+4.68, +13.46] |
| ad_cn     | mri_real_both | -0.55 [-2.11, +0.98]  | -1.55 [-4.35, +1.11]  |
| mci_cn    | mri           | -2.13 [-6.30, +2.10]  | -2.42 [-6.28, +1.42]  |
| mci_cn    | mri_real_both | +0.31 [-3.15, +3.81]  | -0.86 [-4.57, +3.01]  |
| emci_lmci | mri           | +3.52 [-2.42, +9.50]  | +6.91 [+2.02, +11.98] |
| emci_lmci | mri_real_both | +3.29 [-2.12, +8.54]  | +1.19 [-3.73, +6.06]  |

以上为既存5000次fold/class配对bootstrap的边际95%CI，没有同时覆盖或多重比较校正。AD/CN相对MRI的ACC/AUC/balanced ACC支持条件性改善；MCI/CN三者CI跨0且点估计为负；EMCI/LMCI仅balanced ACC的原区间[2.02,11.98]支持改善，ACC/AUC区间跨0。Syn−Real双PET三任务AUC区间均跨0，不构成等效证据。AD/CN ACC原区间上界约−.00272个百分点，接近0，不能夸大有限bootstrap的边界结果。

## 新增临床对照的AUC差值（百分点）

| task      | target       | reference    |     delta |    ci_low |   ci_high |
|:----------|:-------------|:-------------|----------:|----------:|----------:|
| ad_cn     | mri_syn_both | clinical     |  -6.17603 |  -8.82061 |  -3.9256  |
| ad_cn     | mri_syn_both | mri_clinical |  -5.34224 |  -7.87614 |  -3.17673 |
| ad_cn     | mri_clinical | mri          |  12.1443  |   9.19898 |  15.4179  |
| ad_cn     | clinical     | mri          |  12.9781  |   9.84708 |  16.491   |
| mci_cn    | mri_syn_both | clinical     | -29.4749  | -33.432   | -25.6737  |
| mci_cn    | mri_syn_both | mri_clinical | -23.6109  | -27.4845  | -19.805   |
| mci_cn    | mri_clinical | mri          |  21.4811  |  18.0947  |  24.9968  |
| mci_cn    | clinical     | mri          |  27.3451  |  23.6158  |  31.1969  |
| emci_lmci | mri_syn_both | clinical     | -33.6068  | -38.8337  | -28.1938  |
| emci_lmci | mri_syn_both | mri_clinical | -23.2724  | -28.5706  | -17.9808  |
| emci_lmci | mri_clinical | mri          |  26.7938  |  21.7408  |  31.6749  |
| emci_lmci | clinical     | mri          |  37.1282  |  31.5136  |  42.5461  |

新比较在分析前固定：Syn双PET−Clinical-only、Syn双PET−MRI+Clinical、MRI+Clinical−MRI、Clinical-only−MRI，每任务4项；各指标使用同一轮fold×class层内受试者抽样，5000次seed20261102，3折指标等权均值的配对差。12×5项CI均为边际未校正区间；不写成多重比较控制后的总体显著性。Syn双PET相对两个临床条件的AUC区间在三个任务均低于0，当前测试中没有独立增量优势。

逐折DeLong：原18项不重跑，另增加36项临床相关配对；原18和新36分开作为Holm族。p_holm不替代原始p；36项若方差退化则保留缺失并以p1计入族大小，不补造p。本数据均可计算。任何逐折p都不能被平均或直接称为三折总体DeLong显著，未提供总体DeLong p。

ROC：三任务PNG均显示MRI、Real双PET、Syn双PET、Clinical-only、MRI+Clinical，三折TPR曲线等权平均，FPR网格步长.005，2000次fold/class重采样的逐点95%带。图例AUC为原始经验fold AUC均值，不是pooled score AUC，也不是有限网格曲线积分。置信带条件于固定模型/划分，不包含重新训练随机性，不为同时置信带。图像输入资产来源与W1 Full checkpoint绑定限制见../G2/REPORT.md。
