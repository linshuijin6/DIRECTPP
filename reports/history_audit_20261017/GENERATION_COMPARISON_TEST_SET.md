# 论文生成对比指标到底基于哪份测试名单？

**截至本轮SSH核查：165对应的1856人训练名单已恢复；论文生成对比指标的实际测试名单尚未恢复。不能把训练过程的1人验证集，或1856人训练集，直接认定为论文对比实验的测试集。**

本页专门回答SSIM、PSNR、MSE、MAE生成对比实验，不讨论分类或修稿。核查日期：2026-10-17。

**已经找到原始对比汇总表**

在3002的`/home/ssddata/liutuo/liutuo_data/新建 XLS 工作表.xls`找到7种方法×3组评估×4项指标的原始表。本轮只读复制到[source_materials/generation_comparison_original_3002.xls](source_materials/generation_comparison_original_3002.xls)，SHA-256为`92643950a8408dac3465bf97d65850ac7d1e25c85dfe84256f598dcde8a005df`。

表内84个数值与已定位绘图notebook的3组数组逐项一致。DIReCT++对应行为：

| 表内评估组 | SSIM (%) | PSNR (dB) | MSE (%) | MAE (%) | 实际测试被试名单 |
|---|---:|---:|---:|---:|---|
| ADNI FDG | 89.94 | 28.72 | 0.33 | 2.96 | 尚未恢复 |
| ADNI AV45 | 88.21 | 28.09 | 0.39 | 2.73 | 尚未恢复 |
| OASIS AV45 | 83.97 | 26.79 | 0.94 | 3.01 | 尚未恢复 |

这份Excel只有一张非空工作表（9行×15列，另两张为空），没有被试ID、样本数、fold、逐人结果、隐藏数据表或批注；Workbook流中没有公式记录。它证明汇总数字的保存位置，无法单独告诉我们这些数字由哪些被试计算而来。绘图notebook也直接使用这些汇总数组，没有在这3个绘图cell中读取逐人指标或测试名单。

证据：[Excel提取与来源](generation_original_spreadsheet.json)、[7种方法全部21组数值](paper_generation_plot_values.csv)、[绘图源码](generation_radar_source.txt)。

**三种集合必须分开理解**

| 集合 | 本轮实际核实结果 | 能否当作论文对比测试集 |
|---|---|---|
| 165相关历史训练名单 | ADNI 1856人，[逐人名单](generator_165_subject_roles.csv)中role=train | 不能据此认定 |
| 训练过程的验证名单 | ADNI 1人，011_S_4105，用于训练期间验证 | 没有证据认定论文对比数字就来自此人 |
| 论文SSIM/PSNR等对比指标的评估名单 | 汇总表已找到，实际名单、逐人聚合及折记录未恢复 | 目前无法给出经过核实的人数和ID |

论文文字声称ADNI内部交叉验证、OASIS外部评估，但方法与结果部分还存在两折/三折冲突。论文的协议描述不能代替实际运行名单。OASIS候选548人/638session也不能直接替代论文419人的实际评估对象。

**为何也不能把165对训练集推理的1856人当作答案**

原new-final notebook Cell 11加载165，对train_loader推理，历史输出确实包含1856名训练对象的MRI写出记录，并有FDG 1597条、AV45 1364条逐人SSIM/PSNR。不同示踪剂有缺失，故指标记录少于1856。

只对这些已经保存、精度为小数后4位的历史逐人指标取均值，得到：

| 历史训练集推理 | 指标记录数 | SSIM均值 (%) | PSNR均值 (dB) | 论文汇总表PSNR |
|---|---:|---:|---:|---:|
| FDG | 1597 | 95.92 | 32.67 | 28.72 |
| AV45 | 1364 | 93.77 | 31.26 | 28.09 |

它们与论文汇总表不一致，不能直接认定论文使用的就是这次训练集推理的逐人算术均值。不同预处理、运行版本、筛选或聚合方式的可能性尚无证据区分；本轮不据此推断汇总数字产生原因。

证据：[历史逐人指标](generator_165_historical_inference_metrics.csv)、[对比追踪记录](generation_comparison_trace.json)。这是文本输出解析，没有重新推理或重算影像指标。

**其余已排查线索**

3002的`test`目录实际是2名ADNI对象的示例文件；`test1`也只有2名输入对象，部分基线输出仅1人，`ours`的文件名还对应另外的ID。它们不能仅因目录名含test就被当作论文统一评估队列；目录清单在[comparison_example_directories.json](comparison_example_directories.json)及[nested_baseline_directories.json](nested_baseline_directories.json)。

GitHub候选源码里出现`test_size=558`，但保存输出仍为1856/1，且与new-final共享历史输出；这不证明当时确实按558人独立测试，未重建一个558人名单来冒充历史结果。

本轮还对三台指定服务器的相关源目录做了有深度和资源上限的评估文件名搜索，原始Excel由这次搜索找到。3003搜索触及3000目录的上限，3014的nohup.out仍无读取权限；未声称穷尽全服务器。搜索记录为`evaluation_artifact_search_*.json`。

**当前缺失的准确对象，是把这张汇总表接回具体评估运行的材料：输入测试名单、各方法的逐人指标、以及跨折或跨样本汇总记录。找到其中可相互核实的一组，才能回答论文真正测试了哪些人。现在没有依据回答“就是1人”，也没有依据回答“肯定是1856人”。**
