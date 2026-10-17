# 691 人记录代表什么

**691 不能据此认定为论文生成主对比实验的测试人数。这是该 notebook 从 1100 人的训练加载器中，按已有文件筛出的本次待处理人数。**

2026-10-17 通过 SSH 重新读取 3003 原始 notebook，当前文件与本地归档 SHA256 一致。这里只解析历史源码及保存输出，没有运行模型或重新计算影像指标。

## 直接证据

来源：`3003:/home/data/liutuo/code/mri2pet all data_add personal clip_concat-32_64_64_128-final-nii.ipynb`。下列 Cell 编号沿用既有审计的 notebook JSON 从 0 起计数。

| 位置 | 源码与保存输出 | 含义 |
|---|---|---|
| Cell 8 | `train_data = paired_all_with_desc[:1100]`；`val_data = paired_all_with_desc[1100:]`；输出训练 1100、验证 29 | 此 notebook 保存的划分是 1100/29；这里没有把 691 定义成测试集 |
| Cell 10 | `train_loader` 使用 `train_data`，batch_size=1，shuffle=False | 后续推理所用加载器属于上述训练部分 |
| Cell 15 | 先遍历 `train_loader`，把名字不在 `PET_nii` 目录文件名集合中的对象加入 `missing_names`；输出数量 691 | 691 来自文件存在性筛选，没有独立测试划分步骤 |
| Cell 15 | 再遍历 `train_loader`，仅为 `missing_names` 中的对象生成 PET，保存至 `generated_PET/train` | 这是一次补生成任务 |
| Cell 15 | 每例生成后立即计算 SSIM、PSNR，再保存 NIfTI；日志记录 49:04:03 | 49 小时是这次推理任务耗时；这段代码不是读入所有方法结果后进行统一评估 |

筛选代码查看的是**真实 PET 的 `PET_nii` 保存目录**，并非直接检查合成 PET 输出目录。因此这里只能准确描述为“根据已有文件筛出的待处理对象”，不能保证此前的合成 PET 文件状态。

从原始日志提取到 691 条 SSIM/PSNR 记录和 691 个不同的保存对象，其顺序与打印的 `missing_names` 完全一致。对这些历史打印值取算术平均，得到 PSNR **26.9989756 dB**、SSIM **0.900417928（90.0418%）**。先前所述 27.00 dB、90.04% 的均值本身是正确的，但不能由此推断测试集身份。

该 Cell 加载 `noise2image about mri2pet_method_two_second_part_200.pth`，使用 1000 步扩散推理。它不是此前追查的 `first_part_165.pth`。输入来自 `ADNI1+2_baseline/MRI` 与 `ADNI1+2_baseline/PET`；这里的路径没有直接标明 AV45，不宜仅因均值接近就将其认作论文 Ours AV45 的原始评估记录。

## 对“先推理、再统一评估”的判断

先分别推理各方法、再统一读取合成 PET 评估，是可能存在的实验流程。当前记录既不能排除后续另有评估，也没有证明那一步实际发生过。**即使后续确实进行了统一评估，也不能把这次补生成数量 691 自动变成最终测试人数。**要确认后者，仍需后续评估实际读取的名单或逐例结果。

因此，这条线索可以证明一批历史 PET 推理确实完成并保存过，不能补上论文主对比实验测试人数的缺口。该 notebook 的 1100/29 划分也不能直接当作论文所有方法的统一训练/测试比例。

证据：[源码、哈希与统计收据](receipt.json)、[Cell 8 划分](cell_8_source.py.txt)、[Cell 10 加载器](cell_10_source.py.txt)、[Cell 15 完整源码](cell_15_source.py.txt)、[Cell 15 原始输出](cell_15_original_output.log)、[逐例打印指标](per_subject_logged_metrics.csv)、[691 人待处理名单](missing_subjects.csv)。
