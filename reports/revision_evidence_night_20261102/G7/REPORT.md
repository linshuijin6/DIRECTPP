# G7 历史结果、OASIS及结论范围

原Figure2雷达图未修改。既存Excel/绘图数组84/84交叉核对已PASS，复用21行×4指标，原source/cell身份保留。它们是历史绝对汇总，不能与W1固定两折OOF作配对检验。缺少逐人最终指标/明确名单的baseline不附造SD、CI、p。

OASIS已有历史AV45汇总如下；原单位保留，SSIM/MSE/MAE为percent标度、PSNR dB，不自动换成SUV/SUVR。未进行新外部推理。

| method         |   SSIM_percent |   PSNR |   MSE_percent |   MAE_percent |
|:---------------|---------------:|-------:|--------------:|--------------:|
| Cyclegan       |          40.27 |  12.38 |          4.86 |         10.78 |
| Swin-Unet      |          51.34 |  14.96 |          3.96 |         10.16 |
| DDIM(3D)       |          68.59 |  17.05 |          3.48 |          8.24 |
| SegGuidedDif   |          71.85 |  19.63 |          2.51 |          7.59 |
| Rectified Flow |          80.44 |  21.33 |          1.87 |          4.29 |
| Ours(single)   |          82.66 |  25.48 |          1.12 |          3.55 |
| Ours           |          83.97 |  26.79 |          0.94 |          3.01 |

仅此类汇总不能证明恢复了逐方法完整OOF或历史最终checkpoint/逐人测试身份。现有外部证据仅AV45，不能扩展为FDG、MCI任务、全部prompt字段可得或多示踪剂跨中心泛化。OASIS字段缺失处理、secondary screening等具体材料缺口保留，不触碰G8临床来源分析。

需要降低强度的原论文结论：

1. prognosis/早期干预：当前为横断面诊断/阶段区分，无纵向转归证据。
2. synthetic PET可替代真实PET或clinically actionable biomarker：normalized uptake与回顾性分类不足支撑，未验证临床量化或个体病理状态。
3. precisely preserved区域疾病差异/等效：历史d有偏移且个别近零符号反转；新Full ROI个体CCC中位约.35/.38；p或q不显著不证明等效。
4. VLM或临床prompt带来普遍增益：TabularMLP/TracerOnly/Single比较有不利或混合指标，独立训练随机性未控制，固定权重评分移除效应很小且方向依指标而变。
5. 三个分类任务均获益：AD/CN支持固定模型条件下增益，MCI/CN没有明确增益，EMCI/LMCI只对balanced ACC有原有边际区间支持。
6. 广泛外部泛化/临床筛查：OASIS只有历史AV45范围，无FDG/MCI外部或前瞻多中心证据。
7. 精确一步ODE积分/同时生成双PET/全流程.25秒：实际是t0单tracer网络forward加MRI的学习近似，时间排除了文本、预处理与I/O。

仅交付科学证据与限制，不撰写正式Response，不改正文。
