# 远程实例 2

本文件记录为了加速 3D UNET 实验所购买的新计算实例，用于与实例 1 并行训练另外一折（Fold 2）。仓库不保存密码；当前已配置 SSH key 免密登录。

## 连接

```bash
ssh -p 40818 root@connect.westb.seetacloud.com
```

- 核验日期：2026-10-27（Asia/Shanghai）
- 远端 hostname：`autodl-container-8e334ab691-5844cb0a`
- 用户：`root`
- GPU：NVIDIA GeForce RTX 4090，UUID `GPU-beefc3a1-51aa-7a0e-9988-f6765abdddd9`，显存约 48 GB (49140 MiB)
- Python：`/root/miniconda3/bin/python`（Python 3.12.3）
- 已核验依赖环境（**已与实例 1 达成 100% 字节级一致**）：
  - PyTorch: `2.7.0+cu128` (CUDA 12.8)
  - Torchvision: `0.22.0+cu128`
  - MONAI: `1.5.2`
  - Nibabel: `5.4.0`
  - NumPy: `2.2.6`
  - Pandas: `3.0.1`
  - scikit-learn: `1.8.0`

## 并行分工与固定路径

- **分工定位**：实例 1 当前正运行 Fold 1；实例 2 专用于并行执行 Fold 2。
- **新代码根目录**：`/root/autodl-tmp/DIRECTPP_task_a`
- **Full 缓存目录**：
  `/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3`（共 1,857 个受试者 `.pt` 文件，109,553,770,710 字节，与实例 1 完全一致）
- **共享存储与资产目录**：
  `/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027`（即挂载的 AutoFS 共享存储，两台实例自然共享产出）
- **Fold 2 资产输出路径**：
  `/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027/formal/fold2`

## 验证证据（与实例 1 浮点完全一致）

在新实例上实测验证输出：
- `check-config` 状态：`PASS`（1,857 受试者，哈希 `4284fd52b2c5b4b5...`）
- `smoke-test` 单样本损失：`0.29227329790592194`（与实例 1 浮点 16 位完全一致）
- 显存峰值：`12,751,513,088` 字节分配，`16,234,053,632` 字节保留（与实例 1 完全一致）
- 科学状态：`PASS_NO_OPTIMIZER_STEP`（未执行任何优化器参数更新）

## 正式启动记录

Fold 2 已于 2026-10-27 13:42:36（Asia/Shanghai）启动。复现命令为：

```bash
cd /root/autodl-tmp/DIRECTPP_task_a
nohup bash experiments/clinical_regression_unet/run_instance2_fold2.sh \
  > /autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027/runtime/fold2_pipeline.log 2>&1 &
```

## 2026-11-02 无卡模式开机核验记录

- **核验时间**：2026-11-02 21:20（Asia/Shanghai）
- **运行模式**：无卡模式开机（经核验无 `/dev/nvidia*` 设备，未挂载 GPU，避免产生 GPU 计费）
- **SSH 连通性**：正常免密登录（`ssh -p 40818 root@connect.westb.seetacloud.com`，远端 hostname `autodl-container-8e334ab691-5844cb0a`）
- **Python 运行时**：`/root/miniconda3/bin/python` 可正常执行，PyTorch 2.7.0+cu128、MONAI 1.5.2 均正常载入
- **磁盘与数据核验**：
  - **系统盘（`/`）**：overlay 分区 30 GB，已用 18 GB（60%），可用 13 GB。
  - **数据盘（`/root/autodl-tmp`）**：独立 XFS 分区 250 GB，已用 103 GB（41%），可用 148 GB。
    - Full 缓存（`/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3`）：103 GB，严格包含 1,857 个受试者 `.pt` 文件，总计 109,553,770,710 字节（与实例 1 达成 100% 逐字节一致）。
    - 代码目录（`/root/autodl-tmp/DIRECTPP_task_a`）：完整保留。
    - 脚本与传输日志（`cache_transfer.log`、`resume_transfer.sh` 等）：完整保留。
  - **共享存储（`/autodl-fs/data` 即 `/root/autodl-fs`）**：与实例 1 挂载同一 AutoFS 存储（共 82 GB 资产）：
    - `formal/fold2`：包含 19 个权重 checkpoint（epoch 10 至 200 每 10 轮及 epoch 165、`recovery.pt`）、`start.json`、`complete.json`、`epochs.jsonl`、`training_trace.jsonl` 全部完整。
    - `oof/epoch165/fold2`：完整生成 1,481 个 NIfTI 预测文件（FDG 806 个，AV45 675 个）及 `complete.json`。
    - `oof/epoch200/fold2`：完整生成 1,481 个 NIfTI 预测文件、`metrics.csv` 及 `complete.json`。
    - `runtime/`：包含 `fold2_pipeline.log`、`watchdog_instance2.log`。

