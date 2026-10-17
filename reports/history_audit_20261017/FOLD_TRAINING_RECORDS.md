# 三个 fold 权重的原始训练记录

**已找到与现存三个 `best_model_fold_*.pth` 强匹配的原始训练记录。它们是分类器权重，不是165生成器的三个fold。**

来源为3002的`/home/ssddata/liutuo/mri2pet all data-_mri classification-densenet-Copy2.ipynb`，Cell 19（从0计数）。本轮通过SSH重新读取原文件，SHA-256仍为`ba066e8fea5c403aa0fef6927dd1ea8f6ec102658dd5ce85f6af900f592f0f81`。

**这段记录做的实验**

- 任务：EMCI+LMCI合并为阳性，对比CN。
- 队列：741人，EMCI287、LMCI149、CN305。
- 保存的训练/验证划分：494/247；三次训练沿用同一组DataLoader。
- 输入：MRI、真实FDG、真实AV45，3通道DenseNet121，2分类输出。
- 每次训练200轮，每2轮验证一次；原始输出完整保留600条逐轮训练loss和300条验证指标。
- 以`ACC + AUC`最大值保存各次最佳模型，文件名为`best_model_fold_1.pth`、`best_model_fold_2.pth`、`best_model_fold_3.pth`。

| 文件 | 日志中的最佳轮次 | 当轮ACC | 当轮AUC | 权重内训练批次计数 | 原文件修改时间（北京时间） |
|---|---:|---:|---:|---:|---|
| best_model_fold_1.pth | 38 | 70.45% | 75.88% | 3762 | 2025-05-17 23:00:28 |
| best_model_fold_2.pth | 44 | 72.87% | 73.79% | 4356 | 2025-05-18 01:43:49 |
| best_model_fold_3.pth | 14 | 70.85% | 74.61% | 1386 | 2025-05-18 03:59:25 |

上述指标直接取自保存的原始日志，不是新跑的评估结果。三次均训练到200轮，表中轮次指最佳模型保存位置。

**如何将日志与这三个文件对应起来**

本轮在CPU上只读加载3002根目录下的三个权重。它们都是3输入通道、2输出类别的DenseNet参数字典。每个文件121个BatchNorm层的`num_batches_tracked`均一致。494个训练样本、batch_size=5时，每轮99批，因此三个计数分别满足：

- 3762 = 99 × 38；
- 4356 = 99 × 44；
- 1386 = 99 × 14。

这与Cell 19三个fold最后保存最佳模型的轮次全部一致。另三段同样使用3通道、保存相同文件名的候选日志，最后保存轮次分别为94/142/174、188/58/194、46/18/40，均不匹配。比较见[取证收据](fold_training_records/recovery_receipt.json)，权重身份见[权重检查记录](fold_checkpoint_identity.json)。

因此这是比同名文件更强的对应证据，但权重本身仍只有state_dict，没有内嵌run ID、epoch或被试名单；本页将其称为“强匹配”，不声称有原生运行绑定。文件修改时间作为辅助记录，不单独当作训练起止时间。

**可直接查看的原始记录**

- [完整原始训练输出](fold_training_records/original_cell_19_training.log)
- [Fold 1原始输出](fold_training_records/fold_1_original_training.log)、[Fold 2原始输出](fold_training_records/fold_2_original_training.log)、[Fold 3原始输出](fold_training_records/fold_3_original_training.log)
- [原cell源码](fold_training_records/original_cell_19_source.py.txt)和[原cell对象](fold_training_records/original_cell_19.json)
- [600条训练loss](fold_training_records/training_loss_600_epochs.csv)、[300条验证记录](fold_training_records/validation_metrics_300_records.csv)、[三个最佳模型的日志指标](fold_training_records/best_checkpoint_logged_metrics.csv)
- [该分支逐人训练/验证名单](EMCI_LMCI_vs_CN_741_real_Copy2_subject_roles.csv)：验证名单来自历史打印输出；训练成员为总名单扣除验证名单得到的补集。

这次补齐的是这三个分类权重的训练记录。论文生成对比指标的测试名单仍是另一项未恢复材料，见[专项说明](GENERATION_COMPARISON_TEST_SET.md)。没有执行训练、推理或历史cell，也没有修改原服务器文件。
