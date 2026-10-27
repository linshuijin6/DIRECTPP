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
