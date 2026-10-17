# Revision Evidence Report — BMEF-D-26-00169

2026-10-16；范围：既有审计指向资产及必要上游证据；结论：**可修订部分统计与事实声明，分类可靠性和独立泛化尚未解决。** 原始模型、图表、论文均保留；本轮无生成器训练、无分类训练、无 GPU 推理。

## 核心差异与推荐

原审计的“500 人训练”“fixed_split 80 人可作干净测试”“掩膜含脑桥 174”“419 人 OASIS-3 PET 已恢复”“165 轮完整日志”均不能作为已证实事实沿用。其 #8–19 的意见对应也有错位，本报告以原始英文 Reviewer Report #1–20 为准。

推荐先采用本轮从真实资产重算的 normalized uptake 统计和可恢复的人口学结果；删去等效、显著优于、纵向预后和临床替代的越界结论。**旧 Figure 5 的验证性结论需要撤回或用新独立实验替换；当前不应启动分类训练。**

## 1. 最终生成器暴露集合与分类队列

- 500 train / 39 val 的 JSON 路径属于早期 ADNI2；两组不相交，全部出现在 1857 人元数据里。
- fixed_split 的 720 train / 80 val 中，分别只有 430 / 52 人在当前队列；早期 500 人仅 45 人落在 fixed train、2 人落在 fixed val。故 fixed_split 不是该 500 人集合的 90/10 扩展，也没有证据绑定最终 checkpoint，不能把 80 人认证为干净留出。
- 最终 notebook `mri2pet _two trace_new-final.ipynb` Cell 2–4 输出为 **1856 train / 1 val**，训练日志也反复显示 `1856/1856`。按排序 ID、seed=42、test_size=1 重建得到相同首训练 ID `021_S_4924` 与验证 ID `011_S_4105`。用户随后恢复了 `train_data_1856_first_part_165.json` 和 `val_data_1_first_part_165.json`：逐 ID 与重建完全一致，1857 条 Description 全部与元数据一致，两集合无交集、并集恰为1857人。上游另一个现存 JSON 是1857/0，不能混用文件版本。
- `first_part_165.pth` 仅含 model/optimizer/epoch：epoch=164（零起算），Adam step=306190；`150Best` 为 epoch=149、step=278356。步数支持大队列长期训练，不支持只凭 500 人 JSON 认定训练人数；checkpoint 未携带 manifest，不能认证完整训练历程。

**按用户恢复并指定为最终165对应的名单，最终划分已核实为1856 train / 1 val。** 训练标签为 CN 576、AD 317、EMCI 291、LMCI 152、MCI 520；名单外仅 **011_S_4105（CN，1人）**。因此原审计中“1857−500=1357 人未见”不成立。该1人曾用于生成器验证，训练和验证都未触及的人数为 **0**；三个二分类任务分别只有 CN 1、CN 1、0 人，均无法评估。Checkpoint 本身未内嵌 manifest；这里以用户恢复的对应名单、日志及身份复核建立关联，不声称存在原生加密绑定。Raw/adapted guidance 的运行身份仍未解决。

逐人交集及文件路径见 [subject_membership_and_assets_enriched.csv](subject_membership_and_assets_enriched.csv)，最终名单复核和哈希见 [final165_split_receipt.json](final165_split_receipt.json)。早先的 [final_split_reconstruction.json](final_split_reconstruction.json) 保留为名单恢复前的推断记录，不作为最终队列状态。

全队列 CN/AD/EMCI/LMCI/MCI = 577/317/291/152/520；现存双 Syn/Real PET+MRI 交集为 1106 人，分布 305/165/287/149/200。按已恢复分类代码的任务定义，当前可用 AD/CN **470**、EMCI+LMCI/CN **741**、EMCI/LMCI **436**；这是现有资产的可用人数，不冒充旧 Figure 5 每一行的已核实历史人数。除该1名CN外均在最终训练名单。排除早期 539 人所得 226/338/195 人只是错误前提下的候选上限，不能拿来启动“独立”实验。恢复的 MCI 分类代码不含另外520名未细分 MCI，论文必须澄清实际定义。

## 2. 区域统计：修正 Syn 列后重新计算

训练/保存流程使用 PET 的 NormalizeIntensity + ScaleIntensity，Syn 输出还 clamp 到 [0,1]。现有 ROI 提取只取 mask 内均值，没有小脑/脑桥除法。六例原卷核验表明：保存 MRI 与 replay 需共同三轴反转才能对齐；用 MRI 独立确认此方向后，588 个 Real ROI 与 CSV 一致（最大差约 4.6×10⁻⁸），**588 个 Syn ROI 均不一致**（绝对差超过 10⁻⁶）。这证实输入版本不一致，不能据此判断差异产生原因。

因此保留原 CSV 直接统计为诊断结果，重新对全部 **2963 个 Syn 卷（AV45 1365、FDG 1598）及 1857 个对应 mask** 提取 98 区均值；Real 使用经六例源卷核验的原 CSV 列。未全量 replay Real。所有最终区域结果位于 [image_derived/](image_derived/)，不引用本目录根部诊断统计。

| Tracer | n/ROI | MAE 中位数 | ICC(A,1) 中位数（范围） | CCC 中位数 | p<0.05 / 全196项BH q<0.05 |
|---|---:|---:|---|---:|---|
| AV45 | 1363–1365 | 0.01257 | 0.9847（0.9150–0.9933） | 0.9847 | 91/98；91/98 |
| FDG | 1592–1598 | 0.01210 | 0.9707（0.8990–0.9858） | 0.9706 | 93/98；93/98 |

AV45：98 区均值偏差范围 -0.00969 至 0.01264；MAE 范围 0.00572–0.01990。完整每区 bias CI、ICC/CCC CI、LoA 和校准参数见总表。

FDG：98 区均值偏差范围 -0.01832 至 0.01472；MAE 范围 0.00743–0.02219。完整每区 bias CI、ICC/CCC CI、LoA 和校准参数见总表。

报告单位为 **normalized uptake，arbitrary units**。这些是固定生成器下的回顾性一致性结果，不能用于证明未见受试者的泛化，更不证明临床可互换。总体 p>0.05 不等于等效；不挑选不显著区域。原稿“所有主要区域无差异”“精确保留病理”“已证实生物标志物等效”等措辞需根据实际结果撤回或收紧。

SUV/SUVR：保存强度不能单凭数值范围认定物理尺度；现有掩膜中的脑干 label 16 不等于脑桥 174。**不计算/声称已恢复定量 SUVR，不实施无依据 5%/10% 边界的 TOST。** 参考区比值只有在原尺度、变换及有效参考区闭环后才能另行命名与解释。

FDR family 为总体配对 196 项、五诊断分层 980 项、Real/Syn 的 AD−CN Welch 392 项；同时保存原始 p 和 BH q。ICC/CCC、bias 95% CI、Bland–Altman LoA/近似 CI、校准及 proportional-bias 结果齐全。另已执行年龄/性别 HC3 调整：Syn−Real 的 AD−CN contrast 在 AV45 49/98、FDG 43/98 区仍显著（各 outcome 全 196 项 BH），不能用“Real 和 Syn 均显著”证明精确保留组间效应。加入有效体重后分别为 42/98、41/98。调整不能排除临床 prompt 捷径。重提取发现 AV45 5、FDG 14 个 subject×ROI 缺失，均保留 NA、逐区报告 n，未填零。方法与限制见 [METHODS_AND_PROVENANCE.md](METHODS_AND_PROVENANCE.md)。

## 3. Table S1：只用原始可观察记录

从上游 63812 行临床/影像导出中，按 SID+Sex+Age+Weight+Research Group 精确锚定 1857 人；去除重复影像行，不跨访视借值。原字段可核对，但导出缺少 EXAMDATE/VISCODE，临床与影像日期配对仍无法认证。

真实五组年龄 ANOVA **p=6.168899×10⁻⁷**，sex χ²(4)=34.863928，**p=4.954112×10⁻⁷**。65 个零体重按无效值设缺失后，有效 n=1792，体重 ANOVA **p=3.269258×10⁻⁴**（Kruskal–Wallis p=6.269891×10⁻⁵）；体重原始单位待字典确认，暂不强称 kg。原 filled 表含零值的体重检验不是推荐表格。

MMSE/GDS/CDR/FAQ/NPI-Q 在选定记录上分别仅 464/462/464/211/199 个观测；EMCI、LMCI 多项没有观测或仅一例。**五组认知评分 P 值不可恢复，填 NA，并报告每组实际 n，不以填补/模拟数据代替。** 旧随机数 P 值及 filled 表上“重新计算”的认知 P 值均不采用。

已给出 [候选 Table S1 LaTeX](table_s1_observed_candidate.tex)、[真实连续变量统计](table_s1_observed_continuous.csv)、[逐记录来源](clinical_observed_provenance.csv)。这些候选表不会覆盖原稿。

## 4. 最小分类方案、prompt 敏感性与模型事实

完整方案和预算见 [CLASSIFICATION_AND_SENSITIVITY_PLAN.md](CLASSIFICATION_AND_SENSITIVITY_PLAN.md)。先决条件是可认证的独立 subject 队列；当前没有合格的 ADNI 二分类队列。条件成立后，先考虑同队列 Real/Syn ROI 的 CPU logistic 对照（约 ≤1 CPU 小时的规划估计）；若需 MRI/DenseNet 结论，先 AD/CN 三条件×三折 9 fits，再决定其他任务，完整三任务为 27 fits。每折重建 loader、inner validation 选择、outer OOF 概率和 subject CI，绝不跨 epoch 平均性能。

Figure 5 不能只替换 Syn 柱或给旧均值补 CI：继续展示原 11 模态需换全部 33 行；采用最低成本方案则缩减为重新评估的条件，不能拼接新旧数字。显著优效必须基于相同 subjects 的配对预测，旧汇总表不能恢复 DeLong/McNemar/paired bootstrap。

临床直接对照：真实 MMSE+CDR 在 AD/CN 233（83/150）、未细分 MCI/CN 381（231/150）、EMCI/LMCI 0 人可用；全 5 评分完整者仅 14/23/0 人。原 Figure 5 的 EMCI+LMCI/CN 任务在 MMSE+CDR 完整子集中仅余 150 名 CN，无阳性，不能分类。它们也未认证生成器未见。filled 值最多作为 conditioning-variables-only 捷径对照，不能冒充原始临床评分。

Full / No Cognitive Scores / Null patient prompt 在结构上可通过更换患者 token 实现，不重训生成器；先复现 Full，再固定 20 例、双 tracer、三条件共 120 forwards。保留 tracer token，No Cognitive 删除全部五类评分文字/数值，Null 用同一编码器的空文本 token。去评分及 Null 都存在训练分布偏移，只能证明固定模型条件敏感性，不能独自证实/排除标签捷径。本轮未执行此 GPU 实验。

必须修正的模型事实：

- U-Net checkpoint 为 **9,925,921 个存储参数元素**（不含冻结 BiomedCLIP），1 输入/1 输出通道，512 维 cross-attention；患者与 tracer 各一 token。`attention_levels=(False,False,False,True)`，不能描述为每个多尺度 stage 均注入。FDG 和 AV45 使用同一网络分别 forward；不是一次 forward 同时输出双通道 PET。双 tracer 成本需计两次调用。
- new-final 路径直接编码 raw tracer 文本；github 路径加载 adapted tensor。两者引用同名 165 checkpoint，checkpoint 内没有外部 token provenance。**不能延续“已证实最终 adapter 完全旁路”，也不能宣称最终 checkpoint 确实使用适配向量。** 应据可证实运行收紧 Eq.1/域适配因果归因，未绑定则明确限制。
- 独立 adapter 代码确实存在：512 维 PET image features 为 160 个 2D slice 特征的平均；scalar scale+512 bias，Adam lr=10⁻³、500 iterations；实际约束是 `100×(cos−0.82)²` 的软目标，不能写成已严格满足 `cos≥τ` 的硬约束。τ=0.82 的选择及训练时消融证据未恢复。
- 已见训练代码将 t 固定为 0 做 endpoint fine-tuning，未见 teacher/trajectory 蒸馏损失；初训阈值 140、resume 代码阈值 120，不把代码版本差异包装成精确统一日程。“exact one-step ODE sampling”应改为学习的一步端点近似。
- 训练 CSV 只有 60 条记录（58 个完整 epoch、两条部分进度），缺 48–153 的逐轮记录，且最后 epoch 165 仅 71%；不能称“完整 165 轮收敛日志”，也不能据此独立核实 138 GPU-hours。参数数已实查，FLOPs/显存/同硬件延迟未测，不提供伪精确效率表。

## 5. 原始 Reviewer #1–20 证据矩阵

| 原编号 | 原始意见主题 | 状态 | 证据/处置 |
|---|---|---|---|
| #1 | 科学创新 | 可低成本解决 | 保留条件 RF/双 tracer 贡献；域适配的实际使用未绑定，不以概念图代替运行证据。 |
| #2 | 临床动机 | 可低成本解决 | 保留成本/可及性动机；输入应写 MRI+患者临床文本，避免声称仅 MRI。 |
| #3 | 三折与两折不一致 | 需额外实验 | 旧 loader 作用域及 epoch 平均不构成有效三折；如实撤回旧协议结论，独立分类需重算。 |
| #4 | 预后夸大 | 可低成本解决 | EMCI/LMCI 改为横断面阶段区分；不声称转换预测。 |
| #5 | 临床信息捷径 | 需额外实验 | 提供固定模型三条件敏感性及临床变量对照方案；尚未执行，不能声称已排除捷径。 |
| #6 | subject/访视隔离 | 已解决（划分）；需额外实验（独立分类） | 新提供的最终名单核实1856 train/1 CN val，互斥且覆盖1857人；无足够未训练二分类样本。 |
| #7 | 外部双示踪剂证据不完整 | 建议以局限性回应 | 仅可声称经身份核验的 AV45 外部结果；当前软链是 OASIS-1 MRI，419 人 OASIS-3 PET 未闭环。 |
| #8 | 非显著不能证明等效 | 已解决（收紧结论） | 撤除 p>0.05→等效；报告 bias/CI/LoA；无合理边界不做 TOST。 |
| #9 | 多重比较 family | 已解决 | 196 总体、980 分层、392 AD/CN 原始 p 与 BH q 已保存；方法明确 family。 |
| #10 | PET 一致性与校准 | 已解决（描述性范围） | 从真实 Syn 卷重提 98 区，报告 ICC/CCC/BA/校准；用 normalized uptake，不夸大为临床定量替代。 |
| #11 | 分类不确定性 | 需额外实验 | 旧汇总不能补出有效 OOF CI；新协议逐 subject 概率、fold 结果和 paired subject bootstrap。 |
| #12 | 显著优效直接检验 | 可低成本解决或需额外实验 | 先删无支持的 significantly；若保留优效主张，需相同独立 subjects 的配对预测与直接检验。 |
| #13 | exact one-step 术语 | 可低成本解决 | 改为 endpoint fine-tuning 后学习的一步近似；双 tracer 两次 forward，不称精确 ODE 积分。 |
| #14 | VLM/adapter 可复现细节 | 可低成本解决（仍有溯源缺口） | 补 512 维、160 切片平均、prompt 与独立 adapter 优化；raw/adapted 运行分歧须声明。 |
| #15 | Eq.1 与 τ | 建议以局限性回应 | 代码为 cos=0.82 软目标，不是 ≥τ 硬约束；无训练时 τ 消融，不声称已证明最优或稳健。 |
| #16 | 人口学混杂 | 可低成本解决（部分） | 完成 age/sex HC3 和正体重敏感性；真实临床评分缺失及 prompt 捷径仍限制因果解释。 |
| #17 | 基线改造与公平性 | 建议以局限性回应 | 说明可验证的实现差异；未闭环同 split/调参预算，不把雷达图匹配视为公平性证明。 |
| #18 | 效率实测 | 需额外实验 | 已核 generator 参数数；138 GPUh/完整日志未核实。只规划小型同硬件计时，不编造 FLOPs/显存。 |
| #19 | 复现材料 | 可低成本解决 | 提供 commit、源哈希、逐人集合、命令、统计环境；注明最终名单由用户恢复，checkpoint 未内嵌 manifest。 |
| #20 | 临床转化过强 | 可低成本解决 | 删除临床可操作/广泛筛查已成立等说法；限定为回顾性研究，前瞻和多中心验证待开展。 |

## 交付与未解决项

[最终区域总表](image_derived/regional_agreement_overall.csv)；[分组表](image_derived/regional_agreement_by_diagnosis.csv)；[Bland–Altman 图](image_derived/bland_altman_fixed_regions.pdf)；[人口学调整](image_derived/regional_AD_CN_adjusted_observed_demographics.csv)；[旧 Syn 列与原卷差异](image_derived/old_csv_syn_vs_actual_volumes.csv)；[验证收据](validation_receipt.json)。执行命令、family、源文件哈希和结果关系在 METHODS 文件及 CSV 中。

仍无法解决：adapter 实际使用的身份绑定；可用于二分类的独立队列；部分真实认知变量及访视日期；原 OASIS-3 PET 队列与外部结果的身份闭环；基线训练公平性、直接 runtime/FLOPs/显存；临床等效边界与前瞻性临床效用。它们必须作为限制或新实验前提，不能由当前高 ICC、非显著 p 或审计报告的标签替代。
