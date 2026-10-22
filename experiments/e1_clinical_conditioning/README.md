# E1：隔离的阶段0–1入口

评审范围补充（2026-10-19）：完整意见见[R2/R3 与编辑要求索引](../../reports/source_reports/REVIEW_REQUIREMENTS.md)及[合并分析](../../reports/source_reports/DIReCTpp_Reviewer3_A1E585AEE7BF88E690_20261018.md)。本 E1 的 Full/No-Scores 设计对应 R2-5、R2-16，并与 R3-1 的临床条件问题相关；它不能单独覆盖 R3-1 的 Clinical-only/MRI+clinical 分类与错配提示要求，也不能代替 R3-2 的 Table S1/插补核查、R3-8/9 的机制消融或其他新增意见。意见登记不改变本实验的既有授权、配置、终点及完成状态。

## 2026-10-17 接续启动

阶段2已由作者在“PLEASE IMPLEMENT THIS PLAN: E1 启动准备与 Gemini 交接”消息中批准。
启动版本及授权收据另存 `reports/e1_stage2_launch_20261017/`；本目录以下阶段0–1说明
保留为历史流程，不代表当前授权状态。启动前的旧试跑属于旧配置工程证据。

`run.py` 通过 `@email_on_error()` 包装正常CLI入口，成功/失败沿用各节点xiaochou邮件设置；
不在仓库复制任何邮件凭据。日志记录每epoch前5步、每100步及epoch结束。
每项正式任务的 `start.json` 和 `startup_5_updates.json` 记录版本、PID及首次5次实际更新；
它们只证明启动，不能作为完成或完整epoch吞吐证据。

3002使用 `E1_ASSETS_ROOT=/home/linshuijin/DIRECTPP_E1/stage01_20261017`，
只映射资产根目录，冻结配置/cohort中的原身份不变，加载时继续校验SHA。
同节点同折顺序执行Full、No-Scores，失败即停；不在3002并发两个RAM缓存。

正式续跑使用 `run.py train --config <frozen-config> --fold <1|2> --condition <condition>
--resume <this-task-formal-dir>/recovery.pt`。仅接受本任务version-2正式恢复点，
从已完成epoch的下一个epoch开始，恢复模型、Adam、scaler及Python/NumPy/Torch/CUDA RNG；
输入/条件版本不匹配或pilot checkpoint直接拒绝。恢复点每10个epoch及最终epoch原子写入。
AMP/xformers恢复仍为容差内复现，不声称GPU逐位一致。

当前授权只覆盖输入检查、条件准备和训练侧工程短试跑。`config.json` 的
`formal_training_authorized=false` 禁止正式训练；解剖侧别和 MRI/mask 绑定另有独立硬门槛。
不要改开关绕过验收，不得将 `pilot_only.pt` 用作正式起点。

本次收据与报告位于 `reports/e1_stage01_20261017/`；大文件独立放在
`/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017/`。
所有历史材料保持只读。当前病例空间问题见验收报告，缓存存在不代表科学评价通过。

## 入口与复现

本次 CPU 使用3003的 `xiaochou` Python，预处理明确导入原3003的
`/home/data/liutuo/code/monai`（415个Python文件已逐个确认与归档副本字节一致；
当前复现入口改用该归档副本，指纹见报告目录）；GPU 使用3014的
`/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python`。
GPU CUDA、PyTorch、MONAI、xformers版本和设备 UUID 保存在运行收据。
预处理后的张量和真实空间 affine 一起缓存，GPU 不依赖3003的原始软链。

新批次须选择新的 `--out` 和 `--assets`；不能复用初始化已完成的输出目录。

```sh
python prepare.py init --out <new-report-dir> --assets <new-assets-dir>
python prepare.py prepare --out <new-report-dir> --workers 4
python accept.py freeze --out <new-report-dir>
python accept.py source-receipt --out <new-report-dir>
python accept.py qc-exclude --out <new-report-dir>
python accept.py laterality-fix --out <new-report-dir>
python run.py bundle --config <new-report-dir>/config.json
CUDA_VISIBLE_DEVICES=<idle-gpu-uuid> python run.py encode --config <new-report-dir>/config.json
CUDA_VISIBLE_DEVICES=<idle-gpu-uuid> python run.py features --config <new-report-dir>/config.json
python run.py adapt --config <new-report-dir>/config.json
CUDA_VISIBLE_DEVICES=<idle-gpu-uuid> python run.py pilot --config <new-report-dir>/config.json --steps 36
python evaluate.py pipeline-check --config <new-report-dir>/config.json
python accept.py io --out <new-report-dir>
python accept.py figures --out <new-report-dir>
python accept.py report --out <new-report-dir>
```

完整预算报告还读取 `io_benchmark.json`，记录从该批次真实缓存读取三模态的计时；
收据中的读取时间和 GPU step 时间分列，不能把缓存命中或短试跑外推称为完整epoch实测。

`run.py train/infer` 和 `evaluate.py collect` 为后续正式入口，当前会拒绝运行。
正式运行在每折独立随机初始化，两条件使用同一初始化、顺序和t采样；
seed=42为基础seed，生成器/adapter各折使用42+fold。正式模型只选固定epoch165，
epoch零起算140进入t=0；恢复点保存优化器、scaler、RNG及输入/条件版本。
不得将试跑权重或历史Full权重传入正式训练。

正式入口采用单折RAM缓存：三模态数组最多约54.8 GB，主机RAM建议80 GiB/fit。
缓存一次加载后用于165个epoch，与核心CacheDataset及短试跑的缓存方式一致。
RAM不足时拒绝执行，不自动退化成每epoch同步重读NFS；并发两fit须为两个缓存留内存。
fold1（928人）完整RAM缓存已实测：装载345秒，峰值RSS 51.4 GiB（`full_fold_cache_probe.json`）。

24GB卡上原始双tracer同时保图短试跑触发OOM，失败日志完整保留。
当前入口逐tracer反传、同一受试者只执行一次optimizer/scaler更新，梯度累加对应原来的
`L_FDG + L_AV45`，不改变网络或损失权重。`gradient_check.py`在实际网络的小张量上
验证FP32/AMP两种路径，结果见`gradient_equivalence.json`。正式预算只适用于此执行配方。

## 科学契约

- 正式生成训练仅Full、No-Scores；No-Patient只缓存空文本embedding，留待固定Full模型敏感性分析。
- 原实际临床文本及filled值冻结；患者描述无新拟合的插补参数。来源未知不等于确认独立于PET。
- 折划分按唯一PTID、原诊断分层、seed42；分类器三折不参与E1。
- 冻结BiomedCLIP的PET特征可预计算；adapter优化只读取该训练折PTID行，完整ID记录在折内收据。
- adapter固定τ=0.82、Adam 1e-3、5000步及100倍软约束，供两条件共享；不实施E2消融。
- MRI/PET预处理保持核心notebook：历史数组加载→LPI→MRI foreground crop→MRI histogram
  normalization→160×192×160 pad/crop→1mm spacing→NormalizeIntensity→ScaleIntensity。
- 历史数组加载丢弃原affine，故新缓存另保存 `raw_affine @ processed_index_affine`；
  用MRI replay独立锚定历史mask网格（经原始MRI重采样验证为正确世界映射）。
  历史分割的Left/Right命名对全部被试统一与物理半球互换；不交换标签、不改缓存，
  单侧结果按 `hemisphere_label_map.json` 的物理名称报告（`accept.py laterality-fix`）。
- `016_S_4952` 按预设MRI/mask绑定QC排除（`accept.py qc-exclude`，`qc_exclusions.json`），
  `common.active_rows` 在 adapt/train/infer/evaluate 中过滤；不重新划分。
  有效队列adapter重拟合在 `conditions/qc_exclusion_20261017/`，阶段1原adapter保留。
- ROI有效性与PET无关：标签体素数<队列中位数10%即该被试该ROI无效（`roi_validity.json`）。
- 单tracer占位全零不进入loss；指标只在真实PET有效者上计算，强度命名normalized uptake。
- 两个主要终点为subject-level ROI MAE；关键ROI、bootstrap seed/次数及多重比较规则见config。
  PSNR/SSIM、CCC/ICC(A,1)、Bias和Bland–Altman限于归一化空间；不声称SUV/SUVR或临床等效。
- `evaluate.py clinical-only`保留CPU demographics-only/clinical-only区域Ridge，内部三折选alpha，
  空间门槛未通过时拒绝科学分析。它不是第三个生成训练条件。
- E1年龄/性别分析检验评分收益异质性；全论文疾病组间调整交给E4，不用前者替代后者。
- 新E1与未绑定相同划分的历史指标分开，不计算对历史论文的直接增益。

固定数据、模型和条件文件都应通过收据SHA256核对。No-Go也属于完成验收，不能为获得Go而
删除失败病例或重命名历史结果。
