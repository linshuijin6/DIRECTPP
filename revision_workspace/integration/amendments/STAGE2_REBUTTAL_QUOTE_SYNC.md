# Stage 2 pending Rebuttal quotation synchronization

Status: pending Stage 4; no Rebuttal sections were changed in Stage 2.

The current working manuscript is the authority for final quotations. Preserve the author-confirmed Stage 1 edits. The historical author-response sources and their source snapshots must remain unchanged.

## Exact quotations requiring synchronization

- M1: `rebuttal/sections/04_reviewer3_minor.tex`, current source line 13.
- M2: `rebuttal/sections/04_reviewer3_minor.tex`, current source line 25.

Both are the `\changedtext` excerpt for `Introduction / ill-posed inverse problem` and are generated from the first sentence of `G7-INTRODUCTION-GRAMMAR`. In Stage 4, regenerate the excerpts through the existing `build_rebuttal.py` process after updating the final manuscript locations.

Original quoted sentence:

```text
Generative artificial intelligence (AI) offers a transformative pathway to bridge this clinical gap by synthesizing PET biomarkers from routinely acquired MRI~\cite{dayarathna2024deep,lee2024synthesizing}.
```

Current manuscript sentence to quote:

```text
Generative artificial intelligence (AI) offers methods for estimating PET images from routinely acquired MRI~\cite{dayarathna2024deep,lee2024synthesizing}.
```

## Other Stage 2 positions

B1, B3, B4, B5 and B6 do not change any current verbatim `\changedtext` excerpt. The Stage 1-confirmed final sentence of the second Introduction paragraph is retained unchanged. Recompute final PDF page/line references for affected manuscript positions in Stage 4; existing location maps and delivery files were intentionally not refreshed here.
