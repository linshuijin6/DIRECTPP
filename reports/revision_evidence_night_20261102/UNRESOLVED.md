# 尚未解决与未执行事项

| 项目 | 实际原因与状态 |
|---|---|
| G8/Table S1 | OUT_OF_SCOPE，未分析临床来源、历史填补或表格异常。 |
| 全套七项系统消融、跨随机种子因果归因 | 禁止新训练；既有独立训练不能拆分初始化/训练随机性与条件/编码模块贡献。 |
| 历史Figure2/4精确最终运行绑定 | 84个绝对汇总及指定ROI CSV已恢复；所有最终checkpoint、逐人名单与绘图流程尚未统一绑定，不能补造SD/CI/paired p。 |
| 63项分类Syn输入的生成折身份 | 分类名单/outer-test结果已核对，输入指向历史data_augmentation目录；未把它们认证为本轮W1 Full165生成资产。按作者2fold→3fold说明保留，未重启全库追查。 |
| 临床基线高性能及独立临床价值 | 含诊断相关量表，AD/CN观察到完美分离；经验bootstrap[100,100]不代表总体无错误。来源/缺失问题归G8，本任务不解决。 |
| 三折总体DeLong | 仅逐折有效；18/36两族Holm记录不构成三折总体p。Bootstrap为固定模型/划分的条件区间，未覆盖重训方差或消除训练集重叠。 |
| Whole-volume目标数组逐字节一致性 | 严格配对subject/tracer/fold及冻结缓存协议；brain-mask报告已记录云端target约2.38e-7浮点差。旧whole-volume指标不改写，不宣称canonical目标逐位一致；R3-11 masked已统一canonical且只复用。 |
| 新Full区域协议 | Full/OT预测属于W1，ROI mask和Real区域目标来自E1冻结数组，和R3-11 canonical-target图像指标协议分开。历史ROI CSV为第三套来源。禁止把高历史CCC移植给新Full。 |
| 最差病例 | 两tracer均016_S_4952，既定MRI/mask QC失败；按预设whole-volume排序保留且明示，不作典型模型失败或masked病例展示。 |
| Full效率的外推 | 仅一真实MRI、一个GPU、固定条件；不含文本/预处理/I/O。无经验证完整算子FLOP/MAC计数器；其他模型无同协议延迟，历史138GPUh未认证。 |
| 冻结BiomedCLIP的MMSE数值扰动 | 相关当前实验目录未发现现成入口，条件未满足；未另建复杂消融。 |
| OASIS FDG/MCI、外部逐人CI | 无允许使用的已完成对应资产；仅保留历史AV45绝对汇总，用户禁止新外部推理。 |
| Aβ状态、SUVR/Centiloid、TOST等临床量化 | 明确不执行；没有确定参考区/界值，不能换标签或模拟统计。 |

这些限制不通过重复计算或更换seed、epoch、受试者、目标缓存来消除。不利结果全部保留。
