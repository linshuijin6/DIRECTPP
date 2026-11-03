# R3-11 brain-mask PET quality evidence

完成结果见 [REPORT.md](run_20261102/REPORT.md)，最终状态见 [completion.json](run_20261102/completion.json)。

三个模型均完成 FDG 1,597 / AV45 1,364 例评价；两个比较各含 8 项预定义配对检验，分别 Holm 校正。冻结 SynthSeg 非零标签并集包括脑室和 CSF。所有模型最终使用完全相同的 canonical PET 与 mask 数组。

论文共享草稿：[汇总 Markdown](run_20261102/supplementary_summary.md)、[汇总 LaTeX](run_20261102/supplementary_summary.tex)、[配对 Markdown](run_20261102/supplementary_paired.md)、[配对 LaTeX](run_20261102/supplementary_paired.tex)。这些表格无 PTID。

内部结果：[逐人指标](run_20261102/per_subject_metrics.csv)、[分布汇总](run_20261102/summary_metrics.csv)、[配对统计](run_20261102/paired_comparisons.csv)、[输入清单](run_20261102/input_manifest.json)、[验证](run_20261102/validation.json)、[执行与恢复记录](run_20261102/RUN_LOG.md)。内部逐人及来源文件不直接公开。历史失败日志按要求保留；最终完成状态由 completion.json 指定。

未训练、重新生成预测、改动原始影像/缓存、修改稿件或正式 supplementary，未提交或推送 Git。
