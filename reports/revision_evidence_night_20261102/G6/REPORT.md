# G6 Full单步推理效率

实测对象为W1 Full fold1 epoch165（550ac2c4），同一真实MRI及冻结FDG/AV45条件token，输入[1,1,160,192,160]，CUDA FP32、原attention后端。RTX4090 24GB，PyTorch2.5.1+cu121；两tracer分别warmup10次、计时50次，GPU同步后的壁钟延迟。每次forward仅生成一个tracer，MRI+velocity后clamp；文本编码、预处理、磁盘I/O、CPU→GPU复制和NIfTI写入均不计入。

生成器参数9925921，不包含冻结BiomedCLIP或未在forward中常驻的其他组件。FDG mean约.251015s、AV45约.251411s；完整sample SD、median、p05/p95及50次样本见CSV。peak allocated8901482496bytes≈8.290GiB，reserved14245953536bytes≈13.268GiB；这是本进程PyTorch分配器峰值，不是整卡占用。两次相同输入forward的maxabs为0，仅证明所测固定输入条件下的确定性。

一次速度场估计在t=0加MRI构成学习得到的单步近似；不能称精确ODE积分，也不能把一次forward写成同时输出两个PET。本次未复核历史138GPUh训练成本，未由参数量推算FLOPs。缺少经验证覆盖所有attention算子的MAC/FLOP计数入口，保留不可用。其他模型只有异协议工程参数/预检记录，不构成可比延迟排行。

首次测量在结果打包时出现重复keyword错误，原100次延迟样本保留为latency_samples_attempt1.csv及失败日志；修正打包后完整重测一次并生成正式receipt。两组均不用于挑选更快结果，正式使用修复后的协议执行结果。
