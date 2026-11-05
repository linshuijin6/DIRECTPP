#!/usr/bin/env bash
set -eu
TASK_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TASK_TOOLS="$TASK_ROOT/revision_workspace/integration/toolchain/root"
TASK_DERIVED="$TASK_ROOT/revision_workspace/integration/derived"
TASK_BUILD="$TASK_ROOT/revision_workspace/build/variants"
mkdir -p "$TASK_BUILD"
export TEXINPUTS="$TASK_TOOLS/usr/share/texlive/texmf-dist/tex//:"
export PERL5LIB="$TASK_TOOLS/usr/share/perl5:$TASK_TOOLS/usr/lib/x86_64-linux-gnu/perl5/5.30"
export LD_LIBRARY_PATH="$TASK_TOOLS/usr/lib:$TASK_TOOLS/usr/lib/x86_64-linux-gnu:${LD_LIBRARY_PATH:-}"
cd "$TASK_ROOT/manuscript"
"$TASK_TOOLS/usr/bin/latexdiff" --type=CFONT --disable-citation-markup --exclude-textcmd=caption,section,subsection,subsubsection --config="PICTUREENV=(?:picture|DIFnomarkup|longtable|tabular|tabularx)" "$TASK_DERIVED/baseline_flat.tex" "$TASK_DERIVED/current_flat.tex" > "$TASK_DERIVED/manuscript_highlighted.tex" 2> "$TASK_BUILD/latexdiff.stderr"
"/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python" "$TASK_ROOT/revision_workspace/integration/tune_highlight.py"
pdflatex -recorder -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" "$TASK_DERIVED/manuscript_highlighted.tex" > "$TASK_BUILD/manuscript_highlighted.pass1.stdout" 2>&1
"$TASK_TOOLS/usr/bin/biber" --input-directory "$TASK_BUILD" --output-directory "$TASK_BUILD" manuscript_highlighted > "$TASK_BUILD/manuscript_highlighted.biber.stdout" 2>&1
pdflatex -recorder -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" "$TASK_DERIVED/manuscript_highlighted.tex" > "$TASK_BUILD/manuscript_highlighted.pass2.stdout" 2>&1
pdflatex -recorder -interaction=nonstopmode -halt-on-error -output-directory="$TASK_BUILD" "$TASK_DERIVED/manuscript_highlighted.tex" > "$TASK_BUILD/manuscript_highlighted.pass3.stdout" 2>&1

# Publish only a completed highlighted build under the validated artifact name.
mkdir -p "$TASK_ROOT/revision_workspace/build/final_highlight"
for TASK_EXT in pdf log aux bbl; do
 cp "$TASK_BUILD/manuscript_highlighted.$TASK_EXT" "$TASK_ROOT/revision_workspace/build/final_highlight/manuscript_highlighted.$TASK_EXT"
done
