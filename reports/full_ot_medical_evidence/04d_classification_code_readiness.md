# Stage 4D：2-fold DenseNet121 分类代码准备报告

## 结论

**PASS_CODE_AND_SMOKE。** 已建立独立的 generator-anchored 2-fold 分类入口，可运行固定的 3 tasks × 2 outer folds × 4 conditions = 24 fits；真实 E1 MRI 的最小 GPU 训练验证已经通过。当前 4C-4 尚未签发正式完成收据，因此 `MRI+Full`/`MRI+OT` 会按设计 fail-closed；这不影响 `MRI`/`MRI+Real` 的代码验证，也不会误用仍在生成中的文件。

4C-4 完成并生成 SHA-256 绑定的 `04c4_full_inference_receipt.json`、`04c4_full_prediction_manifest.csv` 和 `04c4_classification_asset_index.csv` 后，先执行全条件 preflight；通过后即可启动 24 fits。

## 1. 实现范围

新增目录 `experiments/classification_2fold/`：

- `run.py`：`preflight`、单一 `fit`、自动续跑全部 `all`、最小 `smoke` 四个入口；
- `protocol.py`：4B/4C-4 身份核验、generator fold 角色约束、影像加载及数组 QC；
- `config.json`：冻结任务、fold、condition、模型、训练设置和输出根；
- `test_protocol.py`：threshold 和指标的确定性单元测试；
- `README.md`：执行命令。

每个 fit 独立创建 DenseNet121、optimizer 和 DataLoader，输出：

- `input_manifest.csv`、`resolved_config.json`；
- `last_state.pth`（逐 epoch 原子更新，可断点续训）；
- `best_model.pth`（inner-validation AUC 最大，平局取最早 epoch）；
- `history.csv`；
- `inner_validation_predictions.csv`；
- `outer_test_predictions.csv`；
- `metrics.json`、`complete.json`。

`all` 只跳过身份完全匹配且状态为 `COMPLETE` 的 fit；身份包含 runner、protocol code、config、4B manifest/receipt 以及（Syn 条件）4C-4 receipt/index SHA。部分运行从 `last_state.pth` 恢复，身份不匹配时拒绝继续。

## 2. 冻结数据协议

| Task | 总人数 | Fold 1 train/val/test | Fold 2 train/val/test |
|---|---:|---:|---:|
| AD/CN | 469 | 186 / 47 / 236 | 188 / 48 / 233 |
| MCI/CN | 740 | 295 / 74 / 371 | 296 / 75 / 369 |
| LMCI/EMCI | 436 | 179 / 45 / 212 | 169 / 43 / 224 |

以上计数来自并重新核验了 4B 冻结 manifest。代码强制：

1. `generator_fold == outer_fold` 只能是 `outer_test`；其 Full/OT 必须逐路径、逐 SHA 等于 4B 冻结的对应 G_f OOF。
2. `generator_fold != outer_fold` 只能是 `inner_train` 或 `inner_validation`；Full/OT 必须来自 4C-4 实际收据索引，禁止选用 cross-OOF。
3. outer test 不进入 checkpoint 或 threshold 选择；threshold 在所选 checkpoint 的 inner validation 上按 Youden J 确定，平局依次取最接近 0.5、再取较小 threshold。
4. AUC 使用 softmax 后的阳性类概率；最终逐折指标包括 AUC、ACC、SEN、SPE、balanced ACC 和分层 subject bootstrap 95% CI。
5. 同一 task/fold 的所有 condition 使用相同 seed；Full/OT 的初始化与 shuffle 规则相同。

4C-4 分类资产索引被固定为每个 `task × outer_fold × PTID` 一行，并须包含 Full/OT 的 FDG、AV45 实际路径及 SHA。索引本身和 3,620 行预测总表都必须由正式 4C-4 receipt 绑定；代码不猜测文件路径。

## 3. DenseNet 与训练设置

- MONAI 3D `DenseNet121`，MRI 为 1 channel，其余条件为 MRI + FDG + AV45 共 3 channels；
- `CrossEntropyLoss`；Adam，learning rate `1e-4`；200 epochs；每 2 epochs 做 inner validation；
- 最佳 checkpoint 按 inner-validation AUC；
- 输入为 E1 已验证的 normalized arrays，shape `160×192×160`、float32、finite、范围 `[0,1]`；不做新的重采样、配准或强度归一化；
- 与原 notebook 的 `CacheDataset` 目的相同，当前 fit 对已读取的 train/validation/test arrays 作逐 fit 内存缓存，避免 200 epochs 重复读取 NFS；fit 结束后释放，任务间不共享数组；
- batch size 固定为 1、AMP 开启，所有 Full/OT fits 相同。历史 notebook 的 batch size 为 5；此处按 24 GB GPU 和全分辨率 3D 输入作资源性调整，不改变 backbone、loss、optimizer、learning rate 或 epoch 规则。

最大 MCI/CN 三通道 fit 的全部 arrays 理论体积约 43.4 GiB；本次 3014 定向检查显示约 521 GiB system memory available，因此逐 fit 内存缓存具备资源余量。正式启动前仍应重新核验 GPU 与主存。

原 notebook 的主要架构和训练参数已复用。根据 4B 冻结方案，checkpoint 选择从历史的 validation ACC 改为预先指定的 validation AUC，并用 softmax probability 而非 raw logit 计算 AUC。

## 4. 实际 smoke validation

使用只读 GPU 资源快照选择 3014 物理 GPU 4；启动前定向核验为 RTX 3090、24,110 MiB free。GPU 0–3 上的 4C-4 进程未被触碰。

| 项目 | 实际结果 |
|---|---|
| Node / GPU | 3014 (`server`) / physical GPU 4, RTX 3090 |
| Task / fold / condition | AD/CN / outer fold 1 / MRI |
| 实际输入 | E1 cache，`1×1×160×192×160`, float32, `[0,1]` |
| 实际检查 | loader、forward、CrossEntropy、backward、Adam step、validation forward、atomic checkpoint |
| Forward 输出 | `1×2` logits |
| Smoke loss | 0.66455078125 |
| 运行时间 | 2.4267 s |
| 峰值 GPU memory | 1,302,619,136 bytes（约 1.21 GiB） |
| Checkpoint | 45,607,294 bytes；SHA-256 `73f122a532fea19cab80bc694a871a70f57a18c09253a5f902cbcdecebff8f82` |

Smoke receipt 位于：

`/mnt/datas230/users/linshuijin/DIRECTPP_classification_2fold/smoke_20261028_gpu4_v3/smoke_receipt.json`

该 smoke 只用各一例阳性/阴性训练样本执行一个 optimizer step，并用各一例阳性/阴性检查验证路径；其 AUC 不具有科学解释。PyTorch 对本机 `avg_pool3d/max_pool3d` backward 报告没有完全确定性 CUDA kernel；代码已固定 seed、关闭 cuDNN benchmark，并以 `warn_only` 记录这一运行时限制。Full/OT 仍使用完全相同的 seed 和规则，但不声称跨运行 bitwise deterministic。

## 5. 已执行的工程验证

- `py_compile`：通过；
- threshold/metric 单元测试：2/2 通过；
- `preflight/fit/all/smoke --help`：均可实际解析；
- MRI/MRI+Real 共 12 个 task×fold×condition 静态 preflight：全部通过；
- 4B manifest SHA、行数、PTID 唯一性、generator fold 与 inner role、各 split 双类别：全部通过；
- MRI+Real 实际样本加载：`3×160×192×160`、float32、finite、`[0,1]`；
- 错误正式授权：拒绝；
- 4C-4 receipt 尚不存在时请求 `MRI+Full`：拒绝，未训练；
- smoke checkpoint 已重新加载并核验模型 state。

## 6. 4C-4 完成后的启动命令

先在目标节点重新确认空闲 GPU，然后执行全条件身份与文件 SHA preflight：

```bash
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python \
  experiments/classification_2fold/run.py preflight \
  --output reports/full_ot_medical_evidence/04d_full_preflight.json
```

preflight 为 `PASS` 后，在选定 GPU 上自动运行或续跑全部 24 fits：

```bash
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
CUDA_VISIBLE_DEVICES=<physical_gpu> \
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python \
  experiments/classification_2fold/run.py all \
  --authorization RUN_STAGE_4D_24_FITS
```

单一 fit 可用 `fit --task <task> --outer-fold <1|2> --condition <mri|mri_real|mri_full|mri_ot> --authorization RUN_STAGE_4D_24_FITS`。正式输出根为 `/mnt/datas230/users/linshuijin/DIRECTPP_classification_2fold/20261028`。

## 7. 当前待满足条件

唯一外部前提是 4C-4 全部完成并签发上述三个正式资产文件。当前 synthetic conditions 的 BLOCKED 是预期安全行为，不是通过 MRI 或 Real 条件可绕过的检查。4C-4 receipt/index 到位后仍须先运行完整 preflight；只有 3,620 条预测、资产 SHA、outer-train/outer-test 角色和 OOF 绑定全部通过，才可启动 24 fits。

本阶段没有启动完整分类训练，没有修改论文，也没有干扰或重新推理 PET。
