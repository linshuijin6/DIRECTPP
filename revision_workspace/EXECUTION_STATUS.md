# 本地整合执行状态

本轮已实施正文、Rebuttal、图表及补充材料整合；交付用于作者验收，未执行期刊提交。原Notion导出25个文件及27个整合前基线文件均保留，哈希核验见最终验证记录。

入口：[交付说明](delivery/README.md)、[最终验证](verification/FINAL_VALIDATION.json)、[执行计划](FINAL_INTEGRATION_PLAN.md)。交付候选包括clean正文、含补充材料的高亮稿、独立Supplementary、56条逐点回复、Cover Letter、纯文本摘要、单独图件及可编辑源。各文件页数、哈希以验证JSON和交付manifest为准。

82个最终修改位置见 integration/position_registry.csv；56条意见双向对应见 integration/comment_position_map.csv。123处Original/Revised候选和17处新增入口分别有candidate_disposition.csv、addition_disposition.csv；无按审稿编号依次覆盖正文的操作。英文来源逐条保存在integration/responses，事实及完成时态更新保留diff和理由。R3-9仍标明是按确认中文方向重建英文，不冒称历史逐字稿。

| 修改组 | 已实施范围与边界 |
| --- | --- |
| G1 | 冻结512D编码器、1026参数affine adapter、实际软惩罚目标、prompt、cross-attention与表示层τ分析；重建Full使用原始tracer向量，E1为不同权重族的固定权重干预 |
| G2 | 两折生成与独立三折分类设计、任务N与MCI定义、OASIS AV45范围、选择/预处理/复现设置和数据使用说明；未将临床源Image ID当作已核实NIfTI身份 |
| G3 | 历史绝对值主文表、whole-volume及masked结果、配对比较和客观选例；保留不利结果、信息和训练终点差异，不宣称Full全面优胜 |
| G4 | 指定shuijin ROI CSV、98ROI BH族、16行一致性/回归表和20行效应量表、normalized uptake定义及重绘；不宣称SUVR、TOST或临床等效 |
| G5 | 实际27配置/81fit、三折sample SD、条件bootstrap CI、逐折DeLong与临床基线、ROC及人口学敏感性；MCI/CN无普遍改善，不宣称独立增量诊断价值 |
| G6 | 实际晚期t=0残差拟合、一forward一tracer、9,925,921参数与RTX4090约251ms/8.29GiB实际测量范围；无独立teacher恢复证据，无匹配多步/FLOPs/基线速度排行 |
| G7 | 标题/摘要/Discussion及引言统一横断面MCI阶段区分，区分影像相似性与生物学确诊，加入2024标准及p-tau217背景，收紧临床部署和预后承诺 |
| G8 | 9285评分单元中1751 observed、7534 source-missing；核正四项均值/SD，移除评分组间p值，补缺失/填补表；CN体重0–227kg来源有效性仍未解决，未删人或替换数据 |

图1/4/5及S1–S6有原生SVG与重绘代码；图2/3保留历史PDF及drawio/PPTX来源候选。单独导出PNG为400dpi不等于提升历史位图的原生细节。为可读性，Figure4改为横向分半小提琴，S1–S4按atlas ID重排90个非主图ROI；未保留原位图的顺序/分组，这是明确交给作者验收的版式差异，不能描述为历史图精确复原。原图保存在baseline，不覆盖丢弃。

页码从实际最终PDF及aux取得。Rebuttal以combined reference copy为统一参照，补充材料同时给出独立PDF页码；打印行号仅覆盖实际匹配短语。位置匹配、56条来源哈希、原件/基线哈希、构建警告及交付哈希由验证脚本检查；这些工程检查不等于对科学结论的独立认证。已抽查主图、区域表、病例图、分类长表、高亮首页及回复封面。

仍须作者处理：全体作者License/COI、适用复用授权、决定信额外附件，以及上述图件版式验收。历史分类Syn-PET与重建Full checkpoint未绑定、OASIS完整prompt缺失、填补相关混杂、未完成的完整无文本/匹配多步等科学限制已在正文/回复保留。没有新增训练、推理、队列替换、统计检验、签名、在线提交、commit或push。

最终高亮稿因NFS元数据等待转至本地临时目录构建，三遍pdflatex后复制到`build/final_highlight/`，源码等同性收据随构建保存。先前NFS尝试不计入验收，仅写scratch构建目录；状态见`integration/build_attempts.json`。未控制其他进程。
