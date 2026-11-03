# G1 E1 fixed-weight score removal

两折全量推理在本次任务开始前已完成，1479+1482=2961 volumes，1856 subjects；本次只补统计汇总。Full checkpoint为f9455190/fc69fa4e，原epoch index164（完成165轮），与W1的550ac2c4/f67e4a78不同。两分支同MRI、tracer、权重，替换Full患者token为冻结Age+Sex+Weight的No-Scores患者token。不是空token，不是重新训练的No-Scores消融。

原pilot8幅Full重放逐值一致；全量阶段不重放Full，使用既存Full参考测量，full_replay列为空是设计所致，不能称2961幅全部重新验证逐位重放。原入口对fold、checkpoint、prediction/cache身份、eligible cohort与指标索引的核验全部运行通过。输出12项对比，10000次fold-stratified paired bootstrap，seed20261017；ROI MAE/brain MAE为主要终点，每终点FDG+AV45组成Holm2项族，置换p来自10000次paired sign permutations。其他SSIM/PSNR/输出差异CI为描述性边际区间。

差值=No-Scores−Full。FDG ROI MAE增加约0.000036，AV45约0.000079；两项在各自端点族内有统计支持，但绝对效应很小。brain MAE在FDG无明确方向、AV45增加约0.000144。两示踪剂SSIM7/11反而随移除评分上升、PSNR下降，指标方向不一致。实际输出平均绝对改变约0.001019 FDG/0.001105 AV45 arbitrary units；证明固定权重对条件有非零响应，不证明可靠临床增益。所有CI均条件于固定权重与队列，不反映重训变异。

| tracer   | metric                      |    n |         mean |       ci_low |      ci_high |   p_permutation |   p_holm_within_endpoint_two_tracers |
|:---------|:----------------------------|-----:|-------------:|-------------:|-------------:|----------------:|-------------------------------------:|
| fdg      | roi_mae                     | 1597 |  3.63611e-05 |  1.18272e-05 |  6.01943e-05 |      0.00179982 |                           0.00359964 |
| fdg      | brain_mae                   | 1597 | -1.39166e-05 | -3.50725e-05 |  7.21746e-06 |      0.220378   |                           0.220378   |
| fdg      | psnr                        | 1597 | -0.00417362  | -0.00673816  | -0.00160625  |    nan          |                         nan          |
| fdg      | ssim7                       | 1597 |  0.000220733 |  0.000182378 |  0.000260921 |    nan          |                         nan          |
| fdg      | ssim11                      | 1597 |  0.000215856 |  0.000178967 |  0.000253801 |    nan          |                         nan          |
| fdg      | full_vs_no_scores_voxel_mae | 1597 |  0.00101927  |  0.00100572  |  0.00103318  |    nan          |                         nan          |
| av45     | roi_mae                     | 1364 |  7.87648e-05 |  4.56388e-06 |  0.000152402 |      0.039996   |                           0.039996   |
| av45     | brain_mae                   | 1364 |  0.0001445   |  9.57843e-05 |  0.000193458 |      0.00019998 |                           0.00039996 |
| av45     | psnr                        | 1364 | -0.0201903   | -0.0247279   | -0.0157227   |    nan          |                         nan          |
| av45     | ssim7                       | 1364 |  0.000684918 |  0.000619745 |  0.000750227 |    nan          |                         nan          |
| av45     | ssim11                      | 1364 |  0.000554805 |  0.000491236 |  0.000619548 |    nan          |                         nan          |
| av45     | full_vs_no_scores_voxel_mae | 1364 |  0.00110469  |  0.0010868   |  0.00112321  |    nan          |                         nan          |

分折实际差值见fold_differences.csv；各分支分折均值及sample SD见fold_descriptive.csv。未开展新的Adapter拟合或生成训练。没有发现现成MMSE数值扰动入口，故未新增复杂embedding消融。
