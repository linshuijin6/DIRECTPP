# Stage 4A：Fig. 5 分类协议静态核查与 Full/OT 无泄漏复用方案

## 结论

原 Fig. 5 的科学问题可以复用，但**不能原样复用历史分类执行方式，也不能把两折 OOF 图像直接重新随机分成三折后训练/测试分类器**。当前最可靠的外层隔离单元是 Full/OT 已冻结的两折生成器 fold；分类 outer test 必须等于对应生成器 held-out fold。

在不重训生成器的前提下，有两种有效边界：

1. **当前资产即可执行的最小部署对照**：每个生成器 outer fold 内，用另一 fold 的 Real PET（及 MRI）训练 DenseNet，在 held-out fold 上以同一个分类器分别预测 Real、Full 和 OT。它能公平比较 Full/OT 作为 Real-trained classifier 的替代输入，但不是原 Fig. 5“分别在 synthetic PET 上训练分类器”的完全复现。
2. **推荐的 Fig. 5 忠实方案**：仍使用两折 outer split；对每个 fold，用该 fold 的冻结 Epoch 165 生成器 checkpoint 对 outer-train 受试者补做一次 train-side 推理，再在 Full 或 OT 图像上独立训练分类器，最后在现有 OOF held-out 图像上测试。该方案不重训生成器，但当前缺少 train-side synthetic 资产，因此在补推理前为 **BLOCKED**。

本阶段未训练、推理或评价分类器，也未运行生成器。

## A. 原论文 Fig. 5 定义

### A1. 论文位置

- Results Section 2.4：`manuscript/BMEF_main.tex:151–167`。声明 ADNI、3-fold classification、DenseNet、三项任务和 ACC/SEN/SPE/AUC，并给出 Fig. 5 的若干点估计。
- Fig. 5 caption：`BMEF_main.tex:160–164`。明确三项任务与 11 组输入。
- Methods Section 4.5.2（源码标题为 `Diagnosis and Prognostic Stratification`）：`BMEF_main.tex:338–344`。声明 identical DenseNet、3-fold stratified sampling、ACC/SEN/SPE；这里漏写 AUC，与 Results/Fig. 5 不完全一致。
- 数据与生成器 split：`BMEF_main.tex:292–303`。全队列 1,857 人，CN/AD/EMCI/LMCI/MCI-U 分别 577/317/291/152/520；生成评价另声明 two-fold。
- Supplementary：`manuscript/supplementary/supplementary.tex:45–68` 仅给五组总体人口学人数，没有 Fig. 5 的逐任务/逐模态样本量、fold 或不确定性；没有额外分类协议。

论文把 EMCI/LMCI 称为 prognostic stratification，但现有标签是横断面阶段标签，不是纵向转归终点；后续只能称“EMCI/LMCI 阶段区分”。

### A2. 三项标签定义与当前可用人数

正类预先固定为 AD、MCI、LMCI。历史代码中的 “MCI vs CN” 实际把 `EMCI + LMCI` 合为正类，**排除了 520 名 MCI-U**；这与论文宽泛的 “MCI” 表述存在歧义，后续若要复用 Fig. 5，必须沿用这一历史定义，不能静默加入 MCI-U。

以下人数为排除 E1 冻结 QC 病例 `016_S_4952` 后的 1,856 人；括号为类别数。

| 任务（正类 vs 负类） | MRI | FDG 可用 | AV45 可用 | 双 tracer 交集 |
|---|---:|---:|---:|---:|
| AD vs CN | 893：317/576（35.5%） | 673：303/370（45.0%） | 689：179/510（26.0%） | 469：165/304（35.2%） |
| EMCI+LMCI vs CN（历史 MCI/CN） | 1,019：443/576（43.5%） | 811：441/370（54.4%） | 948：438/510（46.2%） | 740：436/304（58.9%） |
| LMCI vs EMCI（论文写作 EMCI vs LMCI） | 443：152/291（34.3%） | 441：151/290（34.2%） | 438：150/288（34.2%） | 436：149/287（34.2%） |

表内为 `总数：正类/负类（正类比例）`。双 tracer generator fold1/fold2 分别为：AD/CN `238：83/155` 与 `231：82/149`；历史 MCI/CN `374：219/155` 与 `366：217/149`；LMCI/EMCI `219：75/144` 与 `217：74/143`。旧审计的双 tracer 470/741/436 包含后来冻结排除的 CN `016_S_4952`，因此当前有效队列为 469/740/436。Fig. 5 没有报告每组柱子的实际人数；不能把总体 1,857 或任一双 tracer 人数套用于全部 11 组。

### A3. 11 组输入及复用状态

| # | Fig. 5 输入 | 当前有效队列 | 历史实现证据 | 下一阶段状态 |
|---:|---|---|---|---|
| 1 | MRI | MRI task cohort | 3D DenseNet121, 1 channel | 可复用 backbone/输入；须重建 split/loader/评估 |
| 2 | Real FDG | FDG cohort | Real-PET notebook, 1 channel | 可用 E1 Real cache；须修复协议 |
| 3 | Syn FDG | FDG cohort | generated-PET notebook, 1 channel | Full/OT OOF test 可用；忠实训练缺 train-side Syn |
| 4 | Real AV45 | AV45 cohort | Real-PET notebook, 1 channel | 可用 E1 Real cache；须修复协议 |
| 5 | Syn AV45 | AV45 cohort | generated-PET notebook, 1 channel | 同 #3 |
| 6 | MRI + Real FDG | FDG cohort | concat, DenseNet 2 channels | 数据可用；须修复协议 |
| 7 | MRI + Syn FDG | FDG cohort | concat, DenseNet 2 channels | OOF test 可用；忠实训练缺 train-side Syn |
| 8 | MRI + Real AV45 | AV45 cohort | concat, DenseNet 2 channels | 数据可用；须修复协议 |
| 9 | MRI + Syn AV45 | AV45 cohort | concat, DenseNet 2 channels | 同 #7 |
| 10 | MRI + Real FDG + Real AV45 | dual cohort | concat, DenseNet 3 channels | 数据可用；须修复协议 |
| 11 | MRI + Syn FDG + Syn AV45 | dual cohort | concat, DenseNet 3 channels | OOF test 可用；忠实训练缺 train-side Syn |

Full 是原论文 Syn-PET 的当前可追溯实现；OT 是新增 tracer-only 对照。若完整扩展 Fig. 5，应在五个 synthetic 输入旁各增加对应 OT，而不是替换 Real、MRI 或 Full。

## B. 原始 DenseNet 实现核查

核心入口由 `CORE_CODE.md` 和 `paper_index/core_code_index.csv` 指向：

- Syn-PET 分类：`source_archive/vscode-3002/home/ssddata/liutuo/mri2pet all data-_mri classification-densenet.ipynb`，SHA-256 `bc772e80…2b5c`。
- Real-PET 分类：同目录 `...classification-densenet-Copy2.ipynb`，SHA-256 `ba066e8f…f81`；核心索引标记 cell 19。
- AD/CN 历史入口：`source_archive/vscode-3003/.../mri2pet all data-_mri classification-densenet-checkpoint.ipynb`，SHA-256 `58923ca5…d89d`。
- 既有修稿方案：`appendix/legacy_only/8_revision_evidence/revision_20261016/CLASSIFICATION_AND_SENSITIVITY_PLAN.md`。

### 可以保留

- MONAI `DenseNet121(spatial_dims=3, out_channels=2)`。
- 1/2/3 channel 的体积拼接方式，对应单模态、MRI+单 tracer、MRI+双 tracer。
- CrossEntropyLoss、Adam `lr=1e-4`、原 200 epoch 上限可作为待冻结超参数；是否使用早停必须统一。
- ACC、SEN、SPE、AUC；鉴于类别不平衡，新增 balanced accuracy 作为预先指定的必要辅助指标，不取代原四项。

### 必须修复，不能直接执行历史 notebook

1. notebook 先运行一次 `StratifiedKFold` 并只留下最后一折的 `train_data/val_data`，随后只据此构建一次 loader；后面的 `KFold` 外层循环虽然产生新 indices，却**没有重建 Dataset/DataLoader**，因此三次训练实际重复使用同一 loader 划分。
2. 训练循环使用 `KFold` 而非论文声明的 stratified split。
3. 同一 val fold同时用于每两 epoch选最佳 ACC和报告性能，没有独立 inner validation/outer test。
4. 最终数值把每折所有 validation epochs 的指标先平均，再跨折平均；这不是每名受试者一条 outer OOF 预测，也不是合法的 checkpoint-level CV 估计。
5. AUC 使用 positive-class raw logit；应固定为 `softmax(logits)[:, positive_class]`（或明确等价的二分类 score）并输出逐 subject 概率。
6. `random.shuffle` 未固定种子，训练随机性、数据增广、worker 和 checkpoint 身份均无完整收据。
7. 原始路径、模态交集和旧生成图像身份没有和当前 Epoch 165 Full/OT 哈希绑定。

因此，历史代码只能作为 backbone、channel 组合和超参数线索，旧 Fig. 5 数字不能作为新 Full/OT 比较的基线结果继续拼接。

## C. Full/OT 两折身份与泄漏分析

Stage 2 已核验：有效 cohort 1,856 人，生成器 fold1/fold2 各 928 人；Full/OT Epoch 165 键完全一致。有效预测每模型 FDG 1,597、AV45 1,364，双 tracer 交集 1,105；预测与 checkpoint、PTID、tracer、fold 和 SHA-256 已绑定。

生成器规则为：`test_fold=f` 的受试者由未使用该 fold 的 checkpoint `G_f` 生成。单个 OOF 预测对该受试者自身是 held-out，但这不足以保证下游分类独立：

```text
错误三折方案：
classification test 中的 A（generator fold 1）
        ↓ 曾参与训练
classification train 中 B 的 OOF 生成器（在 generator fold 1 上训练）
```

因此，将全部 OOF 图像混合后再做任意 3-fold classification，会让分类训练特征的上游生成器见过分类测试受试者。即使每名受试者自己的图像是 OOF，也仍有跨样本的 upstream leakage。

### 合法 outer-fold 契约

对 `outer test = generator fold f`：

- 分类 test：只用现有 `G_f` 对 fold f 的 OOF Full/OT。
- 分类 train：只用另一 fold的受试者。
- 若训练 synthetic classifier，train 图像必须也由同一个 `G_f` 生成；不能使用这些训练受试者现有的交叉 OOF（它们来自另一 checkpoint，后者见过 outer test）。
- 分类 train 内再做 subject-stratified inner validation；所有 scaler、增广选择、checkpoint、threshold 只由 outer-train/inner-validation决定。
- 每个 outer fold重新构建 dataset、loader和模型。禁止同一 PTID跨 train/test；若未来引入多访视，按 PTID成组。

这会把论文的 3-fold 分类改为**生成器锚定的 2-fold outer evaluation**。这是当前固定生成器资产下避免重训生成器且不泄漏的必要变化，必须在报告/论文中明确，不能称为原 3-fold 原样复现。

## D. Full vs OT、公平配对和基线

### D1. Full vs OT

- 同一 task、modality、outer fold 使用完全相同的 PTID、标签、MRI、初始化 seed、训练超参数和停止规则。
- 忠实方案中 Full/OT 各自训练分类器，但 outer-test 概率按同一受试者配对；至少固定相同 seed。若资源允许，预先固定多个 seed并把 seed当重复因素，不能结果后选 seed。
- 主要比较预先固定为五组同构输入的 `Full vs OT` pooled outer-OOF AUC；若采用最小双 tracer方案，则只把 `MRI+Full FDG+Full AV45 vs MRI+OT FDG+OT AV45` 定为主要比较。
- ΔAUC 用 paired subject bootstrap（同时按 outer fold和标签分层）；ACC/balanced ACC/SEN/SPE差值用同一 paired bootstrap，错误率另报 McNemar。阈值只能在 outer train内确定。
- 多任务/多输入比较事前定义 family并校正；最小方案建议三任务的主要 ΔAUC 用 Holm。不能凭某一任务结果再改变主要输入。

### D2. Clinical-only 与 MRI+Clinical

- `age/sex/weight` 在 E1 cohort中可直接使用，可执行 demographic-only baseline。
- Full prompt中的 MMSE/CDR/GDS/FAQ/NPI-Q 来自历史 filled table。真实 observed complete-case 极少：MMSE+CDR 的 AD/CN 为233，历史 EMCI+LMCI/CN 只有150名CN，EMCI/LMCI为0；五评分完整者分别14、10名CN-only、0。故 observed-score clinical-only 无法在三任务共同影像队列上公平执行。
- 可从冻结 Full description解析 filled conditioning values，执行 `prompt-variables-only shortcut`；必须明确它不是经验证的原始临床评分，也不能用作独立临床效用证据。它对诊断标签可能高度直接。
- MRI+Clinical 不是原 Fig. 5 的 11组之一，需要新增 MRI DenseNet embedding + 低维 clinical MLP/线性头；技术上可执行，但属于预先声明的审稿人敏感性基线，不能冒充原 DenseNet输入组合。所有缺失处理与标准化必须在 outer train拟合。

## E. 下一阶段最小可执行实验

### E1. 推荐主方案：忠实比较，需补 train-side 推理

仅保留原 Fig. 5 最关键的四个 dual-tracer 条件：

1. MRI only；
2. MRI + Real FDG + Real AV45；
3. MRI + Full FDG + Full AV45；
4. MRI + OT FDG + OT AV45。

队列固定为各任务的 dual-tracer交集：AD/CN 469、历史 MCI/CN 740、EMCI/LMCI 436；outer fold和每折类别数已由 E1 `test_fold` 固定。训练量为 `3 tasks × 2 outer folds × 4 conditions = 24 DenseNet fits`。其中 MRI-only可跨同任务的模态比较共用一次，但不能跨任务共用。

执行前先用每个已冻结 Full/OT Epoch 165 checkpoint 对其 outer-train受试者生成对应 train-side双 tracer图像；现有 OOF只作为 outer test。此步骤是推理，不是重训生成器，但本阶段未执行。每折在 outer train中固定一个 stratified inner validation用于 checkpoint和阈值选择。

若用户要求完整扩展 11组：保持 MRI和5组 Real输入，给5组 Syn输入分别加入 Full与OT，共16组；`3 tasks × 2 folds × 16 = 96 classifier fits`，另需 Full/OT train-side推理。它不是“最小”方案。

### E2. 当前资产即可执行的无额外生成推理方案

仍使用三任务、两 outer folds和 dual cohort，训练：

- MRI-only DenseNet；
- MRI+Real dual-PET DenseNet。

共 `3 × 2 × 2 = 12 fits`。第二个分类器在同一 outer test上分别输入 MRI+Real、MRI+Full、MRI+OT，得到严格配对的 deployment/domain-transfer比较。优点是无上游泄漏、无需生成器推理；局限是 Full/OT 没有各自训练分类器，不能回答“在 synthetic 分布上训练的 Fig. 5 classifier”问题。

### E3. 指标、产物与资源

- 主要：pooled outer-OOF AUC及 Full−OT ΔAUC；辅助：ACC、balanced ACC、SEN、SPE、confusion matrix。所有指标给 subject-level 95% CI、两折各自值和 pooled值；不把两折当两个独立重复实验。
- 每人每条件恰好一条 outer-test probability。保存 cohort、fold、标签、路径和输入 SHA；每折配置、seed、checkpoint和选择理由；逐 subject概率；配对检验原始/校正p；失败与缺模态清单。
- 资源规划沿用历史 3D DenseNet、batch 1起步。既有方案对27 fits估计约18.8–62.5 GPU小时但未实测；按线性粗略缩放，24 fits约16.7–55.6 GPU小时，12 fits约8.4–27.8 GPU小时，均只是规划场景。实际显存、吞吐和 train-side生成推理时间必须用获批后的短试跑测量。

## F. 进入执行阶段前的阻塞项

| 项目 | 状态 | 要求 |
|---|---|---|
| Full/OT OOF test身份、Epoch165、fold、空间网格 | VERIFIED | 直接复用 Stage 2索引与哈希 |
| E1 MRI/Real PET cache和标签 | VERIFIED | 按 task/modality交集冻结 cohort |
| 历史 MCI/CN真实定义 | VERIFIED | 固定 EMCI+LMCI vs CN；不纳入 MCI-U |
| 原 DenseNet backbone/channel组合 | VERIFIED | 可移植，不执行 notebook |
| 历史 Fig. 5逐柱样本、合法OOF概率和可复用checkpoint | UNVERIFIED/不可复用 | 新协议全量重算，不拼旧数字 |
| Full/OT train-side synthetic图像 | MISSING | 忠实方案必须用对应 outer-fold checkpoint补推理 |
| 分类 inner split、seed、threshold、early stop | 未冻结 | 执行前写入独立配置和名单 |
| observed cognitive-score基线 | BLOCKED for all tasks | 不填补冒充 observed；可做 demographic或明确命名的 filled-prompt shortcut |
| MRI+Clinical融合实现 | MISSING but feasible | 新实现，单独标为敏感性基线 |
| 24/12-fit实际GPU预算 | UNVERIFIED | 下一阶段短试跑后报告实测 |

## G. 对三个核心问题的回答

1. **原 Fig. 5 如何正确复用？** 保留三项历史标签、DenseNet121、11组输入语义和原四项指标，但按当前生成器两折重建全部分类 outer evaluation；旧 notebook的 split、loader、epoch平均和旧柱值不能复用。MCI/CN必须明确为 EMCI+LMCI vs CN。
2. **Full/OT 如何无泄漏公平比较？** classification outer fold必须与 generator held-out fold一致。现有 OOF只用于 outer test；忠实训练需要同一个 outer-fold checkpoint为 outer train补生成 Full/OT。不能把两折 OOF混合后另做三折分类。Full/OT使用相同受试者、fold、seed、超参数、阈值规则和配对统计。
3. **下一阶段最小实验是什么？** 推荐24 fits：三任务×两 outer folds×四个 dual-tracer条件（MRI、MRI+Real、MRI+Full、MRI+OT），外加冻结生成器的 train-side推理；若严格禁止任何新增生成推理，则退化为12 fits的 Real-trained deployment比较，并明确它不是 Fig. 5 synthetic-trained classifier复现。

本方案完全预先按 Fig. 5 和 Full/OT实验身份确定，没有依据 Stage 3A/3B结果选择任务、病例、ROI或模型设置。
