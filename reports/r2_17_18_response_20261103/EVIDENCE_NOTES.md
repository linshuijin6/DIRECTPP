# R2-17 / R2-18：核对说明与中文摘要

独立英文文本：[R2-17](R2_17_RESPONSE_DRAFT.md)、[R2-18](R2_18_RESPONSE_DRAFT.md)。本次只读核对并生成文本，没有插入rebuttal或稿件，没有新增训练、推理或GPU计时。

## 中文摘要

**R2-17：基线迁移与公平性。** 本轮可以核实新增比较使用同一1,857人cohort、固定两折名单和预处理缓存，共评价1,598份FDG及1,365份AV45。Swin实际实现是3D SwinUNETR，以单通道连续输出和MSE迁移到PET强度回归，不再按分割标签训练；Single DIReCT按tracer和fold独立训练；新增临床回归U-Net接收与Full描述相同的八项临床数值，训练折内标准化，为相同临床信息下的独立模型对照。但Swin只评价200轮，Full/ClinicalUNet/Single的主终点是165轮、另有200轮次终点，不能称全部预算一致。同epoch也不等于同GPUh。历史CycleGAN、SegGuidedDiff、plain RF的最终实现与结果绑定仍缺，DDIM候选虽有3D临床条件通路，也不能因此认证原图最终运行。故回复不再笼统承诺相同调参努力、最佳配置或所有原基线完全公平。

**R2-18：计算效率。** Full fold1 epoch165生成器有9,925,921个参数，不包含冻结BiomedCLIP。现有实测在RTX4090 24GB、FP32、真实160×192×160 MRI与GPU缓存条件下进行，每tracer预热10次、同步计时50次；FDG为251.015±0.187 ms，AV45为251.411±0.256 ms。±为固定输入重复调用的sample SD，不是跨受试者SD或CI。PyTorch峰值allocated/reserved为8.290/13.268 GiB，不能称整卡占用。一次forward只生成一个tracer；计时不含文本编码、预处理、I/O、传输及影像导出。现有证据不提供完整FLOPs、同协议扩散/流基线计时或历史138GPUh核验，因此不写加速倍数或完整效率排名。

**完成范围：** 两条独立回复文本已完成；这不等于两条审稿意见的全部实证要求均已满足。缺口在英文正文中明确保留，没有把后续待完成实验写成已有结果。

## R2-17证据入口与本次核验

- 审稿原文：`reports/source_reports/review_comment_register.csv` 的 R2-17/18；稿件现有不受限公平性表述在 `manuscript/BMEF_main.tex` 基线段落，138GPUh在Implementation Details。
- Full：`reports/original_author_reproduction_20261020/config.json`、`cohort.json`、`split_manifest.csv`、`oof_summary/completion.json`；本次重新计算cohort与split文件SHA-256，与冻结配置一致。cohort SHA为`91ee8eeec5ea853c4517df868e85fccd2857164a8e4171ba81e45121e5dc9311`，split SHA为`007e49835ed44c73dea69a94e390dded33c495c21033089f83d05b429519977c`。
- Full实际预处理：`experiments/original_author_reproduction/run.py:build_transform()`，共同评价见其推理代码。读取的`oof_summary/completion.json`确认两折OOF完成，不依据旧config的PREPARED状态判断当前完成情况。
- ClinicalUNet：`experiments/clinical_regression_unet/{README.md,run.py,model.py}`、`reports/clinical_regression_unet_task_a_20261027_instance1/config.json`及`oof_summary/completion.json`。本次核对config的cohort/split哈希与Full一致，读取完成收据、165轮逐人记录与汇总；仅使用真实完成结果。
- SwinUNETR：历史核心notebook `source_archive/vscode-3002/home/ssddata/liutuo/mri2pet swinunet useful.ipynb` cell12/13与当前 `experiments/baselines/swinunetr/run.py`。本次读取四个实际实例config：`instance3_fdg_fold1_200`、`instance4_fdg_fold2`、`instance5_av45_fold1`、`instance6_av45_fold2`，epochs/final_epoch均200，cohort/split哈希与Full一致；对应`oof_launch_20261102T120914Z/instance{3,4,5,6}/complete.json`确认200轮OOF完成，人数792/806/690/675。父目录旧config仍写800轮，未把它当作当前执行证据，也未改写该旧配置。
- Single：`experiments/baselines/direct_single/{README.md,run.py,common.py}`及`reports/direct_single_2fold_20261030/`配置。本次逐个核对四任务配置的200轮训练、165/200终点、LR及cohort/split身份；`reports/revision_evidence_night_20261102/remote/single_results/{fdg_fold1,fdg_fold2,av45_fold1,av45_fold2}/metrics.csv`确为165轮，人数792/806/690/675。
- 历史DDIM候选：直接阅读核心notebook `source_archive/vscode-3003/home/data/liutuo/code/mri2pet _add pretrained commom clip_concat-ddpm.ipynb` cell16/18/30/31的相关源码，核实3D、2→1通道、MRI与noisy/current PET拼接、512维context、MSE和候选20步采样；没有将不同cell参数拼为已确认最终运行。
- 历史缺口线索：`reports/r3_10_baseline_audit_20261020/REPORT.md`和`reports/baseline_metrics_provenance_20261020/REPORT.md`。只在必要范围复核具体源码；未重启全库来源追查。对未恢复实现保持unknown，不由未检出推断不存在，也不由原方法的2D/3D设定推断本地实际运行。
- ClinicalUNet SSIM点估计直接从Full/ClinicalUNet的165轮逐人表复算；作为同输入信息对照的描述性结果，不冒充对VLM单组件收益的证明。

## R2-18证据入口与本次核验

- 正式计时原件：`reports/revision_evidence_night_20261102/G6/{receipt.json,latency_samples.csv,summary.csv}`。本次从100条正式样本重新计算每tracer的N、mean、sample SD、median、p05/p95，全部与summary在浮点精度内一致；失败尝试记录保留原位，未择优选择样本。
- 计时代码：`reports/revision_evidence_night_20261102/code/efficiency.py`。核实无optimizer，使用`torch.inference_mode()`、GPU同步、10次预热、每tracer50次计时；模型参数用`sum(p.numel() for p in model.parameters())`计算，内存用PyTorch allocator峰值，文本/传输/I/O不在计时内。
- receipt记录checkpoint SHA为`550ac2c4b1ef27b0dbb5624445dace2a04f58a84354e4900810509401cc4ea77`；与Full训练汇总fold1 epoch165字段一致。receipt中的单次真实输入、FP32、RTX4090、PyTorch2.5.1+cu121身份明确，不换写成原稿A6000/PyTorch2.6.0。
- 峰值allocated 8,901,482,496 bytes / 2^30 = 8.290151596 GiB；reserved 14,245,953,536 bytes / 2^30 = 13.267578125 GiB。
- 没有从参数量推算FLOPs，没有把两个tracer的单独均值相加冒充实测双tracer端到端耗时，没有认证138GPUh，也没有把异协议预检计时拿来构造基线加速比。
