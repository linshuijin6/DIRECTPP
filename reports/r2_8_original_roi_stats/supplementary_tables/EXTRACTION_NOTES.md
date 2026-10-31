# Extraction and verification notes

## Source and scope

- Statistical source: `../regional_paired_statistics.csv` (SHA-256 `10e80e00e4ee809e9a7dd9c8618802d9b900922bd881fd9711beefec50ca6e8f`). Methods, exclusions, and input provenance are documented in `../REPORT.md`.
- These files are **extracts**, not a new analysis. No paired statistic, interval, p-value, or q-value was recomputed. Numeric CSV fields were copied as text from the statistical source, retaining its precision.
- All measurement and error quantities are **normalized regional uptake (arbitrary units)**. The paired difference is Syn − Real. The Bland–Altman bias duplicates the mean paired difference by definition; the limits of agreement are observation-spread estimates, not confidence intervals.
- The original Benjamini–Hochberg q-values are retained for all three outputs. Each source q-value belongs to a family of 98 ROI tests within one tracer × diagnostic group. The 48-row Figure 4 subset was **not** used to form a new correction family.

## ROI labels and Figure 4 selection

- Every one of the 98 ROI IDs had exactly one matching label in the existing `/mnt/nfsdata/nfsdata/linshuijin/freesurfer/FreeSurferColorLUT.txt`. The `ROI anatomical name` column reproduces that verified LUT label; no anatomical name was inferred from a numeric ID alone.
- The selected IDs are `1025`, `2025`, `1032`, `2032`, `1033`, `2033`, `1028`, and `2028` for each tracer. Their Figure 4A/B labels and ID mappings were checked in `../REPORT.md` against the manuscript figure and LUT.
- Figure 4A/B display overall distributions without diagnostic-group stratification. The 48-row table applies the **verified Figure 4 ROI selection** to the source CSV's CN, AD, and MCI rows; it is not a claim that the original figure plotted these three groups separately or used the exact same CSV files.

## Diagnostic-group limitation

`MCI` is the original `Research Group` label from the selected CSV source. It was not pooled with `EMCI` or `LMCI`; those remain separate rows in the complete table. Available evidence does not establish that CSV `MCI` equals manuscript `MCI-U`, all MCI participants, or any particular pooled definition. The manuscript's original MCI grouping and exact Figure 4 plotting input remain unresolved; no mapping was assumed.

## Output checks

| Output | Expected and verified rows | Group/ROI coverage |
|---|---:|---|
| `full_regional_statistics.csv` | 1,176 | 98 ROIs × 6 groups × 2 tracers |
| `figure4_primary_regions.csv` | 48 | 8 verified ROIs × CN/AD/original CSV MCI × 2 tracers |
| `overall_regional_statistics.csv` | 196 | 98 ROIs × overall × 2 tracers |

All output statistical fields were compared with the corresponding source row as exact strings; `Tracer`, `ROI ID`, and `Diagnostic group` remained unique together. Source group labels and their counts were preserved, and all output q-values and 98-test family sizes matched the source. No source CSV, manuscript file, or Git history was changed for this extraction.
