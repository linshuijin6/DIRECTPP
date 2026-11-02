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

用户随后明确指定 3002 GPU 3 进行共享试跑：只有这种明确指定的情况才传
`--allow-shared`；本次同时传 `--memory-limit-gib 12`，给已有任务保留显存。
3002 的解释器为 `/home/pnxc/Anaconda3/envs/xiaochou/bin/python`。
该节点无法访问仓库影像软链接的目标，需明确传
`--data-root /home/ssddata/liutuo/liutuo_data`。五个模态目录的完整文件名单和
文件大小已与原资产逐项比较一致；此参数只做运行时路径映射，不改写总表。
共享 GPU 的计时包含资源竞争，不能当作独占 GPU 的性能测量。

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

`timing_probe.py` 仅对当前固定训练集的少量真实 batch 进行计时，不保存模型或
测试预测。每种输入两次预热、四次计时，用于区分通道数和临床基线的成本；
不构成额外完整 fit，不用其预测或损失作科学结果。

## PET-only 补充输入（2026-11-02获授权）

`real_fdg`、`syn_fdg`、`real_av45`、`syn_av45`分别只加载对应PET字段，
使用原单通道DenseNet121；其余训练逻辑、预处理和splits.csv保持不变。
三任务×四输入×三折共36项，输出与既有影像及临床模型分开保存。
后续队列计划可设置`wait_for_prior_queue_exit`、`prior_pid`及`prior_starttime`，
通过Linux pidfd事件等待该实例整个临床队列退出，再核对`prior_queue_status`
为`QUEUE_COMPLETE`后接续；等待期间不轮询，单GPU仍按原队列顺序运行。

## 本轮获授权的云端接续

用户新增授权实例 3/4/5/6 在原 direct_single PID 结束后自动接续 **63 项影像分类**；
临床基线暂不启动。`watch_queue.py` 读取每实例的固定队列，按预估计时器唤醒后检查一次原 PID
启动时间、GPU 释放、四轮试跑放行和数据就绪。每实例仅顺序执行自己的队列，
失败即停止，不自动恢复或更改参数。每次正式 fit 为 200 epochs、batch size 5。

`finish_cloud_staging.py` 逐模态等待原文件上传结束、核对文件大小，再借
四实例共同挂载的共享文件系统向其余三实例并行复制；校验成功才写 `inputs_ready.json`。程序、队列、部署状态
及上传状态见 `reports/r2_11_classification_3fold/`。这两个脚本是本次固定任务的
一次性接续程序，不接入外部调度器。

用户随后要求不轮询：两个接续脚本使用 --first-check-utc 设置首次唤醒期限；
未结束则按已记录进度及实际速率重新估时后睡眠。没有每分钟 PID 或 SSH 查询。
