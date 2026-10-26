# 原作者生成训练语义两折复现

本次完成的 Fold 1/Fold 2 训练与 OOF 指标见
[`MAIN_EXPERIMENT_F1_F2_REPORT.md`](../../reports/original_author_reproduction_20261020/MAIN_EXPERIMENT_F1_F2_REPORT.md)。

本目录只实现 `source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb`
零起算 cell 1、2、4、8、9、11 的隔离复现。它不导入或改写
`experiments/e1_clinical_conditioning`。

固定协议：

- `KFold(2, shuffle=True, random_state=42)`，不分层；这是根据作者说明与源码 seed
  重建的新两折，不是找回的历史名单。
- 原作者 notebook 没有设置训练 RNG seed，本复现也不设置；只记录初始状态和支持同一运行恢复。
- 训练跑满 200 epoch；epoch 165 是论文主终点，epoch 200 是源码循环终点。
- 保留两个 tracer 前向图后合并 loss，再做一次 backward；OOM 时失败，不切换到 E1 的省显存路径。
- 只报告两折 OOF 的 SSIM、PSNR、MSE、MAE；不运行分类器。

创建全新运行身份并先做静态核验：

```sh
python experiments/original_author_reproduction/run.py prepare \
  --out reports/original_author_reproduction_20261020 \
  --assets /mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020
python experiments/original_author_reproduction/run.py hash-inputs \
  --config reports/original_author_reproduction_20261020/config.json
python experiments/original_author_reproduction/run.py parity-check \
  --config reports/original_author_reproduction_20261020/config.json
```

CUDA 数值等价测试以及正式训练只能在独占、至少 45 GiB 空闲显存的 48 GiB GPU 上执行；
精确复刻训练折和留出折两个 `CacheDataset` 还要求至少 128 GiB 可用主机内存。

```sh
CUDA_VISIBLE_DEVICES=<exclusive-gpu-uuid> python experiments/original_author_reproduction/run.py parity-check \
  --config reports/original_author_reproduction_20261020/config.json --cuda --full-sample
CUDA_VISIBLE_DEVICES=<exclusive-gpu-uuid> python experiments/original_author_reproduction/run.py train \
  --config reports/original_author_reproduction_20261020/config.json --fold 1
CUDA_VISIBLE_DEVICES=<exclusive-gpu-uuid> python experiments/original_author_reproduction/run.py train \
  --config reports/original_author_reproduction_20261020/config.json --fold 2
```

中断后只允许恢复对应折自己的 `recovery.pt`：

```sh
python experiments/original_author_reproduction/run.py train --config <config> --fold <fold> \
  --resume <assets>/formal/fold<fold>/recovery.pt
```

两折训练完成后，对两个预注册终点分别推理，再汇总：

```sh
python experiments/original_author_reproduction/run.py infer --config <config> --fold 1 --epoch 165
python experiments/original_author_reproduction/run.py infer --config <config> --fold 2 --epoch 165
python experiments/original_author_reproduction/run.py infer --config <config> --fold 1 --epoch 200
python experiments/original_author_reproduction/run.py infer --config <config> --fold 2 --epoch 200
python experiments/original_author_reproduction/run.py summarize --config <config>
```

如果已存在由同一 `cohort.json` 身份生成的 MONAI `PersistentDataset` 缓存，可在推理时
传入 `--cache-dir <cache>`。入口会先按 MONAI 的 `pickle_hashing` 规则核对缓存目录必须
恰好覆盖本次 cohort 的全部缓存键；缺失、额外或来自其他 cohort 的缓存都会拒绝运行。
完成收据会记录 `input_source` 与实际缓存路径。未传该参数时仍从配置中的原始影像路径读取。

不得复用既有输出目录、历史 `first_part_165.pth` 或 E1 checkpoint。`COMPLETE` 仅表示这次新建
复现完整，不认证论文历史两折身份、历史训练 RNG 或 Fig. 2 的原始结果链。
