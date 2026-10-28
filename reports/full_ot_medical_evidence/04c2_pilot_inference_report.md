# Stage 4C-2：train-side PET pilot inference

## 结论

**PASS。Full/OT × 两个 generator outer folds 四组 pilot 均完成；32/32 个 PET 体积通过身份、condition/context、数值、MRI 空间锚点和 cache 不变性检查。** 本阶段没有执行全队列推理、原 OOF 重推理或分类训练。

主要证据：

- `04c2_pilot_prediction_manifest.csv`：32 个逐文件记录；SHA-256 `267d1d26f38b18ea78a95293a682493cb9b876f2b4364bffd26f44a021ac9d70`。
- `04c2_pilot_receipt.json`：最终状态 `PASS`。
- `04c2_pilot_config.json`：冻结抽样和派生输出协议。
- `experiments/train_side_inference/run.py`：pilot、check-only、失败收据和最终 QC 实现。

## 1. 执行协议与安全修复

每个 outer fold 只从冻结 `outer_train` 行中按 PTID 排序，依次选择 CN、AD、EMCI、LMCI 各一人。Full 与 OT 使用相同 PTID，每人仅生成 FDG、AV45 两个体积。runner 对单次运行硬编码为 4 人/8 体积，并对全 pilot 断言 `2 folds × 2 models × 8 = 32`；参数错误不能退化为全量推理。

实际样本：

| Outer fold | Generator fold（样本来源） | CN | AD | EMCI | LMCI |
|---:|---:|---|---|---|---|
| 1 | 2 | 002_S_0295 | 002_S_5018 | 002_S_2010 | 002_S_4171 |
| 2 | 1 | 002_S_1261 | 003_S_4152 | 002_S_2073 | 002_S_4229 |

真实推理前重新执行 check-only，四个 checkpoint、Full/OT condition、4B manifest SHA、generator fold、禁止 cross-OOF 和输出隔离均通过。错误 fold 与 outer-test 测试现在调用真实执行选择验证函数，分别因行属于错误 outer fold、`outer_role=outer_test/generator_fold==outer_fold` 被拒绝，不再直接抛出预设异常。

4B manifest 保持未修改。其计划路径与本阶段 pilot 隔离要求的差异通过 `04c2_pilot_config.json` 的派生协议解决：

`/mnt/datas230/users/linshuijin/DIRECTPP_stage4c2_pilot/20261028/epoch165/outer_fold{f}/{full|ot}/{fdg|av45}/generated_{tracer}_{PTID}.nii.gz`

该根目录与原 OOF、checkpoint、condition、cache 和正式 train-side 根隔离。运行目录已存在、文件已存在或路径重叠均 fail-closed。全量 `infer` 在本阶段被禁用，需未来 Stage 4C-3 的独立授权口令。

## 2. 四组实际执行

| Model | Outer fold | 体积 | Runtime (s) | Peak GPU memory | 输出字节 |
|---|---:|---:|---:|---:|---:|
| Full | 1 | 8 | 20.156 | 8,946,178,048 | 78,281,033 |
| OT | 1 | 8 | 14.817 | 8,946,178,048 | 78,767,536 |
| Full | 2 | 8 | 23.670 | 8,946,178,048 | 126,347,531 |
| OT | 2 | 8 | 18.517 | 8,946,178,048 | 120,280,570 |

总输出为 32 个 NIfTI、403,676,670 bytes。每组只有 `complete.json` 状态为 `COMPLETE` 后才计为成功；异常路径会保留 `failure.json` 和部分输出且不得标记 COMPLETE。本次无失败组或额外 NIfTI。

## 3. 身份、context 与数值 QC

32/32 文件逐一复核：

- PTID、diagnosis、outer fold、实际 generator fold、model、tracer 与冻结选择一致；每个 fold 的 Full/OT subject×tracer 集合完全相同。
- checkpoint 均为相应 `G_f` 的 Epoch 165 实物 SHA；Full fold 1/2 分别为 `550ac2c…4ea77`、`f67e4a…4315`，OT 分别为 `573778ad…e69db`、`32b89214…206085`。
- Full context 逐体积等于 `[该 PTID patient token, tracer token]`；OT 等于 `[冻结 empty-patient token, tracer token]`。运行时 tensor SHA 经最终汇总重新构造核验，32/32 一致。
- 实际公式为 `prediction = clamp(MRI + model_velocity(t=0, context), 0, 1)`，与原推理实现一致。
- 写盘前检查 shape `160×192×160`、dtype `float32`、finite、范围 `[0,1]`、非恒定；只有通过后才原子写入。最终重新读盘复核 32/32 通过，identity affine 保持不变。
- 全部预测总体 min/max 为 0/1；最小体积标准差为 0.20817，未发现恒定输出。每文件 SHA 和字节数均与 manifest 一致。

## 4. PersistentDataset 与 MRI 空间核验

每个 PTID 使用 MONAI `pickle_hashing` 计算实际 cache key；对应文件在读取前已存在，并记录于逐文件 manifest。四组运行各自比较执行前后完整 cache 文件 `(name, size, mtime_ns)` 集合：均为 1,857→1,857 且逐项不变，未静默生成、覆盖或删除 cache。

原 receipt 路径已迁移，本次继续使用同 namespace 的只读备份 `v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup`。cache 没有历史逐文件内容 SHA receipt，因此不能声称逐 cache 文件内容 SHA 得到历史闭合；但本次命中 key、文件集合与元数据前后不变均有执行证据。

8 名抽样受试者的推理 MRI 与 E1 NPZ MRI 均为同 shape、float32、finite；最大 `max_abs_error=1.7881393432617188e-07`，低于 Stage 2 冻结门槛 `2e-6`。跨模型显式比较确认同一 fold/PTID 的 Full/OT `mri_array_sha256`、cache key、source MRI SHA 和 E1 cache SHA 完全相同。没有使用 Real PET 误差选择病例、变换或参数。

## 5. DONE 回答与下一阶段门槛

1. **四组是否完成？** 是，Full-F1、OT-F1、Full-F2、OT-F2 均为 COMPLETE，各 8 个体积。
2. **32 个 PET 是否通过 QC？** 是，32/32 通过文件身份、shape、float32、finite、范围、非恒定、SHA 和读盘复核。
3. **context/checkpoint 是否正确？** 是。Full patient+tracer、OT empty-patient+tracer 均逐体积重构核验；四个 Epoch 165 checkpoint 与 outer fold 正确绑定。
4. **PersistentDataset 是否正确命中且未修改？** 是。8 个实际 key 均命中，四组前后完整 cache 文件集合及 size/mtime 不变；限制是不存在历史逐 cache 文件内容 SHA receipt。
5. **是否存在阻止全量推理的问题？** pilot 未发现身份、空间、condition、数值、显存或 cache 阻塞。但当前全量入口被有意禁用，且旧通用 `infer` 尚未提升为与 pilot 完全相同的数量控制、写盘前 QC、cache 前后快照和失败收据协议。因此**不能直接开始全量**；Stage 4C-3 需先把已验证的 pilot 执行路径参数化为冻结全队列模式、签发正式派生 manifest/receipt，并获得单独授权。此为工程门，不是 pilot 数据失败。

本阶段到此停止，未生成其余 train-side PET，未进入分类训练。
