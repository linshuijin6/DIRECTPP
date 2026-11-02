# DIReCT++ R2-11：全部63个分类模型的最终测试结果

汇总时间：2026-11-02 09:22 CST。已获得63/63个正式200-epoch fit，覆盖3任务×7输入×3折；未筛选或排除模型、fold。

新实验不支持“三个任务均由合成双PET统一改善”的表述。相对MRI，MRI+Syn双PET的ACC/AUC/balanced ACC均值差分别为：AD/CN **+8.52/+6.80/+9.06** 个百分点；MCI/CN **−2.02/−2.13/−2.42**；EMCI/LMCI **+0.92/+3.52/+6.91**。这些仅为描述性比较，未检验显著性或等效性。

## 队列、汇总口径与结果完整性

生成阶段沿用现有2-fold OOF Syn-PET；下游分类按PTID稳定排序后重新固定subject-level Stratified 3-fold（shuffle=True，random_state=42），每个outer train内部固定分层留出15% validation。同一任务七组使用完全相同的被试和外层/内部划分。训练200轮、每2轮验证；checkpoint仅按内部验证ACC严格增加时更新；最终outer test在重载该checkpoint后评估一次。阈值0.5，AUC使用阳性类softmax概率。

| 任务 | 总人数 | 阴性 | 阳性 | 外层test各折人数 |
|---|---:|---|---|---|
| AD vs CN | 470 | CN 305 | AD 165 | 157/157/156 |
| EMCI+LMCI vs CN | 741 | CN 305 | EMCI+LMCI 436 | 247/247/247 |
| EMCI vs LMCI | 436 | EMCI 287 | LMCI 149 | 146/145/145 |

MCI-U不纳入上述任务；保留原始QC病例016_S_4952。没有因性能高低改变队列或移除fold。

全部63项test_metrics.json及test_predictions.csv可读取，元数据均为complete、200 epochs、非pilot且test_evaluations=1。逐人记录与splits.csv的外层test PTID、fold、标签一致；无重复或缺失。共11,529条预测（7×[470+741+436]），同一task-condition每名被试恰有一条OOF测试预测。用保存的概率重算63项指标，与保存指标在浮点精度内一致；未执行模型推理。

下表所有指标均为百分数；mean为3折等权算术均值，SD为sample SD（ddof=1，单位为百分点），显示2位小数。**SD不是95% CI**。各折测试集互斥，但训练集有重叠，三折SD仅描述折间波动。

## 三折最终test：mean ± sample SD

### AD vs CN

| 输入 | ACC | AUC | SEN | SPE | balanced ACC |
|---|---:|---:|---:|---:|---:|
| MRI | 79.56 ± 6.20 | 87.02 ± 5.44 | 75.15 ± 10.01 | 81.96 ± 6.90 | 78.56 ± 6.59 |
| MRI + Real FDG | 89.36 ± 0.72 | 94.28 ± 0.55 | 81.21 ± 6.39 | 93.78 ± 4.41 | 87.50 ± 1.06 |
| MRI + Syn FDG | 88.72 ± 3.31 | 94.40 ± 0.89 | 80.00 ± 12.73 | 93.45 ± 3.95 | 86.73 ± 5.21 |
| MRI + Real AV45 | 85.53 ± 2.67 | 92.54 ± 2.53 | 74.55 ± 1.82 | 91.47 ± 4.86 | 83.01 ± 1.77 |
| MRI + Syn AV45 | 84.04 ± 2.80 | 91.81 ± 3.54 | 81.21 ± 2.10 | 85.56 ± 4.90 | 83.39 ± 2.00 |
| MRI + Real双PET | 90.64 ± 2.59 | 94.38 ± 0.90 | 84.24 ± 2.78 | 94.09 ± 2.62 | 89.17 ± 2.60 |
| MRI + Syn双PET | 88.08 ± 2.06 | 93.82 ± 3.21 | 86.06 ± 5.84 | 89.18 ± 0.93 | 87.62 ± 2.90 |

### EMCI+LMCI vs CN

| 输入 | ACC | AUC | SEN | SPE | balanced ACC |
|---|---:|---:|---:|---:|---:|
| MRI | 67.48 ± 0.23 | 71.59 ± 1.80 | 79.57 ± 11.66 | 50.12 ± 17.10 | 64.85 ± 2.73 |
| MRI + Real FDG | 61.27 ± 2.70 | 64.82 ± 2.79 | 63.30 ± 3.89 | 58.35 ± 1.73 | 60.83 ± 2.48 |
| MRI + Syn FDG | 62.48 ± 3.25 | 65.77 ± 5.56 | 67.00 ± 12.26 | 56.10 ± 14.64 | 61.55 ± 3.28 |
| MRI + Real AV45 | 66.80 ± 2.10 | 72.00 ± 0.79 | 75.45 ± 8.66 | 54.43 ± 11.27 | 64.94 ± 2.42 |
| MRI + Syn AV45 | 65.99 ± 1.21 | 71.52 ± 1.85 | 73.17 ± 6.51 | 55.76 ± 11.84 | 64.47 ± 2.73 |
| MRI + Real双PET | 63.70 ± 3.54 | 69.15 ± 2.42 | 65.60 ± 9.91 | 60.97 ± 8.42 | 63.29 ± 2.81 |
| MRI + Syn双PET | 65.45 ± 1.64 | 69.46 ± 1.34 | 79.33 ± 12.80 | 45.53 ± 14.60 | 62.43 ± 0.94 |

### EMCI vs LMCI

| 输入 | ACC | AUC | SEN | SPE | balanced ACC |
|---|---:|---:|---:|---:|---:|
| MRI | 64.90 ± 3.09 | 62.81 ± 2.50 | 17.40 ± 12.64 | 89.53 ± 6.57 | 53.46 ± 4.63 |
| MRI + Real FDG | 64.21 ± 4.93 | 61.66 ± 3.35 | 36.86 ± 16.63 | 78.34 ± 15.69 | 57.60 ± 1.88 |
| MRI + Syn FDG | 65.36 ± 3.46 | 63.02 ± 1.14 | 32.84 ± 5.47 | 82.20 ± 6.97 | 57.52 ± 2.15 |
| MRI + Real AV45 | 65.82 ± 3.65 | 60.62 ± 2.37 | 29.50 ± 9.10 | 84.66 ± 1.30 | 57.08 ± 4.92 |
| MRI + Syn AV45 | 65.37 ± 5.56 | 62.12 ± 6.88 | 36.19 ± 6.89 | 80.46 ± 11.73 | 58.32 ± 2.46 |
| MRI + Real双PET | 64.90 ± 4.88 | 63.04 ± 1.25 | 41.05 ± 19.06 | 77.31 ± 13.00 | 59.18 ± 5.52 |
| MRI + Syn双PET | 65.82 ± 2.06 | 66.33 ± 0.54 | 43.03 ± 10.87 | 77.71 ± 8.82 | 60.37 ± 1.12 |

## 合并OOF预测的整体指标

以下先合并各折test预测，再对每组完整队列计算一次指标；这些是**pooled OOF点估计**，不附三折SD，不能与上表mean±SD混作同一口径。尤其pooled AUC包含不同折模型之间的分数排序，受折间分数尺度影响，并不等于三个AUC的均值。例如AD/CN MRI+Real AV45：fold均值AUC为92.54%，pooled AUC为89.44%。此处直接使用保存的概率，不重新校准或调整预测。

### AD vs CN

| 输入 | N | ACC | AUC | SEN | SPE | balanced ACC |
|---|---:|---:|---:|---:|---:|---:|
| MRI | 470 | 79.57 | 87.08 | 75.15 | 81.97 | 78.56 |
| MRI + Real FDG | 470 | 89.36 | 93.71 | 81.21 | 93.77 | 87.49 |
| MRI + Syn FDG | 470 | 88.72 | 93.84 | 80.00 | 93.44 | 86.72 |
| MRI + Real AV45 | 470 | 85.53 | 89.44 | 74.55 | 91.48 | 83.01 |
| MRI + Syn AV45 | 470 | 84.04 | 91.36 | 81.21 | 85.57 | 83.39 |
| MRI + Real双PET | 470 | 90.64 | 94.30 | 84.24 | 94.10 | 89.17 |
| MRI + Syn双PET | 470 | 88.09 | 93.93 | 86.06 | 89.18 | 87.62 |

### EMCI+LMCI vs CN

| 输入 | N | ACC | AUC | SEN | SPE | balanced ACC |
|---|---:|---:|---:|---:|---:|---:|
| MRI | 741 | 67.48 | 70.69 | 79.59 | 50.16 | 64.88 |
| MRI + Real FDG | 741 | 61.27 | 64.09 | 63.30 | 58.36 | 60.83 |
| MRI + Syn FDG | 741 | 62.48 | 65.39 | 66.97 | 56.07 | 61.52 |
| MRI + Real AV45 | 741 | 66.80 | 70.48 | 75.46 | 54.43 | 64.94 |
| MRI + Syn AV45 | 741 | 65.99 | 71.09 | 73.17 | 55.74 | 64.45 |
| MRI + Real双PET | 741 | 63.70 | 66.53 | 65.60 | 60.98 | 63.29 |
| MRI + Syn双PET | 741 | 65.45 | 68.49 | 79.36 | 45.57 | 62.47 |

### EMCI vs LMCI

| 输入 | N | ACC | AUC | SEN | SPE | balanced ACC |
|---|---:|---:|---:|---:|---:|---:|
| MRI | 436 | 64.91 | 59.56 | 17.45 | 89.55 | 53.50 |
| MRI + Real FDG | 436 | 64.22 | 61.71 | 36.91 | 78.40 | 57.65 |
| MRI + Syn FDG | 436 | 65.37 | 61.85 | 32.89 | 82.23 | 57.56 |
| MRI + Real AV45 | 436 | 65.83 | 60.69 | 29.53 | 84.67 | 57.10 |
| MRI + Syn AV45 | 436 | 65.37 | 60.23 | 36.24 | 80.49 | 58.36 |
| MRI + Real双PET | 436 | 64.91 | 59.60 | 40.94 | 77.35 | 59.15 |
| MRI + Syn双PET | 436 | 65.83 | 66.16 | 42.95 | 77.70 | 60.33 |

## Real/Syn及MRI的描述性比较

差值统一为“目标条件均值−参照条件均值”，单位为百分点；正值表示目标条件数值更高。SD三元组顺序为**ACC/AUC/balanced ACC**，均为各条件自身的fold-wise SD，不是差值的SD。A为Syn双PET对MRI；B/C/D为双PET、FDG、AV45的Syn对Real；E为其他六组对MRI。A与E重合的比较只列一次。无DeLong、McNemar、bootstrap或其他显著性检验。

### AD vs CN

| 比较：目标 − 参照 | ΔACC | ΔAUC | Δbalanced ACC | 参照SD三元组 | 目标SD三元组 |
|---|---:|---:|---:|---|---|
| E：MRI + Real FDG − MRI | +9.80 | +7.26 | +8.94 | 6.20/5.44/6.59 | 0.72/0.55/1.06 |
| E：MRI + Syn FDG − MRI | +9.15 | +7.38 | +8.17 | 6.20/5.44/6.59 | 3.31/0.89/5.21 |
| E：MRI + Real AV45 − MRI | +5.97 | +5.52 | +4.45 | 6.20/5.44/6.59 | 2.67/2.53/1.77 |
| E：MRI + Syn AV45 − MRI | +4.47 | +4.78 | +4.83 | 6.20/5.44/6.59 | 2.80/3.54/2.00 |
| E：MRI + Real双PET − MRI | +11.07 | +7.35 | +10.61 | 6.20/5.44/6.59 | 2.59/0.90/2.60 |
| A/E：MRI + Syn双PET − MRI | +8.52 | +6.80 | +9.06 | 6.20/5.44/6.59 | 2.06/3.21/2.90 |
| B：MRI + Syn双PET − MRI + Real双PET | -2.55 | -0.55 | -1.55 | 2.59/0.90/2.60 | 2.06/3.21/2.90 |
| C：MRI + Syn FDG − MRI + Real FDG | -0.65 | +0.13 | -0.77 | 0.72/0.55/1.06 | 3.31/0.89/5.21 |
| D：MRI + Syn AV45 − MRI + Real AV45 | -1.49 | -0.73 | +0.38 | 2.67/2.53/1.77 | 2.80/3.54/2.00 |

### EMCI+LMCI vs CN

| 比较：目标 − 参照 | ΔACC | ΔAUC | Δbalanced ACC | 参照SD三元组 | 目标SD三元组 |
|---|---:|---:|---:|---|---|
| E：MRI + Real FDG − MRI | -6.21 | -6.77 | -4.02 | 0.23/1.80/2.73 | 2.70/2.79/2.48 |
| E：MRI + Syn FDG − MRI | -4.99 | -5.82 | -3.30 | 0.23/1.80/2.73 | 3.25/5.56/3.28 |
| E：MRI + Real AV45 − MRI | -0.67 | +0.41 | +0.09 | 0.23/1.80/2.73 | 2.10/0.79/2.42 |
| E：MRI + Syn AV45 − MRI | -1.48 | -0.07 | -0.38 | 0.23/1.80/2.73 | 1.21/1.85/2.73 |
| E：MRI + Real双PET − MRI | -3.78 | -2.44 | -1.56 | 0.23/1.80/2.73 | 3.54/2.42/2.81 |
| A/E：MRI + Syn双PET − MRI | -2.02 | -2.13 | -2.42 | 0.23/1.80/2.73 | 1.64/1.34/0.94 |
| B：MRI + Syn双PET − MRI + Real双PET | +1.75 | +0.31 | -0.86 | 3.54/2.42/2.81 | 1.64/1.34/0.94 |
| C：MRI + Syn FDG − MRI + Real FDG | +1.21 | +0.95 | +0.72 | 2.70/2.79/2.48 | 3.25/5.56/3.28 |
| D：MRI + Syn AV45 − MRI + Real AV45 | -0.81 | -0.48 | -0.47 | 2.10/0.79/2.42 | 1.21/1.85/2.73 |

### EMCI vs LMCI

| 比较：目标 − 参照 | ΔACC | ΔAUC | Δbalanced ACC | 参照SD三元组 | 目标SD三元组 |
|---|---:|---:|---:|---|---|
| E：MRI + Real FDG − MRI | -0.69 | -1.15 | +4.13 | 3.09/2.50/4.63 | 4.93/3.35/1.88 |
| E：MRI + Syn FDG − MRI | +0.46 | +0.21 | +4.06 | 3.09/2.50/4.63 | 3.46/1.14/2.15 |
| E：MRI + Real AV45 − MRI | +0.91 | -2.18 | +3.62 | 3.09/2.50/4.63 | 3.65/2.37/4.92 |
| E：MRI + Syn AV45 − MRI | +0.47 | -0.68 | +4.86 | 3.09/2.50/4.63 | 5.56/6.88/2.46 |
| E：MRI + Real双PET − MRI | +0.00 | +0.23 | +5.72 | 3.09/2.50/4.63 | 4.88/1.25/5.52 |
| A/E：MRI + Syn双PET − MRI | +0.92 | +3.52 | +6.91 | 3.09/2.50/4.63 | 2.06/0.54/1.12 |
| B：MRI + Syn双PET − MRI + Real双PET | +0.92 | +3.29 | +1.19 | 4.88/1.25/5.52 | 2.06/0.54/1.12 |
| C：MRI + Syn FDG − MRI + Real FDG | +1.15 | +1.36 | -0.07 | 4.93/3.35/1.88 | 3.46/1.14/2.15 |
| D：MRI + Syn AV45 − MRI + Real AV45 | -0.44 | +1.50 | +1.24 | 3.65/2.37/4.92 | 5.56/6.88/2.46 |

AD/CN：Syn双PET相对MRI改善ACC、AUC和balanced ACC；相对Real双PET分别低2.55、0.55和1.55个百分点。Syn/Real FDG的AUC差仅+0.13个百分点，而ACC与balanced ACC略低；AV45的Syn/Real差也随指标变化，不能描述为一致优效。

MCI/CN：Syn双PET未超过MRI，ACC、AUC和balanced ACC均低于MRI；其SEN为79.33%±12.80，SPE仅45.53%±14.60。相对Real双PET，Syn的ACC/AUC高1.75/0.31个百分点，但balanced ACC低0.86个百分点。FDG的Syn比Real三项均略高，AV45则三项均略低。点估计差较小不能证明等效。

EMCI/LMCI：Syn双PET相对MRI的balanced ACC提高6.91个百分点，但其LMCI敏感度仍为43.03%±10.87；MRI仅17.40%±12.64。此任务EMCI 287人、LMCI 149人，多数类恒预测的参考ACC为65.83%，接近Syn双PET的65.82%；仅凭ACC不能宣称分期准确。Syn双PET相对Real双PET的AUC高3.29个百分点，方向与AD/CN的−0.55不同，三个任务不一致。

“接近”在此最多是对个别指标点估计差距的描述，没有预设等效界值，也没有等效或非劣效检验。

## 与原稿Figure 5的描述性对照

新实验使用重新固定的三折划分、独立outer test评价与内部validation选择checkpoint；原稿历史点估计与本次fold mean±SD不是同一统计口径，原分类折名单未恢复。以下对照不能归因于单一训练因素，也不要求重现旧值。原稿Figure 5共有11种输入，本次仅对应其中7种MRI及MRI+PET输入，不纳入四个PET-only条件。

正文可精确引用的历史点估计与新结果对照如下（新值为三折均值；Δ=新−旧，百分点）：

| 任务/输入/指标 | 原稿正文 | 本次均值 | Δ |
|---|---:|---:|---:|
| AD vs CN / MRI / ACC | 87.69 | 79.56 | -8.13 |
| AD vs CN / MRI / AUC | 91.88 | 87.02 | -4.86 |
| AD vs CN / MRI + Syn双PET / ACC | 93.47 | 88.08 | -5.39 |
| AD vs CN / MRI + Syn双PET / AUC | 95.65 | 93.82 | -1.83 |
| AD vs CN / MRI + Real双PET / ACC | 94.27 | 90.64 | -3.63 |
| AD vs CN / MRI + Real双PET / AUC | 96.10 | 94.38 | -1.72 |
| EMCI+LMCI vs CN / MRI / SEN | 71.43 | 79.57 | +8.14 |
| EMCI+LMCI vs CN / MRI + Syn双PET / SEN | 78.17 | 79.33 | +1.16 |
| EMCI vs LMCI / MRI / ACC | 77.65 | 64.90 | -12.75 |
| EMCI vs LMCI / MRI + Syn双PET / ACC | 81.96 | 65.82 | -16.14 |

R3-7指出原图MCI/CN的MRI-only ACC约51%；本次67.48%±0.23，较这一读图近似值高约16.5个百分点，AUC为71.59%±1.80。MRI基线改善后，Syn双PET未能超过MRI，因此原稿关于MCI任务附加获益的结论需要重新表述。

对照当前原稿[figure_5.pdf](../../../manuscript/figures/figure_5.pdf)柱形方向，七组的主要变化如下。仅报告明显方向，不把读图近似值当作精确历史数据；↑/↓表示本次三折均值比原图柱高/低，未检验显著性。balanced ACC原图未报告，无直接旧值可比。

| 对应输入 | AD/CN | MCI/CN | EMCI/LMCI |
|---|---|---|---|
| MRI | ACC/AUC/SEN↓；SPE↓ | ACC/AUC↑；SEN↑；SPE↓ | ACC/AUC/SEN↓；SPE↑ |
| MRI + Real FDG | ACC/AUC/SEN↓；SPE↑ | ACC/AUC↓；SEN↑；SPE↓ | ACC/AUC/SEN↓；SPE↑ |
| MRI + Syn FDG | ACC/AUC/SEN↓；SPE↑ | ACC/AUC↓；SEN↑；SPE↓ | ACC/AUC/SEN↓；SPE↑ |
| MRI + Real AV45 | ACC/AUC/SEN↓；SPE↑ | ACC/AUC↓；SEN↓；SPE↓ | ACC/AUC/SEN↓；SPE↑ |
| MRI + Syn AV45 | ACC/AUC/SEN↓；SPE↑ | ACC/AUC↓；SEN↑；SPE↓ | ACC/AUC/SEN↓；SPE↑ |
| MRI + Real双PET | ACC/AUC/SEN↓；SPE↑ | ACC/AUC↓；SEN↓；SPE↓ | ACC/AUC/SEN↓；SPE↑ |
| MRI + Syn双PET | ACC/AUC/SEN↓；SPE↑ | ACC/AUC↓；SEN↑；SPE↓ | ACC/AUC/SEN↓；SPE↑ |

原图EMCI/LMCI的SEN/SPE阳性类方向在这项描述性读图中未独立确认，本次明确以LMCI为阳性；因此上表SEN/SPE仅作指标栏位的数值方向对照，不能直接解释为同一诊断类别识别能力的变化。新任务为436人（287/149），也不同于R3-7引用的历史291/152；应避免将所有变化解释成同一队列上的性能退化。

AD/CN的新MRI、Real双PET、Syn双PET的ACC/AUC均低于原稿正文值；EMCI/LMCI两组ACC也低于原稿正文值。MRI-only并非在三个任务中都改善。Syn双PET相对MRI：AD/CN改善、MCI/CN下降、EMCI/LMCI的ACC小幅提高且balanced ACC提高；不能沿用“所有任务显著提升”的原结论。

## 对审稿意见的支持范围

| 意见 | 本次可提供 | 尚未完成/不能宣称 |
|---|---|---|
| R2-11 | 全部21组ACC/AUC/SEN/SPE及balanced ACC的三折mean±sample SD；63折原始指标与逐人预测 | 未计算95% CI；SD不能标成CI。原意见要求mean±SD或CI，本次完成前一口径的数据准备 |
| R2-12 | 同被试、同折的逐人配对预测及Real/Syn/MRI描述性差值，供后续直接检验 | 尚无DeLong、McNemar或paired bootstrap，不能支持“显著优于”、等效或非劣效表述 |
| R3-7 | 统一四项主要指标，补balanced ACC、折间SD；重新训练的MRI-only基线与所有组同协议；MCI MRI基线高于原图约51% | 95% CI和DeLong尚未做；不能声称已证明最优/足够强MRI基线，或用三个fold的SD替代CI；EMCI/LMCI低敏感度仍需如实呈现 |

Clinical-only与MRI+Clinical尚未完成，未纳入63模型及本报告统计。相应基线结果仍待补充；本次未启动训练或提出新的实验调度。

## 文件、单位及计算依据

- [fold_metrics.csv](fold_metrics.csv)：63行。保留各fold保存的最终test指标，`*_pct`为原始比例×100（保留数值精度），并记录测试人数、类别数、实例和三个源文件路径。
- [summary_metrics.csv](summary_metrics.csv)：21行。`*_mean_pct`为三折等权均值，`*_sd_pp`为sample SD；`*_mean_sd`为2位小数显示文本；`pooled_*_pct`为完整OOF点估计。数值列以百分数/百分点保留2位小数，差值在未舍入数值上计算。
- [oof_predictions.csv](oof_predictions.csv)：11,529行，保留task、condition、fold、PTID、y_true、p_positive、y_pred。`p_positive`保留原始0–1概率，标签为0/1；这是预测数据，不作百分数转换。
- 四个源目录为`/root/autodl-tmp/DIRECTPP_classification_3fold/20261031_instance{3,4,5,6}/`；本次按既有SSH端口44919/22299/15055/51712仅仅读取test_metrics.json、test_predictions.csv及summary身份/完成字段，未复制checkpoint、NIfTI或缓存。各实例63项分别为15/16/16/16。
- 固定名单：[splits.csv](../splits.csv)。实现参考：[run.py](../../../experiments/classification_3fold/run.py)。历史对照：[原稿正文](../../../manuscript/BMEF_main.tex)分类Results及Figure 5；[审稿登记](../../source_reports/review_comment_register.csv)R2-11/R2-12/R3-7；[R3原文](../../source_reports/raw_review.md)第7项。
- ACC=(TP+TN)/N，SEN=TP/(TP+FN)，SPE=TN/(TN+FP)，balanced ACC=(SEN+SPE)/2；AUC按连续`p_positive`的ROC排序计算。mean=三折指标之和/3；SD=sqrt(sum[(fold−mean)^2]/(3−1))。pooled先合并三折预测再按相同公式计算。未进行显著性检验、重新选checkpoint、训练或推理。
