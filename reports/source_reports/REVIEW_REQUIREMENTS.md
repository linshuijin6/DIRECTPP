# R2、R3 审稿意见与编辑修回要求

登记日期：2026-10-19。稿件：BMEF-D-26-00169。编辑决定：Major Revision；编辑回信列明修回截止日期 **2026-11-04**，未给出具体时刻或时区。

## 材料与编号

- [R2 原始 Word 报告](BMEF_Reviewer_Report_English.docx)：20 条 Major Reviewer Comments，其中第 1、2 条为肯定评价。
- [完整编辑回信](raw_review.md)：编辑要求、R2 总评及其详细报告路径、R3 的 15 条 Major Comments 和未编号的 Minor Comments。R2 的全部细节须结合 Word 阅读。
- [R2/R3 合并分析](DIReCTpp_Reviewer3_A1E585AEE7BF88E690_20261018.md)：虽以 Reviewer3 命名，但同时对照两位审稿人的意见，并给出综合建议。保留原文件和原题；分析中的优先级、风险和实验建议不视作审稿原文或已经验证的结论。
- [逐项原文登记表](review_comment_register.csv)：66 条，保留每条完整英文原文、来源位置、源文件 SHA-256、主题及相关编号。下面的中文为导航摘要，具体要求以原文为准。

使用 `R2-1`–`R2-20`、`R3-1`–`R3-15` 分别回应；R3 次要意见按原文顺序赋予项目编号 `R3-minor-01`–`R3-minor-21`，References 下七项各占一条。编辑事项为 `EDITOR-01`–`EDITOR-10`。关联编号表示主题有交集，不表示一条回复自动满足另一位审稿人的全部要求。

登记表中 `recording_status=recorded` 只确认收录，`response_status=not_assessed` 表示本次没有重新审定完成情况；不推翻或认证既有实验结果。原始审稿中的质疑仍按质疑记录。

## R2：20 条原始编号

| 编号 | 主题 | 需保留或回应的内容 |
|---|---|---|
| R2-1 | 科学创新（肯定评价） | 保留审稿人对 3D RF、VLM 与双示踪剂方法创新的肯定。 |
| R2-2 | 临床动机（肯定评价） | 保留审稿人对 PET 成本、辐射和可及性问题的肯定。 |
| R2-3 | 生成与分类交叉验证表述 | 分别说明各实验的折数，统一 Results 与 Methods。 |
| R2-4 | 横断面分期与预后主张 | EMCI/LMCI 是阶段区分；无纵向转归则收紧预后主张。 |
| R2-5 | 临床评分条件信息泄漏 | 补去认知评分的条件消融，区分 Syn-PET 与诊断元数据。 |
| R2-6 | 受试者及纵向访视隔离 | 明确同一受试者的全部访视保留在同一折。 |
| R2-7 | 外部验证仅 AV45 | OASIS-3 无 FDG 评价，限定多示踪剂外部泛化结论。 |
| R2-8 | 非显著差异与等效性 | p>0.05 不证明等效；如做 TOST 须预设临床合理界值。 |
| R2-9 | FDR 检验族与校正值 | 报告统计 family、检验数、原始 p 和调整 p/q。 |
| R2-10 | 个体 PET 一致性与校准 | 增加 ICC/CCC、Bland–Altman、区域偏差与校准。 |
| R2-11 | 分类性能的不确定性 | ACC/AUC/SEN/SPE 需 fold mean±SD 或 95% CI。 |
| R2-12 | 统计优效的直接检验 | 显著优效需 DeLong、配对 bootstrap/McNemar 等适当比较。 |
| R2-13 | 一步采样术语 | 区分精确 ODE 积分和学习得到的一步近似。 |
| R2-14 | VLM/adapter 复现细节 | 补 embedding 维度、3D PET 特征、prompt、adapter、τ 及优化细节。 |
| R2-15 | Eq.1、跨示踪剂相似性与 τ | 解释跨 tracer 相似性与差异保留的关系，补 τ 敏感性/消融或收紧结论。 |
| R2-16 | 人口学混杂 | 用匹配、调整或分层分析量化年龄、性别等条件变量的混杂。 |
| R2-17 | 基线适配与比较公平性 | 交代基线迁移方式，明确同 split、预处理、调参和预算。 |
| R2-18 | 计算效率的实测证据 | 补每卷推理时间、参数、FLOPs、显存及同条件基线比较；核对 138 GPUh。 |
| R2-19 | 数据划分、种子与版本发布 | 提供固定 split、种子、代码版本以及软件/硬件信息。 |
| R2-20 | 临床转化主张边界 | 回顾性队列不能支撑广泛筛查或临床可操作性；说明前瞻验证需求。 |

## R3：15 条 Major Comments

| 编号 | 主题 | 新增或细化的要求 | 相关 R2 编号 |
|---|---|---|---|
| R3-1 | 临床 prompt 与诊断标签循环性 | 列出真实 prompt 和量表，明确是否包含 Logical Memory II/CDR；Clinical-only、MRI+clinical 分类；tracer-only 合成/分类及 shuffle/mismatch 对照。 | R2-5、R2-16 |
| R3-2 | Table S1 分布、缺失率与插补 | 解释异常小 SD、LMCI MMSE 和 CN 体重分布；按变量及诊断组报告缺失率、统计来源与插补策略。 | R2-5、R2-16 |
| R3-3 | 缺乏纵向预后终点 | 要么提供有随访窗的 pMCI/sMCI、Cox/C-index 等真实预后分析，要么调整题目和全文 prognosis/stratification 主张。 | R2-4、R2-20 |
| R3-4 | 个体一致性、等效与 Aβ 状态 | 总体及组内区域 SUVR 的 Pearson/Lin CCC、ICC、Bland–Altman；预设界值的 TOST；真实/合成 Aβ 状态 SEN/SPE/κ，特别关注 CN Aβ+、MCI Aβ−。 | R2-8、R2-10 |
| R3-5 | SUV/SUVR、min–max 与统计量 | 说明比值在原 PET 还是 min–max 后计算、参考区及 SUV/SUVR 定义；核对图中 FDR；报告 real/synthetic 组间效应量 Cohen’s d。 | R2-9、R2-10 |
| R3-6 | split、OOF 与影像配对 | 分别说明 subject-level split、生成器未见被试的 OOF、两阶段折关系、MRI/PET 时差、florbetapir 身份、PET 预处理/扫描仪及各分类任务与 MCI-U 样本数。 | R2-3、R2-6、R2-19 |
| R3-7 | 分类统计与 MRI 基线 | 统一 ACC/SEN/SPE/AUC；fold mean±SD、95% CI、DeLong；balanced ACC；解释偏低 MRI-only 基线并核对或加强训练。 | R2-11、R2-12、R2-17 |
| R3-8 | VLM、数值编码和适配机制 | 比较 fixed adapted token 与 learned token；验证 CLIP 数值嵌入并比较 tabular MLP；说明 3D→2D 特征汇聚、τ 及优化/敏感性，统一 Fig.1/Eq.1 符号。 | R2-14、R2-15 |
| R3-9 | 七项系统性消融 | no text、tracer-only、clinical-only、frozen/adapted、VLM/tabular、一步/多步、joint/separate；澄清 3D RF 并非只差 BiomedCLIP 的单变量对照。 | R2-14、R2-15 |
| R3-10 | 同临床信息的公平基线 | 补直接相关 MRI→PET 方法和相同临床变量的强基线；说明 CycleGAN/Swin-UNet 适配、SegGuidedDiff 2D/3D 与调参方式。 | R2-17 |
| R3-11 | 图像质量指标与病例图 | brain-mask 内 SSIM/PSNR/MAE/MSE mean±SD、配对检验、per-tracer OASIS；代表/最差误差图、个体 composite SUVR 散点、ROC CI；说明选例标准，或采用中位及第10百分位病例。 | R2-10、R2-11、R2-12、R2-17 |
| R3-12 | 确定性、条件均值与不确定性 | 相同条件的回归 U-Net；讨论条件均值与不确定性，考虑 ensemble/stochastic；澄清 exact one-step 及蒸馏 teacher steps、loss、epoch140 后日程。 | R2-13、R2-18 |
| R3-13 | 外部验证范围和 OASIS prompt | OASIS 仅 AV45、CN/AD 且年龄不平衡；交代可用 prompt 字段、缺失处理与 secondary screening；说明 FDG/MCI 外部证据缺口。 | R2-7、R2-16 |
| R3-14 | 临床定位及 biomarker 讨论 | 收紧筛查、治疗选择和替代分子确认的主张；回应审稿人要求讨论的 2024 AD criteria 与 p-tau217。 | R2-4、R2-20 |
| R3-15 | 相对 DIReCT 的增量贡献 | 明确相对 IPMI 2025 DIReCT 的第二 tracer、adapter、蒸馏等差异，并用消融区分贡献。 | R2-1、R2-14、R2-17 |

## R3：21 条 Minor Comments

以下编号由本项目补充；原文没有这些编号。参考文献条目分别登记，避免将七项问题压成一个已完成状态。

| 编号 | 主题 | 原文定位 |
|---|---|---|
| R3-minor-01 | This challenge stems 语法 | raw_review.md 第 170 行 |
| R3-minor-02 | neurodegeneration 拼写 | raw_review.md 第 171 行 |
| R3-minor-03 | SUV/SUVR 与复数 | raw_review.md 第 172 行 |
| R3-minor-04 | Vθ、θ、c 的定义 | raw_review.md 第 173 行 |
| R3-minor-05 | Methods/Results 的诊断组范围 | raw_review.md 第 174 行 |
| R3-minor-06 | Temporoparietal junction 的真实 ROI | raw_review.md 第 175 行 |
| R3-minor-07 | SynthSeg 版本与引文统一 | raw_review.md 第 176 行 |
| R3-minor-08 | Refs.27/33 重复 | raw_review.md 第 178 行 |
| R3-minor-09 | Ref.35 Billot 首字母 | raw_review.md 第 179 行 |
| R3-minor-10 | Ref.28 作者与标题 | raw_review.md 第 180 行 |
| R3-minor-11 | Ref.26 作者格式 | raw_review.md 第 181 行 |
| R3-minor-12 | Ref.34 的 SPM 引文 | raw_review.md 第 182 行 |
| R3-minor-13 | Ref.36 的 FDG ROI 引文 | raw_review.md 第 183 行 |
| R3-minor-14 | Ref.25 的 DDIM 来源 | raw_review.md 第 184 行 |
| R3-minor-15 | Data Availability 的 FDG 和 subject/image IDs | raw_review.md 第 185 行 |
| R3-minor-16 | 缺失超参数与网络规模 | raw_review.md 第 186 行 |
| R3-minor-17 | Fig.1 Just Add It 图例 | raw_review.md 第 187 行 |
| R3-minor-18 | Fig.4 C–F 的 MCI 比较 | raw_review.md 第 188 行 |
| R3-minor-19 | 图轴单位与参考区 | raw_review.md 第 189 行 |
| R3-minor-20 | 投稿系统摘要裸 LaTeX | raw_review.md 第 190 行 |
| R3-minor-21 | sex/gender 统一 | raw_review.md 第 191 行 |

## 编辑要求与修回材料清单

以下均按用户提供的编辑回信登记，尚未审查材料是否备齐，也未访问投稿系统或下载外部指南。原文中的表格和指南链接完整保存在 `raw_review.md` 及登记表对应行。

| 编号 | 事项 | 要求或说明 |
|---|---|---|
| EDITOR-01 | 逐点回复/cover letter | 准备列出变更或针对每条评语进行 rebuttal 的 cover letter；分别覆盖 R2 和 R3。 |
| EDITOR-02 | 独立高亮修订稿 | 提交单独的 revised manuscript 文件，突出显示修改。 |
| EDITOR-03 | 独立高清可编辑图件 | 单独提交高清且可编辑的图；优先矢量，接受 AI/PDF/EPS/PSD/JPEG/PNG/TIFF；编辑回信附 figure guide 链接。 |
| EDITOR-04 | 全体作者签署出版许可及利益冲突表 | 所有列名作者签署 License to Publish 和 Conflict of Interest 表；表格链接保留于原文。 |
| EDITOR-05 | 复用图片授权（如适用） | 对复用或取自其他来源的图片，提供再使用和/或修改权利证明；原文附指南。 |
| EDITOR-06 | 作者变更表（如适用） | 若作者信息发生变更，所有作者须签署 Authorship Change 表。 |
| EDITOR-07 | 再次外审与修订轮次提醒 | 修订稿会再次外审；编辑表示期刊很少允许多轮修改。 |
| EDITOR-08 | 修回截止日期 | 编辑回信列明 2026-11-04；信中未注明具体时刻或时区。 |
| EDITOR-09 | 修回提交入口 | 在 Editorial Manager 以 Author 登录，从 Submission Needing Revision 找到稿件提交。 |
| EDITOR-10 | 额外决定信附件 | 回信提示还有补充文件，需通过系统 View Attachments 查看；脱敏文本中的 ******** 不是可用下载链接，本次未访问投稿系统。 |

编辑回信另含 APC 说明和数据保护通知，原文保留于 `raw_review.md`；本次不判断实际费用或将历史资助日期转换为当前报价。现有原投稿 cover letter 不是这次修回的逐点回复。

## 历史材料与当前工作范围

旧 [reviewer_evidence_matrix_1_to_20.csv](../../appendix/legacy_only/8_revision_evidence/revision_20261016/reviewer_evidence_matrix_1_to_20.csv)、`reviewer_original.txt` 及旧“20 条意见”报告只覆盖 R2，原件和哈希保持不变。其问题编号对应 `R2-*`，不得当成两位审稿人的完整矩阵，也不得将其中“已解决”自动迁移到 R3。

[作者流程说明](../author_protocol_clarification_20261017.md)仍作为修稿协议背景：生成器 2-fold OOF → 分类器 3-fold。此次将 R3-6 原文完整收录，不据合并分析重新启动已结束的历史泄漏追查。未来回复应准确解释两阶段折数及原文各子问题。

[E1 入口](../../experiments/e1_clinical_conditioning/README.md)的 Full/No-Scores 设计与 R2-5、R2-16、R3-1 相关；它不自动覆盖 Clinical-only/MRI+clinical 分类、全部 mismatch/shuffle 对照、Table S1/插补审查、其他机制消融或 R3 的全部要求。合并分析提出的新增实验作为建议记录，执行范围沿用已有授权。

本次仅补全意见及要求的记录和导航，三份评审/分析输入、冻结稿件及历史归档保持原样。后续写回复时，每条意见应绑定真实稿件位置与证据，分别记录回应状态。
