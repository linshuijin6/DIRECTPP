# G1 conditioning and VLM evidence

τ/Adapter：复用既存10组（5设置×2折）表示层结果与核验；未重新拟合或调参。τ=.82为目标余弦平方软惩罚，非硬不等式。T082跨tracer余弦均值.821419，无跨项T000为.989683；原始两文本余弦.8205374479与.82的两位近似一致，但不能据此补写作者当时选值动机，更不是生成质量优化得到的阈值。该表示实验没有生成器性能评价。

W1 Full/TracerOnly运行审计：患者token确实进入cross-attention并产生非零输出响应；重复同条件推理差异0。固定权重actual→empty的差异大于actual→shuffled近邻患者token差异。全队列患者向量高度相似，但并非相同。独立训练Full/TracerOnly的总体影像差异不能归因于患者条件单因素，须保留未设固定训练种子/不同初始化的限制。TracerOnly未支持稳定Full优势；不得把旧报告提出的“可能在局部更好”当作已证实结论。

W1 Full/TabularMLP：Full SSIM在两tracer较高，TabularMLP的PSNR/MSE反而较好，MAE未见Holm校正差异；只支持指标依赖的整套训练结果，不直接证明BiomedCLIP单模块因果贡献。数值敏感性不能由embedding非零变化推出临床有效性。

Full/OT ROI：使用W1 Full/TracerOnly预测及E1冻结mask/Real target（不是E1生成模型）。两tracer总体ROI MAE点估计偏向OT，FDGΔ(OT−Full)=−.000766，95%CI[−.001175,−.000364]，Holm p=.0012，|dz|=.093；AV45区间跨0。196个ROI的Full−OT MAE比较中12个BH显著，方向均为OT，无关键ROI支持Full优势。本次完整保留该不利结果。

评分移除独立见../G1_E1/REPORT.md；临床分类独立见../G5/REPORT.md。这些证据不能填补全部七项系统消融、前瞻临床验证或尚未处理的G8来源问题。
