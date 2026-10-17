# 历史实验是怎样做的：165 生成器、分类名单与 OASIS

**后续作者说明（2026-10-17）：用户转述生成器采用两折交叉训练，合并留出预测为 OOF 合成 PET 后用于三折分类。下文1856/1等记录仍成立，但尚未与作者所述两折流程连接；不能仅凭分类被试与165训练名单相交，就认定论文分类输入发生泄露。更新后的查找目标与结论边界见[作者说明](../author_protocol_clarification_20261017.md)。**

本轮于 2026-10-17 通过 SSH 只读访问 3002、3003、3014，读取原 notebook 及保存输出、JSON、CSV，并核对源文件哈希。未执行历史 notebook、训练或影像推理，也未修改原服务器材料。下文只描述查到的历史实验，不讨论修稿。

**阅读范围：本页1856/1指生成器训练及训练期间验证，不代表论文生成对比指标的测试集。论文对比指标的原始Excel已另行找到，但实际测试名单仍未恢复，详见[生成对比测试集专项核查](GENERATION_COMPARISON_TEST_SET.md)。**

**目前最明确的结论：165 主生成记录使用 ADNI 1856 人训练、1 人验证；分类存在多套历史分支，现已从保存输出提取出它们的被试与验证名单；OASIS 没有出现在这些已恢复的主训练及分类名单中。**

**165 权重对应的训练过程**

核查对象是 3002 上的 `/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized/first_part_165.pth`。本轮源端 SHA-256 为 `fa43adae089aefbe66df8d1f196a618662b75dbdc880cce10923dd22b844165e`，与此前选定的 165 权重一致。CPU 只读加载显示：包含 model、optimizer、epoch，epoch=164（零起算），优化器 step=306190；没有内嵌被试名单。

对应的原 notebook 为 3002 `/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb`：

1. Cell 2 从 ADNI1234 目录中的 MRI、AV45、FDG 和元数据组织 1857 名 ADNI 被试，保存输出为 1856 人训练、1 人验证。
2. Cell 3 明确保存了“Loaded 1856 training samples”及验证 ID `011_S_4105`。Cell 4 从同一对 JSON 建立 DataLoader，batch_size=1。
3. Cell 10 加载 `first_part_154.pth` 继续训练；保存的 Epoch 154–164 进度均为 1856/1856。该 cell 按 `first_part_{epoch+1}.pth` 保存权重，因此 epoch=164 对应文件名 165。
4. Cell 11 加载上述 165 权重，对 **train_loader** 做推理。本轮从该 cell 保存的 MRI 写出路径中提取到 1856 个唯一 ID，逐个比对，恰好全部属于恢复的 1856 人训练名单。

训练名单在原服务器 3002 的 `ADNI1234_mri_fdg_av45_original/train_data_with_description.json`，验证名单在同目录的 `val_data_with_description.json`。两者与先前补入证据包的 1856/1 文件逐字节相同，并集正好覆盖元数据的 1857 人。训练组为 CN 576、AD 317、EMCI 291、LMCI 152、MCI 520；验证为 CN 1 人。

可直接查看 [165 的逐人训练/验证名单](generator_165_subject_roles.csv)。这里的 1 人是验证对象，不是独立测试队列。

现存的 500/39 ADNI2 文件没有被上述续训 cell 加载，不能把它们用作该 165 运行的训练名单。3003 的另一对同名 JSON 现在是 1857/0，也不能替代 notebook 保存的历史 1856/1 划分。3002 原路径 `ADNI1234_mri_fdg_av45` 当前已不存在，恢复文件保存在带 `_original` 的目录；本轮没有重命名或修复这些路径。

**仍有一个历史边界：**154 权重目前未在该 checkpoint 目录找到，保存日志也缺少 48–153 的连续记录。因此，1856/1 是现有代码、名单和末段训练输出共同支持的历史训练划分；不能声称已经证明此前每个阶段都从未换过数据，或该权重内原生保存了这份名单。

**分类任务实际使用了哪些人**

本轮从 notebook 已保存的 `print(paired_all_with_desc)` 和 `print(val_data)` 中解析真实列表，未重新随机分折。表中的验证 ID 直接来自历史输出；训练 ID 是该分支总名单扣除已打印验证名单得到的补集。MCI/CN 分支在分折循环结束后建立 loader，保存的是最后一次切分；训练循环未按新 fold 重建 loader，不能把下表解释为已恢复三套不同的有效测试折。

| 历史分支 | 队列组成 | 建立 loader 的训练/验证人数 | 验证对象与 165 训练名单重合 | 逐人名单 |
|---|---|---|---|---|
| AD/CN：3003 隐藏 DenseNet 版本，读取 ADNI1+2 MRI/PET 的 .mat 文件 | AD 230、CN 290，共520 | 400 / 120 | 120 / 120 | [名单](AD_CN_520_subject_roles.csv) |
| EMCI+LMCI/CN：3002 单 PET 配对版本，路径指向生成 FDG | EMCI 290、LMCI 151、CN 371，共812 | 542 / 270 | 270 / 270 | [名单](EMCI_LMCI_vs_CN_812_subject_roles.csv) |
| EMCI+LMCI/CN：3002 Copy2，MRI+真实 FDG/AV45 配对 | EMCI 287、LMCI 149、CN 305，共741 | 494 / 247 | 246 / 247；另外1人是生成器验证对象 | [名单](EMCI_LMCI_vs_CN_741_real_Copy2_subject_roles.csv) |
| 同队列 Copy3，真实 FDG/AV45 版本 | 同上741人 | 494 / 247 | 247 / 247 | [名单](EMCI_LMCI_vs_CN_741_real_Copy3_subject_roles.csv) |
| 同队列顶层 DenseNet，生成 FDG/AV45 版本 | 同上741人 | 494 / 247 | 247 / 247 | [名单](EMCI_LMCI_vs_CN_741_generated_subject_roles.csv) |
| sMCI/pMCI：3003 顶层 DenseNet，读取 ADNI1+2 MRI_nii/fake_PET | sMCI 418、pMCI 83，共501 | 420 / 81 | 81 / 81 | [名单](sMCI_pMCI_501_subject_roles.csv) |
| 较宽 MCI/CN：3014 隐藏 DenseNet | sMCI 418、pMCI 83、MCI 108、CN 290，共899 | 730 / 169 | 168 / 169 | [名单](broad_MCI_vs_CN_899_subject_roles.csv) |

这说明分类不是一套统一的“1857 人实验”。同为741人的几个版本，保存的验证 ID 也不同，已分别保留，未按人数相同合并。sMCI/pMCI 是另一项历史任务，不能重命名为 EMCI/LMCI。此次指定目录及归档候选中仍未找到明确的 EMCI vs LMCI 独立二分类主实现。

表中“与165训练重合”只是身份交集。AD/CN 的520人分支读取旧 MRI/PET 目录，不能仅凭身份重合就声称它使用了165合成 PET；而3002的生成 PET 分支确实引用生成影像目录。上述分支也尚未逐一绑定到论文 Figure 5 的全部33行，不能把本表当成33组最终实验的完整记录。

后续补充：本轮已用三个现存fold权重的3通道结构及BatchNorm批次计数，与Copy2的Cell 19原始日志建立强匹配，最佳保存轮次为38/44/14；该段对应MRI+真实FDG+真实AV45的EMCI+LMCI/CN任务。完整日志和交叉核对见[三个fold权重的原始训练记录](FOLD_TRAINING_RECORDS.md)。

**OASIS 在哪里出现，是否进入该阶段**

- 1856/1 生成名单全部为 ADNI 格式 ID，数据路径也为 ADNI；与3003现存548名 OASIS-3 候选的 ID 交集为0。已恢复的各分类总名单和验证名单也全部为 ADNI ID，无 OASIS 路径或 ID。
- 3003 `/home/djh_OASIS3` 确有 OASIS-3 预处理材料。`pup_files_complete.csv` 为548人（CN463、AD85），`AV45_nii_used` 为638个 session 目录。找到这些材料可以证明 OASIS 数据存在，不能证明它被送进了165训练或上述分类 loader。
- 3014 的一个隐藏分类 notebook 的 Cell 24 出现 `Task502_OASIS3/imagesTs`。该 cell 是独立的影像方向修正示例，execution_count=None，没有连接分类数据列表或训练 loader，不能据此判断分类训练混入 OASIS。
- 3002 的 `oasis_av45fanhua` 目录仅见 `T1.nii` 和 `av45RAI.nii.gz` 两个文件；没有被试名单或训练消费记录。未将它当成完整外部验证。

**据此次恢复的运行记录，OASIS 没有被并入165主训练及这些分类名单。** 已找到的 OASIS 证据主要是预处理和候选资产；仍未恢复其完整419人模型评估链。这一结论不扩大为“整个项目历史上从未训练或评估过任何 OASIS 数据”。

**证据入口与复查方式**

- [主要结论与交集机器记录](historical_summary.json)：各分支的来源、cell、人数、类别及交集。
- [所有已恢复分类分支的逐人角色](classification_subject_roles.csv)：区分直接打印的验证成员和推导出的训练补集。
- [历史输出直接提取的被试记录](historical_printed_subjects.csv)及[notebook目录](notebook_cohort_catalog.json)：保留不同版本，不自动合并。
- [源端与归档哈希比较](live_vs_archive_hashes.csv)：本轮读取的有既存索引的文件，逐项核对是否变化。
- `live_3002.json`、`live_3003.json`、`live_3014.json`：SSH取得的代码、文本输出和指定名单快照。3014快照移除了图片输出，仅保留源码、文本及原文件哈希。
- `targeted_*.json`：名单、权重哈希、指定目录清单及访问错误。3014的`nohup.out`仍为PermissionError，未改变权限；失效历史目录按原样登记。
- `*_source.txt`：按 cell 和 cell内行号整理的源码及简短输出；原始完整文件仍在原归档中。

本轮程序为标准库只读采集与文本解析脚本。依次运行`collect_live.py <3002|3003|3014>`、`collect_targeted.py <节点>`、`extract_history.py`、`summarize_history.py`可重查当前文件状态；新的源端状态可能与本轮快照不同。全程没有执行任何历史研究cell。脚本已检查生成名单互斥/覆盖、分类ID唯一、验证集为总队列子集以及逐人交集。
