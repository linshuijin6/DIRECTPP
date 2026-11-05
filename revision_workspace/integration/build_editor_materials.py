from edit_registry import ROOT,WORK,apply,amend
from build_rebuttal import latex
import csv,json
# Import above deterministically refreshes the 56-point sections from their indexed sources.
records={x['comment_id']:x for x in csv.DictReader((ROOT/'reports/source_reports/review_comment_register.csv').open())}
general=r'''\reviewersec{General Response}
We thank the Editor and both reviewers for their detailed assessment of manuscript BMEF-D-26-00169. The revised manuscript distinguishes cross-sectional MCI stage discrimination from longitudinal prognosis, reports task-dependent classification findings and clinical baselines, and clarifies the extent of diagnosis-conditioned filling in the clinical inputs.

The main changes concern frozen BiomedCLIP and tracer-adapter definitions; subject-level two-fold synthesis and independent three-fold classification protocols; absolute historical and reconstructed image-quality evidence; normalized regional uptake statistics and FDR families; classification uncertainty, paired comparisons and clinical controls; measured one-step forward cost; and the limits of external and clinical interpretation. We explicitly distinguish the historical input assets from reconstructed generator experiments and do not claim clinical equivalence or molecular confirmation.

Below we reproduce and answer all 20 Reviewer 2 comments, all 15 Reviewer 3 major comments and all 21 Reviewer 3 minor comments individually. Each response is linked to the implemented final manuscript or supplementary locations. Suggested analyses that were not completed are identified and are not represented as completed experiments. Editorial forms and submission-system requirements are tracked separately from scientific revisions.
'''
responses={
'EDITOR-01':'We have prepared the point-by-point response covering all 56 reviewer comments and a separate revision cover letter. The manuscript changes are identified by their actual final locations below.',
'EDITOR-02':'A clean revised manuscript and a separate highlighted revision are included in the prepared delivery package. The highlighted version is derived from the preserved pre-integration manuscript, rather than from a different historical draft.',
'EDITOR-03':'The delivery package contains separate figure PDFs and high-resolution exports. Recreated schematic and quantitative figures include editable SVG and source code; existing composite images retain their supplied source files and documented limitations. We do not describe a raster-only panel as a fully editable vector reconstruction.',
'EDITOR-04':'The signed License to Publish and Conflict of Interest forms from all authors remain to be verified before submission.',
'EDITOR-05':'The recreated plots and schematic have documented sources. Any required permissions for reused material remain to be confirmed before submission.',
'EDITOR-06':'The author list and affiliations are unchanged from the preserved manuscript version. If the submission record differs or an authorship change is requested, we will provide the required author confirmations and change form.',
'EDITOR-07':'We acknowledge that the revised manuscript may undergo further external review and have addressed the reviewers point by point, with unsupported claims narrowed to the available evidence.',
'EDITOR-08':'We note the revision deadline of 4 November 2026 stated in the decision letter.',
'EDITOR-09':"We will upload the final files through the journal's Editorial Manager revision workflow after author review.",
'EDITOR-10':'The additional attachments listed under View Attachments remain to be reviewed and addressed before submission.'}
editor=r'\reviewersec{Response to Editorial Requirements}'+'\n'
for cid,text in responses.items():editor+='\n'+r'\subsection*{'+cid+'}\n'+r'\revcomment{'+cid+'}{'+latex(records[cid]['original_text'])+'}\n'+r'\response{'+latex(text)+'}\n'
for name,text in [('00_general_response.tex',general),('01_editor.tex',editor)]:
 p=ROOT/'rebuttal/sections'/name
 if any(r['position_id']=='REBUTTAL-'+name for r in csv.DictReader((WORK/'position_registry.csv').open())):
  if p.read_text()!=text:amend('REBUTTAL-'+name,text,decision='Render original editor HTML/URL references as breakable links without changing quoted meaning.')
  continue
 apply('REBUTTAL-'+name,str(p.relative_to(ROOT)),p.read_text(),text,[],['REBUTTAL'],['reports/source_reports/REVIEW_REQUIREMENTS.md','revision_workspace/FINAL_INTEGRATION_PLAN.md'],'Replace generic blanket-compliance assertions with actual prepared artifacts and explicit unverified author/system requirements',section=name)
p=ROOT/'rebuttal/main.tex';old=p.read_text();new=old.replace('for MCI Stratification','for MCI Stage Stratification').replace(r'\noindent\textbf{Date:} \today',r'\noindent\textbf{Date:} 4 November 2026');apply('REBUTTAL-TITLE-DATE','rebuttal/main.tex',old,new,[],['REBUTTAL'],['manuscript/BMEF_main.tex'],'Align manuscript title and stated revision date with current author working context',section='Rebuttal cover page')
letter=r'''\documentclass[11pt]{letter}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[margin=2.5cm]{geometry}
\usepackage{hyperref}
\signature{The authors of BMEF-D-26-00169}
\date{4 November 2026}
\begin{document}
\begin{letter}{The Editor\\BME Frontiers}
\opening{Dear Editor,}
Please consider the revised manuscript BMEF-D-26-00169, ``Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for MCI Stage Stratification.'' We thank the Editor and reviewers for their constructive comments.

The revision clarifies the clinical conditioning and extensive diagnostic-group-conditioned filling of missing scores, corrects the prepared clinical summaries, and adds clinical-only and MRI+Clinical classification controls. We distinguish the two-fold synthesis design from independent three-fold classifier evaluation and explicitly state source-identity and acquisition-record limitations.

We provide absolute synthesis metrics, additional frozen-prediction comparisons, masked image-quality evaluation, regional agreement and FDR/effect-size statistics, classifier uncertainty and paired comparisons, and objective supplemental cases with error maps. Results and interpretation retain metric-dependent and unfavorable comparisons. The method description now separates frozen encoders, affine-adapter analyses and actual generator conditioning, and reports the measured scope of one-step forward timing.

The title, abstract and conclusions have been restricted to cross-sectional classification and MCI stage discrimination. The available evidence does not establish longitudinal prognosis, clinical equivalence, independent incremental diagnostic value over diagnosis-related clinical inputs, or replacement of molecular biomarker confirmation. External validation is limited to historical AV45 synthesis in the OASIS-3 CN/AD cohort.

The accompanying response addresses all 56 reviewer comments individually and identifies corresponding manuscript and supplementary locations. We provide clean and highlighted manuscripts, supplementary materials and separate figure files for author review and submission.
\closing{Sincerely,}
\end{letter}
\end{document}
'''
p=ROOT/'rebuttal/cover_letter.tex'
if p.exists():assert p.read_text()==letter
else:p.write_text(letter)
(WORK/'editor_requirements_status.json').write_text(json.dumps({'prepared_local_materials':['56-point response','revision cover letter','clean/highlight manuscript and standalone supplementary in final packaging pipeline','separate figure files and editable sources'],'unverified_author_materials':['all-author signed License to Publish','all-author signed Conflict of Interest','applicable reused-material permissions','authorship change documentation if applicable','decision-letter extra attachments'],'online_submission_performed':False,'signatures_created_or_asserted':False},ensure_ascii=False,indent=2)+'\n')
