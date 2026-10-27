# Full vs OT 医学影像区域摄取准确性验证（Stage 3A）

结论：**Stage 3A 完成，数据与统计检查 PASS；结果不支持 Full clinical-text 在区域 normalized uptake 复原上的增量价值。** OT 的总体 ROI MAE 在 FDG 和 AV45 均略小；FDG 差异有统计学证据但效应很小，AV45 无统计学证据。这里的 uptake 是 E1 预处理后的 `[0,1]` normalized uptake（arbitrary units），不是 SUV/SUVR。

`Delta = MAE_OT − MAE_Full`；正值表示 Full 更准确，负值表示 OT 更准确。

## A. 数据与评价协议

- 固定使用 Stage 2 已核验的 Epoch 165 两折 OOF：1,856 人，FDG 1,597 例、AV45 1,364 例；Full/OT 与 Real PET 按同一 PTID、tracer、fold 配对。
- Real PET、mask 来自 E1 冻结预处理 cache；Full/OT 使用已通过 MRI-anchored grid validation 的原数组索引。未重推理、重分折、翻转、配准或重采样。
- 使用冻结 98 ROI、`roi_validity.json` 和 `hemisphere_label_map.json`；区域 uptake 为同一有效 mask 内体素均值。无效 ROI 的 Real/Full/OT 同时置为缺失，不填零。
- 每名受试者先在其全部有效 ROI 上分别计算 Full、OT 对 Real 的平均绝对误差，再作配对比较；受试者等权，FDG/AV45 分开分析。
- 统计复用 E1 协议：10,000 次 fold-stratified paired bootstrap、10,000 次 paired permutation；两个主要 tracer 终点作 Holm 校正；98 ROI × 2 tracer 的逐区检验统一作 BH-FDR。
- 数值预检覆盖两折、五个诊断组的 10 人：1,960 个 subject–tracer–ROI 单元与 E1 `evaluate.py` 完全一致，独立区域均值复算差异为 0。

## B. FDG/AV45 主要 ROI MAE 对比

| Tracer | N | Full MAE | OT MAE | Delta（OT−Full） | 95% bootstrap CI | 配对 dz | 原始 p | Holm p | 判定 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| FDG | 1,597 | 0.043176 | 0.042409 | **−0.000766** | [−0.001175, −0.000364] | −0.093 | 0.000600 | **0.001200** | OT MAE 较小；证据明确、效应很小 |
| AV45 | 1,364 | 0.061623 | 0.061335 | −0.000288 | [−0.001062, 0.000490] | −0.020 | 0.453355 | 0.453355 | OT MAE 数值略小；无统计学证据 |

FDG 中 Full MAE 比 OT 高约 1.81%（以 OT MAE 为分母），但绝对差仅 `0.000766` arbitrary units，配对效应量 `|dz|=0.093`。AV45 的绝对差和效应量更小，区间覆盖零。不能把“大样本下显著”解释为临床显著或临床等效。

## C. 冻结关键 ROI 对比

以下严格限定为 `config.json` 中每 tracer 的 10 个 key ROI；未加入 isthmus cingulate 或其他论文图示区域。q 值来自全部 196 项统一 BH-FDR。

| Tracer | ROI ID | 物理 ROI 名称 | N | Delta | 95% CI | 原始 p | q(BH-196) | 数值方向 |
|---|---:|---|---:|---:|---:|---:|---:|---|
| FDG | 17 | Right-Hippocampus | 1,590 | −0.000829 | [−0.001797, 0.000137] | 0.091391 | 0.337636 | OT |
| FDG | 53 | Left-Hippocampus | 1,595 | −0.000766 | [−0.001662, 0.000154] | 0.108389 | 0.366281 | OT |
| FDG | 1008 | ctx-rh-inferiorparietal | 1,597 | −0.001151 | [−0.002240, −0.000037] | 0.046595 | 0.268608 | OT |
| FDG | 2008 | ctx-lh-inferiorparietal | 1,597 | −0.000246 | [−0.001431, 0.000922] | 0.691131 | 0.890750 | OT |
| FDG | 1015 | ctx-rh-middletemporal | 1,597 | **−0.001435** | [−0.002288, −0.000547] | 0.001800 | **0.032070** | **OT，FDR 显著** |
| FDG | 2015 | ctx-lh-middletemporal | 1,597 | −0.000164 | [−0.001088, 0.000735] | 0.711129 | 0.896086 | OT |
| FDG | 1023 | ctx-rh-posteriorcingulate | 1,597 | −0.001427 | [−0.002545, −0.000295] | 0.012199 | 0.119548 | OT |
| FDG | 2023 | ctx-lh-posteriorcingulate | 1,597 | −0.001050 | [−0.002198, 0.000116] | 0.067193 | 0.321217 | OT |
| FDG | 1030 | ctx-rh-superiortemporal | 1,597 | −0.000576 | [−0.001411, 0.000284] | 0.190981 | 0.509549 | OT |
| FDG | 2030 | ctx-lh-superiortemporal | 1,597 | +0.000095 | [−0.000756, 0.000907] | 0.820518 | 0.951312 | Full |
| AV45 | 1015 | ctx-rh-middletemporal | 1,364 | +0.000127 | [−0.001320, 0.001551] | 0.856114 | 0.963645 | Full |
| AV45 | 2015 | ctx-lh-middletemporal | 1,364 | +0.000614 | [−0.000890, 0.002106] | 0.425157 | 0.716823 | Full |
| AV45 | 1025 | ctx-rh-precuneus | 1,364 | −0.000238 | [−0.002226, 0.001761] | 0.800320 | 0.939298 | OT |
| AV45 | 2025 | ctx-lh-precuneus | 1,364 | −0.000845 | [−0.002757, 0.001089] | 0.377162 | 0.701866 | OT |
| AV45 | 1027 | ctx-rh-rostralmiddlefrontal | 1,364 | −0.000419 | [−0.002103, 0.001234] | 0.603740 | 0.850835 | OT |
| AV45 | 2027 | ctx-lh-rostralmiddlefrontal | 1,364 | −0.001006 | [−0.002688, 0.000621] | 0.233377 | 0.544546 | OT |
| AV45 | 1028 | ctx-rh-superiorfrontal | 1,364 | −0.000874 | [−0.002352, 0.000528] | 0.238976 | 0.551051 | OT |
| AV45 | 2028 | ctx-lh-superiorfrontal | 1,364 | −0.001304 | [−0.002762, 0.000142] | 0.078592 | 0.333167 | OT |
| AV45 | 1030 | ctx-rh-superiortemporal | 1,364 | −0.000074 | [−0.001344, 0.001207] | 0.905509 | 0.966020 | OT |
| AV45 | 2030 | ctx-lh-superiortemporal | 1,364 | +0.000274 | [−0.001150, 0.001673] | 0.723928 | 0.896086 | Full |

关键 ROI 中，FDG 有 9/10 个点估计偏向 OT、AV45 有 7/10 个偏向 OT。只有 FDG `ROI 1015`（物理 `ctx-rh-middletemporal`）在统一 FDR 后保留证据，方向为 **OT 优势**；没有关键 ROI 显示经 FDR 校正的 Full 优势。

在全部 196 个逐区比较中，12 个通过 `q<0.05`（FDG 11、AV45 1），方向全部为 OT；AV45 唯一显著项为非关键集的物理右侧 temporal pole。逐区完整结果见 `03a_per_roi_comparison.csv`。

## D. Full/OT 配对差与置信区间

- FDG：Delta 均值 `−0.000766`，95% CI 完全低于 0；851/1,597 人 OT 更准确，746 人 Full 更准确，无相等值。
- AV45：Delta 均值 `−0.000288`，95% CI 跨 0；701/1,364 人 OT 更准确，663 人 Full 更准确，无相等值。
- 两个 tracer 点估计都不支持 Full 优势，但只有 FDG 能排除零差异。效应均很小，尤其 AV45 接近零。

## E. Fold 1/2 一致性

| Tracer | Fold | N | Full MAE | OT MAE | Delta | 95% CI | 未校正配对 p | 方向 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| FDG | 1 | 791 | 0.043285 | 0.042589 | −0.000697 | [−0.001240, −0.000169] | 0.009999 | OT |
| FDG | 2 | 806 | 0.043068 | 0.042233 | −0.000835 | [−0.001426, −0.000232] | 0.008599 | OT |
| AV45 | 1 | 689 | 0.062484 | 0.061712 | −0.000772 | [−0.001766, 0.000207] | 0.134787 | OT |
| AV45 | 2 | 675 | 0.060745 | 0.060950 | +0.000205 | [−0.000942, 0.001389] | 0.734927 | Full |

FDG 两折方向一致，且两折区间均低于 0。AV45 两折点估计方向相反、区间均跨 0，因此 AV45 不具备可重复的方向性证据。fold 行是预设的防掩盖描述性检查，p 值未作额外多重校正，不替代总体主要终点。

## F. 无效 ROI 与数据完整性

- `03a_regional_uptake.csv` 共 290,178 行；有效 289,932 行，无效 246 行。17 名受试者涉及无效 ROI，对应 28 个 subject–tracer 记录；每个 subject–tracer 实际有效 ROI 为 74–98 个。
- 2,933/2,961 个 subject–tracer 具有完整 98 ROI；其余 28 个严格在共同有效 ROI 上计算受试者 MAE。
- 冻结关键 ROI 中仅 FDG hippocampus 受影响：ROI 17 排除 7 人，ROI 53 排除 2 人；三条件同步排除。
- 重复 `PTID+tracer+fold`：0；重复区域键：0；有效 ROI 缺失值：0；缺失 ROI 填零：0。
- 实际 fold/tracer 数：fold1 FDG 791、AV45 689；fold2 FDG 806、AV45 675，与 Stage 2 身份一致。

## G. 客观结论及未解决问题

1. **总体谁更小？** OT 在 FDG 和 AV45 的总体 ROI MAE 都略小。
2. **统计证据和效应？** FDG 支持 OT 优势（Holm `p=0.0012`），但绝对差 `0.000766`、`dz=−0.093`，效应很小；AV45 无证据排除零差异（Holm `p=0.453`）。
3. **关键 ROI？** 只有 FDG 物理右侧 middle temporal 在 196 项统一 FDR 后显示 OT 优势；没有关键 ROI 支持 Full 优势。其他方向仅为未经 FDR 支持的点估计。
4. **FDG/AV45 趋势一致吗？** 总体点估计都偏 OT，但证据强度不一致；FDG 两折一致，AV45 两折方向不一致。
5. **是否支持 clinical-text 的区域复原增量价值？** **不支持。** 本次固定协议没有观察到 Full 优于 OT；FDG 反而出现小幅 OT 优势，AV45 近似无差异。

未解决问题：这是每种条件各一套已完成 checkpoint 的单次两折 OOF 对比，不能分离 conditioning 差异与独立训练随机性的贡献；因此可以否定“本次运行已显示区域复原增量价值”，但不能据此证明 clinical text 在所有训练重复中必然无效。normalized uptake 也不能外推为 SUV/SUVR 或临床结局。

## 输出文件

- `03a_regional_uptake.csv`：逐 PTID、tracer、ROI 的 Real/Full/OT uptake、误差、validity 与物理名称。
- `03a_subject_roi_mae.csv`：2,961 个 subject–tracer 主要终点。
- `03a_primary_paired_comparison.csv`：总体与 fold 分层配对结果。
- `03a_per_roi_comparison.csv`：196 个逐区比较及 BH-FDR。
- `03a_key_roi_summary.csv`：冻结 20 个 tracer-specific key ROI 子集。
- `03a_precheck.json`、`03a_analysis_receipt.json`、`03a_roi_accuracy.py`：数值预检、完整性收据和只读分析实现。

