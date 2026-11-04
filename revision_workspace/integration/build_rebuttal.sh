#!/usr/bin/env bash
set -eu
TASK_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK_BUILD="$TASK_ROOT/revision_workspace/build/rebuttal"
mkdir -p "$TASK_BUILD"
cd "$TASK_ROOT/rebuttal"
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" main.tex > "$TASK_BUILD/pass1.stdout" 2>&1
(cd "$TASK_BUILD" && BIBINPUTS="$TASK_ROOT/rebuttal:" bibtex main) > "$TASK_BUILD/bibtex.stdout" 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" main.tex > "$TASK_BUILD/pass2.stdout" 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" main.tex > "$TASK_BUILD/pass3.stdout" 2>&1
pdflatex -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" cover_letter.tex > "$TASK_BUILD/cover_letter.stdout" 2>&1
