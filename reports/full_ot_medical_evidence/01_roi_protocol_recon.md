# Full/OT 医学影像 ROI 协议静态核查

状态：静态核查完成；未运行预处理、推理、统计或训练。以下“Exact / Approximate / Missing”均以 **E1 冻结关键 ROI 集合**为参照；`Missing` 不表示该标签不在 98 区 atlas 中。

## 结论

1. **E1 与原论文在预设医学类别层面一致，但并非逐标签完全一致。** FDG 的双侧 hippocampus、posterior cingulate，以及 AV45 的 bilateral precuneus 可直接视为原协议的延伸；AV45 的部分 frontal/temporal 子区也与 Fig. 3/4 的具体标签完全重合。
2. **不能直接等同的核心映射有两类。** FDG `temporoparietal junction` 在 98 区 atlas 中没有单一同名标签，E1 用 inferior parietal + middle/superior temporal 作近似覆盖；Fig. 3/4 的 `isthmuscingulate`（1010/2010）与 E1 的 `posteriorcingulate`（1023/2023）是不同 Desikan--Killiany 分区。
3. **论文建立了 98 区 parcellation，但现有原件不足以证明论文统计实际完整覆盖 98/98。** 区域提取代码可生成 98 区；Fig. 4 A/B 加 S1--S4 的一致性图按归档绘图逻辑只有 95 个唯一标签，且原绘图代码使用独立样本检验，与正文所写 paired test + FDR 不一致。因此“原论文已对完整 98 ROI 完成配对、校正后的统计验证”应记为 `UNVERIFIED`。
4. **Full/OT 不能把现有 NIfTI 直接交给 E1 `evaluate.py`。** 两组预测均为 `160×192×160`，但写入 identity affine；E1 缓存使用受试者真实世界 affine（示例为 `[[1,0,0,-78],[0,-1,0,79],[0,0,-1,87],[0,0,0,1]]`）。必须先做 MRI-anchored array/grid 核验并赋回经过验证的 E1 affine，不能仅凭 shape 相同套用 SynthSeg mask。
5. **normalized uptake 不是正文所述参考区归一化 SUV。** E1 的实际量是经 `NormalizeIntensityd` + `ScaleIntensityd` 后的 `[0,1]` 图像，在 ROI 内取体素均值，单位为 arbitrary units；代码没有除以 AV45 cerebellar gray 或 FDG pons。后续可复用这一工程量做 Full/OT 配对比较，但不能称为论文定义的 SUV/SUVR，除非另行验证并实现参考区归一化。

## A. 原论文已有的医学影像评价体系

### A1. 论文定义

| 项目 | 原论文定义 | 原件位置 | 核查结论 |
|---|---|---|---|
| ROI atlas | `mri_synthseg`（FreeSurfer 7.4.1）；Desikan--Killiany + `aseg`；98 个 cortical、subcortical、cerebellar、brainstem ROI | `manuscript/BMEF_main.tex:118-119, 292-301, 323-326`；`BMEF_main.pdf` pp. 5, 13 | **已核实**；PDF 与 TeX 在这些定义上一致。 |
| 区域摄取 | ROI 内 mean tracer uptake；正文称 standardized uptake value (SUV) | `BMEF_main.tex:119` | **已核实文本定义**；与现有实现的 `[0,1]` normalized uptake 不同。 |
| 参考区 | AV45：cerebellar gray matter；FDG：pons | `BMEF_main.tex:119` | **已核实文本定义**；现有 E1/历史区域代码未见该除法。 |
| FDG AD 关键区 | bilateral hippocampus、temporoparietal junction、posterior cingulate cortex | `BMEF_main.tex:326` | **预设类别**；TPJ 无一对一 atlas 标签。 |
| AV45 AD 关键区 | precuneus、frontal lobes、temporal lobes | `BMEF_main.tex:326` | **预设类别**；后两者是宽泛解剖类别。 |
| 实像 vs 合成像 | 同一诊断组内 paired two-sided t-test；正文称多 ROI FDR 校正 | `BMEF_main.tex:134-136, 328-336` | **论文协议**；归档绘图代码却用 `ttest_ind`/Welch，执行一致性 `UNVERIFIED`。 |
| 疾病判别 | AD vs CN 独立 two-sided t-test，分别在 real 和 Syn-PET 重复；FDR | `BMEF_main.tex:138, 328-336` | **已核实文本定义**。 |
| Fig. 3 | FDG：`Left-Hippocampus`、`ctx-lh-isthmuscingulate`、`ctx-lh-superiortemporal`；AV45：`ctx-lh-precuneus`、`ctx-lh-rostralmiddlefrontal`、`ctx-lh-middletemporal` | `manuscript/figures/figure_3.pdf`；图注 `BMEF_main.tex:121-131` | **已核实图面标签**；Fig. 3 的 cingulate 是 isthmus，不是 posterior cingulate。 |
| Fig. 4 A/B | 两 tracer 的 real vs synthetic：bilateral precuneus、frontal pole、temporal pole、superior frontal（共 8 个显示位置） | `figure_4.pdf` A/B；图注 `BMEF_main.tex:140-148` | **已核实图面标签**。 |
| Fig. 4 C / S5 | AV45 AD vs CN：左 precuneus、inferior/middle/superior/transverse temporal | `figure_4.pdf` C；`supplementary.tex:31-36`；`supplementary_figure_5.pdf` | **已核实图面标签**；S5 实际重复同一组 5 个标签，并非新增“remaining”标签。 |
| Fig. 4 D / S6 | FDG AD vs CN：bilateral isthmus cingulate、左 supramarginal、bilateral hippocampus；S6 仅右 supramarginal | `figure_4.pdf` D；`supplementary.tex:38-43`；`supplementary_figure_6.pdf` | **已核实图面标签**。 |
| Fig. 4 E/F | 非疾病相关示例。AV45：bilateral VentralDC、bilateral hippocampus、Left-Cblm-WM；FDG：bilateral thalamus、右 parsorbitalis/lateraloccipital/lingual | `figure_4.pdf` E/F | **已核实图面标签**；不应并入 AD 关键集。 |
| S1--S4 | AV45/FDG 的“remaining brain regions”一致性小提琴图，各 tracer 两页、每页 45 个显示位置 | `supplementary.tex:3-29`；`supplementary_figure_1.pdf`--`4.pdf` | **已核实图面结构**；“remaining”标题不等于 98 个唯一 ROI 全覆盖。 |

### A2. 论文是否实际使用完整 98 ROI

- **Atlas/提取层面：是。** `paper data statistics .ipynb` 零起算 cells 16--17 从首个 SynthSeg mask 的全部非零 `unique_labels` 初始化结果，并逐 label 输出区域 CSV；E1 `roi_labels.csv` 也有 98 个唯一 ID/名称。
- **论文图件层面：不是 98/98 的直接证据。** `test/tiqintu.py:12-13, 28-30, 44-53` 每页取 15 个、6 组共 90 个，同时只从 supplement 列表排除 5 个主图 ID。Fig. 4 A/B 显示 8 个，其中 3 个（右 temporal pole、双侧 superior frontal）又出现在 S1--S4。故 A/B + 对应 supplement 的并集为 **95 个唯一 ROI**；绘图切片遗漏 `60`、`7`、`8`。AV45 Fig. 4 E 另外显示 `60` 与 `7`，但 `8` 仍未见；FDG D/F/S6 未补齐这三项。
- **统计层面：`UNVERIFIED`。** 归档的 `violin.py:83-106` 和 `tiqintu.py:59-86` 对 real 与 synthetic 使用独立样本 t-test，而论文方法写 paired test + FDR。后期 `appendix/legacy_only/8_revision_evidence/compute_regional_statistics.py` 的确生成过 all-98 指标，但它属于修稿期派生分析，不能倒推为原论文图件的实际执行证据。
- 历史绘图脚本引用的 `brain_labels.json` 当前既不在仓库，也不在其原绝对路径；原文件内容/哈希为 **`UNVERIFIED`**。E1 名称表可由冻结的 `roi_labels.csv`（其哈希记录在 `config.json:33`）以及 FreeSurfer 标签表交叉恢复，但不能替代缺失原件的 provenance。

## B. Paper → E1 ROI 映射表

说明：成对 ID 的 `lh/rh` 是 segmenter 名称；E1 已核实其物理左右全部反转，故“物理名称”按 `hemisphere_label_map.json` 报告。`关键集=否` 的标签仍存在于 E1 的 98 区目录，禁止据此新增到冻结关键集。

| Tracer | Paper Section/Figure | 原文脑区名称 | E1 ROI ID（关键集） | E1 ROI 名称 | 物理左右半球名称 | 等级 | 证据来源 |
|---|---|---|---|---|---|---|---|
| FDG | Methods；Fig. 4D | bilateral hippocampus | `17/53`（是） | Left/Right-Hippocampus | Right/Left-Hippocampus | Exact | `BMEF_main.tex:326`；`figure_4.pdf` D；`config.json:66-77` |
| FDG | Methods | posterior cingulate cortex | `1023/2023`（是） | ctx-lh/rh-posteriorcingulate | ctx-rh/lh-posteriorcingulate | Exact | `BMEF_main.tex:326`；`roi_labels.csv:24,67` |
| FDG | Methods | temporoparietal junction | `1008/2008 + 1015/2015 + 1030/2030`（是） | inferiorparietal + middletemporal + superiortemporal | 每对均为物理 rh/lh | Approximate | 论文只给宽泛 TPJ；E1 冻结为三对邻近/组成性子区，atlas 无单一 TPJ 标签 |
| FDG | Fig. 3 | Left-Hippocampus | `17`（是） | Left-Hippocampus | **Right-Hippocampus** | Exact（标签）；物理侧别冲突 | `figure_3.pdf`；`hemisphere_label_map.json:213-217` |
| FDG | Fig. 3；Fig. 4D | ctx-lh/rh-isthmuscingulate | `1010/2010`（否） | ctx-lh/rh-isthmuscingulate | ctx-rh/lh-isthmuscingulate | Missing | `figure_3.pdf`、`figure_4.pdf` D；E1 关键集用 `1023/2023`，不是此标签 |
| FDG | Fig. 3 | ctx-lh-superiortemporal | `1030`（是；双侧集另含 `2030`） | ctx-lh-superiortemporal | ctx-rh-superiortemporal | Exact（标签） | `figure_3.pdf`；`config.json:75-76` |
| FDG | Fig. 4D；S6 | ctx-lh/rh-supramarginal | `1031/2031`（否） | ctx-lh/rh-supramarginal | ctx-rh/lh-supramarginal | Missing | `figure_4.pdf` D；`supplementary_figure_6.pdf` |
| AV45 | Methods；Fig. 3；Fig. 4C/S5 | precuneus | `1025/2025`（是） | ctx-lh/rh-precuneus | ctx-rh/lh-precuneus | Exact | `BMEF_main.tex:326`；Fig. 3/4；`config.json:53-65` |
| AV45 | Methods | frontal lobes | `1027/2027 + 1028/2028`（是） | rostralmiddlefrontal + superiorfrontal | 每对均为物理 rh/lh | Approximate | “frontal lobes”宽于两个具体 parcel；E1 未把所有额叶 parcel 纳入关键集 |
| AV45 | Fig. 3 | ctx-lh-rostralmiddlefrontal | `1027`（是；双侧集另含 `2027`） | ctx-lh-rostralmiddlefrontal | ctx-rh-rostralmiddlefrontal | Exact（标签） | `figure_3.pdf`；`config.json:57-58` |
| AV45 | Methods | temporal lobes | `1015/2015 + 1030/2030`（是） | middletemporal + superiortemporal | 每对均为物理 rh/lh | Approximate | 原文为宽泛 temporal lobes；E1 仅冻结其中两对 |
| AV45 | Fig. 3 | ctx-lh-middletemporal | `1015`（是；双侧集另含 `2015`） | ctx-lh-middletemporal | ctx-rh-middletemporal | Exact（标签） | `figure_3.pdf`；`config.json:61-64` |
| AV45 | Fig. 4C/S5 | left inferior/middle/superior/transverse temporal | `1009`（否）、`1015`（是）、`1030`（是）、`1034`（否） | 对应 ctx-lh-*temporal | 均为对应 ctx-rh-*temporal | Exact ×2；Missing ×2 | `figure_4.pdf` C；`supplementary_figure_5.pdf`；`roi_labels.csv:10,16,31,35` |
| AV45/FDG | Fig. 4 A/B | bilateral precuneus、frontalpole、temporalpole、superiorfrontal | `1025/2025, 1032/2032, 1033/2033, 1028/2028` | 同名 ctx-lh/rh labels | 每对均为物理 rh/lh | AV45：Exact（precuneus/superiorfrontal）+ Missing（两 pole）；FDG：均 Missing | Fig. 4 A/B；全部 8 个标签均在 E1 98 区目录 |
| AV45 | Fig. 4E | bilateral VentralDC、bilateral hippocampus、Left-Cblm-WM | `28/60, 17/53, 7`（均否） | 同名 segmenter labels | 成对结构物理左右反转；`7` 为物理 Right-Cblm-WM | Missing | Fig. 4 E；非疾病相关对照，不属于 AV45 预设关键区 |
| FDG | Fig. 4F | bilateral thalamus、ctx-rh-parsorbitalis/lateraloccipital/lingual | `10/49, 2019, 2011, 2013`（均否） | 同名 segmenter labels | 成对 thalamus 物理右/左；三个 `ctx-rh` 均为物理 `ctx-lh` | Missing | Fig. 4 F；非疾病相关对照 |
| AV45/FDG | S1--S4 | remaining brain regions | 98 区目录中的广泛其余标签；不是冻结关键集的扩展授权 | 见 `roi_labels.csv` | 必须经 physical-name map | 不逐项定级 | `supplementary.tex:3-29`；四张 supplement PDF；存在上述 95/98 覆盖缺口 |

### isthmus cingulate 与 posterior cingulate 的边界

- `1010/2010 = ctx-lh/rh-isthmuscingulate`；`1023/2023 = ctx-lh/rh-posteriorcingulate`。四个 ID 在 `roi_labels.csv` 与 FreeSurfer 标签表中分别存在，**不是别名**。
- Fig. 3（左）与 Fig. 4D（双侧）实际画的是 isthmus cingulate；正文 Methods 的 FDG 预设写 posterior cingulate；E1 冻结关键集遵循 Methods，选 `1023/2023`。
- 因此 E1 posterior cingulate 可以扩展论文的**文字预设**，但不能声称复现 Fig. 3/4 的 isthmus-cingulate 图示。若下一阶段只保持冻结集，应把该差异作为预先声明的近邻但非等同关系，不新增 `1010/2010`。

## C. 已有代码的可复用清单

| 能力 | 当前实现 | 可复用状态 | 限制 |
|---|---|---|---|
| 98 区目录 | `roi_labels.csv`：98 个唯一 ID/名称 | 直接复用 | 原 `brain_labels.json` 本体缺失；用冻结 CSV，不重建或改名。 |
| 物理半球名 | `hemisphere_label_map.json`；`evaluate.py:27-34` | 直接复用 | 输出必须用 `physical_name`；不能把 `lh/rh` segmenter 字符串当物理左右。 |
| ROI 有效性 | `roi_validity.json`；`evaluate.py:37-38, 158-161` | 直接复用到 E1 1856 交集 | 17 名受试者至少一 ROI 无效；关键 ROI 中 ID17 对 7 人、ID53 对 2 人无效。 |
| ROI 均值 | `evaluate.py:20-24` 的 bincount sums/counts | 条件满足后复用 | 预测与 mask 必须处于同一数组格；零 voxel 返回 NaN。 |
| ROI MAE | `evaluate.py:167-182, 197-220` | 直接复用统计逻辑 | E1 主终点是每受试者对可用 ROI 的平均绝对误差；并非参考区 SUV 误差。 |
| CCC | `evaluate.py:41-53` | 直接复用 | 跨受试者、逐 ROI；需要至少 3 个有效 pair。 |
| ICC | `evaluate.py:41-53`，标为 two-way absolute single-measure `ICC(A,1)` | 直接复用 | 报告中应保持该 ICC 类型，不笼统写 ICC。 |
| Bland--Altman | `evaluate.py:45-53` 输出 bias、`bias ± 1.96 SD` LoA | 数值可复用 | 当前 E1 代码没有 BA 作图；`agreement.csv` 仅保存汇总量。 |
| 校准 | `evaluate.py:201-205` slope/intercept | 可选复用 | 属于协议补充，不替代 CCC/ICC/BA。 |
| 完整 98 敏感性 | `evaluate.py:183-187, 220` | 可复用 | 主分析会按受试者剔除无效 ROI；`complete98_sensitivity.csv` 才是全 98 complete-case。 |
| normalized uptake | `prepare.py:170-178` + `evaluate.py:20-24` | 可复用为工程尺度 | 实际定义为预处理后 `[0,1]` 体素的 ROI mean，报告单位已写 `normalized uptake (arbitrary units)`（`prepare.py:279`、`evaluate.py:161`）；**不是** cerebellar-gray/pons-normalized SUV/SUVR。 |
| 原论文统计绘图 | `shuijin_code.ipynb`、`test/violin.py`、`test/tiqintu.py` | 不直接复用推断 | real/synthetic 被当独立样本；多重比较与正文不一致；只可用于恢复图中 ROI 身份和布局。 |

E1 两组关键集均为 10 个 ID，全部存在于 98 区目录；两 tracer 并集为 16 个唯一 ID。这里的“属于 98 区”已核实，“每位受试者都能使用全部关键 ID”不成立，须沿用 `roi_validity.json`。

## D. 空间/数据对应的潜在阻塞项

| 项目 | 静态证据 | 判定 |
|---|---|---|
| Cohort 身份 | Full/OT 为 1,857 名；E1 冻结 `cohort.json` 也含同一 1,857 PTID，但有效分析排除 `016_S_4952`，剩 1,856；原始 MRI/FDG/AV45 的 5,571 个路径与 SHA-256 在两套 input manifest 中逐项一致 | **可对齐**；Full/OT ROI 分析必须固定取 E1 1,856 交集，保留原 Full/OT split/预测/checkpoint，不重分折。 |
| Tracer 有效数 | Full/OT：FDG 1,598、AV45 1,365；E1 有效：1,597/1,364 | **可解释**；差 1 正是被排除的 `016_S_4952`，不可把 1,857 与 1,856 的总体指标直接混报。 |
| Full/OT 配对身份 | 审计记录 Full 与 OT 各 5,926 行、键 `PTID+tracer+fold+epoch` 全部对齐；fold 留出 929/928，交集 0 | **可直接复用身份与资产**；不改变 checkpoint、epoch、fold。证据：`full_tracer_conditioning_audit/AUDIT.md:61-73`。 |
| Array shape | Full/OT 抽查与收据均为 `160×192×160`；E1 cache/mask 同 shape | **必要但不充分**。 |
| NIfTI affine | Full 和 OT 推理代码均经同一入口用 `np.eye(4)` 保存（`original_author_reproduction/run.py:893-923`）；只读 header 抽查两者均为 identity。E1 `evaluate.py:151-154` 要求预测 affine 与 cache affine 在 `1e-5` 内一致 | **阻塞：当前不可直接送入 E1 evaluator**。 |
| 预处理语义 | Full/OT 与 E1 都是 headerless `get_fdata` → LPI → MRI crop → histogram normalization(MRI) → pad/crop 160×192×160 → 1-mm spacing → normalize → scale；E1 显式 `allow_smaller=True`，Full 未显式设置 | **很可能同数组格，但仍是推断**；MONAI 版本/默认参数和实际 crop 边界尚未逐 subject 证明。 |
| MRI-anchored alignment | E1 用 saved-MRI 精确 replay 锚定历史 mask，并为 1,856 人通过 gate；Full/OT NIfTI header 未携带该世界变换 | **必须做**。至少要用同 PTID 的 Full/OT 输入 MRI 数组与 E1 cache MRI 做 exact/max-abs 核验，再决定能否直接 array-index mask。 |
| 左右半球 | E1 证明 segmenter 左右名对全部 1,856 人物理反转；Full/OT 预测本身无可信 world affine | **必须沿用 E1 physical map**；禁止从 Full/OT identity header 推断左右。 |
| 论文参考区归一化 | E1 98 区含 cerebellar cortex，但不含单独 pons（仅 Brain-Stem）；现有代码没有参考区除法 | **阻塞于论文 SUV/SUVR 等价性**；若只做 frozen normalized-uptake 比较可继续，但必须明确不是正文 SUV 定义。 |
| 原始 `brain_labels.json` | 历史代码引用，文件未归档/原路径不存在 | **UNVERIFIED provenance**；不阻塞使用冻结 `roi_labels.csv`，但阻止声称已核对原 JSON 本体。 |

当前可直接复用：1,856 人交集、PTID/tracer/fold/epoch 身份、Full/OT 预测与 checkpoint 收据、E1 的 98 标签目录、physical hemisphere map、ROI validity、ROI mean/MAE/CCC/ICC/LoA 计算逻辑。

下一阶段前必须验证：Full/OT 数组与 E1 MRI/mask 的 exact grid 关系、写回 affine 后的 evaluator gate、epoch 选择、以及是否坚持 E1 normalized-uptake 工程尺度还是另建论文参考区 SUV/SUVR 协议。后者是协议选择，不得用当前结果事后决定。

## E. 下一阶段 Full/OT ROI 验证的最小可执行建议

1. **冻结分析身份。** 不改 Full/OT cohort、两折、预测或 checkpoint；分析集预注册为 Full/OT 共同键与 E1 有效名单的交集（1,856 人；有效 FDG 1,597、AV45 1,364），端点先固定 epoch 165 或在启动前另行声明 epoch 165/200 的层级。
2. **先过 MRI 锚定空间门。** 对每个 PTID 比较 Full/OT 实际推理 cache 的 MRI array 与 E1 cache MRI；要求 shape 一致并给出 exact/max-abs 收据。通过后，给预测复制经验证的 E1 cache affine，抽样检查 mask overlay、左右物理质心，再做全队列 header/shape gate。任何 PET 相似度不得用于选择翻转或配准。
3. **保持冻结 ROI。** 主分析只使用 E1 `key_rois`、`physical_name` 与 `roi_validity`；不因 Full/OT 结果添加 `isthmuscingulate`、`supramarginal`、inferior/transverse temporal、pole 或其他 ROI。可在报告中把 paper-specific Missing 项作为未复现边界列出，而不是补选。
4. **复用一致性指标。** 对 Full 与 OT 分别计算逐 ROI real-vs-pred 的 MAE、bias、CCC、ICC(A,1)、LoA；以同受试者 Full--OT ROI absolute-error delta 作配对比较，并保留 complete-98 sensitivity。区域推断须预先定义 multiplicity；不要沿用历史独立样本 real-vs-synthetic t-test。
5. **明确强度协议。** 最小可执行版本沿用 E1 的 `[0,1] normalized uptake (arbitrary units)`，并明确它只是原论文区域评价任务的工程扩展、不是参考区 SUV/SUVR 复现。若目标要求严格复现正文 AV45 cerebellar-gray / FDG pons 归一化，应先独立确认参考标签、计算公式与输入尺度；FDG pons 在当前 98 标签资产中的可恢复性为 `UNVERIFIED`，未确认前不启动统计。

## DONE 判定

- **1. E1 关键 ROI 与原论文是否一致？** 类别层面基本一致；逐标签为“部分 Exact、部分 Approximate、部分 Missing”，不是完全一致。
- **2. 哪些可直接扩展？** FDG bilateral hippocampus、posterior cingulate；AV45 bilateral precuneus；以及 E1 已冻结且与 Fig. 3/4 同名的 rostral middle frontal、superior frontal、middle temporal、superior temporal。
- **3. 哪些不能等同？** TPJ 与 E1 三类子区只能近似；isthmus cingulate 绝不能等同 posterior cingulate；宽泛 frontal/temporal lobes 不能等同少数选定 parcel；未进冻结集的 supramarginal、inferior/transverse temporal、frontal/temporal pole 等不能补称为 E1 关键 ROI。
- **4. Full/OT 接入前还需确认什么？** 1,856 交集、MRI-anchored exact array/grid、可信 affine、左右物理名、epoch/统计层级，以及 normalized uptake 与正文参考区 SUV/SUVR 的协议边界。

