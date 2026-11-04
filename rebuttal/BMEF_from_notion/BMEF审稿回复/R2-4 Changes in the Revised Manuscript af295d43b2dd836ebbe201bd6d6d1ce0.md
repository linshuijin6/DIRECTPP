# R2-4 Changes in the Revised Manuscript

### 1. Abstract

原稿 LaTeX 第 60、68 行；PDF 第 1–2 页

Impact Statement

原文：

> This work advances a scalable, data-efficient tool for the early diagnosis and prognostic prediction of AD.
> 

建议替换为：

This work advances a scalable, data-efficient tool for the early diagnosis of AD and discrimination between MCI stages.

Conclusion

原文：

> Crucially, combining these synthesized PET images with MRI enables precise personalized stratification of mild cognitive impairment (MCI), advancing a scalable, data-efficient tool for the early diagnosis and prognostic prediction of AD.
> 

建议替换为：

Crucially, combining these synthesized PET images with MRI enables precise discrimination between early and late stages of mild cognitive impairment (MCI), advancing a scalable, data-efficient tool for the early diagnosis of AD.

### 2. Introduction

LaTeX 第 77、81 行；PDF 第 2–3 页

第 77 行，将：

> Despite these advances, a critical limitation remains: the subject-specific precision necessary for personalized diagnosis and prognostic stratification is still lacking, which is particularly crucial for a heterogeneous condition like AD~\cite.
> 

替换为：

Despite these advances, a critical limitation remains: the subject-specific precision necessary for personalized diagnosis and MCI stage discrimination is still lacking, which is particularly crucial for a heterogeneous condition like AD~\cite.

第 81 行，将：

> When combined with the original MRI scans to train deep learning classifiers~\cite, the synthesized PET data enable accurate personalized diagnosis and, most importantly, the stratification of MCI patients based on their risk of progression to AD.
> 

替换为：

When combined with the original MRI scans to train deep learning classifiers~\cite, the synthesized PET data enable accurate personalized diagnosis and, most importantly, the differentiation between early and late MCI stages.

### 3. Results — Section 2.4

LaTeX 第 151–158 行；PDF 第 7–9 页

章节标题

原文：

`Precise Prognostic Stratification of Mild Cognitive Impairment`

建议：

`Diagnostic Classification and MCI Stage Discrimination`

第一段第一句

Original：

> To evaluate the clinical utility of the synthetic images for personalized diagnosis and prognostic stratification, we conducted classification tasks on the ADNI cohort using a 3-fold cross-validation scheme.
> 

Revised：

> To evaluate the clinical utility of the synthetic images for personalized diagnosis and MCI stage discrimination, we conducted classification tasks on the ADNI cohort using a 3-fold cross-validation scheme.
> 

Original：

> Crucially, the combination of baseline MRI and synthetic multi-tracer PET also enabled accurate prognostic stratification, achieving 81.96% accuracy in differentiating EMCI from LMCI, compared to 77.65% using MRI alone (Fig. 5C).
> 

Revised：

> Crucially, the combination of baseline MRI and synthetic multi-tracer PET also enabled accurate MCI stage discrimination, achieving 81.96% accuracy in differentiating EMCI from LMCI, compared to 77.65% using MRI alone (Fig. 5C).
> 

Original：

> This result highlights the potential of DIReCT++ to stratify patients at the prodromal stage based on their risk of progression.
> 

Revised：

> This result highlights the potential of DIReCT++ to distinguish different stages of MCI.
> 

LaTeX 第 167 行

Original

> Taken together, these findings confirm the translational potential of DIReCT++, as its synthetic outputs serve as effective proxies for real PET biomarkers in critical downstream diagnostic and prognostic tasks.
> 

Revised

> Taken together, these findings confirm the translational potential of DIReCT++, as its synthetic outputs serve as effective proxies for real PET biomarkers in downstream diagnostic tasks, including MCI stage discrimination.
> 

### 4. Discussion

LaTeX 第 171、175、188 行；PDF 第 9–12 页

建议采用以下定向修改：

| 原稿措辞 | 建议替换 |
| --- | --- |
| `enable precise prognostic stratification of MCI` | enable precise MCI stage discrimination |
| `accurate diagnosis and prognostic stratification of MCI` | accurate diagnosis and discrimination between MCI stages |

新增limitations

Importantly, the EMCI-versus-LMCI classification was based on cross-sectional diagnostic categories rather than longitudinal conversion outcomes. Although previous studies have reported differences in subsequent dementia-conversion risk between EMCI and LMCI populations, the present study did not evaluate individual-level disease progression or future conversion to AD. Therefore, the classification results should not be interpreted as evidence of prognostic prediction. Longitudinal validation will be necessary to investigate the prognostic relevance of the synthesized PET images.

### 9. Materials and Methods — Section 4.3

LaTeX 第 295 行

Original

> To account for the heterogeneity of MCI, we further subclassified individuals based on delayed recall performance on the WMS-R Logical Memory II Story A task: Early MCI (EMCI; n = 291) denoted a milder impairment stage, whereas Late MCI (LMCI; n = 152) indicated proximity to dementia conversion.
> 

Revised

> To account for the heterogeneity of MCI, we further subclassified individuals based on delayed recall performance on the WMS-R Logical Memory II Story A task: Early MCI (EMCI; n = 291) denoted a milder impairment stage, whereas Late MCI (LMCI; n = 152) denoted a more severe impairment stage.
> 

下一句

Original：

> The remaining MCI participants without clear progression status were grouped as MCI-unclassified (MCI-U; n = 520).
> 

Revised：

> The remaining MCI participants not classified as EMCI or LMCI were grouped as MCI-unclassified (MCI-U; n = 520).
> 

### 6. Materials and Methods — Section 4.5.2

LaTeX 第 338–340 行；PDF 第 18 页附近

原章节标题：

`Diagnosis and Prognostic Stratification`

建议修改为：

`Diagnostic Classification and MCI Stage Discrimination`

第一句

Original：

> To rigorously evaluate the clinical utility of synthesized PET (Syn-PET) images, we assessed their capacity to support diagnostic and prognostic classification across the AD continuum.
> 

Revised：

> To rigorously evaluate the clinical utility of synthesized PET (Syn-PET) images, we assessed their capacity to support diagnostic classification and MCI stage discrimination across the AD continuum.
> 

第二句

Original：

> Specifically, we trained identical DenseNet classifiers to discriminate between three clinically salient diagnostic pairs: (1) AD versus CN individuals, a canonical diagnostic boundary; (2) MCI versus CN, representing early disease detection; and (3) EMCI versus late MCI (LMCI), a prognostic distinction reflecting differential progression risk.
> 

Revised：

> Specifically, we trained identical DenseNet classifiers to discriminate between three clinically salient diagnostic pairs: (1) AD versus CN individuals, a canonical diagnostic boundary; (2) MCI versus CN, representing early disease detection; and (3) EMCI versus late MCI (LMCI), representing different degrees of memory impairment.
>