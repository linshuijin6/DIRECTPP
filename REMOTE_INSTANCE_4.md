# 远程实例 4

本文件记录用于与实例 3、实例 5 并行训练 SwinUNETR MRI-to-PET 对比方法基线的第四台云端计算实例。仓库不保存密码；当前已配置 SSH key 免密登录。

## 连接

```bash
ssh -p 22299 root@connect.westb.seetacloud.com
```

- 核验日期：2026-10-29（Asia/Shanghai）
- 远端 hostname：`autodl-container-58a0ln8rhl-a7b5e942`
- 用户：`root`
- 所在区域：AutoDL 西宁机房（`westb`，与实例 2、实例 3、实例 5 处于同一机房）
- GPU：NVIDIA GeForce RTX 4090，UUID `GPU-1aa1851f-d56a-2168-f42d-517dd6da300c`，显存约 48 GB (49140 MiB)
- Python：`/root/miniconda3/bin/python`（Python 3.12.3）
- 基础环境：PyTorch `2.5.1+cu124` (CUDA 12.4)
- 存储：系统盘 30 GB，数据盘 `/root/autodl-tmp` 250 GB NVMe SSD，文件存储 `/autodl-fs/data` 200 GB

## 路径规划与分工定位

- **分工定位**：专用于与实例 3、实例 5（及后续多实例）组成并行计算集群，加速 SwinUNETR 对比基线（200 epochs）训练。
- **当前固定任务**：FDG Fold 2，792 个训练目标，200 epochs，共 158,400 updates；预计约 26.9 小时（按实例 3 的实测预检中位数 0.6123 秒/step 粗估）。
- **代码根目录**：`/root/autodl-tmp/DIRECTPP`
- **实验代码**：`/root/autodl-tmp/DIRECTPP/experiments/baselines/swinunetr`
- **Full 依据元数据**：`/root/autodl-tmp/DIRECTPP/reports/original_author_reproduction_20261020`
- **SwinUNETR 报告目录**：`/root/autodl-tmp/DIRECTPP/reports/swinunetr_2fold_20261029`
- **Full 缓存目录**：
  `/root/autodl-tmp/directpp_cache/v1_3f362cdb3ebe8a94_bbcd413100d8ece3`（已核验 1,857/1,857 项，名称集合哈希 `4284fd52b2c5b4b556fa3c32fbbeaa83fb88aaa324b21ddcfd6e991a0a517e5a`）
- **本地高 IO 资产目录**：
  `/root/autodl-tmp/DIRECTPP_swinunetr/20261029`
- **持久化共享存储目录**：
  `/autodl-fs/data/`

## 硬件与环境核验状态

1. **GPU 硬件**：已实测确认独占 48 GB RTX 4090，0 进程，空闲就绪。
2. **免密登录**：本机 SSH 公钥（`id_ed25519.pub`）已部署至实例 4，免密登录生效。
3. **机房内网互信**：已配置与实例 3（`ssh instance3`）、实例 5（`ssh instance5`）的双向免密互信登录。
4. **依赖安装**：已安装 `monai==1.5.2`、`nibabel==5.4.0`、`einops==0.8.2`、`scipy==1.18.1`。
5. **代码同步**：已同步至 `/root/autodl-tmp/DIRECTPP`，核心文件（`run.py`、`model.py`、`cohort.json`）SHA-256 与本地一致。
6. **工程验证**：`smoke-test --size 64 --cuda` 验证通过（`status: PASS`, 62,186,659 参数）。
7. **训练状态（2026-10-29 14:01 UTC）**：FDG Fold 2，200 epochs，PID `4322`，状态运行中；RTX 4090 UUID `GPU-1aa1851f-d56a-2168-f42d-517dd6da300c`。日志：`/root/autodl-tmp/DIRECTPP_swinunetr/20261029_instance4/logs/fdg_fold2.log`。启动收据和预检结果保存在报告子目录 `reports/swinunetr_2fold_20261029/instance4_fdg_fold2/`；启动记录已同步到本地同名报告目录。
