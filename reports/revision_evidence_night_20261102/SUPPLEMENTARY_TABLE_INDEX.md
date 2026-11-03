# 补充表格草稿索引

S-N编号为本次内部草稿编号，不修改正式supplementary.tex，不占用G8 Table S1。LaTeX为longtable片段，需longtable/booktabs；横向表另需pdflscape。未编译论文。

| id    | title                                      |   rows | csv                                                         | latex                                                       |
|:------|:-------------------------------------------|-------:|:------------------------------------------------------------|:------------------------------------------------------------|
| S-N01 | Whole volume generation metrics            |     12 | tables/S-N01_whole_volume_generation_metrics.csv            | tables/S-N01_whole_volume_generation_metrics.tex            |
| S-N02 | Generation distributions                   |     48 | tables/S-N02_generation_distributions.csv                   | tables/S-N02_generation_distributions.tex                   |
| S-N03 | Paired generation comparisons              |     40 | tables/S-N03_paired_generation_comparisons.csv              | tables/S-N03_paired_generation_comparisons.tex              |
| S-N04 | Brain-mask metrics unchanged               |     24 | brain_mask/summary_metrics.csv                              | tables/S-N04_brain_mask_reused.tex                          |
| S-N05 | Brain-mask paired comparisons unchanged    |     16 | brain_mask/paired_comparisons.csv                           | tables/S-N05_brain_mask_reused.tex                          |
| S-N06 | Historical98 ROI agreement                 |    196 | tables/S-N06_historical98_roi_agreement.csv                 | tables/S-N06_historical98_roi_agreement.tex                 |
| S-N07 | Historical98 ROI paired inference by group |   1176 | tables/S-N07_historical98_roi_paired_inference_by_group.csv | tables/S-N07_historical98_roi_paired_inference_by_group.tex |
| S-N08 | Historical98 ROI Bland Altman              |    196 | tables/S-N08_historical98_roi_bland_altman.csv              | tables/S-N08_historical98_roi_bland_altman.tex              |
| S-N09 | Historical16 ROI Pearson OLS               |     16 | tables/S-N09_historical16_roi_pearson_ols.csv               | tables/S-N09_historical16_roi_pearson_ols.tex               |
| S-N10 | Historical Figure4 disease effect sizes    |     20 | tables/S-N10_historical_figure4_disease_effect_sizes.csv    | tables/S-N10_historical_figure4_disease_effect_sizes.tex    |
| S-N11 | Full OT OOF98 ROI agreement                |    392 | tables/S-N11_full_ot_oof98_roi_agreement.csv                | tables/S-N11_full_ot_oof98_roi_agreement.tex                |
| S-N12 | Full OT OOF98 ROI bias inference           |    392 | tables/S-N12_full_ot_oof98_roi_bias_inference.csv           | tables/S-N12_full_ot_oof98_roi_bias_inference.tex           |
| S-N13 | Classification27 conditions five metrics   |    135 | tables/S-N13_classification27_conditions_five_metrics.csv   | tables/S-N13_classification27_conditions_five_metrics.tex   |
| S-N14 | Existing imaging paired classification     |     30 | tables/S-N14_existing_imaging_paired_classification.csv     | tables/S-N14_existing_imaging_paired_classification.tex     |
| S-N15 | New clinical paired classification         |     60 | tables/S-N15_new_clinical_paired_classification.csv         | tables/S-N15_new_clinical_paired_classification.tex         |
| S-N16 | Classification paired DeLong by fold       |     54 | tables/S-N16_classification_paired_delong_by_fold.csv       | tables/S-N16_classification_paired_delong_by_fold.tex       |
| S-N17 | E1 fixed weight score removal              |     12 | tables/S-N17_e1_fixed_weight_score_removal.csv              | tables/S-N17_e1_fixed_weight_score_removal.tex              |
| S-N18 | E1 score removal by fold                   |     24 | tables/S-N18_e1_score_removal_by_fold.csv                   | tables/S-N18_e1_score_removal_by_fold.tex                   |
| S-N19 | Adapter sensitivity existing results       |     10 | tables/S-N19_adapter_sensitivity_existing_results.csv       | tables/S-N19_adapter_sensitivity_existing_results.tex       |
| S-N20 | Historical Figure2 absolute summaries      |     21 | tables/S-N20_historical_figure2_absolute_summaries.csv      | tables/S-N20_historical_figure2_absolute_summaries.tex      |
| S-N21 | Full measured inference efficiency         |      2 | tables/S-N21_full_measured_inference_efficiency.csv         | tables/S-N21_full_measured_inference_efficiency.tex         |
| S-N22 | Classification split identity              |      9 | tables/S-N22_classification_split_identity.csv              | tables/S-N22_classification_split_identity.tex              |
| S-N23 | Generator OOF split coverage               |      2 | tables/S-N23_generator_oof_split_coverage.csv               | tables/S-N23_generator_oof_split_coverage.tex               |

指标定义、多重比较族与来源边界随每份LaTeX表保留；完整可复算说明见各G组REPORT.md及code/PROTOCOL.md。
