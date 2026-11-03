# Response to Reviewer 2, Comment 14

Thank you for pointing out that the domain-adaptation procedure requires a more explicit description. We agree that embedding dimensions, volume-to-feature conversion, prompt construction, trainable parameters, and the implemented optimization objective must be specified separately. The following details describe the affine-adapter branch and distinguish it from implementations using unadapted tracer embeddings.

**Embedding dimensions and frozen encoders.** The local BiomedCLIP implementation produces 512-dimensional projected text and image features; these should be distinguished from the encoders' 768-dimensional hidden representations. The image and text encoders, including their projection layers, are kept fixed. Adaptation operates on the projected tracer-text embeddings rather than updating the BiomedCLIP backbone. Each clinical description also produces one 512-dimensional vector. For each subject and target tracer, the clinical vector and the corresponding tracer vector are stacked as two context tokens, giving a conditioning tensor of shape \(B\times2\times512\), where \(B\) is the batch size. The rectified-flow U-Net receives this context through cross-attention with a context dimension of 512.

**PET feature extraction.** The 2D BiomedCLIP image encoder is applied slice by slice rather than directly to a 3D PET volume. From a preprocessed PET tensor of size \(160\times192\times160\), 160 slices are selected uniformly along the third array dimension using integer indices from `linspace(0, D−1, 160)`. Each slice is scaled as \((x-\min x)/(\max x-\min x+10^{-5})\), multiplied by 255, converted to unsigned 8-bit values, resized to \(224\times224\) with PIL, and replicated across three channels. The images then pass through the bundled image processor, which applies its configured resize, center-crop, and channel normalization. The normalization means are (0.48145466, 0.45782750, 0.40821073), and the standard deviations are (0.26862954, 0.26130258, 0.27577711). The frozen image encoder returns one projected 512-dimensional feature per slice. These features are averaged across the 160 slices to obtain one subject-level PET feature, which is subsequently L2-normalized for adapter fitting. The same procedure is used for each tracer in the fold-specific revision implementation. PET features are used for fitting the tracer guidance vectors; a test subject's PET is not required to construct the inference-time context.

**Prompt construction.** Tracer knowledge and subject information are encoded separately. The fixed tracer descriptions are:

FDG: “FDG PET is a functional brain imaging technique that visualizes the dynamic changes in glucose metabolism, directly linked to neuronal energy demands and synaptic activity. It serves as a tool to assess functional connectivity and energy utilization across brain regions. Areas with decreased metabolic activity, such as those affected by neurodegenerative diseases, should exhibit reduced signal intensity. High-intensity metabolic hotspots in gray matter (e.g., the cerebral cortex and basal ganglia) are key markers of neuronal activity.”

AV45: “AV45 PET is a molecular imaging technique that highlights the static distribution of amyloid-beta plaques, a critical pathological marker of Alzheimer's disease. This imaging modality provides a spatial map of amyloid deposition in cortical regions (e.g., the temporal, parietal, and frontal lobes) and can distinguish amyloid-positive areas from amyloid-negative white matter regions. The primary focus is on identifying amyloid deposition patterns to assess disease progression and pathological burden.”

The clinical prompt follows a fixed template:

“Subject is a {age}-year-old {sex} with a weight of {weight} kg. The global Clinical Dementia Rating (CDR) score, which assesses dementia severity (0: no dementia to 3: severe dementia), is {CDR}. The Mini-Mental State Examination (MMSE) score, assessing cognitive function (0: severe impairment to 30: normal), is {MMSE}. The Geriatric Depression Scale (GDS) score, screening depression (0: no depression to 15: severe depression), is {GDS}. The Functional Activities Questionnaire (FAQ) score, assessing daily activity impairment (0: no impairment to 30: severe impairment), is {FAQ}. The Neuropsychiatric Inventory Questionnaire (NPI-Q) Total Score, assessing neuropsychiatric symptom burden (0: no symptoms to higher scores indicating greater burden), is {NPI-Q}.”

Age and the MMSE, GDS, FAQ, and NPI-Q scores are formatted without decimal places; weight and CDR use one decimal place. Sex is expressed as “male” or “female.” Text tokenization uses the bundled BERT tokenizer with a maximum length of 256 and truncation enabled. Tracer descriptions are encoded with their attention masks. In the fold-specific revision implementation, clinical descriptions are encoded in equal-length batches without padding, using the historical input-IDs-only encoder call, and are checked for truncation. Clinical embeddings are not passed through the tracer adapters or additionally L2-normalized. The template does not explicitly insert the diagnosis label or Logical Memory II, although this does not establish that the upstream clinical values are independent of diagnosis or free of imputation; their provenance is a separate issue.

**Affine adapters and implemented objective.** For tracer \(m\in\{f,a\}\), let \(c_m\in\mathbb R^{512}\) be the L2-normalized tracer-text feature and \(v_{im}\) the L2-normalized PET feature of training subject \(i\). The adapted guidance vector is

\[
z_m=\frac{s_m c_m+b_m}{\|s_m c_m+b_m\|_2},
\qquad s_m\in\mathbb R,\quad b_m\in\mathbb R^{512}.
\]

Each adapter therefore contains one scalar scale and a 512-dimensional bias, or 513 trainable parameters; the two adapters contain 1,026 parameters in total. The implemented loss is

\[
\mathcal L=
-\frac{1}{N_f}\sum_{i=1}^{N_f}\cos(z_f,v_{if})
-\frac{1}{N_a}\sum_{i=1}^{N_a}\cos(z_a,v_{ia})
+100\big[\cos(z_f,z_a)-0.82\big]^2.
\]

The alignment terms average individual subject-level cosine similarities for each tracer. They are not computed as cosine similarity with a re-normalized cohort-mean feature. Importantly, the cross-tracer term is a two-sided squared soft penalty: similarities both above and below 0.82 are penalized. The manuscript's constrained notation \(\cos(z_f,z_a)\geq\tau\) does not accurately describe this implementation.

**Optimization and use of the fitted vectors.** Scales are initialized to 1 and biases to independent Gaussian values with standard deviation 0.01. Both adapters are optimized jointly with full-batch Adam at a learning rate of \(10^{-3}\) for 5,000 updates, without a learning-rate schedule or early stopping. In the fold-specific revision implementation, fitting uses only PET features belonging to the generator training fold; the two fold seeds are 43 and 44. The final normalized vectors are saved after the last update and remain fixed during generator training and inference. This procedure learns one guidance vector per tracer and fold, rather than a separate PET-derived vector for each test subject.

**Meaning of \(\tau\).** The value 0.82 is a fixed soft-penalty target. It numerically matches the two-decimal approximation of the initial cosine similarity between the two unadapted tracer-text embeddings: 0.8205 in the archived notebook output and 0.8205374479 when recomputed from the frozen revision embeddings. This numerical correspondence does not establish the original selection rationale. We therefore do not describe 0.82 as a threshold optimized for synthesis or classification performance, a hard constraint, or a demonstrated optimum. The separate adapter-level sensitivity analysis addresses changes in representation alignment and does not establish downstream image or clinical benefits.

Finally, the affine-adapter and frozen-token branches must be identified separately. The optimization details above apply to the adapter branch; they should not be attributed to runs that directly use unadapted BiomedCLIP tracer embeddings. This distinction is necessary for a reproducible account of the actual conditioning used in each experiment.
