# 已勾选审稿意见：原文、英文回复与正文修改

导出范围：当前清单中 33 条已勾选的 R2、R3、Minor 意见。正文修改为来源中的方案或候选稿，**不代表已实施或最终确认**。正文位置和 TeX 行号仅按来源记录；未标注的不推测。重复位置保留并提示整合。

[来源：BMEF审稿回复](https://app.notion.com/p/3d295d43b2dd8300b74601d792205677) · [G4 合并方案](https://app.notion.com/p/40c95d43b2dd8081b5b3ea02e06e0964)

# Reviewer 2 — Major

## R2-1. 方法创新性

### Original

> High scientific novelty: The integration of 3D rectified flow, a domain-adapted BiomedCLIP/VLM, and multi-tracer PET synthesis is a clear methodological contribution beyond conventional MRI-to-PET translation.

### Response

We sincerely thank the reviewer for the positive assessment of the methodological contribution of our work. We appreciate the recognition of the value of integrating 3D rectified flow, domain-adapted BiomedCLIP/VLM, and multi-tracer PET synthesis.

## R2-2. 临床研究动机

### Original

> Strong clinical motivation: Synthesizing AV45-PET and FDG-PET from routine MRI addresses important limitations related to PET cost, radiation exposure, and accessibility.

### Response

We thank the reviewer for highlighting the clinical relevance of our study. Addressing the challenges of PET acquisition costs, radiation exposure, and limited accessibility through MRI-based synthesis of AV45-PET and FDG-PET is a central motivation for our work.

## R2-3. 交叉验证折数不一致

### Original

> Cross-validation inconsistency: The Results section reports 3-fold cross-validation, whereas the preprocessing/methodology section reports a two-fold scheme. The exact protocol must be reconciled and stated consistently for each experiment.

### Response

We thank the reviewer for pointing out the insufficient clarification of the cross-validation protocols in the original manuscript.

We confirm that the two-fold and three-fold cross-validation schemes were employed for different experimental stages. Specifically, two-fold cross-validation was used for PET image synthesis, where the training and held-out subsets were exchanged between folds to generate out-of-fold (OOF) synthetic PET images for the study subjects. Subsequently, a separate three-fold cross-validation scheme was applied to the downstream diagnostic classification tasks using the generated synthetic PET images to evaluate the contribution of different imaging inputs to classification performance.

Therefore, the two cross-validation schemes are not contradictory but correspond to distinct evaluation stages: PET image synthesis and downstream diagnostic classification. We will clarify their respective purposes and consistently distinguish these protocols in the Results and Methods sections of the revised manuscript to avoid ambiguity.

**核查提示：** 上述历史三折描述与主页面“原始分类三折重复使用同一折”的已确认事实存在冲突；新实验完成前不得将其视为历史有效三折结果。

### Modified in Manuscript

#### 来源：主页面

修改一：Results → Superior Fidelity and Generalizability of Synthesized PET

位置：`BMEF_main.tex` 第 102 行。

###### 修改 1

- 位置：Results → Superior Fidelity and Generalizability of Synthesized PET
- TeX 行号：102

Original

```txt
Models were trained on the ADNI dataset and evaluated under two settings: internally via 3-fold cross-validation on ADNI, and externally on the independent OASIS cohort (for which only $^{18}$F-AV-45 was available).
```

Revised

```txt
Models were trained on the ADNI dataset and evaluated under two settings: internally via two-fold cross-validation for PET synthesis on ADNI, and externally on the independent OASIS cohort (for which only $^{18}$F-AV-45 was available).
```

修改理由： 将错误的 `3-fold` 修正为 `two-fold`，同时增加 `for PET synthesis` 明确适用范围。其余内容保持不变。

修改二：Methods → Materials and Data Preprocessing

位置：`BMEF_main.tex` 第 303 行。

###### 修改 2

- 位置：Methods → Materials and Data Preprocessing
- TeX 行号：303

Original

> Model evaluation was conducted under a two-fold cross-validation scheme: the cohort was randomly partitioned into two equal-sized subsets, with alternating roles as training/validation and test sets to ensure unbiased performance estimation.

Revised

> PET synthesis was evaluated under a two-fold cross-validation scheme: the cohort was randomly partitioned into two equal-sized subsets, with alternating roles as training/validation and test sets to ensure unbiased performance estimation. The held-out synthetic PET images generated from both folds were combined to form an out-of-fold (OOF) dataset for subsequent analyses.

修改理由：

将 `Model evaluation` 明确为 `PET synthesis`，并补充一句 OOF 合并与下游分类之间的关系。

这与原作者确认的历史实验流程一致，也解释了为什么生成阶段采用两折，而分类阶段可以独立采用三折。


## R2-4. 预后分层表述过度

### Original

> Overstatement of prognostic stratification: EMCI-versus-LMCI classification is a stage-discrimination task and does not by itself establish longitudinal prognosis or future conversion to AD. The terminology should be moderated unless longitudinal conversion outcomes are analyzed.

### Response

We thank the reviewer for highlighting the important distinction between MCI stage discrimination and longitudinal prognostic prediction.

Our original motivation for relating EMCI/LMCI classification to disease progression was based on previous longitudinal studies showing that patients with LMCI generally exhibit more severe cognitive impairment and have a higher subsequent risk of conversion to dementia than those with EMCI (Aisen et al., 2015; Lin et al., 2022; Petersen, 2021). This clinical evidence motivated us to include EMCI-versus-LMCI classification as a downstream task to evaluate the performance of synthetic PET in distinguishing clinically relevant MCI stages.

Nevertheless, we agree that such population-level associations do not establish individual-level prognostic prediction. Our study evaluated cross-sectional classification performance without analyzing longitudinal conversion outcomes. Therefore, the EMCI-versus-LMCI classification results cannot, by themselves, demonstrate the ability to predict future conversion to AD or disease progression.

To address this concern, we will explicitly describe this task as MCI stage discrimination and revise the relevant terminology and conclusions throughout the manuscript. In particular, we will remove unsupported claims regarding prognostic prediction and future disease progression, ensuring that our conclusions accurately reflect the scope of the analyses performed.

1. Aisen, P. S., et al. (2015). Alzheimer's Disease Neuroimaging Initiative 2 Clinical Core: Progress and plans. Alzheimer's & Dementia, 11(7), 734–739. [https://doi.org/10.1016/j.jalz.2015.05.005](https://doi.org/10.1016/j.jalz.2015.05.005)
2. Lin, S.-Y., et al. (2022). The Clinical Course of Early and Late Mild Cognitive Impairment. Frontiers in Neurology, 13, 685636. [https://doi.org/10.3389/fneur.2022.685636](https://doi.org/10.3389/fneur.2022.685636)
3. Petersen, R. C. (2021). MCI Criteria in ADNI: Meeting Biological Expectations. Neurology, 97(12), 597–599. [https://doi.org/10.1212/WNL.0000000000012588](https://doi.org/10.1212/WNL.0000000000012588)

**核查提示：** Results §2.4 的历史三折分类数值及主张需依据重做的分类实验重新核验；Methods §4.5.2 标题与 R3-3 的方案不同，需归组统一。

### Modified in Manuscript

#### 来源：[R2-4 Changes in the Revised Manuscript](https://app.notion.com/p/af295d43b2dd836ebbe201bd6d6d1ce0)

##### 1. Abstract

原稿 LaTeX 第 60、68 行；PDF 第 1–2 页

Impact Statement

###### 修改 1

- 位置：Abstract
- TeX 行号：60、68

原文：

> This work advances a scalable, data-efficient tool for the early diagnosis and prognostic prediction of AD.

建议替换为：

This work advances a scalable, data-efficient tool for the early diagnosis of AD and discrimination between MCI stages.

Conclusion

###### 修改 2

- 位置：Abstract
- TeX 行号：60、68

原文：

> Crucially, combining these synthesized PET images with MRI enables precise personalized stratification of mild cognitive impairment (MCI), advancing a scalable, data-efficient tool for the early diagnosis and prognostic prediction of AD.

建议替换为：

Crucially, combining these synthesized PET images with MRI enables precise discrimination between early and late stages of mild cognitive impairment (MCI), advancing a scalable, data-efficient tool for the early diagnosis of AD.

##### 2. Introduction

LaTeX 第 77、81 行；PDF 第 2–3 页

###### 修改 3

- 位置：Introduction
- TeX 行号：77

第 77 行，将：

> Despite these advances, a critical limitation remains: the subject-specific precision necessary for personalized diagnosis and prognostic stratification is still lacking, which is particularly crucial for a heterogeneous condition like AD\~\\cite.

替换为：

Despite these advances, a critical limitation remains: the subject-specific precision necessary for personalized diagnosis and MCI stage discrimination is still lacking, which is particularly crucial for a heterogeneous condition like AD\~\\cite.

###### 修改 4

- 位置：Introduction
- TeX 行号：81

第 81 行，将：

> When combined with the original MRI scans to train deep learning classifiers\~\\cite, the synthesized PET data enable accurate personalized diagnosis and, most importantly, the stratification of MCI patients based on their risk of progression to AD.

替换为：

When combined with the original MRI scans to train deep learning classifiers\~\\cite, the synthesized PET data enable accurate personalized diagnosis and, most importantly, the differentiation between early and late MCI stages.

##### 3. Results — Section 2.4

LaTeX 第 151–158 行；PDF 第 7–9 页

章节标题

###### 修改 5

- 位置：Results — Section 2.4
- TeX 行号：151–158

原文：

`Precise Prognostic Stratification of Mild Cognitive Impairment`

建议：

`Diagnostic Classification and MCI Stage Discrimination`

第一段第一句

###### 修改 6

- 位置：Results — Section 2.4
- TeX 行号：151–158

Original：

> To evaluate the clinical utility of the synthetic images for personalized diagnosis and prognostic stratification, we conducted classification tasks on the ADNI cohort using a 3-fold cross-validation scheme.

Revised：

> To evaluate the clinical utility of the synthetic images for personalized diagnosis and MCI stage discrimination, we conducted classification tasks on the ADNI cohort using a 3-fold cross-validation scheme.

###### 修改 7

- 位置：Results — Section 2.4
- TeX 行号：151–158

Original：

> Crucially, the combination of baseline MRI and synthetic multi-tracer PET also enabled accurate prognostic stratification, achieving 81.96% accuracy in differentiating EMCI from LMCI, compared to 77.65% using MRI alone (Fig. 5C).

Revised：

> Crucially, the combination of baseline MRI and synthetic multi-tracer PET also enabled accurate MCI stage discrimination, achieving 81.96% accuracy in differentiating EMCI from LMCI, compared to 77.65% using MRI alone (Fig. 5C).

###### 修改 8

- 位置：Results — Section 2.4
- TeX 行号：151–158

Original：

> This result highlights the potential of DIReCT++ to stratify patients at the prodromal stage based on their risk of progression.

Revised：

> This result highlights the potential of DIReCT++ to distinguish different stages of MCI.

LaTeX 第 167 行

###### 修改 9

- 位置：Results — Section 2.4
- TeX 行号：167

Original

> Taken together, these findings confirm the translational potential of DIReCT++, as its synthetic outputs serve as effective proxies for real PET biomarkers in critical downstream diagnostic and prognostic tasks.

Revised

> Taken together, these findings confirm the translational potential of DIReCT++, as its synthetic outputs serve as effective proxies for real PET biomarkers in downstream diagnostic tasks, including MCI stage discrimination.

##### 4. Discussion

LaTeX 第 171、175、188 行；PDF 第 9–12 页

建议采用以下定向修改：

<table header-row="true">
<colgroup>
<col />
<col width="428" />
</colgroup>
<tr>
<td>
原稿措辞
</td>
<td>
建议替换
</td>
</tr>
<tr>
<td>
`enable precise prognostic stratification of MCI`
</td>
<td>
enable precise MCI stage discrimination
</td>
</tr>
<tr>
<td>
`accurate diagnosis and prognostic stratification of MCI`
</td>
<td>
accurate diagnosis and discrimination between MCI stages
</td>
</tr>
</table>

新增limitations

Importantly, the EMCI-versus-LMCI classification was based on cross-sectional diagnostic categories rather than longitudinal conversion outcomes. Although previous studies have reported differences in subsequent dementia-conversion risk between EMCI and LMCI populations, the present study did not evaluate individual-level disease progression or future conversion to AD. Therefore, the classification results should not be interpreted as evidence of prognostic prediction. Longitudinal validation will be necessary to investigate the prognostic relevance of the synthesized PET images.

##### 9. Materials and Methods — Section 4.3

LaTeX 第 295 行

###### 修改 10

- 位置：Materials and Methods — Section 4.3
- TeX 行号：295

Original

> To account for the heterogeneity of MCI, we further subclassified individuals based on delayed recall performance on the WMS-R Logical Memory II Story A task: Early MCI (EMCI; n = 291) denoted a milder impairment stage, whereas Late MCI (LMCI; n = 152) indicated proximity to dementia conversion.

Revised

> To account for the heterogeneity of MCI, we further subclassified individuals based on delayed recall performance on the WMS-R Logical Memory II Story A task: Early MCI (EMCI; n = 291) denoted a milder impairment stage, whereas Late MCI (LMCI; n = 152) denoted a more severe impairment stage.

下一句

###### 修改 11

- 位置：Materials and Methods — Section 4.3
- TeX 行号：295

Original：

> The remaining MCI participants without clear progression status were grouped as MCI-unclassified (MCI-U; n = 520).

Revised：

> The remaining MCI participants not classified as EMCI or LMCI were grouped as MCI-unclassified (MCI-U; n = 520).

##### 6. Materials and Methods — Section 4.5.2

LaTeX 第 338–340 行；PDF 第 18 页附近

原章节标题：

`Diagnosis and Prognostic Stratification`

建议修改为：

`Diagnostic Classification and MCI Stage Discrimination`

第一句

###### 修改 12

- 位置：Materials and Methods — Section 4.5.2
- TeX 行号：338–340

Original：

> To rigorously evaluate the clinical utility of synthesized PET (Syn-PET) images, we assessed their capacity to support diagnostic and prognostic classification across the AD continuum.

Revised：

> To rigorously evaluate the clinical utility of synthesized PET (Syn-PET) images, we assessed their capacity to support diagnostic classification and MCI stage discrimination across the AD continuum.

第二句

###### 修改 13

- 位置：Materials and Methods — Section 4.5.2
- TeX 行号：338–340

Original：

> Specifically, we trained identical DenseNet classifiers to discriminate between three clinically salient diagnostic pairs: (1) AD versus CN individuals, a canonical diagnostic boundary; (2) MCI versus CN, representing early disease detection; and (3) EMCI versus late MCI (LMCI), a prognostic distinction reflecting differential progression risk.

Revised：

> Specifically, we trained identical DenseNet classifiers to discriminate between three clinically salient diagnostic pairs: (1) AD versus CN individuals, a canonical diagnostic boundary; (2) MCI versus CN, representing early disease detection; and (3) EMCI versus late MCI (LMCI), representing different degrees of memory impairment.


## R2-6. 受试者级划分和纵向访视

### Original

> Subject-level splitting must be explicit: Because ADNI contains longitudinal scans, the authors should confirm that all visits from a given participant remain within a single fold to avoid subject leakage between training and testing.

### Response

We thank the reviewer for highlighting the importance of subject-level data splitting and the potential risk of data leakage arising from longitudinal visits.

Although the original ADNI database contains longitudinal imaging data, the subset used in our study was selected such that only one imaging record was retained per subject. Consequently, no scans from different visits of the same subject could be assigned to different cross-validation folds, thereby preventing subject-level data leakage arising from repeated visits.

We will clarify this data selection criterion in the revised manuscript to avoid ambiguity.

### Modified in Manuscript

#### 来源：主页面

修改位置： `BMEF_main.tex` 第 293 行，Methods → Materials and Data Preprocessing，第一段。

###### 修改 1

- 位置：Methods → Materials and Data Preprocessing
- TeX 行号：293

Original

```txt
This study leveraged neuroimaging data from 1,857 participants enrolled in the Alzheimer’s Disease Neuroimaging Initiative (ADNI), spanning cohorts from ADNI-1 through ADNI-4. All participants underwent structural T1-weighted MRI, while subsets also had \textsuperscript{18}F-FDG-PET ($n = 1,598$) and \textsuperscript{18}F-AV45-PET ($n = 1,365$) scans available, enabling multi-tracer PET synthesis.
```

Revised

```txt
This study leveraged neuroimaging data from 1,857 participants enrolled in the Alzheimer’s Disease Neuroimaging Initiative (ADNI), spanning cohorts from ADNI-1 through ADNI-4. All participants underwent structural T1-weighted MRI, while subsets also had \textsuperscript{18}F-FDG-PET ($n = 1,598$) and \textsuperscript{18}F-AV45-PET ($n = 1,365$) scans available, enabling multi-tracer PET synthesis. Only one imaging record per participant was retained for analysis, excluding repeated longitudinal visits from the same participant.
```


## R2-7. 双示踪剂外部验证不足

### Original

> External validation is incomplete for multi-tracer claims: OASIS-3 external evaluation includes AV45-PET but excludes FDG-PET. Therefore, external generalizability is demonstrated only partially and the multi-tracer generalization claim should be qualified.

### Response

We thank the reviewer for highlighting the need to clarify the scope of our external validation.

In this study, both AV45-PET and FDG-PET synthesis were evaluated internally on the ADNI dataset, whereas external validation on the independent OASIS-3 dataset was conducted only for AV45-PET. As described in the original manuscript (Section 4.3), FDG-PET scans in OASIS-3 were not included in the external evaluation due to the lack of a standardized PUP processing pipeline.

We agree that the current OASIS-3 results provide evidence of cross-dataset generalizability for AV45-PET synthesis only and cannot be directly extended to FDG-PET synthesis. Accordingly, we will clarify the scope of external validation and refine the relevant statements regarding multi-tracer generalizability in the revised manuscript to ensure that our conclusions accurately reflect the evaluations performed.

### Modified in Manuscript

#### 来源：[R2-7 正文修改](https://app.notion.com/p/56895d43b2dd82f4b08f017a857a96b6)

##### 一、Abstract — Results

LaTeX 第 66 行

###### 修改 1

- 位置：Abstract — Results
- TeX 行号：66

Original

> Extensive evaluations on multi-center datasets demonstrate that DIReCT++ not only produces synthetic PET images (¹⁸F-AV-45 and ¹⁸F-FDG) of superior fidelity and generalizability but also accurately recapitulates disease-specific patterns.

Revised

Extensive evaluations on multi-center datasets demonstrate that DIReCT++ not only produces synthetic PET images (¹⁸F-AV-45 and ¹⁸F-FDG) of superior fidelity but also accurately recapitulates disease-specific patterns, with cross-dataset generalizability demonstrated for ¹⁸F-AV-45 PET synthesis.

##### 二、Introduction — 研究贡献总结

LaTeX 第 81 行

###### 修改 2

- 位置：Introduction — 研究贡献总结
- TeX 行号：81

Original

> Comprehensive experiments demonstrate that our model generates multi-tracer PET images with superior fidelity and generalizability compared to state-of-the-art methods.

Revised

Comprehensive experiments demonstrate that our model generates multi-tracer PET images with superior fidelity compared to state-of-the-art methods, with cross-dataset generalizability further demonstrated for ¹⁸F-AV-45 PET synthesis.

##### 三、Results — Section 2.2

LaTeX 第 106 行

这一段已经分别讨论内部评估和 OASIS 外部验证，因此只建议修改其中两句。

##### 修改 1：外部验证的范围

###### 修改 3

- 位置：Results — Section 2.2
- TeX 行号：106

Original

> External validation on the OASIS cohort confirmed that the advantages of DIReCT++ generalize beyond the training data (Fig. 2A).

Revised

External validation on the OASIS cohort confirmed that the advantages of DIReCT++ in ¹⁸F-AV-45 PET synthesis generalize beyond the training data (Fig. 2A).

只增加 in ¹⁸F-AV-45 PET synthesis，其余保持不变。

##### 修改 2：段落总结

###### 修改 4

- 位置：Results — Section 2.2
- TeX 行号：106

Original

> This robust performance across diverse datasets affirms the state-of-the-art status of DIReCT++, highlighting its superior fidelity, generalization capacity, and effective cross-modal and cross-tracer integration.

Revised

This robust performance across diverse datasets affirms the state-of-the-art status of DIReCT++ especially for ¹⁸F-AV-45 PET synthesis, highlighting its superior fidelity and generalization capacity.

##### 四、Figure 2 — Caption

LaTeX 第 112–114 行

##### Panel A

###### 修改 5

- 位置：Figure 2 — Caption
- TeX 行号：112–114

Original

> (A) Radar plots show normalized quantitative results (SSIM, MSE, MAE, PSNR) for FDG-PET and AV45-PET reconstruction on ADNI, and cross-dataset generalization on OASIS.

Revised

(A) Radar plots show normalized quantitative results (SSIM, MSE, MAE, PSNR) for FDG-PET and AV45-PET reconstruction on ADNI, and cross-dataset generalization of AV45-PET on OASIS.

##### Panel C

###### 修改 6

- 位置：Figure 2 — Caption
- TeX 行号：112–114

Original

> (C) Generalization to OASIS using models trained on ADNI.

Revised

(C) Generalization to OASIS for AV45-PET using models trained on ADNI.

修改说明： 两处均为局部补充示踪剂名称，不改变图注的其他描述，也不需要修改 Figure 2 的图片内容。


## R2-8. 非显著性不等于等效性

### Original

> Non-significance does not prove equivalence: Using p > 0.05 between real and synthetic PET as evidence of high fidelity is statistically insufficient. Equivalence testing (e.g., TOST) with clinically meaningful equivalence margins is more appropriate.

### Response

We thank the reviewer for pointing out that the absence of a statistically significant difference does not constitute evidence of equivalence. We agree that relying solely on paired comparisons with p > 0.05 between real and synthetic PET images is statistically insufficient to support claims of high fidelity.

To provide a more comprehensive evaluation of regional uptake agreement, we performed additional statistical analyses using the originally preserved subject-level paired data. In addition to paired t-tests and multiple-comparison correction, we calculated the mean paired differences and their 95% confidence intervals, mean absolute error (MAE), Lin’s concordance correlation coefficient (CCC), intraclass correlation coefficient (ICC), and Bland–Altman bias and limits of agreement. Together, these metrics provide a more comprehensive assessment of mean bias, regional errors, and subject-level agreement.

The additional analyses showed that, across the 98 brain regions evaluated for each tracer, the median regional CCC values were 0.9745 and 0.9450 for AV45 and FDG, respectively, while the corresponding median regional MAE values were 0.0160 and 0.0159. Under the predefined multiple-comparison correction procedure, no statistically significant mean paired differences were detected in the vast majority of regions and diagnostic groups.

Regarding the suggested two one-sided tests (TOST), we acknowledge the value of formal equivalence testing. However, the regional uptake values in our study were derived from per-image min–max intensity normalization rather than clinically standardized quantitative measurements such as SUV or SUVR. Currently, a well-established equivalence margin with a clear clinical interpretation is lacking for measurements on this normalized intensity scale. Defining an arbitrary equivalence margin without sufficient justification could lead to conclusions that lack clinical interpretability. Therefore, we did not perform TOST to claim clinical equivalence.

Accordingly, we will revise the statistical interpretation in the manuscript to clearly distinguish the absence of statistically significant mean differences, regional uptake agreement, and formal equivalence. We will also moderate the original statements that inferred high fidelity from p > 0.05. Furthermore, we will explicitly acknowledge in the Limitations section that our current analyses support agreement in normalized regional uptake values but do not establish clinical quantitative equivalence. Future work will explore PET quantitative evaluation scales with clear biological and clinical interpretations, the definition of appropriate equivalence margins, and corresponding formal equivalence testing methods.

### Modified in Manuscript

#### G4 修改 1

- 位置：Results §2.3：区域摄取值定义
- TeX 行号：119
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
To assess the clinical validity of the synthesized PET images, we parcellated both synthetic and real PET scans into anatomical regions using \texttt{mri\_synthseg} (FreeSurfer v7.4.1)~\cite{fischl2012freesurfer,dalca2022synthseg}, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and \textit{aseg} atlases. This approach yielded a total of 98 distinct regions of interest (ROIs), including cortical, subcortical, cerebellar, and brainstem structures. Regional standardized uptake value  (SUV) were computed by extracting the mean tracer uptake within each ROI and normalizing to the cerebellar gray matter (for \textsuperscript{18}F-AV-45 PET) or the pons (for \textsuperscript{18}F-FDG PET). Fig.~\ref{fig:3} illustrates this analysis for key ROIs in two representative ADNI subjects, demonstrating strong regional consistency between synthetic and real images, as well as clear distinctions between syntheses from different diagnostic groups.
```

**Revised**

```txt
To assess the clinical validity of the synthesized PET images, we parcellated both synthetic and real PET scans into anatomical regions using \texttt{mri\_synthseg} (FreeSurfer v7.4.1)~\cite{fischl2012freesurfer,dalca2022synthseg}, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and \textit{aseg} atlases. This approach yielded a total of 98 distinct regions of interest (ROIs), including cortical, subcortical, cerebellar, and brainstem structures. Regional normalized uptake values (arbitrary units) were computed as the mean voxel intensity within each ROI from PET images normalized using per-image min--max intensity scaling. Fig.~\ref{fig:3} illustrates this analysis for key ROIs in two representative ADNI subjects, demonstrating strong regional consistency between synthetic and real images, as well as clear distinctions between syntheses from different diagnostic groups.
```

#### G4 修改 2

- 位置：Results §2.3：两类统计分析的目的
- TeX 行号：134
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
For a comprehensive quantitative evaluation, we performed two group-wise statistical comparisons on the ADNI cohort. First, we compared synthetic and real images to validate the regional SUV precision of DIReCT$++$. Second, we compared synthetic images across diagnostic groups (cognitively normal, i.e., CN, MCI, AD) to verify their ability to capture disease-relevant patterns.
```

**Revised**

```txt
For a comprehensive quantitative evaluation, we performed two complementary regional statistical analyses on the ADNI cohort. First, we compared synthetic and real images to assess the normalized regional uptake agreement of DIReCT$++$. Second, we compared the AD and CN groups separately in real and synthetic PET to assess whether disease-related regional differences were retained.
```

#### G4 修改 3

- 位置：Results §2.3：Real–Syn 区域一致性
- TeX 行号：136
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
Paired-sample $t$-tests between synthetic and real images revealed no statistically significant differences in mean SUV across all principal brain regions for the CN, MCI, and AD groups ($p>0.05$; Fig.~\ref{fig:4}A, B; figs.~\ref{fig:supp_av45_1}, \ref{fig:supp_av45_2}, \ref{fig:supp_fdg_1}, and \ref{fig:supp_fdg_2}). This high fidelity was consistent for both $^{18}$F-AV-45 (Fig.~\ref{fig:4}A) and $^{18}$F-FDG (Fig.~\ref{fig:4}B), indicating that DIReCT$++$ effectively captures the regional characteristics of the ground truth.
```

**Revised**

```txt
Paired-sample $t$-tests between synthetic and real images revealed no statistically significant differences in normalized regional uptake across the principal brain regions shown in Fig.~\ref{fig:4}A, B for the overall cohorts of both tracers ($p>0.05$). Across all 98 ROIs, no overall comparisons remained significant after Benjamini--Hochberg false discovery rate (FDR) correction (all $q>0.05$). Among the diagnosis-stratified paired comparisons, only the right pericalcarine cortex (ROI 2021) in the $^{18}$F-FDG MCI subgroup showed a significant mean paired difference after FDR correction ($q=0.0481$). The median concordance correlation coefficients (CCC) across the 98 ROIs were 0.9745 for $^{18}$F-AV-45 and 0.9450 for $^{18}$F-FDG, with corresponding median mean absolute errors (MAE) of 0.0160 and 0.0159 (normalized intensity units). For the 16 representative tracer--ROI combinations in Fig.~\ref{fig:4}A, B, descriptive regression slopes ranged from 0.9794 to 1.0127 (median, 1.0007) for $^{18}$F-AV-45 and from 0.9844 to 1.0101 (median, 1.0001) for $^{18}$F-FDG, without a consistent direction of deviation from unity. These results indicate close agreement in normalized regional uptake between synthetic and real PET, with detailed statistics for the representative ROIs provided in Supplementary Table~\ref{tab:regional_agreement}.
```

#### G4 修改 5

- 位置：Methods §4.5.1：Real–Syn 配对一致性
- TeX 行号：331
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
\item \textbf{Intra-group consistency}: For each diagnostic group (AD and CN), we performed paired two-sided $t$-tests to compare the mean standardized uptake values (SUVs) between real and Syn-PET images within each key ROI. The null hypothesis was that the mean difference in SUV between real and synthesized scans is zero. A non-significant result ($p > 0.05$, corrected for multiple comparisons) would indicate high fidelity of Syn-PET to ground-truth PET at the group level.
```

**Revised**

```txt
\item \textbf{Intra-group consistency}: We performed paired two-sided $t$-tests to compare normalized regional uptake between real and Syn-PET images within each ROI, both across the overall cohorts and within individual diagnostic groups. The null hypothesis was that the mean paired difference in normalized regional uptake was zero. Mean paired differences with 95\% confidence intervals, mean absolute error (MAE), Lin's concordance correlation coefficient (CCC), the two-way absolute-agreement single-measure intraclass correlation coefficient (ICC(A,1)), and Bland--Altman bias and 95\% limits of agreement were also calculated to assess regional agreement. For the 16 representative tracer--ROI combinations shown in Fig.~\ref{fig:4}A, B, we additionally performed subject-level ordinary least-squares regression of synthetic on real normalized regional uptake in the overall cohorts, reporting slopes, intercepts, and their unadjusted 95\% confidence intervals.
```

#### G4 修改 6

- 位置：Methods §4.5.1：AD/CN 组间效应量
- TeX 行号：333
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
\item \textbf{Inter-group discriminability}: To assess whether Syn-PET preserves diagnostic signal, we conducted independent two-sided $t$-tests comparing mean SUVs between the AD and CN groups in the same ROIs—first using real PET and then repeating the analysis with Syn-PET. Preservation of statistically significant group differences (e.g., hypometabolism in FDG, elevated amyloid in AV45) in Syn-PET data would demonstrate its capacity to recapitulate clinically meaningful biomarkers.
```

**Revised**

```txt
\item \textbf{Inter-group discriminability}: To assess whether Syn-PET preserves diagnostic signal, we conducted independent two-sided Student's $t$-tests (assuming equal variances) comparing mean normalized regional uptake between the AD and CN groups in the same ROIs—first using real PET and then repeating the analysis with Syn-PET. Cohen's $d$ was calculated separately for real and synthetic PET as the AD--CN mean difference divided by the pooled within-group sample standard deviation, to characterize the direction and magnitude of the group differences.
```

#### G4 修改 7

- 位置：Methods §4.5.1：BH-FDR 的比较族
- TeX 行号：336
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
All statistical tests were two-tailed, and $p$-values were adjusted for multiple ROI comparisons using the false discovery rate (FDR) procedure~\cite{benjamini1995controlling}. This dual-validation framework ensures that Syn-PET not only approximates real PET quantitatively but also retains its discriminative power for early diagnostic stratification.
```

**Revised**

```txt
All $t$-tests were two-tailed, and $p$-values were adjusted for multiple ROI comparisons using the Benjamini--Hochberg false discovery rate (FDR) procedure~\cite{benjamini1995controlling}. For the paired real--synthetic comparisons, FDR correction was applied across 98 ROIs separately for each tracer and analysis group (overall, AD, CN, EMCI, LMCI, and MCI), yielding 12 families (2 tracers $\times$ 6 analysis groups) and 1,176 tests in total. For the AD--CN comparisons, FDR correction was applied across 98 ROIs separately for each tracer and PET type (real or synthetic), yielding four families and 392 tests in total. Statistical significance was defined as an FDR-adjusted $q<0.05$.
```

#### G4 修改 9

- 位置：Discussion
- TeX 行号：186
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
Several limitations of this study present clear avenues for future work. First, the current text guidance relies on fundamental patient information and imaging knowledge. Incorporating additional clinically accessible data, such as blood biomarkers~\cite{hansson2023blood}, could further enhance subject-level precision, necessitating the development of targeted cross-modal pretraining or prompt-learning strategies. Second, while DIReCT$++$ synthesizes $^{18}$F-AV-45 and $^{18}$F-FDG, extending the framework to include tau-PET imaging would provide a more comprehensive biomarker profile for sensitive screening at the preclinical stage. Third, to maximize clinical utility, future iterations could integrate downstream task guidance (e.g., diagnosis or prognosis labels) directly into the generative model, enabling controllable synthesis~\cite{wang2025flexibly,chang2025controllable} tailored for specific clinical decisions. Finally, the evaluation was conducted on well-characterized but limited research cohorts (ADNI, OASIS). Prospective validation on more diverse, real-world clinical populations (including data from thick-slice or low-field MRI~\cite{sorby2024portable}) is essential to fully establish the generalizability and robustness of the framework.
```

**Revised**

```txt
Several limitations of this study present clear avenues for future work. First, the current text guidance relies on fundamental patient information and imaging knowledge. Incorporating additional clinically accessible data, such as blood biomarkers~\cite{hansson2023blood}, could further enhance subject-level precision, necessitating the development of targeted cross-modal pretraining or prompt-learning strategies. Second, while DIReCT$++$ synthesizes $^{18}$F-AV-45 and $^{18}$F-FDG, extending the framework to include tau-PET imaging would provide a more comprehensive biomarker profile for sensitive screening at the preclinical stage. Third, to maximize clinical utility, future iterations could integrate downstream task guidance (e.g., diagnosis or prognosis labels) directly into the generative model, enabling controllable synthesis~\cite{wang2025flexibly,chang2025controllable} tailored for specific clinical decisions. Regional uptake agreement was evaluated using per-image min--max-normalized intensities rather than standardized SUV or SUVR, and clinically interpretable equivalence margins have not yet been established for these measurements. Future work will explore clinically meaningful PET quantification and justified equivalence margins to enable formal equivalence testing. Finally, the evaluation was conducted on well-characterized but limited research cohorts (ADNI, OASIS). Prospective validation on more diverse, real-world clinical populations (including data from thick-slice or low-field MRI~\cite{sorby2024portable}) is essential to fully establish the generalizability and robustness of the framework.
```

#### 补充材料：Sx — 区域一致性与描述性回归（完整 16 行）

- 位置：Supplementary Materials
- TeX 行号：
- 状态：拟新增；编号及最终内容待确认。

Regional uptake agreement and descriptive regression between synthetic and real PET

| Tracer | ROI | N | Mean diff. (95% CI) | MAE | CCC | ICC(A,1) | BA bias (95% LoA) | p | q | OLS slope (95% CI) | OLS intercept (95% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AV45 | L precuneus (1025) | 1365 | +0.00052 \[−0.00056, +0.00159\] | 0.0163 | 0.9863 | 0.9863 | +0.00052 \[−0.0391, +0.0401\] | 0.3445 | 0.9786 | 1.0127 \[1.0038, 1.0215\] | -0.0064 \[-0.0114, -0.0014\] |
| AV45 | R precuneus (2025) | 1365 | +0.00021 \[−0.00079, +0.00120\] | 0.0150 | 0.9887 | 0.9887 | +0.00021 \[−0.0366, +0.0370\] | 0.6846 | 0.9786 | 1.0008 \[0.9928, 1.0088\] | -0.0002 \[-0.0047, +0.0043\] |
| AV45 | L frontal pole (1032) | 1365 | +0.00033 \[−0.00072, +0.00138\] | 0.0157 | 0.9808 | 0.9808 | +0.00033 \[−0.0385, +0.0392\] | 0.5384 | 0.9786 | 1.0037 \[0.9932, 1.0143\] | -0.0012 \[-0.0055, +0.0032\] |
| AV45 | R frontal pole (2032) | 1364 | +0.00039 \[−0.00068, +0.00147\] | 0.0160 | 0.9815 | 0.9815 | +0.00039 \[−0.0392, +0.0400\] | 0.4746 | 0.9786 | 1.0007 \[0.9904, 1.0110\] | +0.0001 \[-0.0042, +0.0045\] |
| AV45 | L temporal pole (1033) | 1365 | −0.00009 \[−0.00117, +0.00099\] | 0.0162 | 0.9591 | 0.9591 | −0.00009 \[−0.0399, +0.0398\] | 0.8769 | 0.9786 | 0.9794 \[0.9640, 0.9947\] | +0.0078 \[+0.0019, +0.0137\] |
| AV45 | R temporal pole (2033) | 1365 | +0.00031 \[−0.00076, +0.00138\] | 0.0163 | 0.9644 | 0.9644 | +0.00031 \[−0.0392, +0.0399\] | 0.5667 | 0.9786 | 1.0087 \[0.9942, 1.0232\] | -0.0032 \[-0.0092, +0.0027\] |
| AV45 | L superior frontal (1028) | 1365 | −0.00037 \[−0.00146, +0.00073\] | 0.0165 | 0.9806 | 0.9807 | −0.00037 \[−0.0407, +0.0400\] | 0.5102 | 0.9786 | 1.0002 \[0.9896, 1.0107\] | -0.0005 \[-0.0058, +0.0049\] |
| AV45 | R superior frontal (2028) | 1365 | +0.00063 \[−0.00041, +0.00168\] | 0.0157 | 0.9822 | 0.9822 | +0.00063 \[−0.0380, +0.0393\] | 0.2354 | 0.9786 | 0.9970 \[0.9869, 1.0071\] | +0.0021 \[-0.0030, +0.0073\] |
| FDG | L precuneus (1025) | 1598 | −0.00003 \[−0.00100, +0.00093\] | 0.0156 | 0.9573 | 0.9573 | −0.00003 \[−0.0386, +0.0385\] | 0.9433 | 0.9774 | 0.9844 \[0.9699, 0.9990\] | +0.0108 \[+0.0006, +0.0209\] |
| FDG | R precuneus (2025) | 1598 | +0.00010 \[−0.00086, +0.00105\] | 0.0156 | 0.9598 | 0.9598 | +0.00010 \[−0.0380, +0.0382\] | 0.8428 | 0.9774 | 0.9983 \[0.9841, 1.0125\] | +0.0013 \[-0.0086, +0.0111\] |
| FDG | L frontal pole (1032) | 1598 | +0.00024 \[−0.00074, +0.00122\] | 0.0160 | 0.9586 | 0.9586 | +0.00024 \[−0.0389, +0.0394\] | 0.6273 | 0.9410 | 1.0039 \[0.9895, 1.0184\] | -0.0019 \[-0.0100, +0.0061\] |
| FDG | R frontal pole (2032) | 1597 | −0.00032 \[−0.00130, +0.00065\] | 0.0159 | 0.9634 | 0.9634 | −0.00032 \[−0.0394, +0.0387\] | 0.5160 | 0.9410 | 1.0041 \[0.9906, 1.0177\] | -0.0026 \[-0.0103, +0.0050\] |
| FDG | L temporal pole (1033) | 1598 | −0.00034 \[−0.00132, +0.00063\] | 0.0159 | 0.9430 | 0.9430 | −0.00034 \[−0.0392, +0.0385\] | 0.4901 | 0.9410 | 0.9934 \[0.9764, 1.0105\] | +0.0023 \[-0.0046, +0.0091\] |
| FDG | R temporal pole (2033) | 1598 | +0.00068 \[−0.00030, +0.00166\] | 0.0161 | 0.9449 | 0.9449 | +0.00068 \[−0.0386, +0.0400\] | 0.1754 | 0.9410 | 0.9902 \[0.9736, 1.0069\] | +0.0047 \[-0.0022, +0.0116\] |
| FDG | L superior frontal (1028) | 1598 | +0.00093 \[−0.00006, +0.00191\] | 0.0159 | 0.9438 | 0.9438 | +0.00093 \[−0.0385, +0.0403\] | 0.0657 | 0.9410 | 1.0101 \[0.9931, 1.0271\] | -0.0052 \[-0.0156, +0.0051\] |
| FDG | R superior frontal (2028) | 1598 | +0.00081 \[−0.00017, +0.00178\] | 0.0158 | 0.9465 | 0.9465 | +0.00081 \[−0.0382, +0.0398\] | 0.1055 | 0.9410 | 1.0020 \[0.9855, 1.0185\] | -0.0004 \[-0.0104, +0.0096\] |

Supplementary Table note（建议）

Regional uptake and error measurements are expressed in arbitrary units after per-image min--max normalization. Mean paired differences and Bland--Altman bias are defined as synthetic minus real PET. The reported BH-FDR-adjusted q-values correspond to 98 ROI comparisons within each tracer-specific overall cohort. OLS regression was performed with real regional uptake as the independent variable and synthetic regional uptake as the dependent variable. Regression slopes and intercepts are accompanied by unadjusted, descriptive 95% confidence intervals. These regression results do not establish clinical SUV or SUVR calibration.


## R2-9. 多重比较校正

### Original

> Multiple-comparison reporting should be clearer: FDR correction is appropriate, but the statistical family, number of tests, and adjusted p/q-values should be reported explicitly.

### Response

We thank the reviewer for the valuable suggestion regarding the transparency of multiple-comparison correction reporting. We agree that, although the original manuscript stated that false discovery rate (FDR) correction was applied, the statistical families, number of tests, and adjusted p/q-values were not sufficiently specified.

To address this concern, we have confirmed the original regional statistical data and performed a systematic re-evaluation of the regional comparisons between real and synthetic PET images.

For the paired regional uptake agreement analysis between real and synthetic PET, we performed two-sided paired t-tests across all 98 regions of interest (ROIs) for each tracer, both in the overall cohorts and within individual diagnostic subgroups. Benjamini–Hochberg FDR correction was applied separately within each statistical family, comprising 12 families and 1,176 regional comparisons in total. The corresponding results for representative brain regions in the overall cohorts, including raw p-values and FDR-adjusted q-values, have been compiled in a new supplementary table.

For the AD versus CN comparisons shown in Figure 4C–F, we additionally performed two-sided independent-samples t-tests separately for AV45 Real, AV45 Syn, FDG Real, and FDG Syn PET. Benjamini–Hochberg FDR correction was applied across all 98 ROIs within each of these four statistical families, comprising 392 comparisons in total.

The re-evaluation showed that all 20 significant annotations in Figure 4C/D remained statistically significant after FDR correction, while all 20 non-significant annotations in Figure 4E/F remained non-significant. Sensitivity analyses using Welch’s t-test did not change the significance classifications of these regions. Thus, the existing significant and non-significant classifications in Figure 4C–F are supported by the FDR-adjusted results and do not require changes.

In the revised manuscript, we will explicitly report the statistical families and corresponding numbers of tests, clarify the FDR correction procedure and significance thresholds in the Statistical Analysis section and the relevant descriptions of Figure 4, and provide adjusted q-values for representative brain regions to improve the transparency and reproducibility of the statistical analysis.

### Modified in Manuscript

#### G4 修改 4

- 位置：Results §2.3：AD/CN 疾病效应与 Cohen's d
- TeX 行号：138
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
Critically, independent-sample $t$-tests demonstrated that the significant differences between diagnostic groups observed in real PET data were precisely preserved in the synthetic images (Fig.~\ref{fig:4}C, D; figs.~\ref{fig:supp_disease_av45} and \ref{fig:supp_disease_fdg}). For instance, DIReCT$++$ recapitulated the statistically significant differences ($p<0.001$) between AD and CN groups in the precuneus for $^{18}$F-AV-45 (Fig.~\ref{fig:4}C) and in the hippocampus for $^{18}$F-FDG (Fig.~\ref{fig:4}D). Similarly, regional differences that were non-significant in real PET data were also consistently non-significant in the synthetic images ($p>0.05$, Fig.~\ref{fig:4}E, F). These findings confirm that DIReCT$++$ reliably preserves the essential biomarker information necessary for clinical differentiation.
```

**Revised**

```txt
Critically, independent-sample $t$-tests demonstrated that the significant differences between diagnostic groups observed in real PET data were also observed in the synthetic images (Fig.~\ref{fig:4}C, D; figs.~\ref{fig:supp_disease_av45} and \ref{fig:supp_disease_fdg}). For instance, DIReCT$++$ recapitulated the statistically significant differences between AD and CN groups in the left precuneus for $^{18}$F-AV-45 (real: $q=7.73\times10^{-66}$; synthetic: $q=1.25\times10^{-63}$; Fig.~\ref{fig:4}C) and in the left hippocampus for $^{18}$F-FDG (real: $q=4.27\times10^{-15}$; synthetic: $q=1.27\times10^{-13}$; Fig.~\ref{fig:4}D). Similarly, regional differences that were non-significant in real PET data remained non-significant in the synthetic images after FDR correction (all $q\geq0.05$ for the regions shown in Fig.~\ref{fig:4}E, F). The AD--CN effect-size directions were consistent between real and synthetic PET for all ten regions shown in Fig.~\ref{fig:4}C, D, although the absolute Cohen's $d$ decreased in nine regions (maximum reduction, 0.0771). These findings support the preservation of group-level disease-related regional uptake patterns, while indicating variations in effect-size magnitude. Complete effect-size estimates and FDR-adjusted results for the displayed regions are provided in Supplementary Table~\ref{tab:regional_effect_sizes}.
```

#### G4 修改 6

- 位置：Methods §4.5.1：AD/CN 组间效应量
- TeX 行号：333
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
\item \textbf{Inter-group discriminability}: To assess whether Syn-PET preserves diagnostic signal, we conducted independent two-sided $t$-tests comparing mean SUVs between the AD and CN groups in the same ROIs—first using real PET and then repeating the analysis with Syn-PET. Preservation of statistically significant group differences (e.g., hypometabolism in FDG, elevated amyloid in AV45) in Syn-PET data would demonstrate its capacity to recapitulate clinically meaningful biomarkers.
```

**Revised**

```txt
\item \textbf{Inter-group discriminability}: To assess whether Syn-PET preserves diagnostic signal, we conducted independent two-sided Student's $t$-tests (assuming equal variances) comparing mean normalized regional uptake between the AD and CN groups in the same ROIs—first using real PET and then repeating the analysis with Syn-PET. Cohen's $d$ was calculated separately for real and synthetic PET as the AD--CN mean difference divided by the pooled within-group sample standard deviation, to characterize the direction and magnitude of the group differences.
```

#### G4 修改 7

- 位置：Methods §4.5.1：BH-FDR 的比较族
- TeX 行号：336
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
All statistical tests were two-tailed, and $p$-values were adjusted for multiple ROI comparisons using the false discovery rate (FDR) procedure~\cite{benjamini1995controlling}. This dual-validation framework ensures that Syn-PET not only approximates real PET quantitatively but also retains its discriminative power for early diagnostic stratification.
```

**Revised**

```txt
All $t$-tests were two-tailed, and $p$-values were adjusted for multiple ROI comparisons using the Benjamini--Hochberg false discovery rate (FDR) procedure~\cite{benjamini1995controlling}. For the paired real--synthetic comparisons, FDR correction was applied across 98 ROIs separately for each tracer and analysis group (overall, AD, CN, EMCI, LMCI, and MCI), yielding 12 families (2 tracers $\times$ 6 analysis groups) and 1,176 tests in total. For the AD--CN comparisons, FDR correction was applied across 98 ROIs separately for each tracer and PET type (real or synthetic), yielding four families and 392 tests in total. Statistical significance was defined as an FDR-adjusted $q<0.05$.
```

#### G4 修改 8

- 位置：Figure 4 Caption
- TeX 行号：143–146
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
\caption{
\textbf{Regional comparison of mean uptake between real and MRI-synthetic PET images.}
(A,B) Violin plots show regional mean uptake across cortical and subcortical regions for real and synthetic PET, comparing AV45 (A) and FDG (B). Statistical significance was assessed for each region. (C–F) Disease-related patterns. Violin plots display mean uptake in AD (red) and CN (green) subjects for selected regions. Each region uses paired half-violins: left (solid) = real PET, right (dashed) = synthetic PET; colors match across modalities. Solid lines indicate real PET significance, dashed lines indicate synthetic PET significance. (C,D) show representative disease-related regions for AV45 and FDG, (E,F) show non–disease-related regions. Cblm-WM denotes Cerebellum-White-Matter. Additional analyses are in the Supplementary Materials.
}
```

**Revised**

```txt
\caption{
\textbf{Regional comparison of mean normalized uptake between real and MRI-synthetic PET images.}
(A,B) Violin plots show regional mean normalized uptake (arbitrary units) across cortical and subcortical regions for real and synthetic PET, comparing AV45 (A) and FDG (B). Statistical significance was assessed for each region. (C--F) AD--CN regional comparisons. Violin plots display mean normalized uptake in AD (red) and CN (green) subjects for selected regions. Each region uses paired half-violins: left (solid) = real PET, right (dashed) = synthetic PET; colors match across modalities. Solid lines indicate real PET significance, dashed lines indicate synthetic PET significance. The statistical annotations in panels (C--F) are consistent with the revised BH-FDR analysis: \texttt{****} corresponds to $q<10^{-4}$ and \texttt{ns} to $q\geq0.05$. (C,D) show representative regions with significant AD--CN differences for AV45 and FDG, whereas (E,F) show selected regions without significant AD--CN differences after FDR correction. Cblm-WM denotes Cerebellum-White-Matter. Additional regional agreement and effect-size analyses are provided in the Supplementary Materials.
}
```

#### 补充材料：Sy — AD/CN 效应量与 FDR（20 行）

- 位置：Supplementary Materials
- TeX 行号：
- 状态：拟新增；编号及最终内容待确认。

AD/CN effect sizes and FDR-adjusted regional comparisons

R2-9 / R3-5 · Figure 4C–F

20 行

新增一张表，报告 Real/Syn 的 AD/CN Cohen's d，以及同一区域各自的 BH-FDR q 值。

第二张表建议采用以下精简结构，数值来自已核验的 R3-5 CSV。

| Panel / Tracer | ROI ID | Real d | Syn d | Real q | Syn q |
| --- | --- | --- | --- | --- | --- |
| C / AV45 | 1025 | 1.6783 | 1.6437 | 7.73e−66 | 1.25e−63 |
| C / AV45 | 1009 | 1.6831 | 1.6337 | 4.68e−66 | 4.74e−63 |
| C / AV45 | 1015 | 1.6482 | 1.6236 | 4.67e−64 | 1.72e−62 |
| C / AV45 | 1030 | 1.5780 | 1.5434 | 5.64e−60 | 8.51e−58 |
| C / AV45 | 1034 | 1.5133 | 1.5288 | 2.84e−56 | 5.61e−57 |
| D / FDG | 1010 | −1.2531 | −1.1774 | 2.69e−48 | 2.10e−43 |
| D / FDG | 2010 | −1.3972 | −1.3201 | 1.18e−57 | 1.94e−52 |
| D / FDG | 1031 | −0.4848 | −0.4308 | 2.14e−9 | 1.10e−7 |
| D / FDG | 17 | −0.6401 | −0.6042 | 4.27e−15 | 1.27e−13 |
| D / FDG | 53 | −0.7518 | −0.7189 | 4.59e−20 | 1.54e−18 |
| E / AV45 | 28 | −0.1050 | −0.0933 | 0.2368 | 0.2858 |
| E / AV45 | 60 | −0.1211 | −0.0986 | 0.1729 | 0.2618 |
| E / AV45 | 53 | −0.0068 | 0.0006 | 0.9373 | 0.9949 |
| E / AV45 | 7 | −0.0745 | −0.1010 | 0.3996 | 0.2529 |
| E / AV45 | 17 | 0.0701 | 0.1232 | 0.4241 | 0.1667 |
| F / FDG | 10 | −0.0097 | 0.0582 | 0.9008 | 0.4667 |
| F / FDG | 49 | −0.0668 | −0.0530 | 0.3964 | 0.4991 |
| F / FDG | 1019 | −0.1294 | −0.0913 | 0.1035 | 0.2506 |
| F / FDG | 1011 | −0.1239 | −0.0978 | 0.1171 | 0.2229 |
| F / FDG | 2013 | −0.0493 | −0.0435 | 0.5303 | 0.5744 |

正式表格还应包含解剖名称与 AD/CN 样本数；具体信息均可直接从 [完整 Cohen's d CSV](https://github.com/linshuijin6/DIRECTPP/blob/main/reports/r3_5_effect_size/figure4_effect_sizes.csv?utm_source=chatgpt.com) 生成，不需要人工重新抄录数据。

新增表注建议

```txt

Cohen's d was calculated separately for real and synthetic PET as the AD--CN mean difference divided by the pooled within-group sample standard deviation. Positive values indicate higher normalized regional uptake in AD than CN. The reported q-values were obtained from the revised two-sided Student's t-test analysis with Benjamini--Hochberg FDR correction across 98 ROIs within each tracer and PET type. All uptake measurements were derived from per-image min--max-normalized PET images and do not represent SUV or SUVR. Differences in Cohen's d do not establish clinical equivalence or non-equivalence.
```


## R2-10. PET 生物标志物一致性

### Original

> PET agreement metrics should be strengthened: SSIM, PSNR, MSE, and MAE are useful image-similarity metrics but are insufficient for biomarker agreement. ICC/CCC, Bland-Altman analysis, regional SUV bias, and calibration analyses would improve clinical validation.

### Response

We thank the reviewer for the valuable suggestion to strengthen the evaluation of PET biomarker agreement. We agree that image-similarity metrics such as SSIM, PSNR, MSE, and MAE alone are insufficient to characterize subject-level regional uptake agreement and systematic differences between synthetic and real PET images.

To address this concern, we performed additional analyses using the original subject-level paired data across all 98 regions of interest (ROIs) for each tracer. Specifically, we calculated Lin’s concordance correlation coefficient (CCC), the intraclass correlation coefficient (ICC(A,1)), mean paired differences with 95% confidence intervals, and Bland–Altman bias and 95% limits of agreement. These complementary metrics provide a more comprehensive assessment of regional errors, subject-level agreement, and systematic differences. Across the 98 ROIs, the median regional CCC values were 0.9745 for AV45 and 0.9450 for FDG.

Furthermore, to examine the relationship between synthetic and real regional uptake values, we conducted subject-level ordinary least-squares regression analyses for the 16 representative tracer–ROI combinations shown in Figure 4A/B. Real PET regional uptake was used as the independent variable and synthetic PET regional uptake as the dependent variable. Regression slopes, intercepts, and their corresponding 95% confidence intervals were calculated.

The regression slopes ranged from 0.9794 to 1.0127 (median: 1.0007) for AV45 and from 0.9844 to 1.0101 (median: 1.0001) for FDG. These representative regions did not exhibit a consistent pattern of linear compression or expansion, although modest deviations from a unit slope were observed in some regions. The regression results provide additional information on how synthetic regional uptake varies with real uptake levels and complement the CCC, ICC, and Bland–Altman analyses.

Importantly, the regional uptake measurements in this study were derived from per-image min–max normalized PET intensities rather than clinically standardized quantitative SUV or SUVR measurements. Therefore, the reported agreement and regression results characterize normalized regional uptake only and should not be interpreted as evidence of clinical SUV/SUVR agreement, absolute quantitative accuracy, or clinically validated calibration. We will explicitly clarify this distinction and its implications in the revised manuscript. Future work will investigate PET synthesis and validation approaches that preserve clinically meaningful quantitative uptake measurements.

In the revised manuscript, we will expand the regional agreement supplementary table to include regression slopes, intercepts, and their 95% confidence intervals for the 16 representative tracer–ROI combinations, alongside the existing agreement and bias metrics. We will also clarify the corresponding statistical methods and limitations.

### Modified in Manuscript

#### G4 修改 1

- 位置：Results §2.3：区域摄取值定义
- TeX 行号：119
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
To assess the clinical validity of the synthesized PET images, we parcellated both synthetic and real PET scans into anatomical regions using \texttt{mri\_synthseg} (FreeSurfer v7.4.1)~\cite{fischl2012freesurfer,dalca2022synthseg}, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and \textit{aseg} atlases. This approach yielded a total of 98 distinct regions of interest (ROIs), including cortical, subcortical, cerebellar, and brainstem structures. Regional standardized uptake value  (SUV) were computed by extracting the mean tracer uptake within each ROI and normalizing to the cerebellar gray matter (for \textsuperscript{18}F-AV-45 PET) or the pons (for \textsuperscript{18}F-FDG PET). Fig.~\ref{fig:3} illustrates this analysis for key ROIs in two representative ADNI subjects, demonstrating strong regional consistency between synthetic and real images, as well as clear distinctions between syntheses from different diagnostic groups.
```

**Revised**

```txt
To assess the clinical validity of the synthesized PET images, we parcellated both synthetic and real PET scans into anatomical regions using \texttt{mri\_synthseg} (FreeSurfer v7.4.1)~\cite{fischl2012freesurfer,dalca2022synthseg}, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and \textit{aseg} atlases. This approach yielded a total of 98 distinct regions of interest (ROIs), including cortical, subcortical, cerebellar, and brainstem structures. Regional normalized uptake values (arbitrary units) were computed as the mean voxel intensity within each ROI from PET images normalized using per-image min--max intensity scaling. Fig.~\ref{fig:3} illustrates this analysis for key ROIs in two representative ADNI subjects, demonstrating strong regional consistency between synthetic and real images, as well as clear distinctions between syntheses from different diagnostic groups.
```

#### G4 修改 3

- 位置：Results §2.3：Real–Syn 区域一致性
- TeX 行号：136
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
Paired-sample $t$-tests between synthetic and real images revealed no statistically significant differences in mean SUV across all principal brain regions for the CN, MCI, and AD groups ($p>0.05$; Fig.~\ref{fig:4}A, B; figs.~\ref{fig:supp_av45_1}, \ref{fig:supp_av45_2}, \ref{fig:supp_fdg_1}, and \ref{fig:supp_fdg_2}). This high fidelity was consistent for both $^{18}$F-AV-45 (Fig.~\ref{fig:4}A) and $^{18}$F-FDG (Fig.~\ref{fig:4}B), indicating that DIReCT$++$ effectively captures the regional characteristics of the ground truth.
```

**Revised**

```txt
Paired-sample $t$-tests between synthetic and real images revealed no statistically significant differences in normalized regional uptake across the principal brain regions shown in Fig.~\ref{fig:4}A, B for the overall cohorts of both tracers ($p>0.05$). Across all 98 ROIs, no overall comparisons remained significant after Benjamini--Hochberg false discovery rate (FDR) correction (all $q>0.05$). Among the diagnosis-stratified paired comparisons, only the right pericalcarine cortex (ROI 2021) in the $^{18}$F-FDG MCI subgroup showed a significant mean paired difference after FDR correction ($q=0.0481$). The median concordance correlation coefficients (CCC) across the 98 ROIs were 0.9745 for $^{18}$F-AV-45 and 0.9450 for $^{18}$F-FDG, with corresponding median mean absolute errors (MAE) of 0.0160 and 0.0159 (normalized intensity units). For the 16 representative tracer--ROI combinations in Fig.~\ref{fig:4}A, B, descriptive regression slopes ranged from 0.9794 to 1.0127 (median, 1.0007) for $^{18}$F-AV-45 and from 0.9844 to 1.0101 (median, 1.0001) for $^{18}$F-FDG, without a consistent direction of deviation from unity. These results indicate close agreement in normalized regional uptake between synthetic and real PET, with detailed statistics for the representative ROIs provided in Supplementary Table~\ref{tab:regional_agreement}.
```

#### G4 修改 5

- 位置：Methods §4.5.1：Real–Syn 配对一致性
- TeX 行号：331
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
\item \textbf{Intra-group consistency}: For each diagnostic group (AD and CN), we performed paired two-sided $t$-tests to compare the mean standardized uptake values (SUVs) between real and Syn-PET images within each key ROI. The null hypothesis was that the mean difference in SUV between real and synthesized scans is zero. A non-significant result ($p > 0.05$, corrected for multiple comparisons) would indicate high fidelity of Syn-PET to ground-truth PET at the group level.
```

**Revised**

```txt
\item \textbf{Intra-group consistency}: We performed paired two-sided $t$-tests to compare normalized regional uptake between real and Syn-PET images within each ROI, both across the overall cohorts and within individual diagnostic groups. The null hypothesis was that the mean paired difference in normalized regional uptake was zero. Mean paired differences with 95\% confidence intervals, mean absolute error (MAE), Lin's concordance correlation coefficient (CCC), the two-way absolute-agreement single-measure intraclass correlation coefficient (ICC(A,1)), and Bland--Altman bias and 95\% limits of agreement were also calculated to assess regional agreement. For the 16 representative tracer--ROI combinations shown in Fig.~\ref{fig:4}A, B, we additionally performed subject-level ordinary least-squares regression of synthetic on real normalized regional uptake in the overall cohorts, reporting slopes, intercepts, and their unadjusted 95\% confidence intervals.
```

#### G4 修改 9

- 位置：Discussion
- TeX 行号：186
- 状态：G4 合并讨论方案，尚待最终确认。

**Original**

```txt
Several limitations of this study present clear avenues for future work. First, the current text guidance relies on fundamental patient information and imaging knowledge. Incorporating additional clinically accessible data, such as blood biomarkers~\cite{hansson2023blood}, could further enhance subject-level precision, necessitating the development of targeted cross-modal pretraining or prompt-learning strategies. Second, while DIReCT$++$ synthesizes $^{18}$F-AV-45 and $^{18}$F-FDG, extending the framework to include tau-PET imaging would provide a more comprehensive biomarker profile for sensitive screening at the preclinical stage. Third, to maximize clinical utility, future iterations could integrate downstream task guidance (e.g., diagnosis or prognosis labels) directly into the generative model, enabling controllable synthesis~\cite{wang2025flexibly,chang2025controllable} tailored for specific clinical decisions. Finally, the evaluation was conducted on well-characterized but limited research cohorts (ADNI, OASIS). Prospective validation on more diverse, real-world clinical populations (including data from thick-slice or low-field MRI~\cite{sorby2024portable}) is essential to fully establish the generalizability and robustness of the framework.
```

**Revised**

```txt
Several limitations of this study present clear avenues for future work. First, the current text guidance relies on fundamental patient information and imaging knowledge. Incorporating additional clinically accessible data, such as blood biomarkers~\cite{hansson2023blood}, could further enhance subject-level precision, necessitating the development of targeted cross-modal pretraining or prompt-learning strategies. Second, while DIReCT$++$ synthesizes $^{18}$F-AV-45 and $^{18}$F-FDG, extending the framework to include tau-PET imaging would provide a more comprehensive biomarker profile for sensitive screening at the preclinical stage. Third, to maximize clinical utility, future iterations could integrate downstream task guidance (e.g., diagnosis or prognosis labels) directly into the generative model, enabling controllable synthesis~\cite{wang2025flexibly,chang2025controllable} tailored for specific clinical decisions. Regional uptake agreement was evaluated using per-image min--max-normalized intensities rather than standardized SUV or SUVR, and clinically interpretable equivalence margins have not yet been established for these measurements. Future work will explore clinically meaningful PET quantification and justified equivalence margins to enable formal equivalence testing. Finally, the evaluation was conducted on well-characterized but limited research cohorts (ADNI, OASIS). Prospective validation on more diverse, real-world clinical populations (including data from thick-slice or low-field MRI~\cite{sorby2024portable}) is essential to fully establish the generalizability and robustness of the framework.
```

#### 补充材料：Sx — 区域一致性与描述性回归（完整 16 行）

- 位置：Supplementary Materials
- TeX 行号：
- 状态：拟新增；编号及最终内容待确认。

Regional uptake agreement and descriptive regression between synthetic and real PET

| Tracer | ROI | N | Mean diff. (95% CI) | MAE | CCC | ICC(A,1) | BA bias (95% LoA) | p | q | OLS slope (95% CI) | OLS intercept (95% CI) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AV45 | L precuneus (1025) | 1365 | +0.00052 \[−0.00056, +0.00159\] | 0.0163 | 0.9863 | 0.9863 | +0.00052 \[−0.0391, +0.0401\] | 0.3445 | 0.9786 | 1.0127 \[1.0038, 1.0215\] | -0.0064 \[-0.0114, -0.0014\] |
| AV45 | R precuneus (2025) | 1365 | +0.00021 \[−0.00079, +0.00120\] | 0.0150 | 0.9887 | 0.9887 | +0.00021 \[−0.0366, +0.0370\] | 0.6846 | 0.9786 | 1.0008 \[0.9928, 1.0088\] | -0.0002 \[-0.0047, +0.0043\] |
| AV45 | L frontal pole (1032) | 1365 | +0.00033 \[−0.00072, +0.00138\] | 0.0157 | 0.9808 | 0.9808 | +0.00033 \[−0.0385, +0.0392\] | 0.5384 | 0.9786 | 1.0037 \[0.9932, 1.0143\] | -0.0012 \[-0.0055, +0.0032\] |
| AV45 | R frontal pole (2032) | 1364 | +0.00039 \[−0.00068, +0.00147\] | 0.0160 | 0.9815 | 0.9815 | +0.00039 \[−0.0392, +0.0400\] | 0.4746 | 0.9786 | 1.0007 \[0.9904, 1.0110\] | +0.0001 \[-0.0042, +0.0045\] |
| AV45 | L temporal pole (1033) | 1365 | −0.00009 \[−0.00117, +0.00099\] | 0.0162 | 0.9591 | 0.9591 | −0.00009 \[−0.0399, +0.0398\] | 0.8769 | 0.9786 | 0.9794 \[0.9640, 0.9947\] | +0.0078 \[+0.0019, +0.0137\] |
| AV45 | R temporal pole (2033) | 1365 | +0.00031 \[−0.00076, +0.00138\] | 0.0163 | 0.9644 | 0.9644 | +0.00031 \[−0.0392, +0.0399\] | 0.5667 | 0.9786 | 1.0087 \[0.9942, 1.0232\] | -0.0032 \[-0.0092, +0.0027\] |
| AV45 | L superior frontal (1028) | 1365 | −0.00037 \[−0.00146, +0.00073\] | 0.0165 | 0.9806 | 0.9807 | −0.00037 \[−0.0407, +0.0400\] | 0.5102 | 0.9786 | 1.0002 \[0.9896, 1.0107\] | -0.0005 \[-0.0058, +0.0049\] |
| AV45 | R superior frontal (2028) | 1365 | +0.00063 \[−0.00041, +0.00168\] | 0.0157 | 0.9822 | 0.9822 | +0.00063 \[−0.0380, +0.0393\] | 0.2354 | 0.9786 | 0.9970 \[0.9869, 1.0071\] | +0.0021 \[-0.0030, +0.0073\] |
| FDG | L precuneus (1025) | 1598 | −0.00003 \[−0.00100, +0.00093\] | 0.0156 | 0.9573 | 0.9573 | −0.00003 \[−0.0386, +0.0385\] | 0.9433 | 0.9774 | 0.9844 \[0.9699, 0.9990\] | +0.0108 \[+0.0006, +0.0209\] |
| FDG | R precuneus (2025) | 1598 | +0.00010 \[−0.00086, +0.00105\] | 0.0156 | 0.9598 | 0.9598 | +0.00010 \[−0.0380, +0.0382\] | 0.8428 | 0.9774 | 0.9983 \[0.9841, 1.0125\] | +0.0013 \[-0.0086, +0.0111\] |
| FDG | L frontal pole (1032) | 1598 | +0.00024 \[−0.00074, +0.00122\] | 0.0160 | 0.9586 | 0.9586 | +0.00024 \[−0.0389, +0.0394\] | 0.6273 | 0.9410 | 1.0039 \[0.9895, 1.0184\] | -0.0019 \[-0.0100, +0.0061\] |
| FDG | R frontal pole (2032) | 1597 | −0.00032 \[−0.00130, +0.00065\] | 0.0159 | 0.9634 | 0.9634 | −0.00032 \[−0.0394, +0.0387\] | 0.5160 | 0.9410 | 1.0041 \[0.9906, 1.0177\] | -0.0026 \[-0.0103, +0.0050\] |
| FDG | L temporal pole (1033) | 1598 | −0.00034 \[−0.00132, +0.00063\] | 0.0159 | 0.9430 | 0.9430 | −0.00034 \[−0.0392, +0.0385\] | 0.4901 | 0.9410 | 0.9934 \[0.9764, 1.0105\] | +0.0023 \[-0.0046, +0.0091\] |
| FDG | R temporal pole (2033) | 1598 | +0.00068 \[−0.00030, +0.00166\] | 0.0161 | 0.9449 | 0.9449 | +0.00068 \[−0.0386, +0.0400\] | 0.1754 | 0.9410 | 0.9902 \[0.9736, 1.0069\] | +0.0047 \[-0.0022, +0.0116\] |
| FDG | L superior frontal (1028) | 1598 | +0.00093 \[−0.00006, +0.00191\] | 0.0159 | 0.9438 | 0.9438 | +0.00093 \[−0.0385, +0.0403\] | 0.0657 | 0.9410 | 1.0101 \[0.9931, 1.0271\] | -0.0052 \[-0.0156, +0.0051\] |
| FDG | R superior frontal (2028) | 1598 | +0.00081 \[−0.00017, +0.00178\] | 0.0158 | 0.9465 | 0.9465 | +0.00081 \[−0.0382, +0.0398\] | 0.1055 | 0.9410 | 1.0020 \[0.9855, 1.0185\] | -0.0004 \[-0.0104, +0.0096\] |

Supplementary Table note（建议）

Regional uptake and error measurements are expressed in arbitrary units after per-image min--max normalization. Mean paired differences and Bland--Altman bias are defined as synthetic minus real PET. The reported BH-FDR-adjusted q-values correspond to 98 ROI comparisons within each tracer-specific overall cohort. OLS regression was performed with real regional uptake as the independent variable and synthetic regional uptake as the dependent variable. Regression slopes and intercepts are accompanied by unadjusted, descriptive 95% confidence intervals. These regression results do not establish clinical SUV or SUVR calibration.


## R2-13. 单步采样术语不准确

### Original

> One-step sampling terminology requires correction: The phrase “exact one-step sampling” is too strong for a distilled end-point predictor. The manuscript should distinguish exact ODE integration from learned one-step approximation.

### Response

We thank the reviewer for pointing out the imprecision in our description of one-step sampling. We agree that the continuous ODE process underlying rectified flow should be distinguished from the learned one-step approximation employed in DIReCT++.

Specifically, DIReCT++ generates the target PET image directly from the input MRI in a single forward pass, which does not imply exact integration of the underlying ODE. Accordingly, we will revise the expression "exact one-step sampling" to more accurately describe the learned one-step generation process.

### Modified in Manuscript

#### 来源：[R2-13正文修改](https://app.notion.com/p/0fc95d43b2dd8370b0ac81535a429e1a)

##### 一、Methods §4.2.3 — 单步采样的理论表述

LaTeX 第 283 行 · Multi-Task Learning and One-Step Generation

###### 修改 1

- 位置：Methods §4.2.3 — 单步采样的理论表述
- TeX 行号：283

Original

> A key advantage of rectified flow is its ability to support exact one-step sampling.

Revised

A key advantage of rectified flow is its potential to support efficient one-step generation through distillation.

##### 二、Methods §4.2.3 — Eq. (7) 的引出语句

LaTeX 第 286 行

###### 修改 2

- 位置：Methods §4.2.3 — Eq. (7) 的引出语句
- TeX 行号：286

Original

> Mathematically, the generation process is expressed as:

Revised

Mathematically, this learned one-step approximation is expressed as:


## R2-15. Equation (1) 及参数敏感性

### Original

> Equation (1) needs stronger justification: The semantic-similarity constraint between FDG and AV45 embeddings may conflict with the stated goal of preserving inter-tracer differences. A sensitivity analysis for τ and an explicit ablation are recommended.

### Response

We thank the reviewer for the valuable comments regarding the rationale and parameter sensitivity of the cross-tracer semantic similarity constraint. We agree that its design motivation and its role in balancing text–PET feature alignment and tracer-specific representations warrant further clarification.

In DIReCT++, we employ a pre-trained BiomedCLIP model to encode the textual descriptions of FDG and AV45, followed by two independent affine adapters that align the corresponding textual embeddings with their respective PET image features. However, optimizing only the individual text–PET alignment objectives may cause the two adapted guidance vectors to become highly similar, potentially diminishing the inter-tracer distinctions present in the original textual representations. We therefore introduce a cross-tracer similarity constraint, not to maximize the similarity between the two representations, but to regulate their relative similarity during feature alignment.

Regarding the selection of τ=0.82, we would like to clarify its specific basis. Before affine adaptation, the cosine similarity between the original FDG and AV45 textual embeddings produced by the pre-trained BiomedCLIP model was 0.8205374, which rounds to 0.82. Accordingly, we selected τ=0.82 as the target cross-tracer similarity, using the original relationship between the two textual representations as a reference. This allows the adapters to align the textual embeddings with their corresponding PET image features while maintaining approximately the relative similarity originally encoded by BiomedCLIP. Thus, τ=0.82 was not an arbitrarily assigned value, but was determined from the representational characteristics of the pre-trained text encoder.

We also acknowledge that Equation (1) in the original manuscript presented a simplified inequality constraint to convey the underlying design principle of cross-tracer semantic consistency. In the actual adapter optimization, this principle was implemented using a differentiable squared penalty, `100 × (cos(z_FDG, z_AV45) − τ)²`, which encourages the cosine similarity between the adapted tracer embeddings to approach the specified target τ. This formulation penalizes deviations both above and below the target, thereby preventing the two tracer representations from becoming increasingly similar without constraint during text–PET alignment. We will clarify the implemented optimization objective and the rationale for selecting τ in the revised manuscript.

To further validate this design, we conducted additional adapter-level parameter sensitivity and cross-tracer constraint ablation experiments. Using identical two-fold data splits, original text and PET features, initialization procedures, and optimization settings, we evaluated τ values of 0.70, 0.82, 0.90, and 0.98, together with an additional configuration in which the cross-tracer similarity penalty was completely removed.

The results demonstrate that τ effectively regulates the relative similarity between the adapted tracer guidance vectors. As τ increased from 0.70 to 0.98, the mean cosine similarity between the adapted FDG and AV45 embeddings increased from 0.7032 to 0.9807. At the originally adopted τ=0.82, the resulting similarities were 0.8213 and 0.8215 for the two folds, respectively, closely matching the specified target. In contrast, removing the cross-tracer penalty increased these similarities to 0.9900 and 0.9894, indicating that optimizing text–PET alignment alone caused the two guidance vectors to become highly similar.

Further analysis showed that the individual text–PET feature alignment also increased with τ. At τ=0.82, the mean alignment similarities were 0.9687 for FDG and 0.9661 for AV45. Although removing the cross-tracer constraint further increased these alignment values, it simultaneously brought the cosine similarity between the two adapted tracer embeddings close to 0.99. These findings indicate that maximizing individual text–PET alignment does not necessarily preserve the original representational distinctions between tracers. Instead, the cross-tracer similarity term provides a controllable mechanism for balancing individual feature alignment and inter-tracer representational separation.

Therefore, the rationale for selecting τ=0.82 is to use the original similarity between the BiomedCLIP textual representations as a reference, maintaining substantial text–PET feature alignment while preventing the two adapted guidance vectors from becoming excessively similar.

The additional experiments directly demonstrate the influence of τ on adapter-level representation learning and the relative geometry of the tracer embeddings. Since these analyses focus on the representation level rather than retraining PET synthesis models under different τ settings, we present them as supporting evidence for the parameter selection and similarity constraint mechanism, rather than as an optimization study of PET synthesis performance.

We will incorporate the rationale for τ=0.82, the actual optimization formulation, and the additional sensitivity and ablation results into the revised manuscript to improve the methodological clarity and reproducibility of our approach.

**核查提示：** 清单已勾选，但主页面状态仍标为待定；参数及历史实现的表述需作者最终确认。

### Modified in Manuscript

#### 来源：[R2-15回复及正文修改](https://app.notion.com/p/40995d43b2dd80d79c0ee3144ba8cb2e)

##### 修改一：Methods — Domain-Adapted VLM

位置： `BMEF_main.tex` 第 229–241 行，Equation (1) 及相邻说明。

这里需要同时处理两项差异：原稿采用 `sim ≥ τ` 的简化表述，而实际使用目标相似度平方惩罚；原稿采用与平均 PET 特征比较的记号，而实际代码计算的是逐受试者文本–PET 余弦相似度的均值。

###### 修改 1

- 位置：Methods — Domain-Adapted VLM
- TeX 行号：229–241

Original

```txt
where $\alpha_1, \beta_1 $ are learnable scalar weights and $\alpha_2, \beta_2 $ are learnable bias vectors. We choose scalar scaling rather than full linear projection to minimize trainable parameters and avoid overfitting, given the limited size of medical imaging datasets. The optimal parameters are obtained by solving a constrained optimization problem:
\begin{equation}
\begin{aligned}
& \underset{Adapt_f,\, Adapt_a}{\arg \min} \quad
   \mathcal{L}_{\text{align}} = \big(1 - \operatorname{sim}(Adapt_f(c_f), \mathbb{E}[f_f])\big) + \big(1 - \operatorname{sim}(Adapt_a(c_a), \mathbb{E}[f_a])\big) \\
& \text{subject to} \quad
   \operatorname{sim}\big(Adapt_f(c_f), Adapt_a(c_a)\big) \geq \tau,
\end{aligned}
\label{eq:align_opt}
\end{equation}
where $\operatorname{sim}(\cdot, \cdot)$ denotes cosine similarity, and $\tau \in [0,1]$ is a predefined threshold. The constraint ensures the cross-modality guidance vectors maintain a certain level of semantic consistency.

By solving~\eqref{eq:align_opt}, we obtain the modality-specific guidance vectors $Adapt_f(c_f)$ and $Adapt_a(c_a)$, which are subsequently used to steer the rectified flow translation process in a domain-informed manner.
```

Revised

```txt
where $\alpha_1, \beta_1 $ are learnable scalar weights and $\alpha_2, \beta_2 $ are learnable bias vectors. We choose scalar scaling rather than full linear projection to minimize trainable parameters and avoid overfitting, given the limited size of medical imaging datasets. The optimal parameters are obtained by minimizing the following objective:
\begin{equation}
\begin{aligned}
\mathcal{L}_{\text{align}} ={}&
-\frac{1}{N_f}\sum_{i=1}^{N_f}
\operatorname{sim}\big(Adapt_f(c_f), f_{f,i}\big) \\
&-\frac{1}{N_a}\sum_{j=1}^{N_a}
\operatorname{sim}\big(Adapt_a(c_a), f_{a,j}\big) \\
&+\lambda_{\text{cross}}
\left[
\operatorname{sim}\big(Adapt_f(c_f), Adapt_a(c_a)\big)-\tau
\right]^2,
\end{aligned}
\label{eq:align_opt}
\end{equation}
where $\operatorname{sim}(\cdot,\cdot)$ denotes cosine similarity, $f_{f,i}$ and $f_{a,j}$ denote the normalized PET image features of individual FDG and AV45 training subjects, and $N_f$ and $N_a$ are the corresponding numbers of available features. We set $\lambda_{\text{cross}}=100$ and $\tau=0.82$, the latter corresponding to the cosine similarity of the original FDG and AV45 BiomedCLIP textual embeddings (0.8205) before affine adaptation. The cross-tracer penalty encourages the adapted guidance vectors to retain approximately this reference similarity while being aligned with their respective PET image features, thereby regulating their relative representational separation.

By solving~\eqref{eq:align_opt}, we obtain the modality-specific guidance vectors $Adapt_f(c_f)$ and $Adapt_a(c_a)$, which are subsequently used to steer the rectified flow translation process in a domain-informed manner.
```

修改理由：

- 保留原稿关于两个独立 affine adapters 的结构与解释。
- 将概念性不等式改为实际优化使用的平方惩罚目标。
- 明确 \\(\\tau=0.82\\) 来源于适配前两种文本向量的余弦相似度 0.8205。
- 使图文对齐项与实际的逐受试者余弦均值计算一致。
- 保留原有公式标签 `eq:align_opt`，不影响后续交叉引用。

这部分不需要在正文额外解释为什么原稿采用简化形式。相关说明已经在 Response 中给出，正文只需准确呈现方法。

##### 修改二：Results — The DIReCT++ Framework for Precision PET Synthesis

位置： `BMEF_main.tex` 第 88 行之后，紧接介绍 BiomedCLIP prompt learning 的段落。

这里建议保留整个原段落，仅在其后补充两句结果。

###### 修改 2

- 位置：Results — The DIReCT++ Framework for Precision PET Synthesis
- TeX 行号：88

Original

> To achieve subject-wise precision, text guidance incorporating both common knowledge (e.g., general descriptions of PET tracers) and personal patient information (e.g., age, gender, clinical scores) is encoded by a pre-trained VLM and integrated into the RF model via cross-attention. We fine-tune the VLM from BiomedCLIP using a straightforward prompt learning strategy (Fig.\~\\refB). This strategy maximizes the intra-tracer alignment between text and image embeddings while preserving the inherent inter-tracer differences, reflecting the distinct yet complementary molecular activities captured by \$\^18\$F-AV-45 and \$\^18\$F-FDG PET.

Revised

原段落完整保留，在其后新增：

```txt
An additional adapter-level sensitivity analysis showed that varying $\tau$ from 0.70 to 0.98 changed the mean cross-tracer embedding similarity from 0.7032 to 0.9807. At the adopted $\tau=0.82$, the similarity was 0.8214, compared with 0.9897 when the cross-tracer penalty was removed, demonstrating its role in regulating inter-tracer representational similarity (Table~\ref{tab:supp_tau_adapter}).
```

修改理由：

只报告关键发现，不在主文重复五组实验的全部指标。新增表格放在 Supplementary Materials 中，供审稿人检查。

这里刻意使用 adapter-level sensitivity analysis 和 embedding similarity，避免将新增表示层结果误写成 PET 合成性能比较。

##### 修改三：Supplementary Materials — 新增 Adapter 消融结果

位置： `manuscript/supplementary/supplementary.tex`，建议放在现有软件依赖表之后，即补充材料末尾。

###### 修改 3

- 位置：Supplementary Materials — 新增 Adapter 消融结果
- TeX 行号：

Original

该位置没有对应原文，为新增内容。现有补充材料的末项是软件依赖表，原有内容全部保留。

Revised

建议新增一张表格：

```txt
\begin{table}[htbp]
\caption{\textbf{Adapter-level sensitivity analysis of the cross-tracer similarity constraint.}
Values are descriptive means across two folds. FDG and AV45 alignment denote the mean cosine similarity between each adapted tracer embedding and the corresponding individual PET image features. The cross-tracer similarity is the cosine similarity between the two adapted tracer embeddings. The analysis used 1,856 QC-filtered ADNI subjects. Only training-fold PET features were used for adapter optimization, and held-out features were used solely for evaluation. No cross-term indicates complete removal of the cross-tracer penalty.}
\label{tab:supp_tau_adapter}
\centering
\small
\begin{tabular}{lccccc}
\toprule
\textbf{Setting} &
\multicolumn{2}{c}{\textbf{Training alignment}} &
\multicolumn{2}{c}{\textbf{Held-out alignment}} &
\textbf{Cross-tracer} \\
 & FDG & AV45 & FDG & AV45 & similarity \\
\midrule
$\tau=0.70$ & 0.9437 & 0.9410 & 0.9436 & 0.9410 & 0.7032 \\
$\tau=0.82$ & 0.9687 & 0.9661 & 0.9687 & 0.9661 & 0.8214 \\
$\tau=0.90$ & 0.9838 & 0.9813 & 0.9838 & 0.9812 & 0.9018 \\
$\tau=0.98$ & 0.9948 & 0.9923 & 0.9948 & 0.9923 & 0.9807 \\
No cross-term & 0.9952 & 0.9927 & 0.9952 & 0.9926 & 0.9897 \\
\bottomrule
\end{tabular}
\end{table}
```

修改理由：

该表包含完整的五组 Adapter 实验，直接对应 R2-15 的参数敏感性与约束消融要求。数据采用两折描述性均值，保留了训练折与留出折的区别。

你已经生成的 `tau_sensitivity.png` 也可以作为补充图，但我认为目前新增这张表已经能够支撑正文中的结果描述，没有必要为了这一条意见扩大图表修改范围。


## R2-20. 临床应用主张过强

### Original

> Clinical translation claims should be moderated: Statements regarding widespread screening, clinically actionable biomarkers, and early intervention exceed the evidence from retrospective ADNI/OASIS cohorts. Prospective, diverse, multi-center clinical validation is needed before such claims are justified.

### Response

We appreciate the reviewer's thoughtful suggestions regarding the clinical translation of our work.

One of the primary motivations of DIReCT++ is to explore the feasibility of synthesizing multi-tracer PET images from routine MRI, potentially alleviating the challenges associated with PET acquisition costs, radiation exposure, and limited accessibility. Our evaluations on the ADNI and OASIS-3 datasets provide preliminary evidence of the framework's PET synthesis performance, while regional uptake analyses and downstream classification on ADNI further support its potential clinical relevance.

Nevertheless, translating these findings from retrospective research cohorts into clinical practice requires more comprehensive evidence. We agree with the reviewer that the current results are insufficient to support the direct application of synthetic PET in routine clinical screening or treatment decision-making. Accordingly, we will moderate statements regarding widespread screening, clinically actionable biomarkers, and early intervention to better distinguish the demonstrated findings from potential future clinical applications. We will also clarify that prospective validation in more diverse, real-world clinical populations remains necessary.

**核查提示：** Discussion 第 177 行旧方案含 “widespread screening roughly”，与弱化临床筛查主张的意图不一致；需在 G7 整合时重审。

### Modified in Manuscript

#### 来源：[R2-20正文修改](https://app.notion.com/p/0c495d43b2dd82848aad018dc525c2d2)

##### 一、Introduction — 研究贡献总结

LaTeX 第 81 行，Introduction 最后一段

###### 修改 1

- 位置：Introduction
- TeX 行号：81

Original

> Our work establishes a translational paradigm for precision biomarker synthesis, offering a scalable and data-efficient tool for early intervention in dementia.

Revised

Our work proposes a translational approach to precision biomarker synthesis, offering a scalable and data-efficient strategy with potential applications in the early assessment of dementia.

##### 二、Discussion — 临床意义段落

LaTeX 第 175 行，Discussion 第三段

这一段是 R2-20 最需要修改的位置。

##### 修改 1：临床研究价值

###### 修改 2

- 位置：Discussion
- TeX 行号：175

Original

> Beyond its technical merits, the primary significance of DIReCT++ lies in its potential to democratize access to critical biomarker profiling, thereby addressing a major bottleneck in the early and precise management of dementia.

Revised

Beyond its technical merits, the primary significance of DIReCT++ lies in its potential to improve access to biomarker-related imaging information, thereby addressing a major challenge in the early assessment of dementia.

##### 修改 2：直接临床应用

###### 修改 3

- 位置：Discussion
- TeX 行号：175

Original

> By generating accurate proxies for both amyloid and metabolic PET from a single routine MRI scan, our framework effectively translates the gold-standard biological definition of AD into a scalable tool for clinical practice.

Revised

By generating synthetic estimates of both amyloid and metabolic PET from a single routine MRI scan, our framework offers a scalable approach for multimodal imaging research.

##### 修改 3：临床可行性证据

###### 修改 4

- 位置：Discussion
- TeX 行号：175

Original

> The clinical viability of this approach is strongly evidenced by our results on personalized MCI diagnosis and stratification (Fig. 5B, C), where the combination of MRI and synthetic multi-tracer PET achieved performance comparable to the resource-intensive ideal of MRI with real PET, significantly outperforming models using MRI or real PET alone.

Revised

The potential clinical relevance of this approach is supported by the observed consistency of disease-related regional uptake patterns between synthetic and real PET (Figs. 3 and 4), as well as by our results on personalized MCI diagnosis and stratification (Fig. 5B, C), where the combination of MRI and synthetic multi-tracer PET achieved performance comparable to MRI with real PET and outperformed models using MRI or real PET alone.

##### 三、Discussion — 临床应用展望

LaTeX 第 177 行，Discussion 第四段

##### 修改 4：临床筛查及治疗候选者识别

###### 修改 5

- 位置：Discussion
- TeX 行号：177

Original

> It could enable widespread screening of individuals at the preclinical or prodromal stages in primary care settings, identifying those with underlying AD pathology who are most likely to benefit from disease-modifying therapies.

Revised

It could enable widespread screening roughly for individuals at the preclinical or prodromal stages in primary care settings, and provide a basis for exploring more accessible assessment strategies.

##### 修改 5：临床工作流程

###### 修改 6

- 位置：Discussion
- TeX 行号：177

Original

> DIReCT++ thus moves us closer to a future where multi-modal diagnostic precision is accessible as part of the standard clinical workflow, unconstrained by current resource limitations.

Revised

DIReCT++ thus offers a potential foundation for more accessible multi-modal imaging approaches in future clinical workflows.

##### 四、Discussion — 方法价值总结

LaTeX 第 179 行，Discussion 第五段

##### 修改 6：Clinically actionable biomarkers

###### 修改 7

- 位置：Discussion
- TeX 行号：179

Original

> DIReCT++ moves beyond this by achieving precise generation of subject-specific biomarkers that are clinically actionable.

Revised

DIReCT++ moves beyond this by achieving precise generation of subject-specific PET images that recapitulate disease-related regional uptake patterns.

##### 五、Discussion — Conclusion

LaTeX 第 188 行，Discussion 最后一段

这两句建议一并修改，且整合此前 R2-4 已确认的 MCI stage discrimination 相关修改。

##### 修改 7：研究结论

###### 修改 8

- 位置：Discussion
- TeX 行号：188

Original

> By generating clinically actionable biomarkers that enable accurate diagnosis and prognostic stratification of MCI, our work effectively bridges the gap between the biological definition of AD and its clinical application.

Revised

By generating synthetic PET images that support diagnostic classification and discrimination between MCI stages, our work offers a potential approach to bridging the gap between the biological definition of AD and its clinical application.

修改理由： 保留原来的句式及“连接 AD 生物学研究与临床应用”这一科学意义，但将其定位于潜在应用，而非已经实现的临床诊断能力。

##### 修改 8：早期干预

###### 修改 9

- 位置：Discussion
- TeX 行号：188

Original

> DIReCT++ represents a significant step toward scalable, accessible, and precise tools for early intervention in neurodegenerative disorders.

Revised

DIReCT++ represents a step toward scalable, accessible, and precise tools for early assessment of neurodegenerative disorders.

修改理由： 将 early intervention 调整为 early assessment，使结论与本研究以影像合成和下游分类为核心的验证范围更加一致。


# Reviewer 3 — Major

## R3-3. 横断面分层不等于预后预测

### Original

"Prognostic stratification" is not supported by the analysis.

EMCI vs. LMCI is a cross-sectional severity distinction based on a memory cutoff, not a prognostic outcome. The manuscript also describes LMCI as indicating "proximity to dementia conversion" and MCI-U as lacking "clear progression status" (lines 360-362), which conflates the two concepts. To justify the title and the claims in lines 178-181 and 249-250, the authors should perform a genuine prognostic analysis: progressive vs. stable MCI (pMCI/sMCI) over a defined follow-up (e.g., 36 months), with time-to-conversion modeling (Cox regression, C-index). Otherwise, "prognostic" and "stratification" should be removed from the title and claims.

### Response

We thank the reviewer for further highlighting the important distinction between MCI stage discrimination and longitudinal prognostic prediction.

Our original motivation for relating EMCI/LMCI classification to disease progression was based on previous studies examining the clinical characteristics and subsequent conversion risks associated with these two MCI stages (Aisen et al., 2015; Lin et al., 2022; Petersen, 2021). Accordingly, we included EMCI-versus-LMCI classification as a downstream task to investigate the performance of synthetic PET in fine-grained MCI stage stratification.

We agree that EMCI and LMCI in our study were defined according to baseline memory impairment, and that we did not perform progressive-versus-stable MCI (pMCI/sMCI) classification or time-to-conversion analysis based on longitudinal follow-up outcomes. Therefore, the current experiments do not establish the model's ability to predict longitudinal disease progression.

However, we would like to clarify that stratification in our study refers to grouping MCI patients according to their current degree of cognitive impairment, rather than stratification according to future disease-conversion risk. To avoid ambiguity, we will remove or revise unsupported prognostic claims throughout the manuscript and clarify that the task concerns MCI stage stratification. We will also revise the descriptions in the Methods section that characterize LMCI as indicating proximity to dementia conversion and MCI-U as lacking clear progression status, ensuring that the group definitions accurately reflect the cross-sectional classification criteria used in our study.

Accordingly, we will revise the manuscript title to “Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stage Stratification” to clarify the scope of the stratification task.

**核查提示：** 与 R2-4 对 Methods §4.5.2 标题提出不同版本；最终标题应在归组修改中统一。

### Modified in Manuscript

#### 来源：[R3-3正文修改](https://app.notion.com/p/51895d43b2dd838dbc088101b7eab8e2)

##### 三、Methods §4.3：修正 EMCI、LMCI 和 MCI-U 的定义

这是 R2-4 与 R3-3 的共同修改点。此前已确认的方案在此直接沿用，不重复提出新的修改方向。

##### 1. LMCI 的定义

###### 修改 1

- 位置：Methods §4.3：修正 EMCI、LMCI 和 MCI-U 的定义
- TeX 行号：295

Original — 第 295 行

> To account for the heterogeneity of MCI, we further subclassified individuals based on delayed recall performance on the WMS-R Logical Memory II Story A task: Early MCI (EMCI; \$n = 291\$) denoted a milder impairment stage, whereas Late MCI (LMCI; \$n = 152\$) indicated proximity to dementia conversion.

Revised

To account for the heterogeneity of MCI, we further subclassified individuals based on delayed recall performance on the WMS-R Logical Memory II Story A task: Early MCI (EMCI; \$n = 291\$) denoted a milder impairment stage, whereas Late MCI (LMCI; \$n = 152\$) denoted a more severe impairment stage.

只修改 LMCI 的解释，不改变分类依据、人数或句式结构。

##### 2. MCI-U 的定义

###### 修改 2

- 位置：Methods §4.3
- TeX 行号：

Original

> The remaining MCI participants without clear progression status were grouped as MCI-unclassified (MCI-U; \$n = 520\$).

Revised

The remaining MCI participants not classified as EMCI or LMCI were grouped as MCI-unclassified (MCI-U; \$n = 520\$).

这里应删除 without clear progression status，因为 MCI-U 在本文中指未被归入 EMCI 或 LMCI 的受试者，而不是缺乏纵向疾病进展结局的患者。

四、Methods §4.5.2：明确分类任务的含义

##### 1. 小节标题

###### 修改 3

- 位置：Methods §4.5.2：明确分类任务的含义
- TeX 行号：

Original

> `\subsubsection{Diagnosis and Prognostic Stratification}`

Revised

```txt
\subsubsection{Diagnosis and MCI Stage Discrimination}
```

这里保留 Discrimination，因为本节描述的是具体分类实验；论文总标题使用 MCI Stage Stratification，二者并不矛盾。

##### 2. 第一段首句

###### 修改 4

- 位置：Methods §4.5.2：明确分类任务的含义
- TeX 行号：

Original

> To rigorously evaluate the clinical utility of synthesized PET (Syn-PET) images, we assessed their capacity to support diagnostic and prognostic classification across the AD continuum.

Revised

To rigorously evaluate the clinical utility of synthesized PET (Syn-PET) images, we assessed their capacity to support diagnostic classification and MCI stage discrimination across the AD continuum.

##### 3. EMCI/LMCI 分类的描述

###### 修改 5

- 位置：Methods §4.5.2：明确分类任务的含义
- TeX 行号：

Original

> Specifically, we trained identical DenseNet classifiers\~\\cite to discriminate between three clinically salient diagnostic pairs: (1) AD versus CN individuals, a canonical diagnostic boundary; (2) MCI versus CN, representing early disease detection; and (3) EMCI versus late MCI (LMCI), a prognostic distinction reflecting differential progression risk.

Revised

Specifically, we trained identical DenseNet classifiers\~\\cite to discriminate between three clinically salient diagnostic pairs: (1) AD versus CN individuals, a canonical diagnostic boundary; (2) MCI versus CN, representing early disease detection; and (3) EMCI versus late MCI (LMCI), representing different degrees of memory impairment.

只替换最后一个任务的解释，不改动前两个分类任务或 DenseNet 的方法描述。

##### 4. 本节最后的比较框架

###### 修改 6

- 位置：Methods §4.5.2：明确分类任务的含义
- TeX 行号：344

Original — 第 344 行

> This comparative framework enables a direct assessment of whether Syn-PET preserves the discriminative biomarker information encoded in real PET, and whether multi-tracer Syn-PET enhances early stratification beyond single-modality or MRI-only approaches.

Revised

This comparative framework enables a direct assessment of whether Syn-PET preserves the discriminative biomarker information encoded in real PET, and whether multi-tracer Syn-PET enhances downstream diagnostic classification and MCI stage stratification beyond single-modality or MRI-only approaches.

#### 论文标题（来自英文 Response）

- 位置：Title
- TeX 行号：

**Original**

来源未列出。

**Revised**

Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stage Stratification

**核查提示：** 标题是否保留 stratification 仍待最终确认。


## R3-14. 临床定位和过度结论

### Original

Clinical positioning and overstatement.

The Discussion makes strong claims: "democratize access," "primary care screening," "qualitative leap," "new paradigm," and identifying candidates "most likely to benefit from disease-modifying therapies" (lines 208-234). Synthetic amyloid images cannot substitute for molecular confirmation, particularly for anti-amyloid therapy eligibility, where a false positive has real consequences. The authors should:

temper these claims;

discuss the 2024 revised Alzheimer's Association criteria, which define AD biologically by core biomarkers;

compare against, or at least discuss, plasma biomarkers such as p-tau217, which are now a low-cost, radiation-free route to amyloid status. They are mentioned only as a future prompt input (lines 236-237).

### Response

We thank the reviewer for the valuable suggestions regarding the clinical positioning of our study and the interpretation of its potential applications.

We agree that the clinical translation claims in the original manuscript should be moderated. Our study evaluated PET image synthesis, regional uptake patterns, and downstream classification performance using retrospective research cohorts, but did not directly establish the effectiveness of synthetic PET for routine clinical screening or treatment decision-making. Accordingly, we will revise the overstated claims regarding widespread clinical screening, identification of candidates for disease-modifying therapies, and transformative clinical impact. We will also clarify that synthetic PET cannot currently substitute for established molecular biomarker confirmation.

We also appreciate the reviewer’s suggestion to contextualize our work within the latest AD diagnostic framework. The 2024 revised Alzheimer’s Association criteria further emphasize the biological definition of AD based on core biomarkers and recognize the diagnostic role of blood-based biomarkers, including plasma p-tau217 assays that meet appropriate performance requirements. We have expanded the Discussion to address this updated diagnostic framework, highlight the importance of these biomarkers in assessing AD pathology, and further clarify the current research positioning of DIReCT++.

**核查提示：** 关联正文修改子页面为空；相关 R2-20 修改可供参考，但此处没有独立正文方案。

# Minor Comments

## Minor-1. 语法

### Original

> Line 57: "This challenges stems" → "This challenge stems."

### Response

We thank the reviewer for pointing out this grammatical error. We have corrected “This challenges stems” to “This challenge stems” in the revised manuscript.

**核查提示：** 第 77 行与 Minor-2 为同一句，须采用合并后的唯一版本。

### Modified in Manuscript

#### 来源：主页面

Minor-1 — Introduction 语法修正

`BMEF_main.tex` 第 77 行，Introduction 第二段

###### 修改 1

- 位置：Introduction
- TeX 行号：77

Original

> This challenges stems from the inherent nature of MRI-to-PET synthesis as an ill-posed inverse problem; neurodegenration visible on MRI is typically a downstream effect of prior molecular pathologies captured by PET\~\\cite.

Revised

This challenge stems from the inherent nature of MRI-to-PET synthesis as an ill-posed inverse problem; neurodegeneration visible on MRI is typically a downstream effect of prior molecular pathologies captured by PET\~\\cite.


## Minor-2. 拼写

### Original

> Lines 58-59: "neurodegenration" → "neurodegeneration."

### Response

We thank the reviewer for identifying this typographical error. We have corrected “neurodegenration” to “neurodegeneration” in the revised manuscript.

**核查提示：** 第 77 行与 Minor-1 为同一句；此处 Original 已包含 Minor-1 修改，并非最初原稿。

### Modified in Manuscript

#### 来源：主页面

Minor-2 — Introduction 拼写修正

`BMEF_main.tex` 第 77 行，Introduction 第二段

###### 修改 1

- 位置：Introduction
- TeX 行号：77

Original（已包含 Minor-1 确认的修改）

> This challenge stems from the inherent nature of MRI-to-PET synthesis as an ill-posed inverse problem; neurodegenration visible on MRI is typically a downstream effect of prior molecular pathologies captured by PET\~\\cite.

Revised

This challenge stems from the inherent nature of MRI-to-PET synthesis as an ill-posed inverse problem; neurodegeneration visible on MRI is typically a downstream effect of prior molecular pathologies captured by PET\~\\cite.


## Minor-3. SUV/SUVR 术语

### Original

> Line 137: "standardized uptake value (SUV) were" → "values (SUVRs) were."

### Response

Thank you for pointing out this grammatical and terminology issue. We agree that the original wording was imprecise. Upon reviewing the regional uptake analysis, we confirmed that the reported measurements represent mean regional intensities extracted from min–max-normalized PET images, rather than standardized uptake values (SUVs) or reference-region–normalized uptake ratios (SUVRs).

Therefore, directly replacing “SUV” with “SUVR” would not accurately reflect the measurements performed in this study. We will correct the grammatical error and use the more appropriate term “normalized regional uptake” in the revised manuscript, while ensuring consistent terminology and units in the corresponding figures.

**核查提示：** 第 119 行与 G4 及 Minor-7 重叠；分别保留现有方案，待统一合并。

### Modified in Manuscript

#### 来源：主页面

Minor-3 — 正文修改方案（尚未实施）

位置：`BMEF_main.tex` 第 119 行，Results → Recapitulation of Disease-Specific Biomarker Patterns，第三句。

###### 修改 1

- 位置：Results → Recapitulation of Disease-Specific Biomarker Patterns
- TeX 行号：119

Original

```latex
Regional standardized uptake value  (SUV) were computed by extracting the mean tracer uptake within each ROI and normalizing to the cerebellar gray matter (for \textsuperscript{18}F-AV-45 PET) or the pons (for \textsuperscript{18}F-FDG PET).
```

Revised

```latex
Regional normalized uptake values were computed by extracting the mean voxel intensity within each ROI from min--max-normalized PET images.
```

修改理由：纠正单复数语法；将不符合实际计算方法的 SUV/SUVR 术语改为 normalized regional uptake；删除未经实际分析证实的小脑灰质和脑桥参考区归一化表述。前后句不变，其他 SUV/SUVR 术语和 Figure 4 纵坐标分别在 R3-5、Minor-19 中处理。


## Minor-4. 速度场的数学符号

### Original

> Line 301: "a learnable velocity field Vθ denotes the network parameters" is garbled; θ and c should be defined separately.

### Response

We thank the reviewer for identifying the unclear notation. We will clarify that \\(V\_\\theta\\) denotes the learnable velocity field and \\(\\theta\\) its network parameters. We will also use \\(\\mathbf\{c\}\\) consistently for the conditioning context, retaining its component-wise definition in the subsequent formulation.

**核查提示：** 来源中数学符号存在破损，按原样保留，需对照论文源文件核查，不能直接用于 LaTeX。

### Modified in Manuscript

#### 来源：主页面

Minor-4 — 正文修改方案

`BMEF_main.tex` 第 245 行，Methods → Rectified Flow；已写入候选修订稿 `BMEF_main_minor4_revised.tex`

###### 修改 1

- 位置：Methods → Rectified Flow
- TeX 行号：245

Original

> Specifically, given two heterogeneous medical distributions---\$\\mathbf0 \\sim \\mathcal\}\$ and \$\\mathbf1 \\sim \\mathcal\}\$ (multi-tracer)---we model the transformation between them via a learnable velocity field \$V\_\\theta\$ denotes the network parameters and \$c\$ encodes modality-specific contextual cues (e.g., anatomical priors or clinical metadata).

Revised

Specifically, given two heterogeneous medical distributions---\$\\mathbf0 \\sim \\mathcal\}\$ and \$\\mathbf1 \\sim \\mathcal\}\$ (multi-tracer)---we model the transformation between them via a learnable velocity field \$V\_\\theta\$, where \$\\theta\$ denotes the network parameters.


## Minor-6. Temporoparietal junction 不是明确 atlas ROI

### Original

> Line 427: "Temporoparietal junction" is not a SynthSeg/Desikan-Killiany label. Please specify the ROIs actually used.

### Response

We thank the reviewer for pointing out the inconsistency between the anatomical terminology and the atlas labels used in our analysis. In the original manuscript, we used the general anatomical term “temporoparietal junction,” which does not correspond to a distinct ROI label in the adopted atlas and may have caused ambiguity regarding the regions actually analyzed.

To clarify this issue, we re-examined the original ROI statistical analysis and Figure 4 plotting code and confirmed the specific regions used. For FDG-PET, the selected regions included the bilateral hippocampus (Left/Right-Hippocampus), isthmus cingulate cortex (ctx-lh/rh-isthmuscingulate), and supramarginal gyrus (ctx-lh/rh-supramarginal). For AV45-PET, the selected regions included the bilateral precuneus (ctx-lh/rh-precuneus) and the inferior, middle, superior, and transverse temporal gyri (ctx-lh/rh-inferiortemporal, middletemporal, superiortemporal, and transversetemporal).

Accordingly, we will replace the imprecise or overly broad anatomical descriptions with the corresponding atlas labels and clearly distinguish the full ROI-based statistical analysis from the representative disease-related regions presented in Figure 4. These revisions will ensure that the Methods section accurately reflects the regions used in the analysis and the corresponding figures.

**核查提示：** 第 326 行与 Minor-13 重叠，以合并方案为基础审核，勿重复覆盖。

### Modified in Manuscript

#### 来源：主页面

修改位置： `BMEF_main.tex` 第 326 行，Methods → Statistical Analysis → Regional Group-Wise Comparison。
###### 修改 1

- 位置：Methods → Statistical Analysis → Regional Group-Wise Comparison
- TeX 行号：326

original：
`Among these, we prioritized a set of AD-relevant regions: for metabolic assessment with \textsuperscript{18}F-FDG PET, the bilateral hippocampus, temporoparietal junction, and posterior cingulate cortex ~\cite{mueller2005alzheimers}; and for amyloid burden evaluation with \textsuperscript{18}F-AV45 PET, the precuneus, frontal lobes, and temporal lobes~\cite{wong2010in}.`
revised:

```txt
Among the 98 anatomical ROIs, we selected representative disease-related regions for the comparisons shown in Fig.~\ref{fig:4}C,D.

For \textsuperscript{18}F-FDG PET, these included the bilateral hippocampus (\texttt{Left-Hippocampus} and \texttt{Right-Hippocampus}), isthmus cingulate cortex (\texttt{ctx-lh-isthmuscingulate} and \texttt{ctx-rh-isthmuscingulate}), and supramarginal gyrus (\texttt{ctx-lh-supramarginal} and \texttt{ctx-rh-supramarginal})~\cite{mueller2005alzheimers}.

For \textsuperscript{18}F-AV45 PET, these included the bilateral precuneus (\texttt{ctx-lh-precuneus} and \texttt{ctx-rh-precuneus}) and the bilateral inferior, middle, superior, and transverse temporal gyri (corresponding to the \texttt{ctx-lh-} and \texttt{ctx-rh-} labels with the suffixes \texttt{inferiortemporal}, \texttt{middletemporal}, \texttt{superiortemporal}, and \texttt{transversetemporal})~\cite{wong2010in}.
```


## Minor-7. SynthSeg 名称与引用不一致

### Original

> Line 133 vs. line 390: "mri\_synthseg (FreeSurfer v7.4.1)" and "SynthSeg \[35\]" cite different references for the same tool. Please use one version and one citation.

### Response

We thank the reviewer for pointing out the inconsistent nomenclature and citations for the brain parcellation method across the manuscript. We acknowledge that the use of “mri\_synthseg (FreeSurfer v7.4.1)” and “SynthSeg” in different sections, together with inconsistent references, may have caused confusion.

To address this issue, we will consistently refer to the ROI parcellation method as SynthSeg and standardize its citation throughout the manuscript. We will also clearly distinguish the FreeSurfer-based skull-stripping step from SynthSeg-based brain parcellation and clarify that the ROI masks derived from T1-weighted MRI were used for regional PET analysis. These revisions will ensure a consistent and accurate description of the preprocessing and ROI analysis procedures.

**核查提示：** Results 第 119 行与 G4 区域摄取定义修改重叠，且关于 SynthSeg 分割对象的表述不同；须合并为唯一版本。

### Modified in Manuscript

#### 来源：[M7正文修改](https://app.notion.com/p/40795d43b2dd8025b837db224bcb3515)

##### 位置一：Results → Section 2.3，第 119 行

###### 修改 1

- 位置：Results → Section 2.3
- TeX 行号：119

Original

> To assess the clinical validity of the synthesized PET images, we parcellated both synthetic and real PET scans into anatomical regions using `\texttt{mri\_synthseg}` (FreeSurfer v7.4.1)`~\cite{fischl2012freesurfer,dalca2022synthseg}`, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and `\textit{aseg}` atlases.

Revised

To assess the clinical validity of the synthesized PET images, we parcellated the corresponding T1-weighted MRI scans using SynthSeg`~\cite{synthseg}`, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and `\textit{aseg}` atlases, and applied the resulting ROI masks to both synthetic and real PET images.

修改原因： 统一使用 SynthSeg 名称及单一引用，并明确实际流程是对 T1 MRI 进行脑区分割，再将 ROI 掩码应用于真实和合成 PET，而非分别对 PET 执行 SynthSeg 分割。

##### 位置二：Methods → Materials and Data Preprocessing，第 301 行

###### 修改 2

- 位置：Methods → Materials and Data Preprocessing
- TeX 行号：301

Original

> For quantitative regional analysis, brain parenchyma was parcellated into 98 anatomical structures using SynthSeg`~\cite{synthseg}`.

Revised

For quantitative regional analysis, T1-weighted MRI scans were parcellated into 98 anatomical regions using SynthSeg`~\cite{synthseg}`, and the resulting ROI masks were applied to the spatially aligned PET images.

修改原因： 将分割对象明确为 T1-weighted MRI，并补充 ROI 掩码在 PET 区域分析中的实际用途，与 Results 的修改保持一致。

##### 参考文献处理

目前原稿存在三个 SynthSeg 引用键：`fischl2012freesurfer`、`dalca2022synthseg`、`synthseg`。

这里暂以 `\cite{synthseg}` 作为统一引用键，因为 Methods 两处已经使用它。但当前没有 `references.bib`，尚不能确认该键对应的条目是否准确。 统一合并时需要检查对应文献的作者、题名及重复条目，尤其是审稿人另行指出的 Billot 作者姓名错误。


## Minor-8. 重复引用

### Original

> Refs. 27 and 33 are duplicates (Fischl, FreeSurfer).

### Response

We thank the reviewer for identifying the duplicate reference. We have confirmed that References 27 and 33 refer to the same FreeSurfer publication. We will merge the duplicate entries and standardize the corresponding citations in the revised manuscript to ensure accuracy and consistency.

**核查提示：** 第 119 行与 Minor-7 和 G4 重叠；待整合。

### Modified in Manuscript

#### 来源：主页面

R3 Minor-8 — 正文修改方案

M8 与已讨论的 M7 直接关联，不需要额外改写正文，只需合并重复的 FreeSurfer 参考文献并统一引用。

##### 位置一： `BMEF_main.tex` 第 119 行，Results → Section 2.3。

###### 修改 1

- 位置：Results → Section 2.3
- TeX 行号：119

Original

> To assess the clinical validity of the synthesized PET images, we parcellated both synthetic and real PET scans into anatomical regions using `\texttt{mri\_synthseg}` (FreeSurfer v7.4.1)`~\cite{fischl2012freesurfer,dalca2022synthseg}`, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and `\textit{aseg}` atlases.

Revised（沿用 M7 已讨论的方案）

To assess the clinical validity of the synthesized PET images, we parcellated the corresponding T1-weighted MRI scans using SynthSeg`~\cite{synthseg}`, a deep learning-based segmentation tool that provides high-resolution cortical and subcortical labeling consistent with the Desikan--Killiany and `\textit{aseg}` atlases, and applied the resulting ROI masks to both synthetic and real PET images.


## Minor-9. 参考文献作者姓名

### Original

> Ref. 35: "Billot C" should be "Billot B."

### Response

We thank the reviewer for identifying the incorrect author name in Reference 35. We have verified that the first author is Benjamin Billot and will correct “Billot C” to “Billot B” in the revised manuscript.

### Modified in Manuscript

#### 来源：主页面

R3 Minor-9 — 正文修改方案

修改位置： References，第 35 条，SynthSeg 方法文献。

###### 修改 1

- 位置：References
- TeX 行号：

Original

> Billot C, Greve DN, Puonti O, et al. SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining. Med. Image Anal. 2023;86:102789.

Revised

35\. Billot B, Greve DN, Puonti O, et al. SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining. Med. Image Anal. 2023;86:102789.


## Minor-10. 文献 28

### Original

> Ref. 28: author list and title should be verified.

### Response

We thank the reviewer for identifying the inaccuracies in Reference 28. Upon verification, we found that its author list, title, and publication details were inconsistent with the official SynthSeg publication. We will remove the incorrect entry and consistently cite the correct SynthSeg paper by Billot et al., published in Medical Image Analysis in 2023, to ensure the accuracy and consistency of the references.

### Modified in Manuscript

#### 来源：主页面

R3 Minor-10 — 参考文献修改方案

本条与 M7、M9 的修改直接关联。建议删除错误的参考文献 28，统一保留正确的 SynthSeg 文献，不再新增重复条目。

##### 位置一：References，原第 28、35 条

###### 修改 1

- 位置：References
- TeX 行号：

Original

> Dalca AV, Petit E, Billot B, et al. SynthSeg: Domain randomization for segmentation of brain scans of any contrast and resolution. Med. Image Anal. 2022;80:102480.

> Billot C, Greve DN, Puonti O, et al. SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining. Med. Image Anal. 2023;86:102789.

Revised

删除原第 28 条，将原第 35 条更正并保留为唯一的 SynthSeg 方法文献：

Billot B, Greve DN, Puonti O, et al. SynthSeg: Segmentation of brain MRI scans of any contrast and resolution without retraining. Medical Image Analysis. 2023;86:102789. [https://doi.org/10.1016/j.media.2023.102789](https://doi.org/10.1016/j.media.2023.102789?utm_source=chatgpt.com).


## Minor-11. 文献 26 格式

### Original

> Ref. 26: author formatting is garbled ("Xingchao Liu Chengyue Gong QL").

### Response

We thank the reviewer for identifying the author formatting error in Reference 26. We have verified that the correct authors are Xingchao Liu, Chengyue Gong, and Qiang Liu. We will correct the author list and update the reference to the officially published ICLR 2023 version to ensure accuracy and consistency.

### Modified in Manuscript

#### 来源：主页面

R3 Minor-11 — 参考文献修改方案

本条仅涉及参考文献 26 的作者格式及出版信息，不需要修改正文内容。

修改位置： References，第 26 条。

###### 修改 1

- 位置：References
- TeX 行号：

Original

> Xingchao Liu Chengyue Gong QL. Flow straight and fast: Learning to generate and transfer data with rectified flow. ArXiv Prepr. ArXiv220903003 2022.

Revised

Liu X, Gong C, Liu Q. Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow. International Conference on Learning Representations (ICLR). 2023.


## Minor-12. SPM 引用

### Original

> Ref. 34 (a gray-matter asymmetry protocol) is not an appropriate citation for SPM spatial normalization.

### Response

We thank the reviewer for pointing out the inappropriate citation for SPM. The original reference primarily describes voxel-wise gray matter asymmetry analysis rather than the SPM software used for spatial normalization, and it’s our mistake. We will replace it with an authoritative reference for SPM and its associated methods to ensure that the citation accurately reflects the neuroimaging preprocessing tool used in our study.

### Modified in Manuscript

#### 来源：主页面

R3 Minor-12 — 正文修改方案

位置： `BMEF_main.tex` 第 301 行，Methods → Materials and Data Preprocessing。

###### 修改 1

- 位置：Methods → Materials and Data Preprocessing
- TeX 行号：301

Original

> Both modalities were jointly affinely normalized to the MNI152 standard space using `SPM~\cite{spm}`, with identical transformation matrices applied to preserve cross-modality alignment.

Revised

`Both modalities were jointly affinely normalized to the MNI152 standard space using SPM~\cite{spm}, with identical transformation matrices applied to preserve cross-modality alignment~\cite{friston1995spatial}.`

参考文献修改：`reference.bib.txt` 第 325–333 行

###### 修改 2

- 位置：References.reference.bib.txt
- TeX 行号：

Original：

```txt
@article{spm,
  title = {A 12-step user guide for analyzing voxel-wise gray matter asymmetries in statistical parametric mapping ({{SPM}})},
  author = {Kurth, Florian and Gaser, Christian and Luders, Eileen},
  year = 2015,
  journal = {Nat. Protoc.},
  volume = {10},
  pages = {293--304},
  keywords = {/unread}
}
```

Revised：

```txt
@book{spm,
  title = {Statistical Parametric Mapping: The Analysis of Functional Brain Images},
  editor = {Friston, Karl J. and Ashburner, John and Kiebel, Stefan J. and Nichols, Thomas E. and Penny, William D.},
  publisher = {Academic Press},
  year = {2007},
  isbn = {9780123725608}
}

@article{friston1995spatial,
  title   = {Spatial Registration and Normalization of Images},
  author  = {Friston, Karl J. and Ashburner, John and
             Frith, Christopher D. and Poline, Jean-Baptiste and
             Heather, John D. and Frackowiak, Richard S. J.},
  journal = {Human Brain Mapping},
  volume  = {3},
  number  = {3},
  pages   = {165--189},
  year    = {1995},
  doi     = {10.1002/hbm.460030303}
}
```


## Minor-13. FDG 易损区域引用

### Original

> Ref. 36 (an ADNI overview) is not an appropriate source for FDG AD-vulnerable regions.

### Response

We thank the reviewer for pointing out the inappropriate citation for AD-vulnerable regions in FDG-PET. We acknowledge that the original reference primarily describes the Alzheimer's Disease Neuroimaging Initiative (ADNI) and does not directly support the regional metabolic alterations discussed in our study.

To address this issue, we will replace the original citation with more relevant FDG-PET studies, including Mosconi et al. on hippocampal hypometabolism, He et al. on AD-related regional metabolic abnormalities, and Strom et al. on metabolic alterations involving the isthmus cingulate region. These references provide a more appropriate scientific basis for the selected disease-related regions.

**核查提示：** 第 326 行与 Minor-6 重叠；此处记载为合并方案。

### Modified in Manuscript

#### 来源：主页面

R3 Minor-13 — 正文及参考文献修改方案

本条与 M6 的 ROI 名称修订直接关联。建议在 M6 的候选修改基础上，仅替换 FDG-PET 疾病相关区域的引用文献，保留 AV45-PET 的原有引用及 ROI 统计分析方法。

修改位置： `BMEF_main.tex` 第 326 行，Methods → Statistical Analysis → Regional Group-Wise Comparison。

###### 修改 1

- 位置：Methods → Statistical Analysis → Regional Group-Wise Comparison
- TeX 行号：326

Original

```txt
Among these, we prioritized a set of AD-relevant regions: for metabolic assessment with \textsuperscript{18}F-FDG PET, the bilateral hippocampus, temporoparietal junction, and posterior cingulate cortex ~\cite{mueller2005alzheimers}; and for amyloid burden evaluation with \textsuperscript{18}F-AV45 PET, the precuneus, frontal lobes, and temporal lobes~\cite{wong2010in}.
```

Revised（整合 M6 与 M13）

```txt
Among the 98 anatomical ROIs, we selected representative disease-related regions for the comparisons shown in Fig.~\ref{fig:4}C,D.

For \textsuperscript{18}F-FDG PET, these included the bilateral hippocampus (\texttt{Left-Hippocampus} and \texttt{Right-Hippocampus}), isthmus cingulate cortex (\texttt{ctx-lh-isthmuscingulate} and \texttt{ctx-rh-isthmuscingulate}), and supramarginal gyrus (\texttt{ctx-lh-supramarginal} and \texttt{ctx-rh-supramarginal})~\cite{mosconi2005reduced,he2015meta,strom2022cortical}.

For \textsuperscript{18}F-AV45 PET, these included the bilateral precuneus (\texttt{ctx-lh-precuneus} and \texttt{ctx-rh-precuneus}) and the bilateral inferior, middle, superior, and transverse temporal gyri (corresponding to the \texttt{ctx-lh-} and \texttt{ctx-rh-} labels with the suffixes \texttt{inferiortemporal}, \texttt{middletemporal}, \texttt{superiortemporal}, and \texttt{transversetemporal})~\cite{wong2010in}.
```

##### 需要新增的 BibTeX 文献

当前 `reference.bib.txt` 中不存在这三篇文献，建议在统一修改时增补：

| 建议引用键 | 文献 | DOI |
| --- | --- | --- |
| `mosconi2005reduced` | Mosconi et al. Reduced hippocampal metabolism in MCI and AD: automated FDG-PET image analysis. Neurology. 2005;64(11):1860–1867. | `10.1212/01.WNL.0000163856.13524.08` |
| `he2015meta` | He et al. Meta-analytic comparison between PIB-PET and FDG-PET results in Alzheimer's disease and MCI. Cell Biochem Biophys. 2015;71(1):17–26. | `10.1007/s12013-014-0138-7` |
| `strom2022cortical` | Strom et al. Cortical hypometabolism reflects local atrophy and tau pathology in symptomatic Alzheimer's disease. Brain. 2022;145(2):713–728. | `10.1093/brain/awab294` |


## Minor-14. 3D DDIM 引用

### Original

> Ref. 25 (MRI-to-CT for spinal segmentation) should be checked as the source for the 3D DDIM baseline.

### Response

We thank the reviewer for pointing out the inappropriate reference for the 3D DDIM baseline. We re-examined the original experimental code and confirmed that our baseline was not based on the implementation by Graf et al. Instead, it was implemented using the 3D DiffusionModelUNet provided by MONAI GenerativeModels, with DDIMScheduler employed for accelerated sampling. We will remove the inappropriate citation to Graf et al. and replace it with the original DDIM paper by Song et al. and an appropriate reference for MONAI GenerativeModels. We will also clarify the implementation framework and sampling procedure of the 3D conditional diffusion baseline to ensure that the methodological description and references accurately reflect the experimental implementation.

### Modified in Manuscript

#### 来源：主页面

##### 位置一： `BMEF_main.tex` 第 101 行，Results → Superior Fidelity and Generalizability of Synthesized PET。

###### 修改 1

- 位置：Results → Superior Fidelity and Generalizability of Synthesized PET
- TeX 行号：101

Original

```txt
We rigorously evaluated the multi-tracer PET synthesis performance of DIReCT$++$ against a comprehensive suite of representative methods, including generative adversarial networks (CycleGAN~\cite{zhu2017unpaired}), transformer-based architectures (Swin-UNet~\cite{Cao2021swin}), and diffusion/flow-based models (SegGuidedDif ~\cite{konz2024anatomically}, 3D DDIM~\cite{Graf2023}, 3D RF ~\cite{Xing2022}), alongside our baseline model, DIReCT~\cite{liu2025direct}, which performs mono-tracer generation without prompt adaptation.
```

Revised

```txt
We rigorously evaluated the multi-tracer PET synthesis performance of DIReCT$++$ against a comprehensive suite of representative methods, including generative adversarial networks (CycleGAN~\cite{zhu2017unpaired}), transformer-based architectures (Swin-UNet~\cite{Cao2021swin}), and diffusion/flow-based models (SegGuidedDif ~\cite{konz2024anatomically}, 3D DDIM~\cite{song2021ddim}, 3D RF ~\cite{Xing2022}), alongside our baseline model, DIReCT~\cite{liu2025direct}, which performs mono-tracer generation without prompt adaptation.
```

此处只替换引用键，不修改实验叙述。

##### 位置二： `BMEF_main.tex` 第 316 行，Methods → Competing Methods。

###### 修改 2

- 位置：Methods → Competing Methods
- TeX 行号：316

Original

```txt
\item \textbf{3D DDIM}~\cite{Graf2023}: A deterministic fast-sampling variant of 3D diffusion models, included to assess DIReCT$++$’s computational efficiency and sampling quality relative to accelerated diffusion approaches.
```

Revised

```txt
\item \textbf{3D DDIM}: A 3D conditional diffusion baseline implemented using the \texttt{DiffusionModelUNet} and \texttt{DiffusionInferer} components of MONAI GenerativeModels (v0.2.3)~\cite{pinaya2023generative}, with \texttt{DDIMScheduler}~\cite{song2021ddim} employed for accelerated sampling. This baseline was included to assess DIReCT$++$'s computational efficiency and sampling quality relative to accelerated diffusion approaches.
```

这段修改明确交代了模型架构、软件实现来源和采样方法，并保留该基线原有的比较目的，没有暗示使用了 Graf 的代码。

##### 对应参考文献修改

在 `reference.bib.txt` 中，建议移除 `Graf2023` 的错误关联，新增两项。

DDIM 原始方法：

```txt
@inproceedings{song2021ddim,
  title = {Denoising Diffusion Implicit Models},
  author = {Song, Jiaming and Meng, Chenlin and Ermon, Stefano},
  booktitle = {International Conference on Learning Representations},
  year = {2021},
  url = {https://openreview.net/forum?id=St1giarCHLP}
}
```

MONAI GenerativeModels 软件论文：

```txt
@article{pinaya2023generative,
  title = {Generative AI for Medical Imaging: Extending the MONAI Framework},
  author = {Pinaya, Walter H. L. and Graham, Mark S. and
            Kerfoot, Eric and Tudosiu, Petru-Daniel and
            Dafflon, Jessica and Fernandez, Virginia and
            Sanchez, Pedro and Wolleb, Julia and
            da Costa, Pedro F. and Patel, Ashay and
            Chung, Hyungjin and Zhao, Can and Peng, Wei and
            Liu, Zelong and Mei, Xueyan and Lucena, Oeslle and
            Ye, Jong Chul and Tsaftaris, Sotirios A. and
            Dogra, Prerna and Feng, Andrew and Modat, Marc and
            Nachev, Parashkev and Ourselin, Sebastien and
            Cardoso, M. Jorge},
  journal = {arXiv preprint arXiv:2307.15208},
  year = {2023},
  eprint = {2307.15208},
  archivePrefix = {arXiv},
  url = {https://arxiv.org/abs/2307.15208}
}
```


## Minor-15. Data Availability 与受试者名单

### Original

> Data Availability mentions only "structural MRI and AV-45 PET"; FDG-PET should be added. Please also release the list of ADNI/OASIS subject and image IDs used, to allow exact replication.

### Response

We thank the reviewer for identifying the omission in the Data Availability statement and for emphasizing the importance of data traceability and reproducibility.

We acknowledge that FDG-PET was inadvertently omitted from the original statement. We will correct this omission and clarify the imaging modalities used in each dataset, distinguishing the multi-tracer PET data from ADNI and the AV45-PET data used for external validation on OASIS-3.

Regarding subject and image identifiers, we agree that detailed data selection and splitting information is important for reproducibility. We will organize the data selection criteria, fixed data splits, random seeds, and relevant reproducibility materials for the revised experiments and make them available to the extent permitted by the applicable ADNI and OASIS-3 data use agreements. Any sharing of subject- or image-level identifiers will comply with the corresponding data access and redistribution requirements.

We will also review and correct the data access and licensing information in the Data Availability statement to ensure consistency with the requirements of the respective data providers.

### Modified in Manuscript

#### 来源：主页面

R3 Minor-15 — Data Availability 正文修改方案

修改位置：`BMEF_main.tex` 第 380–381 行，Data Availability。

建议保留原有数据来源说明，重点修改三处：补充 FDG-PET、纠正 OASIS-3 的数据获取和许可描述，以及补充修订实验的可复现性信息。

###### 修改 1

- 位置：Data Availability
- TeX 行号：380–381

Original

> The data used in this study were obtained from two publicly available datasets: the Alzheimer's Disease Neuroimaging Initiative (ADNI) and the Open Access Series of Imaging Studies (OASIS-3). ADNI data are publicly accessible through the LONI Image and Data Archive (IDA) at `\url{https://ida.loni.usc.edu}` after registration and agreement to the data use terms. OASIS-3 data are available at `\url{https://www.oasis-brains.org}` under a Creative Commons Attribution 4.0 International License. The specific imaging and clinical data used in this work include structural MRI and AV-45 PET scans, along with associated demographic and cognitive assessments.

Revised

```txt
The data used in this study were obtained from two research datasets: the Alzheimer's Disease Neuroimaging Initiative (ADNI) and the Open Access Series of Imaging Studies (OASIS-3). ADNI data are available to approved researchers through the LONI Image and Data Archive (IDA) at \url{https://ida.loni.usc.edu}, subject to the ADNI Data Use Agreement. OASIS-3 data are available through the official OASIS data access process at \url{https://sites.wustl.edu/oasisbrains/request-access/}, subject to the corresponding Data Use Terms. The ADNI data used in this study included structural T1-weighted MRI, $^{18}$F-FDG PET, and $^{18}$F-AV45 PET, along with associated demographic and cognitive assessments. The OASIS-3 external validation used structural MRI and $^{18}$F-AV45 PET.

To facilitate reproducibility, the data selection criteria, fixed data splits, random seeds, and relevant implementation details for the revised experiments will be documented and made available to the extent permitted by the applicable data use agreements. Any sharing of subject- and image-level identifiers will comply with the corresponding data access and redistribution requirements.
```


## Minor-16. 超参数

### Original

> Missing hyperparameters: τ, λ\_F, λ\_A, batch size, U-Net depth and channel widths, cross-attention placement, and parameter count.

### Response

We thank the reviewer for highlighting the insufficient reporting of model architecture details and training hyperparameters. We agree that providing these specifications is essential for methodological transparency and reproducibility.

We have further examined the original experimental notebooks and the configuration used for the revised experiments. The verified loss weights are λ\_F = 1.0 and λ\_A = 1.0, with a batch size of 1. The generator U-Net consists of four resolution levels with channel widths of (32, 64, 64, 128) and one residual block per level. Cross-attention is configured only at the deepest resolution level, with a conditioning dimension of 512. By instantiating the corresponding U-Net architecture, we verified that it contains 9,925,921 parameters, all of which are trainable. This count refers specifically to the generator U-Net and excludes the VLM and separate adaptation modules.

Regarding the similarity threshold τ, we verified that the revised E1 Full configuration uses τ = 0.82 as a target in a soft penalty rather than as a strictly enforced constraint. We will therefore clarify the distinction between this implementation and the hard-constraint formulation presented in the original manuscript, and revise the mathematical description to accurately reflect the implemented optimization procedure.

In the revised manuscript, we will provide the verified architectural specifications and hyperparameters, clarify the placement of cross-attention, and explicitly define the scope of the reported parameter count. We will also distinguish settings confirmed from the original experimental records from those verified in the reconstructed experiments, ensuring that the reported implementation details are accurate and reproducible.

**核查提示：** 勾选状态与 τ 待确认提示并存；Methods 第 229–241 行与 R2-15 方案重叠，需按来源证据统一。

### Modified in Manuscript

#### 来源：[M16正文修改](https://app.notion.com/p/40895d43b2dd807fb42cc33f85b765a6)

##### R3 Minor-16 — 正文修改方案

根据你提供的代码核验结果，建议修改 `BMEF_main.tex` 中的四处内容，其中三处可以直接确定修改文本，\\(\\tau\\) 的数学公式需要保留一个待核实项。

整体采用最小修改原则：不改变网络设计、不引入新实验结果，同时区分原始实验记录与 E1 Full 重建实验的证据来源。

##### 1. 修正 cross-attention 的位置描述

位置：第 263 行，Methods → Rectified Flow。

###### 修改 1

- 位置：Methods → Rectified Flow
- TeX 行号：263

Original

> This two-token context representation is injected into the velocity U-Net via cross-attention layers at multiple resolutions, enabling spatial features at each scale to dynamically attend to both the target imaging modality and the patient’s unique clinical attributes. Critically, no additional trainable parameters are introduced for clinical metadata encoding—all semantic information is derived from the pre-trained BiomedCLIP model—thereby enhancing generalizability and mitigating overfitting in data-limited medical imaging scenarios.

Revised

```txt
This two-token context representation is injected into the velocity U-Net through cross-attention at its deepest resolution level, which is 512, allowing the corresponding features to attend to both the target imaging modality and the subject-specific clinical information. Critically, no additional trainable parameters are introduced for clinical metadata encoding---the clinical text embeddings are obtained from the frozen BiomedCLIP model.
```

修改理由： 实际配置为 `attention_levels=(False, False, False, True)`，不能继续写作 at multiple resolutions。保留了原句关于临床信息无需另行训练编码器的含义，但避免推导未经实验验证的泛化性能结论。

##### 2. 补充双示踪剂损失权重

位置：第 282 行，Methods → Multi-Task Learning and One-Step Generation。

###### 修改 2

- 位置：Methods → Multi-Task Learning and One-Step Generation
- TeX 行号：282

Original

> where \\(\\mathbf\{x\}\_\{\\mathrm\{MRI\}\}\\) denotes the input magnetic resonance image, \\(\\mathbf\{y\}\_f\\) and \\(\\mathbf\{y\}\_a\\) are the corresponding ground-truth FDG and AV45 PET images (when available), and \\(\\delta\_F,\\delta\_A\\in\\\{0,1\\\}\\) indicate the presence (1) or absence (0) of each PET modality for a given subject. The hyperparameters \\(\\lambda\_F\\) and \\(\\lambda\_A\\) balance the relative contribution of each task during training. This formulation ensures that supervision is applied solely to available modalities, enabling robust training in heterogeneous clinical cohorts with incomplete multi-tracer imaging.

Revised

```txt
where $\mathbf{x}_{\text{MRI}}$ denotes the input magnetic resonance image, $\mathbf{y}_f$ and $\mathbf{y}_a$ are the corresponding ground-truth FDG and AV45 PET images (when available), and $\delta_F, \delta_A \in \{0,1\}$ indicate the presence ($1$) or absence ($0$) of each PET modality for a given subject. The loss weights were set to $\lambda_F = 1.0$ and $\lambda_A = 1.0$, assigning equal weights to the two tracer-specific objectives. This formulation ensures that supervision is applied solely to available modalities, enabling training in heterogeneous clinical cohorts with incomplete multi-tracer imaging.
```

修改理由： 明确报告原始训练 notebook 中的 `alpha=1.0` 和 `beta=1.0`。同时将 enabling robust training 改成更中性的表述，避免将训练机制直接等同于已经验证的鲁棒性。

##### 3. 补充 U-Net 结构、batch size 和参数量

位置：第 347 行，Methods → Implementation Details。

###### 修改 3

- 位置：Methods → Implementation Details
- TeX 行号：347

Original

> All models were implemented in PyTorch (v2.6.0) and trained on NVIDIA RTX A6000 GPUs (48 GB memory per card). The Adam optimizer was used with an initial learning rate of \\(2.5\\times10\^\{-5\}\\). Training was conducted for 165 epochs, with knowledge distillation applied from epoch 140 onward. Automatic Mixed Precision (AMP) was employed to accelerate training and reduce memory consumption. Each model required approximately 138 GPU hours for full convergence. A complete list of software dependencies and their versions is provided in Table S\[software\] for full reproducibility.

Revised

All models were implemented in PyTorch (v2.6.0) and trained on NVIDIA RTX A6000 GPUs (48 GB memory per card). The Adam optimizer was used with an initial learning rate of \\(2.5\\times10\^\{-5\}\\). Training was conducted for 165 epochs, with knowledge distillation applied from epoch 140 onward. Automatic Mixed Precision (AMP) was employed to accelerate training and reduce memory consumption. Each model required approximately 138 GPU hours for full convergence. A complete list of software dependencies and their versions is provided in Table S\[software\] for full reproducibility.

Specifically, the generator employed a four-level 3D U-Net with channel widths of $(32, 64, 64, 128)$ and one residual block per level. Cross-attention was enabled only at the deepest resolution level, with a conditioning dimension of 512. The batch size was set to 1. The instantiated generator U-Net contained 9,925,921 parameters, all of which were trainable. 

##### 4. 修正 \\(\\tau\\) 的硬约束表述

位置：第 229–241 行，Methods → Domain-Adapted VLM。

这是本条唯一不能只靠现有参数截图完成最终修改的部分。

###### 修改 4

- 位置：Methods → Domain-Adapted VLM
- TeX 行号：229–241

Original

```txt
The optimal parameters are obtained by solving a constrained optimization problem:
\begin{equation}
\begin{aligned}
& \underset{Adapt_f,\, Adapt_a}{\arg \min} \quad
   \mathcal{L}_{\text{align}} = \big(1 - \operatorname{sim}(Adapt_f(c_f), \mathbb{E}[f_f])\big) + \big(1 - \operatorname{sim}(Adapt_a(c_a), \mathbb{E}[f_a])\big) \\
& \text{subject to} \quad
   \operatorname{sim}\big(Adapt_f(c_f), Adapt_a(c_a)\big) \geq \tau,
\end{aligned}
\label{eq:align_opt}
\end{equation}
where $\operatorname{sim}(\cdot, \cdot)$ denotes cosine similarity, and $\tau \in [0,1]$ is a predefined threshold. The constraint ensures the cross-modality guidance vectors maintain a certain level of semantic consistency.

By solving~\eqref{eq:align_opt}, we obtain the modality-specific guidance vectors $Adapt_f(c_f)$ and $Adapt_a(c_a)$, which are subsequently used to steer the rectified flow translation process in a domain-informed manner.
```

Revised（目前已确定的文字部分）

```txt
The adaptation parameters were optimized using a modality-specific alignment objective together with a soft penalty encouraging cross-tracer semantic consistency. In the revised E1 Full configuration, the similarity target was set to $\tau = 0.82$. Unlike a hard constraint, this penalty encourages the adapted tracer representations to maintain a specified level of semantic similarity without guaranteeing that the target is satisfied at every optimization step.
```


## Minor-17. Figure 1 图例

### Original

> Fig. 1 legend: "Just Add It" should be replaced with a clear description (e.g., "element-wise addition").

### Response

We thank the reviewer for pointing out the unclear terminology in the legend of Figure 1. We agree that the phrase "Just Add It" is informal and does not adequately describe the underlying mathematical operation.

After reviewing the correspondence between the schematic and the one-step generation formulation, we confirmed that this operation represents element-wise addition of the input MRI and the predicted velocity field to obtain the synthesized PET image.

Accordingly, we will replace "Just Add It" with "Element-wise Addition" in the revised Figure 1 to provide a more precise and technically appropriate description of the operation.

### Modified in Manuscript

#### 来源：主页面

- 位置：Figure 1
- TeX 行号：

替换为revised-1029-fig1.pdf


## Minor-18. Figure 4 缺少 MCI 分析

### Original

> Fig. 4 C-F show only AD vs. CN. Please add MCI comparisons, given the paper's focus on MCI.

### Response

We thank the reviewer for the suggestion to include MCI comparisons in Figure 4C–F. We appreciate the importance of evaluating synthetic PET images in individuals with mild cognitive impairment.

The primary purpose of Figure 4C–F is to investigate whether synthetic PET images preserve representative AD-related regional differences observed in real PET images. We therefore selected AD and CN as contrasting groups to provide a clearer comparison of regional uptake patterns across distinct disease states. Given the clinical and pathological heterogeneity of MCI, whose imaging characteristics may overlap with those of both CN and AD, these panels were not intended to provide an exhaustive comparison across all diagnostic stages.

Instead, our evaluation of MCI focuses on the potential utility of synthetic PET for distinguishing cognitive impairment stages. Specifically, Figure 5 includes dedicated downstream classification tasks for MCI versus CN and EMCI versus LMCI, assessing the contribution of synthetic PET to MCI identification and the differentiation of early- and late-stage MCI. These analyses complement the AD-related regional comparisons presented in Figure 4C–F.

We acknowledge that the original manuscript did not sufficiently clarify this rationale. We will revise the relevant descriptions to explain the purpose of the AD/CN comparisons and the complementary role of the MCI-related classification experiments. We will also clarify that the overall regional analyses in Figure 4A–B included CN, MCI, and AD subjects without separate diagnostic-group stratification.

**核查提示：** 第 134、138 行与 G4 合并方案重叠。此处旧方案仍含 precisely preserved，需在归组时整合，不能直接覆盖 G4。

### Modified in Manuscript

#### 来源：[M18正文修改](https://app.notion.com/p/40895d43b2dd80e0806fc69c8f338f19)

##### 位置一：`BMEF_main.tex` 第 134 行，Results → Regional Statistical Analysis

原文称第二项分析比较了 CN、MCI 和 AD 三组，但实际 Figure 4C–F 只进行了 AD/CN 比较。这里需要直接纠正。

###### 修改 1

- 位置：Results → Regional Statistical Analysis
- TeX 行号：134

Original

> For a comprehensive quantitative evaluation, we performed two group-wise statistical comparisons on the ADNI cohort. First, we compared synthetic and real images to validate the regional SUV precision of DIReCT\$++\$. Second, we compared synthetic images across diagnostic groups (cognitively normal, i.e., CN, MCI, AD) to verify their ability to capture disease-relevant patterns.

Revised

```txt
For a comprehensive quantitative evaluation, we performed two complementary regional analyses on the ADNI cohort. First, we compared synthetic and real PET images to assess their regional correspondence. Second, we compared the AD and CN groups using both real and synthetic PET images to examine whether representative AD-related regional differences observed in real PET were reflected in the synthesized images.
```

修改理由：明确 Figure 4 的两项分析任务，并删除原稿中容易使人误以为 C–F 包含三组比较的描述。

##### 位置二：`BMEF_main.tex` 第 138 行，Results → Regional Statistical Analysis

这里是回应审稿人最关键的位置。建议在现有结果段落结尾补充分析目的及与 MCI 分类任务的关系。

###### 修改 2

- 位置：Results → Regional Statistical Analysis
- TeX 行号：138

Original

> Critically, independent-sample \\(t\\)-tests demonstrated that the significant differences between diagnostic groups observed in real PET data were precisely preserved in the synthetic images (Fig. 4C, D; supplementary figures). For instance, DIReCT++ recapitulated the statistically significant differences between AD and CN groups in the precuneus for AV45 PET and in the hippocampus for FDG PET. Similarly, regional differences that were non-significant in real PET data were also consistently non-significant in the synthetic images. These findings confirm that DIReCT++ reliably preserves the essential biomarker information necessary for clinical differentiation.

Revised

```txt
Critically, independent-sample $t$-tests demonstrated that the significant differences between diagnostic groups observed in real PET data were precisely preserved in the synthetic images (Fig.~\ref{fig:4}C, D; figs.~\ref{fig:supp_disease_av45} and \ref{fig:supp_disease_fdg}). For instance, DIReCT$++$ recapitulated the statistically significant differences ($p<0.001$) between AD and CN groups in the precuneus for $^{18}$F-AV-45 (Fig.~\ref{fig:4}C) and in the hippocampus for $^{18}$F-FDG (Fig.~\ref{fig:4}D). Similarly, regional differences that were non-significant in real PET data were also consistently non-significant in the synthetic images ($p>0.05$, Fig.~\ref{fig:4}E, F). These findings confirm that DIReCT$++$ reliably preserves the essential biomarker information necessary for clinical differentiation. The AD--CN comparison was intentionally selected to illustrate representative AD-related regional differences between two distinct diagnostic states, rather than to provide an exhaustive comparison across all diagnostic groups. Given the heterogeneity of MCI, its diagnostic differentiation was evaluated separately through the downstream MCI-versus-CN and EMCI-versus-LMCI classification tasks (Fig.~\ref{fig:5}B, C).
```

修改理由：保留原有统计结果描述，新增两句话，直接解释为什么 Figure 4C–F 采用 AD/CN，以及为什么 MCI 的重点安排在 Figure 5 中。

需要注明：本段原有的显著性、统计检验及 precisely preserved 等表述仍需结合 R3-4、R3-5 最终核验，本次 M18 暂不重新判定这些结论


## Minor-20. 投稿系统中的 LaTeX

### Original

> Abstract: The abstract in the submission system contains raw LaTeX commands (`\noindent`, `\textbf`, `$^{18}$F`), which should be cleaned.

### Response

We thank the reviewer for pointing out the incorrectly displayed LaTeX commands in the abstract within the submission system. We will correct this error when submitting the revised manuscript.

## Minor-21. Sex/Gender 术语

### Original

> Terminology: Please use "sex" consistently rather than alternating with "gender."

### Response

We thank the reviewer for pointing out the inconsistent terminology. We will replace "gender" with "sex" in the relevant passage to ensure consistent terminology throughout the manuscript.

**核查提示：** Results 第 88 行与 R2-15 的新增内容涉及同一段落，需归组整合。

### Modified in Manuscript

#### 来源：主页面

R3 Minor-21 — 正文修改方案

修改位置： `BMEF_main.tex` 第 88 行，Results → Overview of DIReCT++，第二段第一句。

###### 修改 1

- 位置：Results → Overview of DIReCT++
- TeX 行号：88

Original

> To achieve subject-wise precision, text guidance incorporating both common knowledge (e.g., general descriptions of PET tracers) and personal patient information (e.g., age, gender, clinical scores) is encoded by a pre-trained VLM and integrated into the RF model via cross-attention.

Revised

> To achieve subject-wise precision, text guidance incorporating both common knowledge (e.g., general descriptions of PET tracers) and personal patient information (e.g., age, sex, clinical scores) is encoded by a pre-trained VLM and integrated into the RF model via cross-attention.

位置： Supplementary Materials，Table S2 对应的数据集人口统计学描述。

###### 修改 2

- 位置：Supplementary Materials
- TeX 行号：

Original

> The demographic characteristics of this selected cohort, including age and gender distribution, are detailed in Table S2.

Revised

> The demographic characteristics of this selected cohort, including age and sex distribution, are detailed in Table S2.

修改理由： 仅将 `gender` 替换为 `sex`，与 Methods 中已有的 `sex` 术语保持一致，其他内容完全保留。

FIG1中的gender也改为Sex


