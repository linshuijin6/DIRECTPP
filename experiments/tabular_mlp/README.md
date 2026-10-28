# Tabular-MLP clinical-token ablation

This isolated entrypoint reuses the completed Full DIReCT++ trainer and replaces
only the patient-specific BiomedCLIP text token with a trainable two-layer MLP:

`[age, sex, weight, CDR, MMSE, GDS, FAQ, NPI-Q] -> Linear(8,128) -> GELU -> Linear(128,512)`.

Continuous fields are standardized with the current training fold only. Sex is
deterministically encoded as female=0 and male=1. The output is one 512-D patient
token; the second 512-D tracer token is copied byte-for-byte from the actual Full
`conditions.pt`. The generator context therefore remains `[patient, tracer]` with
shape `[B,2,512]`.

The actual completed Full code uses the raw BiomedCLIP tracer text features; it
does not contain the fold-specific adapter implemented later in E1. This ablation
preserves the actual Full token rather than silently changing the comparator.

All rendered Full prompts contain the eight finite fields. Their historical
upstream filled-value/imputation mechanism and possible diagnosis dependence were
not recovered, so this experiment rejects missing/non-finite prompt values and
does not claim that those historical values were label-independent.

Run `prepare`, then `preflight --fold N --cuda`. Only after both fold preflights
pass, use `train --fold N`. Inference must pass the exact completed Full cache via
`--cache-dir`; endpoints remain epochs 165 and 200.
