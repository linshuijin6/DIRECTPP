# 远程实例 3

本文件记录用于复现并训练修稿所需 SwinUNETR MRI-to-PET 对比方法基线的云端计算实例。仓库不保存密码；当前已配置 SSH key 免密登录。

## 连接

```bash
ssh -p 44919 root@connect.westb.seetacloud.com
```

- 核验日期：2026-10-29（Asia/Shanghai）
- 远端 hostname：`autodl-container-9b594ca734-b8eefc9f`
- 用户：`root`
- 所在区域：AutoDL 西宁机房（`westb`，与实例 2 处于同一机房）
- **实例互信**：已配置与实例 2（40818）的双向免密互信，可直接在终端使用别名：
  - 在实例 3 上运行 `ssh instance2` 直达实例 2
  - 在实例 2 上运行 `ssh instance3` 直达实例 3
- GPU：NVIDIA GeForce RTX 4090，UUID `GPU-78b16573-7ae5-8fd3-653b-cae3904821d5`，显存约 48 GB (49140 MiB)
- Python：`/root/miniconda3/bin/python`（Python 3.12.3）
- 已核验依赖环境：
  - PyTorch: `2.5.1+cu124` (CUDA 12.4)
  - Torchvision: `0.20.1+cu124`
  - MONAI: `1.5.2`
  - Nibabel: `5.4.0`
  - einops: `0.8.2`
  - SciPy: `1.18.1`
  - NumPy: `2.1.3`

## 路径规划与分工定位

- **当前分工定位**：FDG Fold 1，固定 200 epochs。此前 800-epoch v4 目录和记录均保留；当前全新初始化运行使用 `20261029_instance3_v5`，不从旧 checkpoint 恢复。
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

当前四实例分工（各实例独立初始化、单独 tracer/fold）：实例 3 FDG Fold 1（806 个训练目标，161,200 updates）；实例 4 FDG Fold 2（792，158,400）；实例 5 AV45 Fold 1（675，135,000）；实例 6 AV45 Fold 2（690，138,000）。按实例 3 先前真实全尺寸 10-step 预检中位数 0.6123 秒/step 粗估，单实例约 27.4、26.9、23.0、23.5 小时，四实例独占不同 GPU 并行理想墙钟约 27.4 小时；不含 I/O、恢复及节点波动。

## 已核验工程证据

1. **代码一致性核验**：
   - 代码直接传输自本地，严格未改动源码。
   - `run.py` SHA-256：`9092e7f732c2094a84cb00601d5ca39d8fa18a673f17270dbceac8f22c8e6456`（100% 一致）
   - `model.py` SHA-256：`97942d6d6fe262a00d2d1253c8fa76daf535ce2b0ae8423b4b69a69bb3a23947`（100% 一致）
   - `cohort.json` SHA-256：`91ee8eeec5ea853c4517df868e85fccd2857164a8e4171ba81e45121e5dc9311`（100% 一致）
   - `split_manifest.csv` SHA-256：`007e49835ed44c73dea69a94e390dded33c495c21033089f83d05b429519977c`（100% 一致）

2. **模型参数量**：
   - 构造检查：MONAI 1.5.2 兼容构造函数（显式 `spatial_dims=3`，省略历史 `img_size` 参数）。
   - 参数量：严格为 `62,186,659`，与本地工程校验完全相符。

3. **GPU 冒烟前向测试**：
   - 运行命令：
     ```bash
     cd /root/autodl-tmp/DIRECTPP && \
     /root/miniconda3/bin/python experiments/baselines/swinunetr/run.py smoke-test --size 64 --cuda
     ```
   - 结果：`status: PASS`，输出张量 `[1, 1, 64, 64, 64]`，全值有限（finite），CUDA 与模型推理链路正常。

## 当前状态与后续启动

- **2026-10-29 14:26 UTC**：FDG Fold 1 全新训练已启动，200 epochs，PID `2034`；日志 `/root/autodl-tmp/DIRECTPP_swinunetr/20261029_instance3_v5/logs/fdg_fold1.log`。使用 RTX 4090 UUID `GPU-78b16573-7ae5-8fd3-653b-cae3904821d5`。
- 本次代码哈希为 `917b677d03c04b88446df42f9550b087e068431fa33c5f25a514fb3405aa5d76`；全尺寸预检通过。启动配置和收据在报告子目录 `reports/swinunetr_2fold_20261029/instance3_fdg_fold1_200/`，旧 v4 运行资产未改动。
