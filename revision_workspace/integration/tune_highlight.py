"""Reserve a small margin for latexdiff color boxes around full-width case figures."""
from pathlib import Path
p=Path(__file__).resolve().parent/'derived/manuscript_highlighted.tex';s=p.read_text()
for t in ['fdg','av45']:s=s.replace(r'\includegraphics[width=\textwidth]{revision_cases_'+t+'}',r'\includegraphics[width=0.97\textwidth]{revision_cases_'+t+'}')
p.write_text(s)
