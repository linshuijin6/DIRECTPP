# R3-11 最终补充病例图：内部交付与验证记录

已完成 FDG、AV45 两张综合图；每张均为 3 行 × 4 列，含 MRI、真实 PET、合成 PET 和逐体素绝对误差。两张 PNG 均为 **4800 × 4160 像素、400 dpi**（PNG 元数据因单位换算记录为 399.9992 dpi），并提供 PDF。已实际打开两张 PNG、两张 PDF 的栅格预览和全部六张可选三正交图，综合图未见文字裁切、面板错位、比例失真或明显排版问题。

## 选例范围与冻结

仅使用 `original_author_reproduction_20261020` 的 DIReCT++ Full epoch 165、冻结两折 OOF 逐受试者 **whole-volume SSIM**。未使用 brain-mask SSIM 排序，也未重算 SSIM、PSNR 或任何 brain-mask 统计。冻结指标来源：[原始逐人 CSV](../../original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv)。

既有 [QC 排除原件](../../e1_stage01_20261017/qc_exclusions.json) 将 `016_S_4952` 标记为 MRI/mask 网格对应失败；[既有逐人纳入表](../../r3_11_brain_mask_metrics/run_20261102/eligibility_and_exclusions_internal.csv) 在两种 tracer 中均据此排除该病例。原有效 OOF 为 FDG 1,598、AV45 1,365；本次统一有效集合分别为 **1,597、1,364**。无有效 OOF 目标者不进入候选集合，未新增任何排除。

分别在各 tracer 的同一 QC 有效集合内按 SSIM 排序，median/P10 取距线性经验分位数最近的受试者，worst 取最小 SSIM；距离并列时按 PTID 升序。未按图像外观换例。完整候选排序保存在 [eligible_ranking_internal.csv](eligible_ranking_internal.csv)。选择清单在本任务首次读取病例影像前冻结，哈希为 `ba4828b291ea7dda0d6f0fc01afed5a541be8c8a1c86fca5b29353f0fa7a9667`；见 [selection_frozen.json](selection_frozen.json)。

| Tracer | Selection | PTID（仅内部） | Fold | 已保存 SSIM | 图中 SSIM | 既有 QC 依据 |
| --- | --- | --- | --- | --- | --- | --- |
| FDG | Median | 041_S_1418 | 2 | 0.933095395565033 | 0.9331 | included=True；既有 spatial gate pass=True |
| FDG | P10 | 033_S_1281 | 2 | 0.8746604919433594 | 0.8747 | included=True；既有 spatial gate pass=True |
| FDG | Worst QC-passed | 123_S_4096 | 1 | 0.567237377166748 | 0.5672 | included=True；既有 spatial gate pass=True |
| AV45 | Median | 036_S_6088 | 1 | 0.8923619985580444 | 0.8924 | included=True；既有 spatial gate pass=True |
| AV45 | P10 | 003_S_0907 | 2 | 0.8467223644256592 | 0.8467 | included=True；既有 spatial gate pass=True |
| AV45 | Worst QC-passed | 128_S_4842 | 1 | 0.5808225274085999 | 0.5808 | included=True；既有 spatial gate pass=True |

空间依据为 [既有逐人空间核验表](../../full_ot_medical_evidence/02_spatial_subject_checks.csv) 对应六行；本次只读取记录，不重建 mask 或做新的空间校正。QC-passed 表示通过这套既有规则，不代表新增临床质量认证。

## 与旧选例的核对及复用

| Tracer / Selection | 旧病例 | 最终病例 | 处理及原因 |
| --- | --- | --- | --- |
| FDG median | 041_S_1418 | 041_S_1418 | 统一集合下仍成立；复用原三正交 PNG |
| FDG P10 | 022_S_0543 | 033_S_1281 | 去除既定 QC 异常后，P10 目标变为 0.8742475509643555；最近病例改变 |
| FDG worst | 016_S_4952 | 123_S_4096 | 原病例既定 QC 失败；选有效集合最低 SSIM |
| AV45 median | 116_S_4625 | 036_S_6088 | 新 median 目标为 0.8923506140708923；两病例距离并列，PTID 升序选 036_S_6088 |
| AV45 P10 | 033_S_10027 | 003_S_0907 | 新 P10 目标为 0.8467225074768067；最近病例改变 |
| AV45 worst | 016_S_4952 | 128_S_4842 | 原病例既定 QC 失败；选有效集合最低 SSIM |

复用文件为 [原 FDG median 三正交图](../figures/G3_case_fdg_median.png)，在 [details/R3_11_FDG_median_orthogonal.png](details/R3_11_FDG_median_orthogonal.png) 以相对符号链接引用，未重复生成。其 Real 数组哈希与旧 render manifest 完全一致。该可选旧图保留原 200 dpi 和原共用色条注释，仅作为已有详细视图；正式投稿采用本目录的 400 dpi 综合图及独立色条。单独搬运 `details/` 时需保留相对链接的原图来源。

其余五个新病例在 `details/` 中生成 400 dpi 三正交 PNG/PDF，切面固定为 grid axis 0/1/2 的中央索引 80/96/80。所有旧 `G3_case_*.png`、旧选择清单和旧报告均保留原位且哈希不变。两张旧 QC 异常 worst 图未纳入此次正式综合图或最终六例详细图。

## 读取、显示与验证

复用 [cases.py](../code/cases.py) **第 25–35 行原始读取代码块**，在独立命名空间原样执行；没有导入会执行旧选例和覆写旧图的顶层脚本，也未改写原脚本。具体加载来源、代码块哈希、输入/数组/输出哈希见 [figure_manifest.json](figure_manifest.json)。

1. 逐例核对原 CSV、Full input index、原 split/cohort 中 PTID/tracer/fold/epoch 身份；缓存内部 `name` 与 `test_fold` 也一致。
2. NIfTI 字节 SHA-256 与冻结 CSV 一致；checkpoint SHA-256 与对应 fold 的实际 OOF `complete.json` 一致，并核验该回执指向的 `metrics.csv` 哈希。fold 1 checkpoint 身份为 `550ac2c4b1ef27b0dbb5624445dace2a04f58a84354e4900810509401cc4ea77`；fold 2 为 `f67e4a788eff3d958edd1d0da8cc739691affc59de84bdf3a1ae1f2821ce4315`。本任务没有重新读取/运行模型权重。
3. 真实 PET 来自对应 Full 持久缓存的 tracer 键；缓存文件哈希和真实 PET 数组哈希均匹配既有 `subject_asset_checks.jsonl`，未混入 E1 的另一套 PET 数组。所有 MRI/Real/Syn 均 finite，shape 均为 160×192×160。
4. SSIM 直接复用原 CSV，并核对图上四位小数。独立复核整个有效集合的最近分位数与最低值选择，没有重算影像评价指标。
5. 误差为原流程中的 `np.abs(pred-real)`；另以 `np.maximum(pred-real, real-pred)` 对整数组逐元素验证完全相等。实际绑定到每个面板的数据与对应切片逐元素相等，色标上下限核验为 0/1。误差最大值均小于 1，所有被显示数组均在 [0,1]，故无需截断、无截断体素。
6. 综合图全部使用 grid axis 2、index 80，保留原流程 `np.rot90` 的显示旋转、nearest 插值和等比例显示；没有对保存数组做翻转、重采样、配准、重新归一化或 affine 修改。不同病例固定同一数组索引，不声称逐病例解剖位置完全一致；不从 identity affine 推断左右，不新增 L/R 标记。
7. MRI 为 gray、PET 为 magma、误差为 inferno，各自有明确色条；PET 和误差均固定 0–1，跨行及两 tracer 可比。误差图显示整个网格，不掩掉脑外误差。值为 normalized uptake / arbitrary units，未声明 SUV/SUVR。
8. 自动检查新图全部文本边界位于画布内，公开图中没有 PTID/内部路径。实际打开两张综合 PNG、两张综合 PDF 栅格预览及六张详细 PNG，确认行/列标题、SSIM、色条、图像比例与面板对应正确，未见明显裁切/重叠。没有模拟色盲视图；PET/误差采用顺序亮度色图并分别标注。

## 文件与使用范围

- FDG：[PNG](R3_11_FDG_cases.png)、[PDF](R3_11_FDG_cases.pdf)。
- AV45：[PNG](R3_11_AV45_cases.png)、[PDF](R3_11_AV45_cases.pdf)。
- [英文图注](CAPTIONS.md)、[内部六例清单](selection_manifest_internal.csv)、[冻结收据](selection_frozen.json)、[图件及逐数组验证清单](figure_manifest.json)、[最终交付检查](verification.json)。
- [绘图/选例脚本](build_figures.py) 与 [运行日志](render_attempt01.log) 留存于本目录。使用项目既定 xiaochou 解释器及现有 NumPy/Pandas/Torch/Nibabel/Matplotlib/Pillow，未引入绘图框架。

本次仅新增本目录文件，没有训练、推理、评价指标重算；未修改原 NIfTI、mask、缓存、统计 CSV、正式 Figure 2/3、LaTeX、BibTeX 或 Notion，未提交或推送 Git。

## 待作者确认

没有阻塞本次选例或绘图的未解决问题。作者整合补充材料时仅需确定两张 Supplementary Figure 的最终编号并定稿英文图注。原 Figure 2/3 的诊断分组内随机选例依据采用本轮作者说明，本任务未重新追查其历史绘图文件身份；本次结果明确属于 original-author reproduction 的冻结 OOF，不据此证明原论文历史运行身份。
