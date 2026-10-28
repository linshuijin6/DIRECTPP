# Stage 4C-1 train-side PET inference runner 预检

## 结论

**PASS（check-only）；未执行真实 PET 推理或分类训练。** 独立 runner 已建立，4B 三个 manifest、Full/OT 四个 Epoch 165 checkpoint、两套 condition 与冻结 generator fold 均通过身份核验；七项 fail-closed 安全测试全部通过。当前节点依赖与 CUDA 可用，可在用户另行授权的 Stage 4C-2 先执行单一 `model×fold` 小样本验证。本阶段未加载生成器、未执行 forward、未生成 PET。

实现与机器可读结果：

- `experiments/train_side_inference/run.py`
- `reports/full_ot_medical_evidence/04c1_check_only_results.json`

## 1. 输入、fold 与生成计划

check-only 重新核验了 4B config 和三个 manifest 的 receipt SHA-256、字节数与行数，并逐行验证：`outer_test ⇔ generator_fold == outer_fold`，`outer_train ⇔ generator_fold != outer_fold`；checkpoint/condition 必须按 `outer_fold=f` 绑定 `G_f`；train-side 行的 cross-OOF 使用状态必须为 `FORBIDDEN_AS_OUTER_TRAIN_INPUT` 且预测状态为 `PLANNED_MISSING`。E1 test fold 只保留作审计字段，没有参与选择。

三项任务冻结人数仍为 469/740/436。任务受试者并集为 905 人：

| outer fold | train-side 来源 generator fold | 受试者 | 每模型双 tracer 体积 |
|---|---:|---:|---:|
| 1 | 2 | 457 | 914 |
| 2 | 1 | 448 | 896 |

因此最小分类所需的四组总计划量是 **3,620 个体积**（1,810/模型），而不是把整个 1,105 人双示踪剂队列都补推理的 4,420 个上限。此处仅去除三个任务之间的重复 PTID，不改变任何任务、队列或 fold。

## 2. checkpoint 与 condition 身份

四个实物 checkpoint 的内容 SHA-256、字节数及各自 receipt 均匹配 4B 冻结值；receipt 内 generator fold、one-based epoch 165、checkpoint SHA 和 model-state SHA 一致：

| 模型 | G1 SHA-256（前 12 位） | G2 SHA-256（前 12 位） |
|---|---|---|
| Full | `550ac2c4b1ef` | `f67e4a788eff` |
| OT | `573778adc271` | `32b89214b55e` |

Full condition SHA 为 `bbcd413100d8...`，形状为 patient `[1857,512]`、tracer `[2,512]`。OT runtime 已由现有冻结资产与 checkpoint receipts 完整恢复并核验：模式为 `tracer_only_fixed_empty_patient`，empty-patient `[1,512]` 的 tensor SHA 为 `691e8c92170f...`，tracer `[2,512]` 与 Full tracer token 逐元素相同且 FDG/AV45 token 不同；OT 两个 checkpoint receipt 均绑定同一 OT condition SHA `e1dfd6399d59...` 和 empty-patient SHA。未猜测或替换训练超参数，也未用 Full condition/权重代替 OT。

## 3. MRI 预处理 cache 与执行环境

runner 复用原作者实现的 `build_transform`、PersistentDataset cache、U-Net `new_model`、`MRI + velocity` 与 clamp 预测定义。冻结 input-hash manifest SHA、cache namespace 和 1,857 个 cache 文件数量一致。

原 cache receipt 记录的目录已迁移；当前使用同 namespace 的只读备份 `v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup`，文件数为 1,857。该 cache 没有逐文件内容 SHA receipt，故逐 cache 文件 SHA 标记为 **UNAVAILABLE**；已验证的是冻结 input/condition hash 绑定、完全相同 namespace 及完整文件集合。正式执行仍由 PersistentDataset 按预期 cache key 选择文件。

当前核验解释器 `/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python` 可导入 PyTorch 2.5.1、MONAI 1.5.1、Nibabel 5.3.2，CUDA 12.4 可用。默认 shell 的 base Python 不含 torch，不能用于执行 runner。

## 4. 输出隔离与运行记录

新输出根固定为 `/mnt/datas230/users/linshuijin/DIRECTPP_stage4c_train_side/20261028/epoch165`；check-only 未创建该目录。布局为：

`outer_fold{f}/{full|ot}/{fdg|av45}/generated_{tracer}_{PTID}.nii.gz`

runner 拒绝输出根与原 OOF、checkpoint、condition 或 cache 的相同/祖先/子孙路径关系；当前 `model×fold` 运行目录或预测文件已存在时立即拒绝覆盖。四组可独立顺序执行，已完成组不会阻止尚未开始的其他组。

后续每个预测记录 PTID、outer/generator fold、model、tracer、checkpoint SHA、condition SHA、4B runtime config SHA、cache namespace、source MRI SHA、shape、dtype、finite、min/max、预测路径和预测 SHA。NIfTI 保持原推理的 identity affine；其用途是与已验证数组索引一致的分类输入，不把 header 视为空间对齐证据。

## 5. fail-closed 验证

以下七种故障均被 runner 拒绝：

1. 错误 generator fold；
2. 错误 checkpoint SHA；
3. Full/OT condition 混用；
4. 输出指向原 OOF；
5. outer-test 受试者进入 train-side；
6. 已存在运行输出；
7. OT runtime 缺失或不完整。

此外，真实推理子命令必须同时给出一个明确的 `model`、一个 `outer-fold` 和精确的 Stage 4C-2 acknowledgement；check-only 不具备触发 forward 的路径。

## 6. 对 DONE 条件的回答

1. **runner 是否可用：是。** 独立实现已通过语法、依赖、冻结身份、选择规则、路径隔离和故障注入检查。
2. **四个 checkpoint 是否正确绑定：是。** Full/OT 的 G1/G2 均绑定 outer fold 1/2、Epoch 165，并与实物及 receipt SHA 一致。
3. **OT runtime 是否完整恢复：是。** empty-patient+tracer tensor、模式、Full tracer 绑定及两个 OT checkpoint receipt 一致。
4. **check-only 是否全部通过：是。** 状态为 `PASS_CHECK_ONLY`，安全测试为 `PASS`；模型加载、forward 和 PET 写入均为 false。
5. **能否进入四组小样本真实推理：技术上可以，但须下一阶段单独授权。** 建议依次对 Full-G1、OT-G1、Full-G2、OT-G2 各取预先固定的同一小样本，核对输出 receipt、数值范围和 Full/OT 条件记录后再决定是否扩展；本阶段未执行该步骤。

未解决限制：cache 缺少逐文件 SHA receipt；正式推理前应保留当前 namespace/文件集合核验，并在首个小样本运行中确认实际 cache key 命中。该限制不影响本次 check-only PASS，但需要在 Stage 4C-2 的执行收据中明确记录。
