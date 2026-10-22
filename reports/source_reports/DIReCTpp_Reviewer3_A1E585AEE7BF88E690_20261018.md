# DIReCT++ 完整审稿意见补充分析（Reviewer 3）

- 稿件：BMEF-D-26-00169，*Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stratification*
- 编辑决定：Major Revision；修回截止日期：2026-11-04；修回将再次外审，期刊称很少允许多轮修改。
- 分析依据：`view-letter.txt`（Reviewer 3 完整报告、编辑决定）、`Reviewer2的审稿意见.docx`（Reviewer 2 的 20 条意见）、`稿件修改分析.txt`（此前 R2 分析）、`BMEF_main.pdf`（30 页投稿稿件）。
- 范围：此文**补充此前 R2 分析**，不把重复意见当作全新问题；尚未检查训练代码、数据清单、实际预处理或原始预测，故“可能泄漏/数据失真”均是待核实的风险，不是已证实事实。
- 优先级：**P0** 涉及基本数据有效性、标签循环性或核心临床定量结论；**P1** 涉及新实验支持与关键公平性；**P2** 涉及方法披露、措辞与图表规范。优先级为分析判断，并非审稿人等级。

## 一、核心结论与相较此前分析的变化

Reviewer 2 总体认可创新性，关注折数、临床信息泄漏、区域统计等。Reviewer 3 则进一步要求**因果归因和反证**：Syn-PET 的预测性能究竟来自 MRI 对个体病理的恢复，还是临床文本携带的诊断信息？BiomedCLIP 固定向量是否真的优于普通 trainable token、数值 MLP？确定性的单步 Rectified Flow 是否优于直接回归？与真实 PET 在**个体层面的 Aβ 阳性/阴性**是否一致？如果这些问题没有证据，仅提高图像 SSIM/PSNR 不足以维护“subject-specific precision”“biomarker”“clinical stratification”等核心主张。

比此前明显新增的两个最高优先级核查：**Table S1 统计数值可信度及缺失数据插补**；**PET 最小最大归一化与真实 SUVR/Centiloid 定量标志物的一致性**。这两项可能决定是否还能沿用现有下游结论。

## 二、Reviewer 3 15 条 Major Comments 逐条补充分析

### R3-1. Clinical prompt 与诊断标签循环性（P0）
**与 R2 的关系**：深化 R2-5（临床信息泄漏）和 R2-16（人口学混杂）。

- 审稿人明确指出 EMCI/LMCI 的认知分组与 Logical Memory II 等量表定义紧密相关，而合成条件可能包含同类评分；因此 MRI+Syn-PET 相对于 MRI 的分类增益，不必然意味着来自 MRI 的分子病理信息。
- 稿件第 4.2.2 节描述临床 token 由 age/sex/weight/neuropsychological scores 构建，但缺少逐字段、逐任务、逐数据集的实际提示模板，不能单凭 Table S1 推断每个量表一定进入了 prompt。
- 必须先核对 **Logical Memory II、CDR、MMSE、FAQ、GDS、NPI-Q 是否作为输入**，以及在具体时点是否可以获得、是否用于定义标签。
- 必需对照：Clinical-only；MRI+clinical；MRI+tracer-only Syn-PET；MRI+full-clinical Syn-PET；以及 shuffled/mismatched clinical prompts。更严格的研究问题是比较 **MRI+Syn-PET 是否超越 MRI+同一临床变量**，而非仅 MRI alone。
- 对“prompt mismatch 导致图像变化”的解读应有分寸：模型原本就是条件模型，输入改变导致输出改变不自动等于泄漏；需要判断这种改变是否符合真实 PET，以及是否导致预测主要依赖标签相关条件。
- **回复必须以实际输入字段和对照结果为依据**；若强相关临床评分是重要驱动力，可认可其价值，但应明确限制“从 MRI 推断独立分子病理”的解释。

### R3-2. Table S1 的标准差异常及潜在按组插补（P0；全新重点）
**与 R2 的关系**：R2 没有明确指出此问题，是实质新增风险。

- Reviewer 3 特别列举 EMCI MMSE **27.50 ± 0.50**、LMCI MMSE **24.47 ± 0.50**、LMCI NPI-Q **4.00 ± 0.03**、EMCI GDS **1.01 ± 0.14**、LMCI GDS **3.02 ± 0.28**，以及 CN 体重 SD **24.13 kg**。
- 稿件 Table S1 将这些数值标为 **mean ± s.d.**。对于单次、原始整数总评分，LMCI NPI-Q 4.00 ± 0.03 尤其不寻常；例如若该组 n=152 且数据均为整数，只要至少一个观测值偏离 4 分 1 分，样本 SD 的量级就会约为 0.081，而不是 0.03（具体结论取决于是否做过连续值转换、汇总或插补）。
- 但**不能直接判定按组填补或造假**：可能是误将 SE 写为 SD、列错位、标注错误、脱敏/变换或旧统计脚本错误；必须检查原始表、统计定义、缺失记录及随访聚合策略。
- 提供每组每变量的 n_obs/n_missing、原始统计、插补前后统计、插补方法、插补拟合范围及是否使用诊断标签。检查是否按 group mean 填补；若按标签填补，分类任务存在直接循环信息风险，必须撤回相关污染结果并在合适划分上重评估。
- 将数据插补置于**训练 fold 以内**，严禁以测试集信息或诊断组标签构造测试受试者的条件变量。

### R3-3. EMCI vs. LMCI 非真实预后终点（P0，主要改文字）
**与 R2 的关系**：同 R2-4、R2-20，但 R3 明确要求修改标题。

- EMCI/LMCI 是横断面临床分期或记忆损伤程度区分；分类准确率 81.96% 不能证明未来 AD 转化或转化时间。
- R3 提供两条备选路：新做定义随访窗的 pMCI/sMCI、Cox/C-index；或从标题及结果中撤掉 prognostic 主张。考虑截稿期与主工作为图像合成，**优先采用现有证据支持的标题与 MCI stage discrimination 定位**；如已有真实纵向结局再考虑补充。
- 同步纠正对 MCI-U 的“缺少进展状态”叙述，避免将当前疾病分级和纵向结局混为一谈。

### R3-4. 组水平平均无法证明个体 PET 精度；Aβ 阳性一致性（P0/P1）
**与 R2 的关系**：深化 R2-8、R2-10；**新增 Aβ-positive/Aβ-negative 正确分型要求**。

- 原文以 paired t-test p>0.05 解释 high fidelity；不显著不等于等效，群体分布相似不等于每个受试者被正确预测。
- 执行每位受试者、每 ROI 的真实/合成 **SUVR** 一致性分析：Pearson / Lin’s CCC / 明确型别的 ICC / Bland–Altman 偏差与一致性限；总体及 CN、MCI、AD 分组。
- 若能得到具有可靠物理/生物学含义的合成 SUVR 或 Centiloid，使用**事先确定且与示踪剂/预处理协议匹配**的 Aβ cutoff，计算 sensitivity、specificity、Cohen’s κ、混淆矩阵与置信区间；尤其检查 CN Aβ+ 与 MCI Aβ− 等 MRI 与诊断不一致的亚群。
- 不要为了达到显著等效性而事后挑选 TOST 边界。边界应依据扫描重复性或有理据的临床误差阈值。
- 若现在无法为 Syn-PET 提供有效 SUVR，就不能用任意 min–max 后的 0–1 数值直接套用已发表阈值，也不能假称已完成 Aβ 阳性验证；必须先解决 R3-5 的量化语义问题，或收缩“可替代生物标志物”表述。

### R3-5. SUV/SUVR、每例 min–max 归一化与 ROI 定量（P0；新增致命技术核查）
**与 R2 的关系**：R2-10 曾额外提及 SUV/SUVR，但 R3 首次明确将其连到归一化步骤、Aβ 阈值及 Fig.4。

- 原文 4.3 写 MRI/PET cropped 并 min–max 归一化为 [0,1]；2.3 又称“normalized to cerebellar gray matter or pons”的区域摄取比值，图上显示 0–1 轴。必须查明 **SUVR 在什么时候计算、在什么图像域计算、使用哪个 reference ROI**。
- 对原始 PET 强度 P，若 per-image min–max 使用 (P−m)/(M−m)，则 reference 比值为 (P_ROI−m)/(P_ref−m)，**一般不等于** P_ROI/P_ref。标准 SUVR 阈值不能直接迁移。合成图像的尺度恢复也不能在测试中利用 real PET 的真实 min/max，否则又引入目标信息。
- R3 明确质疑 AV45 的 reference（提到 whole cerebellum 的 ADNI 常用标准）与当前稿件 cerebellar gray matter 之间的差别。必须依据**实际使用的 ADNI/PUP 协议**解释参考区选择，不能简单把词改成 whole cerebellum 而不重算。
- 核实“Mean Uptake 0–1”的真实量化含义；在证据不支持 SUVR 时，准确标成 arbitrary normalized uptake，并相应限制临床结论。检查 FDR 实际运行与图中星号，以及 real 和 syn 的组间 Cohen’s d 是否具有相当量级。

### R3-6. 生成器与分类器之间的泄漏、扫描配对、示踪剂来源（P0）
**与 R2 的关系**：深化 R2-3、R2-6、R2-19，并新增多条数据实际使用协议。

- 合成 3-fold、4.3 写 2-fold、分类 3-fold 的冲突是稿件确定存在的**描述矛盾**；真实实验是否有错需检验 split / checkpoint / predictions。
- 必须确认同一 ADNI subject 所有访视严格归于一个外层 fold，**且分类测试受试者的 Syn-PET 必须由从未见过该受试者的生成器输出**；明确两阶段 folds 是完全对齐、嵌套还是其他受试者独立方案。
- 新增需披露：MRI–PET 获取最大时间差；ADNI-3/4 是否混入 florbetaben（当前声称 AV45/florbetapir）；PET 数据是 raw 还是 ADNI 标准预处理版本；多扫描仪/站点差异处理；MCI-U 等具体参加哪些分类任务、每类准确 n。
- 如果 split 或时间配对不成立，属真正需要重做实验的阻断项，先于所有模型消融开展审计。

### R3-7. 分类表现统计、类别不平衡与 MRI baseline 偏弱（P1）
**与 R2 的关系**：深化 R2-11、R2-12，部分涉及 R2-17。

- Methods 4.5.2 只列 ACC/SEN/SPE，Figure 5/Results 又报告 AUC，须补 Methods 定义。
- 各任务及模态补 fold mean±SD、95% CI、混淆矩阵；主要配对比较报告正确的 AUC 对比统计（同一受试者的独立 holdout 可考虑 paired DeLong；OOF 比较需处理跨 fold 训练相关性，不可机械将所有折当独立实验）。
- EMCI n=291、LMCI n=152 不平衡；增加 balanced accuracy，并明确阳性类别、模型选择指标及阈值策略。
- Reviewer 3 认为 Fig.5B MRI-only MCI-vs-CN ACC 约 51%，异常偏低，可能夸大 Syn-PET 的增益。先核对训练收敛、任务样本、模型容量、调参与归一化、类比例、是否用一致训练资源；必要时补充更强 MRI-only baseline。

### R3-8. VLM 定义可能夸大：固定 token 与数值语义（P1，核心新增挑战）
**与 R2 的关系**：深化 R2-14、R2-15。

- 当前描述中 Adapt_f(c_f)、Adapt_a(c_a) 在训练主 RF 前预计算并固定。**从 RF 训练阶段的函数输入角度看，它们就是两个固定向量**；是否保留了 BiomedCLIP 带来的语义优势必须与同维度 trainable tracer tokens 比较。
- 数值量表通过冻结 CLIP 文本编码不一定保留数值排序或距离：建议测量同模板下 MMSE 29、24 等的 embedding 距离/单调关系；比较相同数值变量的简单 standardized tabular-MLP conditioning。
- 还需真实交代 2D BiomedCLIP 如何从 3D PET 提取 E[f_f]、E[f_a]（所用切片、聚合），τ 值与约束优化、冻结范围；同步统一 Fig.1B 与 Eq.1 的 α/β 符号。
- 如果普通 learned token/MLP 表现接近，不应强行维护“VLM 是唯一贡献”，应把价值表述为具体条件化或多示踪剂联合训练表现，同时公正报告消融结果。

### R3-9. 系统性消融不足（P1；Reviewer 3 明确列出 7 项）
**与 R2 的关系**：R2-14/15 要求 VLM 与 τ 的细节，R3 进一步要求形成**实验矩阵**。

审稿人最低要求：①no text；②tracer-only；③clinical-only；④frozen vs adapted tracer embedding；⑤VLM text vs numeric/tabular encoder；⑥distilled one-step vs multi-step ODE；⑦joint vs separate tracer generation。当前 3D RF baseline 改动多，不是 isolating BiomedCLIP 的单变量消融。

- 优先组合为解释性对照：**文本因果贡献组**（no/tracer/clinical/full + shuffled）；**语义特异性组**（fixed VLM token vs learned token、CLIP vs tabular MLP）；**生成机制组**（single-step vs multi-step、joint vs separate、条件匹配 regression）。
- 严格一致的数据、可用条件、网络容量/预算、评价指标。不能只依赖未控制变量的已有 DIReCT 结果。
- 时间不足时，应优先能决定主要主张能否成立的对照，而非以大量低价值训练消耗截至期限。

### R3-10. 基线强度及临床条件公平性（P1）
**与 R2 的关系**：R2-17 已提适配公平性，R3 新增**对比方法没有相同临床输入**这一关键混杂。

- CycleGAN 是 unpaired，Swin-UNet 是 segmentation，且相关 MRI→PET 文献 refs.11–14 缺乏直接复现比较；仅声称相同 splits 并不等于 baseline 得到公平任务适配。
- 至少添加一个**输入相同的强基线**（例如相同 MRI+clinical 条件的 3D RF 或条件回归 U-Net），否则无法把 DIReCT++ 的提升归因于架构而不是附加信息。
- 说明 SegGuidedDiff 是 2D/3D、先验来自何处、基线选择与调参预算；必要时区分“不同输入设置的系统性能”与“同输入公平方法比较”两种研究问题。

### R3-11. 图像质量可追溯性及避免案例挑选（P1）
**与 R2 的关系**：深化 R2-10/11/12/17，提出更具体的可复算证据。

- Fig.2 雷达图归一化隐藏**原始绝对指标、变异与不利样本**。应补 AV45/FDG 分开的 SSIM/PSNR/MAE/MSE mean±SD；解释 brain mask 内计算与 intensity range，防止背景体素人为推高相似度。
- 补主要方法的 paired comparison、每示踪剂外部结果（实有 AV45，FDG 外部不可虚构）、voxelwise error maps（典型与 worst-case）、real-vs-synthetic composite SUVR scatter、ROC+CI。
- Fig.2B/C 和 Fig.3 的案例选择标准应公开，建议用 median、低分位、失败案例展示系统性限制。

### R3-12. MRI→PET 确定性单步映射可能只是条件回归，缺乏不确定性（P1）
**与 R2 的关系**：R2-13 质疑 exact single-step，R3 进一步质疑方法学基本性质。

- Equation (7) 从 x0=MRI 经过单步确定性输出 x1，无法自动表示同一 MRI 可能对应多种真实病理负担的不确定性；对于 ill-posed translation，单像素平方误差会偏向条件平均，掩盖 CN-Aβ+ 等异常者。
- 公平对照与**同条件回归 U-Net** 的个体 SUVR/误差，观察相似 MRI 不同 amyloid 水平的建模能力；说明是否有随机性/多样化采样，或明确当前仅返回点估计，不支持 epistemic/aleatoric uncertainty 的充分量化。
- Ensemble 或 stochastic sampling 是可能的扩展，但非所有研究都能在单次修订中完成；不足时需限制临床单例应用主张。
- 删除 “exact one-step sampling”，核实蒸馏教师、步数、目标、loss、epoch140 训练日程和单步计算开销。

### R3-13. OASIS 数据完整性与外部泛化的实际边界（P1/P2）
**与 R2 的关系**：深化 R2-7，新增外部 prompt 缺失处理。

- OASIS-3 当前仅 AV45、CN(n=334)/AD(n=85)，无 MCI 外部验证；两组年龄均值 66.33 vs 72.76，且 weight/FAQ/GDS/NPI-Q 等字段可能缺失。
- 必须列出 OASIS 的 prompt 字段可用性、缺失率、插补规则及是否和 ADNI 使用同一提示语义；外部标签或真实 PET 不得用于生成条件填补。
- 只能声称“external AV45 synthesis on selected CN/AD cohort”，不能外推 FDG 或 MCI stage generalization；若可能可提供 OASIS 子组稳健性分析。

### R3-14. 临床定位及现代替代路径（P2，但全文必改）
**与 R2 的关系**：R2-4/20 已要求收缩结论，R3 指出具体医学框架。

- 删除把 Syn-PET 当作生物学确证或治疗用药资格工具的表述；目前无前瞻性验证、无可靠个体病理状态阈值测试。
- R3 要求讨论 **2024 Alzheimer's Association revised biological criteria** 和 **plasma p-tau217** 等血浆检测替代路径。不是简单说“将来可以加入血液标志物”，而是定位合成影像相比现代血液检测的潜在研究价值、成本与适用场景，同时承认没有 head-to-head clinical utility data。
- 把 primary care screening、actionable biomarker、democratize 等收缩成“research-stage method”“potential to complement downstream assessment, pending external/prospective validation”。

### R3-15. 与作者之前 DIReCT (IPMI 2025) 的增量创新（P1，重要新增）
**与 R2 的关系**：R2-1 高度肯定创新，R3 则明确要求量化**相对于已有工作**的新增价值。

- 审稿人观察到可能的增量是第二 tracer、适配 tracer token、蒸馏。当前主文只用 DIReCT single 作为 baseline，无法单独分解贡献。
- 需要一张 DIReCT vs DIReCT++ 的**方法差异表**（数据/任务、条件变量、VLM/adapter、multi-task/gating、distillation/inference、评价标准），逐个核对原论文与真实实现，不能把原有技术错误归功于 ++。
- 用 joint vs separate、adapted vs fixed、one-step vs multi-step、clinical vs no clinical、matched input 的消融证明核心新增价值。若增益多来自临床输入，论文应以透明方式解释“方法增量”和“信息增量”。

## 三、Reviewer 3 Minor Comments：建议一次性统一清单

1. **语言与术语**：This challenges stems → This challenge stems；neurodegenration → neurodegeneration；sex/gender 统一；SUV 修改为定义准确的 SUVR（须先解决量化流程）；Figure 1 “Just Add It” 换成实际操作定义。
2. **数学/细节**：正文 Equation (2) 前 Vθ 和 θ 的语法混乱；Fig.1B α/β 与 Eq.(1) α1/α2/β1/β2 统一；τ、λ_F、λ_A、batch size、U-Net 深度/宽度、cross-attention 位置、参数量补齐。
3. **统计报告冲突**：Methods §4.5.1 只写 AD/CN 的 paired tests，Results §2.3 写 CN/MCI/AD；需按实际分析一致化；Fig.4 C–F 增加适当的 MCI 对照或说明选择缘由；SUVR reference 定义到每张图。
4. **ROI 与分割器**：temporoparietal junction 不属于直接 atlas label，列出所组合的 ROI；统一 `mri_synthseg (FreeSurfer v7.4.1)` 与 SynthSeg 的实现、版本、引文。
5. **参考文献**：Refs 27/33 FreeSurfer 重复；Ref35 Billot 姓名首字母；Ref28 authors/title；Ref26 排版异常；Ref34 是否正确支持 SPM normalization；Ref36 是否正确支持 AD-vulnerable FDG ROIs；Ref25 MRI-to-CT 与 3D DDIM baseline 的对应性核实。只按真实来源修订，不凭评语擅自替换引用。
6. **数据与复现**：Data Availability 补 FDG；核对许可后提供数据清单/scan IDs、版本、固定 splits/seeds、可复现实验的仓库标签。
7. **稿件管理系统**：R3 称投稿系统中的 abstract 含 `\\noindent`、`\\textbf`、`$^{18}$F` 等裸 LaTeX；需在实际系统里检查并清理，该现象无法仅从 PDF 确认。

## 四、跨审稿人对照（R3 → R2）

| Reviewer 3 | 对应 Reviewer 2 | Reviewer 3 明确新增的核心要求 |
|---|---|---|
| #1 prompt-label circularity | #5、#16 | exact fields、Clinical-only 与 MRI+clinical、shuffled mismatched prompts |
| #2 Table S1 plausibility | #5、#16 间接相关 | **SD 异常、按诊断组插补、缺失率审计** |
| #3 prognosis | #4、#20 | **标题**应移除 prognostic 或做真实纵向终点 |
| #4 agreement | #8、#10 | **Aβ 阳性一致性**、CN Aβ+ 与 MCI Aβ− 分层 |
| #5 quantitative definitions | #9、#10 | **min–max 破坏 SUVR、reference region、效果量** |
| #6 split + pairing | #3、#6、#19 | generator/classifier OOF、扫描时差、tracer identity、scan IDs、MCI-U n |
| #7 classification | #11、#12、#17 | balanced ACC、MRI-only baseline 异常偏低 |
| #8 VLM claims | #14、#15 | **learned token 与 numeric/tabular MLP**；2D encoder 如何处理 3D |
| #9 ablation | #14、#15 | **七项系统性消融**，强调单一变量隔离 |
| #10 fair baselines | #17 | **相同临床变量输入的强基线**，真实 MRI→PET 参考 |
| #11 image/figures | #10–#12、#17 | brain-masked metrics、worst cases、composite scatter、ROC bands |
| #12 deterministic model | #13、#18 | **条件均值、回归基线、不确定性** |
| #13 external | #7、#16 | **OASIS prompt 缺失**、CN/AD 年龄结构、无 MCI |
| #14 clinical | #4、#20 | **2024 biomarker criteria、p-tau217**、治疗资格误判风险 |
| #15 novelty delta | #1、#14、#17 | **与 DIReCT 原文方法差异及贡献归因** |

## 五、建议把 35 条主要意见组织成六个科学工作包

### A. 数据及标签有效性（必须首先过闸）
R2-3/5/6/16/19；R3-1/2/5/6/13。

1) 提取训练/推理真实输入提示、映射和缺失变量处理；2) 复核 Table S1 原始分布和 imputation provenance；3) 核对 `subjectID-visit-MRI-scanID-PET-scanID-tracer-date-group-split` 关联、折数与 generator/classifier OOF；4) 确认真实 PET 与合成 PET 的定量域。如果任一项发现问题，应决定哪些结论必须作废及哪些实验必须重做。**这比先启动 GPU 消融更重要。**

### B. 条件信息与 VLM 的机制验证
R2-5/14/15/17；R3-1/8/9/10/15。

同样输入条件下，区分临床信息带来的预测收益、BiomedCLIP 表征独有的收益、multi-tracer learning 收益。保证临床-only/MRI+clinical 直接预测对照，适配器 vs 普通 token，VLM vs MLP，joint vs separate，控制预算。对 mismatch/shuffle 的结论避免将“条件响应”本身误判为泄漏。

### C. 临床个体层 PET 定量有效性
R2-8/9/10；R3-4/5/11。

先确定 PET 强度单位和 SUVR 来源，之后 per-subject/per-ROI CCC/ICC/BA、效果量和 FDR/TOST；最终可行时做 Aβ+/Aβ− agreement，优先观察疾病标签与真实 amyloid status 不一致的受试者。若没有量化基础，不得直接给 threshold 结果。

### D. 下游分类稳健性与对比公平
R2-11/12/17；R3-7/10/11。

统一主体独立外层数据折，保存 per-subject 预测；提供 ACC/SEN/SPE/AUC/balanced ACC 的区间、合适的 paired comparison；重核 MRI-only 低基线；图像质量脑区 mask、真实数值及失败案例。

### E. Flow 价值、计算效率与不确定性
R2-13/18；R3-9/12/15。

核对“蒸馏”实现、单步/多步对照、相同临床条件的 plain regression baseline；测推理时间、参数/显存/步骤；讨论确定性生成下无法给出概率不确定性的适用限制。

### F. 科学定位、图稿、回复信与行政要求
R2-4/7/19/20；R3-3/13/14/全部 minor。

标题和 abstract 去除无纵向依据的 prognosis；AV45 only OASIS 限定；严肃讨论血浆 biomarker；公开版本和数据清单；准备每个 review point 的独立回复，投稿更新标色稿与高清可编辑图、所有作者的签署文件。

## 六、建议的“最小充分证据”与研究资源决策

**必须核实且不可仅文字解释（阻断项）**：Table S1 与插补、prompt真实字段、subject-level & OOF、SUVR 尺度可用性、示踪剂/扫描配对。若发现按标签插补或 generator/test 受试者重叠，相关评估应重做；若归一化后不能恢复有效 SUVR，需放弃未得到支持的 biomarker threshold/clinical substitution 主张。

**优先新实验（支撑主要主张）**：MRI+clinical、Clinical-only vs MRI+Syn-PET；tracer-only / full / mismatch；fixed VLM tracer token vs learnable token；VLM numeric vs tabular MLP；matched-input regression U-Net；joint vs separate；个体 SUVR agreement/Aβ status（仅当量纲成立）。其中不少可合并为少量研究设计合理的对照，而非 15 组完全独立项目。

**可用现有结果加分析**：ROI 配对统计、CCC/BA/CI、fold-wise 与 OOF 分类误差、balanced ACC、brain-masked metrics、worst-case plots、baseline fairness table、reference 和插补缺失率审计（取决于原数据是否保存）。

**文字/图稿为主**：分期 vs 预后改题、外部 AV45 结论、exact sampling 描述、VLM 真实冻结方式、Eq(1) 约束、参数详情、引用错误、摘要投稿系统格式、数据/代码可用性与临床未来应用。

## 七、建议修稿时间顺序（2026-10-18 至 2026-11-04）

1. **10/18–10/20：阻断项审计**：冻结稿件版本；核对实际 prompt、统计脚本、Table S1、MRI/PET 时差、split、OOF、量化域。给每项形成 yes/no + 原始证据，立即判断是否需要实质重做。
2. **10/21–10/26：最高价值对照与分析**：先做临床直接分类 baseline、核心条件消融与 matched-input 对照；并行完成 PET 定量可信性验证及分类误差统计。
3. **10/27–10/31：结果收敛**：聚焦 Aβ status、VLM/Flow 增量、OASIS prompt；完善必要图片/表格并据结果重写摘要、标题和讨论。
4. **11/01–11/03：逐点回复和提交材料核验**：R2 20 条、R3 15 条及 minor 逐条回信，确保每条有稿件位置、数据/图表/实验证据；核对 figure source、所有作者表格及高亮修订。
5. **11/04：正式提交前最后核对**。若 data audit 发现必须重跑、无法在两周内完成关键实验，应及时联系编辑申请延期（是否批准不确定），而不是提交未经证实的结果。

## 八、我的总判断与不确定性边界

- R3 对“临床输入循环性”和“BiomedCLIP/Flow 独特贡献”的要求**并非否定研究**，而是把创新从架构叙述提升为须可隔离、可复现验证的科学主张。
- **R3-2（Table S1）与 R3-5（量化域）是此前分析不够重视的两个可能致命问题**；需要先查真实脚本/数据，再决定是统计表错误、方法局限还是实验无效。
- **R3-4 的 Aβ positivity 分层**是医学说服力很高、但不能绕开定量一致性前提的验证。
- R3-8/9/10/12/15 可被一套设计良好的、同输入条件的模型机制对照共同解决；不应只把模型训练次数堆高。
- R2 对高创新的肯定与 R3 对相对于 DIReCT 的增量质疑可以并存：需要以实验结果而非意见投票来证明贡献。
- 本报告只做稿件与审稿文本的科学推理；尚未检查仓库、历史训练配置、补充数据、原始预测和标准真实阈值，因此没有宣布任何数据泄漏或统计错误已被证实。
