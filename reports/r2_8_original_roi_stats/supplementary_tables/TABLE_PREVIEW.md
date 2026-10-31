# Supplementary table preview: paired regional uptake agreement

**Measurement:** normalized regional uptake (arbitrary units). Paired difference and Bland–Altman bias are Syn − Real. Values below are rounded for display; the CSV files retain the source table's numeric text.

| Table | Scope | Rows |
|---|---|---:|
| `full_regional_statistics.csv` | AV45 and FDG; 98 ROIs × overall, AD, CN, EMCI, LMCI, and original CSV label MCI per tracer | 1,176 |
| `figure4_primary_regions.csv` | Figure 4A/B's eight verified ROIs per tracer × CN, AD, and original CSV label MCI | 48 |
| `overall_regional_statistics.csv` | All 98 ROIs per tracer, all available paired subjects | 196 |

## Figure 4 primary-region table: representative rows

These six rows illustrate the CSV layout for one verified ROI. The full 48-row table contains all eight Figure 4A/B ROIs per tracer. “MCI” is reproduced exactly as stored in the original CSV; its relationship to manuscript MCI-U or a pooled MCI category remains unresolved.

| Tracer | ROI ID | ROI anatomical name | Diagnostic group | N | Mean paired difference | 95% CI | MAE | CCC | ICC(A,1) | Bland–Altman 95% LoA | Raw paired t-test p | BH-FDR q |
|---|---:|---|---|---:|---:|---|---:|---:|---:|---|---:|---:|
| AV45 | 1025 | ctx-lh-precuneus | CN | 511 | +0.0002 | [-0.0015, +0.0019] | 0.0158 | 0.980 | 0.980 | [-0.0384, +0.0389] | 0.793 | 0.9908 |
| AV45 | 1025 | ctx-lh-precuneus | AD | 179 | +0.0025 | [-0.0005, +0.0055] | 0.0167 | 0.980 | 0.980 | [-0.0372, +0.0421] | 0.1033 | 0.8329 |
| AV45 | 1025 | ctx-lh-precuneus | MCI | 237 | -0.0012 | [-0.0036, +0.0013] | 0.0155 | 0.987 | 0.987 | [-0.0388, +0.0365] | 0.3575 | 0.8486 |
| FDG | 1025 | ctx-lh-precuneus | CN | 371 | -0.0010 | [-0.0030, +0.0011] | 0.0159 | 0.918 | 0.918 | [-0.0402, +0.0383] | 0.346 | 0.9198 |
| FDG | 1025 | ctx-lh-precuneus | AD | 303 | +0.0012 | [-0.0010, +0.0035] | 0.0155 | 0.967 | 0.967 | [-0.0372, +0.0397] | 0.2699 | 0.9230 |
| FDG | 1025 | ctx-lh-precuneus | MCI | 483 | +0.0006 | [-0.0011, +0.0024] | 0.0157 | 0.956 | 0.956 | [-0.0372, +0.0384] | 0.4699 | 0.9858 |

**Table note.** The CSVs provide separate lower and upper columns for the mean-difference CI and Bland–Altman limits, as well as an explicit Bland–Altman bias column. BH-FDR q-values come unchanged from the original 98-ROI family for each tracer × diagnostic group. A non-significant paired difference does not establish equivalence or subject-level agreement.
