# DIRECTPP 论文材料归档

Agent 协作先读 [AGENTS.md](AGENTS.md)：按修稿入口检索，历史材料按需回查。[.rgignore](.rgignore) 收紧默认 ripgrep 检索范围，保留核心分析脚本；不改变 Git 跟踪或任何原文件位置。

主节点：`vscode-3003`。基准为冻结的 `manuscript/BMEF_main.tex`，不是对全部论文实验复现通过的认证。

**当前重心：回应 R2、R3 两位审稿人的意见与修稿。**先看[核心代码入口](CORE_CODE.md)、[完整审稿与修回要求索引](reports/source_reports/REVIEW_REQUIREMENTS.md)和[论文](manuscript/BMEF_main.tex)。原始材料为[R2 详细意见（Word）](reports/source_reports/BMEF_Reviewer_Report_English.docx)及[编辑回信与 R3 完整意见](reports/source_reports/raw_review.md)；Word 仅含 R2，不能作为全部审稿意见。另见[R2/R3 合并分析](reports/source_reports/DIReCTpp_Reviewer3_A1E585AEE7BF88E690_20261018.md)，其中风险判断和实验建议不代表已验证结论或新增实验授权。按作者说明采用生成器 **2-fold OOF → 分类器 3-fold** 的实验流程，two-fold 不是笔误；数据泄露专项追查到此结束。`source_archive` 默认忽略，仅保留核心代码与生成模型依赖对 Git 可见；检索、采集和转存辅助代码同样忽略，本地文件保留。

编辑回信记录修回截止日期为 **2026-11-04**，要求逐点回复、高亮修订稿、独立高清可编辑图件及作者签署材料等；完整清单见上述索引。审稿登记包括 R2 20 条、R3 15 条 Major Comments 和 21 条逐项编号的 Minor Comments；旧的 `reviewer_evidence_matrix_1_to_20.csv` 仅覆盖 R2。

| 目录 | 内容 |
|---|---|
| manuscript | 原论文、补充材料、参考文献、11图及已有PDF的冻结快照 |
| paper_index | 论文对应矩阵、21组生成/33组分类清单、原cell/行号、来源哈希与缺口 |
| source_archive | 按原服务器和原绝对路径组织的源码/表/日志原件；隐藏checkpoint版本和输出原样保留 |
| results | 原实验结果与派生结果入口；不将历史测试或后补统计改称主实验 |
| reports | 本次对应/完整性说明与有来源的历史报告 |
| data | 3003可读的原始源链接与复制校验后发布的资产；验证级别见transfer |
| appendix | 旧目录独有的后补恢复名单、修订/审计材料，不作为论文原实验依据 |
| transfer | 转存任务入口、manifest、后台进度/查询/恢复说明 |

历史材料需要回查时，使用[论文对应与缺口报告](reports/论文对应与缺口报告.md)、[协议记录](paper_index/protocol_conflicts.md)和[材料缺口](paper_index/gaps.md)。它们保留过去核查的上下文；后续工作范围以上述修稿入口及作者说明为准。

原代码没有修复，历史绝对路径可能失效，禁止直接照旧README重建划分或覆盖输出。AD/CN隐藏历史候选与顶层sMCI/pMCI测试已区分。1856/1主候选及旧500/39不得冒充独立测试；OASIS3候选548人/638session不得冒充论文419人。

前台文件复制、旧目录保留位置及后台状态见 [转存状态入口](transfer/STATUS.md) 和 `transfer/status.json`。大数据任务不依赖当前SSH；数据仍在复制时，本归档只交付前台成果与后台进度，不宣称全部转存完成。此次未启动研究实验，未选择论文最终权重，未修改论文。

R2/R3 审稿原文、编辑回信、合并分析与原投稿 cover letter 的来源及适用范围见 [评审材料说明](reports/source_reports/README.md)；原投稿 cover letter 不代表本次逐点回复已准备完成。旧目录独有材料见 [附录来源](appendix/legacy_only/README.md)及 `appendix/legacy_only/provenance.json`，均保留独立身份。论文15个冻结文件见 `paper_index/manuscript_freeze.json`。3014原始nohup.out因PermissionError未收录，保留缺口而不修改权限。

2026-10-17 作者沟通补充：**生成器采用两折交叉训练，为每个留出折生成 PET，合并为全队列 OOF 合成 PET，再用于三折分类。**这与论文数据部分的 two-fold 描述一致，作为后续修稿的实验协议。沟通记录见[作者实验流程说明](reports/author_protocol_clarification_20261017.md)。

生成器数据队列：共 1857 人，全部有 MRI；其中 1598 人有 FDG、1365 人有 AV45。

下游分类任务：已定位的 EMCI+LMCI/CN 分支有741个被试，代码先按诊断保留 EMCI、LMCI、CN，再筛选 MRI、FDG、AV45 能配对的对象。它是分类任务筛选后的队列。作者说明分类设计为3-fold；已恢复分支中重复使用同一划分的执行问题仍单独保留，不能仅凭设计说明认定其已正确执行三折。
