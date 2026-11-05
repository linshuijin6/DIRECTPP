"""Reserve a small margin for latexdiff color boxes around full-width case figures."""
from pathlib import Path
import re
p=Path(__file__).resolve().parent/'derived/manuscript_highlighted.tex';s=p.read_text()
for t in ['fdg','av45']:s=s.replace(r'\includegraphics[width=\textwidth]{revision_cases_'+t+'}',r'\includegraphics[width=0.97\textwidth]{revision_cases_'+t+'}')
# Keep CFONT color markup, but do not issue a text-size command inside math.
s=s.replace(r'\providecommand{\DIFdeltex}[1]{{\protect\color{red} \scriptsize #1}}',r'\providecommand{\DIFdeltex}[1]{{\protect\color{red} \ifmmode #1\else\scriptsize #1\fi}}')
# Heading commands are excluded from inline latexdiff matching so deleted headings
# cannot corrupt a new heading argument or create duplicate hyperref destinations.
s=re.sub(r'%DIFDELCMD < \\(section|subsection|subsubsection)(\*?)\{([^{}\n]*)\}[ \t]*$',lambda m:r'\par\noindent\DIFdel{\textbf{'+m.group(3)+r'}}\par',s,flags=re.M)
base=p.parent
old=(base/'baseline_flat.tex').read_text();current=(base/'current_flat.tex').read_text()
head=r'\\(section|subsection|subsubsection)(\*?)\{([^{}]*)\}'
oldheads=set(re.findall(head,old))
for command,star,title in re.findall(head,current):
 if (command,star,title) not in oldheads:
  token='\\'+command+star+'{'+title+'}'
  replacement='\\'+command+star+r'{\texorpdfstring{\DIFadd{'+title+'}}{'+title+'}}'
  s=s.replace(token,replacement)
# Changed captions are marked blue as complete current captions; do not repeat
# long deleted captions inside floats or alter their scientific text.
def captions(text):
 found=[]
 for m in re.finditer(r'\\caption\{',text):
  line=text[text.rfind('\n',0,m.start())+1:m.start()]
  if re.search(r'(?<!\\)%',line):continue
  start=m.end();i=start;depth=1
  while depth:
   if text[i]=='\\':i+=2;continue
   if text[i]=='{':depth+=1
   elif text[i]=='}':depth-=1
   i+=1
  found.append((start,i-1,text[start:i-1]))
 return found
oldcaps={' '.join(c.split()) for _,_,c in captions(old)}
newcaps={' '.join(c.split()) for _,_,c in captions(current)}
for start,end,caption in reversed(captions(s)):
 normalized=' '.join(caption.split())
 if normalized in newcaps and normalized not in oldcaps:s=s[:start]+r'{\color{blue}'+caption+'}'+s[end:]
p.write_text(s)
