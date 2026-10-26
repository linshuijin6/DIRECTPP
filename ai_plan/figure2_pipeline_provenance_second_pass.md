# DIRECTPP Figure 2 第二轮深度溯源：统一评价程序与指标来源

> 日期：2026-10-26  
> 范围：原作者 3002、3003 节点与本地原始证据；只读取证。  
> 本报告不覆盖第一轮报告。未执行历史 notebook，未启动训练、推理或评价，未重算 Figure 2。

## 1. Executive Findings

### 结论先行

**当前无法判定 Figure 2 的全部指标采用了何种统一或分散的评价流程。** 在本轮实际覆盖范围内，没有找到把七种方法统一遍历、加载预测与真实 PET、计算四指标并写入结果表的程序，也没有找到各方法共同调用的自定义评价函数。找到的是若干彼此独立的候选评价入口，以及复用 MONAI/Generative 指标库的代码；这些候选没有被闭环到 Excel 的 84 项数值。

| 核心问题 | 本轮裁决 | 证据边界 |
|---|---|---|
| 统一多方法评价脚本 | **NOT FOUND / UNRESOLVED** | 74 本当前 notebook、10 个非依赖 Python 文件及两份 IPython 历史中未命中；不等于历史上从未存在 |
| 若存在，处理 NIfTI 还是逐模型推理 | **UNRESOLVED** | 未找到统一入口；已恢复的候选两类都有，但均是单模型/单目录 |
| 共享自定义评价函数 | **NOT FOUND / UNRESOLVED** | 未发现公共 `def evaluate...` 及反向调用；多个候选复用相同第三方指标类，但参数并不完全一致 |
| 方法独立评价的直接证据 | **VERIFIED（仅候选运行）** | single-flow 329 人四指标、Swin/DDIM 单被试双指标、DIReCT++ 不同 loader 输出，以及新增的预生成 NIfTI 双指标历史输入 |
| 混合来源 | **POSSIBLE，未证实为 Figure 2 来源** | 候选运行的 loader、样本数、SSIM kernel 与输出形式不同；但没有这些候选进入 Excel 的操作证据 |
| 能否证明全部指标是单样本 | **不能；该全称判断 UNRESOLVED** | 存在单样本候选，也存在 329/1856 人候选；均不能代表 Figure 2 全部数值 |
| 是否找到此前未明确登记的核心评价代码 | **是，但不是四指标统一 evaluator** | 3003 Session 178 Lines 32–35：预生成 NIfTI、单目录、SSIM/PSNR、最多 1129 个交集键；无 stdout/保存结果 |
| 所有方法共享测试对象、预处理与指标实现 | **无法证明** | 已恢复候选反而显示 `train_loader`/`val_loader`、kernel 7/11 等差异；Figure 2 实际协议仍未知 |

### 四种竞争解释

- **H1 统一多方法评价脚本：UNRESOLVED。** 本轮没有支持证据；覆盖范围内的多方法数组均是绘图输入，不是评价循环。
- **H2 共享评价函数、分方法运行：UNRESOLVED。** 第三方 `SSIMMetric`/`PSNRMetric` 等的重复调用是共享库，不等于作者自定义公共 evaluator；未找到跨方法调用的公共函数。
- **H3 各方法独立计算后人工汇总：部分前提 SUPPORTED，汇总方式 UNRESOLVED。** 独立计算有直接证据，但“人工汇总”没有文件生成或录入操作证据。
- **H4 混合来源：POSSIBLE。** 不同候选流程确实存在，但没有足够证据把 Figure 2 的某行或某指标分别绑定到这些流程。

证据标签：**VERIFIED**=直接原件确认；**SUPPORTED**=强关联但未闭环；**POSSIBLE**=合理但未证明；**UNRESOLVED**=现有材料无法判定；**CONTRADICTED**=被直接证据否定。`NOT FOUND` 仅描述本轮覆盖范围。

## 2. New Evidence

以下优先列本轮新增或直接复核后改变结论边界的证据。第一轮已经记录的 notebook 候选数值只在后文用于对照，不冒充新发现。

### N1. 对统一入口、公共函数与结果导出进行了新的结构性检索

- **节点与根**：3002 `/home/ssddata/liutuo`；3003 `/home/data/liutuo/code`。
- **节点身份**：分别通过 `192.168.1.4`、`192.168.1.5` 连接；两者 `hostname=pnxc`、`whoami=linshuijin`，初始 `pwd` 分别为 `/home/ssddata/linshuijin`、`/home/data/linshuijin`。
- **覆盖**：3002 当前 30 本 notebook、1 个非依赖 Python 文件、1,474 条 IPython 输入；3003 当前 44 本 notebook、9 个非依赖 Python 文件、4,736 条 IPython 输入。检索排除了第三方 `monai`、`generative`、`BiomedCLIP` 实现本体及无关个人目录。
- **结构性条件**：除方法名外，还检查 `for ...method... in`、`method_dirs`、`method_names`、`results_dir`、`compare_methods`、同一指标 cell 多次 `torch.load`、NIfTI 读取与指标共现、`def *eval/*metric`、`to_excel`/`ExcelWriter`/`to_csv`。
- **结果**：上述 notebook 和 IPython 输入中，多 checkpoint/方法目录结构命中均为 0；保存 notebook 中 NIfTI+四指标 API 命中为 0，自定义评价函数命中为 0。3002 `to_excel` 与 `ExcelWriter` 均为 0。
- **支持**：在当前覆盖范围内，没有统一多方法 evaluator、逐行加载多个 checkpoint 的评价 cell、公共自定义评价函数或指标表生成脚本。
- **不支持**：不能据此声称所有历史介质、已删除文件、合作者环境或未检查节点不存在这些程序。

### N2. 新增：3003 存在预生成 NIfTI 的单目录双指标评价历史

- **原件**：3003 `/home/data/liutuo/.ipython/profile_default/history.sqlite`。
- **数据库 SHA-256**：`ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0`；`output_history=0`。
- **位置**：Session 178 Lines 32–35；session 存储时间为 2024-11-12 至 2024-11-15。
- **source_raw SHA-256**：L32 `be12947411fd4ec7ee3f32c7e496196f6cd103705663a91df7b9e62da0165d52`；L33 `19941fe1e3760687c89cf8b515b3b528604777c158fdbea5d9e2e2d0ecf95b58`；L34 `fd30282f40c4947c914a498da6fa7e50ea3be6624766ec794c1fbb8b4899e27f`；L35 `1c41152fabff04bf90bdb0fbefb2500209521f591a41737d5dc1cb44573d7f29`。

```python
path_real = "/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/PET_niigz"
path_generated = "/home/data/liutuo/code/liutuo_data/ADNI1+2_baseline/generated_PET"
real_files_dict = {f[:10]: f for f in files_real}
generated_files_dict = {f[:10]: f for f in files_generated}
common_keys = list(set(real_files_dict.keys()) & set(generated_files_dict.keys()))[:1129]
ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
psnr_metric = PSNRMetric(1.0)
# 逐键 nib.load(...).get_fdata()，仅保存内存列表并打印两个均值
```

- Lines 32/33/34/35 的上限依次为 10/10/50/1129；L33 修正了 batch/channel 维度。`set` 转 `list` 没有排序，故代码本身不保证固定子集顺序。
- **同 session 上游**：Lines 27–31 引用 `...clip-_flow/...second_part_159.pth`、单步 RF，并曾写 `flow generated pet`；这与 `generated_PET` 不是同一路径。当前 159.pth 存在，但 `generated_PET` 与 `flow generated pet` 均不存在。真实目录 `PET_niigz` 当前有 1,129 个文件。
- **支持**：作者曾输入过“对已生成 NIfTI 做独立 SSIM/PSNR 汇总”的程序；它是预生成文件评价，不是逐模型统一推理。
- **不支持**：没有 MSE/MAE、逐人 CSV、stdout 或 Excel 输出；当前预测目录缺失，不能认证实际完成人数、模型身份、四指标均值或 Figure 2 关联。

### N3. Session 342 Line 33 的数据上下文是一名验证对象，不是已恢复的大样本测试

- **原件/SHA**：同 N2 的 3003 历史数据库。
- **位置**：Session 342 Lines 3、5、33；session 存储开始/结束时间为 `2025-02-22 13:24:31.802978` / `2025-02-24 00:38:07.581244`。
- **Line 33 source_raw SHA-256**：`48498c5a62c6b72d3d3862b9b949350811b3f2feda7be766bac9de7ddb9db494`。

```python
# Session 342 Line 3
train_data, val_data = train_test_split(paired_data, test_size=1, random_state=42)
# Line 5
val_loader = DataLoader(val_ds, batch_size=1, shuffle=False, num_workers=0)
# Line 33
checkpoint_path = ".../mri2pet _two trace_add clip_flow/first_part_310.pth"
for step, data_val in enumerate(val_loader):
    ...  # 双 tracer 四指标累加
avg_psnr_fdg = psnr_fdg_total / num_batches
```

- **支持**：Line 33 是具有四指标平均语法的单模型、双示踪剂候选代码；当其在本 session 的 `val_loader` 上运行时，分母对应的验证名单大小为 1。
- **不支持**：数据库无 stdout，不能声称已找回计算结果；存在均值语法不等于 Figure 2 使用了该均值，更不等于多受试者独立测试均值。
- **当前资产状态**：该 session 引用的 train/val JSON 与 `/home/data/liutuo/code/checkpoint/mri2pet _two trace_add clip_flow/first_part_310.pth` 当前均不存在；没有以其他目录的相似 epoch 替代。


### N4. Excel 上游没有生成代码；当前文件时间还纠正了第一轮时间记录

- **3002 历史原件**：`/home/ssddata/liutuo/.ipython/profile_default/history.sqlite`，SHA-256 `85be4f4fa1affc1d26d1c398fbe56f7796e650853740408cb3ef58aeef3b32e6`；1,474 条输入，`output_history=0`。
- **Excel**：`/home/ssddata/liutuo/liutuo_data/新建 XLS 工作表.xls`，23,040 bytes，SHA-256 `92643950a8408dac3465bf97d65850ac7d1e25c85dfe84256f598dcde8a005df`。
- **直接检索结果**：历史中没有 `to_excel`、`ExcelWriter` 或该 Excel 的写入代码。Session 140 Lines 1–3、5、6 只有 `pd.ExcelFile`/`pd.read_excel`，Lines 4–6 转 Markdown/LaTeX；一个早期 `xlwt` 输入是无关网页爬虫，不是本任务结果表。
- **直接 stat**：当前 Excel `mtime=2025-06-17 16:29:13.715346031 +0800`；不是第一轮所述 `16:24:31`。后者实际是 Session 140 的存储开始时间 `2025-06-17 16:24:31.915090`。
- **绘图时间**：Session 129 Lines 35/36/37 的 session 存储开始时间为 `2025-05-29 22:17:29.457919`，已经包含三组硬编码数组；绘图 notebook 当前 mtime 为 `2025-06-01 01:11:45.468754946 +0800`。
- **限制**：IPython `history` 表没有逐 line 时间，Session 140 无 end 时间；不能精确排列某次读取与 16:29:13 的先后，也不能由 mtime 推断手工复制方向。
- **支持**：当前 Excel 内容、绘图数组和读取/LaTeX 输入分别存在；没有找到指标写入 Excel 或 Excel 生成雷达数组的直接操作。
- **不支持**：不能把 `Excel → Figure` 或 `Figure数组 → Excel` 的复制方向画成 VERIFIED。

### N5. 中间结果与历史日志的扩展检查仍未形成指标表链

- 对 3002 `liutuo_data` 及选定代码根共 **17,819 个文件**、3003 对应范围 **33,059 个文件**检查文件名；对 CSV 仅读取开头 8,192 bytes 检查指标列名。
- 没有发现文件名指向 Figure 2 的 `metrics/results/evaluation/summary/psnr/ssim` 结果表；没有 CSV 头部同时承载这些指标字段；两个数据根均未发现 `.npy`/`.npz` 指标中间数组。
- 3002 唯一相关 spreadsheet 是上述原始 `.xls`；3003 该范围没有 spreadsheet。依赖库内部名称中的 `metric` 文件不计为实验结果。
- 另外读取 3002 的 3 个、3003 的 2 个 `.txt/.log/.out` 文本文件，未发现 `Average PSNR/SSIM` 或四指标汇总日志。
- **边界**：这是当前文件系统与限定根目录的阴性结果，不是对被删除、外部介质或合作者文件的否定。

### N6. 84 项原始值重新核实；三个“匹配”都只能保留为候选关联

本地原始副本 `reports/baseline_metrics_provenance_20261020/original_assets/performance_table.xls` 的 SHA-256 与原节点一致；`performance_table_extracted.json` 和绘图 notebook 零起算 cells 9–11 再次确认 **84/84 一致**。FDG DIReCT++ 的正确四项是 **89.94 / 28.72 / 0.33 / 2.96**，不是 `0.28/2.39`。

| 候选输出 | 原始位置 | 论文值 | 可验证数值关系 | 不能推出的结论 |
|---|---|---:|---|---|
| DIReCT++ FDG PSNR `28.71800994873047` | 3002 `mri2pet _two trace_new-final.ipynb` cell 10 | 28.72 | 正常四舍五入为 28.72；差值 `-0.0019900513` | 同 cell SSIM=`0.905945...`≠论文 `0.8994`，无同源 MSE/MAE；不能证明复制 |
| Swin FDG PSNR `19.827280044555664` | 3002 `mri2pet swinunet useful.ipynb` cell 14 | 19.82 | 截断为 19.82；正常四舍五入应为 19.83；差值 `0.0072800446` | 同 cell SSIM=`0.739291...`≠论文 `0.7529`，无 MSE/MAE；不能证明直接录入 |
| DDIM 候选 PSNR `21.34878921508789` | 3003 DDIM notebook cell 13 | AV45 21.33 | 差值 `0.0187892151`；四舍五入为 21.35，截断为 21.34 | 不是浮点级或简单舍入一致；SSIM=`0.660645...`≠论文 `0.7337`，无 MSE/MAE |

三项均至多是 **PSNR 部分关联**。S1（单样本来源）与 S3（偶然相近）均未被直接录入证据排除；S2（多受试者汇总）在其他候选上存在，但未闭环到论文；S4（不同指标来自不同运行）与 S5（未恢复运行/合作者资料）同样保持开放。


## 3. Pipeline Reconstruction

### 3.1 目前唯一闭环的是“表格数值—绘图数组”，不是“评价—表格”

```text
[独立候选A：模型checkpoint → loader内推理 → notebook指标输出]
[独立候选B：预生成NIfTI目录 → Session178双指标代码]
                         │
                         └── UNVERIFIED：没有结果表/复制操作把候选绑定到84项
                                      │
                                      v
                     [中间metrics/CSV/NPY：NOT FOUND]
                                      │
                                      UNVERIFIED
                                      │
                                      v
              [新建 XLS 工作表.xls：84项内容 VERIFIED]
                                      │
                         UNVERIFIED（方向与版本均未知）
                                      │
                                      v
       [雷达notebook cells9–11 / Session129硬编码数组：84项 VERIFIED]
                                      │
                                      │ 绘图调用 VERIFIED
                                      v
                              [Figure 2雷达图]
```

- `S178 generated_PET → 双指标 evaluator` 只是代码引用关系；预测目录当前缺失且无 stdout，不是完成运行的收据。
- `Session342 val_loader(1人) → Line33` 是数据构建与代码上下文关系；执行输出未恢复。
- `Excel → LaTeX` 有 Session 140 读取/转换输入，但缺少逐行时间及 stdout，不能认证当前文件版本就是当时读取版本。

### 3.2 时间线（均为存储字段，不自动构成因果箭头）

| 时间（+0800，数据库时间按原存储值） | 事件 | 可证/不可证 |
|---|---|---|
| 2024-11-12 至 2024-11-15 | 3003 Session 178，含 NIfTI 双指标输入 | 代码输入可证；运行结果不可证 |
| 2024-11-23 | single-flow cell16 对应 Session 222 输入 | 329人 notebook 输出可证；进入论文不可证 |
| 2025-02-22 至 2025-02-24 | Session 342，val_size=1 与 Line33 | 代码上下文可证；stdout不可证 |
| 2025-05-29 22:17:29 | Session 129，三组硬编码雷达数组 | 数组存在可证；来源不可证 |
| 2025-06-01 01:11:45 | 当前雷达 notebook mtime | 文件保存时间；不是评价时间 |
| 2025-06-17 16:24:31 | Session 140 start | 读取/转换会话开始；逐line时间未知 |
| 2025-06-17 16:29:13 | 当前 Excel mtime | 当前版本修改时间；不是创建/复制方向证明 |

## 4. Method Provenance Matrix

完整字段、checkpoint、名单、输出与缺口见 `ai_plan/figure2_method_metric_provenance_matrix.csv`。下表覆盖全部 21 组；“候选”均不表示已认证为 Figure 2 evaluator。

| Cohort | Method | Paper metrics (SSIM/PSNR/MSE/MAE) | Evaluator type | Metric agreement | Evidence level |
|---|---|---|---|---|---|
| ADNI-FDG | CycleGAN | 67.82/17.26/2.35/6.47 | UNKNOWN | UNKNOWN | 仅绘图 |
| ADNI-FDG | Swin-UNet | 75.29/19.82/1.27/5.76 | 独立单样本候选 | 部分：PSNR仅截断匹配 | 候选+仅绘图 |
| ADNI-FDG | 3D DDIM | 82.62/23.09/0.98/3.98 | 独立单样本候选，FDG未认证 | 候选不匹配 | 候选+仅绘图 |
| ADNI-FDG | SegGuidedDif | 84.85/23.76/0.57/3.73 | UNKNOWN | UNKNOWN | 仅绘图 |
| ADNI-FDG | Rectified Flow | 85.69/24.96/0.53/3.52 | UNKNOWN（plain RF） | UNKNOWN | 仅绘图 |
| ADNI-FDG | DIReCT (single) | 87.48/26.51/0.43/3.08 | 独立329人候选 | 候选均值不匹配 | 候选+仅绘图 |
| ADNI-FDG | DIReCT++ | 89.94/28.72/0.33/2.96 | 多个独立候选 | 部分：PSNR正常舍入匹配 | 候选+仅绘图 |
| ADNI-AV45 | CycleGAN | 59.56/15.43/3.24/8.39 | UNKNOWN | UNKNOWN | 仅绘图 |
| ADNI-AV45 | Swin-UNet | 69.16/17.54/2.67/7.95 | 未绑定独立候选 | UNKNOWN | 仅绘图 |
| ADNI-AV45 | 3D DDIM | 73.37/21.33/1.73/7.01 | 独立单样本候选 | 仅PSNR相近，非一致 | 候选+仅绘图 |
| ADNI-AV45 | SegGuidedDif | 80.29/21.99/1.12/6.92 | UNKNOWN | UNKNOWN | 仅绘图 |
| ADNI-AV45 | Rectified Flow | 85.43/24.74/0.69/4.31 | UNKNOWN（plain RF） | UNKNOWN | 仅绘图 |
| ADNI-AV45 | DIReCT (single) | 87.37/27.11/0.51/3.16 | 独立329人候选 | 候选均值不匹配 | 候选+仅绘图 |
| ADNI-AV45 | DIReCT++ | 88.21/28.09/0.39/2.73 | 多个独立候选 | 已恢复候选不匹配 | 候选+仅绘图 |
| OASIS-AV45 | CycleGAN | 40.27/12.38/4.86/10.78 | UNKNOWN | UNKNOWN | 仅绘图 |
| OASIS-AV45 | Swin-UNet | 51.34/14.96/3.96/10.16 | UNKNOWN | UNKNOWN | 仅绘图 |
| OASIS-AV45 | 3D DDIM | 68.59/17.05/3.48/8.24 | UNKNOWN | UNKNOWN | 仅绘图 |
| OASIS-AV45 | SegGuidedDif | 71.85/19.63/2.51/7.59 | UNKNOWN | UNKNOWN | 仅绘图 |
| OASIS-AV45 | Rectified Flow | 80.44/21.33/1.87/4.29 | UNKNOWN（plain RF） | UNKNOWN | 仅绘图 |
| OASIS-AV45 | DIReCT (single) | 82.66/25.48/1.12/3.55 | UNKNOWN | UNKNOWN | 仅绘图 |
| OASIS-AV45 | DIReCT++ | 83.97/26.79/0.94/3.01 | UNKNOWN | UNKNOWN | 仅绘图 |


## 5. Prior Report Corrections

### 已得到支持的判断

1. 原 Excel 与雷达 notebook 的 84 个展示值一致；绘图 cells 9–11 没有在 cell 内从逐人结果求均值。
2. `test/ddim`、`test/seg_guided_diff` 等目录名不能认证模型身份；历史输入确实存在 RF 权重写入这些目录的情况。
3. Swin 候选实现是 MONAI `SwinUNETR`；DDIM 候选有 10 步/40.pth 与 20 步/200.pth 两个不能混拼的分支。
4. single-flow cell16 的 329 人四指标输出及 DIReCT++ 165 的 1856 人 train_loader 输出，都不是 Figure 2 的完整闭环。
5. 仍未找到从统一完整测试名单、预测/GT 到 84 项表格的端到端日志。

### 应当收窄或更正的判断

1. **撤回“证据确凿证明全部关键指标来自单样本/极少样本并手工填入表格”的确定性。** 单样本候选存在，但缺直接录入证据；多受试者候选也存在，且全部指标来源仍未知。
2. **数值相近不等于复制。** 28.718→28.72 是正常舍入匹配；19.827→19.82 需截断；21.348789→21.33 既不是正常舍入也不是截断匹配。
3. **SSIM/MSE/MAE 不支持同一整套四指标来源。** 三个候选输出仅有 SSIM/PSNR，且 SSIM 均不等于对应论文值，应称“PSNR 部分关联”。
4. **1856 人 train_loader 均值不能否定未恢复的独立测试均值。** 它只能证明该次输出不是论文均值，不能证明论文没有其他运行。
5. **Session 342 不应被描述为已执行的多受试者 Figure 2 平均程序。** 当次 `val_data` 的构建是 `test_size=1`，且无 stdout；当前 JSON/310 权重路径缺失。
6. **共享第三方指标类不等于统一指标协议。** Swin/DDIM 候选 kernel=11，RF/DIReCT++ 候选 kernel=7；loader 和聚合对象也不同。
7. **Excel 时间需更正。** 当前 mtime 是 `2025-06-17 16:29:13.715346031 +0800`，不是 `16:24:31`。时间戳及 session start 均不能证明复制顺序。
8. **FDG DIReCT++ MSE/MAE 为 0.33/2.96。** Gemini 文中 `0.28/2.39` 与原始 Excel 和绘图数组均不符。
9. 第一轮把候选运行统称为“B级强关联”容易过度解读；本报告将其降为 **候选**，除非另有直接文件/输出链。

## 6. Unresolved Questions

1. 哪个程序或人工过程把各方法四指标写入 `/home/ssddata/liutuo/liutuo_data/新建 XLS 工作表.xls`？是否存在旧版 Excel、外部表格或合作者文件？
2. 七种方法各自的最终 checkpoint、预测 NIfTI、真实 PET、完整测试名单与逐人四指标在哪里？尤其缺 CycleGAN、真实 SegGuidedDif、无 VLM guidance 的 plain RF。
3. 3003 Session 178 的 `generated_PET` 与 `flow generated pet` 当前均缺失；其实际生成者、运行输出和与 Figure 2 的关系未恢复。
4. 3003 Session 342 的 train/val JSON 和原路径 `first_part_310.pth` 当前缺失；Line 33 没有输出，不能恢复数值。
5. Swin cell14 的 `/home/data/liutuo/code/checkpoint/swinunter/swinunter_1.pth` 当前缺失；3002 的 FDG/AV45 权重组尚未与该输出或论文选择绑定。
6. single-flow 141.pth 当前缺失；DIReCT++ cell10 的 154.pth 当前缺失。现存其他 epoch 不得自行替代。
7. OASIS 仅有少量输入/GT 实物线索，完整 OASIS 队列、七方法预测与指标输出均未恢复。
8. 当前没有证明各方法共享测试对象、预处理、有效 tracer 筛选、SSIM 参数、MSE/MAE 百分比换算和聚合方式的原始协议。
9. 本轮未连接 live 3014；仅复核了本地已有的 3014 归档索引。其他服务器、外部存储和合作者资料属于未检查范围。

### 本轮停止点与覆盖限制

已完成定向统一入口检索、Excel 上游检索、中间结果/日志检查、方法候选核对和 IPython 历史关联。未进行全服务器无差别递归搜索，未读取无关个人文件。搜索未命中只适用于上述路径与当前文件状态。

## 7. Baseline Reproduction Feasibility

以下仅评价资产可恢复性，不启动任何实验，也不表示科学结果已经验证。

| 方法 | 直接统一评价现有预测 | 使用历史模型在独立测试集重新推理 | 核心资产与主要阻塞 |
|---|---|---|---|
| CycleGAN | **不可：缺完整且身份可靠的预测/GT** | **不可直接执行** | 未找到经代码认证的训练/推理实现和 checkpoint；可能必须恢复实现后重训 |
| Swin-UNet | **不可直接统一：仅少量示例且协议不全** | **有限资产，不能复现论文行** | MONAI SwinUNETR 源码存在；3002 FDG 13个/AV45 9个权重存在，但 cell14 原权重路径及论文选择未知；SSIM kernel 候选为11 |
| 3D DDIM | **不可直接统一：缺完整预测与测试绑定** | **有代码和权重，但论文运行不可直接复现** | 40/200.pth 当前存在，10/20步分支存在；最终分支、测试名单与四指标输出缺失 |
| SegGuidedDif | **不可** | **不可直接执行** | 未找到可认证的核心实现和权重；RF写入同名目录的历史不能替代，可能必须重训/恢复外部实现 |
| Rectified Flow（plain） | **不可** | **不可直接执行** | 无条件/plain 基线身份未恢复；临床条件 single-flow 或双示踪剂模型不能替代 |
| DIReCT (single) | **不可直接统一：329人候选不是论文表** | **历史141运行不可直接复现** | 训练/推理及329人输出存在，但141.pth缺失；159.pth不是同一运行，论文独立测试身份未知 |
| DIReCT++ | **不可直接统一：现有预测目录与名单不闭环** | **有部分资产，但论文行不可直接复现** | 165/140/120 等权重存在，154与3003原310路径缺失；165输出是train_loader且仅双指标，缺最终独立测试协议 |

**总体可行性**：当前资产足以研究若干候选实现和指标定义，但不足以在不补证、不更换权重/队列的情况下统一重建 Figure 2 的 84 项原始结果。若未来开展复现，应先恢复或重新冻结各方法身份、独立测试名单、预处理与指标协议，并生成新的逐人结果；那将是新实验，不属于本轮工作。

---

交付物：

- `ai_plan/figure2_pipeline_provenance_second_pass.md`
- `ai_plan/figure2_method_metric_provenance_matrix.csv`（21 个方法—数据集组合，15 个字段）

