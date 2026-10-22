# E1 正式启动收据与工程验收

结论：四次正式训练已获作者批准；两个首发Full任务均已完成5次实际optimizer更新，loss有限、无OOM，采集收据时进程存活并占用指定GPU。任务继续固定165 epochs，尚无任何一项训练完成。

| 节点 | 首发任务 | 训练PID | 队列PID | GPU UUID | 启动检查 |
|---|---|---:|---:|---|---|
| 3002 | fold1 Full | 2563008 | 2563007 | GPU-4e00852f-6d7a-af71-10b5-1c59593a6681 | 5次更新通过 |
| 3003 | fold2 Full | 3207145 | 3207144 | GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417 | 5次更新通过 |

同折Full成功后顺序运行No-Scores；失败即停，不自动重试。3002 GPU5上的TAU任务PID2306716保留。
已停止的作者TAU任务为3002 GPU3 PID2296316和3003 GPU5 PID2998272，精确身份/后代列表见resource_handoff_*.json；未停止其他用户任务。

## 验证和版本

- 新版QC过滤覆盖训练、adapter、推理、评价、pilot和缓存探针；1856人，两折各928，原cohort、划分及16个冻结输入不变。
- 新ROI过滤与98个唯一物理名称检查通过；Clinical-only输出physical_region。
- 新续跑入口通过CPU RNG/优化器恢复及CUDA/AMP非空scaler状态恢复fixture，下一次fixture参数更新误差0；旧生成器AMP证据仍按容差解释。
- 错误条件和pilot恢复点会拒绝；正式入口只接受本任务version-2 recovery.pt。
- E1_ASSETS_ROOT在3002映射本地资产，完整1856个活动缓存和条件/adapter SHA检查通过；保留已有复制任务直到完成，未重复传输。
- 两节点真实email_on_error装饰器的成功/异常dry-run与异常重新抛出验证通过；正式队列DRY_RUN关闭。实际SMTP投递未独立验证，不能覆盖SIGKILL或断网。
- 15个冻结论文文件不变。最终配置仅改变授权、启动报告路径、授权收据及实现冻结关系，科学超参数不变。

配置SHA256：`612aa3b97b06e793337cf3a1cbbead019f2299067cb45d8f2067683bde51096b`。
依据：launch_receipt.json、startup_3002.json、startup_3003.json、engineering_checks.json、cuda_amp_resume_fixture.json、evaluation_pipeline_check.json、node_assets_3002.json、preservation_checks.json。
旧stage01验收/试跑收据保留，不冒充当前版本复测证据。3003初次后台shell未初始化队列即退出，未创建训练进程/权重；随后以独立session正常提交，历史启动尝试单独记录。

## 资源与科学解释边界

- 3002：实际RAM缓存装载376.4秒；前5步峰值reserved显存23.31GiB。此前SHA检查耗时另计；装载时间不能代表全部准备时间。
- 3003：实际RAM缓存装载511.2秒；前5步峰值reserved显存23.31GiB。此前SHA检查耗时另计；装载时间不能代表全部准备时间。

保留3090短试跑外推的250–271 GPUh总预算；A6000前5步含热身，不据此声称稳定吞吐或重新外推165 epochs。后续用完整epoch计时修订。两节点软件版本不同，均在各自运行收据记录；同折两条件固定在同一节点/环境配对， pooled分析仍按折分层，不声称统一软件栈或GPU逐位一致。

解释仍限历史conditioning fields的增量贡献及normalized-space reconstruction fidelity；不是可确认真实评分贡献、SUV/SUVR、临床等效或排除shortcut。新E1不与未绑定相同划分的历史指标合并求增益。

## 交接

Codex完成首发各5次更新检查后停止训练跟踪。Gemini按GEMINI_HANDOFF.md只读监控；队列只训练，不自动启动OOF、评价或其他实验。
