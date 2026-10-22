# DIRECTPP 修稿协作规则

本文件适用于本仓库及子目录。当前任务是 BMEF-D-26-00169 的修稿；用户当前指令和会话中已有授权优先。默认中文沟通，先给结论，明确已核实、推断和待解决事项。

## 阅读入口与检索顺序

1. 先读 `CORE_CODE.md`，按具体任务查看 `manuscript/BMEF_main.tex`、`reports/source_reports/REVIEW_REQUIREMENTS.md` 和 `reports/source_reports/review_comment_register.csv`。无需每次读取全部材料。
2. 方法实现按 `paper_index/core_code_index.csv` 定位历史核心文件及 cell；当前修稿实验实现优先查看 `experiments/` 下对应目录。核心清单是历史入口，不是当前全部实验代码的清单。
3. 先在相关模块检索；结果或运行问题只读对应配置、日志、checkpoint 收据和报告目录。扩大范围前先确认当前命中不足。
4. `source_archive/` 其他版本、`appendix/legacy_only/`、历史审计和采集记录只在当前问题需要原始依据或依赖时回查。不要以全库递归扫描或全库 `--no-ignore` 开始任务。
5. `.rgignore` 仅控制 ripgrep 默认检索，`.gitignore` 控制 Git 忽略；它们不限制文件访问，也不保证所有 IDE/agent 索引遵守。使用不读取本文件的工具时，应显式提供本文件作为项目上下文。

常用检索方式（从仓库根目录运行）：

```sh
# 当前实验代码
rg -n '关键词' experiments --glob '*.py'
# 当前审稿要求和稿件
rg -n '关键词' reports/source_reports manuscript --glob '*.md' --glob '*.csv' --glob '*.tex'
# 按问题回查指定历史目录；仅对这个范围绕过忽略规则
rg -n --no-ignore '关键词' appendix/legacy_only/8_revision_evidence/revision_20261016 --glob '*.py'
```

历史目录默认隐藏后，没有默认搜索命中不等于文件不存在。可以直接读取明确路径，或在最小目录内使用 `rg --files --hidden --no-ignore <目录>`。

## Notebook 与归档依赖

- 核心 notebook 先按清单中的零起算 cell 编号读取 `cells[i].source`；需要发现实现时只检索代码单元。避免把整本 JSON、图像 base64、进度条或全部输出送入上下文。
- 仅在核验某次历史运行时读取相关 cell 输出；输出必须与源文件、cell 和具体运行身份一起解释。不得执行整本历史 notebook 来查看源码。
- 如需源码提取副本，写入临时或独立派生目录，记录原路径、原文件 SHA-256 和 cell 编号；不得覆盖原 notebook，也不得把提取副本当作独立实现依据。
- 不要为简化检索搬走、删除或批量重写归档。`experiments/e1_clinical_conditioning/prepare.py` 的 `init()` 仍读取 `appendix/legacy_only/8_revision_evidence/revision_20261016/clinical_observed_subjects.csv` 和 `clinical_observed_provenance.csv`，以及其他归档来源。修改依赖前逐项核实调用和路径。

## 证据与修稿范围

- 审稿原文与编辑要求优先于 agent 分析或旧计划。R2 Word 只含 R2；R3 与编辑要求见 `raw_review.md`。分别按登记表编号回应，不把旧 20 条矩阵当成完整 R2/R3 清单。
- `appendix/legacy_only/` 是混合历史材料保留区，不能整体归为某个 agent 的输出，也不是正式 supplementary。`provenance.json` 的复制哈希一致、意见已收录、实验科学有效是三种不同状态。
- 源码用于核对实现，配置/名单/checkpoint/逐人结果用于核对实际执行。历史报告提供线索；其中“已解决”“验证通过”等判断必须核对对应原件和适用范围。新登记不自动认证或推翻已有结果。
- 按作者说明采用生成器两折 OOF → 分类器三折的实验设计；设计说明不替代实际执行证据。不主动重启已经结束的全库泄露追查；对具体审稿意见核查必要的折身份、受试者和结果来源。
- 不混用不同 cohort、fold、预处理、checkpoint 或指标协议；缺失证据明确保留缺口。训练启动、短试跑、缓存或文件完整性通过不能写成完整实验完成。
- 未核实参考区归一化时使用 normalized uptake；不得由 p>0.05 推断等效，不模拟结果或虚构 TOST 界值。0.82 按对应源码解释为预设软惩罚目标，不写成已优化阈值或硬约束。

## 修改与验证

- 保留用户已有的未提交修改。只修改当前任务需要的文件；原始审稿材料、provenance、冻结稿件和历史输出不得因整理而批量改写。用户要求改稿时可按具体意见编辑目标稿件。
- 新分析和实验写入独立路径，保留失败记录；不静默替换数据、划分、归一化或最终权重。当前运行状态和配置须实时核实，旧 README 的阶段描述不是当前状态。
- 本轮检索规则修改不授权新增训练、改队列、终止进程或发送外部消息。后续执行沿用用户会话中的已有授权，不重复请求；新增耗时实验先只读核实并给出范围和资源方案。
- 规则/文档修改检查链接、检索可见性和原件保留；代码修改运行与变更相称的检查。报告具体改动、验证结果和限制，不将工程检查写成科学结论。
