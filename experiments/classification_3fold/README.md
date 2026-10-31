# DIReCT++ 独立三折分类

主要复用原作者 `mri2pet all data-_mri classification-densenet.ipynb` 的零起算
cell 10（MONAI 缓存和加载）与 cell 13（DenseNet121、CE、Adam 和训练循环）。
归档 notebook、受试者总表和影像均保持不动；这里与已有 `classification_2fold/`
是独立的分类协议，不读取生成器折或 checkpoint。

## 固定名单

```bash
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python -B \
  experiments/classification_3fold/run.py prepare
```

从 `reports/r2_11_classification_subjects.csv` 读取五模态完整队列，按 PTID 排序。
每任务独立 `StratifiedKFold(3, shuffle=True, random_state=42)`；每个外层训练部分
使用 `train_test_split(test_size=0.15, stratify=y, random_state=42)` 固定内部验证集。
`reports/r2_11_classification_3fold/splits.csv` 是所有输入组合共用的名单，已有名单
不会被 prepare 覆盖。`split_counts.csv` 给出角色及正负类人数。

任务正类分别为 AD、EMCI+LMCI、LMCI；原始 MCI 不纳入，保留 016_S_4952。

## 单次有限试跑

仅在已确认空闲的 GPU 所在节点执行。使用该节点的绝对 Python 路径；下例的
`--gpu 0` 是物理编号，程序内部按 GPU UUID 单独绑定，不再叠加外部 CUDA 绑定。

```bash
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python -B -u \
  experiments/classification_3fold/run.py fit \
  --task mci_cn --condition mri_syn_both --fold 1 \
  --epochs 4 --batch-size 5 --gpu 0 \
  --output reports/r2_11_classification_3fold/pilot_fold1_bs5
```

默认仅 4 epochs；没有启动全部实验的命令、调度、续训或自动 OOM 恢复。
启动前拒绝已有计算进程的 GPU。OOM 后保留失败记录；人工按 5→2→1 顺序更改
batch size，使用新的输出目录。正式训练需另行授权后显式指定 `--epochs 200`。

影像条件为 `mri`、`mri_real_fdg`、`mri_syn_fdg`、`mri_real_av45`、
`mri_syn_av45`、`mri_real_both`、`mri_syn_both`。通道顺序固定 MRI、FDG、AV45。
保留 LoadImaged、EnsureChannelFirstd、CacheDataset；不新增归一化、重采样或增强。
batch size 默认 5，Adam lr=1e-4，每两轮验证。仅内部验证 ACC 严格提高才保存
checkpoint；并列保留较早模型。最终重新加载最佳模型，test 仅评估一次。
概率为正类 softmax，预测阈值固定 0.5。

额外提供两个尚需实际验证的简单基线：`clinical` 使用 8→2 线性分类器，
`mri_clinical` 将原 MRI DenseNet 池化特征与 8 项临床变量拼接后接二分类线性层。
变量为年龄、性别、体重、MMSE、GDS、CDR、FAQ、NPI-Q。仅在派生临床输入中将
体重 0 和 2.3 标为缺失；训练子集拟合中位数及标准化参数，验证和 test 只应用。
不使用诊断标签或 Description 作为临床特征，不改写临床源表。

每次 fit 保存最佳权重、逐轮耗时、最终 test 指标和逐人预测。`summary.json`
记录 GPU、参数量、加载/初始化、首轮和后续训练、每次验证、checkpoint 和 test
耗时，以及 PyTorch 峰值显存和 CPU RSS。试跑输出不作为论文结果。

## 耗时估算口径

完成试跑后，以实测初始化、首轮、后续训练均值、验证均值及 test 耗时估算：

`T200 ≈ 初始化 + 首轮 + 199×后续训练轮均值 + 100×验证均值 + checkpoint写入 + 最终test加载/推理`。

其他任务按实际训练/验证/test batch 数分别缩放。1/2 通道和 MRI+Clinical
如未计时，只能标为外推，不能假设耗时严格与输入通道数成比例。Clinical-only
需自己的短计时。无 GPU 实测时，不输出虚构的 GPU-hours。
