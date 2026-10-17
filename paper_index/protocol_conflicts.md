# 协议冲突与证据边界

Cell编号从0起，cell内行号从1起；精确位置和原文见 `code_evidence_locations.csv`，原cell源码与输出哈希见 `notebook_evidence.json`。本次仅解析归档文件，未执行研究cell。

1. **论文协议冲突**：BMEF_main.tex:102写生成内部3-fold，:303写two-fold，分类:152/:342写3-fold。保留原文，不替作者选择。
2. **生成条件路径**：new-final与github候选的直接text features/adapted输入分开保存。当前源码与历史输出不构成适配向量、checkpoint及论文结果的唯一绑定；本次完整source/outputs对象相等比较见 `shared_historical_outputs.json`。
3. **主生成候选划分**：new-final的test_size=1和train_loader推理不能作为独立测试。后补1856/1名单只属恢复材料；旧500/39验证人群与最终训练重叠的旧核查须保留证据边界。
4. **分类身份**：3003隐藏AD/CN候选确实存在，勿继续标成全无AD/CN。其400/rest、历史AD230/CN290输出不等于论文33组。顶层sMCI/pMCI不可重命名为AD/CN主实验；EMCI+LMCI/CN不可替代EMCI/LMCI。
5. **分类协议**：3002候选先覆盖fold变量、循环外建立loader、训练再循环KFold，不能认证有效三折；同名fold权重不能确定任务与模态。部分旧pet键与当前loader结构不符。
6. **外部队列**：真实OASIS-3候选548人/638session与论文419人(CN334/AD85)不一致，未恢复筛选依据；OAS1链接不得充数。原3003 `code/Untitled.ipynb` Cell1保存638→548，Cell9/10保存CN463/AD85；Cell5/6按OASISID跨访视平均MMSE/CDR并round，应保留统计时点边界，不能据此宣称已恢复论文队列。
7. **区域统计**：旧归档196张表的原始来源已定位为3002的 `liutuo_data/shuijin/statistics_of_regions_{av45,fdg}_adjust`，不是复制内容错误。原_new、shuijin/*_adjust分别归档；调整后表不能称未改动_new原表。原cell均值、独立t检验/硬编码星号不自动符合论文参考区归一化、配对检验和FDR。后补修订统计不替代历史论文来源。
8. **训练记录**：保留完整notebook输出与TensorBoard原件；由历史输出提取的60行(0–47及154–165)不能称完整165轮日志，不据此推断完整GPU小时。
9. **基线身份**：候选实现、输出影像及硬编码雷达图分别登记。历史ours single/ddim重复影像若未完成源端全量哈希，只沿用为待核实风险，不当作本次全量验证。

以上差异是来源和协议边界，不构成对研究意图的判断。数值相同不证明运行来源。
