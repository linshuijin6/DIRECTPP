# E1 阶段0–1验收报告（修订版）

结论：**科学验收通过，等待阶段2授权（GO_PENDING_AUTHORIZATION）**。四次正式训练未启动，`formal_training_authorized=false`。

## 本次修订解决的两项阻止项

1. MRI/mask绑定：`016_S_4952`按阶段0预设QC规则（保存MRI重放误差>2e-6，八种轴翻转均无法绑定）排除出adapter拟合、训练、OOF推理和全部评价。未重新划分；`cohort.json`字节不变，排除名单见`qc_exclusions.json`。有效队列1856人（FDG 1597、AV45 1364）；两折留出各928/928人。两折adapter已在有效队列上重拟合至`conditions/qc_exclusion_20261017/`（fold1 FDG/AV45 795/687、fold2 802/677），与留出集合交集为0；阶段1原adapter保留不动。
2. ROI侧别：根因是历史分割的左右命名对全部被试统一反转，而不是缓存仿射或个别病例错误。推测机制（未直接复现分割步骤）：历史流程以无头数组读取LAS存储的MNI配准MRI，并以identity头保存后分割，分割器按identity头理解左右，导致“Left/Right”名称与实际半球互换。原始配准MRI本身未镜像（20/20例与MNI模板的未翻转相关高于x翻转）。缓存仿射`ref.affine @ proc.affine`经原始MRI重采样验证是正确的索引→世界映射（10例相关系数0.988–0.999，x镜像映射仅0.58–0.75）。在该仿射下，白质、壳核、侧脑室、丘脑四对大结构在1856/1856人中全部呈一致镜像，无例外。
   - 处理：不交换mask标签、不翻转网格、不改缓存；冻结`hemisphere_label_map.json`，报告时用物理半球名称（如label 17报告为物理Right-Hippocampus）。
   - 子代理最初结论（“仿射叠加两次”）不成立，已在`reports/e1_laterality_rootcause_20261017/CORRECTION.md`更正；其全队列“零镜像”统计反映的是同一一致性。曾按其建议生成的错误修正文件已移至`superseded_wrong_affine_fix/`，未被任何入口使用。
   - 对E1：主要终点ROI MAE是对全部有效ROI取均值，与半球命名无关；预设关键ROI均为双侧成对，选择不变。仅涉及单侧的报告需用物理名称。
   - 历史论文若有单侧ROI表述，可能存在同样的命名互换；本轮未修改论文，建议作者单独核对。
3. ROI有效性（与PET无关）：某标签体素数低于队列中位数10%时，该被试该ROI视为无效。17人共168个ROI单元无效；其中7人各有20–24个无效ROI（整体分割质量差），按原计划只计“共同有效ROI”，并在98区完整者敏感性分析中自然排除，不新增被试排除。

## 已通过与解释限制（保留）

- Full/No-Scores 168/20 tokens，无截断、按PTID绑定；两条件同折初始化、样本及t序列一致。
- 评分来源：观测可追溯值与实际条件值有38个字段不一致；填补方法未恢复，未确认诊断派生或直接PET依赖（不能据此宣称不存在）。结论限定为历史conditioning fields贡献。
- 强度：normalized uptake（arbitrary units），不称SUV/SUVR、临床等效或已排除shortcut。
- 新E1两折与历史结果隔离，不与历史指标计算增益。
- AMP下恢复后一步更新最大参数差约2.8e-6，属数值容差内重放，非逐位复现（xformers flash backward非确定）。

## 实测预算（1856人有效队列）

- 硬件：server，NVIDIA GeForce RTX 3090；训练峰值reserved显存23.19 GiB（24 GB卡余量小，配方为逐tracer反传＋expandable allocator）。
- 四次165-epoch纯训练外推：207.6 GPUh；推理0.280秒/卷，两条件共0.46 GPUh。
- 单折RAM缓存实测：928人装载345秒，峰值RSS 51.4 GiB；建议每fit 80 GiB主机内存，两fit并发需约160 GiB。
- 合计（含装载及20–30%余量）：250.1–270.9 GPUh，单卡约10.4–11.3天，两卡约5.2–5.6天。
- 若每epoch重读NFS：额外12.2–108.3小时，入口不会自动切换。
- 已发生且可复用：冻结PET特征0.80 GPUh；预处理缓存127.8 GB（datas230）。3014本地SSD约余22 GB，不做本地整折缓存。
- 基于3090短试跑外推；A6000未测；论文138 GPUh未验证。

## 停止边界

阶段0–1完成。唯一剩余条件是作者明确批准四次正式训练及上述预算；批准后需将`formal_training_authorized`改为true（训练入口其余门槛已通过）。旧`spatial_qc.png`的标题/轴注释沿用修订前假设，仅作历史记录。

证据：`acceptance.json`、`qc_exclusions.json`、`qc_revision_receipt.json`、`laterality_fix_receipt.json`、`hemisphere_label_map.json`、`roi_validity.json`、`full_fold_cache_probe.json`、`measured_budget.json`、`pilot_receipts.json`。大文件：/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017。
