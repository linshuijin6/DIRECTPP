"""Prepare derived submission variants; never alter the preserved baseline."""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[2];W=ROOT/'revision_workspace/integration';D=W/'derived';D.mkdir(exist_ok=True)
s=(ROOT/'manuscript/BMEF_main.tex').read_text();aux=(ROOT/'revision_workspace/build/manuscript/BMEF_main.aux').read_text()
labels=[l for l in aux.splitlines() if l.startswith(r'\newlabel{')]
sl=[l for l in labels if re.match(r'\\newlabel\{[^}]+\}\{\{S\d',l)];ml=[l for l in labels if l not in sl]
(D/'supplementary_labels.tex').write_text('\n'.join(sl)+'\n');(D/'main_labels.tex').write_text('\n'.join(ml)+'\n')
a=s.index(r'\section*{Supplementary Materials}');b=s.index(r'\printbibliography',a)
main=s[:a]+s[b:];main=main.replace(r'\begin{document}',r'\input{../revision_workspace/integration/derived/supplementary_labels.tex}'+'\n'+r'\begin{document}',1)
(D/'manuscript_clean.tex').write_text(main)
preamble=s.split(r'\title{',1)[0]
supp=preamble+r'''
\title{Supplementary Materials\\BMEF-D-26-00169}
\author{}
\date{}
\renewcommand{\thefigure}{S\arabic{figure}}
\renewcommand{\theHfigure}{S\arabic{figure}}
\renewcommand{\thetable}{S\arabic{table}}
\renewcommand{\theHtable}{S\arabic{table}}
\emergencystretch=2em
\onehalfspacing
\input{../revision_workspace/integration/derived/main_labels.tex}
\begin{document}
\maketitle
\input{supplementary/supplementary}
\end{document}
'''
(D/'supplementary_standalone.tex').write_text(supp)
# Use the final bibliography number assignments in verbatim manuscript excerpts.
# Plain-text submission abstract contains no TeX syntax.
abstract=s.split(r'\begin{abstract}',1)[1].split(r'\end{abstract}',1)[0]
abstract=re.sub(r'\\noindent\\textbf\{([^}]+)\}',r'\1',abstract)
for a,b in [(r'DIReCT$++$','DIReCT++'),(r'\pm',' ± '),(r'\%','%')]:abstract=abstract.replace(a,b)
abstract=abstract.replace('$','');abstract='\n\n'.join(' '.join(p.split()) for p in abstract.split('\n\n') if p.strip())+'\n'
assert '\\' not in abstract and '$' not in abstract
(W/'submission_abstract.txt').write_text(abstract)
# latexdiff receives flattened manuscript bodies, including table inputs and supplements.
def flatten(text,base):
 def sub(m):
  p=base/(m.group(1)+('.tex' if not Path(m.group(1)).suffix else ''))
  if not p.is_file():return m.group(0)  # TeX-distribution input, resolved by the build.
  return '\n% BEGIN '+m.group(1)+'\n'+flatten(p.read_text(),base)+'\n% END '+m.group(1)+'\n'
 return re.sub(r'\\input\{([^}]+)\}',sub,text)
old=(W/'baseline/manuscript/BMEF_main.tex').read_text()
(D/'baseline_flat.tex').write_text(flatten(old,W/'baseline/manuscript'))
# Historical references are retained only to typeset deleted citations in the diff.
oldbib=(W/'baseline/manuscript/references.bib').read_text();newbib=(ROOT/'manuscript/references.bib').read_text()
extra=[]
for entry in re.split(r'(?m)(?=^@)',oldbib):
 m=re.match(r'@[^\{]+\{([^,]+),',entry)
 if m and m.group(1) in ['fischl2012freesurfer','dalca2022synthseg']:extra.append(entry)
(D/'references_highlighted.bib').write_text(newbib+'\n% Baseline-only entries for deleted citations; excluded from the clean manuscript.\n'+'\n'.join(extra))
flat=flatten(s,ROOT/'manuscript').replace(r'\addbibresource{references.bib}',r'\addbibresource{../revision_workspace/integration/derived/references_highlighted.bib}')
(D/'current_flat.tex').write_text(flat)
(W/'variants_receipt.json').write_text(json.dumps({'clean':'main text and references; supplementary labels imported from final combined manuscript','supplementary':'standalone source with main-label import','highlight':'latexdiff against preserved pre-integration manuscript, flattened inputs','plain_abstract':str((W/'submission_abstract.txt').relative_to(ROOT))},indent=2)+'\n')
print('Prepared clean, standalone supplementary, flattened diff inputs and plain-text abstract.')
