```text
E1 梯度报错修复与重启，2026-10-18（北京时间）

旧任务状态：
3002 fold1 Full：日志最后记录epoch=7/iteration=400，随后Nonfinite gradient断言退出。
3003 fold2 Full：日志最后记录epoch=8/iteration=500，随后同一断言退出。
两任务均没有正式recovery.pt；旧策略每10个epoch保存，无法从中途恢复。
失败任务目录重命名为fold{1,2}_Full.failed_20261018_nonfinite；原启动报告、日志、收据保持原样。

已确认的问题：
batch_step在GradScaler.step/update前断言梯度必须有限，阻止了AMP标准溢出跳步及降尺度。
历史日志没有保存scale或出错样本，不能证明当次异常仅由scale过大造成。

修复：
遇到非有限梯度时由GradScaler阻止无效更新并降尺度，恢复CUDA RNG后重算同一受试者/时间步。
最多8次尝试，只有有限梯度实际执行一次optimizer.step后才返回并累计更新数。
非有限loss、禁用scaler时的非有限梯度或持续梯度异常仍立即失败/有界失败。
日志记录amp_overflow_retry及amp_scale，方便区分实际更新与重试。
每个已完成epoch原子写入recovery.pt；恢复时仍核对正式任务与输入身份。

验证：
两个节点各自的xiaochou环境均运行原生batch_step的CUDA回归fixture。
AMP溢出处理语义参考PyTorch官方文档：https://docs.pytorch.org/docs/stable/notes/amp_examples.html
有限loss溢出可复现，4次降尺度后恢复，只有1次有效更新；参数和Adam状态匹配参考。
Dropout CUDA RNG状态匹配单次正常前向；NaN loss和持续无效梯度不会污染参数/优化器。
fixture仅为合成Linear/Dropout验证，不是生成器质量或临床实验结果。

协议：
原划分、活动队列1856人（每折训练928）、条件资产、adapter、学习率、seed及165 epochs不变。
配置仅更新实现冻结哈希、重启授权收据及执行报告位置；旧配置和源代码在before_fix/。
新配置冻结副本见config.frozen.json，变更收据见config_change_receipt.json。
3002 GPU3：fold1 Full -> No-Scores。
3003 GPU5：fold2 Full -> No-Scores。
新队列通过nohup+setsid脱离终端，只训练，非零退出停止。
未停止任何现有进程；3002 GPU5旧TAU任务核查时已不在运行，未作干预。

启动状态：
两个Full任务均已完成首批5次真实更新，loss有限，GPU/PID/配置身份已核实；当前仍在训练。
3002 GPU3：fold1 Full，训练PID2823185，队列PID2823184，已进入epoch=1（第2个epoch）。
3003 GPU5：fold2 Full，训练PID3434650，队列PID3434649，处于epoch=0（第1个epoch）。
两节点初始化权重SHA均与原失败任务一致。
3002完成首个epoch后已保存recovery.pt，确认epoch=0、928次更新、配置身份正确、模型和优化器状态有限。
checkpoint_3002_epoch0.json记录实际保存证据；3003完成首个epoch后才产生首个恢复点。
当前启动证据以startup_3002/3003.json和launch_receipt.json为准。
新日志：logs/3002_fold1_Full.log、logs/3003_fold2_Full.log。
每条队列PID/退出码在queues/{3002_fold1,3003_fold2}/。
首发各5次实际更新检查只证明启动，不能证明越过历史第8/9个epoch失败点或165 epochs完成。
```
