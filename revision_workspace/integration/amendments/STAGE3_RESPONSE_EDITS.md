# Stage 3 — Rebuttal academic tone and concision

起点：Stage 2 commit `3f431b28e1f90ed40b09bb88361fa622be60256f`。

本记录列出全部获批替换或删除的完整文本单元；同一 Response 的其余内容保持不变。LaTeX 由现有 formatter 输出，原始作者来源和 `.source.md` 未修改。

## Reviewer responses

### R3-1

位置：`rebuttal/sections/03_reviewer3_major.tex`，当前 Response 起始行 3。

修改 1：删除重复的研究目标、评分医学意义辩解及未来修改承诺；其余证据和第一阶段限定保留。

Original：
```text
We would also like to clarify that the primary objective of DIReCT++ is to synthesize multi-tracer PET by integrating MRI with clinically available complementary information. Cognitive scores provide relevant context regarding patients’ cognitive status, which is particularly meaningful when studying fine-grained MCI stages such as EMCI and LMCI. We appreciate the reviewer’s important observation and will further clarify the role of clinical conditioning in the revised manuscript, while providing a more cautious interpretation of the downstream classification findings and the potential clinical value of synthetic PET.
```

Revised：
删除该文本，不添加替代句。

### R3-8

位置：`rebuttal/sections/03_reviewer3_major.tex`，当前 Response 起始行 233。

修改 1：删除铺垫和 not merely/Instead 辩解；下一段保留八个变量、评分解释与医学语境。

Original：
```text
We understand the reviewer’s concern regarding the ability of CLIP-based text encoders to represent numerical clinical variables. However, we would like to clarify that the purpose of clinical text conditioning in our study is not merely to transform numerical values such as age, MMSE, and CDR into high-dimensional vectors. Instead, our approach incorporates both the numerical measurements and their corresponding medical interpretations into the conditioning representation.
```

Revised：
删除该文本，不添加替代句。

修改 2：删除已由具体 prompt 构造与比较结果说明的研究价值和方法动机。

Original：
```text
We believe that the research value of BiomedCLIP-based text encoding lies in its integration of pre-trained biomedical semantic representations with clinical measurements and their medical interpretations, allowing patient-specific information to participate in PET generation within a clinically contextualized representation space. Compared with relying exclusively on numerical feature learning, this provides an alternative conditioning strategy with a clear methodological motivation.
```

Revised：
删除该文本，不添加替代句。

修改 3：删除重复的 VLM 中心作用总结；前面 tracer 与 patient encoding 解释保留。

Original：
```text
Taken together, we consider the central role of the vision-language model in DIReCT++ to be the provision of biomedical semantic representations for tracer knowledge and patient-specific clinical information, supporting multi-tracer PET synthesis through a shared conditioning mechanism.
```

Revised：
删除该文本，不添加替代句。

修改 4：删除再次比较文本与数值表示动机的总结；输入与模型差异已在前文保留。

Original：
```text
Compared with conditioning approaches based solely on randomly initialized vectors or directly encoded structured numerical variables, BiomedCLIP-based text conditioning offers a distinct representation strategy. On the one hand, tracer conditioning originates from text descriptions containing explicit biomedical knowledge. On the other hand, the patient-specific clinical prompts incorporate numerical measurements together with the medical meanings of the corresponding assessments, allowing clinical information to participate in generation within a shared biomedical text representation space.
```

Revised：
删除该文本，不添加替代句。

修改 5：删除对条件敏感性、指标权衡和 adapter 几何结果的重复总结；原始证据段保留。

Original：
```text
Our additional analyses demonstrate that patient-specific conditioning influences the generated outputs, that BiomedCLIP-based and TabularMLP-based encoding strategies exhibit trade-offs across different image-quality metrics, and that the tracer adaptation mechanism regulates the relative relationship between tracer representations at the feature level. These findings provide further insight into the roles of different conditioning representations within the PET synthesis framework.
```

Revised：
删除该文本，不添加替代句。

修改 6：删除重复感谢及笼统修改总结；各技术回答与最后的 Full/adapter 范围限定保留。

Original：
```text
We sincerely appreciate the reviewer’s constructive suggestions. In the revised manuscript, we now further clarify the BiomedCLIP feature-encoding procedure, clinical prompt construction, tracer adaptation mechanism, and mathematical notation. Together with the additional experiments, these revisions will provide a more precise description of the methodological motivation and practical role of biomedical semantic conditioning in DIReCT++.
```

Revised：
删除该文本，不添加替代句。

修改 7：删除上一段已说明的数值加医学解释重述；保留后一句实际 BiomedCLIP 编码过程。

Original：
```text
Through this prompt construction strategy, clinical conditioning is represented not simply as a collection of isolated numerical values, but as structured natural-language descriptions combining patient-specific measurements with relevant medical context.
```

Revised：
删除该文本，不添加替代句。

修改 8：删除对输入区别的抽象重述；保留 TabularMLP 无自然语言描述及其实际配置。

Original：
```text
Therefore, the distinction between the two approaches extends beyond their network architectures to the representation of clinical information and the prior information used during encoding.
```

Revised：
删除该文本，不添加替代句。

### R2-15

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 290。

修改 1：保留原始 cosine similarity、取整依据和软目标含义，删除开场铺垫及不是任意选择的重复辩解。

Original：
```text
Regarding the selection of \ensuremath{\tau}=0.82, we would like to clarify its specific basis. Before affine adaptation, the cosine similarity between the original FDG and AV45 textual embeddings produced by the pre-trained BiomedCLIP model was 0.8205374, which rounds to 0.82. Accordingly, we selected \ensuremath{\tau}=0.82 as the target cross-tracer similarity, using the original relationship between the two textual representations as a reference. This allows the adapters to align the textual embeddings with their corresponding PET image features while maintaining approximately the relative similarity originally encoded by BiomedCLIP. \textbf{Thus, \ensuremath{\tau}=0.82 was not an arbitrarily assigned value, but was determined from the representational characteristics of the pre-trained text encoder}.
```

Revised：
```text
Before affine adaptation, the cosine similarity between the original FDG and AV45 textual embeddings produced by BiomedCLIP was 0.8205374, which rounds to 0.82. We therefore selected \ensuremath{\tau}=0.82 as the soft cross-tracer similarity target, using the original relationship between the two textual representations as a reference during text–PET feature alignment.
```

### R2-4

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 35。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
To address this concern, we will explicitly describe this task as \textbf{MCI stage discrimination} and revise the relevant terminology and conclusions throughout the manuscript.
```

Revised：
```text
We have described this task as \textbf{MCI stage discrimination} and revised the relevant terminology and conclusions throughout the manuscript.
```

### R2-8

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 128。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
We will also moderate the original statements that inferred high fidelity from p \textgreater{} 0.05.
```

Revised：
```text
We have also revised the statements that inferred high fidelity from p \textgreater{} 0.05.
```

修改 2：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
Furthermore, we will explicitly acknowledge in the Limitations section that our current analyses support agreement in normalized regional uptake values but do not establish clinical quantitative equivalence.
```

Revised：
```text
The Discussion now states that these analyses support agreement in normalized regional uptake values but do not establish clinical quantitative equivalence.
```

### R2-9

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 154。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
In the revised manuscript, we will explicitly report the statistical families and corresponding numbers of tests, clarify the FDR correction procedure and significance thresholds in the Statistical Analysis section and the relevant descriptions of Figure 4, and provide adjusted q-values for representative brain regions to improve the transparency and reproducibility of the statistical analysis.
```

Revised：
```text
The revised manuscript reports the statistical families and numbers of tests, specifies the FDR procedure and significance thresholds in Statistical Analysis and Figure 4, and provides adjusted q-values for representative brain regions.
```

### R2-10

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 180。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
We will explicitly clarify this distinction and its implications in the revised manuscript.
```

Revised：
```text
The revised manuscript clarifies this distinction and its implications.
```

修改 2：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
In the revised manuscript, we will expand the regional agreement supplementary table to include regression slopes, intercepts, and their 95\% confidence intervals for the 16 representative tracer–ROI combinations, alongside the existing agreement and bias metrics.
```

Revised：
```text
The regional agreement supplementary table now includes regression slopes, intercepts, and their 95\% confidence intervals for the 16 representative tracer–ROI combinations, alongside the agreement and bias metrics.
```

### R2-12

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 222。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
In the revised manuscript, we will present these findings alongside the corresponding confidence intervals and statistical comparisons, and refine the original statements regarding statistical superiority to provide a more accurate interpretation of the contribution of synthetic PET to downstream classification.
```

Revised：
```text
The revised manuscript presents these findings with their confidence intervals and statistical comparisons and revises the statements regarding statistical superiority accordingly.
```

### R2-14

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 257。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
In the revised manuscript, we will supplement the descriptions of feature dimensionality, PET slice-based encoding, clinical prompt composition, adapter parameters, and optimization settings to improve the reproducibility of the model implementation and the different experimental configurations.
```

Revised：
```text
The revised manuscript specifies feature dimensionality, PET slice-based encoding, clinical prompt composition, adapter parameters, and optimization settings for the different experimental configurations.
```

### R2-20

位置：`rebuttal/sections/02_reviewer2.tex`，当前 Response 起始行 414。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
Accordingly, we will moderate statements regarding widespread screening, clinically actionable biomarkers, and early intervention to better distinguish the demonstrated findings from potential future clinical applications.
```

Revised：
```text
We have revised the statements regarding widespread screening, clinically actionable biomarkers, and early intervention to distinguish the demonstrated findings from potential future clinical applications.
```

### R3-2

位置：`rebuttal/sections/03_reviewer3_major.tex`，当前 Response 起始行 38。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
Accordingly, based on the existing experimental results and cognitive-score sensitivity analysis, we will more clearly delineate the potential implications of diagnostic-group-conditioned completion for the interpretation of PET synthesis and downstream classification results.
```

Revised：
```text
The revised manuscript discusses how diagnosis-conditioned filling limits the interpretation of PET synthesis and downstream classification results.
```

### R3-12

位置：`rebuttal/sections/03_reviewer3_major.tex`，当前 Response 起始行 450。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
We will explicitly acknowledge this limitation in the Discussion and identify uncertainty quantification, including ensemble-based or stochastic approaches, as a direction for future research.
```

Revised：
```text
The Discussion acknowledges this limitation and identifies uncertainty quantification, including ensemble-based or stochastic approaches, as a direction for future research.
```

### R3-15

位置：`rebuttal/sections/03_reviewer3_major.tex`，当前 Response 起始行 541。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
In the revised manuscript, we will more explicitly distinguish the methodological extensions introduced in DIReCT++ from those established in DIReCT and interpret their contributions in light of the available experimental evidence, without attributing the overall performance differences to any single component.
```

Revised：
```text
The revised manuscript distinguishes the methodological extensions introduced in DIReCT++ from those established in DIReCT and interprets their contributions without attributing the overall performance differences to any single component.
```

### M7

位置：`rebuttal/sections/04_reviewer3_minor.tex`，当前 Response 起始行 89。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
We will also clearly distinguish the FreeSurfer-based skull-stripping step from SynthSeg-based brain parcellation and clarify that the ROI masks derived from T1-weighted MRI were used for regional PET analysis.
```

Revised：
```text
The revised manuscript also distinguishes FreeSurfer-based skull stripping from SynthSeg-based brain parcellation and specifies that ROI masks derived from T1-weighted MRI were used for regional PET analysis.
```

修改 2：删除已经完成的具体说明之后的模板化未来效果总结，无独立事实损失。

Original：
```text
These revisions will ensure a consistent and accurate description of the preprocessing and ROI analysis procedures.
```

Revised：
删除该文本，不添加替代句。

### M9

位置：`rebuttal/sections/04_reviewer3_minor.tex`，当前 Response 起始行 120。

修改 1：仅将当前正文及补充材料中已完成的修改改为准确完成状态；未来研究和投稿操作不变。

Original：
```text
We have verified that the first author is Benjamin Billot and will correct “Billot C” to “Billot B” in the revised manuscript.
```

Revised：
```text
We have verified that the first author is Benjamin Billot and corrected “Billot C” to “Billot B” in the revised manuscript.
```

### R2-11：保留原文

当前已使用完成的实验描述及现在时结果报告，没有待修正的未来承诺；整条 Response 保持不变。

## Editorial responses

### EDITOR-04

位置：`rebuttal/sections/01_editor.tex`。保留未完成事项及原始截止日期，不推定签署、许可、延期或在线投稿已完成。

Original：
```text
The local integration has not verified signed License to Publish or Conflict of Interest forms from all authors. These forms must be supplied and checked by the authors before submission; no signature or completed-form status is inferred from the manuscript.
```

Revised：
```text
The signed License to Publish and Conflict of Interest forms from all authors remain to be verified before submission.
```

### EDITOR-05

位置：`rebuttal/sections/01_editor.tex`。保留未完成事项及原始截止日期，不推定签署、许可、延期或在线投稿已完成。

Original：
```text
No clearance of third-party reuse rights is asserted by the local integration. Recreated plots and the schematic have documented local sources; the authors must confirm any applicable permission requirements for reused material before submission.
```

Revised：
```text
The recreated plots and schematic have documented sources. Any required permissions for reused material remain to be confirmed before submission.
```

### EDITOR-06

位置：`rebuttal/sections/01_editor.tex`。保留未完成事项及原始截止日期，不推定签署、许可、延期或在线投稿已完成。

Original：
```text
This integration did not change the author list or affiliations relative to the preserved manuscript baseline. If the submission record differs or an authorship change is requested, the required author confirmations and change form must be handled by the authors.
```

Revised：
```text
The author list and affiliations are unchanged from the preserved manuscript version. If the submission record differs or an authorship change is requested, we will provide the required author confirmations and change form.
```

### EDITOR-08

位置：`rebuttal/sections/01_editor.tex`。保留未完成事项及原始截止日期，不推定签署、许可、延期或在线投稿已完成。

Original：
```text
We note that the decision letter states a revision deadline of 4 November 2026. The local preparation does not establish that an online submission has occurred or that an extension was granted.
```

Revised：
```text
We note the revision deadline of 4 November 2026 stated in the decision letter.
```

### EDITOR-09

位置：`rebuttal/sections/01_editor.tex`。保留未完成事项及原始截止日期，不推定签署、许可、延期或在线投稿已完成。

Original：
```text
The authors will upload the reviewed final files through the journal's Editorial Manager revision workflow. This local integration has not logged into or submitted files to the journal system.
```

Revised：
```text
We will upload the final files through the journal's Editorial Manager revision workflow after author review.
```

### EDITOR-10

位置：`rebuttal/sections/01_editor.tex`。保留未完成事项及原始截止日期，不推定签署、许可、延期或在线投稿已完成。

Original：
```text
The decision letter refers to additional attachments available through View Attachments. Their contents have not been verified in the local materials; the authors must inspect and account for them before submission.
```

Revised：
```text
The additional attachments listed under View Attachments remain to be reviewed and addressed before submission.
```

## 保留的独立证据与第四阶段待办

R3-8 保留八项变量与医学解释、BiomedCLIP 编码过程、TabularMLP 输入及 512 维配置、混合指标结果、条件输出敏感性、未来区域定量研究、160 张 2D PET slice 编码、affine adapter、soft tau 目标、Figure 1 参数符号，以及 frozen encoder / representation-level adapter / reconstructed raw-tracer Full 的区别。删去的总结均由这些保留段落覆盖。

全部 reviewer/editor comment 原文、Action in Manuscript、changedtext 和当前页码保持不变。M1/M2 继续使用旧引文，按 `STAGE2_REBUTTAL_QUOTE_SYNC.md` 留待第四阶段同步。其他最终页码、行号及交付构建也留待第四阶段。
