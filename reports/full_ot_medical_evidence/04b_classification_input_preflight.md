# Stage 4B：2-fold 分类输入协议与 train-side PET 推理预检

## 结论

**静态身份预检 PASS；正式 train-side 推理尚未就绪，分类训练保持 BLOCKED。** 三个冻结任务的 469/740/436 名受试者、实际 generator fold、MRI/Real PET cache、Full/OT Epoch 165 OOF、四个 checkpoint 及 condition tensor 均已逐行绑定并写入 manifest。没有加载影像或模型，也没有执行推理、训练或分类评价。

现有 Full/OT 推理实现的模型前向、MRI预处理、持久缓存和 condition hook可复用，但现有 CLI 只能推理 `test_fold == fold` 并写入不可覆盖的 OOF目录，**不能直接用于 outer-train**。必须先建立独立 train-side inference入口和新输出命名空间；OT还缺少当前工作区内可直接加载的完整 runtime config/report bundle，需从已验证收据重建或恢复，不能只凭 checkpoint路径启动。

## A. 冻结队列和 fold 身份

### A1. 唯一有效的 generator fold来源

正式 `generator_fold` 来自 Stage 2 `02_prediction_identity_checks.csv` 中 Full/OT Epoch 165 的实际 OOF fold，并由对应 checkpoint SHA交叉核验。E1 `cohort.json:test_fold` 是另一套 E1实验划分，只保留为 `e1_test_fold_audit_only`。

双 tracer有效队列1,105人中，两种 fold身份有 **529人不同**。因此不能沿用04a中基于 E1 fold计算的每折人数；04a的总体469/740/436人数仍正确，本报告以下实际outer fold人数取代其折内描述。

| Task | 正类定义 | 总数（正/负） | Outer fold 1 test/train | Outer fold 2 test/train |
|---|---|---:|---:|---:|
| AD/CN | AD=1，CN=0 | 469（165/304） | 236/233；test 77/159 | 233/236；test 88/145 |
| MCI/CN | EMCI或LMCI=1，CN=0 | 740（436/304） | 371/369；test 212/159 | 369/371；test 224/145 |
| LMCI/EMCI | LMCI=1，EMCI=0 | 436（149/287） | 212/224；test 79/133 | 224/212；test 70/154 |

每个任务manifest采用长表：每名受试者分别出现于outer fold1和2各一次；在其generator fold为`outer_test`，在另一fold为`outer_train`。inner validation仅从outer train按标签分层固定抽取20%，seed为`20261028 + outer_fold`。

### A2. Manifest内容与完整性

每行包含：PTID、diagnosis、label、generator fold、outer角色、inner角色；E1 NPZ cache路径及SHA；原MRI/FDG/AV45路径、SHA和字节数；Full/OT checkpoint路径、receipt和SHA；condition路径和SHA；现有OOF路径/SHA；分类实际选择路径及资产状态。

对outer-train行，现有cross-OOF路径仅作为审计字段，`existing_oof_usage=FORBIDDEN_AS_OUTER_TRAIN_INPUT`；分类选择路径指向尚未生成的独立train-side目录，SHA固定为`PENDING_TRAIN_SIDE_INFERENCE`。对outer-test行，选择路径必须等于已核验OOF路径。

| Manifest | Subjects | Rows | 静态检查 |
|---|---:|---:|---|
| `04b_manifest_ad_cn.csv` | 469 | 938 | 无重复outer_fold+PTID；角色/fold、四个OOF和checkpoint均匹配 |
| `04b_manifest_mci_cn.csv` | 740 | 1,480 | 同上 |
| `04b_manifest_lmci_emci.csv` | 436 | 872 | 同上 |

完整SHA和字节数见`04b_manifest_receipt.json`。

## B. Checkpoint与condition绑定

| Model | Outer fold | Epoch165 checkpoint SHA-256 | Condition |
|---|---:|---|---|
| Full | 1 | `550ac2c4…4ea77` | patient+tracer；`conditions.pt` SHA `bbcd4131…84384a` |
| Full | 2 | `f67e4a78…4315` | 同一Full condition资产 |
| OT | 1 | `573778ad…0e69db` | fixed empty-patient+tracer；SHA `e1dfd639…dc71ec` |
| OT | 2 | `32b89214…206085` | 同一OT condition资产 |

四个checkpoint实物SHA均等于Stage 2收据、OOF逐行索引和各自`first_part_165.json`；receipt内fold、one-based epoch 165、checkpoint SHA及model SHA均一致。Full/OT共用同一1,857人cohort、split manifest、输入hash和持久预处理cache；两模型仅condition模式及训练所得权重不同。

## C. Outer train/test执行契约

对outer fold `f`：

```text
outer test = generator_fold f
  Full/OT PET = 已有 G_f OOF，允许读取且必须匹配manifest SHA

outer train = generator_fold != f
  Full/OT PET = 必须由同一个 G_f 对这些MRI补推理
  现有cross-OOF来自 G_(3-f)，禁止作为训练输入
```

这保证分类outer-test受试者没有参与`G_f`训练，同时分类train/test的synthetic域由同一个生成器实例产生。任何分类loader若在outer-train行读取`existing_oof_path`，应立即失败。

MRI和Real双PET从同一E1 NPZ的`mri/fdg/av45`数组读取；Full/OT使用已通过Stage 2 MRI-anchored检查的160×192×160 float32数组。分类阶段不得因identity affine重采样、翻转或重配准。

## D. Train-side推理可执行性

### D1. 可直接复用的组件

- `experiments/original_author_reproduction/run.py`：`build_transform`、PersistentDataset cache、`context_from_batch`、U-Net加载、`prediction=clamp(MRI+velocity,0,1)`和双tracer循环。
- `experiments/tracer_only_control/run.py`：固定empty-patient+tracer condition加载及runtime context hook。
- 已验证持久cache：1,857份，与Full/OT OOF使用相同MRI预处理；分类只需选择dual-tracer outer-train PTID。
- 四个Epoch165 checkpoint和condition tensor均可读、SHA通过。

### D2. 不能直接调用现有CLI的原因

1. `command_infer`硬编码`held_out = test_fold == args.fold`，没有train-side selection参数。
2. 输出硬编码到`oof/epoch165/foldf`并以`exist_ok=False`创建；这些目录已存在且属于原始OOF，禁止覆盖。
3. 推理同时计算Real-target SSIM/PSNR/MSE/MAE；train-side分类资产不需要用这些指标选变换或病例。新入口应只做身份和数组QC，Real PET不能参与空间变换选择。
4. OT当前工作区没有原始运行时`config.json/cohort.json/split_manifest`完整bundle；仅有结果汇总、provenance、checkpoint、condition和OOF收据。虽然科学身份可闭合，但现有OT wrapper的`load_config/_static_checks`不能直接通过。

因此问题2的准确回答是：**核心代码和资产足以生成，但现有CLI不能原样安全执行；补齐隔离入口与OT运行bundle后可执行。**

### D3. 新入口必须满足的最小门

- 参数显式包含`--outer-fold f --selection outer-train --manifest <file> --output-root <new-root>`；拒绝任何OOF输出根目录。
- 只加载manifest中`outer_role=outer_train`且`generator_fold!=f`的唯一PTID，并断言其checkpoint为`G_f`。
- Full和OT输出分别放在：`.../epoch165/outer_foldf/full/`与`.../outer_foldf/ot/`；文件名保持`generated_{tracer}_{PTID}.nii.gz`。目录必须不存在或为空，禁止静默续写/覆盖。
- 每文件记录PTID、tracer、outer fold、source generator fold、checkpoint/condition/cache SHA、预测SHA、shape/dtype/finite/min/max；生成完成后签发不可变receipt。
- 不改原checkpoint、condition、cache、OOF或E1文件。原NIfTI仍可用identity affine保存，但分类按数组索引读取；不得把header替换当作对齐证明。

## E. Train-side与held-out分布检查计划

该检查只用于发现执行漂移，不用于选择模型、空间变换、分类子集或阈值：

1. 每模型×outer fold先固定少量预检PTID，覆盖两类标签和三项任务的并集；同一PTID同时生成FDG/AV45。
2. 逐文件检查shape=`160×192×160`、float32、finite、范围`[0,1]`、非恒定、路径与checkpoint/condition SHA；确认与任何已有OOF文件路径不重合。
3. 对train-side和对应held-out OOF分别汇总每卷mean、SD、p01/p50/p99、零值和一值比例；按model/tracer/fold报告，不以Real PET相似度挑选处理。
4. MRI cache身份逐PTID匹配Stage 2；若需要视觉QC，只做MRI/预测同索引overlay和方向检查，不自动配准。
5. 预检通过后才扩展。任一核心身份、空间、finite或范围检查失败即停止，不删除病例强行通过。

完整dual cohort扩展预计每模型新增`1,105×2 tracer=2,210`个train-side体积，Full+OT共4,420个；每名受试者只为其“另一checkpoint”补生成一次，不按三个任务重复推理。三个任务只是在分类manifest中引用同一生成资产。

## F. DenseNet分类协议草案

- 四条件：MRI、MRI+Real、MRI+Full、MRI+OT；3D MONAI DenseNet121。MRI为1 channel，后三组为MRI+FDG+AV45共3 channels，二分类输出2 logits。
- 24 fits：3 tasks×2 outer folds×4 conditions。每fit重新构建model/dataset/loader；outer test不参与模型、epoch、阈值或预处理选择。
- Outer train内固定stratified inner validation 20%；名单已写入manifest。Full/OT完全相同的split、seed、CrossEntropyLoss、Adam `1e-4`、200 epoch上限、每2 epoch验证和选择规则。
- Checkpoint按inner-validation AUC最大选择；并列取最早epoch。阈值在选定checkpoint的inner validation上最大化Youden J；并列先取最接近0.5，再取较低阈值。batch size尚需GPU短试跑确认，但Full/OT必须相同。
- 每个outer-test subject输出正类`softmax(logits)[:,1]`概率、固定阈值预测和checkpoint身份。三项任务分别合并两折为一条/人outer-OOF概率。
- 主要比较：MRI+Full vs MRI+OT的paired pooled outer-OOF AUC；按label×outer fold分层subject bootstrap给95% CI，三任务主要ΔAUC使用Holm。保留ACC、SEN、SPE、balanced ACC及其95% CI；可补McNemar错误比较。两折分别报告，但不当作独立重复实验。

## G. 正式训练前阻塞项

| 阻塞项 | 状态 | 解除条件 |
|---|---|---|
| Generator fold与任务manifest | VERIFIED | 已冻结；只读使用本阶段CSV/SHA |
| Full/OT Epoch165 checkpoint/condition | VERIFIED | 每次运行前复核实物SHA |
| Outer-test OOF路径、哈希、空间 | VERIFIED | Stage 2资产只读 |
| Train-side selection/output隔离 | BLOCKED | 实现独立入口并加入禁止cross-OOF断言 |
| OT可运行配置bundle | BLOCKED | 恢复原runtime config或按现有收据重建并逐SHA核验 |
| Train-side PET | MISSING | 预检后生成4,420个文件并签发receipt |
| Train/OOF分布QC | PENDING | 预设QC通过，不据结果改队列 |
| DenseNet batch/显存/吞吐 | UNVERIFIED | 获批后短试跑；不产生正式结果 |
| 正式分类入口和结果schema | MISSING | 独立实现，不修改历史notebook |

## H. 下一阶段最小安全顺序

1. 只实现train-side runner和静态`--check-only`；恢复/重建OT runtime bundle，验证其cohort、split、input、condition及source SHA。
2. 在新输出根执行每模型×outer fold的小样本推理预检；完成身份、数组、空间和分布QC后停止审核。
3. 审核通过后，一次性生成dual cohort的4,420个train-side体积；写逐文件manifest和完成receipt。不得按任务重复生成。
4. 将生成SHA回填本阶段三个分类manifest的`selected_sha256`，重新签发最终输入receipt。
5. 先运行一个任务/一个fold/四条件的DenseNet工程预检，只验证loader、loss、checkpoint和概率schema；不报告科学结果。
6. 工程门通过后才执行预注册24 fits，最后统一做paired AUC和辅助指标统计。

## I. DONE问题回答

1. **2-fold样本与checkpoint是否全部核验？** 是。469/740/436人、实际generator fold、outer角色、四个checkpoint、Full/OT condition和全部现有OOF SHA均已核验。特别确认E1 fold不可替代generator fold。
2. **Train-side Full/OT PET能否通过现有代码生成？** 计算核心可以复用，但现有CLI不能直接安全生成；必须增加outer-train选择和独立输出入口，并补齐OT runtime bundle。
3. **是否存在空间、条件或文件身份阻塞？** 空间无新阻塞；checkpoint和condition身份已闭合。当前阻塞是train-side入口/输出隔离、OT运行bundle和尚未生成的train-side资产。
4. **如何安全执行首次推理与分类？** 先check-only和小样本四组合预检，再全dual cohort生成并回填SHA；随后做单fit工程门，最后才运行冻结的24 fits。任何核心门失败均停止，不换fold、不删病例、不覆盖OOF。

## 产物索引

- `04b_manifest_ad_cn.csv`
- `04b_manifest_mci_cn.csv`
- `04b_manifest_lmci_emci.csv`
- `04b_execution_config_draft.json`
- `04b_manifest_receipt.json`
- `04b_build_manifests.py`

