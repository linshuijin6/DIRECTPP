#!/usr/bin/env bash
set -eu
TASK_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK_TOOLS="$TASK_ROOT/revision_workspace/integration/toolchain/root"
TASK_BUILD="$TASK_ROOT/revision_workspace/build/manuscript"
mkdir -p "$TASK_BUILD"
export TEXINPUTS="$TASK_TOOLS/usr/share/texlive/texmf-dist/tex//:"
export BIBINPUTS="$TASK_TOOLS/usr/share/texlive/texmf-dist/bibtex//:"
export BSTINPUTS="$TASK_TOOLS/usr/share/texlive/texmf-dist/bibtex//:"
export PERL5LIB="$TASK_TOOLS/usr/share/perl5:$TASK_TOOLS/usr/lib/x86_64-linux-gnu/perl5/5.30"
export LD_LIBRARY_PATH="$TASK_TOOLS/usr/lib:$TASK_TOOLS/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
cd "$TASK_ROOT/manuscript"
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" BMEF_main.tex > "$TASK_BUILD/pass1.stdout" 2>&1
"$TASK_TOOLS/usr/bin/biber" --input-directory "$TASK_BUILD" --output-directory "$TASK_BUILD" BMEF_main > "$TASK_BUILD/biber.stdout" 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" BMEF_main.tex > "$TASK_BUILD/pass2.stdout" 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" BMEF_main.tex > "$TASK_BUILD/pass3.stdout" 2>&1
