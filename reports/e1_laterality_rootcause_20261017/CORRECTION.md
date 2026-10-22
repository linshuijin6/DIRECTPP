# 更正：E1 ROI 侧别根因（主代理复核，2026-10-17）

本文件更正同目录 `FINDINGS.md` 的根因结论；`FINDINGS.md` 原样保留作记录。

## FINDINGS.md 的错误

`FINDINGS.md` 认为 `prepare.py` 中 `world_affine = ref.affine @ proc["mri"].affine` 把几何变换叠加了两次。这个判断不成立。`prepare.py` 和子代理脚本 `affine_fix_test.py` 都用 `Lambdad(nib.load(p).get_fdata())` 读取影像，得到的是不带 header 的裸数组。因此 MONAI 的 `proc.affine` 映射的是"处理后索引 → 原始体素索引"，不是世界坐标 mm。`ref.affine @ proc.affine` 才是正确的"索引 → 世界"映射。子代理改用 `proc.affine` 后算出的白质质心 x 约为 61 和 110，并不以 MNI 中线 0 为中心，也说明它不是世界坐标。

## 复核证据（只用 MRI、mask 和模板，不用 PET）

- `verify_cache_affine.py` / `verify_cache_affine.json`：按缓存 affine 在原始配准 MRI 上重采样，与处理后 MRI 的相关系数在 10 例中为 0.988–0.999；按 x 镜像映射时只有 0.58–0.75。结论：缓存 affine 正确。
- `verify_world_frame.py` / `verify_world_frame.json`：在正确的世界坐标下，1856 名有效被试中，标为 Left 的白质、壳核、侧脑室、丘脑全部位于 x>0，即物理右侧；标为 Right 的全部位于 x<0。
- 同一脚本的模板检查：20/20 例原始配准 MRI 与 MNI152 模板的未翻转相关均高于 x 翻转相关，说明原始配准没有镜像。

## 结论

分割的左右命名对全部被试统一互换，没有个别例外。mask 网格和标签值本身可以继续使用。具体机制推测是：MRI 以 identity header 保存后再分割，分割器按 identity header 理解左右。这一机制未通过复现分割步骤直接验证。

## 处理

不交换标签、不翻转网格、不改缓存。冻结 `reports/e1_stage01_20261017/hemisphere_label_map.json`，单侧结果按物理半球名称报告。详见 `../e1_stage01_20261017/laterality_fix_receipt.json` 和 `ACCEPTANCE_REPORT.md`。

此前曾按 FINDINGS.md 的建议生成过一组修正文件，现移至 `../e1_stage01_20261017/superseded_wrong_affine_fix/`。它们未被任何入口使用。
