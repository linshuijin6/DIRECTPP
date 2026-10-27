# Task A：临床条件 3D 回归 U-Net

本目录实现普通、确定性的 MRI→PET 3D 回归 U-Net 对照。它回答相同 cohort、MRI、临床
字段、tracer 和评价协议下，直接回归模型能达到何种 PET 合成性能；它不是单独隔离 VLM、
ODE 或某个网络模块的消融。

## 固定协议

- 直接读取正式 Full 的 `cohort.json` 和 `split_manifest.csv`，不调用或重建 KFold。
- 临床字段固定为年龄、性别、体重、CDR、MMSE、GDS、FAQ、NPI-Q。数值严格来自 Full
  实际使用的 `Description`，并逐人核对冻结底层表；不读取 `Research Group`。
- F=0、M=1；其余七项只用当前 fold 的训练受试者拟合 mean/std。现有 1,857 人冻结表
  八项均完整，因此不新增插补或缺失指示变量。字段属于历史已填充值，上游填补方法未恢复，
  不能整体解释为原始观测。
- 模型为 `(32,64,64,128)` 四级 3D U-Net。`8` 维临床向量与 `2` 维 tracer one-hot 经
  `10→64→256` MLP，仅在 bottleneck 做 FiLM。模型不含 BiomedCLIP、attention、时间步、
  Rectified Flow、ODE、扩散或多步采样。
- 直接对有效 PET 计算 MSE；两个有效 tracer 依次 backward 累积梯度，每名受试者只执行
  一次 Adam step。占位 PET 在预处理缓存中为全零，既不进入损失，也不进入正式评价。
- Adam、学习率 `2.5e-5`、batch size 1、AMP、200 epoch；epoch 165 是主终点，epoch 200
  是次终点。留出 loss 只监测，不选择 checkpoint。
- 推理只 clamp 到 `[0,1]`。指标与 Full 相同：完整预处理体积上的 3D SSIM（range 1、
  kernel 7）、PSNR（max 1）、MSE 和 MAE；不做真实目标驱动的后处理。

现有 Full MONAI 缓存可直接复用。入口按原 cohort 行计算 1,857 个 cache key，要求目录无
缺失或额外 `.pt`。加载后只返回 PTID、MRI、FDG、AV45 和新建的表格向量；缓存中的
`fdg_index`/`av45_index` 不会暴露给模型。

## 准备与轻量检查

所有路径必须使用新的运行身份；`prepare` 和正式输出均拒绝覆盖已有目录。

```bash
python experiments/clinical_regression_unet/run.py prepare \
  --full-config reports/original_author_reproduction_20261020/config.json \
  --clinical-table reports/e1_stage01_20261017/metadata.csv \
  --cache-dir <verified-full-cache> \
  --out reports/clinical_regression_unet_task_a_20261027_instance1 \
  --assets <isolated-assets>

python experiments/clinical_regression_unet/run.py check-config --config <config>
python experiments/clinical_regression_unet/run.py smoke-test --size 32
```

实例 1 正式运行前还执行不更新参数的完整尺寸 CUDA 检查：

```bash
CUDA_VISIBLE_DEVICES=0 python experiments/clinical_regression_unet/run.py smoke-test \
  --cuda --full-sample --config <config>
```

`PASS_NO_OPTIMIZER_STEP` 只表示工程预检通过，不表示训练开始或科学结果成立。

## 正式训练与 OOF

实例 1 的固定命令为：

```bash
CUDA_VISIBLE_DEVICES=0 /root/miniconda3/bin/python -u \
  experiments/clinical_regression_unet/run.py train --config \
  reports/clinical_regression_unet_task_a_20261027_instance1/config.json --fold 1

CUDA_VISIBLE_DEVICES=0 /root/miniconda3/bin/python -u \
  experiments/clinical_regression_unet/run.py train --config \
  reports/clinical_regression_unet_task_a_20261027_instance1/config.json --fold 2
```

两个 fold 必须串行且独立初始化。中断时只允许相同 fold、相同配置恢复：

```bash
python experiments/clinical_regression_unet/run.py train --config <config> --fold <fold> \
  --resume <assets>/formal/fold<fold>/recovery.pt
```

训练完成后，对两个固定终点分别推理并汇总：

```bash
python experiments/clinical_regression_unet/run.py infer --config <config> --fold 1 --epoch 165
python experiments/clinical_regression_unet/run.py infer --config <config> --fold 2 --epoch 165
python experiments/clinical_regression_unet/run.py infer --config <config> --fold 1 --epoch 200
python experiments/clinical_regression_unet/run.py infer --config <config> --fold 2 --epoch 200
python experiments/clinical_regression_unet/run.py summarize --config <config>
```

逐受试者预测位于 `<assets>/oof/epoch{165,200}/fold{1,2}/`；小型汇总和完成收据位于
`<report>/oof_summary/`。checkpoint、NIfTI 和运行日志不得提交 Git。
