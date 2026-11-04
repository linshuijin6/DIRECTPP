# DIReCT++ 最终返稿本地整合计划

稿件 BMEF-D-26-00169；本次只完成资料索引与计划。源材料只读，未修改论文、Rebuttal、图表或补充材料，未启动训练/推理、提交或推送。编辑信记录截止日期 2026-11-04，未给出具体时区/时刻；见 [编辑要求](../reports/source_reports/REVIEW_REQUIREMENTS.md)。

## 1. 本轮结论与入口

- [COMMENT_INDEX](index/COMMENT_INDEX.md)：56 条意见、标题、原文范围、完整英文 Response 范围及组映射。R2 20、R3 Major 15、Minor 21；M1–M21 对应原登记 R3-minor-01–21。
- [REVISION_INDEX](index/REVISION_INDEX.md)：123 个 Original/Revised 候选和17个新增材料入口；原文继续保存在导出文件，避免大文件复制。
- [GROUP_INDEX](index/GROUP_INDEX.md)：G1–G8 的原分组、正文/图表位置与合并入口。
- [SOURCE_MANIFEST](index/SOURCE_MANIFEST.md)：全部25个导出文件及哈希；24 Markdown、1 PDF，没有独立图片文件。28条本地链接可解析，无缺失路径；16条外部链接仅登记。
- [INTEGRITY_REPORT](index/INTEGRITY_REPORT.md)：版本继承、重叠、空页、英文错配及尚未核实的事实。
- [repository_assets.json](index/repository_assets.json) 和 [repository_checks.json](index/repository_checks.json)：67项稿件、图源、实验入口及报告的文件身份与本地检查快照。

**替换文件后，56条意见均有对应英文回复入口，未发现重复英文。** R3-9 消融英文已补齐（L25–39），并新增三处正文方案；其L23声明英文按已确认中文方向整理，未能逐字恢复历史英文定稿，须保留此来源身份。R3-14已补四处Discussion方案及引文提案，旧空页缺口关闭。索引收录不等于正式正文已实施或所有科学主张已通过验证；替换前索引保存在history/快照。7处新增Original均已与当前主稿源码匹配，R3-9三处Revised与G5三处同文；候选编号变更映射及新旧源哈希见 [更新收据](index/SOURCE_UPDATE_R3_9_R3_14.json)。

## 2. 已核实的仓库状态

基线 HEAD 为 `55567213e9286871314952c9716324aa86249e0c`。任务开始 `git status --short` 仅显示未跟踪的 `rebuttal/BMEF_from_notion/`，无已跟踪文件修改。本轮新增仅在 `revision_workspace/`。后续执行前重新核对状态，保留期间新增的用户修改；不自动提交或推送。

| 材料 | 已核实入口 | 实施含义 |
| --- | --- | --- |
| 正文 | `manuscript/BMEF_main.tex`；约400行；仍含 Prognostic Stratification、旧指标及SUV等表述 | 不能把已有PDF当作本轮修订稿；按段落/label匹配，不依赖旧行号 |
| BibTeX | 正文42条、Rebuttal48条；未发现重复key或当前源码缺失引用key | 不等于无重复文献或文献事实正确；落实M8–M14，核对新引文 |
| Figure 1–5 | `manuscript/figures/figure_1.pdf` 至 `figure_5.pdf`；另有 `revised-1029-FIG1.pdf` | 当前源码仍引用figure_1，未自动使用修订候选 |
| 可编辑图源 | `manuscript/raw_pic/1103.drawio`、`图表.rectified.pptx`、`图表2.pptx` | 文件存在不证明每张最终图与之对应，需逐图核对 |
| Supplementary | `manuscript/supplementary/supplementary.tex`，6张补充图、3张表，主稿直接input | 保留已有资产；统一新增编号及必要宏包，不能直接粘贴拟定input路径 |
| Rebuttal | `rebuttal/main.tex`、`sections/00`至`04`、独立references.bib、现有PDF | 已有56条意见入口（Minor使用minorcomment宏），需逐条比对本轮来源；含审计备注、重复修改和未经材料实证的完成式句子 |
| 历史转换脚本 | `rebuttal/build_rebuttal_skeleton.py`、`apply_response_details.py`；旧Markdown详情 | 只作现有实现线索，不直接运行覆盖；Notion本次完整导出为回复来源 |
| 构建工具 | pdflatex、bibtex、pdfinfo可用；biber、latexmk、latexdiff未在PATH发现 | 正文使用biblatex/nejm，需先准备匹配的biber环境；不要为省事改引用体系。Rebuttal使用BibTeX |

现有 Rebuttal 的 Introduction 修改片段还出现 `\~\\cite` 等可疑转换结果；条目数量和既有PDF不能认证转换正确。EDITOR回复中的“all requirements ... complied”须在实际文件及签署材料核对后才可保留。

## 3. 下一轮执行次序与位置唯一性

先建立 `revision_workspace/integration/position_registry.csv`（下轮生成）：每行是一个最终正文位置，字段为 `position_id, target_file, section_or_label, original_anchor_sha256, source_candidates, related_comments, groups, final_text_path, evidence_paths, decision_basis, status`。一条意见可关联多行，一行只能有一个最终文本。候选筛选不能按页面顺序或修改时间。

统一依赖顺序为：**锁定来源及缺口 → G8/G2 → G1 → G3/G4/G5 → G6 → G7 → 全局Minor/引文/编号 → Rebuttal回填 → 构建和交付核验**。G8先明确临床字段来源；G2明确队列/折身份；G7最后统一所有科学主张。共享位置即使跨组，也只写入一次。

| 顺序 | 组 | 统一工作与具体位置 | 完成判据 |
| --- | --- | --- | --- |
| 0 | 来源更新（已完成） | 两个替换文件哈希与内容已核对；R3-9英文及三处方案、R3-14四处方案已收录 | R3-9保留非历史逐字稿说明；采用新来源，随后核对实际执行细节 |
| 1 | G8 | Methods临床段、Table S1、Discussion填补局限；读取R3-2子页与11月3日恢复报告 | observed/filled、逐字段缺失率、诊断条件模拟及统计展示一致；不把填补后分布作为独立临床验证 |
| 2 | G2 | Methods数据选择/预处理、2-fold OOF→独立3-fold、Data Availability、M15 | 区分历史与新实验；任务人数、模态、split/seed/epoch可溯源；不虚构MRI–PET时差 |
| 3 | G1 | Results L88、Figure1/Eq1、Methods VLM/prompt/token/cross-attention | R3-8明确替代旧prompt段，保留R2-14的维度/优化细节；0.82是软惩罚目标；结合M16 |
| 4a | G3 | Figure2及图注、Results生成比较、Comparison Methods、图像指标和补充表 | 分开历史汇总、新whole-volume、新masked；条件/预算差异和不利结果如实呈现 |
| 4b | G4 | Results L119/134/136/138、Figure3/4图注、统计方法、两张区域表及S1–S6图注 | 以集中核心和明确继承为入口；并入M3/5/6/7/13/18/19；原ROI输入严格用shuijin指定版 |
| 4c | G5 | Figure5、分类Results/Methods及临床对照、ROC和表格 | 对照81 fit已完成结果；不能写三个任务均改善或Syn优于clinical；G5子页三项不替代完整结果整合 |
| 5 | G6 | Methods单步/蒸馏/实现、效率、Discussion确定性与不确定性 | 单次forward一个tracer；学习的一步近似；测时范围、硬件、参数和显存明确；FLOPs/138GPUh缺口保留 |
| 6 | G7 | 标题、摘要、Introduction、Discussion/Conclusion、PDF元数据 | 全文统一MCI stage discrimination；仅AV45外部CN/AD范围；保留临床量化/前瞻/填补/确定性局限 |
| 7 | 全局 | M1–M21、BibTeX、图表编号和交叉引用 | Minor逐项验收；两个bib各自key一致，无破损转换和孤立引用 |
| 8 | 回复与交付 | Rebuttal、clean/highlight稿、补充材料和独立图件 | 每句“已修改”绑定实际最终位置及交付文件，最后统一页码/行号 |

共享位置必须显式合并：L119（G4/M3/M7）、L134/138（G4/M18）、L229–241（R2-14/15、M16）、L263（R3-8/M16）、L297（G2/G8）、L342（G5/R3-3）、L347（G1/G2/G6/M16）、L186（G4/G6/G7/G8）。所有行号是当前原稿导航；最终登记用源码锚点。

## 4. 可复用的修订实验证据与适用边界

下表“完成”指本地报告、结果与完成收据记录，不是本轮重跑或独立重算全部科学统计。下轮只核对将被写入论文的具体数字、模型/目标身份和引用，不重新做全库泄露追查。

| 证据入口 | 已有产物 / 当前可核实状态 | 整合限制 |
| --- | --- | --- |
| `reports/revision_evidence_night_20261102/completion.json`、G1–G7/REPORT.md | 完成可行授权范围、复用81分类fit、Single e165四个fold/tracer结果；23组内部表草稿 | G8的OUT_OF_SCOPE只适用于该历史任务，不免除本次G8整理；不能把全部草稿发布为正式Supplement |
| `reports/original_author_reproduction_20261020/`；`experiments/original_author_reproduction/README.md` | 本轮作者语义重建Full两折，165为主终点、200另记 | 不等于历史原论文运行身份，不混入E1 Full |
| G1/REPORT.md、`experiments/r2_15_tau_adapter_ablation/` | 10组表示层τ/adapter结果、运行级token响应 | 不等于生成质量τ优化或VLM独立因果获益；原始余弦相近不能证明当时选值动机 |
| G1_E1/REPORT.md、E1实验入口 | 固定权重评分移除分析 | 推理条件干预不等于从头重训的No-Scores消融 |
| G3/REPORT.md、paired_comparisons.csv | Full/Clinical U-Net/SwinUNETR/TabularMLP/TracerOnly/Single的独立证据及40项比较 | 指标依赖、训练终点/信息不同；部分对照优于Full，保留不利结果 |
| `reports/r3_11_brain_mask_metrics/run_20261102/` | completion为COMPLETE；8883行指标、16项比较；FDG1597/AV451364 | SynthSeg非零标签并集含CSF/脑室；SSIM仅完整7³窗口；不是纯实质mask；Full/Clinical e165、Swin e200；各比较8项Holm族 |
| `reports/r2_8_original_roi_stats/`、`r2_10_normalized_calibration/`、`r3_5_effect_size/` | 原作者指定shuijin ROI复算、一致性/OLS、AD–CN效应量 | 历史ROI证据不能与新生成模型/病例图混同；normalized uptake，不做TOST/临床Aβ状态外推 |
| `reports/r2_11_classification_3fold/final_summary/` | 63/63正式200epoch影像fit；3任务×7条件×3折 | 原顶层REPORT尚有旧试跑/运行中记录，不能用其阶段标签代替最终收据 |
| 同目录 `statistical_comparison/` | 既有5000次条件bootstrap、18项逐折DeLong、mean±sample SD | CI与SD不同；逐折p不能平均成总体p；旧原始p与夜间新增Holm输出需标明各自协议 |
| 夜间G5/REPORT.md | 18/18临床fit；共81fit/27配置；临床CI、比较、三任务ROC | N=470/741/436；MCI=EMCI+LMCI；MCI-U排除；影像分类保留既有QC个体，不套用masked队列排除 |
| 夜间G6/REPORT.md | RTX4090 FP32、每tracer预热10/计时50；约0.251s | 仅生成forward；不含文本编码/I/O/预处理；不能宣称全链路延迟、基线速度排行或历史138GPUh已认证 |
| 夜间`R3_11_final_figures/` | 两张最终综合病例PNG/PDF及manifest、冻结选例和核验记录 | 以whole-volume SSIM选median/P10/worst QC-passed，不能说按masked排名；内部PTID不直接进入投稿表 |
| 11月3日 `filtering_code_recovery_20261103/` | 找回session373筛选/填补代码，1857人逐项核对 | 原表首行不等于最早/最近/基线影像；临床源Image ID不等于实际NIfTI身份 |
| 11月3日 `metadata_1103_review/` | 1749条详细XML，含MRI1147/PET602 | 可计算实际MRI–PET配对为0（缺成对记录，不是0天）；1条AV45/FBB元数据冲突，不能推断项目用了FBB |

旧README、主页面后半段“任务清单/六组/尚未决定”保留为历史讨论，不优先于本轮G1–G8及真实结果。缺失证据允许以收紧结论回应，不自动启动新增耗时实验。

## 5. Figure 1–5、补充图与表

| 图件 | 已有来源 | 最终工作 / 验收 |
| --- | --- | --- |
| Figure1 | 原figure_1、revised-1029-FIG1、drawio/PPTX候选 | 逐面板对应实际网络；冻结encoder/affine adapter、α/β与Eq1统一；Just Add It改为Residual Addition；核实单tracer输出及cross-attention层位置 |
| Figure2 | 原figure_2；G4页修改11–15；G7/historical84_values.csv、S-N20 | 历史绝对汇总与新实验分开；原OASIS仅AV45；新配对/brain-mask结果在独立表，不能给旧模型汇总补造SD/CI；弱化全面优胜 |
| Figure3 | 原figure_3；G4术语与M7 | normalized uptake、min–max及atlas名称一致；保留两例身份范围，不把病例图当总体一致性 |
| Figure4 | 原figure_4；G4集中核心/修改16；ROI统计三套报告 | 8ROI×2 tracer一致性与20ROI疾病对比分开；轴arbitrary units，更新图注/阈值；M18解释为何C–F是AD/CN；源文件未完全恢复时用已确认数据可复现重绘并记录来源，不声称历史完全同一 |
| Figure5 | 原figure_5；分类final_summary、夜间G5统计和ROC | 按新三折mean±SD及明确CI重建，覆盖临床基线；每任务/指标如实陈述，不沿用旧全面改善；区分ROC逐点带与AUC区间 |
| 原Supplementary Figures S1–S6 | manuscript/figures/supplementary_figure_*.pdf；G4修改17 | 保留编号/用途，统一normalized uptake、真实归一化与图轴，检查旧SUV/参考区残留 |
| 新病例图 | 夜间R3_11_final_figures/figure_manifest.json | 采用最终两张综合FDG/AV45图，保留4800×4160/400dpi及PDF；逐图核验选例规则、误差色标/单位与匿名标签，旧G3_cases仅作历史线索 |
| 新ROC/τ图 | 夜间figures/G5_ROC_*、G1_tau_sensitivity_reused.png | ROC放补充且主文引用；τ注明表示层分析；不重复插入同图 |

正式补充表按唯一label先组织，再分配连续编号：

| 表 | 来源 / 内容 | 取舍原则 |
| --- | --- | --- |
| 现有Table S1 | R3-2子页+筛选恢复报告；ADNI人口学/评分、缺失与填补说明 | 源数据可溯源后更新；不凭高性能删除填补局限 |
| 现有OASIS/软件表 | 原supplementary及R3-13、G2 | 队列/年龄/字段缺口与软件实际环境一致 |
| 区域一致性表 `tab:regional_agreement` | R2-10完整16行；补齐CCC/ICC/BA/OLS及CI、p/q | 对应Figure4A/B；不擅自发布196或1176行内部表 |
| 区域疾病效应表 `tab:regional_effect_sizes` | G4 20行、r3_5_effect_size CSV | 对应C–F；补ROI名称/N及real/syn d/q；不把效应差当临床等效 |
| 新生成/配对表 | S-N01/03；masked独立summary/paired tex | 按whole-volume/masked分开；保留协议、N/epoch/比较族；不要把24行long格式当24模型 |
| 新分类表 | S-N13/14/15/16和正式CSV | 27配置五指标、影像和临床差值、逐折DeLong；可按主题拆表，保留未校正与Holm各列含义 |
| 机制/效率/划分 | S-N17/18/19/21/22/23 | 选择满足意见的精简展示，保留完整来源；不是所有内部表均须投稿 |
| 历史Figure2绝对值 | S-N20 | 如主文已纳入则避免重复；没有逐人数据的历史模型不补造统计 |

内部S-N01–23为草稿编号，不直接等于投稿Table S1–S23。具体表格入口见 [原草稿表索引](../reports/revision_evidence_night_20261102/SUPPLEMENTARY_TABLE_INDEX.md)。G4已明确只投稿精简历史ROI两表；夜间S-N06–12等大表留内部，除非后续作者明确改变展示范围。敏感标识和路径仅用于内部溯源，不直接复制入公开补充材料。

## 6. Reviewer Response 与正文双向对应

下一轮在 `integration/comment_position_map.csv` 建立56行以上的关联表：`comment_id, response_source/range/hash, position_id, evidence_file, manuscript_label, final_page_lines, disposition`。从COMMENT_INDEX可查每条意见的组及来源；反向由position_registry查全部意见。致谢或无需改正文的条目（如R2-1/2）明确记为no_change及理由；M20对应投稿系统摘要纯文本，无本地正文强制改动。

Rebuttal只引用已经实施的最终版本。先完成正文、图表和补充材料，再统一替换旧actiontaken/changedtext并回填最终页码；不把多个旧Revised全部作为“已完成变更”列入。保留每条英文回复，不把同组多条意见缩成一条。作者确认的科学立场不自动改写；与新证据不一致的执行细节列出待确认差异并给出有依据的修订候选。

R3-9正文要求可分布在G1/G3/G5/G6，不能因某一组有结果就宣告七项消融全部完成。R3-14子页L19/37/55/73给出四处Revised，L43明确以回复立场纠正R2-20旧方案的widespread screening；按明确继承关系合并。L73仅为Limitations插入两句，不覆盖其他组要求。jack2024revised位于L86–95，尚未写入引用库；正式新增/修改2024 criteria、p-tau217引文时核对原论文/官方资料。R3-14中comparable等表述仍须与新G5的统计边界一致，不据缺口关闭自动认证等效性。

## 7. 下一轮自动整合的检查点

1. **输入冻结**：用本轮source_manifest逐文件复核；新增来源保存新哈希/差异，不覆盖原导出。检查git，先备份或独立派生构建目录，记录源稿/Bib/图件身份。
2. **版本合并**：逐位置生成最终文本及说明。明确继承的旧候选标superseded；不同要求的非互斥补充标merged；真实科学冲突保留unresolved，不凭日期裁定。
3. **数字核对**：所有论文数字/图表单元匹配CSV、cohort、fold、checkpoint、epoch、mask/target协议；只做所用值的定向核对，不无理由重算整库。区分arbitrary units/dB/%/百分点，CI/SD/LoA，BH/Holm族。
4. **引用和图件**：落实M8–M14；查重复文献而非仅重复key；核对Billot、SynthSeg、SPM、FDG ROI、DDIM/MONAI。外部文献事实需原始出版物依据。逐图检查文字、面板、单位、色标和可编辑源。
5. **构建**：准备biber后正文pdflatex→biber→pdflatex两遍；Rebuttal pdflatex→bibtex→pdflatex两遍，均在独立build目录输出。按新增表选择longtable/pdflscape等必要宏包。检查未定义引用、缺图、overfull和PDF裁切；实际打开图表与分页。
6. **全文一致性**：标题/摘要/元数据统一；禁止无依据prognosis、exact ODE、SUVR、临床替代、所有任务优胜；允许在方法/局限中准确讨论未完成项目。全文检查不是机械删除关键词。
7. **双向验收**：56条均有正确英文回复；每项改变有唯一最终位置和证据，正文每个变更可反查意见或必要一致性修正。R3-9旧错配、R3-14旧空页已关闭；继续保留R3-9重建来源限定，核对全部回复的计划式/完成式与实际证据一致；真实冲突清零或明确交由作者处理且不宣告可提交。
8. **最终包**：clean稿、独立高亮稿、Rebuttal、Supplementary、Figure1–5及新增补充图高清文件和可编辑源、投稿摘要纯文本、交付manifest/哈希。高亮可使用核验后的派生差异工具；latexdiff目前缺失，不借此改动冻结稿。

编辑事项独立验收：全体作者License/COI签署、适用的复用图授权和作者变更表、系统额外附件是否取得。当前未核实这些材料，不可用模板的“已全部满足”代替。系统提交、签署、对外消息和推送均不属于本轮计划任务的实际执行。

## 8. 后续Goal任务的可执行起点与停止条件

后续Goal可先读本计划、INTEGRITY_REPORT和comment_index.json，再按position_registry逐位置整合。两个替换文件已补齐旧内容缺口，无需继续等待原先缺失文件。R3-9的三处正文与G5集中页同文，作为重复来源只合并一次；其英文仍含propose/prioritize等计划措辞和历史138GPUh描述，按已完成证据定向核对，不自动启动新实验。R3-14与R2-20共享Discussion位置，遵守子页明示的修正与保留范围。

允许自动继续的是本地来源定位、差异生成、已明确方案合并、定向核对和派生构建。不得静默更换队列、split、归一化、checkpoint/终点或选择有利统计；不得把未覆盖实验伪装完成；新增耗时实验先只读确认范围与资源方案。完成工程整合不等于科学结论自动通过，最终是否可提交取决于正文整合、回复来源与执行事实一致性、统计/主张一致性和编辑材料验收。
