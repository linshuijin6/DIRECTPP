# Local build dependencies

Ubuntu focal packages were downloaded without installation (`apt-get --download-only`, no system mutation) and extracted beneath `root/`. The matched pair is biber 2.14 / biblatex from texlive-bibtex-extra 2019.20200218. Local Perl modules and shared libraries are provided by the downloaded biber dependencies. latexdiff 1.3.0 is also extracted here. Binary dependencies are ignored by Git; the build wrapper sets scoped search paths. The system pdflatex is TeX Live 2019.
