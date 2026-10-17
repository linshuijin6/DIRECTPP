# 本轮分析定义与重跑命令

所有路径相对本 revision 目录，除非给出绝对路径。原始 checkpoint、图 5、论文及数据均只读。未提交、切分支、训练或运行 GPU。原审计只用于导航；不把报告的 VERIFIED 标签当作输入正确性的保证。

## 执行命令

从 `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP` 执行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python 8_revision_evidence/revision_20261016/scoped_audit.py > 8_revision_evidence/revision_20261016/scoped_audit.log
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python 8_revision_evidence/revision_20261016/analyze_evidence.py > 8_revision_evidence/revision_20261016/analyze_evidence.log 2>&1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' python 8_revision_evidence/revision_20261016/verify_assets.py > 8_revision_evidence/revision_20261016/verify_assets_aligned.log 2>&1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' python 8_revision_evidence/revision_20261016/reextract_syn_regions.py > 8_revision_evidence/revision_20261016/reextract_syn_regions.log 2>&1
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python 8_revision_evidence/revision_20261016/incorporate_recovered_split.py > 8_revision_evidence/revision_20261016/incorporate_recovered_split.log
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 CUDA_VISIBLE_DEVICES='' python 8_revision_evidence/revision_20261016/finalize_evidence.py > 8_revision_evidence/revision_20261016/finalize_evidence.log 2>&1
```

`verify_assets.py` 原始运行日志 `verify_assets.log` 记录了未校正空间方向时的差异；最终运行在同表中保留原始 replay 值及 aligned replay 值。`mri_orientation_probe.json` 记录了唯一病例的八种反转检查，随后对六病例用保存 MRI 验证共同方向关系；不是对 PET 拟合可提高 ICC 的空间变换。

工作区初始 commit 为 `c2d5789` 的完整 hash 以执行收据为准，原文件 SHA-256 在 `source_sha256.csv` / `additional_source_sha256.csv`；最终逐一重算历史源哈希。每个实际读取的 Syn volume 和 mask 在 `image_derived/source_volume_sha256.csv` 留下路径和 SHA-256。

用户在本轮期间恢复了最终165对应的1856/1名单；`incorporate_recovered_split.py` 独立核对其唯一ID、交集、并集、重建身份及全部1857条Description，写入 `final165_split_receipt.json`。名单外训练受试者为1名CN，训练和验证均未用者为0。早先 `final_split_reconstruction.json` 和根部初步 `subject_membership_and_assets.csv` 是恢复前状态，只以 enriched CSV 和新 receipt 为最终队列事实。不把新文件的恢复时间假装成历史 checkpoint 保存时的 hash 记录。

## 证据等级

- `image_derived/`：Syn 部分从全部保存体数据重提；Real 部分使用原区域 CSV，六病例/588 区域与上游原 Real 影像的预处理 replay 一致。**未全量重跑 Real 预处理**，不得把有界核验写成全量独立再现。
- 本目录根部 `regional_agreement_*`、`regional_AD_CN_*` 和 `regional_summary.json`：原 CSV 直接统计，仅为发现 Syn 列版本不符保留的诊断产物，不能用于论文。根部旧调整分析同样不是最终结果。
- 旧 `8_revision_evidence/compute_regional_statistics.py`、`regional_statistical_metrics_*` 的自行设置 5%/10% TOST 结果不采用，历史文件原样保留。
- 所有区域结果均为固定模型的回顾性描述，暴露集合未完全绑定，不能当成独立测试的推断或临床替代证明。

## 统计单位与缺失

单位为 subject，每个 tracer/ROI 每个 subject 一对 Real/Syn。先按 SID 唯一性、同 tracer 各区域的 subject 集、metadata 标签一致性检查；不以相同人数代替身份核查。保持 98 区，不挑选不显著区域。有限配对有效观测数逐行报告；不存在掩膜区域保留 NaN，不填零。EMCI、LMCI、MCI 三标签在分层表中独立报告，避免暗中合并。

差值为 Syn−Real，误差单位为 arbitrary normalized uptake。MAE、RMSE、均值偏差、配对 t 检验、均值偏差的 t 分布 95% CI、Pearson 相关、ICC(A,1)（双向绝对一致、单次测量；数值公式与 ICC(2,1) 相同，但不推广到其他任意方法）、Lin CCC（总体经验矩 `ddof=0`）一并给出。两方法为固定的 Real/Syn，相关系数不是一致性替代指标。

ICC/CCC 的 95% CI 采用 ROI 内成对 subject bootstrap：总体 1000 次，各诊断组 500 次，seed=20261016；这是有界 Monte Carlo 估计，不包含生成器训练/模型选择不确定性。Bland–Altman LoA 为均值差±1.96×差值样本 SD，边界 CI 使用常见正态近似 `±1.96 SD sqrt(3/n)`；偏态、异方差和 proportional bias 需结合散点查看，不将该 LoA 当作临床可接受界限。图例明确为回顾性样本。

校准回归为 Syn 对 Real 的 OLS slope/intercept，不施加生理阈值。proportional bias 为差值对两者均值的线性斜率。没有被认可的预设临床等效边界，因此不实施 TOST，不把 p>0.05 或高 ICC 当成等效。

## 多重检验 family

1. 主要总体配对 t：2 tracer × 98 ROI = **196**，统一 BH，保存原始 `paired_p` 和 `paired_q_global`；另存每 tracer 的 98 项校正用于透明比较，主判定用全 196 项。
2. 探索性诊断分层：5 组 × 2 tracer × 98 ROI = **980**，统一 BH；另存 tracer/group 内 98 项校正。
3. AD−CN 未调整差异：Real/Syn × 2 tracer × 98 ROI = **392**，Welch 检验及统一 BH；Real 显著和 Syn 显著不等于两者 AD−CN 差异相等。
4. 年龄/性别 HC3 回归及增加正体重的敏感性回归：每种模型、每种 outcome（Real、Syn、Syn−Real）各 **196** 项 BH。Syn−Real 对 AD 指示变量的系数直接检验两方法 AD−CN contrast 的差异。它仅控制已观测人口学变量，不能排除认知提示、站点或选择偏差。
5. proportional-bias 探索性斜率：总体 196 项统一 BH。
6. Table S1：年龄/有效体重两项可进行的五组 ANOVA 作为一个 2 项 BH family；Kruskal–Wallis 敏感性检验另一个 2 项 family；sex 是单独预设分类变量检验。认知评分的五组检验因空组/单例组不实施，不用 NA 填入校正。

上述 family 分开标注，不能从多个校正方案中选择有利者。

## 人口学来源与边界

源临床导出表为 `/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/ADNI MRI and FDG and AV45 csv.csv`。精确匹配 Subject ID、Sex、Weight、Research Group、Age 五个字段锚定论文选择的记录；1857 人均匹配。一个锚点内仅取唯一的非缺失原始临床值，多次影像导出不重复作为受试者，不从其他访视借值，不做诊断依赖填补。`clinical_anchor_source_rows.csv` 保留 Image ID、Modality 及原始变量，`clinical_observed_provenance.csv` 保存 observed/missing/conflicting 状态和 filled 值对照。

该导出缺少 EXAMDATE/VISCODE，故无法认证临床评分与实际 MRI/PET 日期配对。65 个非正体重设为缺失；未随意剔除其他极端值，体重原始单位需数据字典核实。认知评分空组不能从填补后的 Description 补回。对相关变量保留观察数和 NA，声明不可在选定记录上恢复；不生成模拟数据。

## 方法参考

- [Bland & Altman, 1986](https://pubmed.ncbi.nlm.nih.gov/2868172/)：方法一致性与 LoA。
- [Lin, 1989](https://pubmed.ncbi.nlm.nih.gov/2720055/)：CCC。
- [Koo & Li, 2016](https://pmc.ncbi.nlm.nih.gov/articles/PMC4913118/) 及其 [erratum](https://pmc.ncbi.nlm.nih.gov/articles/PMC5731844/)：ICC 类型与报告。
- [ADNI PET documentation](https://adni.loni.usc.edu/data-samples/adni-data/neuroimaging/pet/)：PET 的参考区及强度归一化；公开规范不能反过来证明本项目的保存影像已经遵循同一量化流程。
