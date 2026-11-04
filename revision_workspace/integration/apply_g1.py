from edit_registry import ROOT,WORK,apply
import re,json,ast
import pandas as pd
main=(ROOT/'manuscript/BMEF_main.tex').read_text()
def para(prefix):return next(l for l in main.splitlines() if l.startswith(prefix))
source='rebuttal/BMEF_from_notion/BMEF审稿回复 3d295d43b2dd8300b74601d792205677.md';tau='rebuttal/BMEF_from_notion/BMEF审稿回复/R2-15回复及正文修改 40995d43b2dd80d79c0ee3144ba8cb2e.md';m16='rebuttal/BMEF_from_notion/BMEF审稿回复/M16正文修改 40895d43b2dd807fb42cc33f85b765a6.md'
ev=[source,tau,'experiments/original_author_reproduction/run.py','reports/revision_evidence_night_20261102/G1/REPORT.md']
old=para('To achieve subject-wise precision')
new=r'''Text guidance incorporates tracer descriptions and patient information (age, sex, weight and clinical scores) encoded by frozen BiomedCLIP encoders and injected into the RF model through cross-attention. The affine fine-tuning formulation optimizes lightweight adapters of BiomedCLIP-derived tracer guidance, rather than BiomedCLIP encoder weights, using a soft cross-tracer similarity penalty (Fig.~\ref{fig:1}B). In a separate adapter-level analysis, varying $\tau$ from 0.70 to 0.98 changed the mean cross-tracer embedding similarity from 0.7032 to 0.9807. At $\tau=0.82$, the similarity was 0.8214, compared with 0.9897 without the cross-tracer penalty (Table~\ref{tab:supp_tau_adapter}). These are representation-level results, not a comparison of PET generation quality across $\tau$. The reconstructed Full generation experiments used the original fixed tracer embeddings; their performance should not be attributed to affine adaptation.'''
apply('G1-RESULTS-CONDITIONING','manuscript/BMEF_main.tex',old,new,['R2-14','R2-15','R3-8','R3-9','R3-15','M21'],['G1'],ev,'Merge R3-8 clarification and R2-15 representation results; explicitly separate actual Full token identity',section='Results / framework conditioning')
old=para('After training, DIReCT')
new=r'''At inference, the shared network predicts a velocity field for the selected tracer from MRI and the corresponding two-token text context. A single forward pass produces one tracer-specific PET estimate; FDG and AV45 are obtained in separate tracer-conditioned passes (Fig.~\ref{fig:1}D). The resulting images are evaluated through image-quality measures, regional uptake analysis and cross-sectional classification (Fig.~\ref{fig:1}E).'''
apply('G1-G6-RESULTS-INFERENCE','manuscript/BMEF_main.tex',old,new,['R2-13','R3-9','R3-12','R3-15'],['G1','G6'],ev,'Single-tracer-per-forward is confirmed in actual implementation; merge G6 correction now at shared position',section='Results / framework inference')
old=re.search(r'\\caption\{\\textbf\{Overview of the DIReCT.*?\\label\{fig:1\}',main,re.S).group(0)
new=r'''\caption{\textbf{Overview of the DIReCT$++$ framework for multimodal PET synthesis and downstream analysis.}
(A) Tracer-conditioned rectified flow from MRI to FDG- or AV45-PET. (B) Lightweight affine fine-tuning of tracer guidance derived from frozen BiomedCLIP encoders. The symbols $\alpha$ and $\beta$ denote FDG adapter parameters $(\alpha_1,\alpha_2)$ and AV45 adapter parameters $(\beta_1,\beta_2)$, respectively; these adaptations are separate from the raw tracer embeddings used by the reconstructed Full generation experiments. (C) A shared conditional 3D U-Net predicts velocity fields for the requested tracer. (D) Learned one-step PET estimation by residual addition of the predicted velocity to MRI; each forward pass produces one tracer. (E) Image-quality, regional uptake and cross-sectional classification analyses. These analyses do not establish clinical replacement of PET.}
    \label{fig:1}'''
apply('G1-G6-FIGURE1-CAPTION','manuscript/BMEF_main.tex',old,new,['R3-8','M17','R2-13','R3-9','R3-15'],['G1','G6'],ev,'Merge affine parameter notation, residual addition and per-tracer forward; figure artwork still requires matching changes',section='fig:1 caption')
old=para('DIReCT$++$ is a VLM-modulated rectified flow (RF) framework')
new=r'''DIReCT$++$ combines a frozen BiomedCLIP text encoder with a conditional 3D rectified flow model to synthesize FDG- or AV45-PET from T1-weighted MRI and tracer/patient text guidance (Fig.~\ref{fig:1}). The affine-adapter formulation aligns tracer-specific text features with PET features while regulating cross-tracer representational similarity. Adapter parameters are optimized separately from the frozen encoder and generator. We distinguish this formulation and its representation-level analyses from generator configurations that use raw frozen tracer embeddings. The following subsections specify the adaptation and conditioning procedures.'''
apply('G1-METHODS-OVERVIEW','manuscript/BMEF_main.tex',old,new,['R2-14','R3-8','R3-15'],['G1'],ev,'Clarify frozen model and configuration-specific tracer adaptation without claiming unverified component causality',section='Methods / DIReCT++ overview')
old=para('To incorporate domain-specific knowledge')
new=old.rstrip()+r''' The frozen BiomedCLIP text and image encoders, including their projection layers, produce 512-dimensional features. For the affine-adapter procedure, each preprocessed 3D PET volume is represented by 160 two-dimensional slices along its third array dimension. Each slice is intensity-normalized, resized to $224\times224$ pixels and converted to a three-channel image before encoding; the slice features are averaged into a subject-level PET representation. The same extraction procedure is used for both tracers in the revised adapter analysis.'''
apply('G1-FEATURE-EXTRACTION','manuscript/BMEF_main.tex',old,new,['R2-14','R3-8'],['G1'],ev,'Retain author-confirmed 512D, slice-based encoding and averaging; scope to adapter feature extraction',section='Domain-Adapted VLM / feature extraction')
start=main.index('where $\\alpha_1, \\beta_1 $');end=main.index('\n\n\n\\subsubsection{Rectified Flow}',start);old=main[start:end]
new=r'''where $\alpha_1,\beta_1$ are scalar scales and $\alpha_2,\beta_2$ are 512-dimensional bias vectors. Each adapter has 513 trainable parameters (1,026 in total). The parameters are optimized using the objective
\begin{equation}
\begin{aligned}
\mathcal{L}_{\mathrm{align}}={}&-\frac{1}{N_f}\sum_{i=1}^{N_f}\operatorname{sim}(Adapt_f(c_f),f_{f,i})\\
&-\frac{1}{N_a}\sum_{j=1}^{N_a}\operatorname{sim}(Adapt_a(c_a),f_{a,j})\\
&+\lambda_{\mathrm{cross}}\left[\operatorname{sim}(Adapt_f(c_f),Adapt_a(c_a))-\tau\right]^2,
\end{aligned}
\label{eq:align_opt}
\end{equation}
where $\operatorname{sim}$ is cosine similarity, $f_{f,i}$ and $f_{a,j}$ are normalized subject-level PET features and $N_f,N_a$ count the available training-fold features. The settings are $\lambda_{\mathrm{cross}}=100$ and $\tau=0.82$. This is a soft squared penalty targeting a reference similarity, not a hard lower-bound constraint or a threshold optimized for generation quality. The target is numerically consistent with the original tracer-text cosine similarity of 0.8205 before adaptation. The two adapters are optimized jointly using Adam (learning rate $10^{-3}$, 5,000 updates); the encoders remain frozen. Adapted vectors remain fixed when used in the affine-adapter conditioning configuration. The reconstructed Full generator uses raw tracer embeddings, while the separate adapter sensitivity analysis tests the representation geometry under Eq.~\eqref{eq:align_opt}.'''
apply('G1-ADAPTER-OBJECTIVE','manuscript/BMEF_main.tex',old,new,['R2-14','R2-15','R3-8','M16'],['G1'],ev+[m16,'experiments/r2_15_tau_adapter_ablation/report.md'],'Merge optimizer details and actual per-subject cosine soft objective, preserving target not optimized-threshold interpretation',section='eq:align_opt')
old=para('The core of DIReCT$++$ is a continuous')
new=old.replace('via a learnable velocity field $V_\\theta$ denotes the network parameters and $c$ encodes modality-specific contextual cues (e.g., anatomical priors or clinical metadata).','via a learnable velocity field $V_\\theta$, where $\\theta$ denotes its network parameters and $\\mathbf{c}$ is the conditioning context containing tracer and clinical text features.')
apply('G1-VELOCITY-NOTATION','manuscript/BMEF_main.tex',old,new,['M4','R3-8'],['G1','G6'],[source],'Define velocity field, its parameters and conditioning separately',section='Rectified Flow / V theta definition')
start=main.index('The modality-specific guidance embeddings');end=main.index('\n\nThis two-token context representation',start);old=main[start:end]
new=r'''For each participant, the conditioning context stacks the patient feature before the fixed target-tracer feature:
\begin{equation}
\mathbf{c}=\begin{bmatrix}c_{\mathrm{demo}}\\g_m\end{bmatrix},
\label{eq:composite_conditioning}
\end{equation}
where $m\in\{f,a\}$ indicates FDG or AV45. The raw tracer text feature is $c_m$ and its affine-adapted form is $Adapt_m(c_m)$; $g_m$ denotes the feature actually supplied by the specified configuration. In the reconstructed Full generator, $g_m=c_m$. The patient feature $c_{\mathrm{demo}}$ is a 512-dimensional frozen BiomedCLIP embedding of a prompt encoding age, sex, weight, Global CDR, MMSE, GDS, FAQ and NPI-Q, with descriptions of the assessments and their medical interpretations. Logical Memory II and an explicit diagnostic label are not prompt fields, whereas CDR and other scores are diagnosis-related, and diagnosis-conditioned filling can encode group information indirectly. The prompt template and tracer texts are provided in Supplementary Methods. Patient prompts are padded and truncated to a maximum of 256 tokens in the reconstructed implementation.'''
apply('G1-CONTEXT-AND-PROMPT','manuscript/BMEF_main.tex',old,new,['R2-5','R2-14','R3-1','R3-8','R3-9'],['G1','G8'],ev,'Use R3-8 replacement token order and complete fields; disclose raw Full tracer features and diagnosis-conditioned score limitation',section='eq:composite_conditioning')
old=para('This two-token context representation')
new=r'''The two-token context is injected by cross-attention only at the deepest of the four U-Net resolution levels (attention levels: false, false, false, true); the conditioning feature dimension is 512. No additional trainable clinical text encoder is introduced: patient features are obtained from the frozen BiomedCLIP model. This design alone does not establish improved generalization or prevention of overfitting.'''
apply('G1-CROSS-ATTENTION','manuscript/BMEF_main.tex',old,new,['R3-8','M16'],['G1'],ev+[m16],'Merge exact attention-level configuration with frozen text-encoder clarification; 512 is feature dimension, not spatial resolution',section='Rectified Flow / cross-attention')
# Build exact, nonidentifying prompt template from AST without running historical code.
q=ROOT/'reports/adni_image_acquisition_audit/filtering_code_recovery_20261103/history_session373_input029.py'
tree=ast.parse(q.read_text());joined=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='description' for t in n.targets))
template=''.join(n.value if isinstance(n,ast.Constant) else '['+n.value.id+']' for n in joined.values)
texttree=ast.parse((ROOT/'experiments/original_author_reproduction/run.py').read_text());tracers={n.targets[0].id:ast.literal_eval(n.value) for n in texttree.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['FDG_TEXT','AV45_TEXT']}
# Escape only literal text; no fabricated individual measurement values.
def esc(t):return t.replace('&',r'\&').replace('%',r'\%').replace('_',r'\_')
tex=r'''\subsection*{Supplementary Methods: conditioning prompts and adapter analysis}
The following is the historical clinical prompt template, with bracketed field placeholders instead of participant identifiers or invented measurements. Values use the historical formatting (rounded age and scores, one decimal for weight and CDR). Its use does not validate the filled values as clinical observations.
\begin{quote}\small
'''+esc(template)+r'''
\end{quote}
\noindent\textbf{FDG tracer prompt.}
\begin{quote}\small
'''+esc(tracers['FDG_TEXT'])+r'''
\end{quote}
\noindent\textbf{AV45 tracer prompt.}
\begin{quote}\small
'''+esc(tracers['AV45_TEXT'])+r'''
\end{quote}
The tracer texts are fixed model inputs; their statements about pathology or progression are not evidence that synthetic PET establishes a biological diagnosis or predicts progression.

\begin{table}[htbp]
\caption{\textbf{Adapter-level sensitivity analysis of the cross-tracer soft target.} Descriptive means across two folds, using 1,856 QC-filtered participants. Only training-fold PET features were used for fitting; held-out features were evaluated after optimization. No cross-term means removal of the penalty ($\lambda_{\mathrm{cross}}=0$), not a target of zero. No generator was retrained or evaluated in this analysis.}
\label{tab:supp_tau_adapter}
\centering\small
\begin{tabular}{lccccc}
\toprule
Setting & \multicolumn{2}{c}{Training alignment} & \multicolumn{2}{c}{Held-out alignment} & Cross-tracer \\
 & FDG & AV45 & FDG & AV45 & similarity \\
\midrule
'''
df=pd.read_csv(ROOT/'experiments/r2_15_tau_adapter_ablation/summary.csv')
for _,r in df.iterrows():
 setting='No cross-term' if r['cross_weight']==0 else f"$\\tau={r['tau']:.2f}$"
 vals=[r[k] for k in ['mean_fdg_alignment','mean_av45_alignment','mean_heldout_fdg_alignment','mean_heldout_av45_alignment','mean_cross_tracer_similarity']];tex+=setting+' & '+' & '.join(f'{v:.4f}' for v in vals)+r' \\'+'\n'
tex+=r'''\bottomrule
\end{tabular}
\end{table}
'''
path=ROOT/'manuscript/supplementary/tables/conditioning.tex';assert not path.exists();path.write_text(tex)
p=ROOT/'manuscript/supplementary/supplementary.tex';old=r'\input{supplementary/tables/reproducibility}'
apply('G1-SUPPLEMENTARY-INPUT','manuscript/supplementary/supplementary.tex',old,old+'\n'+r'\input{supplementary/tables/conditioning}',['R2-14','R2-15','R3-1','R3-8','R3-9'],['G1'],ev+[str(q.relative_to(ROOT)),'experiments/r2_15_tau_adapter_ablation/summary.csv'],'Add exact source prompt templates and CSV-backed adapter table, without exposing participant identifiers',section='Supplementary conditioning methods and tab:supp_tau_adapter')
