# Stage 3B：Full vs OT 区域一致性与疾病摄取模式

结论：**Stage 3B 数据与实现核验 PASS，但结果不支持 Full clinical-text 提供独立于 Stage 3A ROI MAE 的稳定增量证据。** 患者级一致性中没有 ROI 显示经 FDR 校正的 Full 优势，唯一显著差异是 FDG 物理右侧 temporal pole 的 OT 优势。AD/CN contrast 复原呈 tracer 分化：FDG 有 3/98 ROI 支持 Full，AV45 有 34/98 ROI 支持 OT；仅 8/37 个显著项在两折中均有 CI 排除零。以下均为 `[0,1]` normalized uptake（arbitrary units），不是 SUV/SUVR。

## A. 数据身份和方法

- 唯一摄取输入为 Stage 3A `03a_regional_uptake.csv`；实测 SHA-256 `efc721a7e19ae71b1ca355a135a0312f5a198c40a5dfdaf92c4d5d9892e70907`，与 `03a_analysis_receipt.json` 完全一致。
- 固定 Epoch 165、原两折 OOF、E1 冻结 98 ROI、validity 与物理半球映射。输入共 1,856 人；FDG 1,597、AV45 1,364。有效行 289,932/290,178；无效 ROI 的 Real/Full/OT 同时缺失并同步排除；无重复 `PTID–tracer–fold–ROI`。
- 每个 tracer–ROI 对 Real vs Full 和 Real vs OT 使用同一批受试者，计算 Pearson、Lin's CCC、ICC(A,1)、signed bias（预测减 Real）、Bland–Altman 95% limits of agreement、校准斜率/截距。CCC/ICC 差定义为 `Full−OT`，正值有利于 Full。
- CCC 与 ICC 分别进行 10,000 次 fold-stratified paired subject bootstrap；各自对 196 个总体 tracer–ROI 检验统一 BH-FDR。fold1/2 行仅用于重复性检查，不另作 FDR 推断。
- AD/CN 严格使用 E1 cohort 的诊断字段和原论文 Fig. 4 的 `AD−CN` 定义。contrast error 差定义为 `|OT−Real|−|Full−Real|`，正值有利于 Full。10,000 次 bootstrap 按诊断组×fold 分层，并在同一次重采样内共同重算 Real、Full、OT；196 项统一 BH-FDR。
- 论文 Fig. 4 ROI 仅作 `paper-displayed ROI` 标记，没有加入或改变 E1 关键集。脚本未读取 PET 体积，也未执行 ROI 重提取、推理、训练、配准或分类。

## B. CCC/ICC 的 Full/OT 配对比较

| Tracer | ROI 数 | ΔCCC > 0 | ΔICC > 0 | ΔCCC 中位数 | ΔICC 中位数 | FDR 支持 Full | FDR 支持 OT |
|---|---:|---:|---:|---:|---:|---:|---:|
| FDG | 98 | 20 | 20 | −0.01205 | −0.01204 | 0 | 1 |
| AV45 | 98 | 21 | 21 | −0.01139 | −0.01139 | 0 | 0 |
| 合计 | 196 | 41 | 41 | −0.01163 | −0.01163 | 0 | 1 |

唯一经两套 FDR family 均保留的差异为 FDG ROI 1033（物理 `ctx-rh-temporalpole`，Fig. 4B）：CCC Full `0.46197`、OT `0.52088`，ΔCCC `−0.05891`，95% CI `[−0.08626, −0.03154]`，`q=0.03920`；ICC 数值与结论几乎相同。其 fold1/2 ΔCCC 分别为 `−0.05925`、`−0.04425`，两折 CI 均低于零。Pearson 仅作为描述项，没有被当成一致性证据。

因此，没有证据表明 Full 更好地保持患者之间的区域摄取差异；点估计也以 OT 方向为主。未显著项目不能解释为等效。

## C. AD/CN 区域差异复原比较

| Tracer | 可用 AD/CN 范围（每 ROI） | Δerror > 0 | FDR 支持 Full | FDR 支持 OT | Δerror 中位数 |
|---|---|---:|---:|---:|---:|
| FDG | AD 299–303；CN 368–370 | 63/98 | 3 | 0 | +0.000879 |
| AV45 | AD 178–179；CN 507–510 | 12/98 | 0 | 34 | −0.005491 |

FDG 的三个 Full 优势为：ROI 4 `Right-Lateral-Ventricle`，Δerror `+0.003296`，95% CI `[+0.001021,+0.005592]`，`q=0.02665`；ROI 17 `Right-Hippocampus`，`+0.003940` `[+0.001107,+0.006827]`，`q=0.04979`；ROI 26 `Right-Accumbens-area`，`+0.005539` `[+0.001513,+0.009547]`，`q=0.04395`。

AV45 有 34 个 FDR 显著项，方向全部为 OT；ROI ID 为 `14, 17, 26, 51, 58, 1002, 1003, 1012, 1014, 1015, 1016, 1017, 1018, 1023, 1026, 1027, 1028, 1030, 1034, 1035, 2001, 2009, 2015, 2018, 2020, 2022, 2023, 2026, 2027, 2028, 2030, 2031, 2034, 2035`。完整名称、Real/Full/OT contrast、误差、CI、原始 p 与 q 均保留在 `03b_disease_contrast.csv`，没有隐去有利或不利于 Full 的检验。

这些是“模型 contrast 与 Real contrast 的距离”比较，不是以 Real 与 Syn 各自组间显著作为恢复成功的替代证据。

## D. E1 关键 ROI 与论文 Fig. 4 ROI 对照

- E1 冻结关键集共 20 个 tracer–ROI。CCC/ICC 均无 FDR 支持的 Full 或 OT 差异。
- 关键集的疾病 contrast：FDG 仅物理右侧 hippocampus（ROI 17，Fig. 4D）支持 Full；AV45 有 8 项支持 OT：双侧 middle temporal、rostral middle frontal、superior frontal、superior temporal。其余关键 ROI 未通过统一 FDR。
- Fig. 4 展示集共 36 个 tracer–ROI。患者一致性仅 FDG 物理右侧 temporal pole 支持 OT；疾病 contrast 中 FDG 物理右侧 hippocampus 支持 Full，而 AV45 的物理右侧 hippocampus、物理右侧 middle temporal、双侧 superior frontal、物理右侧 superior temporal、物理右侧 transverse temporal 支持 OT。
- `03b_key_and_paper_roi_summary.csv` 包含关键集与论文展示集的 48 个唯一 tracer–ROI 及全部三类比较字段；`is_key_roi` 与 `is_paper_displayed_roi` 分开保存，未改变冻结定义。

## E. Fold 1/2 一致性

- 唯一显著的 CCC/ICC 项（FDG ROI 1033）两折均为 OT 方向，且两折 CI 均排除零。
- 37 个总体 FDR 显著疾病项中，35 个在两折点估计方向一致；AV45 ROI 1012 与 1016 的 fold1 略偏 Full、fold2 偏 OT，故存在方向异质性。
- 仅 8/37 个疾病项在两折各自的 95% CI 都排除零。fold 子集统计功效较低，但这一结果意味着多数总体显著项不能被描述为“每折均有明确证据”。fold 行未作额外多重校正，只用于稳健性审查。

## F. 多重比较、不确定性与完整性

- 预先分为三个 family：196 项 ΔCCC、196 项 ΔICC、196 项 disease contrast-error；各自 BH-FDR。没有按结果合并 family、筛 ROI 或改变方向定义。
- 总体 CI 来自保留两折样本量的配对/分层 bootstrap。bootstrap p 由同一重采样分布的双侧符号尾概率得到；最小可分辨双侧 p 约为 `0.0002`。
- 独立核验：4 个代表性 tracer–ROI–fold–model 组合的 CCC、ICC、bias、LoA 与 E1 `evaluate.py` 一致；两个代表性 disease contrast 直接重算一致；4 个 CSV 的 SHA-256 与收据一致。
- ROI validity 导致每 ROI 的人数略有差异，范围已在 C 节报告；未填零、未删除额外病例。物理半球名称直接继承已冻结并在 Stage 2 核验的映射，因此部分 SynthSeg 源标签的 `Left/Right` 字样与物理名称相反是已知映射结果，不是本阶段重命名。
- 所有细项应以 CSV 为准；本阶段未做统计等效检验，也不声称未显著即等效。

## G. 对 Clinical-text 实际贡献的客观判断

1. **Full 是否更好保持患者间区域差异？** 否。没有 Full 的 CCC/ICC FDR 优势；唯一有统计证据的 ROI 为 OT 优势，且两折一致。
2. **Full 是否更准确复原真实 AD/CN contrast？** 不呈统一优势。FDG 有 3 个 ROI 支持 Full，但 AV45 有 34 个 ROI 支持 OT；tracer 方向明显不一致。
3. **是否存在证据充分、方向一致的 Full 优势？** 仅 FDG 三个局部 contrast 项达到总体 FDR，其中包括预设/论文展示的物理右侧 hippocampus；但不存在跨 tracer、跨指标的 Full 优势，且疾病项只有少数在两折均有排零 CI，不能概括为稳定的总体优势。
4. **是否构成独立于 Stage 3A ROI MAE 的新增证据？** Stage 3B 增加了患者排序/数值一致性及 AD/CN contrast 保留两类证据，但结果方向总体不支持 clinical-text 的增量价值。结合 Stage 3A（FDG ROI MAE 小幅支持 OT、AV45 无差异），当前证据不能支持 Full 优于 OT。

最后，Clinical-text 中认知评分与诊断标签相关；即使某些 AD/CN contrast 更接近 Real，也不能据此宣称 Full 恢复了独立分子病理信息或建立因果贡献。

## 输出索引

- `03b_regional_agreement.csv`：1,176 行，Full/OT × overall/fold1/fold2 的全部一致性指标。
- `03b_full_ot_agreement_comparison.csv`：588 行，CCC/ICC 差、bootstrap CI/p、总体 BH-FDR。
- `03b_disease_contrast.csv`：588 行，AD/CN contrast、两模型误差、差值、CI/p、总体 BH-FDR。
- `03b_key_and_paper_roi_summary.csv`：48 行关键/论文展示 ROI 总体汇总。
- `03b_analysis_receipt.json`：输入、冻结来源和结果文件哈希及执行参数。
- `03b_regional_analysis.py`：本阶段可复现实现。
