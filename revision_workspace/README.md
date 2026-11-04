# DIReCT++ 最终返稿工作区

本地索引及整合已实施。先读[执行状态](EXECUTION_STATUS.md)，交付入口为[作者验收包](delivery/README.md)；[综合实施计划](FINAL_INTEGRATION_PLAN.md)保留本轮执行前的规则与证据范围。

- [意见与英文回复](index/COMMENT_INDEX.md)：56条意见及英文来源。R3-9保留“按已确认中文方向整理，非历史逐字稿”的限定。
- [正文修改与版本](index/REVISION_INDEX.md)：123个来源候选；[候选处置](integration/candidate_disposition.csv)逐项对应唯一最终位置。[新增条目处置](integration/addition_disposition.csv)覆盖17处无Original的增补入口。
- [G1–G8分组](index/GROUP_INDEX.md)、[导出文件清单](index/SOURCE_MANIFEST.md)、[来源完整性快照](index/INTEGRITY_REPORT.md)。
- [最终位置登记](integration/position_registry.csv)、[56条意见双向映射](integration/comment_position_map.csv)、[实际PDF位置](integration/final_pdf_locations.json)、[最终验证](verification/FINAL_VALIDATION.json)。

Notion导出与27个基线文件保持原位、保留哈希。正式 manuscript/ 与 rebuttal/ 已按执行计划修改，不能将本目录误作“尚未实施”的旧索引。旧计划、仓库快照和完整性报告中的“待整合”描述属于当时状态，当前状态以执行记录为准。

索引验证运行 `tools/validate_indexes.py`；重建来源索引可运行 `tools/build_local_index.py`。`tools/audit_repository.py` 会刷新仓库快照，不能将刷新结果覆盖当作本轮整合前基线。所有脚本使用项目默认xiaochou解释器。
