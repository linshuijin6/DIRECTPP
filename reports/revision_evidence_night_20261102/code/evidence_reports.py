from pathlib import Path
import json,hashlib
import numpy as np,pandas as pd
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102'
def md(frame):return frame.to_markdown(index=False,floatfmt='.6g')

# E1: saved No-Scores and Full-reference measurements; no inference or bootstrap rerun.
frames=[pd.read_csv(ROOT/f'reports/r2_5_inference_score_removal_20261030/full/fold{f}/per_subject_metrics.csv') for f in (1,2)]
d=pd.concat(frames,ignore_index=True); rows=[]; differences=[]
for (tracer,fold),s in d.groupby(['tracer','fold']):
    for m in ('roi_mae','brain_mae','psnr','ssim7','ssim11'):
        for condition,c in [('Full','full_'+m),('No-Scores',m)]:
            rows.append(dict(tracer=tracer,fold=fold,metric=m,condition=condition,n=len(s),mean=s[c].mean(),sample_sd=s[c].std(ddof=1)))
        differences.append(dict(tracer=tracer,fold=fold,metric=m,n=len(s),mean_delta=s['delta_'+m].mean(),sample_sd_delta=s['delta_'+m].std(ddof=1)))
    differences.append(dict(tracer=tracer,fold=fold,metric='full_vs_no_scores_voxel_mae',n=len(s),mean_delta=s.full_vs_no_scores_voxel_mae.mean(),sample_sd_delta=s.full_vs_no_scores_voxel_mae.std(ddof=1)))
pd.DataFrame(rows).to_csv(OUT/'G1_E1/fold_descriptive.csv',index=False);pd.DataFrame(differences).to_csv(OUT/'G1_E1/fold_differences.csv',index=False)
contrasts=pd.read_csv(OUT/'G1_E1/paired_summary/contrasts.csv')
(OUT/'G1_E1/REPORT.md').write_text('''# G1 E1 fixed-weight score removal

两折全量推理在本次任务开始前已完成，1479+1482=2961 volumes，1856 subjects；本次只补统计汇总。Full checkpoint为f9455190/fc69fa4e，原epoch index164（完成165轮），与W1的550ac2c4/f67e4a78不同。两分支同MRI、tracer、权重，替换Full患者token为冻结Age+Sex+Weight的No-Scores患者token。不是空token，不是重新训练的No-Scores消融。

原pilot8幅Full重放逐值一致；全量阶段不重放Full，使用既存Full参考测量，full_replay列为空是设计所致，不能称2961幅全部重新验证逐位重放。原入口对fold、checkpoint、prediction/cache身份、eligible cohort与指标索引的核验全部运行通过。输出12项对比，10000次fold-stratified paired bootstrap，seed20261017；ROI MAE/brain MAE为主要终点，每终点FDG+AV45组成Holm2项族，置换p来自10000次paired sign permutations。其他SSIM/PSNR/输出差异CI为描述性边际区间。

差值=No-Scores−Full。FDG ROI MAE增加约0.000036，AV45约0.000079；两项在各自端点族内有统计支持，但绝对效应很小。brain MAE在FDG无明确方向、AV45增加约0.000144。两示踪剂SSIM7/11反而随移除评分上升、PSNR下降，指标方向不一致。实际输出平均绝对改变约0.001019 FDG/0.001105 AV45 arbitrary units；证明固定权重对条件有非零响应，不证明可靠临床增益。所有CI均条件于固定权重与队列，不反映重训变异。

'''+md(contrasts[['tracer','metric','n','mean','ci_low','ci_high','p_permutation','p_holm_within_endpoint_two_tracers']])+ '\n\n分折实际差值见fold_differences.csv；各分支分折均值及sample SD见fold_descriptive.csv。未开展新的Adapter拟合或生成训练。没有发现现成MMSE数值扰动入口，故未新增复杂embedding消融。\n')

# All currently known G1 representation/conditioning evidence.
(OUT/'G1/REPORT.md').write_text('''# G1 conditioning and VLM evidence

τ/Adapter：复用既存10组（5设置×2折）表示层结果与核验；未重新拟合或调参。τ=.82为目标余弦平方软惩罚，非硬不等式。T082跨tracer余弦均值.821419，无跨项T000为.989683；原始两文本余弦.8205374479与.82的两位近似一致，但不能据此补写作者当时选值动机，更不是生成质量优化得到的阈值。该表示实验没有生成器性能评价。

W1 Full/TracerOnly运行审计：患者token确实进入cross-attention并产生非零输出响应；重复同条件推理差异0。固定权重actual→empty的差异大于actual→shuffled近邻患者token差异。全队列患者向量高度相似，但并非相同。独立训练Full/TracerOnly的总体影像差异不能归因于患者条件单因素，须保留未设固定训练种子/不同初始化的限制。TracerOnly未支持稳定Full优势；不得把旧报告提出的“可能在局部更好”当作已证实结论。

W1 Full/TabularMLP：Full SSIM在两tracer较高，TabularMLP的PSNR/MSE反而较好，MAE未见Holm校正差异；只支持指标依赖的整套训练结果，不直接证明BiomedCLIP单模块因果贡献。数值敏感性不能由embedding非零变化推出临床有效性。

Full/OT ROI：使用W1 Full/TracerOnly预测及E1冻结mask/Real target（不是E1生成模型）。两tracer总体ROI MAE点估计偏向OT，FDGΔ(OT−Full)=−.000766，95%CI[−.001175,−.000364]，Holm p=.0012，|dz|=.093；AV45区间跨0。196个ROI的Full−OT MAE比较中12个BH显著，方向均为OT，无关键ROI支持Full优势。本次完整保留该不利结果。

评分移除独立见../G1_E1/REPORT.md；临床分类独立见../G5/REPORT.md。这些证据不能填补全部七项系统消融、前瞻临床验证或尚未处理的G8来源问题。
''')

# G5: preserve existing imaging estimates and add the completed clinical evidence.
clinical=pd.read_csv(OUT/'G5/clinical_summary.csv');tab=[]
for (task,condition),s in clinical.groupby(['task','condition']):
    row=dict(task=task,condition=condition)
    for m in ('ACC','AUC','SEN','SPE','balanced_ACC'):
        r=s[s.metric==m].iloc[0];row[m]=f'{100*r["mean"]:.2f} ± {100*r.sample_sd:.2f}'
    tab.append(row)
paired=pd.read_csv(OUT/'G5/existing_imaging_paired_comparisons.csv');pp=[]
for r in paired.itertuples():
    pp.append(dict(task=r.task,reference=r.reference,AUC=f'{r.delta_AUC_pp:+.2f} [{r.delta_AUC_ci_lower_pp:+.2f}, {r.delta_AUC_ci_upper_pp:+.2f}]',balanced_ACC=f'{r.delta_balanced_ACC_pp:+.2f} [{r.delta_balanced_ACC_ci_lower_pp:+.2f}, {r.delta_balanced_ACC_ci_upper_pp:+.2f}]'))
new=pd.read_csv(OUT/'G5/clinical_paired_comparisons.csv');new_auc=new[new.metric=='AUC'][['task','target','reference','delta','ci_low','ci_high']].copy();new_auc[['delta','ci_low','ci_high']]*=100
(OUT/'G5/REPORT.md').write_text('''# G5 分类正式测试、临床基线与ROC

本次收集并核验18/18临床fit（200epochs、非pilot、test_evaluations=1、outer-test名单/标签/阈值一致），复用63项影像fit及其既存bootstrap/逐折DeLong，不重训、不重推理。三任务N=470/741/436，正类AD/EMCI+LMCI/LMCI，MCI-U未纳入。18项临床预测共3294行；影像11529行。全部81fit均完整，无按结果删折。Clinical-only是18参数线性分类器；MRI+Clinical为11244690参数模型，名称不表示Tabular-MLP生成消融。

## 临床结果（3折mean±sample SD，百分数/百分点）

'''+md(pd.DataFrame(tab))+'''

Clinical-only在AD/CN三折观察到零错误，经验bootstrap CI退化为[100,100]，这不证明总体错误率为0或完美泛化。输入8项临床变量包含Global CDR、MMSE等与诊断相关量表；高性能不能证明Syn-PET提供独立增量临床价值，也不能据此解决诊断循环性、上游填补/来源等未核实问题（G8不处理）。MRI+Clinical也明显高于MRI/Syn双PET，但在某些任务折间SD很大。

## 已有影像配对结果（Syn双PET−参照，百分点）

'''+md(pd.DataFrame(pp))+'''

以上为既存5000次fold/class配对bootstrap的边际95%CI，没有同时覆盖或多重比较校正。AD/CN相对MRI的ACC/AUC/balanced ACC支持条件性改善；MCI/CN三者CI跨0且点估计为负；EMCI/LMCI仅balanced ACC的原区间[2.02,11.98]支持改善，ACC/AUC区间跨0。Syn−Real双PET三任务AUC区间均跨0，不构成等效证据。AD/CN ACC原区间上界约−.00272个百分点，接近0，不能夸大有限bootstrap的边界结果。

## 新增临床对照的AUC差值（百分点）

'''+md(new_auc)+'''

新比较在分析前固定：Syn双PET−Clinical-only、Syn双PET−MRI+Clinical、MRI+Clinical−MRI、Clinical-only−MRI，每任务4项；各指标使用同一轮fold×class层内受试者抽样，5000次seed20261102，3折指标等权均值的配对差。12×5项CI均为边际未校正区间；不写成多重比较控制后的总体显著性。Syn双PET相对两个临床条件的AUC区间在三个任务均低于0，当前测试中没有独立增量优势。

逐折DeLong：原18项不重跑，另增加36项临床相关配对；原18和新36分开作为Holm族。p_holm不替代原始p；36项若方差退化则保留缺失并以p1计入族大小，不补造p。本数据均可计算。任何逐折p都不能被平均或直接称为三折总体DeLong显著，未提供总体DeLong p。

ROC：三任务PNG均显示MRI、Real双PET、Syn双PET、Clinical-only、MRI+Clinical，三折TPR曲线等权平均，FPR网格步长.005，2000次fold/class重采样的逐点95%带。图例AUC为原始经验fold AUC均值，不是pooled score AUC，也不是有限网格曲线积分。置信带条件于固定模型/划分，不包含重新训练随机性，不为同时置信带。图像输入资产来源与W1 Full checkpoint绑定限制见../G2/REPORT.md。
''')
(OUT/'G6/REPORT.md').write_text('''# G6 Full单步推理效率

实测对象为W1 Full fold1 epoch165（550ac2c4），同一真实MRI及冻结FDG/AV45条件token，输入[1,1,160,192,160]，CUDA FP32、原attention后端。RTX4090 24GB，PyTorch2.5.1+cu121；两tracer分别warmup10次、计时50次，GPU同步后的壁钟延迟。每次forward仅生成一个tracer，MRI+velocity后clamp；文本编码、预处理、磁盘I/O、CPU→GPU复制和NIfTI写入均不计入。

生成器参数9925921，不包含冻结BiomedCLIP或未在forward中常驻的其他组件。FDG mean约.251015s、AV45约.251411s；完整sample SD、median、p05/p95及50次样本见CSV。peak allocated8901482496bytes≈8.290GiB，reserved14245953536bytes≈13.268GiB；这是本进程PyTorch分配器峰值，不是整卡占用。两次相同输入forward的maxabs为0，仅证明所测固定输入条件下的确定性。

一次速度场估计在t=0加MRI构成学习得到的单步近似；不能称精确ODE积分，也不能把一次forward写成同时输出两个PET。本次未复核历史138GPUh训练成本，未由参数量推算FLOPs。缺少经验证覆盖所有attention算子的MAC/FLOP计数入口，保留不可用。其他模型只有异协议工程参数/预检记录，不构成可比延迟排行。

首次测量在结果打包时出现重复keyword错误，原100次延迟样本保留为latency_samples_attempt1.csv及失败日志；修正打包后完整重测一次并生成正式receipt。两组均不用于挑选更快结果，正式使用修复后的协议执行结果。
''')
(OUT/'G3_cases/REPORT.md').write_text('''# R3-11 fixed-rule case figures

selection_manifest_internal.csv在任何图像读取前冻结并记录SHA256。分别在W1 Full e165全体积FDG1598/AV451365逐人SSIM中，按线性经验中位/第10百分位最近者及最低值选择；平局按PTID，不按视觉替换。6张图包含MRI、Real、Syn和绝对误差的三正交中央数组切片。所有PET与误差尺度0–1，单位normalized intensity/arbitrary units；未逐图重拉伸或用预测affine证明物理左右。

两示踪剂最低SSIM均为016_S_4952（FDG.196919、AV45.173244），恰是预先存在的MRI/mask QC失败病例。它在Full全体积指标中保留、在brain-mask分析中按既定规则排除。因此这两张worst-case图主要提示既存QC/配对预处理问题，不能单独归因于生成器典型失败。此处按预先冻结的全体积排序保留它，没有换成更好看的病例，也没有重建mask或重算masked指标。需要在投稿选图时把它明确标为质量核查病例。
''')
print('COMPLETE narrative evidence reports',flush=True)
