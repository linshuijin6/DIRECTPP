# PET-only分类接续队列（2026-11-02）

36项正式训练已于北京时间11:13部署至实例3–6，当前均等待各自临床队列的管理PID退出，尚未开始PET-only fit。仅在原队列QUEUE_COMPLETE后才接入；原临床训练继续运行。新旧输出目录独立，未终止或抢占原任务。

## 范围与参数

四种输入real_fdg、syn_fdg、real_av45、syn_av45分别只加载对应PET，不拼接MRI或临床变量。三个任务ad_cn（470人，AD阳性）、mci_cn（741人，EMCI+LMCI阳性）、emci_lmci（436人，LMCI阳性）；每项3折，共36次。沿用固定splits.csv及内部validation名单、原始五模态完整队列，不新增QC排除。

保留1通道MONAI DenseNet121、CE、Adam lr=1e-4、batch_size=5、200 epochs、每2轮验证、内部验证ACC严格大于时更新checkpoint、最终outer test评价一次。现有watch_queue.py正式命令显式传--epochs 200。每个fit保留best_model.pth、history.csv、summary.json、test_metrics.json、test_predictions.csv。

## 已部署的接续

| 实例 | 原临床队列PID | 新等待/队列PID | PET-only fit数 | 预计接入（CST） | 预计完成（CST） |
|---|---:|---:|---:|---|---|
| 3 | 131635 | 135054 | 10 | 11-02 12:04 | 11-02 22:01 |
| 4 | 134949 | 138337 | 8 | 11-02 12:21 | 11-02 21:22 |
| 5 | 48497 | 49971 | 9 | 11-02 12:24 | 11-02 21:53 |
| 6 | 134282 | 137129 | 9 | 11-02 12:31 | 11-02 22:08 |

任务按各实例当前临床队列剩余时间和实测单通道批次耗时静态分配，详细顺序见[assignments.csv](assignments.csv)。这是一次性固定名单，不增加运行时调度系统；每台机器仅一个fit占用GPU。四台原队列各自结束后独立接续，不等其他实例释放。

等待方式为Linux pidfd退出事件：绑定原临床队列管理PID及/proc启动时间，覆盖该队列剩余子进程及共享存储复制。云端conda没有os.pidfd_open，现有pidwait程序也未提供有效等待，因此通过标准库ctypes调用这些x86_64/Linux实例的pidfd_open syscall（434），由select无限阻塞等待内核退出事件，不做定时PID或GPU轮询。原队列成功退出后，再沿用原runner核对GPU释放并顺序执行。
内核API依据：[Linux pidfd_open手册](https://man7.org/linux/man-pages/man2/pidfd_open.2.html)。若原临床队列异常退出，接续会记录STOPPED_ERROR，保留原结果，不静默越过失败。

## 核验与保存

- 四台均用真实短CPU子进程验证内核PID事件等待：实际阻塞约0.8秒，进程退出后唤醒；未执行额外GPU训练作为等待测试。
- 部署后已确认四个新队列均为WAIT_PRIOR_QUEUE_EXIT，/proc中的pidfd实际指向指定旧队列PID，新队列进程存活；旧GPU训练继续运行。证据见[armed_status.json](armed_status.json)。
- 四台四种PET字段均存在完整1106人影像路径；没有重新上传影像、检查图像哈希或重新生成影像。
- 云端代码在替换前与本地修改前一致；新源码语法检查通过并采用临时文件原子替换，运行中的原队列及已启动fit使用其已加载代码。固定splits.csv未重建、未改写。
- 新输出：`/root/autodl-tmp/DIRECTPP_classification_3fold/20261102_pet_only_instanceN/{task}/{condition}/foldK/`；原runner完成每项后复制到`/autodl-fs/data/DIRECTPP_classification_3fold/20261102_pet_only/`。不覆盖此前63个影像或18个临床模型。

## 耗时

按当前单通道MRI+Clinical实测批次速度外推，PET-only总成本约38.1 GPU-hours，中心完成时间约11月2日22:10 CST。PET-only文件读取成本尚为外推，规划范围约20:40–23:40，并非统计置信区间。当前部署成功只证明接续已就绪，不代表36个模型已开始或完成。

## 文件改动

- [run.py](../../../experiments/classification_3fold/run.py)：新增四个PET-only条件映射，训练主体和预处理不变。
- [watch_queue.py](../../../experiments/classification_3fold/watch_queue.py)：仅为本次接续加入可选的原队列PID退出事件等待及成功状态检查；原有队列未设置该选项时行为不变。
- [README.md](../../../experiments/classification_3fold/README.md)：说明PET-only输入和接续入口。
- 本目录：36项分配、四实例queue计划、prelaunch_snapshot.json、launch.json、armed_status.json、time_estimates.json及本报告。未修改论文、Figure 5、Notion或原始数据；未提交Git。
