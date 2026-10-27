# Full/OT OOF 与 E1 SynthSeg ROI mask 空间兼容性报告

结论：**PASS**。Epoch 165 的 Full/OT 两折 OOF 预测可在 **数组索引层面**直接应用 E1 冻结 SynthSeg mask；1,856/1,856 名有效受试者通过 MRI-anchored grid gate，5,922/5,922 个预测文件通过身份、哈希、shape、dtype、finite 与 header 检查。**不需要翻转、重配准、重采样或其他空间变换。**

限制：Full/OT 原始 NIfTI 均保留 identity affine，不能把该 header 当作对齐证明，也不能原样送入要求预测 affine 等于 E1 affine 的 evaluator。第三阶段应在加载后按同 PTID 绑定 E1 cache/mask；如代码入口必须检查 affine，可建立不覆盖原文件的内存视图或派生副本，仅赋入已验证的 E1 affine，不改变体素数组。

本阶段未执行 ROI uptake、MAE、CCC、ICC、SUVR、分类、训练、推理或配准。

## A. 输入资产与身份核验

| 项目 | 核验结果 |
|---|---|
| 分析终点 | 仅 Epoch 165 |
| Full/OT 原始 OOF 身份 | 各 2,963 个 `PTID+tracer+fold+epoch`；两组键完全一致 |
| E1 交集 | 排除冻结 QC 病例 `016_S_4952` 后 1,856 人；Full fold 1/2 各 928 人，不重分折 |
| 有效 tracer | FDG 1,597；AV45 1,364；每个模型各 2,961 个预测 |
| 原始输入清单 | Full 与 E1 的 MRI/FDG/AV45 共 5,571 个身份在路径、字节数和 SHA-256 上 5,571/5,571 一致 |
| E1 冻结资产 | `cohort.json`、`input_hashes_final.csv`、`hemisphere_label_map.json`、`roi_validity.json` 当前 SHA-256 均与 `config.json` 冻结值一致 |
| 推理缓存 | Full 与 OT 的四个 Epoch 165 fold 收据均声明 `verified_persistent_cache`，且指向同一 1,857 文件持久缓存；各 fold `metrics.csv` 实际哈希与收据一致 |
| 预测身份 | 5,922/5,922 路径严格符合模型、fold、tracer、PTID 的预期目录和文件名；实际文件 SHA-256 全部等于逐行指标清单 |

Epoch 165 checkpoint SHA-256：Full fold1 `550ac2c4…ea77`、fold2 `f67e4a78…4315`；OT fold1 `573778ad…e69db`、fold2 `32b89214…06085`。逐预测记录中的 checkpoint 身份与对应 fold 收据一致。

代表性预检先于全队列执行，纳入 10 人，覆盖两个 fold、AD/CN/EMCI/LMCI/MCI 五组，且每人同时有 FDG 与 AV45。10/10 MRI/mask、40/40 Full/OT 预测及 10/10 物理左右质心检查通过后才扩展。预检样本和可视 overlay 见 `02_precheck_results.json`、`02_precheck_overlay.png`。

## B. MRI array/grid 比较结果

| 检查 | 结果 |
|---|---|
| Full/OT 共享推理缓存 MRI vs E1 cache MRI | 1,856/1,856 shape 均为 `160×192×160`；dtype 均为 `float32`；finite 1,856/1,856 |
| 数组误差 | 894/1,856 逐位完全相等；962 人仅有 float32 末位数值差异；全队列最大 `max_abs_error = 1.7881393432617188e-07`，最大 subject-level mean absolute error `2.4805401874217204e-08` |
| 空间门槛 | 1,856/1,856 低于 E1 在本阶段前已冻结的 MRI replay 门槛 `2e-6`；未依据 Full/OT 结果新增阈值 |
| E1 cache 身份 | 1,856/1,856 当前 NPZ 的实际 SHA-256 等于 `geometry_qc_final.json` 记录值 |
| 原始 MRI replay | 冻结收据对 1,856 人均通过；本次同时核对收据、原始输入 manifest 与当前 cache 哈希。原始 `/home/data/...` 路径当前不可挂载，因此未重新执行 raw-NIfTI replay；此项“本次重放”记为 **UNVERIFIED**，但冻结重放证据未发生身份漂移 |

最初诊断版验证器曾把“逐位完全相等”设为通过条件，预检因此在 4/10 人出现 `1.19–1.79e-7` 的末位差异而停止；没有启动全队列。随后验证器改为沿用既有 E1 `2e-6` 门槛，同时保留 exact、max-abs、mean-abs 与差异体素数作为报告字段。该修正不涉及翻转、配准、病例删除或基于 PET 选择变换。

## C. Full/OT 预测与 E1 mask 的兼容性

| 模型 / tracer | 通过 / 总数 | fold 1 / fold 2 |
|---|---:|---:|
| Full FDG | 1,597 / 1,597 | 791 / 806 |
| Full AV45 | 1,364 / 1,364 | 689 / 675 |
| OT FDG | 1,597 / 1,597 | 791 / 806 |
| OT AV45 | 1,364 / 1,364 | 689 / 675 |

全部 5,922 个预测均为 `160×192×160`、`float32`、全 finite，且当前 affine 为 identity；全部实际 SHA-256 与冻结索引一致。每位受试者的 E1 mask 与 E1 MRI 均为相同 `160×192×160` 数组格，mask 为有限整数标签且非空。由于预测由已经逐人通过 MRI 对照的同一 Full/OT 推理缓存直接生成，预测数组与 E1 mask 的 voxel index 对应关系成立。

因此：

- **可直接做：** `prediction_array[mask == label]` 形式的数组索引；无需改变数组。
- **不可直接做：** 把原 identity-affine NIfTI 当作具有正确世界坐标的图像，或仅凭替换 header 宣称完成空间验证。
- **如需 affine gate：** 在已验证的 `PTID+tracer+fold+epoch` 绑定之后，把该 PTID 的 E1 affine 附到内存视图/独立派生对象；这只是补齐经 MRI 锚点证明的空间元数据，不是空间转换。不得覆盖原预测。

## D. 物理左右半球映射核验

- `hemisphere_label_map.json` 当前哈希与 E1 冻结值一致；继续使用“segmenter 左右名称与物理半球全局反转”的映射，不交换标签、不翻转 mask。
- 本次对 10 个预检病例重新计算四对大结构（白质、壳核、侧脑室、丘脑）的世界坐标质心，10/10 与冻结 physical-name map 一致。
- E1 既有 `laterality_fix_receipt.json` 对有效队列的核心门记录为 1,856/1,856 一致；Full/OT MRI 数组已与 E1 MRI 通过同格验证，因此该映射可直接沿用。

## E. 异常病例清单

**本阶段有效队列异常病例：0。**

- MRI/mask grid 失败：0/1,856。
- 预测 shape/dtype/finite/header/hash/路径失败：0/5,922。
- 预检物理左右失败：0/10；冻结全队列 laterality gate 失败：0/1,856。
- 冻结 E1 排除病例仍为 `016_S_4952`；未纳入本阶段有效队列，也未借本阶段结果改变其状态。

上述 962 个非 bitwise-exact MRI 对照不列为异常：最大误差仅 `1.788e-7`，全部低于预先存在的 E1 `2e-6` replay 门槛，shape、dtype、finite、mask、affine provenance 与文件哈希均通过。

## F. 判定

**PASS**

1. Full/OT Epoch 165 预测数组可以直接应用 E1 ROI mask：**是，限数组索引语义。**
2. 是否需要额外空间转换：**不需要。** 禁止自动翻转、配准或重采样。
3. 完整有效队列通过数：**1,856/1,856 人**；FDG 1,597、AV45 1,364；Full/OT 预测合计 **5,922/5,922**。
4. 是否可进入 ROI MAE / CCC / ICC：**可以。** 空间兼容性不再构成阻塞项；仍须保持 E1 冻结 ROI、validity 与 physical-name map，并在统计阶段明确 normalized uptake 协议。

## G. 第三阶段最小接入方式

1. 固定 E1 有效 1,856 人与现有 Full fold，不重新划分；仅取 Epoch 165 和本报告已核验的路径/哈希。
2. 逐 PTID 读取 Full/OT 预测数组与 E1 NPZ 中的 `mask`、`affine`；在进入 ROI 计算前保留 shape、finite 和身份断言。
3. 直接用同索引 mask 提取冻结 ROI；沿用 `roi_validity.json`。其当前哈希与冻结值一致，且 mask 未变，因此原有“低于队列中位体素数 10% 即该 subject-label 无效”规则可直接复用，不需重算或改阈值。
4. 输出物理侧别名称必须使用 `hemisphere_label_map.json`。若 evaluator 强制比较 affine，只对内存视图或独立派生文件赋入 E1 affine；不得覆盖 Full/OT 原文件，也不得把该赋值本身写成对齐证据。
5. 第三阶段才执行 ROI MAE、CCC、ICC(A,1) 等统计；本阶段结果不包含任何区域摄取或 Full/OT 性能比较。

## 证据文件

- `02_spatial_validation_results.json`：汇总门与来源收据。
- `02_spatial_subject_checks.csv`：1,856 人 MRI/mask、cache hash、replay 与误差记录。
- `02_prediction_identity_checks.csv`：5,922 个预测的路径、checkpoint、实际 SHA-256 与 header/array 检查。
- `02_precheck_results.json`、`02_precheck_overlay.png`：扩展前门检与 MRI/mask overlay。
- `02_spatial_compatibility_validation.py`：只读验证实现。

