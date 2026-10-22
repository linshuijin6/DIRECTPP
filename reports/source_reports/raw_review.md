Ref.: Ms. No. BMEF-D-26-00169
Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stratification
BMEF (BME Frontiers)

Dear Dr Xie,

We have received Reviewers' comments on your manuscript. Based on these comments and the evaluation of the editors, we invite you to revise your manuscript.

The reviewers and I have concerns that will require a major revision of your manuscript. For your information, reviewers' comments are appended below.

If you decide to revise the work, please submit the following:
- A cover letter with a list of changes or a rebuttal against each point raised in the review
- A separate revised manuscript file with highlighted changes
- Separate high-resolution figure files in editable file format. We prefer vector-based files but can accept the following file types: Adobe Illustrator (AI), Adobe Portable Document Format (PDF), Encapsulated PostScript (EPS), Photoshop (PSD), JPEG, PNG, and Tagged Image File Format (TIFF). Please see <a href="https://spj.science.org/pb-assets/SPJ/CustomPages/Misc/SPJ_Figure_Preparation_Guide-1691522222.pdf">our figure guide</a> for assistance in preparing your figures.
- Signed License to Publish and Conflict of Interest forms from all listed Authors. Forms can be found here: https://www.editorialmanager.com/bmef/account/BMEF_LicensetoPublish.pdf; https://www.editorialmanager.com/bmef/account/BMEF_ConflictofInterest.pdf
-For all images reused or obtained from other sources, provide documentation of your right to reuse and/or modify the image. Consult our guide for details:https://spj.science.org/pb-assets/SPJ/CustomPages/Forms/forauthors_permissions.docx
-For any change in authorship, all authors must sign the Authorship Change form available here: https://www.editorialmanager.com/BMEF/account/Auth_Change_Form.pdf

Please note that your revised manuscript will be sent out for re-review and BMEF (BME Frontiers) rarely allows multiple revisions.

Your revision is due by Nov 04, 2026.

To submit a revision, go to https://www.editorialmanager.com/bmef/ and log in as an Author. You will see a menu item call Submission Needing Revision. You will find your submission record there.

Yours sincerely,

The BMEF (BME Frontiers) Editorial Office

BMEF is an Open Access journal supported by Article Processing Charges (APCs). There are no submissions charges.

Through September 30, 2025, all APCs will be covered by SIBET CAS. Beginning October 1, 2025, SIBET CAS will partially subsidize APCs for authors, allowing authors to pay reduced rates. Review the reduced rates on the <a href="https://spj.science.org/page/bmef/apc?">journal website</a>.

Authors whose work is submitted for publication in BMEF before October 1, 2025 will not be responsible for paying APCs.

Reviewers' comments:



Reviewer 2: Overall assessment: The manuscript presents a technically strong and clinically relevant framework with high novelty. However, several methodological and statistical issues should be addressed before the work can be considered for acceptance. Detailed in reports/source_reports/BMEF_Reviewer_Report_English.docx


Reviewer 3: Reviewer Report: BME Frontiers

Manuscript ID: BMEF-D-26-00169
Title: Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stratification
Type: Research Article
Recommendation: Major Revision

Summary

The authors present DIReCT++, which synthesizes ¹⁸F-AV-45 and ¹⁸F-FDG PET from T1-weighted MRI. It uses a 3D rectified flow U-Net conditioned, via cross-attention, on two tokens: a tracer-specific BiomedCLIP text embedding adapted by a scalar-plus-bias transform, and a frozen BiomedCLIP embedding of a clinical prompt (age, sex, weight, neuropsychological scores). The model is trained on ADNI (n = 1,857) and externally tested on OASIS-3 (AV-45 only, n = 419). It is evaluated on image similarity, regional uptake agreement, and downstream classification (AD vs. CN, MCI vs. CN, EMCI vs. LMCI).

The problem is clinically important, the engineering is competent, the multi-tracer training with missing-modality gating (Eq. 6) is practical, and the code release is welcome. However, I have serious concerns about three things. First, the downstream classification results may be driven by information leakage from the clinical prompt rather than by MRI-derived molecular information. Second, the statistical framework cannot establish the subject-level equivalence the manuscript claims. Third, "prognostic stratification" is claimed without any prognostic endpoint. Several of these concerns go to the validity of the central conclusions, so I recommend major revision.

Major Comments

1. Circularity: the conditioning prompt contains the information that defines the diagnostic labels.
This is my principal concern. The clinical prompt encodes "neuropsychological scores" (lines 314-315), and Table S1 lists MMSE, CDR, FAQ, GDS, and NPI-Q. In ADNI, diagnostic group membership is defined largely by MMSE, CDR, and Logical Memory II performance, and the authors state that EMCI/LMCI were assigned using Logical Memory II (lines 358-360). The synthetic PET is then fed to a classifier to predict those same labels. Any gain of "MRI + synthetic PET" over "MRI alone" could therefore reflect clinical scores passed through the generator, not molecular information inferred from anatomy.

The following are needed to resolve this:

The exact prompt template, and a list of which scores are included. Is Logical Memory II or CDR in it? The manuscript is inconsistent: line 95 says "age, gender, clinical scores," lines 314-315 say "age, sex, weight, and neuropsychological scores," and Fig. 1 shows only "Age, Gender, ...".
A classifier using the clinical variables alone, and one using MRI + clinical variables, as reference baselines. If MRI + clinical variables matches MRI + synthetic PET, the synthetic PET adds nothing.
Synthesis and classification without clinical text (tracer token only), and with shuffled or mismatched prompts. If synthetic PET changes substantially when a CN subject's MRI is paired with an AD patient's scores, the images reflect the prompt rather than the patient.

2. Table S1 values appear implausible and may indicate imputation that encodes the label directly.
Several within-group standard deviations are not credible for integer-valued clinical scales. Examples: EMCI MMSE 27.50 ± 0.50, LMCI MMSE 24.47 ± 0.50, LMCI NPI-Q 4.00 ± 0.03, EMCI GDS 1.01 ± 0.14, and LMCI GDS 3.02 ± 0.28. The LMCI mean MMSE (24.47) is also lower than both MCI-U (26.83) and typical ADNI LMCI values, and the CN weight SD (24.13 kg) is unusually large. The authors should explain how these values were computed and whether missing scores were imputed with group means. If they were, the prompt literally encodes group membership, and the classification results in Fig. 5 would be invalid. Please report missingness per variable and per group, and the imputation strategy.

3. "Prognostic stratification" is not supported by the analysis.
EMCI vs. LMCI is a cross-sectional severity distinction based on a memory cutoff, not a prognostic outcome. The manuscript also describes LMCI as indicating "proximity to dementia conversion" and MCI-U as lacking "clear progression status" (lines 360-362), which conflates the two concepts. To justify the title and the claims in lines 178-181 and 249-250, the authors should perform a genuine prognostic analysis: progressive vs. stable MCI (pMCI/sMCI) over a defined follow-up (e.g., 36 months), with time-to-conversion modeling (Cox regression, C-index). Otherwise, "prognostic" and "stratification" should be removed from the title and claims.

4. Non-significant paired t-tests do not demonstrate equivalence, and group-level agreement does not show subject-level precision.
Lines 146-150 infer "high fidelity" from p > 0.05 in paired t-tests. Absence of a significant difference is not evidence of equivalence. The central claim of the paper is subject-specific precision (lines 56, 69-73), which group-mean comparisons cannot test: a model that outputs a diagnosis-conditional average image would pass every test in Fig. 4. The authors should provide:

per-subject agreement for regional SUVR (Pearson/Lin's concordance, ICC, Bland-Altman bias and limits of agreement), overall and within each diagnostic group;
formal equivalence testing (e.g., TOST) with pre-specified margins;
most importantly, amyloid-positivity agreement. Using a standard composite SUVR or Centiloid threshold, report sensitivity, specificity, and Cohen's κ for classifying real Aβ+ vs. Aβ− from synthetic AV-45, stratified by CN, MCI, and AD.

The clinically decisive test is whether the model detects amyloid-positive cognitively normal individuals and amyloid-negative MCI. These are exactly the cases where MRI and clinical scores cannot reveal pathology, and where the authors argue the method is most useful (lines 60-61, 217-219).

5. Quantitative definitions: "SUV" vs. SUVR and min-max normalization.
All volumes are min-max normalized to [0, 1] per image (lines 388-389). Regional values are then called "SUV" and normalized to cerebellar gray matter or pons (lines 137-138), and plotted as "Mean Uptake" on a 0-1 axis (Fig. 4, S1-S6). Please clarify:

whether ratios were computed on the original PET or on min-max-normalized images (the latter loses quantitative meaning);
the reference region for florbetapir (whole cerebellum is the ADNI standard);
the correct terminology (SUVR, not SUV).

Please also verify that the FDR correction described in Section 4.5.1 was actually applied to the p-values shown in the figures, and report effect sizes (Cohen's d) for real vs. synthetic group differences. Preserved significance with a much smaller or larger effect size is not "precise preservation."

6. Data splitting and possible leakage between generator and classifier.
The manuscript states 3-fold cross-validation for synthesis (line 114), two-fold cross-validation (line 391), and 3-fold for classification (line 161). Please clarify:

whether splits are at the subject level (ADNI subjects contribute multiple visits);
whether synthetic PET used to test the classifier on a given subject was produced by a generator that did not see that subject in training;
whether generator and classifier folds are nested or aligned;
the maximum allowed interval between MRI and PET acquisitions;
whether only florbetapir scans were used (ADNI-3/4 also use florbetaben);
whether ADNI's pre-processed PET (co-registered, averaged, uniform resolution) was used, and how multi-scanner differences were handled;
which subjects (including MCI-U) entered each classification task, with per-task sample sizes.

7. Classification reporting and claims of significance.

Methods lists ACC, SEN, and SPE (line 459), but Results and Fig. 5 report AUC.
No confidence intervals or statistical tests are given, yet the text says "significantly outperforming" (lines 171, 215-216). Please report mean ± SD across folds, 95% CIs, and DeLong tests for AUC differences.
EMCI vs. LMCI is imbalanced (291 vs. 152), and specificity is low (~55-75% in Fig. 5C). Please report balanced accuracy.
The MRI-only baseline for MCI vs. CN appears near chance (ACC ≈ 51% in Fig. 5B), which is well below published MRI-only performance. This inflates the apparent benefit of synthetic PET. Please justify the classifier and training protocol, or use a stronger MRI baseline.

8. The vision-language component is overstated relative to what is implemented.

The adapted tracer guidance is a fixed constant. Adapt_f(c_f) and Adapt_a(c_a) are pre-computed and fixed (lines 306-307), with a scalar scale and a bias vector. They are therefore equivalent to two learned tracer tokens. Describing this as "domain knowledge encoding" and "prompt learning" overstates its role. An ablation replacing it with a randomly initialized learned tracer embedding is needed.
Numeric encoding by CLIP. Subject-specific information comes from a frozen BiomedCLIP text encoder applied to a prompt with numbers. CLIP-style text encoders are known to represent numeric values poorly. Please show that the embedding meaningfully separates, for example, MMSE 29 from 24 (embedding distance vs. score difference), and compare against a simple tabular encoder (an MLP on normalized variables). If the tabular encoder performs as well, the VLM framing is not justified.
Image features and constraint logic. BiomedCLIP is a 2D model. Please explain how E[f_f] and E[f_a] were computed from 3D PET (which slices, which aggregation). The constraint sim(Adapt_f, Adapt_a) ≥ τ enforces similarity between tracers, which contradicts the stated goal of "preserving inter-tracer differences" (lines 98-99, 277-278). The value of τ, the optimization method for the constrained problem, and a sensitivity analysis are all missing.
Notation. Fig. 1B uses α and β, while Eq. 1 uses α₁, α₂, β₁, β₂.

9. Ablation study is missing.
The manuscript reports no ablation beyond the single-tracer DIReCT comparison. Please add, at minimum:

no text;
tracer token only;
clinical prompt only;
frozen vs. adapted tracer embedding;
VLM text encoder vs. tabular encoder;
one-step distilled vs. multi-step ODE sampling;
joint vs. separate tracer generation.

Section 4.4 describes 3D RF as an ablation "isolating the contribution of BiomedCLIP guidance," but it differs from DIReCT++ in several respects at once.

10. Baselines and fairness of comparison.

CycleGAN is an unpaired method applied to a paired task, and Swin-UNet is a segmentation architecture. Neither is a strong MRI-to-PET baseline.
Directly relevant MRI-to-PET methods cited in the Introduction (e.g., refs. 11-14) are not compared.
Most importantly, the baselines receive no clinical information, while DIReCT++ does. A fair comparison requires at least one strong baseline given the same clinical variables (e.g., 3D RF or a regression U-Net with a tabular conditioning branch).
Please also clarify whether SegGuidedDiff was run in 2D or 3D, and how baseline hyperparameters were "optimized to their reported best configurations."

11. Image-quality metrics and figures.
Radar plots normalized to the best method (Fig. 2A) hide absolute values and variance. Please provide:

a table of SSIM, PSNR, MAE, and MSE (mean ± SD), computed within a brain mask (background inflates PSNR/SSIM);
paired significance tests against each baseline;
per-tracer OASIS results;
voxel-wise absolute error maps for representative and worst-case subjects;
subject-level scatter plots of real vs. synthetic composite SUVR, colored by diagnosis and amyloid status;
ROC curves with confidence bands.

The examples in Fig. 2B-C and Fig. 3 appear hand-selected; the selection criteria should be stated, or cases should be chosen at the median and 10th percentile of performance.

12. Determinism, conditional-mean behavior, and uncertainty.
Because x₀ is the MRI (not noise) and inference is a single deterministic distilled step (Eq. 7), the model effectively performs conditional regression. For an admittedly ill-posed problem (lines 58-61), this tends to produce a conditional mean, which would smooth out individual pathology. Please:

compare against a plain regression U-Net with identical conditioning;
discuss whether the model can represent uncertainty;
consider providing uncertainty estimates (e.g., ensembles or stochastic sampling). For any clinical use, a synthetic amyloid image without a confidence measure is risky.

Also, the claim that rectified flow supports "exact one-step sampling" (lines 338-339) holds only for sufficiently straightened flows. The distillation procedure (teacher steps, loss, schedule after epoch 140) needs a full description.

13. External validation is limited.
OASIS-3 covers AV-45 only, and CN and AD only (no MCI), with notable age imbalance (66.3 vs. 72.8 years). Please state which prompt fields were available for OASIS (weight, FAQ, GDS, NPI-Q may be missing) and how gaps were handled; the Supplement mentions "secondary screening" without detail. External validation of FDG synthesis and of the MCI tasks would substantially strengthen generalizability claims.

14. Clinical positioning and overstatement.
The Discussion makes strong claims: "democratize access," "primary care screening," "qualitative leap," "new paradigm," and identifying candidates "most likely to benefit from disease-modifying therapies" (lines 208-234). Synthetic amyloid images cannot substitute for molecular confirmation, particularly for anti-amyloid therapy eligibility, where a false positive has real consequences. The authors should:

temper these claims;
discuss the 2024 revised Alzheimer's Association criteria, which define AD biologically by core biomarkers;
compare against, or at least discuss, plasma biomarkers such as p-tau217, which are now a low-cost, radiation-free route to amyloid status. They are mentioned only as a future prompt input (lines 236-237).

15. Incremental novelty over DIReCT (ref. 15).
The main differences from the authors' own IPMI 2025 work appear to be the second tracer, the adapted tracer token, and distillation. The manuscript should state the delta explicitly and show, through ablation, which addition drives the gains.

Minor Comments
Line 57: "This challenges stems" → "This challenge stems."
Lines 58-59: "neurodegenration" → "neurodegeneration."
Line 137: "standardized uptake value (SUV) were" → "values (SUVRs) were."
Line 301: "a learnable velocity field Vθ denotes the network parameters" is garbled; θ and c should be defined separately.
Section 4.5.1 describes paired tests for "AD and CN," but Results report CN, MCI, and AD (lines 145-147). Please reconcile.
Line 427: "Temporoparietal junction" is not a SynthSeg/Desikan-Killiany label. Please specify the ROIs actually used.
Line 133 vs. line 390: "mri_synthseg (FreeSurfer v7.4.1)" and "SynthSeg [35]" cite different references for the same tool. Please use one version and one citation.
References:
Refs. 27 and 33 are duplicates (Fischl, FreeSurfer).
Ref. 35: "Billot C" should be "Billot B."
Ref. 28: author list and title should be verified.
Ref. 26: author formatting is garbled ("Xingchao Liu Chengyue Gong QL").
Ref. 34 (a gray-matter asymmetry protocol) is not an appropriate citation for SPM spatial normalization.
Ref. 36 (an ADNI overview) is not an appropriate source for FDG AD-vulnerable regions.
Ref. 25 (MRI-to-CT for spinal segmentation) should be checked as the source for the 3D DDIM baseline.
Data Availability mentions only "structural MRI and AV-45 PET"; FDG-PET should be added. Please also release the list of ADNI/OASIS subject and image IDs used, to allow exact replication.
Missing hyperparameters: τ, λ_F, λ_A, batch size, U-Net depth and channel widths, cross-attention placement, and parameter count.
Fig. 1 legend: "Just Add It" should be replaced with a clear description (e.g., "element-wise addition").
Fig. 4 C-F show only AD vs. CN. Please add MCI comparisons, given the paper's focus on MCI.
Axis labels "Mean AV45/FDG Uptake" should read "SUVR," with the reference region stated.
Abstract: The abstract in the submission system contains raw LaTeX commands (\noindent, \textbf, $^{18}$F), which should be cleaned.
Terminology: Please use "sex" consistently rather than alternating with "gender."


There is additional documentation related to this decision letter. To access the file(s), please click the link below. You may also login to the system and click the 'View Attachments' link in the Action column.
********

In compliance with data protection regulations, you may request that we remove your personal registration details at any time. (Use the following URL: https://www.editorialmanager.com/bmef/login.asp?a=r). Please contact the publication office if you have any questions.