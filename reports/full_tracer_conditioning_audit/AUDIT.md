# Full / Tracer-only 运行级审计（AUDIT）

- 审计日期：2026-10-26/27（运行证据截至 2026-10-27 12:29 `ALL_COMPLETED`）
- 代码基准：Git commit `a0e4b29`（已核实当前 `experiments/original_author_reproduction/run.py` = `1811340c…`、`experiments/tracer_only_control/run.py` = `95bc18bd…`，与 a0e4b29 逐字节一致；HEAD 13fa2c3 对 experiments/ 无改动）
- 审计性质：只读。未改模型/源码/checkpoint/缓存/已有报告；未启动训练；新增文件仅限本目录（`reports/full_tracer_conditioning_audit/`）。
- 审计对象：Full = `original_author_reproduction`（作者 two-trace DiffusionModelUNet 复现，context=[patient, tracer]）；Tracer-only = `tracer_only_control`（同一入口 + context hook，context=[fixed empty-patient, tracer]）。

## 总判定

两组**确实采用了不同的患者条件**（VALID_DISTINCT_CONDITIONS，证据见下），模型机制上患者 token 确实进入 cross-attention K/V 并在固定权重下产生非零条件响应（排除 CONDITION_IGNORED 与 SAME_INPUT_BUG）。但 Full 与 Tracer-only 是**四次互相独立、未设种子（training_seed=null）的训练**，两组逐受试者输出体素差异（max_abs 0.29–0.45、RMSE 0.020–0.034）远大于固定权重下患者 token 的直接因果效应（brain-mask MAE 0.003–0.010），且 e165/e200 之间配对差异方向翻转。因此**总体指标的微小差异不能主要归因于患者条件变化，训练随机性未解决（TRAINING_RANDOMNESS_UNRESOLVED）**；固定权重消融只给出推理期条件效应上界，不能替代配对种子重训。

## 逐项结论

### 1. 正式 train/infer 实际命令、日志、收据 —— PASS（含一处需说明的源码版本差）

- Full 训练：`run.py train --config reports/original_author_reproduction_20261020/config.json --fold {1,2}`（本地 5 次 attempt 中断后 2026-10-21 切换：云端 fold1、本地 A6000 fold2）。日志 `reports/original_author_reproduction_20261020/fold1_attempt{2..5}.log`、`fold2_local_parallel.log`（尾行 epoch 199 完成）；切换收据 `parallel_fold_switch_20261021.json`。
- Tracer-only 训练：`experiments/tracer_only_control/run.py train --config reports/tracer_only_control_20261022/config.json --fold {1,2}`（`run_two_folds.sh`，autodl）。日志 `/mnt/datas230/users/linshuijin/DIRECTPP_cloud_reports/20261025/instance2/tracer_only_control_20261022/fold1_train.log`、`instance1/.../fold2_train.log`。
- Full 推理：node3014 `oof_runtime_logs/run_fold1_infer_3014.sh`、`queue_fold2_epoch200_after_165.sh`（`run.py infer --fold N --epoch E --cache-dir <nfs_backup>`，exit=0，日志含逐行 checkpoint 哈希）。
- Tracer-only 推理：fold1 = node3001 GPU2（2026-10-26，`/mnt/datas230/users/linshuijin/DIRECTPP_control_inference_runs/20261026_fold1/run_infer.py` → `control._delegate(args, full.command_infer)`）；fold2+summarize = node3014 GPU0（2026-10-27，`DIRECTPP_control_inference_runs/20261027_folds1_2/run_sequence.sh`+`run_infer.py`+`run_summarize.py`，status.tsv `ALL_COMPLETED`）。
- preflight：Full `parity_receipt.json` static PASS / CUDA 数值 parity PASS（loss diff 0.0、grad diff 0.0）；Tracer-only 两云端实例 `preflight_receipt.json`：`train/validation/inference_path_context_override=PASS`、`cached_full_patient_token_rejected=true`、CUDA formula parity 0.0/0.0。
- conditioning_receipt：Full `.../conditioning_receipt.json`（conditions.pt `bbcd4131…`，patient (1857,512)）；两实例控制 receipt（`tracer_only_conditions.pt` `e1dfd639…`，empty-patient `691e8c92…`，fdg≠av45）。
- start.json ×4：cohort/split/input/conditions 哈希一致（`91ee8eee…`/`007e4983…`/`3f362cdb…`/`bbcd4131…`），`author_training_rng_seeded=false`，记录 initial_model_sha256 与 startup RNG 哈希；控制组另含 `condition_mode=tracer_only_fixed_empty_patient`。
- 说明（非 FAIL）：训练期云端 `run.py` 为 `d0ed9667…`（commit e1766c0），推理期/当前为 `1811340c…`（75f9746→a0e4b29）；git diff 证实差异仅为 `command_infer` 的 `--cache-dir` 工程选项与收据字段，训练/损失/上下文语义不变；`tracer_only_source_sha256=95bc18bd…` 两期一致。

### 2. 同一 PTID 的 forward 入口 context 对比 —— PASS（VALID_DISTINCT_CONDITIONS）

脚本 `audit_context.py` → `audit_context_results.json`：
- 两个条件资产 sha256 与运行收据一致（`bbcd4131…`/`e1dfd639…`）。
- 持久缓存（train/infer 实际读入的 batch 字段）`fdg_index/av45_index` 与 Full `conditions.pt` 的 `[patient_i, tracer]` **逐位相等**（4 个抽样 PTID 全 true，覆盖两折）——Full forward 入口确实使用逐患者 token。
- 控制资产 tracer token 与 Full 逐位相等（clone），FDG≠AV45；控制 context=`[empty, tracer]`，哈希与任何 Full context 不同。
- `002_S_0295`：patient `4d9638f8…` vs empty `691e8c92…`，max_abs_diff≈2.42、cosine≈0.294（`002_S_1261` 2.41/0.298；`941_S_6854` 2.38/0.308）。
- 全队列患者 embedding **存在变化**：1857 个 token 中 1845 个唯一哈希；相邻 cosine 均值 0.9979（min 0.9934）、跨折 0.9967；empty 不等于任何患者 token（患者 L2 均值 3.69 vs empty 7.01；患者间 cosine≈0.997 vs 对 empty≈0.30）。

### 3. 固定权重推理消融（actual / empty / shuffled patient token）—— PASS

脚本 `audit_infer_ablation.py` → `audit_infer_ablation_results.json`（Full fold1 e165 `550ac2c4…`、fold2 e165 `f67e4a78…`，相同缓存 MRI+tracer，timestep=0，FP32 eval，仅换 context 第一行；未重训练）：
- **同条件重复推理（数值误差对照）：max_abs = mean_abs = RMSE = brain-mask MAE = 0.0（逐位一致）**——后续差异均非数值噪声。
- actual vs empty：max_abs 0.046–0.137；mean_abs 1.3e-3–4.3e-3；RMSE 2.7e-3–8.5e-3；brain-mask MAE（mask=mri>0.01，占比≈0.40–0.43）2.8e-3–1.0e-2。目标 MAE 9 例中 7 例变差（`002_S_1261` fdg 0.02055→0.02095；`002_S_0729` fdg 0.02515→0.02603），个别略变好（`002_S_0295` av45 0.02287→0.02270）。
- actual vs shuffled（另一受试者 token，cosine 0.996–0.999）：max_abs 1.3e-3–6.6e-3；mean_abs 3.6e-5–1.8e-4；RMSE 6.9e-5–3.8e-4 —— 近邻患者 token 间输出几乎不变。

### 4. Cross-attention K/V 是否依赖患者 token —— PASS（非 CONDITION_IGNORED）

- 源码 `source_archive/vscode-3002/home/ssddata/liutuo/generative/networks/nets/diffusion_model_unet.py` L106–160：`CrossAttention.to_k/to_v = Linear(cross_attention_dim=512,…)` 直接作用于 `context`；`new_model()` 为 `attention_levels=(F,F,F,T)`、`cross_attention_dim=512`。
- 数值证据（fold1 e165、`002_S_0729`/fdg，hook 全部 8 个 attn2 K/V 层，actual vs empty patient token）：`to_k` 输出 max_abs_diff 最大 **0.852**、`to_v` 最大 **0.667**（down_blocks.3 / middle_block / up_blocks.0×2）。结合第 3 项非零输出差异与零数值噪声底，患者 token 确实进入注意力并产生非零条件响应。

### 5. fold1/fold2 epoch165/200 checkpoint 哈希与 fold1 复用核验 —— PASS

`sha256sum` 实测 vs `.json` 收据 vs OOF complete.json vs 逐行 metrics.csv 四层一致：

| | Full | Tracer-only |
|---|---|---|
| fold1 e165 | `550ac2c4b1ef27b0dbb5624445dace2a04f58a84354e4900810509401cc4ea77` | `573778adc2717ee8dcb41118da1428746bdd472ec7b7f87014407d707e0e69db` |
| fold1 e200 | `18977785fd4e0ccdb797648f9ecb139f81dfdf68923621c7b234d7fcb9fd78f6` | `6cdf299a6c97782018badd5170da541e119f16737605f9ec60b5ea783bbce02b` |
| fold2 e165 | `f67e4a788eff3d958edd1d0da8cc739691affc59de84bdf3a1ae1f2821ce4315` | `32b89214b55ed03e12c8124d245af203699ad4d187a3616a6938b4c89c206085` |
| fold2 e200 | `58a5ae21594ddb4268972e997fd1a97e37cd444522ec415a54b91f0912798690` | `afdcafe5f252bab349ee8a449724aec42c80c919f2210a2f716545f3a7c31545` |

- 8 个哈希互不相同，无交叉污染；收据含各自 `condition_mode`/`tracer_only_conditions_sha256`/`empty_patient_sha256` 身份。
- **复用的 tracer fold1 输出**：fold1 OOF（2026-10-26 node3001 生成，2026-10-27 summarize 复用）complete.json 与全部逐行 `checkpoint_sha256` 均为 tracer fold1 哈希（`573778ad…`/`6cdf299a…`）；`command_infer` 加载前强制校验 checkpoint 哈希（run.py L884–889）；8 份 metrics.csv sha256 与各自 complete.json 一致；tracer per_subject_metrics.csv（`13184303…`）与运行目录逐字节一致。
- 附注：tracer fold2 为单次连续训练（epochs.jsonl 恰 200 行，10-24 21:32 起至 10-27 04:35）；`fold2_partial_through80_20261025` 为同一 run 的 epoch-80 备份快照（start.json 与正式 fold2 相同）。

### 6. PTID+tracer+fold+epoch 独立对齐、NIfTI 抽查与 paired_comparison 生成逻辑 —— PASS

脚本 `audit_alignment.py` → `audit_alignment_results.json`：
- 两份 per_subject_metrics.csv（Full `814bf7d1…`、Tracer-only `13184303…`，均与其 completion.json 一致）按键对齐：5,926/5,926 全部命中，无单侧键；每 endpoint 2,963 行；fold1/fold2 留出 929/928，交集 0；逐行 checkpoint 配对每 (fold,epoch) 恰一对。
- **paired_comparison_summary.csv 复核**：独立重算配对 t 检验、Cohen's d、95% CI，与归档 CSV 最大偏差 **3.6e-15**；关键值复现：e165 fdg SSIM Δ=+0.00538、d=0.474、p=1.8e-72；e165 av45 SSIM Δ=+0.00134、d=0.133；e165 PSNR/MSE/MAE p=0.74–0.99；e200 av45 SSIM Δ=−0.00276（方向翻转）。生成脚本未随 a0e4b29 归档，已由本审计独立重算替代（该子项由 UNVERIFIED 转为 PASS）。
- NIfTI 体素抽查（6 对，覆盖两折、两 tracer、两 endpoint）：两侧 `prediction_sha256` 全部与 metrics 一致；Full vs Tracer-only 同一受试者输出体素 max_abs **0.29–0.45**、mean_abs 0.010–0.016、RMSE 0.020–0.034，远大于第 3 项条件直接效应。
- e165 最大效应（fdg SSIM +0.0054，d=0.474）与 e200 翻转（av45 SSIM −0.0028，d=−0.255）方向不一致，符合训练随机性主导而非稳定条件效应。

### 7. E1 Full/No-Scores 与 original_author_reproduction/Tracer-only 的实验身份与种子政策 —— PASS（身份清晰、不可混用）

- **E1**（`experiments/e1_clinical_conditioning`，资产 `/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017`）：另一实验族——临床条件 UNet（168-token Full vs 20-token No-Scores），**受控随机性**：`seed_all(cfg["seed"]+fold)`（seed=42+fold），两条件共享同一折的初始化、样本顺序与 t 采样；endpoint 仅 epoch 165；有效队列 1,856 人（`016_S_4952` QC 排除），FDG 1,597/AV45 1,364；主终点 ROI MAE/brain MAE；Full OOF 推理 COMPLETE（`reports/e1_full165_inference_20261020/REPORT.md`），No-Scores 当时待完成。
- **original_author_reproduction（Full）/tracer_only_control（Tracer-only）**：作者 two-trace 生成器语义复现；1,857 人全队列；`training_seed: null`（复刻作者 notebook 未设种子政策，`training_seed_policy="author_notebook_unseeded_user_selected"`；preflight 中 20261020/20261022 仅为 fixture seed）；两条件为**独立、未配对种子**训练（四份 initial_model_sha256 全不同：`19836203…`/`c05774cb…`/`0f940a58…`/`2d05077b…`；硬件异构：Full fold2 本地 A6000 torch2.5.1/cu118，其余云端 RTX 4090 torch2.7.0/cu128）。
- **后果**：E1 的 Full/No-Scores 配对比较在设计上控制了训练随机性；original_author_reproduction vs Tracer-only 的组间比较没有（→ TRAINING_RANDOMNESS_UNRESOLVED）。两者模型族、endpoint、指标协议（E1 有 brain-mask/ROI MAE；two-trace 复现无 brain mask，见 MAIN_EXPERIMENT_F1_F2_REPORT.md）不同，不得交叉混用或互相替代结论。

## 归类

| 类别 | 判定 | 依据 |
|---|---|---|
| SAME_INPUT_BUG | **未发现** | forward 入口 context 实测不同（第 2 项）；缓存 context 与 conditions.pt 逐位一致；控制组 context 哈希独立；8 checkpoint 无交叉 |
| CONDITION_IGNORED | **未发现** | K/V 直接由 context 线性映射（第 4 项，K max diff 0.85 / V 0.67）；固定权重输出对 empty/shuffled 有非零响应且数值噪声底为 0（第 3 项） |
| TRAINING_RANDOMNESS_UNRESOLVED | **成立（针对总体指标差异的解释）** | 四次训练 training_seed=null、独立初始化/RNG、异构硬件；逐受试者体素差异（RMSE 0.02–0.034）≫ 条件直接效应（mask MAE 0.003–0.010）；e165/e200 配对差异方向翻转；总体 ΔSSIM/ΔPSNR 无法归因于条件变化本身 |
| VALID_DISTINCT_CONDITIONS | **成立（实验执行有效性）** | 第 1、2、5 项收据与哈希核验全部通过；两组确为不同患者条件的有效运行 |

## 限制

- 固定权重消融仅覆盖 fold1/fold2 epoch165、每折 3 名受试者×2 tracer（共 9 个有效体积）+1 例 K/V hook；epoch200 未重跑消融（task 限定同一 Full checkpoint，未重训练）。
- paired_comparison 生成脚本未归档，由本审计独立重算（最大偏差 3.6e-15）替代验证。
- "训练随机性"结论基于种子政策/初始哈希/硬件/输出差异的间接证据；定量分解需配对种子重训，超出本审计授权。

## 本审计新增文件（独立路径，未触碰既有产物）

- `reports/full_tracer_conditioning_audit/audit_context.py` + `audit_context_results.json`
- `reports/full_tracer_conditioning_audit/audit_infer_ablation.py` + `audit_infer_ablation_results.json` + `audit_infer_ablation.log`
- `reports/full_tracer_conditioning_audit/audit_alignment.py` + `audit_alignment_results.json`
- `reports/full_tracer_conditioning_audit/AUDIT.md`（本文件）
