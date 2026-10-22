# E1 ROI 左右侧（laterality）失败 —— 根因定位

日期：2026-10-17　工作目录：`/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP`
脚本与输出：`reports/e1_laterality_rootcause_20261017/`（只在本目录写入，未改动任何既有文件，未做训练/GPU）。

## 结论（根因）

**根因是 `experiments/e1_clinical_conditioning/prepare.py` 中的仿射矩阵组合写错，而不是分割标签错、也不是原始 MRI 方向错。**

出错代码：

```python
world_affine = ref.affine @ np.asarray(proc["mri"].affine)
```

`proc["mri"].affine` 本身已经是 MONAI 预处理后「体素索引 → 真实 RAS 世界坐标」的 meta-affine（axcodes=LPI，x 行对角为 `-1`）。再左乘一次原始 MRI 的 `ref.affine`（同样是 MNI、x 行 `-1`），等于把几何变换叠加了两遍，导致合成的 `world_affine` 的 **x 行符号由 `-1` 翻转成 `+1`**（det 由 `-1` 变 `+1`，axcodes 变成 RPI）。于是左右判据 `x(17) < x(53)` 是在一个被镜像的 x 轴上评估的，对几乎所有被试都判为 fail。

解析验证：`raw(x行=-1) @ proc(x行=-1) → world(x行=+1)`，符号被翻转（`demo` 已复现）。

**置信度：极高。**

## 各假设裁决

- **H1 判据/仿射有 bug —— 成立。** 用正确的 `proc["mri"].affine` 直接映射（去掉多余的 `ref.affine`）后，抽样 42 人中海马 40、白质/壳核/丘脑/杏仁核 42/42 全部通过；而 `prepare.py` 的 buggy 仿射只有 2 个退化被试「通过」。
- **H2 预处理轴向导致标签镜像 —— 否定。** 原始 MRI（LAS，x 行 `-1`）与 MONAI 处理后 meta-affine（LPI，x 行 `-1`）**各自独立**都指向「axis0 增大 → 解剖学左侧」，两者一致；标签遵循该方向。
- **H3 分割本身左右颠倒/错标 —— 否定。** 全队列 1857 人统计：白质(2/41) 1857 全对、0 镜像；壳核(12/51) 1857 全对、0 镜像；海马(17/53) 1854 对、0 镜像、2 退化；杏仁核(18/54) 1853 对、0 镜像、3 退化。**全队列零镜像。**
- **H4 原始 MRI 仿射为放射学镜像 —— 否定。** 原始头 qform/sform code=4（MNI），axcodes=LAS，affine `-1,0,0,90`，是标准 RAS 世界坐标的配准图，负 x = 解剖学左侧，完全正常。

## 被试级一致性

- 处理 1857 人，读取 0 错误，**镜像被试 0 个**，未发现按站点/来源目录分出的子群，全队列方向一致。
- 「通过」buggy 判据的 2 人（`100_S_0743`、`128_S_4842`）正是**左海马仅 1 个体素**的退化样本，其「通过」是偶然/伪通过；`010_S_0786` 左海马 0 体素（标签缺失）。这解释了 receipt 里 `laterality_pass_subjects=2` 的现象 —— 实质 ≈0 人通过。

## 原始/mask 头信息

- 原始 MRI：axcodes=LAS，qform=sform=4，det<0，抽样 62 人完全一致。
- mask（`...fenge.nii.gz`）：identity 头、axcodes=RAS、160×192×160；分割器读的是 identity 头的 saved MRI，但由于 saved 数组与分割器的 L/R 帧一致，标签落位在解剖上是正确的。

## 推荐修复

1. **主修复：** 左右判据改用正确的「索引→世界」仿射，即把翻转后的 mask 质心用 `proc["mri"].affine` 映射，**去掉多余的 `ref.affine @`**（最小改动：`world_affine = np.asarray(proc["mri"].affine)`）。
2. **不要**交换标签 17↔53，**不要**翻转 mask 网格 —— 分割在解剖上是对的，这类「修复」反而会**引入**镜像错误。
3. 对退化 ROI（≤5 体素）显式处理，不要让其蒙混通过排序判据（3 名被试左海马近乎缺失）。
4. npz 缓存里存的是 buggy `world_affine`；若下游用该 affine 做 L/R 归属，会继承镜像错误。但**按标签 id 在数组网格上直接统计的 ROI 指标不受影响**，因为标签本身正确。

## 对 E1 评估的影响

- **只要 ROI MAE 是按标签 id 在数组网格上计算的，各 ROI/各半球的 MAE 数值不变**；当前坏掉的只是 laterality QC gate（被误判为 NO_GO）。修正仿射后，该 gate 对全部非退化被试（~1854/1857）变为 PASS，可解除 stage-0 阻塞。
- **若下游评估确实用了 npz 的 buggy `affine` 来分配左右半球**，则左右半球 ROI 会被对调、各半球 MAE 互换 —— 需审计消费 npz `affine` 的评估代码（本次未审计，列为后续项）。
- 已核查 ROI 对：17/53 海马、2/41 白质、4/43 侧脑室、10/49 丘脑、12/51 壳核、13/52 苍白球、18/54 杏仁核、1025/2025 楔前叶、1008/2008 顶下。

## 残余风险 / 未验证项

- 皮层标签 3/42 在 mask 中缺失（为 aseg 风格：仅皮层下 + 少量 DKT 皮层如 1025/2025）；ROI 面板只能用实际存在的标签。
- 3 名被试左海马退化/缺失（属分割质量问题，非 laterality），海马相关 ROI 应标记或排除。
- 全 1857 人的 MONAI 全流程仿射测试未逐一重跑（MONAI 跑了 52 人，mask-only 索引序检查覆盖全部 1857）；因符号论证有仿射锚定且全队列一致，风险低。
- 下游读取 npz `affine` 做 L/R 的评估代码未审计，建议后续核查。
