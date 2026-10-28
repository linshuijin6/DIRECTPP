# Stage 4C-4 full train-side PET inference report

## 结论

**COMPLETE。** Full/OT × 两个 generator folds 四组均完成；3,620/3,620 个 train-side PET 通过身份、文件、SHA、数值、MRI/E1 和 cache 不变性核验。Full/OT 在同一 fold 的 PTID×tracer 集合完全一致。

| Model | Outer fold | Subjects | PET | Runtime (s) | Peak GPU GiB |
|---|---:|---:|---:|---:|---:|
| Full | 1 | 457 | 914 | 3373.6 | 8.33 |
| OT | 1 | 457 | 914 | 3373.5 | 8.33 |
| Full | 2 | 448 | 896 | 4244.2 | 8.33 |
| OT | 2 | 448 | 896 | 4244.3 | 8.33 |

## 完整性

- Fold 1：每模型 457 人、914 PET；Fold 2：每模型 448 人、896 PET。
- 总计 905 名唯一 outer-train 受试者、3,620 条唯一 train-side prediction。
- 每条记录均为 Epoch 165、对应 G_f、shape `160×192×160`、float32、finite、范围 `[0,1]`、非恒定。
- 全部记录 `mri_e1_max_abs_error <= 2e-6`，cache hit 已确认，运行前后 cache SHA 不变；四组 complete receipt 均声明 cache tree 不变。
- 未发现 failure marker、额外身份、缺失或重复预测。
- 实际分类输入只通过 `04c4_classification_asset_index.csv` 绑定；outer-train 来自本次正式 receipt，outer-test 来自 4B 冻结 G_f OOF，不使用 cross-OOF 训练输入。

本收口步骤仅汇总和核验已生成预测，没有重新推理、删除或覆盖任何 PET。
