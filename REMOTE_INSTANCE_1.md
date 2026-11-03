# 远程实例 1

本文件记录 Task A 使用的计算实例。仓库不保存密码；当前已验证 SSH key 可免密登录。

## 连接

```bash
ssh -p 36733 root@connect.weste.seetacloud.com
```

- 核验日期：2026-10-27（Asia/Shanghai）
- 远端 hostname：`autodl-container-e1a2l2ecb5-f3d3c148`
- 用户：`root`
- GPU：NVIDIA GeForce RTX 4090，UUID
  `GPU-67973436-ddfb-1936-b0cb-2cf4e22aec41`，显存约 48 GB
- Python：`/root/miniconda3/bin/python`（Python 3.12）
- 已核验环境：PyTorch 2.7.0+cu128、MONAI 1.5.2、Nibabel 5.4.0、NumPy 2.2.6、
  Pandas 3.0.1、scikit-learn 1.8.0

## Task A 固定路径

- 新代码：`/root/autodl-tmp/DIRECTPP_task_a`
- 原始影像：`/root/autodl-tmp/ADNI1234_mri_fdg_av45`
- Full 缓存：
  `/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3`
- Task A 资产、checkpoint、预测和日志：
  `/root/autodl-fs/DIRECTPP_clinical_regression_unet/task_a_20261027`

`/root/autodl-tmp/DIRECTPP`、`directpp_assets`、`directpp_tracer_only_assets` 和上述 Full
缓存属于已有实验，不得覆盖。部署必须使用已经推送 GitHub 的 commit，并在启动训练前记录
commit SHA、配置 SHA-256、GPU UUID 和缓存身份。

## 2026-11-02 无卡模式开机核验记录

- **核验时间**：2026-11-02 21:20（Asia/Shanghai）
- **运行模式**：无卡模式开机（经核验无 `/dev/nvidia*` 设备，未挂载 GPU，避免产生 GPU 计费）
- **SSH 连通性**：正常免密登录（`ssh -p 36733 root@connect.weste.seetacloud.com`，远端 hostname `autodl-container-e1a2l2ecb5-f3d3c148`）
- **Python 运行时**：`/root/miniconda3/bin/python` 可正常执行，PyTorch 2.7.0+cu128、MONAI 1.5.2、Nibabel 5.4.0 均正常载入
- **磁盘与数据核验**：
  - **系统盘（`/`）**：overlay 分区 30 GB，已用 2.6 GB（9%），可用 28 GB。
  - **数据盘（`/root/autodl-tmp`）**：独立 XFS 分区 250 GB，已用 169 GB（68%），可用 82 GB。
    - Full 缓存（`/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3`）：103 GB，严格包含 1,857 个受试者 `.pt` 文件，总计 109,553,770,710 字节。
    - 原始影像（`/root/autodl-tmp/ADNI1234_mri_fdg_av45`）：30 GB 原始数据及 4 卷分卷压缩包完整。
    - 代码目录（`/root/autodl-tmp/DIRECTPP_task_a` 及 `/root/autodl-tmp/DIRECTPP`）：完整保留。
    - 资产目录（`directpp_assets`、`directpp_tracer_only_assets`、`directpp_tabular_inputs`）：完整保留。
  - **共享存储（`/autodl-fs/data` 即 `/root/autodl-fs`）**：AutoFS 分区 200 GB，已用 183 GB（92%），可用 18 GB。
    - Task A 训练资产（`/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027`，共 82 GB）：
      - `formal/fold1`：包含 19 个权重 checkpoint（epoch 10 至 200 每 10 轮及 epoch 165、`recovery.pt`）、`start.json`、`complete.json`、`epochs.jsonl`、`training_trace.jsonl` 全部完整。
      - `oof/epoch165/fold1`：完整生成 1,482 个 NIfTI 预测文件（FDG 792 个，AV45 690 个）及 `complete.json`。
      - `oof/epoch200/fold1`：完整生成 1,482 个 NIfTI 预测文件及 `complete.json`。
      - `runtime/`：包含 `formal_pipeline.log`、`fold1_finalize.log`、`launch_receipt.json`、`watchdog_instance1.log`。

