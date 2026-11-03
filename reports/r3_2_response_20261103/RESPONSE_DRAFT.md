# R3-2：建议回稿口径与英文回复

结论：建议采用“纠正临床描述表—明确模型输入—用同信息基线支撑方法贡献”的回稿主线。可以积极强调 DIReCT++ 的多示踪剂合成框架和在相同临床信息条件下的图像指标优势，但现有代码不能支持“已经排除按诊断组插补”的保证。这一条可以解释并实质补充，尚不能标记为完全解决。

本次只做相关代码和既有结果核对，以及 CPU 描述统计重建；没有启动训练，没有修改稿件或历史材料。

## 1. 已核实、推断与未解决项

**已核实：CN 体重有具体、可说明的原因。** 历史元数据中 CN 的 577 人含 31 个零体重值；包含它们时恰好得到原表的 73.20 ± 24.13 kg。将非正体重视为无效后，可用 n=546，均值和样本 SD 为 **77.35 ± 17.13 kg**。全队列共 65 个非正体重值。227 kg 的最大值仍保留，未为获得更好分布而另设上限剔除。这里纠正的是描述统计，没有声称历史模型训练时已修复这些值。

**已核实：原 Table S1 不能当作全部原始观测量表的分布。** 现存 `metadata.csv` / `filled.csv` 中，LMCI NPI-Q 全为 4、LMCI CDR 全为 0.5、EMCI GDS 全为 1、LMCI GDS 全为 3。EMCI 和 LMCI 的 MMSE 统计也能复现原表约 27.50 ± 0.50 与 24.47 ± 0.50。因此不能称小 SD 只是 SD/SEM 混淆，也不能把 LMCI MMSE 较低直接解释为该组病情更重。

**已核实：另有按预设组均值和 SD 随机生成数组、再计算 ANOVA 的历史代码。** `paper data statistics 2.ipynb` 的零起算 cell 4 包含与 Table S1 相同的参数，例如 `np.random.normal(4.00, 0.03, n_LMCI)`。这个 cell 不读取逐人评分，也不写出临床输入 CSV。它说明不能以这段代码支持原表的真实逐人统计或 P 值；它不能单独证明历史临床输入表由这段代码生成。建议换用观测记录统计，而非为原表所有数字寻找合理化解释。

**已核实：提示构建逐人读取字段，没有在该函数内按组插补。** `chu li shu ju.ipynb` cell 6 的 `generate_description()` 使用 age、sex、weight、CDR、MMSE、GDS、FAQ、NPI-Q；未将诊断标签或 Logical Memory II 写进提示。它读取已有 `filtered_subjects_filled.csv`，因此“模板不直接写诊断标签”不能推导为“临床变量不编码诊断”。上游填补规则尚未从现有来源恢复，不能写成完全未插补、全局均值插补、训练折内插补或与标签无关。

**本次重建可提供逐变量、逐组可用率。** 用现有临床导出表，按 Subject ID、Sex、Weight、Research Group、Age 精确关联；每个评分只接受唯一非空值，不填补，无效体重转缺失。本次重建与已有 `observed.csv` 逐值一致。结果见 [描述统计](observed_summary.csv) 和 [分组缺失/不可恢复率](missingness_by_group.csv)。例如：

| 字段 | CN | EMCI | LMCI | MCI | AD |
|---|---:|---:|---:|---:|---:|
| 体重无效/缺失 | 5.4% | 0.0% | 0.0% | 5.2% | 2.2% |
| MMSE 不可恢复 | 74.0% | 100.0% | 100.0% | 55.6% | 73.8% |
| NPI-Q 不可恢复 | 96.4% | 57.4% | 100.0% | 92.5% | 95.3% |

这些是**现有导出表在选定人口学锚点上的可恢复性**，不能写成 ADNI 数据库本身的缺失率，也不等于已经核实 MRI 同次访视的原始缺失率。该导出表没有检查日期/访视码。EMCI/LMCI 的原始 MMSE 在此来源不可恢复，故候选描述表中应标为不可用，不能用原有完整表数值冒充观测值。

## 2. 最有利且有依据的叙事

先感谢审稿人发现“描述统计与模型条件表未区分”的问题，给出 CN 体重的明确纠正和观测样本量。这样比泛称“ADNI 人群异质性大”更有说服力。

然后明确 DIReCT++ 的科学定位：在 MRI 和可获得临床背景条件下进行多示踪剂 PET 合成。临床条件是框架的输入设计，方法贡献主要由合成质量及公平比较支持；不能用分类准确率独自证明 MRI 恢复了独立分子病理。

已有相同临床信息的回归 U-Net 比较可作为积极补强：Epoch 165、两折 OOF、相同八项临床字段，FDG n=1,598，AV45 n=1,365，DIReCT++ 的 SSIM 配对提升分别为 **0.0208（95% CI 0.0198–0.0218）**和 **0.0240（0.0227–0.0253）**；八项图像指标比较 Holm 校正后均有统计支持。这说明相同信息条件下完整方法仍有图像指标优势，但两方法共享历史临床字段，不能据此排除其上游填补带来的共同偏倚。

固定权重去评分实验只能作为 R3-1 的补充敏感性结果：输出改变幅度较小，质量指标方向混合；不能写成已完成重新训练的去评分消融，也不能声称已证明临床评分不会驱动分类。本条回复中不建议展开，避免冲淡对描述表的直接回答。

## 3. 英文回复草稿

以下措辞对应本次已完成的代码核对、候选表和既有比较，不声称已经替换论文表格。提交时应将候选表纳入补充材料，并填入最终表号；若正文尚未同步，不要把 “prepared” 改成 “replaced”。

> We thank the reviewer for identifying this important issue. We agree that cohort descriptions should distinguish observed clinical measurements from the completed fields used for model conditioning. The original Table S1 did not make this distinction sufficiently clear, and its unusually narrow score distributions should not be interpreted as evidence of biological homogeneity within diagnostic groups.
>
> We have prepared a reconstructed descriptive table and a variable-by-group availability table using the recoverable clinical export. Each score is summarized only when a unique observed value can be linked to the selected demographic record; unavailable values are not filled for this descriptive analysis. We report the available sample size for each summary and leave unsupported cells unavailable. These availability estimates refer specifically to the recovered export and record linkage, rather than to missingness throughout ADNI. Visit-date alignment cannot be established from this export.
>
> The CN weight discrepancy has a specific explanation: the original calculation included 31 zero-valued weights among 577 CN participants. Treating nonpositive weights as invalid changes the CN summary from 73.20 ± 24.13 kg to 77.35 ± 17.13 kg (n = 546). For the queried EMCI/LMCI MMSE and LMCI NPI-Q values, the corresponding observed scores cannot be recovered from the available export; we therefore do not present the completed-field distributions as observed clinical measurements.
>
> We also checked the clinical-prompt construction. It reads individual-level age, sex, weight, CDR, MMSE, GDS, FAQ, and NPI-Q fields, without explicitly inserting diagnostic group or Logical Memory II. This function does not perform imputation; however, it consumes a previously completed table, whose upstream filling procedure has not been recovered. We therefore cannot certify that diagnosis-dependent filling was absent, and do not use the prompt template alone to dismiss the reviewer's concern.
>
> To assess the methodological contribution under matched input information, the revision experiments additionally compared DIReCT++ with a regression 3D U-Net receiving the same MRI, clinical variables, and tracer identity. In paired two-fold out-of-fold evaluation, DIReCT++ improved SSIM by 0.0208 for FDG (95% CI 0.0198–0.0218; n = 1,598) and 0.0240 for AV45 (0.0227–0.0253; n = 1,365). These results support the complete framework's image-synthesis performance under matched clinical information. They do not resolve the shared upstream data-provenance limitation or establish molecular information independent of the clinical scores. This distinction provides a more precise basis for presenting DIReCT++ as a clinically conditioned multi-tracer synthesis framework.

## 4. 随稿表注建议与提交前剩余事项

候选 Table S1 表注：

> Values are mean ± sample SD, with the available n reported for each variable and group. Only uniquely recoverable observed values from the available clinical export are summarized; no missing values were imputed for this descriptive table. Nonpositive weights were treated as invalid. Availability refers to the selected demographic-record linkage and does not establish visit-date alignment or missingness across the full ADNI database. MCI denotes the original unsplit MCI category, separate from EMCI and LMCI in this cohort.

“原表错了，所以 Fig. 5 不受影响”不是现有证据支持的结论。若要将本条正式标为解决，仍需补明历史填补策略，或以另行授权、信息来源清楚的实验建立相应下游结论。现有积极结果可支撑完整框架的条件合成表现，不能替代这一步。

本次没有改动 `manuscript/supplementary/supplementary.tex`。候选表只提供描述统计；未沿用历史随机模拟数组产生的 P 值，也未为无法观测的评分组生成组间检验。

## 5. 简要依据与复现

- 原提示：[数据处理 notebook](<../../source_archive/vscode-3003/home/data/liutuo/code/chu li shu ju.ipynb>)，零起算 cell 6。
- 历史组参数统计：[统计 notebook](<../../source_archive/vscode-3002/home/ssddata/liutuo/paper data statistics 2.ipynb>)，零起算 cell 4；只核对代码，未执行 notebook。
- 现有临床来源说明：[clinical_source_receipt.json](../e1_stage01_20261017/clinical_source_receipt.json)。本次重新读 CSV 并核对实际分布，没有把该说明中的未知状态改成否定证据。
- 同信息基线：[配对统计表](../clinical_regression_unet_e165_paired_analysis_20261028/table_main_e165.csv)及[范围说明](../clinical_regression_unet_e165_paired_analysis_20261028/REPORT.md)。本次核对汇总数值，未重新计算该既有实验的全部统计。
- 去评分敏感性：[G1 报告](../revision_evidence_night_20261102/G1_E1/REPORT.md)。与同信息基线属于不同 checkpoint/样本集合，未合并效应量或样本量。
- 重建命令：`/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python reports/r3_2_response_20261103/prepare_response_tables.py`。
- 验证：1,857 个唯一受试者，全部关联到导出记录；重建观测值与已有冻结观测表逐值一致；未修改输入、未填补评分、未进行新的 GPU 实验。
