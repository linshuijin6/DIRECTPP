"""Finalize inventory, reviewer mappings and execution report from actual outputs."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
import pandas as pd,numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102'
def md(frame):return frame.to_markdown(index=False,floatfmt='.6g')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
now=datetime.now(timezone.utc).isoformat()
initial=OUT/'inventory_initial.csv'
if not initial.exists():shutil.copyfile(OUT/'inventory.csv',initial)
inv=pd.read_csv(initial).to_dict('records');inv=[r for r in inv if r['experiment']!='clinical_baselines_20261102']
for r in inv:
    r['checkpoint_sha256']=r['checkpoint'];r['training_endpoint']=r['epoch'];r['task']='generation'
    if r['model'] in ('Full','ClinicalUNet','TabularMLP','TracerOnly','SwinUNETR'):
        r.update(status='COMPLETE_AND_VERIFIED',metrics_status='COMPLETE_AND_VERIFIED',missing_artifacts='none within requested statistical scope')
        if r['model'] in ('Full','TabularMLP'):
            cfg=json.loads((ROOT/'reports'/r['experiment']/'config.json').read_text());r['checkpoint']=str(Path(cfg['assets'])/f'formal/fold{r["fold"]}/first_part_165.pth')
        elif r['model']=='TracerOnly':r['checkpoint']=f'/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022/formal/fold{r["fold"]}/first_part_165.pth'
        elif r['model']=='ClinicalUNet':r['checkpoint']=f'/autodl-fs/data/DIRECTPP_clinical_regression_unet/task_a_20261027/formal/fold{r["fold"]}/checkpoint_epoch165.pt (see actual OOF receipt hash)'
        else:r['checkpoint']='remote Swin prespecified epoch200; path and SHA in source fold receipts/config'
    if r['model']=='Single':
        task=r['tracer']+'_fold'+str(r['fold']);p=OUT/f'remote/single_results/{task}/completion.json';d=json.loads(p.read_text())
        r.update(status='COMPLETE_AND_VERIFIED',training_status='COMPLETE_AND_VERIFIED',inference_status='COMPLETE_AND_VERIFIED',metrics_status='COMPLETE_AND_VERIFIED',prediction_count=d['metric_rows'],missing_artifacts='none at approved165 endpoint; FDG200 intentionally not resumed',checkpoint=f'/root/autodl-tmp/DIRECTPP_direct_single/20261030/{task}/formal/checkpoint_epoch165.pt',source=str(p.relative_to(ROOT)))
    if r['model']=='E1_FullWeights_NoScores':r.update(status='COMPLETE_AND_VERIFIED',metrics_status='COMPLETE_AND_VERIFIED',missing_artifacts='none within fixed-weight inference sensitivity scope',checkpoint='E1 frozen Full checkpoint; see run_identity.json',task='score-removal')
meta=[]
for p in sorted((OUT/'remote').glob('*_classification63_metadata.json')):meta+=json.loads(p.read_text())
meta+=json.loads((OUT/'remote/clinical18_metadata.json').read_text())
assert len(meta)==81
split_sha=sha(ROOT/'reports/r2_11_classification_3fold/splits.csv')
for r in meta:
    d=r['summary'];assert d['status']=='complete' and d['epochs']==200 and d['test_evaluations']==1 and r['checkpoint_exists']
    inv.append(dict(experiment='clinical_baselines_20261102' if d['condition'] in ('clinical','mri_clinical') else 'r2_11_imaging63',model=d['condition'],task=d['task'],tracer='NA',fold=d['fold'],epoch=d['best_epoch'],training_endpoint=200,checkpoint=r['checkpoint'],checkpoint_sha256='not rehashed; checkpoint exists, metadata+prediction hashes retained',split_hash=split_sha,training_status='COMPLETE_AND_VERIFIED',inference_status='COMPLETE_AND_VERIFIED',prediction_count=d['split_sizes']['test'],metrics_status='COMPLETE_AND_VERIFIED',status='COMPLETE_AND_VERIFIED',missing_artifacts='historical generator-to-Syn linkage remains a separate source limitation',source=r['source_metadata']))
brain=OUT/'brain_mask/completion.json';b=json.loads(brain.read_text());assert b['status']=='COMPLETE_R3_11_BRAIN_MASK_METRICS'
inv.append(dict(experiment='R3_11_brain_mask_existing',model='Full+ClinicalUNet+SwinUNETR',task='masked metrics',tracer='both',fold='1+2',epoch='165/200',training_endpoint='NA',checkpoint='existing canonical-target masked completion and source audit',split_hash='frozen original_author/E1 QC intersection',training_status='COMPLETE_AND_VERIFIED',inference_status='COMPLETE_AND_VERIFIED',prediction_count=8883,metrics_status='COMPLETE_AND_VERIFIED',status='COMPLETE_AND_VERIFIED',missing_artifacts='none; never recalculated in this task',source=str(brain.relative_to(ROOT))))
pd.DataFrame(inv).to_csv(OUT/'inventory.csv',index=False)
(OUT/'INVENTORY.md').write_text('# 已核实资产清单\n\n最终更新时间UTC：'+now+'。inventory_initial.csv保留首次盘点；inventory.csv为完成状态，共'+str(len(inv))+'行。checkpoint列记录路径/身份入口，checkpoint_sha256列区分实测/收据绑定与未重新哈希的分类权重；epoch对分类为内部验证选中的best epoch，training_endpoint=200，不能将其误读成按test选权重。\n\n已核实：W1 Full165、Clinical U-Net165、Swin200、TabularMLP165、TracerOnly165已有完整两折OOF；其原始汇总CSV与completion digest相符。Single四份165 checkpoint本次补齐2963幅OOF。FDG在此前用户要求保存165后结束训练，收据见code/single_endpoint_policy.json，故无需也没有恢复200轮训练。AV45训练完成200轮，仍按预定165主终点评价。\n\n临床18和影像63项训练metadata均complete、200epochs、test一次，81份best_model.pth在远程存在，逐人test输出已核验/复用；没有重新训练分类器。E1评分移除全量2961幅推理先前已完成，本次补统计；与W1 Full权重分离。R3-11 masked8883行（3模型×2961）原样复用。\n\n本地/NFS与远程原始资产均保留；6实例当前状态快照在remote/instanceN_probe.txt及assets_v2.json，实例1/2是无GPU模式，3–6可用GPU仅执行本次推理。未改变实例运行模式、训练状态或他人进程。\n')

groups={
'G1':(['R2-5','R2-14','R2-15','R2-16','R3-1','R3-2','R3-8','R3-9','R3-15'],'τ10组、运行级token审计、TabularMLP比较、E1固定权重评分移除','G1/REPORT.md;G1_E1/REPORT.md;G3/paired_comparisons.csv','S-N17–19;S-N03','figures/G1_tau_sensitivity_reused.png','条件响应和表示层权衡可证；无VLM独立因果增益，未补齐全部系统消融；R3-2来源/TableS1归G8不处理。'),
'G2':(['R2-3','R2-6','R2-19','R3-6','R3-13'],'W1两折OOF收据与hash、分类9组角色身份','G2/REPORT.md;G2/split_and_source_hashes.csv;G2/classification_outer_test_identity.csv','S-N22–23','NA','已核对当前受试者角色；历史分类Syn到生成checkpoint绑定、visit时间与外部prompt字段仍缺，不能宣称完整两阶段历史独立性认证。'),
'G3':(['R2-17','R3-9','R3-10','R3-11','R3-12','R3-15'],'5基线40配对终点、固定选例、已有brain-mask、历史84值','G3/paired_comparisons.csv;G3/distribution_summary.csv;G3_cases/REPORT.md;brain_mask/completion.json','S-N01–05;S-N20','figures/G3_paired_forest.png;figures/G3_case_*.png','整套模型、输入信息/epoch与独立训练随机性限制；历史汇总不能与新OOF配对；并非所有指标Full优。'),
'G4':(['R2-8','R2-9','R2-10','R3-4','R3-5','R3-11','R3-minor-05','R3-minor-19'],'历史98ROI/6组、一致性/BA、OLS16、40效应量；W1 Full/OT98ROI及新增缺失biasCI','G4/REPORT.md;G4/authorFull_OT_complete_overall.csv;G4/historical_figure4_effect_sizes.csv','S-N06–12','NA','normalized uptake arbitrary units；非SUVR、无等效/Aβ实验。历史CSV与W1预测/E1mask协议分离，后者个体CCC较低。'),
'G5':(['R2-5','R2-11','R2-12','R2-16','R3-1','R3-6','R3-7','R3-9'],'63影像+18临床正式fit、27条件CI、原6+新12配对、逐折DeLong/ROC','G5/REPORT.md;G5/validation.json;G5/clinical_paired_comparisons.csv','S-N13–16','figures/G5_ROC_*.png','逐折p不等于三折总体p；bootstrap条件于固定模型；Clinical评分与诊断可能重叠，高AUC不证明独立临床增益。'),
'G6':(['R2-13','R2-18','R3-9','R3-12','R3-15'],'W1 Full真实输入单tracer forward延迟、参数、显存、重复一致性','G6/REPORT.md;G6/receipt.json;G6/latency_samples.csv','S-N21','NA','网络FP32缓存输入计时，排除文本/预处理/I/O；单forward单tracer；无可靠FLOPs或可比全模型效率排行；不认证138GPUh。'),
'G7':(['R2-4','R2-7','R2-20','R3-3','R3-4','R3-13','R3-14','R3-15'],'历史84绝对值、现有OASIS AV45范围、新OOF及分类的真实边界','G7/REPORT.md;G7/historical84_values.csv;UNRESOLVED.md','S-N20;其他组表','NA','回顾性横断面证据；不支持预后、替代PET、临床量化等效、FDG/MCI外部泛化或普遍获益。'),
'G8':(['R2-5','R2-16','R3-1','R3-2','R3-6'],'OUT_OF_SCOPE','用户本次明确排除','NA','NA','不处理临床数据来源、历史缺失值或TableS1异常。')}
register=pd.read_csv(ROOT/'reports/source_reports/review_comment_register.csv').set_index('comment_id');mat=[]
for group,(comments,experiment,files,tables,figures,limits) in groups.items():
    for comment in comments:
        assert comment in register.index
        r=register.loc[comment];mat.append(dict(group=group,reviewer_comment=comment,review_topic=r.topic,experiment=experiment,source_file=files,result='OUT_OF_SCOPE' if group=='G8' else '实际数值见所列结果；证据范围有限，非意见全部解决',supplementary_table=tables,supplementary_figure=figures,limitations=limits))
matrix=pd.DataFrame(mat);matrix.to_csv(OUT/'G1_G8_EVIDENCE_MATRIX.csv',index=False)
(OUT/'G1_G8_EVIDENCE_MATRIX.md').write_text('# G1–G8 审稿证据映射\n\n分组采用用户指定定义；逐项编号核对本地原始意见登记。已产出证据不等于意见整体解决；G8始终OUT_OF_SCOPE。\n\n'+md(matrix)+'\n')

hist=pd.read_csv(OUT/'G7/historical84_values.csv');oasis=hist[hist.cohort=='OASIS']
(OUT/'G7/REPORT.md').write_text('''# G7 历史结果、OASIS及结论范围

原Figure2雷达图未修改。既存Excel/绘图数组84/84交叉核对已PASS，复用21行×4指标，原source/cell身份保留。它们是历史绝对汇总，不能与W1固定两折OOF作配对检验。缺少逐人最终指标/明确名单的baseline不附造SD、CI、p。

OASIS已有历史AV45汇总如下；原单位保留，SSIM/MSE/MAE为percent标度、PSNR dB，不自动换成SUV/SUVR。未进行新外部推理。

'''+md(oasis[['method','SSIM_percent','PSNR','MSE_percent','MAE_percent']])+'''

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
''')

unresolved='''# 尚未解决与未执行事项

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
'''
(OUT/'UNRESOLVED.md').write_text(unresolved)
status=pd.DataFrame([
['W0','COMPLETE_AND_VERIFIED','6远程实例+本地/NFS完成收据、最终inventory'],
['W1','COMPLETE_AND_VERIFIED','Single4fold165共2963新推理；5baseline共40paired endpoints；已有结果不重跑'],
['W2','COMPLETE_AND_VERIFIED','固定6病例三正交误差图；worst既定QC问题明示；R3masked不重算'],
['W3','COMPLETE_AND_VERIFIED','63影像+18临床；复用旧统计，补临床CI/逐折比较及3ROC置信带'],
['W4','COMPLETE_AND_VERIFIED','历史98ROI、OLS16、效应量40；Full/OT98ROI；仅补缺失biasCI/BH；brain表原样复制'],
['W5','PARTIAL','E1全量推理已先前完成，本次补12对比+分折；τ/token/VLM证据复用；MMSE入口缺失、全消融未完成'],
['W6','PARTIAL','Full真实输入延迟/显存/参数完成，split/hash/outer-test完成；FLOPs与历史Syn生成身份缺口保留'],
['W7','COMPLETE_AND_VERIFIED','历史84值、OASIS AV45、G1-G8映射与23组补充表草稿'],
['G8','OUT_OF_SCOPE','按用户要求未执行']
],columns=['work_package','status','actual_outcome'])
(OUT/'TASK_STATUS.md').write_text('# 任务最终状态\n\n更新时间UTC：'+now+'。状态反映本工作包证据准备，非审稿意见全部解决。\n\n'+md(status)+'\n\n未训练、未恢复训练、未重新选择checkpoint或划分；未改正式LaTeX/BibTeX/Figure，未编译论文、提交或推送，未访问Notion。无需为了凑9小时重复计算。\n')
status.to_csv(OUT/'task_status.csv',index=False)

# Final execution report with exact numerical tables.
distribution=pd.read_csv(OUT/'G3/distribution_summary.csv');summary=[]
for (model,tracer),s in distribution.groupby(['model','tracer'],sort=False):
    row=dict(model=model,tracer=tracer,N=int(s.n.iloc[0]))
    for m in ('ssim','psnr','mse','mae'):
        rr=s[s.metric==m].iloc[0];row[m.upper()]=f'{rr["mean"]:.6g} ± {rr.sample_sd:.6g}'
    summary.append(row)
paired=pd.read_csv(OUT/'G3/paired_comparisons.csv');selected=paired[['model','tracer','metric','n','mean_delta','ci_low','ci_high','cohen_dz','full_better_proportion','p_raw','p_holm']].copy()
selected['full_better_proportion']*=100;selected=selected.rename(columns={'full_better_proportion':'Full better pct'})
e1=pd.read_csv(OUT/'G1_E1/paired_summary/contrasts.csv')
brain_summary=pd.read_csv(OUT/'brain_mask/summary_metrics.csv')
exec_report='''# Overnight revision scientific evidence completion

交付目录固定为reports/revision_evidence_night_20261102/；实际执行跨至2026-11-03（Asia/Shanghai）。仅补证据，不修改论文或正式Response。下面数值均来自实际资产。

## 1. 训练与checkpoint

W1 Full e165、Clinical Regression U-Net e165、SwinUNETR e200、TabularMLP e165、TracerOnly e165均已有冻结两折OOF。Single4份e165 checkpoint均核实；FDG此前由用户明确要求保存e165后停止，AV45完成200轮；本次不续训，仍使用预定165主终点。63影像与18临床分类的81份正式metadata及best_model.pth存在，按内部validation ACC选择，test一次。E1评分移除Full权重为另一模型族；完整hash/位置见inventory.csv与remote收据。

## 2. 本次新增与复用

新增推理仅Single4fold共2963幅（FDG1598、AV451365），写入各原实例的新报告目录。Full、ClinicalUNet、Swin、MLP、TracerOnly不重新推理；E1评分移除2961幅在开始前已完成，仅补统计。R3-11 brain-mask的8883行及16配对检验不重新计算，原表字节一致复制。新增统计只涉及缺失的W1配对/分布、临床18fit汇总/比较/ROC、E1全量汇总和保存ROI的缺失biasCI；既有完整ClinicalUNet、影像分类bootstrap与逐折DeLong不重跑。

## 3. 全体积真实结果

以下为mean±sample SD，N跨受试者。SSIM无单位，PSNR dB，MSE/MAE分别为平方/原normalized uptake单位。全体积含背景；不是brain-mask指标，不是SUV/SUVR。

'''+md(pd.DataFrame(summary))+'''

## 4. Full与五基线的严格受试者配对

Delta=Full−baseline，SSIM/PSNR正值有利，MSE/MAE负值有利；Cohen dz保留符号。每baseline单独Holm8项族；CI为10000次按held-out fold固定样本数的paired bootstrap95%边际区间，seed42。Full better为严格个体获益比例百分数。冻结模型/单次独立训练的区间不估计跨seed变异。

'''+md(selected)+'''

ClinicalUNet8项均支持Full，但AV45 MSE |dz|=.075很小。Swin的FDG MAE无Holm显著差异，且Swin为MRI-only/e200，与Full临床条件/e165并非等信息/等预算比较。TabularMLP在两tracer的PSNR/MSE优于Full，而Full SSIM更高；MAE无Holm差异。TracerOnly的FDG4指标与AV45SSIM优于Full，其余AV45无明确校正差异。Single在FDG SSIM优于Full，而Full FDG PSNR/MSE更好；Full AV45 SSIM更好，MAE两tracerHolm p约.05275，不跨越校正标准。不能写成Full全面优于所有baseline。

MLP与Full的独立训练不是VLM单模块因果证明。TracerOnly使用独立初始化/unseeded训练，现有运行审计已保留随机性限制。Single使用独立tracer模型和原Single条件编码，不能宣称仅joint/separate单因素。旧whole-volume冻结指标的target缓存有极小浮点差异已在R3masked来源审计登记；本次不重算旧结果或宣称逐数组canonical一致。

## 5. Brain-mask已有证据的纳入

原完成报告为reports/r3_11_brain_mask_metrics/run_20261102/，completion与canonical target identity审计PASS。3模型×2961 subject-tracer=8883行，FDG1597/AV451364。两组comparison各8项均支持Full，16项Holm p<.05，属于该masked协议。ClinicalUNet AV45 MSE/MAE效应极小（|dz|约.071/.076），不能写成普遍个体或临床显著改善。SynthSeg非零label union包含CSF/ventricles；SSIM仅完整7窗口中心。两份LaTeX及CSV原样纳入S-N04/05，没有重建mask、重算masked指标或其bootstrap/p值。

## 6. G5分类、临床基线与ROC

63/63影像fit复用，18/18临床fit本次从共享存储恢复，完整3折无遗漏。27条件共81fit；三任务470/741/436人，正类AD/EMCI+LMCI/LMCI，MCI-U不加入。Clinical-only三任务AUC fold均值分别1.000000/.989345/.999364；MRI+Clinical为.991662/.930705/.896020。完整ACC、AUC、SEN、SPE、balanced ACC mean±SD与CI见G5/REPORT.md和S-N13。

Syn双PET相对MRI：AD/CN有原有条件性bootstrap改善证据；MCI/CN无明确增益；EMCI/LMCI只对balanced ACC有边际CI支持。Syn双PET的三任务AUC均低于Clinical-only及MRI+Clinical，新增配对AUC区间均低于0。量表与诊断相关性/历史临床来源未解决，不能把高Clinical性能当成独立临床验证。经验100%bootstrap区间不能证明总体零错误。

原18逐折DeLong不重跑，仅添加Holm18族，均无校正后p<.05；新36逐折比较使用单独Holm36族，33项p<.05。这些均不构成三折总体DeLong检验。所有bootstrap CI条件于已训练模型/固定划分，未作同时多重区间调整。三张ROC显示5个指定条件和2000次fold/class逐点95%带，图例为fold平均AUC，非pooled AUC。

## 7. G1条件敏感性、VLM与Adapter

τ10个既有表示层fit完整复用，T082平均余弦.821419，T000约.989683；τ=.82是平方软惩罚目标，原文本余弦.820537与其两位近似一致，不能称性能优化阈值或硬约束。患者token运行审计证实非零注意力/输出响应，但shuffle近邻token输出变化很小。未新增任何Adapter训练或复杂数值扰动消融。

E1全量评分移除差值如下，严格与W1 Full分开。ROI/brain MAE为主要终点，各端点两tracer组成Holm2族；SSIM/PSNR CI为描述性。

'''+md(e1[['tracer','metric','n','mean','ci_low','ci_high','p_holm_within_endpoint_two_tracers']])+'''

移除评分带来很小ROI MAE增加，但SSIM7/11上升、PSNR下降；不是一致质量获益或重新训练No-Scores消融。Full/OT区域MAE既有结果也未支持Full增量价值。全部不利/混合结果保留。

## 8. G2划分与G6效率

W1生成两折1857人929/928，train/test交集0；OOF行fold与manifest逐项相符。分类9个task/fold train/validation/test互斥，正类/名单与保存预测一致。生成split/hash、分类outer-test身份及种子/模型版本见G2。分类输入沿用历史data_augmentation目录；没有把这些历史Syn资产虚假绑定为本轮W1 Full165，作者2fold→3fold设计说明与实际资产绑定证据分开保留。没有重启历史全库审计。

Full生成器9925921参数。RTX409024GB、FP32、真实[1,1,160,192,160]MRI、缓存条件token，warmup10+每tracer50次同步计时：FDGmean.251015s，AV45mean.251411s；peak allocated约8.290GiB、reserved13.268GiB。单forward单tracer；不含文本编码、预处理、I/O和拷贝，不能称端到端双PET.25秒。无可靠完整FLOPs计数入口，未外推历史138GPUh；同输入两次输出maxabs0仅是本次确定性测量。

## 9. G4与补充材料

历史196个overall ROI与1176个group ROI统计完整保留；16个实际Pearson/OLS、40个AD−CN效应量纳入，Figure4E使用VentralDC28/60。W1 Full/OT预测在E1冻结mask/Real数组协议下已有98ROI指标，不是E1生成模型；本次只从保存区域均值补392行缺失biasCI/paired p/BH98。Full across-ROI CCC中位FDG.35214、AV45.38490，与历史CSV的.9450/.9745不属于相同实验结果，不能移植或作配对对比。新增bias BH98显著计数：FDG Full35/OT73，AV45 Full28/OT28。所有量称normalized uptake arbitrary units，p/q不显著不证明等效。

23组Supplementary CSV/LaTeX草稿、6张固定病例PNG、3张ROC置信带PNG、1张配对森林图、1张复用τ图（11张PNG），索引见SUPPLEMENTARY_TABLE_INDEX.md及FIGURE_INDEX.md。所有LaTeX仅位于新目录；原Figure2/3/4/5不修改，未编译论文。

## 10. 未完成项与真实原因

G8按指令排除。现成MMSEembedding扰动入口未找到，FLOPs无可靠完整计数器，历史最终运行及部分分类Syn生成身份未完全恢复，OASIS仅已有AV45范围，且禁止新增训练或外部推理；故这些缺口不通过重训、换权重/队列或虚构统计补齐。具体限制与禁止的临床量化项目见UNRESOLVED.md。

## 11. 审稿证据映射

G1–G8逐comment映射见G1_G8_EVIDENCE_MATRIX.md/CSV，直接采用用户分组并核对原登记编号。证据文件、结果、表图与限制逐项列明。R3-11的masked、选例与ROC部分有可交付证据，OASIS逐人不确定性/临床量化部分仍缺；任何工作包完成状态不等于整条意见全部解决。

## 12. 需要降低强度的结论

不支持无纵向结局的prognosis/早期干预；不支持合成PET临床替代、SUVR/Centiloid或等效性；不支持全部区域precisely preserved或VLM/临床条件的普遍独立增益；不支持三任务一致改善或FDG/MCI外部泛化；不把一次单tracer近似forward称精确ODE积分或端到端双PET生成。具体依据见G7/REPORT.md。

## 执行与验证记录

未启动/恢复训练，未重选epoch/seed/split，未终止既有进程，未修改原权重/预测/缓存。没有访问Notion、写外部消息、改正式稿件/BibTeX/图、编译论文或提交/推送。首次whole-volume配对因Swin tracer字段大小写差异停止，规范内存键后继续且未重复ClinicalUNet统计；首次效率结果打包有keyword错误，失败样本完整保留后仅修复该失败检查并重测；表格首次语法错误日志保留。以上工程失败不隐匿、不作为科学结果。
'''
(OUT/'EXECUTION_REPORT.md').write_text(exec_report)
print('COMPLETE final documents',len(inv),len(mat),flush=True)
