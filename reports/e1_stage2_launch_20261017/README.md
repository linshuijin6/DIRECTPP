# E1 启动版本与监控边界

本轮作者批准：四次正式训练，fold1/fold2 × Full/No-Scores；固定165 epochs，fresh initialization。
默认两节点各一个任务，同折Full成功退出后再运行No-Scores；任一失败队列即停，不自动重试。
原始16个冻结输入和15个论文文件保持不变。阶段0–1报告保留为历史证据，当前授权以authorization.json为准。

工程检查：engineering_checks.json、evaluation_pipeline_check.json、preservation_checks.json；
两节点email_decorator_checks_*.json验证dry-run通知及异常重新抛出，未验证实际SMTP投递。
最终配置副本config.frozen.json及config_sha256.txt；实现指纹implementation_sha256.json。
CPU fixture的下一次更新逐位一致；GPU AMP/xformers只承诺已验证的数值容差，不声称逐位复现。
旧四次pilot收据对应QC修订前配置；本轮startup_5_updates.json是新版本实际更新证据，不能替代完整epoch吞吐或科学结果。

大文件：3003沿用datas230资产根；3002映射到/home/linshuijin/DIRECTPP_E1/stage01_20261017。
配置/cohort中的原资产身份不变；每次加载继续校验SHA，训练起点不读取pilot或历史权重。
代码和冻结配置从正式启动后保持不变。

任务队列及日志位于本目录queues/和logs/。每任务start.json、startup_5_updates.json及recovery.pt位于各节点资产根formal/fold{n}_{condition}/。
原报告中的“仅等待授权”已补充实际工程检查；本目录launch_receipt.json才记录首发任务的实际启动状态。

当前科学解释仍限历史conditioning fields与normalized-space reconstruction fidelity；不称真实评分贡献、SUV/SUVR或排除shortcut。
主要终点、双侧关键ROI、配对统计、Clinical-only和No-Patient的既定边界不变；本队列只执行训练。

预算：沿用3090短试跑的207.6 GPUh纯训练、含余量250–271 GPUh；A6000五步包含热身，仅作启动证据。
两节点各任务建议80 GiB RAM，避免3002两缓存并发。后续由完整epoch耗时修订A6000预算，不以五步外推稳定速度。
