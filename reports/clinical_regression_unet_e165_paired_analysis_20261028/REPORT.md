# Clinical Regression 3D U-Net paired analysis at Epoch 165

## Executive conclusion

The frozen inputs passed the one-to-one pairing and fairness audit with no material blocker. All eight two-sided paired tests remained significant after Holm correction (largest adjusted p=0.006). All eight comparisons favored Full in both held-out folds. The evidence supports a whole-framework, matched-information comparison only; it does not isolate Rectified Flow or BiomedCLIP and does not establish uncertainty representation or pathology-specific clinical validity.

## 中文科学解释

在完全相同的 Epoch 165 OOF 配对身份上，Full 在 FDG（n=1,598）和 AV45（n=1,365）的四项平均指标上均优于回归 U-Net。FDG 中，Full 的 SSIM 平均差为 0.0208（95% CI 0.0198 至 0.0218；89.9% 受试者改善），PSNR 平均差为 0.611 dB（76.6% 改善），MSE 平均差为 -0.00023（76.6% 改善），MAE 平均差为 -0.00172（75.4% 改善）。 AV45 中，Full 的 SSIM 平均差为 0.0240（95% CI 0.0227 至 0.0253；87.1% 受试者改善），PSNR 平均差为 0.329 dB（62.1% 改善），MSE 平均差为 -0.00015（62.1% 改善），MAE 平均差为 -0.00147（63.7% 改善）。 八项双侧配对检验经 Holm 校正后仍均有统计学支持（最大校正 p=0.006），且八项平均改善在两个 held-out fold 中方向均一致。

八项比较的 |Cohen's dz| 范围为 0.075–0.991。SSIM 的标准化效应较大（FDG dz=0.991；AV45 dz=0.979），AV45 MSE 的标准化效应很小（dz=-0.075），其余指标为小到中等效应。Full 获益比例范围为 62.1%–89.9%。八项中位配对差均支持 Full，且每项均有过半受试者获益，说明均值优势并非仅由极少数离群值驱动；但八项的 5th–95th percentile 均跨越零，仍有一部分受试者在回归 U-Net 下表现更好，不能把优势解释为普遍个体获益。

因此，结论不能只写“统计显著”：应同时报告配对差值、置信区间、效应量和获益比例。对 AV45 MSE 等绝对差值和标准化效应均较小的结果，应表述为“数值幅度较小但在冻结 OOF 样本中有配对统计支持”，不能使用 substantial superiority 或 clinical equivalence。

该结果可直接回应 R3-10 对“基线没有相同临床输入”的质疑，也可回应 R3-12 要求的同条件普通回归 U-Net 比较。但它只支持“完整 DIReCT++ 框架优于本次匹配信息的直接回归基线”，不能单独证明 Rectified Flow、BiomedCLIP/VLM 或任何单一模块的因果增益。

本实验还不能支持：病理区域保真性、brain-mask 内优势、临床 SUVR 一致性、个体淀粉样阳性判别、临床等效性、随机采样或不确定性表示、跨随机种子/重训练稳定性，或已排除历史临床变量填补来源造成的 shortcut/leakage。Full 是本轮新完成的作者代码语义重建，不是原论文历史运行。


## English Results paragraph

At the prespecified epoch-165 endpoint, DIReCT++ Full was compared with the clinical regression 3D U-Net using one-to-one paired two-fold out-of-fold predictions (FDG, n=1,598; AV45, n=1,365). For FDG, Full changed SSIM by 0.0208 (95% CI 0.0198 to 0.0218; 89.9% improved), PSNR by 0.611 dB (76.6% improved), MSE by -0.00023 (76.6% improved), and MAE by -0.00172 (75.4% improved). For AV45, Full changed SSIM by 0.0240 (95% CI 0.0227 to 0.0253; 87.1% improved), PSNR by 0.329 dB (62.1% improved), MSE by -0.00015 (62.1% improved), and MAE by -0.00147 (63.7% improved). All eight two-sided paired tests remained significant after Holm correction (largest adjusted p=0.006). All eight comparisons favored Full in both held-out folds. Across the eight comparisons, |Cohen's dz| ranged from 0.075 to 0.991, and the proportion of subjects favoring Full ranged from 62.1% to 89.9%. SSIM effects were large (dz=0.991 for FDG and 0.979 for AV45), whereas AV45 MSE showed a very small standardized effect (dz=-0.075) despite statistical support; the remaining effects were small to moderate. The median paired difference favored Full for every comparison, and the majority of subjects benefited in each comparison, arguing against an average driven only by a few extreme cases. However, the 5th–95th percentile range crossed zero in 8 of 8 comparisons, so benefit was not universal. These estimates support a consistent but metric-dependent advantage in this frozen OOF realization; their confidence intervals quantify subject-level sampling variation, not uncertainty across random seeds or model retraining.

## Reviewer-response wording

### R3-10

**Suggested response to R3-10.** We added a deterministic clinical regression 3D U-Net baseline that receives the same MRI, the same eight clinical variables (age, sex, weight, CDR, MMSE, GDS, FAQ, and NPI-Q), and tracer identity as DIReCT++. The comparator uses a four-level 3D U-Net with an MLP-conditioned bottleneck FiLM branch, directly regresses normalized PET, and was evaluated on the identical frozen two-fold splits, effective PET targets, preprocessing cache, `[0,1]` clamp, and whole-volume SSIM/PSNR/MSE/MAE protocol. At epoch 165, the paired analysis included 1,598 FDG and 1,365 AV45 predictions. The Full-minus-U-Net mean differences were +0.0208 SSIM, +0.611 dB PSNR, -0.00023 MSE, and -0.00172 MAE for FDG, and +0.0240 SSIM, +0.329 dB PSNR, -0.00015 MSE, and -0.00147 MAE for AV45. All eight two-sided paired tests remained significant after Holm correction (largest adjusted p=0.006). All eight comparisons favored Full in both held-out folds. Subject-level benefit proportions ranged from 62.1% to 89.9% across metrics. This matched-information baseline addresses the confounding caused by earlier baselines lacking clinical inputs, while remaining a whole-framework comparison rather than a single-component causal ablation.

### R3-12

**Suggested response to R3-12.** We compared DIReCT++ against a plain deterministic regression 3D U-Net with identical clinical-variable and tracer information and the same frozen OOF evaluation protocol. DIReCT++ showed the metric-specific paired differences reported in Table 1; all eight tests remained significant after Holm correction (largest adjusted p=0.006), and all eight mean differences favored Full in both folds. Effect sizes were metric-dependent (|dz|=0.075–0.991), with a very small standardized AV45 MSE advantage despite its statistical support. This result shows that the complete DIReCT++ implementation outperformed this direct conditional-regression comparator in the present run, but it does not prove that Rectified Flow alone caused the gain or that conditional-mean smoothing has been eliminated. Both evaluated systems return deterministic point estimates, and the experiment provides no ensemble- or sampling-based epistemic/aleatoric uncertainty estimate. We therefore limit the claim to frozen OOF image-quality metrics and explicitly retain uncertainty quantification and pathology-specific validation as future work.

## Limitations that must remain with the result

- Metrics were computed over the complete preprocessed volume, not within a brain mask.
- Intensities are normalized uptake values scaled to `[0,1]`, not clinical SUVR.
- Whole-volume SSIM/PSNR/MSE/MAE do not establish pathology-region fidelity or subject-level amyloid-status agreement.
- Both evaluated systems are deterministic point estimators; no aleatoric or epistemic uncertainty was estimated.
- The eight clinical fields contain historical filled values whose upstream imputation and visit alignment were not recovered; shortcut/leakage from their provenance has not been excluded.
- Subject-level bootstrap and paired-test uncertainty concerns this frozen OOF experiment only, not random-seed or retraining variability.
- The comparison differs in condition encoding and architecture by design, so it is not a causal single-factor ablation.
- The Full results are a new author-code-semantics reconstruction, not the original paper's historical run.

## Statistical scope

All p values are from two-sided paired t-tests on subject-level Full-minus-U-Net differences. Holm adjustment covers one family of eight prespecified primary comparisons (two tracers × four metrics). Bootstrap intervals use 10,000 paired subject-level resamples with seed 42 and preserve the original fold sizes by resampling separately within each held-out fold. FDG and AV45 were not pooled into a single significance test.
