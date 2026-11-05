# Stage 4 最终一致性与交付报告

起点：main，Stage 3 `45202545b638845b31fd0dadabd089ad958766d5`，初始工作树干净。本阶段只修复引文/定位、同步生成链并构建交付；科学正文、Supplementary、参考文献和图件源码均未修改。未执行训练、推理、统计重算或在线投稿。

## A. changedtext 与 Action 核查

M1/M2 共用的旧引文（不是相应拼写修正的证据）：

```text
Generative artificial intelligence (AI) offers a transformative pathway to bridge this clinical gap by synthesizing PET biomarkers from routinely acquired MRI~\cite{dayarathna2024deep,lee2024synthesizing}.
```

M1/M2 共用的新引文（完整保留当前正文句子及引用）：

```text
This challenge stems from the inherent nature of MRI-to-PET synthesis as an ill-posed inverse problem; neurodegeneration visible on MRI is typically a downstream effect of prior molecular pathologies captured by PET~\cite{jagust2018imaging}.
```

位置：`manuscript/BMEF_main.tex:83`；生成后的 `rebuttal/sections/04_reviewer3_minor.tex` 中 M1/M2。实际 Combined Reference Copy 第2页；匹配短语位于打印行60–61，行号仅表示定位短语，不能代表整句范围。Rebuttal 第52页显示两条引文。

全部56条回复已核查：43条已有引文中39条改选更直接对应意见的当前原句、4条保留；13条仍不新增引文。没有按登记片段首句自动认定对应关系。每条 Original/Revised、意见相关性、登记位置、源码行号和实际PDF短语证据见 `stage4_alignment_audit.json`、`rebuttal_excerpt_selections.json`、`quotation_pdf_locations.json`。

| 意见 | 引文核查结果 | 当前正文位置 | 实际 Combined 页码 |
| --- | --- | --- | --- |
| R2-3 | 保留 | G2-OOF-PROTOCOL | 18 |
| R2-4 | 修正引文选择 | G2-MCI-DEFINITIONS | 18 |
| R2-5 | 修正引文选择 | G1-RESULTS-CONDITIONING | 3 |
| R2-6 | 修正引文选择 | G2-COHORT-SELECTION | 17 |
| R2-7 | 修正引文选择 | G2-OASIS-SCOPE | 18 |
| R2-8 | 修正引文选择 | G4-CORE-3 | 9 |
| R2-9 | 修正引文选择 | G4-CORE-7 | 21 |
| R2-10 | 修正引文选择 | G4-CORE-5 | 21 |
| R2-13 | 修正引文选择 | G6-ONE-STEP-IMPLEMENTATION | 17 |
| R2-14 | 保留 | G1-RESULTS-CONDITIONING | 3 |
| R2-15 | 修正引文选择 | G1-ADAPTER-OBJECTIVE | 15 |
| R2-16 | 修正引文选择 | G5-CLASSIFICATION-METHODS | 22 |
| R2-17 | 修正引文选择 | G3-IMAGE-QUALITY-METHODS | 19 |
| R2-19 | 修正引文选择 | G2-OOF-PROTOCOL | 19 |
| R2-20 | 修正引文选择 | G7-DISCUSSION-MERGED | 13 |
| R3-1 | 修正引文选择 | G5-RESULTS-AND-FIGURE5 | 11 |
| R3-2 | 修正引文选择 | G8-CLINICAL-METHODS | 18 |
| R3-3 | 修正引文选择 | G2-MCI-DEFINITIONS | 18 |
| R3-4 | 修正引文选择 | G4-CORE-3 | 9 |
| R3-5 | 修正引文选择 | G4-CORE-1 | 6 |
| R3-6 | 修正引文选择 | G2-OOF-PROTOCOL | 19 |
| R3-7 | 修正引文选择 | G5-RESULTS-AND-FIGURE5 | 9 |
| R3-8 | 保留 | G1-RESULTS-CONDITIONING | 3 |
| R3-9 | 修正引文选择 | G3-IMAGE-QUALITY-METHODS | 19, 20 |
| R3-10 | 修正引文选择 | G3-IMAGE-QUALITY-METHODS | 19 |
| R3-12 | 修正引文选择 | G6-ONE-STEP-IMPLEMENTATION | 17 |
| R3-13 | 修正引文选择 | G2-OASIS-SCOPE | 18 |
| R3-14 | 修正引文选择 | G7-DISCUSSION-MERGED | 13, 14 |
| R3-15 | 修正引文选择 | G7-INTRODUCTION-CONTRIBUTIONS | 2 |
| M1 | 修正引文选择 | G7-INTRODUCTION-GRAMMAR | 2 |
| M2 | 修正引文选择 | G7-INTRODUCTION-GRAMMAR | 2 |
| M3 | 修正引文选择 | G4-CORE-1 | 6 |
| M4 | 修正引文选择 | G1-VELOCITY-NOTATION | 15 |
| M5 | 修正引文选择 | G4-CORE-5 | 20 |
| M6 | 修正引文选择 | G4-ROI-NAMES | 20 |
| M7 | 修正引文选择 | G4-CORE-1 | 6 |
| M12 | 修正引文选择 | G2-PREPROCESSING | 18 |
| M13 | 修正引文选择 | G4-ROI-NAMES | 20 |
| M14 | 修正引文选择 | G3-DDIM-REFERENCE | 19 |
| M15 | 修正引文选择 | G2-DATA-AVAILABILITY | 24 |
| M16 | 修正引文选择 | G6-IMPLEMENTATION-AND-EFFICIENCY | 22 |
| M18 | 修正引文选择 | G4-CORE-4 | 9 |
| M21 | 保留 | G1-RESULTS-CONDITIONING | 3 |

其余13条无 changedtext 的回复也核查了 Response 与 Action 对应关系。Action 根据现有登记关联及实际PDF位置重新生成；长片段保留多页位置，独立Supplementary位置单独获取，不按统一偏移推断。

另有一处纯定位/标签誊写修正：M19 的实际 Figure4 已采用横向 uptake 轴，且图中文字为 “Normalized uptake (a.u.)”。从生成源同步下面一句，不改图件或科学结论：

```text
To address this concern, we have revised the vertical axis labels in Figure 4 and the corresponding supplementary figures to “Normalized Regional Uptake (a.u.)”.
```

```text
To address this concern, we have revised the uptake axis labels in Figure 4 and the corresponding supplementary figures to “Normalized uptake (a.u.)”.
```

其余55条 Response 正文、全部10条编辑回复及56+10条原始意见完全保留。没有待确认的新科学立场变化；原有科学证据缺口继续保留。

## B. 构建与位置映射

沿用已有脚本顺序：build_manuscript.sh → prepare_variants.py → build_variants.sh；按实际PDF定位运行 map_final_locations.py → build_rebuttal.py → build_rebuttal.sh。高亮排版修复后使用已有 build_highlight.sh 完成最终版本。verify_final.py 通过后使用现有 package_delivery.py 的 --reuse-verified-figures 选项更新交付，避免重绘/重新导出图件。未引入新构建工具或独立流程。

| PDF | 页数 | SHA-256 |
| --- | ---: | --- |
| Manuscript_clean.pdf | 26 | `7989aa32d4bca0127c2292e455fd7db143f6f29b55f5a7f557902e5c65344385` |
| Manuscript_highlighted.pdf | 59 | `ca9c989faa22335adc056cb4e6d894460deed6f6f9c51e641a095c6db3cc8da1` |
| Supplementary_Materials.pdf | 27 | `b20a44d05e10b05ecbde46bb9f5890b1cd3db5b3eebb951d15c7793a78f8f3c1` |
| Response_to_Reviewers.pdf | 66 | `34ad3fee329fda10240923e2e9bdc0f50ebfb9d5a587e4a7a68f513668e3e3c9` |
| Cover_Letter.pdf | 1 | `667472cfed86da90a7f66906137b0c2312214a99f3dc22c72c21192fbf056e78` |
| Combined_reference_copy.pdf（仅内部） | 54 | `6fd45659003bb88eddf6c76bc5094c6a8c659aebb5e47da09a968add84c235a3` |

六份最终LaTeX日志无错误、未解决引用/缺失图件、Overfull或其他警告；Biber/BibTeX日志也无警告或错误。初始编译遍次的临时引用告警已在最终遍次消除。曾遇到的真实失败和修复保存在 `verification/STAGE4_BUILD_ATTEMPTS.json`，没有删除或放宽检查：

- 文本提取器误把转义 `\%` 当注释；修正为只去除未转义 `%`，唯一连续八词PDF匹配标准不变。
- latexdiff标题/数学标记产生书签、重复锚点和字号警告；只修复生成的排版标记，保留 CFONT 样式。当前改动图注整体标蓝，历史图注仍保留在diff源码注释中，避免在float内重复长图注。

已更新 final_pdf_locations.json、quotation_pdf_locations.json、location_verification.json、comment_position_map.csv 及依赖位置的 Action。82个登记位置中69个具有实际打印位置，其余为preamble、构建、书目或Rebuttal等非打印正文登记；未匹配打印位置为零。clean/Combined的正文标签页码一致，独立Supplementary使用自身页码（例如OASIS表为Combined第24页、独立第1页）。

## C. 一致性验证

- verify_final.py：803项全部通过，failed_checks为空；保留原有检查并增加当前构建、意见原文、Response和引文一致性检查。
- 82个final_text片段唯一匹配工作源码；56条Reviewer和10条Editorial原文、对应关系和来源哈希保留。
- Stage 1–3确认的正文、Supplementary、所有引用/公式、实验数据、图件及历史来源未改变。M7保留T1-weighted MRI限定。
- 生成器正常复跑未改变91个已登记/工作section文件；三份amendment是上一登记片段，按原有amend规则统一结尾换行。
- pdflatex recorder记录实际加载输入；六份PDF、最终日志、.fls及当前项目输入哈希见stage4_build_receipt.json。高亮稿包含此前确认改动，已核验关键句并抽查标题/摘要、Introduction、方法公式、M1/M2和Cover Letter。
- 全部工作LaTeX/书目与delivery副本一致；可移植派生源码仅替换既有相对路径。全部manifest哈希回读匹配。
- 75个既有图件资产保持Stage4前哈希；196个指定ROI CSV哈希检查通过，未执行统计分析。

## D. 交付与修改范围

正式投稿候选目录 `revision_workspace/delivery/01_submission/`：Manuscript_clean.pdf、Manuscript_highlighted.pdf、Supplementary_Materials.pdf、Response_to_Reviewers.pdf、Cover_Letter.pdf、submission_abstract.txt。

02_figures为独立图件；03_editable_sources为可编辑来源；04_latex_sources为最新源码；05_internal_audit只作内部追溯（含Combined Reference Copy），不要整目录作为正式投稿附件。

交付manifest管理135个文件，共118,681,048字节。未删除既有交付文件。完整实际修改清单与最终diff --stat将在提交前列于本报告末尾。

本阶段源头修改为引文选择规则、PDF定位、必要的高亮排版与构建收据、无图件重建的打包选项和附加验证；其余为相应登记/生成内容、PDF、delivery副本与追溯记录。未纳入无关文件。

## E. Git

按作者授权创建单独提交 `docs(revision): finalize rebuttal alignment and delivery - stage 4`，仅暂存本阶段明确文件；推送origin/main，不强推、不覆盖其他提交。最终SHA及推送结果以Git记录和会话最终报告为准。

## F. 作者仍需处理

- 核实并签署全体作者 License to Publish、Conflict of Interest，以及适用的作者变更文件。
- 核实图像/材料复用权限、决定信要求的额外附件，并最终检查图件及版式。
- 决定信原期限为2026-11-04；是否获延期、当前系统状态和实际提交需作者核实，本地构建不能证明这些事项完成。
- Cover Letter沿用已确认的2026-11-04日期，实际投稿时请作者核对。
- 原已披露的填补、checkpoint关联、外部prompt等证据局限仍存在；本阶段验证只说明生成和追溯一致，不证明新的科学结论。

未执行Editorial Manager投稿、签署或权限认证。完成后停止，等待作者最终人工检查。

## 实际修改文件（提交范围）

- `rebuttal/sections/02_reviewer2.tex`
- `rebuttal/sections/03_reviewer3_major.tex`
- `rebuttal/sections/04_reviewer3_minor.tex`
- `revision_workspace/EXECUTION_STATUS.md`
- `revision_workspace/build/final_highlight/manuscript_highlighted.pdf`
- `revision_workspace/build/final_highlight/source_receipt.json`
- `revision_workspace/build/manuscript/BMEF_main.pdf`
- `revision_workspace/build/manuscript/pass1.stdout`
- `revision_workspace/build/manuscript/pass2.stdout`
- `revision_workspace/build/manuscript/pass3.stdout`
- `revision_workspace/build/rebuttal/cover_letter.pdf`
- `revision_workspace/build/rebuttal/main.pdf`
- `revision_workspace/build/rebuttal/pass1.stdout`
- `revision_workspace/build/rebuttal/pass2.stdout`
- `revision_workspace/build/rebuttal/pass3.stdout`
- `revision_workspace/build/variants/manuscript_clean.biber.stdout`
- `revision_workspace/build/variants/manuscript_clean.pass1.stdout`
- `revision_workspace/build/variants/manuscript_clean.pass2.stdout`
- `revision_workspace/build/variants/manuscript_clean.pass3.stdout`
- `revision_workspace/build/variants/manuscript_clean.pdf`
- `revision_workspace/build/variants/manuscript_highlighted.biber.stdout`
- `revision_workspace/build/variants/manuscript_highlighted.pass1.stdout`
- `revision_workspace/build/variants/manuscript_highlighted.pass2.stdout`
- `revision_workspace/build/variants/manuscript_highlighted.pass3.stdout`
- `revision_workspace/build/variants/supplementary_standalone.pdf`
- `revision_workspace/delivery/01_submission/Cover_Letter.pdf`
- `revision_workspace/delivery/01_submission/Manuscript_clean.pdf`
- `revision_workspace/delivery/01_submission/Manuscript_highlighted.pdf`
- `revision_workspace/delivery/01_submission/Response_to_Reviewers.pdf`
- `revision_workspace/delivery/01_submission/Supplementary_Materials.pdf`
- `revision_workspace/delivery/01_submission/submission_abstract.txt`
- `revision_workspace/delivery/04_latex_sources/manuscript/BMEF_main.tex`
- `revision_workspace/delivery/04_latex_sources/manuscript/main_labels.tex`
- `revision_workspace/delivery/04_latex_sources/manuscript/manuscript_clean.tex`
- `revision_workspace/delivery/04_latex_sources/manuscript/manuscript_highlighted.tex`
- `revision_workspace/delivery/04_latex_sources/rebuttal/sections/01_editor.tex`
- `revision_workspace/delivery/04_latex_sources/rebuttal/sections/02_reviewer2.tex`
- `revision_workspace/delivery/04_latex_sources/rebuttal/sections/03_reviewer3_major.tex`
- `revision_workspace/delivery/04_latex_sources/rebuttal/sections/04_reviewer3_minor.tex`
- `revision_workspace/delivery/05_internal_audit/Combined_reference_copy.pdf`
- `revision_workspace/delivery/05_internal_audit/FINAL_VALIDATION.json`
- `revision_workspace/delivery/05_internal_audit/comment_position_map.csv`
- `revision_workspace/delivery/05_internal_audit/final_pdf_locations.json`
- `revision_workspace/delivery/05_internal_audit/location_verification.json`
- `revision_workspace/delivery/05_internal_audit/position_registry.csv`
- `revision_workspace/delivery/05_internal_audit/quotation_pdf_locations.json`
- `revision_workspace/delivery/05_internal_audit/rebuttal_excerpt_selections.json`
- `revision_workspace/delivery/05_internal_audit/response_changes.csv`
- `revision_workspace/delivery/05_internal_audit/response_source_manifest.json`
- `revision_workspace/delivery/05_internal_audit/stage4_alignment_audit.json`
- `revision_workspace/delivery/05_internal_audit/stage4_build_receipt.json`
- `revision_workspace/delivery/README.md`
- `revision_workspace/delivery/manifest.json`
- `revision_workspace/integration/STAGE4_FINAL_DELIVERY.md`
- `revision_workspace/integration/amendments/REBUTTAL-02_reviewer2.tex.008.tex`
- `revision_workspace/integration/amendments/REBUTTAL-03_reviewer3_major.tex.009.tex`
- `revision_workspace/integration/amendments/REBUTTAL-04_reviewer3_minor.tex.008.tex`
- `revision_workspace/integration/build_attempts.json`
- `revision_workspace/integration/build_highlight.sh`
- `revision_workspace/integration/build_manuscript.sh`
- `revision_workspace/integration/build_rebuttal.py`
- `revision_workspace/integration/build_rebuttal.sh`
- `revision_workspace/integration/build_variants.sh`
- `revision_workspace/integration/comment_position_map.csv`
- `revision_workspace/integration/derived/current_flat.tex`
- `revision_workspace/integration/derived/main_labels.tex`
- `revision_workspace/integration/derived/manuscript_clean.tex`
- `revision_workspace/integration/derived/manuscript_highlighted.tex`
- `revision_workspace/integration/final_pdf_locations.json`
- `revision_workspace/integration/final_text/REBUTTAL-02_reviewer2.tex.tex`
- `revision_workspace/integration/final_text/REBUTTAL-03_reviewer3_major.tex.tex`
- `revision_workspace/integration/final_text/REBUTTAL-04_reviewer3_minor.tex.tex`
- `revision_workspace/integration/location_verification.json`
- `revision_workspace/integration/map_final_locations.py`
- `revision_workspace/integration/package_delivery.py`
- `revision_workspace/integration/position_registry.csv`
- `revision_workspace/integration/quotation_pdf_locations.json`
- `revision_workspace/integration/rebuttal_excerpt_selections.json`
- `revision_workspace/integration/rebuttal_generated/02_reviewer2.tex`
- `revision_workspace/integration/rebuttal_generated/03_reviewer3_major.tex`
- `revision_workspace/integration/rebuttal_generated/04_reviewer3_minor.tex`
- `revision_workspace/integration/response_changes.csv`
- `revision_workspace/integration/response_source_manifest.json`
- `revision_workspace/integration/responses/M19.diff.txt`
- `revision_workspace/integration/responses/M19.final.md`
- `revision_workspace/integration/stage4_alignment_audit.json`
- `revision_workspace/integration/stage4_build_receipt.json`
- `revision_workspace/integration/submission_abstract.txt`
- `revision_workspace/integration/tune_highlight.py`
- `revision_workspace/integration/verify_final.py`
- `revision_workspace/verification/DELIVERY_VALIDATION.json`
- `revision_workspace/verification/FINAL_VALIDATION.json`
- `revision_workspace/verification/STAGE4_BUILD_ATTEMPTS.json`
- `revision_workspace/verification/manuscript_bbox.html`

未纳入提交：本次核查生成的5张预览PNG、首次高亮尝试的派生源码及variants下的重复高亮PDF。这些仅保存在本地build目录；正式高亮PDF已在final_highlight及delivery中提交，失败记录索引另行保留。

## 最终 git diff --stat

```text
 rebuttal/sections/02_reviewer2.tex                 |   178 +-
 rebuttal/sections/03_reviewer3_major.tex           |   239 +-
 rebuttal/sections/04_reviewer3_minor.tex           |    95 +-
 revision_workspace/EXECUTION_STATUS.md             |     8 +-
 .../final_highlight/manuscript_highlighted.pdf     |   Bin 5251690 -> 5247363 bytes
 .../build/final_highlight/source_receipt.json      |    54 +-
 revision_workspace/build/manuscript/BMEF_main.pdf  |   Bin 5051981 -> 5050946 bytes
 revision_workspace/build/manuscript/pass1.stdout   |    13 +-
 revision_workspace/build/manuscript/pass2.stdout   |     2 +-
 revision_workspace/build/manuscript/pass3.stdout   |     2 +-
 revision_workspace/build/rebuttal/cover_letter.pdf |   Bin 20484 -> 20484 bytes
 revision_workspace/build/rebuttal/main.pdf         |   Bin 456720 -> 467225 bytes
 revision_workspace/build/rebuttal/pass1.stdout     |    48 +-
 revision_workspace/build/rebuttal/pass2.stdout     |    51 +-
 revision_workspace/build/rebuttal/pass3.stdout     |    36 +-
 .../build/variants/manuscript_clean.biber.stdout   |     2 +-
 .../build/variants/manuscript_clean.pass1.stdout   |     9 +-
 .../build/variants/manuscript_clean.pass2.stdout   |     2 +-
 .../build/variants/manuscript_clean.pass3.stdout   |     2 +-
 .../build/variants/manuscript_clean.pdf            |   Bin 2916194 -> 2915165 bytes
 .../variants/manuscript_highlighted.biber.stdout   |     2 +-
 .../variants/manuscript_highlighted.pass1.stdout   |   231 +-
 .../variants/manuscript_highlighted.pass2.stdout   |   210 +-
 .../variants/manuscript_highlighted.pass3.stdout   |   210 +-
 .../build/variants/supplementary_standalone.pdf    |   Bin 2423319 -> 2423319 bytes
 .../delivery/01_submission/Cover_Letter.pdf        |   Bin 20484 -> 20484 bytes
 .../delivery/01_submission/Manuscript_clean.pdf    |   Bin 2916194 -> 2915165 bytes
 .../01_submission/Manuscript_highlighted.pdf       |   Bin 5251690 -> 5247363 bytes
 .../01_submission/Response_to_Reviewers.pdf        |   Bin 456720 -> 467225 bytes
 .../01_submission/Supplementary_Materials.pdf      |   Bin 2423319 -> 2423319 bytes
 .../delivery/01_submission/submission_abstract.txt |     2 +-
 .../04_latex_sources/manuscript/BMEF_main.tex      |    20 +-
 .../04_latex_sources/manuscript/main_labels.tex    |     4 +-
 .../manuscript/manuscript_clean.tex                |    20 +-
 .../manuscript/manuscript_highlighted.tex          |   118 +-
 .../rebuttal/sections/01_editor.tex                |    12 +-
 .../rebuttal/sections/02_reviewer2.tex             |   196 +-
 .../rebuttal/sections/03_reviewer3_major.tex       |   271 +-
 .../rebuttal/sections/04_reviewer3_minor.tex       |    99 +-
 .../05_internal_audit/Combined_reference_copy.pdf  |   Bin 5051981 -> 5050946 bytes
 .../05_internal_audit/FINAL_VALIDATION.json        |  2786 +++-
 .../05_internal_audit/comment_position_map.csv     |   362 +-
 .../05_internal_audit/final_pdf_locations.json     |  2361 ++-
 .../05_internal_audit/location_verification.json   |     2 +-
 .../05_internal_audit/position_registry.csv        |    24 +-
 .../05_internal_audit/quotation_pdf_locations.json |  1009 ++
 .../rebuttal_excerpt_selections.json               |   277 +
 .../05_internal_audit/response_changes.csv         |    31 +-
 .../response_source_manifest.json                  |    36 +-
 .../05_internal_audit/stage4_alignment_audit.json  |  2380 +++
 .../05_internal_audit/stage4_build_receipt.json    |   235 +
 revision_workspace/delivery/README.md              |     2 +-
 revision_workspace/delivery/manifest.json          |   102 +-
 .../integration/STAGE4_FINAL_DELIVERY.md           |   334 +
 .../amendments/REBUTTAL-02_reviewer2.tex.008.tex   |   433 +
 .../REBUTTAL-03_reviewer3_major.tex.009.tex        |   570 +
 .../REBUTTAL-04_reviewer3_minor.tex.008.tex        |   326 +
 revision_workspace/integration/build_attempts.json |     4 +-
 revision_workspace/integration/build_highlight.sh  |     8 +-
 revision_workspace/integration/build_manuscript.sh |     6 +-
 revision_workspace/integration/build_rebuttal.py   |    42 +-
 revision_workspace/integration/build_rebuttal.sh   |     8 +-
 revision_workspace/integration/build_variants.sh   |    14 +-
 .../integration/comment_position_map.csv           |   362 +-
 .../integration/derived/current_flat.tex           |    20 +-
 .../integration/derived/main_labels.tex            |     4 +-
 .../integration/derived/manuscript_clean.tex       |    20 +-
 .../integration/derived/manuscript_highlighted.tex |   118 +-
 .../integration/final_pdf_locations.json           |  2361 ++-
 .../final_text/REBUTTAL-02_reviewer2.tex.tex       |   179 +-
 .../final_text/REBUTTAL-03_reviewer3_major.tex.tex |   240 +-
 .../final_text/REBUTTAL-04_reviewer3_minor.tex.tex |    96 +-
 .../integration/location_verification.json         |     2 +-
 .../integration/map_final_locations.py             |    65 +-
 revision_workspace/integration/package_delivery.py |    65 +-
 .../integration/position_registry.csv              |    24 +-
 .../integration/quotation_pdf_locations.json       |  1009 ++
 .../integration/rebuttal_excerpt_selections.json   |   277 +
 .../rebuttal_generated/02_reviewer2.tex            |   178 +-
 .../rebuttal_generated/03_reviewer3_major.tex      |   239 +-
 .../rebuttal_generated/04_reviewer3_minor.tex      |    95 +-
 .../integration/response_changes.csv               |     1 +
 .../integration/response_source_manifest.json      |     2 +-
 .../integration/responses/M19.diff.txt             |    10 +
 .../integration/responses/M19.final.md             |     2 +-
 .../integration/stage4_alignment_audit.json        |  2380 +++
 .../integration/stage4_build_receipt.json          |   235 +
 .../integration/submission_abstract.txt            |     2 +-
 revision_workspace/integration/tune_highlight.py   |    35 +
 revision_workspace/integration/verify_final.py     |    63 +
 .../verification/DELIVERY_VALIDATION.json          |    19 +-
 .../verification/FINAL_VALIDATION.json             |  2786 +++-
 .../verification/STAGE4_BUILD_ATTEMPTS.json        |    17 +
 .../verification/manuscript_bbox.html              | 15180 +++++++++----------
 94 files changed, 29074 insertions(+), 10500 deletions(-)
```
