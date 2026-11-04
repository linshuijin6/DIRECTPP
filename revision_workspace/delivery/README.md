# BMEF-D-26-00169 本地整合交付

本包用于作者验收；尚未向期刊提交。01_submission 为投稿候选文件；02_figures 为单独图件；03_editable_sources 含新 SVG、重绘脚本及保留的历史 drawio/PPTX（重绘脚本依赖本仓库证据文件，未复制受试者CSV或影像）。04_latex_sources 为构建源码。05_internal_audit 仅用于本地追溯，请勿整目录上传投稿系统。

- Clean 稿仅含正文和参考文献，Supplementary 为独立 PDF。高亮稿包含补充材料；蓝色为新增、红色为删除，以保存的本轮整合前稿为基线。高亮专用Bib保留两条基线旧引用以排印已删除内容；clean稿不含这些弃用条目。
- Rebuttal 页码以 Combined_reference_copy 为统一参照，同时列出独立 Supplementary 页码。页码从实际 PDF/aux 获取；行号只标识核验到的短语，不冒充整段范围。
- 图 1/4/5 和 S1–S6 具有原生 SVG；图 2/3 保留历史 PDF 和 drawio/PPTX。原始复合图中的位图面板不会因 400 dpi 导出而增加原生细节，也不声称所有面板均为可编辑矢量。为可读性，Figure4使用横向分半小提琴；S1–S4按atlas ID重排90个非主图ROI，未保留历史位图顺序/分组。这是需要作者验收的版式差异，不能声称严格复原历史图。
- 全部56条回复保留作者来源快照；事实更新及完成时态变更见 response_changes.csv/工作区 responses 下逐条 diff。123处旧正文候选均有最终位置映射，不能按旧意见顺序再覆盖。

投稿前仍需作者核实全体作者签署的 License/COI、适用的复用授权及决定信额外附件。没有生成签名、认证权限或执行在线投稿。科学边界包括诊断组条件填补、历史分类输入与重建生成器权重未绑定、外部完整 prompt 缺失，以及未完成的匹配多步/无文本消融、FLOPs和同条件基线测时；正文与回复据此收紧结论。

在04_latex_sources/manuscript目录，clean/高亮稿使用 pdflatex → biber → pdflatex 两遍；独立补充材料使用 pdflatex 两遍。rebuttal目录使用 pdflatex → bibtex → pdflatex 两遍；cover_letter.tex单独pdflatex。本机匹配的biblatex/biber环境及构建脚本保存在 revision_workspace/integration，不作为投稿材料复制。

SOURCE: 仓库根目录 revision_workspace/index/ 提供完整 Notion 来源索引；源导出及基线文件保持原位。manifest.json 对本包文件逐一记录大小和 SHA-256，供复制后核验。
