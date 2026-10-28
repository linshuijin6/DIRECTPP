# Stage 4C-3 Readiness：全量 train-side inference 安全协议

## 结论

**PASS_DRY_RUN。当前 runner 可正常启动，正式 `infer` 已与 4C-2 pilot 共用唯一的受控执行与 QC 实现；四组共 905 名唯一受试者、3,620 条预测路径全部通过 dry-run。** 本阶段没有加载生成器、执行 forward、创建正式输出目录或写入 PET，也没有修改 4C-2 pilot 输出。

证据：

- runner SHA-256：`7e1e84c89aae8ae9df42e870de2a969b67adec045e6e7c5136aac56eaba7cf3f`
- `04c3_dry_run_receipt.json` SHA-256：`37e689985011e688955db10deac9104b766998844c8d3211911d77b0d23abf54`
- 冻结计划 SHA-256：`90bf9386eab2e688b15162f97e337f131c33cfbc15b7beead86c73ba203e01f1`

## 1. Parser 与实际命令行验证

已删除重复的 `pilot` 注册；源码中只有一次 `sub.add_parser("pilot")`。以下命令均以当前解释器实际启动并成功显示帮助，而非仅执行 `py_compile`：

- `run.py --help`
- `run.py check-only --help`
- `run.py pilot --help`
- `run.py infer --help`
- `run.py dry-run --help`
- `run.py finalize-pilot --help`

同时逐一调用 parser 验证 handler 与默认输出根：`pilot/finalize-pilot` 指向既有 Stage 4C-2 pilot 根；`check-only/dry-run/infer` 指向新的正式根。新的 check-only 实际运行结果为 `PASS_CHECK_ONLY`，计划数为 3,620，全部拒绝测试通过；结果写入临时文件，没有覆盖 4C-1/4C-2 收据。

`infer --model Full --outer-fold 1` 缺少授权参数时由 argparse 拒绝，退出码 2；错误授权值由执行门拒绝，退出码 1。两者均发生在 preflight、checkpoint state 加载和输出目录创建之前。

## 2. 统一的正式执行实现

旧的低保护全量 `command_infer` 已删除。`pilot` 与 `infer` 现在都调用 `command_controlled_inference`，差异仅为：

- pilot：冻结每折 4 人、每组 8 体积、Stage 4C-2 隔离根；
- formal：冻结 fold 1 为 457 人/914 体积，fold 2 为 448 人/896 体积、Stage 4C-3 正式隔离根。

统一实现包括 4C-2 已验证的核心门：

1. 先核验 4B manifest/config receipt、四个 Epoch 165 checkpoint 实物 SHA、checkpoint receipt、Full/OT condition SHA 与 tensor 定义。
2. 只接受 `outer_role=outer_train`、`generator_fold != outer_fold`，并将 model×fold 严格绑定至 `G_f`；所有 cross-OOF 字段必须标为禁止作为训练输入。
3. 使用 MONAI `pickle_hashing` 计算既有 PersistentDataset cache key；缺一即 BLOCKED，不允许静默重新生成。
4. 对本组全部选中 cache 文件在推理前后计算内容 SHA-256，并比较完整 cache `(name,size,mtime_ns)` 树；任何变化均失败。
5. 每个 PTID 比较实际推理 MRI 与相同 PTID 的 E1 MRI：shape `160×192×160`、float32、finite、`max_abs_error <= 2e-6`。
6. Full 实际 context 必须逐元素等于 `[patient token, tracer token]`；OT 必须等于 `[empty-patient token, tracer token]`。
7. 实际公式固定为 `clamp(MRI + model_velocity(t=0, context), 0, 1)`。
8. 写盘前检查输出身份、shape、float32、finite、范围 `[0,1]` 和非恒定；通过后才写临时 NIfTI 并以 `os.replace` 原子落盘。
9. 每文件记录 PTID/diagnosis、outer/generator fold、model/tracer、checkpoint/condition/context SHA、runtime config、cache key/path/前后 SHA、MRI/E1 身份和误差、公式、数组统计、预测路径/字节数/SHA。
10. 任一异常保留 `failure.json` 和已有部分文件，绝不签发 `complete.json`；已有运行目录或文件一律拒绝覆盖。

## 3. 正式派生输出协议

正式根固定为：

`/mnt/datas230/users/linshuijin/DIRECTPP_stage4c3_train_side/20261028/epoch165`

布局固定为：

`outer_fold{f}/{full|ot}/{fdg|av45}/generated_{tracer}_{PTID}.nii.gz`

该目录与 pilot 根、原 Full/OT OOF、checkpoint、condition 和 cache 完全隔离。四个正式运行目录当前均不存在，正式根也未创建。4B 三个 manifest 和 config 保持冻结、未修改。

正式执行后的唯一文件来源应为每组实际生成的 `prediction_manifest.json` 与 `complete.json`。后续分类 loader 必须解析并核验这些 receipt，不得从命名模板猜测路径，也不得读取 4B 行中的 cross-OOF 审计路径。

## 4. 完整 dry-run 结果

| 组 | 冻结 outer-train subjects | 计划 PET | Checkpoint | Dry-run |
|---|---:|---:|---|---|
| Full-G1 | 457 | 914 | Full Epoch 165 G1 | PASS |
| OT-G1 | 457 | 914 | OT Epoch 165 G1 | PASS |
| Full-G2 | 448 | 896 | Full Epoch 165 G2 | PASS |
| OT-G2 | 448 | 896 | OT Epoch 165 G2 | PASS |

两折 outer-train 集合无交集，并集严格为 905 人；未扩展到完整 1,857 人生成 cohort。计划枚举得到 3,620 个互不重复的预测路径，所有路径均位于正式根且当前未被占用。905 个实际 PersistentDataset cache key 全部存在。

dry-run 中 `models_loaded=false`、`generator_forward_run=false`、`pet_written=false`、`full_inference_run=false`。现有 32 个 pilot 文件的 SHA 重新核对为 32/32 一致。

## 5. 拒绝测试

以下错误均由真实验证函数拒绝：

- 错误 generator/outer fold；
- 错误 checkpoint SHA；
- Full/OT condition 混用或 OT runtime 缺失；
- outer-test PTID 进入 train-side；
- train-side 行允许 cross-OOF；
- 输出指向原 OOF；
- 已存在的正式运行目录/文件冲突；
- 缺少或错误的正式执行授权。

## 6. DONE 回答

1. **当前 runner 能否正常启动？** 是。源码可编译，根命令及五个要求的子命令均通过实际 CLI `--help`；check-only 和 dry-run 也已实际执行通过。
2. **全量 infer 是否复用 pilot 全部核心 QC？** 是。两者已收敛到同一执行函数；正式模式额外强制全量计数及所选 cache 文件前后内容 SHA。
3. **3,620 个路径是否唯一且正确？** 是。计划 SHA 已冻结，3,620/3,620 唯一、未占用、全部位于正式隔离根。
4. **四组是否均通过 dry-run？** 是，Full-G1、OT-G1、Full-G2、OT-G2 均 PASS，计数分别为 914/914/896/896。
5. **能否进入正式全量推理？** **工程准备已完成，可以在用户另行明确授权的后续阶段进入。** 当前 formal authorization 字符串有意与本 Readiness 阶段分离；本阶段没有执行任何真实推理。剩余已知限制是历史 cache 没有预先存在的逐文件 SHA receipt，但正式 runner 会对实际选中的 905 个 cache 文件在每组推理前后计算并核对内容 SHA，因此不会静默接受运行中 cache 漂移。

本阶段到此停止，未进入正式推理或分类实验。
