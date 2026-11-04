# DIReCT++ — Phase 2：56 条审稿意见覆盖与落实审计

- **论文**：BMEF-D-26-00169；DIReCT++
- **审核日期**：2026-11-04
- **基准版本**：本地交付记录 `main` / `27ffbc525e9b8fa47573899fdcdef1b330bd9325`（本阶段未在线验证 GitHub）
- **输入**：6 个本地 ZIP、最终 Rebuttal PDF (68 页)、Clean Manuscript PDF (26 页)、Standalone Supplementary PDF (27 页)、Combined Reference PDF (54 页)、终版 TeX 与 Notion 导出。
- **权限**：只读；没有修改论文、Rebuttal、图表或 Git/Notion。

## 1. 总结

**阶段判定：REVIEW（回复覆盖通过，定位与提交措辞仍有小范围问题）。**

- **56/56 审稿编号**在最终 Rebuttal PDF 中均有独立条目：R2 20/20、R3 Major 15/15、R3 Minor 21/21。
- 终版 LaTeX 中对应 **56/56 `\revcomment`、56/56 `\response` 和 56/56 `\actiontaken`**；R2-1/R2-2 属正面评价，说明无需专门修改。
- **56/56** 均有独立的最终英文回复源文件；对照已集成的 Rebuttal 源文本，未发现整条英文回复遗漏。文本规范化相似度最低约 0.93；差异主要来自 LaTeX/BibTeX 引用表示方法。
- **190/190** 处明确给出的主稿 `(p. N, lines X--Y)` 已在实际 PDF 指定页找到起始行号（含 8 处参考书目引用，使用 54 页 Combined Reference PDF）。
- **43/43** 处 `Revised Text in Manuscript` 的开头语句在终版主稿 LaTeX 中可定位：35 处经空格/简单命令规范化后整体匹配，另 8 处因引用写法（`Fig.~4` 对 `Fig.~\ref{fig:4}`、`Table~S1` 对 `Table~\ref{...}`）非完整逐字匹配；定位的文本实质相同。
- **48** 处 Supplementary 页码引用均在有效页范围内，但部分页码错误或只指向跨页材料的起始位置，必须修订。
- Rebuttal 中 **18 个独立 `\cite` 引用键**均能在本地 `rebuttal/references.bib` 中找到对应文献条目。

上述结果证明**回答和文稿修改可追溯**，但不等于 56 条的实验事实、统计结论或每个图件已通过独立科学核验。后者是 Phase 3/4。

## 2. P1 — 明确的补充材料页码定位问题

在 `rebuttal/sections/02_reviewer2.tex`、`03_reviewer3_major.tex` 的相应 `\actiontaken` 段落中，存在由自动整合生成的粗粒度页码/错误定位。核对对象是交付的独立 Supplementary PDF 与 Combined Reference PDF，非推测。

| 位置类型 / 关联意见 | Rebuttal 当前引用 | 实际页码（独立补充 PDF；合并参考 PDF） | 建议 |
|---|---|---|---|
| `tab:clinical_missingness`：R2-5、R3-1、R3-2、R3-13 | Supplementary p.8；Combined p.32 | **p.9；p.32** | 改独立补充页码为 9 |
| `tab:regional_agreement; tab:regional_effect_sizes`：R2-8、R2-9、R2-10、R3-4、R3-5 | p.11；p.35（同时指两表） | **p.11–12；p.35–36** | 为两张表分别列出页码或范围 |
| `Supplementary classification tables and ROC`：R2-11、R2-12、R3-1、R3-7、R3-11 | p.17；p.41 | **表从 p.19 起，ROC 为 p.26；合并版从 p.43 起，ROC 为 p.50** | 改为 p.19–26 / p.43–50，或者列出表 S13–S16 与 Figure S9 |
| `Supplementary generation tables and cases`：R2-17、R3-9、R3-10、R3-11、R3-12 | p.12；p.36 | **生成表 p.13–16、案例 p.17–18；合并版 p.37–40、p.41–42** | 分别定位 Table S9–S12、Figure S7–S8 |
| `Supplementary clinical score sensitivity and demographic stratification`：R2-5、R2-16、R3-1 | p.26；p.50 | **敏感性 p.26；人口分层 p.27；合并版 p.50–51** | 改为 p.26–27 / p.50–51 |

受上述至少一类页码不精确问题影响的审稿编号共有 **18 个**（部分交叉重叠），但不代表这些意见中的实际修改缺失。主稿页/行引用目前检查结果良好。这一项是 **P1：建议投稿前统一修正回复信定位信息**。

## 3. P1 — M15 数据划分/受试者与影像 ID 提供状态未闭环

- **原始诉求**：Minor-15 要求 Data Availability 包含 FDG-PET，并提供 ADNI/OASIS 的 subject/image IDs 以支持精确复现。
- **已经落实**：主稿 `manuscript/BMEF_main.tex` 的 `Data Availability` 明确列出 ADNI 的 T1 MRI、FDG 和 AV45，以及 OASIS-3 的 AV45；正文/补充复现性表列出了两折生成划分、三折分类、样本量及种子。
- **仍需作者确认**：M15 最终英文回复采用 `We will organize ... and make them available to the extent permitted ...`；主稿仅说 fixed split records/source manifests were retained，并说明共享 ID 受到数据协议约束。本轮交付材料不足以证明投稿时已经对审稿人提供准确的 subject/image ID 列表，也不足以证明数据使用协议许可公开。
- **建议**：作者判断能提供哪些已验证的 ID/划分记录（例如仅对获授权研究者的受限共享），以及不能共享的具体理由；然后让回复、Data Availability 与实际提供材料保持一致。**不可凭推测创建历史影像 ID。**
- **判定**：P1 / REVIEW（不是声称完全没有记录，也不是要求违规公开受限信息）。

## 4. P2 — 最终英文回复仍有“将来修改正文”的历史时态

以下至少 **13 条**在终版回复中仍包含关于**本次已完成正文修改**的 `we will...`，容易让编辑认为部分改动尚未实施：

`R2-4, R2-8, R2-9, R2-10, R2-12, R2-14, R2-20, R3-2, R3-12, R3-15, M6, M7, M9`。

实证例子：

- R2-9 称 “we will explicitly report the statistical families”；终稿 Methods 已写明 **12 个 paired families（1,176 tests）+4 个 AD–CN families（392 tests）**。
- R2-10 称 “we will expand” 16 个 ROI 的 regression slope/intercept；终稿的 `manuscript/supplementary/tables/regional_agreement.tex` 已包含对应列和 95% CI。
- R3-12 称 “We will explicitly acknowledge” deterministic one-step uncertainty；终稿 Discussion 已有专门限制说明。
- M9 称 “will correct Billot C to Billot B”；终版 BibTeX `synthseg` 的第一作者已为 `Billot, Benjamin`。

这些目前是 **P2 编辑一致性问题**，不是科学实验遗漏；建议逐条把已完成改动改为 `we have / we now / the revised manuscript ...`，同时保留未来研究规划的将来时。`M20` 在投稿系统提交时才实际完成，使用将来时合理，不应误改为已完成。`R3-8 / R3-13` 的一般性未来表述不视为明确未落实承诺。

## 5. 需要在提交步骤核对的非正文事项

- **M20：投稿系统摘要清除原始 LaTeX。** 包内存在 `revision_workspace/delivery/01_submission/submission_abstract.txt`，并经 Phase 1 确认没有常见正文 LaTeX 控制序列；但最终粘贴到 Editorial Manager 后是否正确显示，无法从 ZIP 验证。此项仅需作者提交时核对，不应判断为已完成的系统操作。
- **Figure 1 图例（M17）**：独立 `figure_1.pdf` 的可提取文字出现 `Residual addition`，未出现 `Just Add It`，与回复一致；图形全视觉验收仍留给 Phase 4。
- **R3-12**：回复列举的 SSIM 0.9211/0.8844（Full FDG/AV45）和 0.9003/0.8604（ClinicalUNet FDG/AV45），可在终稿 `manuscript/supplementary/tables/whole_volume_generation.tex` 找到对应四舍五入的原始汇总值。这仅核对**表与回复一致**，尚未独立核实实验计算过程。
- **R2-3 / R2-19 等**：两折生成和三折分类的分工在 Methods 与 Supplementary reproducibility table 均有相应文本；历史分类 Syn-PET 输入与重建 Full checkpoint 未建立直接绑定的限制也在正文写明。本阶段只验证该限制被如实披露，不评价原始数据划分有效性。

## 6. 审核方法、覆盖与尚未验证项目

1. 从 6 个 ZIP 中只提取并逐字节读取审计所需的最终 `.tex`、`.md`、补充表源文件和对应 PDF。所生成的中间文本/索引位于本地 `_BMEF_phase2/`，未写回任何原始稿件或仓库。
2. 逐条解析 56 个 Rebuttal 子章节，验证各自 reviewer comment、英文 response、Action in Manuscript 是否齐备；并核实 56 个标题在最终 68 页 PDF 中出现。
3. 将 56 条回复与 `revision_workspace/integration/responses/<ID>.final.md` 对照，定位每条实际纳入的版本；同时核查 43 处 revised text 摘录与最终 TeX 文字。
4. 根据交付 PDF 中可见的行号逐项核对 **190** 个主稿位置，单独核对补充 PDF 的 48 个位置和相关 S 表、S 图实际起始页。
5. 未重新编译 LaTeX，未独立运行统计/复现实验，未对图表进行完整视觉复核，未验证 Editorial Manager 后台状态；这些不是 Phase 2 的 PASS 范围。
6. 读取限制说明：个别超长资料在终端直接预览时显示被截断，但源文件完整可用；全部 56 条回复、190 条主文页行坐标及 48 条补充页码由本地脚本处理了完整文本，并未以截断的终端预览作最终覆盖依据。科学原始 ROI 等大数据文件的完整内容仍留至 Phase 3/4 核验。

## 7. 阶段结论与作者决策点

**覆盖性：PASS（56/56）。** **回复—正文可追溯性：PASS（主文 190/190 定位）/ REVIEW（补充材料页码）**。**科学和统计真实性：NOT VERIFIED（待 Phase 3）**。

当前未发现整条审稿意见遗漏或“声称增加了表/图而所指材料完全不存在”的证据。提交前建议优先修正补充定位和 M15 提供策略；时态可统一编辑。若用户认可本阶段结论，再进入 Phase 3 科学与实验一致性审核；本阶段不进行任何修稿实施。
