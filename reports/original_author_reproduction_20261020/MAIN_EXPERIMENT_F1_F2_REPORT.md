# 主实验生成器两折复现报告（Fold 1 / Fold 2）

完成日期：2026-10-26。实验身份：`original_author_training_reconstruction`。

## 结论范围

本报告记录按原作者训练代码语义重新执行的生成器两折训练与 OOF 推理。Fold 1 和 Fold 2
均完成 200 个 epoch；第 165 轮是预注册主终点，第 200 轮是源码训练循环终点。

这些结果证明本次新复现运行及其固定两折 OOF 结果已经完成，不证明找回了论文历史运行的
fold 身份、未设置的训练随机种子或论文 Fig. 2 的原始结果链。本报告只涉及 MRI→FDG/AV45
生成，不包含下游三折分类结果。

## 实验协议

- Cohort：1,857 名唯一受试者。
- Split：`KFold(n_splits=2, shuffle=True, random_state=42)`，不分层，按受试者分折。
- 留出集：Fold 1 为 929 名；Fold 2 为 928 名；两个留出集互斥并覆盖全 cohort。
- 有效目标：FDG 1,598 例，AV45 1,365 例；每个 endpoint 合计 2,963 个 OOF 影像指标行。
- 训练：200 epoch；batch size 1；学习率 `2.5e-5`；零起算 epoch 140 开始蒸馏阶段。
- 随机性：原作者 notebook 未设置正式训练 RNG seed，本次同样未设置；运行记录保存逐轮
  sample-order 和 RNG 哈希，但不能把不同折间差异解释为仅由数据分折造成。
- 指标：SSIM、PSNR、MSE、MAE，均在 `[0,1]` 归一化后的完整预处理体积上计算。
  当前实现没有应用 brain mask，因此本报告不能替代 R3-11 要求的 brain-mask 内指标。

## 身份与配置核验

| 项目 | SHA-256 / 值 |
|---|---|
| Cohort | `91ee8eeec5ea853c4517df868e85fccd2857164a8e4171ba81e45121e5dc9311` |
| Split manifest | `007e49835ed44c73dea69a94e390dded33c495c21033089f83d05b429519977c` |
| Input hashes | `3f362cdb3ebe8a945b106cc6974e4fbcea9e450474f3cc1f0db28a88ce81ed07` |
| Conditions | `bbcd413100d8ece3e878acffc1969723d091f64c49c57c76b486bd474f84384a` |
| Fold 1 config | `68d1bbebe4604cede9c701fe46d51c6f7187976c6b19424e7efef5833dfa531f` |
| Fold 2 config | `7f6753b63ba879f37b569d9adee5e7df83c3267d009fc5992ed3ce6c5730036a` |

两个 config 哈希的差异只来自云端与本地的四个绝对路径字段：`report`、`assets`、
`data_root` 和 `persistent_cache_root`。实验参数、源码契约、cohort、split 与条件身份一致。

## 训练结果

| Fold | Epoch 165 train loss | Epoch 200 train loss | Epoch 200 monitored held-out loss | Epoch 165 checkpoint SHA-256 | Epoch 200 checkpoint SHA-256 |
|---|---:|---:|---:|---|---|
| 1 | 0.00105712 | 0.00076273 | 0.00477829 | `550ac2c4b1ef27b0dbb5624445dace2a04f58a84354e4900810509401cc4ea77` | `18977785fd4e0ccdb797648f9ecb139f81dfdf68923621c7b239d7fcb9fd78f6` |
| 2 | 0.00109877 | 0.00078362 | 0.00453795 | `f67e4a788eff3d958edd1d0da8cc739691affc59de84bdf3a1ae1f2821ce4315` | `58a5ae21594ddb4268972e997fd1a97e37cd444522ec415a54b91f0912798690` |

两折均完成 200 轮且损失为有限值。训练损失低于留出监测损失；这个差距是描述性观察，
不能单独证明泛化充分、等效或不存在过拟合。

## OOF 生成指标

<!-- OOF_RESULTS_START -->

四次推理均已完成并通过收据哈希、行数、NIfTI 数量、唯一身份和有限值检查。第 165 轮与
第 200 轮各覆盖 1,857 名受试者、FDG 1,598 例和 AV45 1,365 例；两个 endpoint 合计
5,926 条指标记录。

### 完整 OOF 汇总（两个互斥留出折合并）

数值为逐影像 mean ± sample SD。

| Endpoint | Tracer | n | SSIM | PSNR | MSE | MAE |
|---|---|---:|---:|---:|---:|---:|
| Epoch 165（主） | FDG | 1,598 | 0.921129 ± 0.041683 | 27.2230 ± 2.1450 | 0.002244 ± 0.002680 | 0.024129 ± 0.009614 |
| Epoch 165（主） | AV45 | 1,365 | 0.884408 ± 0.040564 | 24.9664 ± 2.2675 | 0.003729 ± 0.003325 | 0.030956 ± 0.011034 |
| Epoch 200（次） | FDG | 1,598 | 0.925662 ± 0.042424 | 27.2439 ± 2.1116 | 0.002226 ± 0.002690 | 0.023680 ± 0.009474 |
| Epoch 200（次） | AV45 | 1,365 | 0.886382 ± 0.040522 | 24.9359 ± 2.2058 | 0.003731 ± 0.003326 | 0.030743 ± 0.010916 |

### 逐折汇总

| Endpoint | Fold | Tracer | n | SSIM | PSNR | MSE | MAE |
|---|---:|---|---:|---:|---:|---:|---:|
| 165 | 1 | FDG | 792 | 0.924699 ± 0.047564 | 27.1277 ± 2.1689 | 0.002350 ± 0.003466 | 0.024094 ± 0.010705 |
| 165 | 1 | AV45 | 690 | 0.885751 ± 0.045946 | 24.8554 ± 2.1939 | 0.003838 ± 0.004120 | 0.031192 ± 0.012064 |
| 165 | 2 | FDG | 806 | 0.917621 ± 0.034627 | 27.3166 ± 2.1184 | 0.002139 ± 0.001556 | 0.024163 ± 0.008411 |
| 165 | 2 | AV45 | 675 | 0.883034 ± 0.034179 | 25.0799 ± 2.3365 | 0.003618 ± 0.002236 | 0.030714 ± 0.009873 |
| 200 | 1 | FDG | 792 | 0.922445 ± 0.048477 | 27.2207 ± 2.1463 | 0.002297 ± 0.003477 | 0.023912 ± 0.010523 |
| 200 | 1 | AV45 | 690 | 0.884211 ± 0.045937 | 24.9106 ± 2.1960 | 0.003797 ± 0.004159 | 0.030982 ± 0.012089 |
| 200 | 2 | FDG | 806 | 0.928823 ± 0.035231 | 27.2667 ± 2.0780 | 0.002157 ± 0.001570 | 0.023451 ± 0.008316 |
| 200 | 2 | AV45 | 675 | 0.888601 ± 0.034003 | 24.9617 ± 2.2170 | 0.003664 ± 0.002168 | 0.030498 ± 0.009572 |

### Endpoint 配对变化

下面是同一受试者 Epoch 200 − Epoch 165 的均值变化，不是优效或等效检验。

| Tracer | n | ΔSSIM | ΔPSNR | ΔMSE | ΔMAE |
|---|---:|---:|---:|---:|---:|
| FDG | 1,598 | +0.004533 | +0.020911 | −0.00001760 | −0.0004493 |
| AV45 | 1,365 | +0.001974 | −0.030561 | +0.00000180 | −0.0002130 |

描述性结果显示 FDG 的 SSIM、PSNR、MSE 和 MAE 整体优于 AV45。第 200 轮相对第 165 轮
没有在全部指标和两个折上保持一致方向：例如 Fold 1 的两种 tracer SSIM 略降，而 Fold 2
略升。第 165 轮仍应作为预注册主终点；不能仅凭第 200 轮的部分均值改善将其改作主终点，
也不能由这些描述性差异推断统计优效或等效。

<!-- OOF_RESULTS_END -->

## 建议解读顺序

1. 先读取本文件，确认实验身份、endpoint 和结论边界。
2. 用 `oof_summary/by_fold_summary.csv` 比较 Fold 1/Fold 2，观察跨折稳定性。
3. 用 `oof_summary/distribution_summary.csv` 读取完整 OOF 的每 tracer 分布汇总。
4. 用 `oof_summary/per_subject_metrics.csv` 检查分布、极端病例及第 165/200 轮的配对变化。
5. 用 `training_epochs.csv` 检查训练轨迹；不要用训练 loss 代替 OOF 图像质量。

## 文件说明

- `training_summary.csv`：两折训练完成状态、终点 loss、checkpoint 与数据身份哈希。
- `training_epochs.csv`：两折全部 400 个 epoch 的逐轮训练记录。
- `oof_summary/by_fold_summary.csv`：按 endpoint、fold、tracer 汇总的均值、标准差和分位数。
- `oof_summary/distribution_summary.csv`：合并两个互斥留出折后的完整 OOF 分布汇总。
- `oof_summary/paired_endpoint_deltas.csv`：同一受试者第 200−165 轮的配对描述性变化。
- `oof_summary/per_subject_metrics.csv`：全部逐受试者、逐 tracer、逐 endpoint 指标及输出哈希。
- `oof_summary/completion.json`：代码入口生成的两折 OOF 完成收据。
- `oof_summary/analysis_manifest.json`：四次推理收据、汇总文件哈希与完整性检查。
