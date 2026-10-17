# 分类复算和固定生成器敏感性分析方案（未执行训练）

本方案是可审核的实验设计，不是已获得的新实验结果。保留 `first_part_165.pth`；不替换为其他 checkpoint，不重训生成器。所有训练均等待用户确认。

## 当前可执行性结论

`train_data_with_description.json` 的 500 人来自早期 ADNI2，而最终 notebook 的训练日志每轮是 1856 个样本；不能通过排除这 500 人获得独立队列。以排序后的 1857 个 ID 重建 `random_state=42, test_size=1`，得到与 notebook 输出一致的首个训练 ID `021_S_4924` 和唯一验证 ID `011_S_4105`（CN）。用户已恢复 `train_data_1856_first_part_165.json` / `val_data_1_first_part_165.json`，逐 ID、全部 Description 和不相交性复核通过，最终名单为1856/1，详见 `final165_split_receipt.json`。Checkpoint 未内嵌 manifest，外部名单由用户指定关联。

**当前1857人中未进入最终训练名单的仅1名CN：011_S_4105；训练/验证都未触及的人数为0。** 三个原任务分别仅有CN 1、CN 1、0人，均无法二分类。原验证样本不等于未参与模型选择的独立测试样本。Affine guidance 若使用全量 PET image features 拟合，其暴露集合还必须一并排除。

MRI 的实际可读路径是 `/home/data/liutuo/code/liutuo_data/data_augmentation_mri/`。注册 Real-PET 在同一上游 `ADNI1234_mri_fdg_av45/PET{1_AV45,2_FDG}_strip_registered/`；项目中旧 Real-PET/MRI 软链指向的 `/home/ssddata` 路径不可用，**不修改软链**。严格按 SID 和实际模态文件存在性取交集，双 Syn/Real PET 加 MRI 的可用队列为1106人，其中1105人在最终训练名单、1人为生成器验证CN。

## 数量与标签，不能混作独立队列

完整元数据：CN 577、AD 317、EMCI 291、LMCI 152、MCI 520。

双示踪剂现存 Syn-PET：CN 305、AD 165、EMCI 287、LMCI 149、MCI 200。由此 AD/CN 是 470 人；按原分类代码的 MCI 定义，EMCI+LMCI/CN 是 741 人；EMCI/LMCI 是 436 人。

原代码的 “MCI vs CN” 排除了 `MCI` 这一标签，不能把它写成所有 MCI 对 CN。若新方案改用 EMCI+LMCI+MCI 对 CN，双示踪剂队列是 941 人，属于更改终点定义，须明确声明；不与旧 Figure 5 的 741 人任务直接混比。

排除早期 ADNI2 500 train + 39 val 后，双 Syn-PET 剩余：CN 143、AD 83、EMCI 140、LMCI 55、MCI 146。因此 AD/CN 226、原定义 MCI/CN 338、EMCI/LMCI 195。这些人数是**条件候选上限**，最终 1856 人训练证据与之冲突，当前不能据此训练或宣称独立。

排除 fixed_split 的 800 人后，双 Syn-PET 剩余：CN 251、AD 149、EMCI 272、LMCI 147、MCI 133；对应 400、670、419 人。同样不代表生成器未见。完整逐人名单在 `subject_membership_and_assets_enriched.csv`。

## 推荐顺序与资源

1. **当前推荐：暂停分类训练，先以本轮真实区域统计修订图 4、Table S1、模型事实及局限性；撤回旧 Figure 5 的验证性结论。** 无额外 GPU 开销。
2. 最终1856/1名单已恢复，仍没有足够的未训练二分类样本。只有新增可认证的独立受试者资产，或另一个明确未训练队列，才能执行后述方案。若已有该队列的 MRI/Real/Syn PET，优先复用；候选人数和标签必须重新取交集，不采用早期500/39排除法。
3. 若不能获得此类 ADNI 队列，只能使用另一个可认证的独立队列。当前 `data/OASIS_DATA_REGISTERED` 实际为 OASIS-1 MRI/分割，不能充当原审计声称的 OASIS-3 419 人 AV45 队列；其样本数、标签及 PET 可用性在本次证据中未建立。不得凭论文的 419 人数字安排实验。

独立数据成立后的最低成本比较：同一完整模态受试者集合、同一 subject folds，用 98 区 Real FDG+AV45 和 Syn FDG+AV45 的区域特征分别训练 L2 logistic regression，另设人口学和临床评分直接分类对照。它检验区域表征的下游判别价值，**不能冒充原 DenseNet 或 MRI+PET Figure 5 的复现**。MRI 对照若需要低成本方案，可从相同 MRI/masks 提取 ROI 体积/强度特征，但必须重新命名其表示方式。

该 CPU 方案 3 任务 × 3 outer folds × 至多 4 条件，约 36 次外层小模型拟合，另计 inner 训练/验证或调参；约 1–4 CPU 核、低于 4 GB 内存、预估小于 1 CPU 小时，属于规划估计，未测速。现成 ROI 表读取量小于 100 MB；如需从原卷提取特征，另计 CPU 解压和 NFS I/O。

如确需保留 MRI/DenseNet 的主结论，最小 GPU 方案为 MRI、MRI+Real 双 PET、MRI+Syn 双 PET 三条件，在相同独立队列的 3 个任务、3 个 outer folds 共 27 fits；先做 AD/CN 的三条件（三折 9 fits），其余任务按结果和少数类人数决定。采用原 DenseNet121，batch 1 起步，必要时梯度累积；1 张 24–48 GB GPU 是候选资源，实际显存须由短试跑确认。以每 fit 50 epochs、每折约 500 个训练样本、有效吞吐 3–10 scans/s 作**未测量的预算场景**，27 fits 的训练部分约 18.8–62.5 GPU 小时，另加验证、早停和 I/O；不能当作实测或保证。不得将 27 fits 写成 18 fits，或沿用错误的旧三折时间。现阶段不申请/占用 GPU、不启动试跑。

所有预算以人数成立为前提。原 200 epochs 上限不应直接套用预算；如要严格沿用，应按实际 epoch 上限扩大预算。

## 训练/评估契约

每个受试者仅用一个预先规定的匹配影像/临床时点；若保留多访视，所有访视必须同组划分且评估按 subject 汇总。outer 3-fold stratified subject split 完全隔离；每个 outer train 内再划 subject-disjoint inner validation，选择 checkpoint/正则化/阈值；outer test 不参与选择。每折**重新构建** Dataset/DataLoader 和分类器，同一受试者 across modalities 使用相同 outer/inner folds。生成器及所有指导向量始终冻结。标准化、缺失值处理、特征筛选、调参只在 inner train 拟合。

用 `softmax(logits)[:, positive_class]` 输出概率，预先固定正类（AD、MCI、LMCI）及训练内阈值规则。各 subject 一条 outer OOF 概率；报告 pooled OOF AUC/ACC/SEN/SPE、confusion matrix、每折数值和按 subject 重采样的 95% CI。不同模态仅在同一受试者上比较；ΔAUC/ΔACC 使用 paired subject bootstrap，二分类错误比较可用 McNemar，事前定义有限的主要比较和校正 family。仅有三折均值不支持独立三次试验的显著性检验。

产物：只读输入及 SHA-256、`cohort.csv`、逐 subject 外/内 fold、标签和模态路径、解析后配置/seed、每折 checkpoint 与选择原因、outer OOF 概率、混淆矩阵、CI/paired comparison 原始及校正值、资源实测、独立保存的新图。失败/缺模态样本须列清单并报告影响。

## Figure 5 必须替换的范围

旧 33 行 × 4 指标的底表、PDF 及 PPT 来源均保留历史原件。三折 loader 未重建、跨 epoch 平均指标及生成器暴露问题影响各任务/模态的共同比较基础，因此不能只换 Syn 柱或只加误差条。若继续呈现原 11 模态/3 任务，需将全部 33 行换成相同独立协议下的新 OOF 结果。若采用最低成本 3 条件方案，则新主图仅展示这三条件；未复算的柱移出验证性主结果并标明历史探索结果，不能拼接新旧数字。

## 临床评分直接分类对照

填补后的 prompt 数值可用于“conditioning-variables-only”捷径诊断，但不是经验证的原始临床评分。真实记录按人口学锚点提取后，MMSE+CDR 完整者 AD/CN 233（AD 83/CN 150），MCI/CN 381（MCI 231/CN 150），EMCI/LMCI 0；5 个评分均完整者分别 14（AD 4/CN 10）、23（MCI 13/CN 10）、0。排除最终训练及验证成员后，这些子集均为0。

上述 381 人的阳性是未细分的 `MCI` 标签，不能替代原 Figure 5 的 EMCI+LMCI/CN 任务：后者在 MMSE+CDR complete-case 子集中仅剩 150 名 CN，没有阳性；全五评分子集中仅剩 10 名 CN，也无法二分类。

因此可设计人口学-only、observed MMSE/CDR-only、人口学+observed MMSE/CDR 对照；但独立比较必须在与影像模型相同的合格 subject 子集上进行。不得用 filled values 补成完整观察，也不能在 14 人样本上提出可靠临床优效结论。当前不执行这些分类拟合。

## Full / No Cognitive Scores / Null Prompt

架构允许只改患者 token；U-Net 输入输出不变，无需重新训练生成器。先绑定准确的原始条件路径，并用 1–2 个病例复现已保存 Full 预测（同 MRI、方向、精度、clamp 和 tracer vector），再开展小样本推理。如果不能复现，应报告条件来源未闭环，不能把变化全部归因于认知评分。

建议预先选定 20 个病例（五个原标签各 4 人，按 SID 固定；不足时如实减少），双 tracer、3 条件共 120 次 forward，固定 MRI、checkpoint、tracer token，患者 token 依次为：

- Full：当时实际输入的完整患者描述。
- No Cognitive Scores：仅保留年龄、性别、体重；删除 CDR、MMSE、GDS、FAQ、NPI-Q 的**全部文字和数值**，不可仅删 MMSE/CDR。
- Null patient prompt：使用空文本经同一 BiomedCLIP 编码，仍保留 tracer token 和双 token 形状；不得把零向量、删除 token、`context=None` 混称同一 Null。

空文本和去评分文本训练时未明确出现，均存在输入分布偏移。变化可说明**这个固定模型对条件的敏感程度**；性能下降不能独自证明原模型发生标签泄漏，性能不变也不能证明完全无捷径。若要评价相应分类可靠性，需同一独立 subject 的各条件 OOF 评估；固定 Full 分类器跨条件预测只是部署扰动敏感性，不是“无评分训练模型”的公平比较。

第一阶段只报告 normalized ROI 变化、影像误差、病例级 paired differences 和图像；没有可信独立分类集时不报告“已排除临床信息泄漏”。τ 向量替换也是 fixed-model 条件扰动，不能替代训练时 τ 消融。

预算是 120 × 实测每 forward 延迟；当前无实测。规划上可把 1 张 24–48 GB GPU、最多 1 GPU 小时设为待确认上限，实际先以 Full 复现检查决定；输入/输出约 2.4 GB 未压缩 float32 PET，另计 MRI/masks。不把此估计写进论文效率表。此轮未执行 GPU 推理。
