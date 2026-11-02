# 远程实例 6

本文件记录用于与实例 3、实例 4、实例 5 并行训练 SwinUNETR MRI-to-PET 对比方法基线的第六台云端计算实例。仓库不保存密码；当前已配置 SSH key 免密登录。

## 连接

```bash
ssh -p 51712 root@connect.westb.seetacloud.com
```

- 核验日期：2026-10-29（Asia/Shanghai）
- 远端 hostname：`autodl-container-5h9rm8rk3z-3396b382`
- 用户：`root`
- 所在区域：AutoDL 西宁机房（`westb`，与实例 2、实例 3、实例 4、实例 5 处于同一机房）
- GPU：NVIDIA GeForce RTX 4090，UUID `GPU-dc44f816-7167-e31f-ccb3-47b0f6dbc8c2`，显存约 48 GB (49140 MiB)
- Python：`/root/miniconda3/bin/python`（Python 3.12.3）
- 基础环境：PyTorch `2.5.1+cu124` (CUDA 12.4)
- 存储：系统盘 30 GB，数据盘 `/root/autodl-tmp` 250 GB NVMe SSD，文件存储 `/autodl-fs/data` 800+ GB

## 路径规划与分工定位

- **分工定位**：与实例 3、实例 4、实例 5 组成 4 实例并行计算集群，各自独立运行 1 折训练任务（共 4 个模型）：
  - **实例 3**：FDG Fold 1（200 epochs，806 subjects/epoch，161,200 updates）
  - **实例 4**：FDG Fold 2（200 epochs，792 subjects/epoch，158,400 updates）
  - **实例 5**：AV45 Fold 1（200 epochs，675 subjects/epoch，135,000 updates）
  - **实例 6**：AV45 Fold 2（200 epochs，690 subjects/epoch，138,000 updates）
  - **估算耗时**：依实例 3 全尺寸预检中位数 0.6123 秒/step，分别约 27.4、26.9、23.0、23.5 小时；独占不同 GPU 并行理想墙钟约 27.4 小时，串行合计约 100.7 小时。该估算未含 I/O、恢复和节点波动。
- **代码根目录**：`/root/autodl-tmp/DIRECTPP`
- **实验代码**：`/root/autodl-tmp/DIRECTPP/experiments/baselines/swinunetr`
- **Full 依据元数据**：`/root/autodl-tmp/DIRECTPP/reports/original_author_reproduction_20261020`
- **SwinUNETR 报告目录**：`/root/autodl-tmp/DIRECTPP/reports/swinunetr_2fold_20261029`
- **Full 缓存目录**：
  `/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3`（待从实例 3 流式同步）
- **本地高 IO 资产目录**：
  `/root/autodl-tmp/DIRECTPP_swinunetr/20261029`
- **持久化共享存储目录**：
  `/autodl-fs/data/`

## 硬件与环境核验状态

1. **GPU 硬件**：已实测确认独占 48 GB RTX 4090，0 进程，空闲就绪。
2. **免密登录**：本机 SSH 公钥（`id_ed25519.pub`）已部署至实例 6，免密登录生效。
3. **依赖安装**：已安装 `monai==1.5.2`、`nibabel==5.4.0`、`einops==0.8.2`、`scipy==1.18.1`。
4. **代码同步**：已同步至 `/root/autodl-tmp/DIRECTPP`，核心文件（`run.py`、`model.py`、`cohort.json`）SHA-256 与本地及实例 3/4/5 完全一致。
5. **机房内网全互信**：已配置与集群实例（实例 3、实例 4、实例 5）的全双向免密互信登录（`ssh instance3` / `ssh instance4` / `ssh instance5`）。
6. **工程验证**：`smoke-test --size 64 --cuda` 验证通过（`status: PASS`, 62,186,659 参数）。
7. **训练状态（2026-10-29 14:27 UTC）**：AV45 Fold 2，200 epochs，PID `4799`，状态运行中；RTX 4090 UUID `GPU-dc44f816-7167-e31f-ccb3-47b0f6dbc8c2`。日志：`/root/autodl-tmp/DIRECTPP_swinunetr/20261029_instance6/logs/av45_fold2.log`。Full 逐人 OOF 指标文件从本地按原哈希补齐后，Full 身份、缓存和全尺寸预检均通过；启动记录已同步到本地同名报告目录。
