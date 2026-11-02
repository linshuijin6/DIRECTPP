# 临床分类基线执行记录

18个正式fit已于2026-11-02 09:53 CST接入实例3–6。每个fit显式使用200 epochs、batch_size=5、CE、Adam lr=1e-4、每2轮validation；仅内部验证ACC选择checkpoint，最终test一次。当前为启动记录，不能当作18项完成报告。

现有run.py、watch_queue.py和splits.csv的内容与本地一致，未修改代码或重新划分。四台48GB RTX 4090启动前均无计算进程。仅同步缺少的1,452,705字节临床CSV，未上传影像；八项特征和训练子集内的中位数填补、标准化沿用原实现，不含诊断标签输入。

## 四轮试跑

| 条件 | 实例 | 任务/折 | 总耗时 | 后续epoch均值 | 峰值GPU分配显存 | 状态 |
|---|---:|---|---:|---:|---:|---|
| clinical | 3 | mci_cn/F1 | 3.05秒 | 0.085秒 | 0.063GiB | 训练、2次validation、checkpoint、单次test通过 |
| mri_clinical | 4 | mci_cn/F1 | 211.38秒 | 25.435秒 | 10.60GiB | 训练、2次validation、checkpoint、单次test通过 |

模型参数分别为18和11,244,690。两次试跑均为batch_size=5；试跑结果独立保存，不计入正式统计。

## 正式任务分配

| 实例 | Clinical-only | MRI+Clinical | 正式fit数 | 队列PID |
|---|---|---|---:|---:|
| 3 | AD/CN F1/F2/F3 | MCI/CN F1；EMCI/LMCI F1 | 5 | 131635 |
| 4 | MCI/CN F1/F2/F3 | MCI/CN F2；AD/CN F1 | 5 | 134949 |
| 5 | EMCI/LMCI F1/F2/F3 | MCI/CN F3；AD/CN F2 | 5 | 48497 |
| 6 | 无 | AD/CN F3；EMCI/LMCI F2/F3 | 3 | 134282 |

每个GPU同一时间仅运行一个fit，复用现有watch_queue.py顺序等待子进程；没有新增调度系统。正式输出位于`/root/autodl-tmp/DIRECTPP_classification_3fold/20261102_clinical_instanceN/{task}/{condition}/foldK/`，包含best_model.pth、test_metrics.json、test_predictions.csv、summary.json、history.csv及clinical_preprocessing.json；不覆盖此前63模型。每个fit完成后由原队列脚本复制到已有共享存储`/autodl-fs/data/DIRECTPP_classification_3fold/20261102_clinical/`。

启动后核对：7/18已完成、四条队列均为CLASSIFICATION_RUNNING；实例3/6已进入MRI+Clinical训练，实例4/5处于临床fit后续或切换阶段，无STOPPED_ERROR。各项状态为启动快照，不作持续轮询。

## 耗时与后续计时器

依据MRI+Clinical四轮实测，以各任务train/validation批次数及加载数据量推算，18项合计约10.02 GPU-hours；各实例队列约2.38/2.46/2.45/2.73小时，中心完成估计2026-11-02 12:37 CST。规划范围约12:15–13:20（0.85–1.25倍耗时余量，并非统计置信区间）。首次加载和不同任务速度仍有不确定性。

已记录下次估时检查为2026-11-02 12:52 CST（见timer.json），此前不频繁检查。完成后只汇总18项正式test结果、6组mean±sample SD及全部OOF预测；不执行显著性检验，不改稿、Figure 5或Notion，不提交Git。

依据文件：assignments.csv、instanceN_queue.json、pilot_launch.json、pilot_check.json、pilot_release.json、launch.json、startup_status.json、time_estimates.csv、timer.json。正式结果待全部完成后另行汇总，不能用本启动记录替代。
