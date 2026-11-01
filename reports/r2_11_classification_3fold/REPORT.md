# DIReCT++ 三折分类：GPU 试跑与云端自动接续

当前状态：指定的 3002 GPU 3 四轮试跑已完成；63 次正式影像分类已获授权，并预分配给云端实例 3–6。两个临床基线不在本次自动启动范围。四实例数据上传、分发和大小校验已于 2026-11-01 01:16 CST 完成；四实例均已进入分类训练（2026-11-01 08:44 CST 核验），尚不能将“监控已部署”写成正式分类已完成。

## 已完成的 GPU 试跑

- Task/condition/fold：`mci_cn / mri_syn_both / 1`，train/validation/test 为 419/75/247 人。
- 硬件：3002 RTX A6000，49140 MiB；用户明确指定共享 GPU 3，启动前已有两个进程，剩余 15270 MiB。
- 本次使用 12 GiB 分配器上限给原任务保留显存；未终止或修改原任务。
- batch size **5**、4 epochs、每两轮验证、FP32、DenseNet121 参数量 **11,288,578**。
- 最佳内部验证 ACC 为 0.72，epoch 4；严格 `>` 更新 checkpoint。重载后最终 test 仅评估一次。
- **全部试跑指标仅用于流程检查，不能作为论文正式结果。**

| 项目 | 实测 |
|---|---:|
| 初始化总时间（含 train/validation 缓存） | 250.0 s |
| train/validation 缓存加载 | 242.9 s |
| 模型及优化器初始化 | 1.67 s |
| 第 1 epoch | 90.2 s |
| 第 2–4 epoch 平均 | 86.2 s |
| 两次 validation | 6.12 / 5.78 s |
| 两次 checkpoint 保存 | 0.23 / 0.29 s |
| checkpoint 重载 | 1.97 s |
| test 缓存加载 / 推理 | 123.9 / 19.6 s |
| PyTorch 峰值已分配 / 保留显存 | 10.78 / 11.94 GiB |
| CPU 峰值 RSS | 42.35 GiB |
| 总墙钟时间 | 12.6 min |

PyTorch 显存数字不包含其他进程，也不等于整卡显存占用。GPU 处于共享计算状态，吞吐包含资源竞争。

试跑 test 指标：ACC 0.6518、AUC 0.6790、SEN 0.8276、SPE 0.4020、balanced ACC 0.6148。这些不是正式分类结果。

## 复用与必要修改

主要复用原作者主 notebook 的零起算 cell 10、13：MONAI DenseNet121、LoadImaged、EnsureChannelFirstd、CacheDataset、CE、Adam lr=1e-4、batch 5、200 轮上限和每两轮验证。未启用被注释的归一化、裁剪、重采样或增强；没有加入 AMP、梯度累积、学习率调度或自动 OOM 搜索。

独立入口修正为：固定 subject-level 分层三折、每折 outer train 内固定留出 15% validation、折内重建 loader/模型/优化器、按内部验证 ACC 选模型、softmax 正类概率、阈值 0.5、最终单次 test、逐人预测及耗时输出。

3002 不能读取仓库软链接的目标，首次尝试在数据入口停止，日志保留为 `pilot_3002_gpu3_path_failure.log`。其后明确使用 `--data-root /home/ssddata/liutuo/liutuo_data`；五个目录的全部文件名单和文件大小与原资产逐项相同。这不是影像哈希认证。总表、原影像及原 notebook 均未改写。

## 固定三折人数

每格为“总人数（负类/正类）”。正类分别为 AD、EMCI+LMCI、LMCI。

| 任务 | fold | train | validation | test |
|---|---:|---:|---:|---:|
| ad_cn | 1 | 266（173/93） | 47（30/17） | 157（102/55） |
| ad_cn | 2 | 266（173/93） | 47（30/17） | 157（102/55） |
| ad_cn | 3 | 266（173/93） | 48（31/17） | 156（101/55） |
| mci_cn | 1 | 419（172/247） | 75（31/44） | 247（102/145） |
| mci_cn | 2 | 419（172/247） | 75（31/44） | 247（102/145） |
| mci_cn | 3 | 419（173/246） | 75（31/44） | 247（101/146） |
| emci_lmci | 1 | 246（162/84） | 44（29/15） | 146（96/50） |
| emci_lmci | 2 | 247（162/85） | 44（29/15） | 145（96/49） |
| emci_lmci | 3 | 247（163/84） | 44（29/15） | 145（95/50） |

按 PTID 稳定排序；StratifiedKFold(3, shuffle=True, random_state=42)。内部验证为 train_test_split(test_size=0.15, stratify=y, random_state=42)。各输入组合共用同一任务的外层与内部名单。原始 MCI 不纳入；016_S_4952 保留。

## 200 epochs 耗时估计

依据实测四轮、两次验证及少量真实 batch 探针外推。探针每种输入两次预热、四次计时，没有额外完整 fit 或 test 预测。单/双/三通道 DenseNet 主体相同，实测速度差异小于共享 GPU 的 batch 波动，不能按 1/2/3 倍缩放。

| 任务规模 | 单通道 | 双通道 | 三通道 |
|---|---:|---:|---:|
| ad_cn，470 人 | 3.3 h（2.4–4.0） | 3.2 h（2.3–4.0） | 3.3 h（2.4–4.2） |
| mci_cn，741 人 | 5.1 h（3.7–6.2） | 5.0 h（3.5–6.3） | 5.1 h（3.7–6.6） |
| emci_lmci，436 人 | 3.0 h（2.2–3.7） | 3.0 h（2.1–3.7） | 3.0 h（2.2–3.9） |

| 范围 | fit 数量 | GPU-hours / 单 GPU 串行小时，中心值（规划范围） |
|---|---:|---:|
| 影像 DenseNet，本次授权 | 63 | 237.5（170.9–298.8） |
| MRI+Clinical，仅估算 | 9 | 34.1（25.3–44.6） |
| Clinical-only，仅估算 | 9 | 0.2（0.1–0.4） |
| 全部 81 项，仅总量估算 | 81 | 271.8（196.3–343.8） |

63 项影像分类按同等 GPU 理想并行：两卡约 85–150 小时，四卡约 43–75 小时，中心值约 59 小时。全部 81 项理想四卡约 49–86 小时，中心值约 68 小时。**后者不构成启动临床基线的授权。**

范围是规划区间，不是统计置信区间：使用探针 batch 的最小/最大耗时并留 10% 余量，缓存加载取实测的 0.5–2 倍，checkpoint 更新次数取 1–100 次（中心 50 次）。Clinical-only 的小模型探针未计入完整 loader 开销，额外估计每 batch 0.5 ms CPU 成本并采用更宽区间。

Real/Syn 条件的计算通道相同，沿用同通道探针；实际文件解压速度不同的影响主要在一次性缓存加载。云端 RTX 4090 与共享 A6000 不同，尚无云端分类实测，不能把上述范围当作其独占性能保证。实际队列墙钟还包含旧任务等待、上传、内网分发、验证及负载不均衡。

计算明细：`time_estimates.csv`、`time_estimates_summary.json`；实测探针：`timing_probe_3002_gpu3.json`。

## 云端预分配与自动接续

用户新增授权：仅启动 63 次影像分类；Clinical-only、MRI+Clinical 暂不启动。

| 实例 | 原训练 PID | 监控 PID | 预分配 fit 数 |
|---|---:|---:|---:|
| 3 | 57412 | 75707 | 15 |
| 4 | 60766 | 79033 | 16 |
| 5 | 42438 | 43273 | 16 |
| 6 | 59831 | 78690 | 16 |

交接时间更正：原 direct_single 日志的 `seconds` 计时器在每个 epoch 内重置；最近记录 FDG 约 446–448 秒/轮、AV45 约 378–381 秒/轮。此前用户提供的 44.8/38.1 秒少算约十倍，释放时间应在 11 月 1 日上午，而非 10 月 31 日 23 点。最近保存 epoch 为实例 3/4 的 90、实例 5 的 110、实例 6 的 100（日志每十轮记录一次，并非当前精确进度）。这只修正等待预估，不改变按 PID 和 GPU 释放触发的逻辑；证据见 `cloud_prior_timing.json`。

监控在每个实例本地运行，按预估计时器到期后核对一次原 PID 及其启动时间，避免 PID 复用误判。仅当原进程退出、输入文件校验通过、试跑放行标记存在、指定 GPU UUID 匹配且没有其他计算进程时，启动本实例固定队列。各实例只运行一个 fit；遇到失败即保存状态并停止该队列，不自动重启或调参。下一项也等待 GPU 清理完成。

监控代码：`experiments/classification_3fold/watch_queue.py`；预分配：`cloud_assignments.csv`、`instance3_queue.json` 至 `instance6_queue.json`。远端状态：`/root/autodl-tmp/DIRECTPP/reports/r2_11_classification_3fold/watch_status.json`。输出在实例本地 `DIRECTPP_classification_3fold/20261031_instanceN`，每项完成后另存共享盘 `DIRECTPP_classification_3fold/20261031/日期_PID/`。

上传的 5,530 个 NIfTI 共约 53.8 GiB，均已为 `.nii.gz`。使用五路按模态分离的 SSH tar 流，AES-GCM、关闭重复压缩，只上传到实例 6 一次；各模态上传完成后经四实例共同挂载的 /autodl-fs/data 临时中转，实例 3/4/5 从共享存储并行复制到本地盘，避免 SSH 别名再次经过公网。临时只保留一个模态（最大约 14.2 GiB），三份副本校验后删除本任务的中转副本。只核验文件名单及大小，不计算影像哈希，不改写源文件。

云端已有 Full 生成阶段缓存虽同为 160×192×160，但抽查 PTID 041_S_6292 的 MRI/Real AV45，各 4,930 个体素中分别有 2,395/2,436 个数值不同，因此未用其替换本次输入，也未重新生成 Syn-PET。

上传/分发控制器：`finish_cloud_staging.py`。状态与 PID 在 `staging_status.json`、`staging_controller_pid.json`，进程逐模态监督上传结束后校验并通过共享文件系统分发，只有校验成功才在各实例写 `inputs_ready.json`。不会依据 SSH 连接失败认定原训练结束。

## 验证与限制

- 固定名单独立重算一致；每个角色包含两类，角色互斥、每名受试者恰好进入一次外层 test。
- 真实数据的原变换、缓存、拼接及 GPU forward/backward 均已在四轮试跑执行。
- 最终 test 的 247 人与固定名单逐项匹配；无重复，标签一致，概率范围与 0.5 阈值正确；ACC/AUC 已独立重算一致。
- 最佳 checkpoint 已保存、重载并用于最终 test；短试跑不是正式科学结果。
- 云端监控进程已实际启动并已改为 TIMER_WAIT_TRANSFER_CHECK（之后按剩余 epochs 估计新计时器）；四实例数据均已就绪，接续程序按计时器等待旧训练结束。后续以实际状态及训练输出为准。
- 未修改论文、Figure 5、Notion、原始临床表或影像，未运行历史 notebook，未提交或推送 Git。

估算校准补充：以探针三通道 batch 均值作参照，分别用完整试跑的训练每 batch 时间、validation 每 batch 时间及 test 每 batch 时间校准探针。不同条件乘相应校准因子；训练项为 200×训练 batch 数×校准后的探针均值，验证项为 100×验证 batch 数×校准后的推理均值。一次性缓存按人数和通道数缩放，另加首轮额外耗时、checkpoint 和 test 加载；全部明细以 time_estimates.csv 为准。

用户离开前更新执行方式：禁止频繁轮询。数据及四实例接续程序均改为定时唤醒检查，首个期限为 2026-10-31 23:58 CST（15:58 UTC）。如旧任务仍在运行，使用最近三条 epoch 耗时的中位数、剩余 epochs 和距上次记录时间重新估时，增加 3% 与 120 秒余量后设置下个计时器；不以预计时间替代 PID 退出和 GPU 释放的实际确认。

2026-11-01 01:57 CST 定时核验：四实例均有 5,530 文件、57,737,240,498 字节，大小异常为零。下一次人工核验设为 08:30 CST，以检查实例 5/6 的自动接续；不进行周期轮询。

用户于 2026-11-01 08:28 CST 更新策略：确认保留 epoch165 checkpoint 后终止原训练并接入分类。四个 checkpoint 均实际在 CPU 读取，epoch=165、任务匹配且模型 state 非空。实例 5/6 已自然结束并自动分类，不作中断；实例 3/4 对原 PID 57412/60766 发 SIGTERM 后确认退出，保留全部既有输出，并于 08:30 CST 启动分类 PID 89807/93137。当前四实例均 CLASSIFICATION_RUNNING；3/4 尚在缓存，5/6 已进入 epoch。详见 stop165_and_classification_launch.json，不能把被终止的 FDG 任务写成已完成 200 epochs。

## 2026-11-01 08:44 CST 云端实测与各实例任务

分类每个 fit 仍为 200 epochs，每 2 epochs 验证、batch size 5。165-epoch 策略仅用于原 direct_single 训练的保留和终止。当前是 3 任务×7输入组合=21组，每组3折，共63个模型；临床基线不启动。四个分类进程均有实际 epoch 日志、validation 和 best_model.pth。原四个 PID 均已结束，四份原165 checkpoint保留。

云端近期单轮约27–29秒，较此前共享A6000的86秒快。按实际训练/验证 batch 数、每实例速度及缓存规模外推，当前剩余约78 GPU-hours；最慢队列约20.4小时，中心预估 11月2日05:10 CST 全部完成。规划范围为约11月2日01:00–10:15（非统计置信区间，采用0.8–1.25倍时间余量）。这替代此前A6000对当前云端的保守耗时估计，完整明细见 cloud_time_estimates_20261101T0844.csv/json。

| 实例 | 模型数 | AD/CN | EMCI+LMCI/CN | EMCI/LMCI | 当前epoch | 中心完成预估（CST） |
|---|---:|---:|---:|---:|---:|---|
| 3 | 15 | 4 | 6 | 5 | 20/200 | 11-02 03:10 |
| 4 | 16 | 5 | 5 | 6 | 19/200 | 11-02 05:10 |
| 5 | 16 | 6 | 5 | 5 | 56/200 | 11-02 04:30 |
| 6 | 16 | 6 | 5 | 5 | 43/200 | 11-02 04:20 |

当前进度对应各实例的第1个模型，当前0/63个完整 fit完成；四台各1个模型运行，其余59个排队。每个实例依次执行其固定队列；child.wait为进程结束事件等待，不作每分钟状态轮询。

### 完整条件与折号分配

表内数字为分类外层 fold；“双PET”为FDG+AV45。

| 任务 | 影像输入 | 实例3 | 实例4 | 实例5 | 实例6 |
|---|---|---|---|---|---|
| AD/CN | MRI | 3 | — | 1 | 2 |
| AD/CN | MRI+Real FDG | — | 1/2/3 | — | — |
| AD/CN | MRI+Syn FDG | — | — | — | 1/2/3 |
| AD/CN | MRI+Real AV45 | 1/2/3 | — | — | — |
| AD/CN | MRI+Syn AV45 | — | — | 1/2/3 | — |
| AD/CN | MRI+Real双PET | — | 1 | 3 | 2 |
| AD/CN | MRI+Syn双PET | — | 2 | 1 | 3 |
| EMCI+LMCI/CN | MRI | 1/3 | 2 | — | — |
| EMCI+LMCI/CN | MRI+Real FDG | — | 2/3 | — | 1 |
| EMCI+LMCI/CN | MRI+Syn FDG | — | — | — | 1/2/3 |
| EMCI+LMCI/CN | MRI+Real AV45 | 2/3 | — | 1 | — |
| EMCI+LMCI/CN | MRI+Syn AV45 | — | — | 1/2/3 | — |
| EMCI+LMCI/CN | MRI+Real双PET | 1/3 | — | 2 | — |
| EMCI+LMCI/CN | MRI+Syn双PET | — | 1/3 | — | 2 |
| EMCI/LMCI | MRI | — | 1 | 2 | 3 |
| EMCI/LMCI | MRI+Real FDG | — | — | — | 1/2/3 |
| EMCI/LMCI | MRI+Syn FDG | 1/2/3 | — | — | — |
| EMCI/LMCI | MRI+Real AV45 | — | — | 1/2/3 | — |
| EMCI/LMCI | MRI+Syn AV45 | — | 1/2/3 | — | — |
| EMCI/LMCI | MRI+Real双PET | 1/2 | — | 3 | — |
| EMCI/LMCI | MRI+Syn双PET | — | 1/2 | — | 3 |

## 单例训练曲线核验（随机抽样，2026-11-01）

从抽样时已完成的 11 个 fit 中，以固定随机种子 20261101 均匀抽取一例，先选模型再读取指标，未按性能挑选。选中实例3：EMCI+LMCI/CN、MRI+Real FDG+Real AV45、fold1，训练419、内部验证75人。原始日志副本、抽样名单和脚本保存在 curve_check_20261101/。

核验结果：200个训练epoch连续无重复，100个验证点恰为2–200的偶数轮；训练loss与验证ACC/AUC均为有限值。训练loss从 0.661849 降到 0.00015790，最后50轮均值 0.00046148，范围 0.00006236–0.00189562。中段有波动，最后50轮保持低量级：支持“训练目标基本收敛、未持续发散”的判断，未证明非凸优化的全局最优。

内部验证后期进入平台：最后50轮ACC均值 70.93%、AUC均值 0.7820；AUC范围 0.7720–0.7889。全程最高验证ACC 77.33% 出现在epoch 24；最高验证AUC 0.8343 在epoch 52。后期均值并未持续恶化，但训练loss继续下降也没有刷新验证峰值，提示额外训练的验证收益有限，不直接判为严重过拟合。日志未记录validation loss，因此不能判断其走势。

checkpoint实际保存轮为2、4、6、22、24，最终保存轮24与summary最佳轮及首次最高验证ACC一致。此次未用test指标选模型或判断收敛，未重新推理、重训或修改运行设置。结论只限这一例。

曲线图：curve_check_20261101/training_curves.png；窗口统计：window_statistics.csv；计算依据：inspect_curve.py与curve_check.json。图已实际渲染检查，横轴、尺度、原始数值和最佳epoch标记一致。

## 全部已完成模型曲线核验（2026-11-01 19:15 CST快照）

快照包含29个已完成fit：EMCI+LMCI/CN 21个、AD/CN 8个；尚无已完成EMCI/LMCI。全部200轮训练和100次内部验证记录连续，数值有限，最佳验证ACC轮次、summary及最后一次checkpoint保存记录一致，未发现记录核验问题。已逐图检查29例，不以test分数判断收敛，不修改运行中的训练。

不能将29例一概称为稳定收敛。22例最后20轮loss均不超过0.01；4例末段反弹后回落；3例最后10轮仍有loss超过0.1的反弹：MCI/CN MRI fold2、MCI/CN MRI+Syn AV45 fold2、AD/CN MRI+Syn双PET fold2。0.01和0.1仅用于描述曲线幅度，不是新增的科学收敛判据或停止规则。低训练loss也不等于验证性能良好，例如MCI/CN MRI+Real FDG fold2验证AUC后期下降。

最佳验证ACC轮次中位数54，范围6–172，3例在100轮后达到最高值。未记录validation loss，不能分析其趋势。详细逐模型报告见 [REPORT.md](curve_check_all_20261101T1914/REPORT.md)，全部29页曲线见 [all_training_curves.pdf](curve_check_all_20261101T1914/all_training_curves.pdf)，数值与来源见 [convergence_summary.csv](curve_check_all_20261101T1914/convergence_summary.csv)。
