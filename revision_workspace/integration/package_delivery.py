"""Build a local author-review delivery, with explicit public/internal separation."""
from pathlib import Path
import shutil,json,hashlib,subprocess,xml.etree.ElementTree as ET,difflib
R=Path(__file__).resolve().parents[2];W=R/'revision_workspace/integration';D=R/'revision_workspace/delivery'
for name in ['01_submission','02_figures','03_editable_sources','04_latex_sources/manuscript','04_latex_sources/rebuttal','05_internal_audit']:(D/name).mkdir(parents=True,exist_ok=True)
def copy(src,dst):
 src=R/src if not isinstance(src,Path) else src;dst=D/dst;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst)
for src,dst in [('revision_workspace/build/variants/manuscript_clean.pdf','Manuscript_clean.pdf'),('revision_workspace/build/final_highlight/manuscript_highlighted.pdf','Manuscript_highlighted.pdf'),('revision_workspace/build/variants/supplementary_standalone.pdf','Supplementary_Materials.pdf'),('revision_workspace/build/rebuttal/main.pdf','Response_to_Reviewers.pdf'),('revision_workspace/build/rebuttal/cover_letter.pdf','Cover_Letter.pdf'),('revision_workspace/integration/submission_abstract.txt','submission_abstract.txt')]:copy(src,'01_submission/'+dst)
copy('revision_workspace/build/manuscript/BMEF_main.pdf','05_internal_audit/Combined_reference_copy.pdf')
# Figure exports. Existing PDFs retain their original intrinsic raster detail.
for p in (R/'manuscript/figures').glob('*'):
 if p.is_file() and (p.name.startswith(('figure_','supplementary_figure_','revision_cases_','revision_roc_'))):copy(p,'02_figures/'+p.name)
for p in (W/'figures').glob('*.png'):copy(p,'02_figures/'+p.name)
for n in [2,3]:subprocess.run(['pdftoppm','-r','400','-singlefile','-png',str(R/f'manuscript/figures/figure_{n}.pdf'),str(D/f'02_figures/figure_{n}')],check=True)
for tracer in ['FDG','AV45']:copy(f'reports/revision_evidence_night_20261102/R3_11_final_figures/R3_11_{tracer}_cases.png',f'02_figures/revision_cases_{tracer.lower()}.png')
for p in (R/'manuscript/figures/editable_sources').glob('*.svg'):copy(p,'03_editable_sources/'+p.name)
for name in ['build_primary_figures.py','build_roi_figures.py','figure_5_plot_data.csv','primary_figure_manifest.json','roi_figure_manifest.json']:copy(W/'figures'/name,'03_editable_sources/'+name)
originals=[]
for p in (R/'manuscript/raw_pic').iterdir():
 if p.is_file():
  copy(p,'03_editable_sources/historical_originals/'+p.name);originals.append({'source':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
# Derive individual native pages without rasterizing or changing the original mxfile.
x=ET.parse(R/'manuscript/raw_pic/1103.drawio').getroot()
for name in ['FIG2','FIG3']:
 page=next(p for p in x if p.get('name')==name);out=ET.Element(x.tag,x.attrib);out.append(ET.fromstring(ET.tostring(page)));ET.ElementTree(out).write(D/f'03_editable_sources/{name}.drawio',encoding='utf-8',xml_declaration=True)
(D/'03_editable_sources/source_receipt.json').write_text(json.dumps({'historical_originals':originals,'derived_drawio_pages':['FIG2','FIG3'],'warning':'Historical composite raster panels remain raster assets; the supplied originals do not certify full vector editability of every panel. High-DPI PNG export does not recover absent raster detail. Recreated ROI figure sources are the author-designated shuijin family, not exact historical drawing files.'},ensure_ascii=False,indent=2)+'\n')
# Portable LaTeX inputs; no tools, data archives, subject CSVs or Notion exports are copied.
for p in [R/'manuscript/references.bib',R/'manuscript/BMEF_main.tex']:copy(p,'04_latex_sources/manuscript/'+p.name)
shutil.copytree(R/'manuscript/supplementary',D/'04_latex_sources/manuscript/supplementary',dirs_exist_ok=True)
shutil.copytree(R/'manuscript/figures',D/'04_latex_sources/manuscript/figures',dirs_exist_ok=True)
for name in ['manuscript_clean.tex','supplementary_standalone.tex','manuscript_highlighted.tex','supplementary_labels.tex','main_labels.tex','references_highlighted.bib']:
 s=(W/'derived'/name).read_text().replace('../revision_workspace/integration/derived/','');(D/'04_latex_sources/manuscript'/name).write_text(s)
for p in (R/'rebuttal').glob('*.tex'):copy(p,'04_latex_sources/rebuttal/'+p.name)
copy('rebuttal/references.bib','04_latex_sources/rebuttal/references.bib');shutil.copytree(R/'rebuttal/sections',D/'04_latex_sources/rebuttal/sections',dirs_exist_ok=True)
for name in ['position_registry.csv','comment_position_map.csv','candidate_disposition.csv','response_changes.csv','response_source_manifest.json','final_pdf_locations.json','location_verification.json','addition_disposition.csv','g8_verification.json','editor_requirements_status.json']:copy(W/name,'05_internal_audit/'+name)
copy('revision_workspace/verification/FINAL_VALIDATION.json','05_internal_audit/FINAL_VALIDATION.json')
for name in ['manuscript','rebuttal']:
 a=(W/f'baseline/{name}/references.bib').read_text();b=(R/name/'references.bib').read_text();(D/f'05_internal_audit/{name}_bibliography.diff').write_text(''.join(difflib.unified_diff(a.splitlines(True),b.splitlines(True),fromfile='preserved baseline',tofile='integrated bibliography')))
(D/'README.md').write_text('''# BMEF-D-26-00169 本地整合交付

本包用于作者验收；尚未向期刊提交。01_submission 为投稿候选文件；02_figures 为单独图件；03_editable_sources 含新 SVG、重绘脚本及保留的历史 drawio/PPTX（重绘脚本依赖本仓库证据文件，未复制受试者CSV或影像）。04_latex_sources 为构建源码。05_internal_audit 仅用于本地追溯，请勿整目录上传投稿系统。

- Clean 稿仅含正文和参考文献，Supplementary 为独立 PDF。高亮稿包含补充材料；蓝色为新增、红色为删除，以保存的本轮整合前稿为基线。高亮专用Bib保留两条基线旧引用以排印已删除内容；clean稿不含这些弃用条目。
- Rebuttal 页码以 Combined_reference_copy 为统一参照，同时列出独立 Supplementary 页码。页码从实际 PDF/aux 获取；行号只标识核验到的短语，不冒充整段范围。
- 图 1/4/5 和 S1–S6 具有原生 SVG；图 2/3 保留历史 PDF 和 drawio/PPTX。原始复合图中的位图面板不会因 400 dpi 导出而增加原生细节，也不声称所有面板均为可编辑矢量。为可读性，Figure4使用横向分半小提琴；S1–S4按atlas ID重排90个非主图ROI，未保留历史位图顺序/分组。这是需要作者验收的版式差异，不能声称严格复原历史图。
- 全部56条回复保留作者来源快照；事实更新及完成时态变更见 response_changes.csv/工作区 responses 下逐条 diff。123处旧正文候选均有最终位置映射，不能按旧意见顺序再覆盖。

投稿前仍需作者核实全体作者签署的 License/COI、适用的复用授权及决定信额外附件。没有生成签名、认证权限或执行在线投稿。科学边界包括诊断组条件填补、历史分类输入与重建生成器权重未绑定、外部完整 prompt 缺失，以及未完成的匹配多步/无文本消融、FLOPs和同条件基线测时；正文与回复据此收紧结论。

在04_latex_sources/manuscript目录，clean/高亮稿使用 pdflatex → biber → pdflatex 两遍；独立补充材料使用 pdflatex 两遍。rebuttal目录使用 pdflatex → bibtex → pdflatex 两遍；cover_letter.tex单独pdflatex。本机匹配的biblatex/biber环境及构建脚本保存在 revision_workspace/integration，不作为投稿材料复制。

SOURCE: 仓库根目录 revision_workspace/index/ 提供完整 Notion 来源索引；源导出及基线文件保持原位。manifest.json 对本包文件逐一记录大小和 SHA-256，供复制后核验。
''')
files=[]
for p in sorted(D.rglob('*')):
 if p.is_file() and p.name!='manifest.json':files.append({'path':str(p.relative_to(D)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(D/'manifest.json').write_text(json.dumps({'purpose':'local author review; no submission performed','files':files},ensure_ascii=False,indent=2)+'\n')
print('Packaged',len(files),'files; total MB',round(sum(x['bytes'] for x in files)/1e6,2))
