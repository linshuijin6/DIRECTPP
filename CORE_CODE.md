# 修稿用核心代码入口

当前工作回到审稿意见与修稿。实验流程按作者说明采用：**生成器两折交叉训练得到全队列 OOF 合成 PET，再做三折分类。论文中的 two-fold 不是笔误；数据泄露不再列为当前追查任务。**

下表划定后续优先阅读和修改的代码范围。原文件保持归档位置，本轮只建立入口，没有迁移、抽取或改写实验代码。核心表示与修稿直接相关，不表示每本历史 notebook 都是可一键运行的最终版本。

| 模块 | 优先入口 | 修稿时的用途 |
|---|---|---|
| 文本条件与适配 | [CLIP 预训练](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _clip_pretrain .ipynb>) | 核对条件构建、适配模块与训练方法描述 |
| 双示踪剂生成 | [生成训练与推理](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb>)；[GitHub 实现](<source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/Github/train/mri2pet _two trace_github.ipynb>) | 模型、损失、训练与推理逻辑；两折 OOF 作为实验协议，不继续用单次历史运行替代整体流程 |
| 下游分类 | [合成 PET 分类](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet all data-_mri classification-densenet.ipynb>)；[真实 PET 分类](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet all data-_mri classification-densenet-Copy2.ipynb>)；[AD/CN 历史入口](<source_archive/vscode-3003/home/data/liutuo/code/.ipynb_checkpoints/mri2pet all data-_mri classification-densenet-checkpoint.ipynb>) | 分类模型、输入模态与训练逻辑 |
| 生成评估与基线 | [四指标评估示例](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_reflow_test or fanhua.ipynb>)；[Swin-UNet](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet swinunet useful.ipynb>)；[扩散基线](<source_archive/vscode-3003/home/data/liutuo/code/mri2pet _add pretrained commom clip_concat-ddpm.ipynb>) | 查指标定义、预处理和已恢复基线实现；评估示例不直接当作论文总体结果 |
| 区域统计与图件 | [ROI 统计](<source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/shuijin_code.ipynb>)；[论文统计](<source_archive/vscode-3002/home/ssddata/liutuo/paper data statistics .ipynb>)；[生成对比图](<source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_AV45-swin unet or fanhua.ipynb>) | ROI 分析、统计方法与图件修改；对比图中的汇总数组属于绘图输入 |
| 现有修稿分析脚本 | [人口学重算](appendix/legacy_only/8_revision_evidence/recalculate_table_s1.py)；[区域统计重算](appendix/legacy_only/8_revision_evidence/compute_regional_statistics.py)；[现有证据分析](appendix/legacy_only/8_revision_evidence/revision_20261016/analyze_evidence.py)；[统计结果与图表整理](appendix/legacy_only/8_revision_evidence/revision_20261016/finalize_evidence.py) | 保留可用于回应审稿意见的分析代码，采用前按具体意见检查输入 |
| 公共工具与模型实现 | [工具函数](source_archive/vscode-3002/home/ssddata/liutuo/liutuo_utils.py)；[生成模型依赖](source_archive/vscode-3002/home/ssddata/liutuo/generative/) | 生成模型、推理器、指标及 notebook 使用的辅助函数 |

原始[审稿意见](reports/source_reports/BMEF_Reviewer_Report_English.docx)、[论文](manuscript/BMEF_main.tex)和[补充材料目录](manuscript/)是修稿入口。逐文件路径和本次核对的 SHA256 见 [core_code_index.csv](paper_index/core_code_index.csv)。其他历史版本仍保留在 `source_archive`，默认被 Git 忽略，不作为默认修改入口。

`.gitignore` 已排除检索、SSH 采集、转存脚本及派生大体积快照，同时排除权重、影像和常见缓存。`source_archive` 默认忽略，只放行清单中的核心文件，以及 3002 的 `generative` Python 包。修稿报告、审稿意见、归档外的 CSV 结果和上述修稿分析脚本继续对 Git 可见。AD/CN 核心 notebook 位于 `.ipynb_checkpoints` 中，已单独放行。
