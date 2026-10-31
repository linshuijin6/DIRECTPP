# DIReCT++ 三折分类入口与有限试跑状态

结论：独立训练入口和固定名单已创建，CPU 数据入口检查通过。**GPU 试跑未启动**：
当前节点以及集群的可用状态快照均未发现无计算进程的空闲 GPU。依照用户
“没有合适空闲 GPU 则停止试跑”的要求，本轮未使用共享剩余显存、未终止其他任务。
因此 batch size 5 可用性、训练/验证/checkpoint/test 流程和 GPU 耗时仍待实测。

资源检查时间与完整状态见 `gpu_availability.json`。3001、3002、3003、3014 的快照
均新鲜，但没有 ready 候选；3015 为 standby 且快照过期，不能据此认定空闲。
其他节点状态来自只读 cluster 技能，不代表已进行 SSH 或 Python 运行环境验证。

## 文件与复用

- `experiments/classification_3fold/run.py`：一个 prepare/单次 fit 入口。
- `experiments/classification_3fold/README.md`：来源、使用方式、保留参数和估算口径。
- `splits.csv`：三个任务共用输入条件的固定外层/内部名单，共 4,941 行。
- `split_counts.csv`：任务、fold、角色及正负类人数。
- `gpu_availability.json`：资源检查和未启动状态；不是训练结果。
- 本报告：已完成事项、验证边界和耗时缺口。

主要复用主 notebook 的零起算 cell 10（LoadImaged、EnsureChannelFirstd、
CacheDataset、DataLoader）和 cell 13（DenseNet121、CE、Adam、训练/验证循环）。
保留 1/2/3 通道、batch size 默认 5、lr=1e-4、最多 200 epochs、每两轮验证，
仅按内部 validation ACC 严格提高保存模型。没有启用原 notebook 中被注释的
归一化、裁剪、重采样或增强，没有增加 AMP、梯度累积、调度器或自动恢复。

必要调整为固定分层名单、折内重建数据和模型、独立内部验证、softmax 概率 AUC、
0.5 阈值、最佳 checkpoint 最终 test 一次，以及逐人预测和耗时记录。
默认只运行 4 轮；入口没有全部实验启动命令，也不会自动重试 OOM。
预留 Clinical-only 线性分类器和 MRI+Clinical 池化特征拼接线性头，均尚未运行。
只在派生临床输入中处理异常体重，填补和标准化参数仅由当前训练子集拟合。

## 三折人数及类别分布

每格为“总数（负类/正类）”。正类：AD、EMCI+LMCI、LMCI。

| 任务 | fold | train | validation | test |
|---|---:|---:|---:|---:|
| AD/CN | 1 | 266（173/93） | 47（30/17） | 157（102/55） |
| AD/CN | 2 | 266（173/93） | 47（30/17） | 157（102/55） |
| AD/CN | 3 | 266（173/93） | 48（31/17） | 156（101/55） |
| EMCI+LMCI/CN | 1 | 419（172/247） | 75（31/44） | 247（102/145） |
| EMCI+LMCI/CN | 2 | 419（172/247） | 75（31/44） | 247（102/145） |
| EMCI+LMCI/CN | 3 | 419（173/246） | 75（31/44） | 247（101/146） |
| EMCI/LMCI | 1 | 246（162/84） | 44（29/15） | 146（96/50） |
| EMCI/LMCI | 2 | 247（162/85） | 44（29/15） | 145（96/49） |
| EMCI/LMCI | 3 | 247（163/84） | 44（29/15） | 145（95/50） |

先稳定按 PTID 排序，每任务使用 StratifiedKFold(3, shuffle=True, random_state=42)。
每个 outer train 使用 train_test_split(test_size=0.15, stratify=y, random_state=42)。
同一任务同一折所有条件直接读取相同名单；不按生成器两折划分分类数据。
原始 MCI 标签不纳入，016_S_4952 保留在 AD/CN 和历史 MCI/CN 中。

## 已完成的验证

- 语法检查通过；基于真实总表独立重算三折与内部划分，名单完全一致。
- 每个任务每折没有重复 PTID；train/validation/test 互斥且覆盖该任务全部受试者。
- 每名受试者恰好进入一次外层 test；每个角色均包含两个类别。
- 概率 AUC 和固定 0.5 阈值的指标计算通过一个可手算例子检查。
- 真实 MRI/Syn FDG/Syn AV45 单例经过原变换和缓存加载，拼接得到
  `(1, 3, 160, 192, 160)` float32；这不是 GPU 显存或完整训练验证。
- 仅在 CPU 构建 DenseNet，没有执行模型 forward/backward：单/双/三通道参数量
  分别为 11,244,674 / 11,266,626 / 11,288,578，池化特征维度 1,024。
- 本地版本为 PyTorch 2.5.1、MONAI 1.5.1、scikit-learn 1.7.2。

未运行模型训练、validation、checkpoint 写入/重载或 test 推理，未产生试跑指标。
未修改原始数据、原作者 notebook、论文、Figure 5 或 Notion，未提交 Git。

## 耗时估算与仍缺的实测数据

本轮没有实测 GPU epoch、validation 或 test 时间，不能给出有依据的数值范围。
初始化、完整缓存加载、首轮、后续轮均值、峰值显存、CPU RSS、checkpoint 和
test 耗时都由 fit 入口记录，但目前没有运行记录。batch size 5/2/1 均未验证。
当前节点可见卡均为 24 GB RTX 3090，但没有选中或启动任何 GPU。

单模型 200 轮的估算公式为：

`T200 ≈ I + E1 + 199×Esteady + 100×V + C + Ltest + Ttest`

其中 I 为初始化及 train/validation 加载，C 为实际最佳 checkpoint 写入累计
（正式 200 轮最多更新 100 次）及重载，Ltest 为最终 test 缓存加载。
4 轮试跑的训练耗时应使用第 2–4 轮均值，验证使用第 2、4 轮的独立耗时。
首轮和缓存加载不能重复算入每轮稳定成本。

以指定 741 人三通道折为参照，其他任务需分别按训练、验证和 test batch 数外推。
若 batch size 为 5，741 人任务为 train 84 / validation 15 / test 50 batches；
470 人为 train 54 / validation 10 / test 32 batches；436 人为 train 50 /
validation 9 / test 29–30 batches。最后一个不满 batch 会使按 batch 数缩放略粗糙。
1/2/3 通道的 DenseNet 主体相同，不能把通道数直接当作耗时倍数；需短计时或保留
未测范围。Clinical-only 不可套用 DenseNet 耗时；MRI+Clinical 还缺融合头实测。

| 实验范围 | fit 数量 | 当前耗时估计 |
|---|---:|---|
| MRI 单通道影像 | 9 | 缺 GPU 实测 |
| MRI+单 PET 双通道影像 | 36 | 缺 GPU 实测 |
| MRI+双 PET 三通道影像 | 18 | 缺 GPU 实测 |
| 全部影像 DenseNet | 63 | 缺 GPU 实测 |
| MRI+Clinical DenseNet | 9 | 缺 GPU 实测 |
| Clinical-only | 9 | 缺轻量模型实测 |
| 全部实验 | 81 | GPU-hours、串行总耗时暂不可确定 |

理论上两/四块同等空闲 GPU 的理想时间分别为串行时间的 1/2、1/4，实际还受共享
I/O、CPU 缓存加载和任务长度影响。本轮未实现任何并行调度。

下一步需要一块确认空闲的 GPU，完成已授权的 mci_cn / mri_syn_both / fold 1
最多 4 轮试跑。如 batch 5 OOM，保留失败目录，再人工改为 2，必要时改为 1。
完成这一流程验证后才能补充实测耗时估计；全部 81 次正式训练仍需另行授权。
