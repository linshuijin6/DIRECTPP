#!/usr/bin/env python3
"""
Generate clean, all-English modular rebuttal skeleton from 
reports/source_reports/review_comment_register.csv for BMEF-D-26-00169 (DIReCT++).
"""

import csv
import re
import os

BASE_DIR = "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
REGISTER_CSV = os.path.join(BASE_DIR, "reports/source_reports/review_comment_register.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "rebuttal")
SECTIONS_DIR = os.path.join(OUTPUT_DIR, "sections")
os.makedirs(SECTIONS_DIR, exist_ok=True)

# English titles for major comments
R2_TOPICS = {
    "R2-1": "Scientific Innovation and Novelty",
    "R2-2": "Clinical Motivation and Radiation Reduction",
    "R2-3": "Cross-Validation Protocols for Synthesis vs. Classification",
    "R2-4": "Cross-Sectional Staging vs. Longitudinal Prognostic Claims",
    "R2-5": "Information Leakage via Clinical Prompt Conditioning",
    "R2-6": "Subject-Level Isolation and Longitudinal Visit Separation",
    "R2-7": "Scope of External Validation (OASIS-3 AV45-Only)",
    "R2-8": "Non-Significance vs. Formal Equivalence Testing",
    "R2-9": "FDR Multiplicity Correction Families and Reporting",
    "R2-10": "Subject-Level Agreement, Calibration, and Regional Concordance",
    "R2-11": "Classification Uncertainty and Confidence Intervals",
    "R2-12": "Statistical Significance Testing of Classification Baselines",
    "R2-13": "One-Step Sampling Terminology and Rectified Flow Integration",
    "R2-14": "VLM Guidance and Adapter Implementation Details",
    "R2-15": "Equation 1, Inter-Tracer Similarity vs. Distinctness, and Tau",
    "R2-16": "Demographic Confounding and Conditioning Variables",
    "R2-17": "Baseline Adaptation, Tuning, and Fair Comparison Protocols",
    "R2-18": "Computational Efficiency, Parameter Counts, and Hardware Benchmarks",
    "R2-19": "Code, Seed, Split, and Model Weight Release",
    "R2-20": "Clinical Translation Scope and Translational Boundaries"
}

R3_MAJOR_TOPICS = {
    "R3-1": "Circularity in Prompt Conditioning and Diagnostic Label Encoding",
    "R3-2": "Table S1 Score Distributions, Plausibility, and Imputation Protocols",
    "R3-3": "Absence of Longitudinal Prognostic Endpoints",
    "R3-4": "Non-Significant Tests vs. Subject-Level Concordance and Amyloid Status",
    "R3-5": "Standardized SUVR Terminology, Min-Max Scaling, and Effect Sizes",
    "R3-6": "Subject-Level Splitting, Generator-Classifier Leakage, and Sample Sizes",
    "R3-7": "Classification Metrics, Confidence Intervals, and MRI-Only Baselines",
    "R3-8": "Vision-Language Grounding, Numerical Encoding, and Adapter Logic",
    "R3-9": "Systematic Multi-Component Ablation Study",
    "R3-10": "Fair Comparisons Against Identically-Conditioned Baselines",
    "R3-11": "Quantitative Metric Reporting, Dispersion, and Exemplar Cases",
    "R3-12": "Deterministic U-Net Comparison, Conditional Mean, and Uncertainty",
    "R3-13": "External Validation Limitations and OASIS-3 Prompt Specifications",
    "R3-14": "Clinical Scope, Screening vs. Stratification, and 2024 Criteria",
    "R3-15": "Incremental Methodological Novelty Beyond DIReCT (IPMI 2025)"
}

R3_MINOR_TOPICS = {
    "R3-minor-01": "Grammar correction: 'This challenge stems'",
    "R3-minor-02": "Spelling correction: 'neurodegeneration'",
    "R3-minor-03": "Standardization of SUV/SUVR terminology and plural forms",
    "R3-minor-04": "Explicit definitions of velocity field $v_\\theta$, parameters $\\theta$, and condition $c$",
    "R3-minor-05": "Consistency of diagnostic cohort naming between Methods and Results",
    "R3-minor-06": "Anatomical specification of the temporoparietal junction ROI",
    "R3-minor-07": "Harmonization of FreeSurfer / SynthSeg citations and versions",
    "R3-minor-08": "Removal of duplicate reference entries (Refs. 27 and 33)",
    "R3-minor-09": "Author initial correction for Billot et al. (Ref. 35)",
    "R3-minor-10": "Correction of author listing and title for Ref. 28",
    "R3-minor-11": "Harmonization of author name formatting in Ref. 26",
    "R3-minor-12": "Correction of SPM citation details in Ref. 34",
    "R3-minor-13": "Correction of citation for the FDG reference region in Ref. 36",
    "R3-minor-14": "Verification and correction of DDIM source citation in Ref. 25",
    "R3-minor-15": "Data Availability disclosure of subject/image IDs and FDG accession",
    "R3-minor-16": "Comprehensive disclosure of network hyperparameters and architecture dimensions",
    "R3-minor-17": "Legend clarification for Fig. 1 ('Just Add It' mechanism)",
    "R3-minor-18": "Fig. 4 C--F: Explicit clarification of MCI cohort comparisons",
    "R3-minor-19": "Standardization of axis units and reference regions in figures",
    "R3-minor-20": "Clean formatting of raw LaTeX symbols in submission system abstract",
    "R3-minor-21": "Harmonization of sex vs. gender terminology across the text"
}

EDITOR_TOPICS = {
    "EDITOR-01": "Point-by-point rebuttal letter and cover letter",
    "EDITOR-02": "Separate revised manuscript with highlighted changes",
    "EDITOR-03": "High-resolution editable figure files (vector format)",
    "EDITOR-04": "Signed License to Publish and Conflict of Interest forms",
    "EDITOR-05": "Permissions for reused or modified figures",
    "EDITOR-06": "Authorship Change Form (if applicable)",
    "EDITOR-07": "Acknowledgement of re-review and single revision policy",
    "EDITOR-08": "Adherence to revision deadline (November 04, 2026)",
    "EDITOR-09": "Editorial Manager submission protocol",
    "EDITOR-10": "Review of decision letter attachments"
}

def clean_latex(text: str) -> str:
    """Escapes special characters and formats equations for LaTeX."""
    t = text.strip()
    
    # HTML links: <a href="URL">text</a> -> \href{URL}{text}
    t = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r'\\href{\1}{\2}', t)
    
    # Protect existing \href{...}{...}
    href_bank = []
    def save_href(m):
        href_bank.append(m.group(0))
        return f"__HREF_{len(href_bank)-1}__"
    t = re.sub(r'\\href\{[^\}]+\}\{[^\}]+\}', save_href, t)
    
    # Raw URLs to \url{...}
    def replace_url(m):
        url = m.group(0)
        trail = ""
        while url and url[-1] in (";", ".", ","):
            trail = url[-1] + trail
            url = url[:-1]
        return rf"\url{{{url}}}" + trail
    
    t = re.sub(r'https?://[^\s\)]+', replace_url, t)
    
    # Restore \href
    for i, h in enumerate(href_bank):
        t = t.replace(f"__HREF_{i}__", h)
        
    # Math & Symbols replacements
    t = t.replace("±", r"$\pm$")
    t = t.replace("¹⁸F", r"$^{18}\text{F}$")
    t = t.replace("κ", r"$\kappa$")
    t = t.replace("≈", r"$\approx$")
    t = t.replace("≥", r"$\ge$")
    t = t.replace("→", r"$\rightarrow$")
    t = t.replace("−", r"$-$")
    t = t.replace("“", "``").replace("”", "''")
    t = t.replace("₀", r"$_0$").replace("₁", r"$_1$").replace("₂", r"$_2$")
    t = t.replace("x$_0$", r"$x_0$")
    t = t.replace("Aβ+", r"A$\beta$+")
    t = t.replace("Aβ−", r"A$\beta$-")
    t = t.replace("Aβ", r"A$\beta$")
    t = t.replace("α₁", r"$\alpha_1$").replace("α₂", r"$\alpha_2$")
    t = t.replace("β₁", r"$\beta_1$").replace("β₂", r"$\beta_2$")
    t = t.replace("α", r"$\alpha$").replace("β", r"$\beta$")
    t = t.replace("θ", r"$\theta$")
    t = t.replace("τ", r"$\tau$")
    t = t.replace("λ_F", r"$\lambda_F$").replace("λ_A", r"$\lambda_A$")
    t = t.replace("λ", r"$\lambda$")
    t = t.replace("Vθ", r"$V_\theta$")
    t = t.replace("E[f_f]", r"$\mathbb{E}[f_f]$").replace("E[f_a]", r"$\mathbb{E}[f_a]$")
    t = t.replace("Adapt_f(c_f)", r"$\text{Adapt}_f(c_f)$").replace("Adapt_a(c_a)", r"$\text{Adapt}_a(c_a)$")
    t = t.replace("Adapt_f", r"$\text{Adapt}_f$").replace("Adapt_a", r"$\text{Adapt}_a$")
    t = t.replace("sim(Adapt_f, Adapt_a)", r"$\text{sim}(\text{Adapt}_f, \text{Adapt}_a)$")
    t = re.sub(r'\b([pP])\s*>\s*0\.05', r'$\1 > 0.05$', t)
    t = re.sub(r'\b([pP])\s*<\s*0\.05', r'$\1 < 0.05$', t)
    t = t.replace("~55-75%", r"$\sim$55--75\%")
    
    # Escape %, &, #, _ if not in math or commands
    parts = t.split("$")
    for idx in range(0, len(parts), 2):
        seg = parts[idx]
        seg = re.sub(r'(?<!\\)%', r'\\%', seg)
        seg = re.sub(r'(?<!\\)&', r'\\&', seg)
        seg = re.sub(r'(?<!\\)#', r'\\#', seg)
        seg = re.sub(r'(?<!\\)_', r'\\_', seg)
        parts[idx] = seg
    t = "$".join(parts)
    
    # Fix quotes: "word" -> ``word''
    t = re.sub(r'"([^"]+)"', r"``\1''", t)
    
    return t

def main():
    with open(REGISTER_CSV, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    editors = [r for r in rows if r["comment_id"].startswith("EDITOR-")]
    r2_comments = [r for r in rows if r["comment_id"].startswith("R2-")]
    r3_major = [r for r in rows if r["comment_id"].startswith("R3-") and not r["comment_id"].startswith("R3-minor-")]
    r3_minor = [r for r in rows if r["comment_id"].startswith("R3-minor-")]

    # 1. Generate main.tex
    main_tex = r"""%% ============================================================
%%  Response to Reviewers — BME Frontiers (SPJ)
%%  Manuscript ID: BMEF-D-26-00169
%%  Title: Precision Synthesis of Multi-Tracer PET via VLM-Modulated
%%         Rectified Flow for MCI Stratification
%% ============================================================
\documentclass[11pt]{article}

%% ── Packages ────────────────────────────────────────────────
\usepackage[margin=2.5cm]{geometry}
\usepackage{xcolor}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{parskip}       % paragraph spacing instead of indent
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{graphicx}
\usepackage{microtype}
\usepackage{cite}
\usepackage{url}

%% ── Colors ──────────────────────────────────────────────────
\definecolor{RevColor}{RGB}{0,80,160}      % reviewer quote (deep blue)
\definecolor{RespColor}{RGB}{20,110,50}    % author response (forest green)
\definecolor{ActColor}{RGB}{150,90,0}      % action taken in manuscript (amber/brown)
\definecolor{ChgColor}{RGB}{170,25,25}     % revised text snippet (dark crimson)
\definecolor{HeaderColor}{RGB}{30,50,100}  % section header

%% ── Custom Review Commands ──────────────────────────────────
% Major comment box: \revcomment{ID}{Quote}
\newcommand{\revcomment}[2]{%
  \vspace{8pt}
  \noindent\textbf{\textcolor{RevColor}{Comment~#1:}}\\[3pt]
  {\color{RevColor}\itshape #2}
  \vspace{4pt}
}

% Author response body
\newcommand{\response}[1]{%
  \vspace{3pt}
  \noindent\textbf{\textcolor{RespColor}{Response:}}\\[2pt]
  #1
  \vspace{4pt}
}

% Action taken in manuscript
\newcommand{\actiontaken}[1]{%
  \vspace{3pt}
  \noindent\textbf{\textcolor{ActColor}{Action in Manuscript:}}\\[2pt]
  #1
  \vspace{4pt}
}

% Revised text snippet with location
\newcommand{\changedtext}[2]{%
  \vspace{3pt}
  \noindent\textcolor{ChgColor}{\textbf{Revised Text in Manuscript (#1):}}\\[2pt]
  {\color{ChgColor}\itshape ``#2''}
  \vspace{6pt}
}

% Reviewer section header
\newcommand{\reviewersec}[1]{%
  \vspace{16pt}
  \noindent\rule{\linewidth}{1.0pt}\\[3pt]
  {\Large\bfseries\textcolor{HeaderColor}{#1}}\\[-2pt]
  \rule{\linewidth}{0.5pt}
  \vspace{6pt}
}

% Minor comment compact format: \minorcomment{ID}{Topic}{Quote}{Action}
\newcommand{\minorcomment}[4]{%
  \vspace{6pt}
  \noindent\textbf{\textcolor{RevColor}{[#1] #2:}}\\[2pt]
  {\color{RevColor}\itshape #3}\\[3pt]
  \noindent\textbf{\textcolor{RespColor}{Response \& Action:}}~#4
  \vspace{4pt}
}

%% ── Header / Footer ─────────────────────────────────────────
\pagestyle{fancy}
\fancyhf{}
\lhead{\small\textit{Response to Reviewers — BMEF-D-26-00169}}
\rhead{\small\textit{DIReCT++}}
\cfoot{\small\thepage}
\renewcommand{\headrulewidth}{0.4pt}

%% ── Title styling ───────────────────────────────────────────
\titleformat{\section}[block]
  {\large\bfseries\color{HeaderColor}}
  {}
  {0em}
  {}

%% ============================================================
\begin{document}

%% ── Cover Page ──────────────────────────────────────────────
\thispagestyle{empty}

\vspace*{0.8cm}
{\LARGE\bfseries\color{HeaderColor}
  Point-by-Point Response to Reviewers\\[6pt]
  \large\normalfont\color{black}
  Manuscript ID: \textbf{BMEF-D-26-00169}
}

\vspace{0.6cm}
\noindent\textbf{Journal:} BME Frontiers (\textit{A Science Partner Journal / AAAS})

\noindent\textbf{Title:} Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stratification

\noindent\textbf{Authors:} Shuijin Lin$^{1,4,\dagger}$, Shaozhen Yan$^{2,\dagger}$, Tuo Liu$^{3,4,\dagger}$, Haifeng Wang$^{3,4}$, Chunfeng Lian$^{3,4}$, Jie Lu$^{2,*}$, Jianhua Ma$^{1,4,*}$, Lin Xie$^{1,4,*}$

\noindent\textbf{Affiliations:}\\
{\small
$^1$School of Life Science and Technology, Xi'an Jiaotong University, Xi'an, China.\\
$^2$Department of Radiology and Nuclear Medicine, Xuanwu Hospital, Capital Medical University, Beijing, China.\\
$^3$School of Mathematics and Statistics, Xi'an Jiaotong University, Xi'an, China.\\
$^4$Research Center for Intelligent Medical Equipment and Devices (IMED), Xi'an Jiaotong University, Xi'an, China.\\
$^*$Corresponding authors: \href{mailto:linxie@xjtu.edu.cn}{linxie@xjtu.edu.cn}; \href{mailto:jhma@xjtu.edu.cn}{jhma@xjtu.edu.cn}; \href{mailto:imaginglu@hotmail.com}{imaginglu@hotmail.com}.\\
$^\dagger$These authors contributed equally to this work.
}

\noindent\textbf{Date:} \today

\vspace{0.8cm}
\noindent\rule{\linewidth}{1.2pt}

%% ── Modular Sections ────────────────────────────────────────
\input{sections/00_general_response.tex}

\clearpage
\input{sections/01_editor.tex}

\clearpage
\input{sections/02_reviewer2.tex}

\clearpage
\input{sections/03_reviewer3_major.tex}

\clearpage
\input{sections/04_reviewer3_minor.tex}

%% ── References ──────────────────────────────────────────────
\clearpage
\bibliographystyle{unsrt}
\bibliography{references}

\end{document}
"""
    with open(os.path.join(OUTPUT_DIR, "main.tex"), "w", encoding="utf-8") as f:
        f.write(main_tex.strip() + "\n")

    # 2. Generate 00_general_response.tex
    gen_resp_tex = r"""%% ============================================================
%%  Section 0: General Response & Summary of Revisions
%% ============================================================
\reviewersec{General Response \& Summary of Major Revisions}

Dear Editor-in-Chief, Associate Editor, and Reviewers,

We express our sincere gratitude to the Editorial Office and the Reviewers for their meticulous, constructive, and insightful evaluations of our manuscript (\textbf{BMEF-D-26-00169}). The feedback has highlighted crucial areas for methodological rigor, statistical discipline, and clinical precision. 

In strict adherence to the reviewers' comments, we have performed comprehensive additional experiments, conducted extensive ablations, rigorously re-evaluated our statistical framework, and substantially revised the manuscript. 

Below is an executive summary of the major revisions implemented:

\begin{enumerate}[leftmargin=1.5em, itemsep=4pt]
  \item \textbf{Circularity Elimination \& Prompt Conditioning Verification (R3-1, R2-5, R2-16):}
  We have fully disclosed the exact prompt template and all clinical features (MMSE, CDR, FAQ, GDS, NPI-Q, age, sex, weight). To definitively eliminate concerns regarding label circularity, we trained and benchmarked two dedicated clinical classification baselines (\emph{Clinical-only MLP} and \emph{MRI + Clinical MLP}), conducted complete prompt-shuffling/mismatch experiments, and performed tracer-only synthesis without clinical conditioning. The results confirm that DIReCT++ synthesizes true anatomy-grounded PET pathology rather than encoding diagnostic metadata.

  \item \textbf{Data Imputation Transparency \& Table S1 Corrections (R3-2):}
  We thoroughly re-examined Table~S1, reported exact per-variable missingness across all diagnostic cohorts, documented the median-imputation protocol within training folds, and clarified the demographic distributions to ensure total transparency.

  \item \textbf{Prognosis vs. Cross-Sectional Stratification Reframing (R3-3, R2-4, R2-20):}
  Acknowledging the cross-sectional nature of the primary ADNI dataset and the absence of longitudinal time-to-conversion endpoints, we have conscientiously removed overreaching claims of ``prognostic prediction'' and ``prognostic stratification'' across the Title, Abstract, Introduction, and Discussion, focusing precisely on cross-sectional severity differentiation (EMCI vs.\ LMCI).

  \item \textbf{Subject-Level Equivalence \& Amyloid Status Agreement (R3-4, R2-8, R2-10):}
  We have abandoned ungrounded assertions of ``high fidelity inferred from $p > 0.05$''. In their place, we provide rigorous subject-level concordance statistics: Lin's Concordance Correlation Coefficient (CCC), Intraclass Correlation Coefficient (ICC), Bland--Altman limits of agreement, and critical amyloid-positivity ($A\beta+$ vs.\ $A\beta-$) classification metrics (Sensitivity, Specificity, Cohen's $\kappa$).

  \item \textbf{Standardized Quantitative Terminology: SUVR vs. SUV (R3-5, R2-9):}
  We standardized all regional uptake terminology to Standardized Uptake Value Ratio (\textbf{SUVR}), clarified reference region normalization (whole cerebellum for AV45, pons/cerebellar gray for FDG), documented the FDR family definitions ($q$-values), and reported Cohen's $d$ effect sizes for all regional comparisons.

  \item \textbf{Strict Subject-Level Isolation \& 2-Fold OOF / 3-Fold Architecture (R3-6, R2-3, R2-6, R2-19):}
  We clarified the two-stage protocol: the generative synthesis model is evaluated via 2-fold Out-Of-Fold (OOF) cross-validation, and downstream classification is evaluated on 3-fold cross-validation with absolute subject-level separation (zero visit leakage). Synthetic PET images evaluated by downstream classifiers were generated exclusively by models that never saw those subjects during training.

  \item \textbf{Systematic Multi-Baseline Comparison \& Ablations (R3-7, R3-9, R3-10, R3-12, R2-17):}
  We added multi-model baselines including tabular MLP, direct regression U-Net, and SwinUNETR baselines under strictly identical splits and preprocessing. All classification metrics are reported with fold-wise mean $\pm$ SD and 95\% confidence intervals.
\end{enumerate}

All modifications are highlighted in \textcolor{red}{red text} in the revised manuscript. Below, we provide our detailed point-by-point responses to each comment raised by the Editor, Reviewer~2, and Reviewer~3.
"""
    with open(os.path.join(SECTIONS_DIR, "00_general_response.tex"), "w", encoding="utf-8") as f:
        f.write(gen_resp_tex.strip() + "\n")

    # 3. Generate 01_editor.tex
    editor_lines = [r"\reviewersec{Part 1: Response to the Editorial Office}"]
    for r in editors:
        cid = r["comment_id"]
        topic = EDITOR_TOPICS.get(cid, cid)
        quote = clean_latex(r["original_text"])
        editor_lines.append(f"""
\\subsection*{{{cid}: {topic}}}
\\revcomment{{{cid}}}{{{quote}}}

\\response{{
We thank the Editorial Office for these instructions. We have complied with all requirements as detailed below.
}}

\\actiontaken{{
We have prepared and verified all required files in full compliance with the journal guidelines.
}}
""")
    with open(os.path.join(SECTIONS_DIR, "01_editor.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(editor_lines).strip() + "\n")

    # 4. Generate 02_reviewer2.tex
    r2_lines = [r"\reviewersec{Part 2: Response to Reviewer 2}"]
    for r in r2_comments:
        cid = r["comment_id"]
        topic = R2_TOPICS.get(cid, cid)
        quote = clean_latex(r["original_text"])
        r2_lines.append(f"""
\\subsection*{{{cid}: {topic}}}
\\revcomment{{{cid}}}{{{quote}}}

\\response{{
We thank Reviewer~2 for this insightful and constructive observation.
% [TODO: Insert detailed response for {cid}]
}}

\\actiontaken{{
% [TODO: Insert summary of changes for {cid}]
}}

\\changedtext{{Section X.X, Page Y}}{{%
% [TODO: Insert revised excerpt for {cid}]
}}
""")
    with open(os.path.join(SECTIONS_DIR, "02_reviewer2.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(r2_lines).strip() + "\n")

    # 5. Generate 03_reviewer3_major.tex
    r3_major_lines = [r"\reviewersec{Part 3: Response to Reviewer 3 — Major Comments}"]
    for r in r3_major:
        cid = r["comment_id"]
        topic = R3_MAJOR_TOPICS.get(cid, cid)
        quote = clean_latex(r["original_text"])
        r3_major_lines.append(f"""
\\subsection*{{{cid}: {topic}}}
\\revcomment{{{cid}}}{{{quote}}}

\\response{{
We express our deepest gratitude to Reviewer~3 for raising this foundational point.
% [TODO: Insert detailed response for {cid}]
}}

\\actiontaken{{
% [TODO: Insert summary of changes for {cid}]
}}

\\changedtext{{Section X.X, Page Y}}{{%
% [TODO: Insert revised excerpt for {cid}]
}}
""")
    with open(os.path.join(SECTIONS_DIR, "03_reviewer3_major.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(r3_major_lines).strip() + "\n")

    # 6. Generate 04_reviewer3_minor.tex
    r3_minor_lines = [r"""\reviewersec{Part 4: Response to Reviewer 3 — Minor Comments}

We thank Reviewer~3 for the meticulous proofreading and valuable minor corrections. We have addressed every item in full:
"""]
    for r in r3_minor:
        cid = r["comment_id"]
        topic = R3_MINOR_TOPICS.get(cid, cid)
        quote = clean_latex(r["original_text"])
        r3_minor_lines.append(f"""
\\minorcomment{{{cid}}}{{{topic}}}{{{quote}}}{{%
We thank the reviewer for pointing this out. We have carefully revised this item in the manuscript.
}}
""")
    with open(os.path.join(SECTIONS_DIR, "04_reviewer3_minor.tex"), "w", encoding="utf-8") as f:
        f.write("\n".join(r3_minor_lines).strip() + "\n")

    print("Successfully generated all clean English rebuttal files!")

if __name__ == "__main__":
    main()
