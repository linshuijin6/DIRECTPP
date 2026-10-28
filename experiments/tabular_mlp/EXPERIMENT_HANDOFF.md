# Tabular-MLP experiment handoff

Status at 2026-10-28 20:02 Asia/Shanghai: both formal folds are running on the
two authorized 48 GB remote instances. Automatic follow-up processes will run
OOF inference at epochs 165 and 200 only after the corresponding training
`complete.json` exists. No classification, Full, OT, or 3D U-Net process was
stopped or modified.

## Implementation and reuse

- Deployed code commit: `3ae891e020c850641debb4dbb17d663f2329931d`.
- New files: `experiments/tabular_mlp/run.py`, `README.md`, and this handoff.
- Reused without source edits: `experiments/original_author_reproduction/run.py`
  owns the ReFlow generator, image transforms/cache, loss, Adam settings,
  200-epoch schedule, checkpointing, OOF inference, SSIM, PSNR, MSE, and MAE.
- Full versus MLP difference: the first context token changes from the frozen
  subject BiomedCLIP text feature to a trainable tabular MLP output. The second
  tracer token and `[B,2,512]` cross-attention interface are unchanged.
- MLP: `Linear(8,128) -> GELU -> Linear(128,512)`, one patient token, 67,200
  parameters. Generator: 9,925,921 parameters. Combined: 9,993,121 parameters.

## Clinical inputs and preprocessing

Fields, in fixed order: age, sex, weight, CDR, MMSE, GDS, FAQ, and NPI-Q.
These are parsed from the exact rendered Full prompt for each of the 1,857
subjects. Continuous fields use population-SD standardization fitted only on
the current training fold. Sex is deterministically encoded as female=0 and
male=1. Missing/non-finite prompt values are rejected; none were found.
Diagnosis, PET, and fold identity are not MLP inputs.

Fold normalization identities:

- Fold 1: 928 fit / 929 held out; SHA-256
  `ae4b87e0add4b8e5595f2975ff601188d1111e8b4eb3de18af65df108467628e`.
- Fold 2: 929 fit / 928 held out; SHA-256
  `31d36892acfeaa07894e3d190ffb71ffddf55c753c6f996246edf2444d33a4be`.

## Validation

- Subject split: PASS; held-out sizes 929/928, train/test overlap 0 in both
  folds, and the original split manifest was reused byte-for-byte.
- Shapes: PASS; clinical `[1,8]`, patient token `[1,1,512]`, tracer token
  `[1,1,512]`, cross-attention context `[1,2,512]`.
- Tracer preservation: PASS; copied Full `conditions.pt` SHA-256
  `bbcd413100d8ece3e878acffc1969723d091f64c49c57c76b486bd474f84384a`;
  runtime tracer tensor is byte-identical to Full.
- Full behavior: PASS; the Full trainer source hash remains
  `1811340c23d498b5aad1da4f64d68f3a8dd51691f60ff71cfb011e2fa15c3eec`,
  and the wrapper's generator has the same state hash as a Full generator made
  from the same fixture RNG state.
- Gradient: PASS; all MLP gradients were finite. Because the Full generator has
  a zero-initialized output layer, the first non-zero MLP gradient appeared at
  smoke step 3 (fold 1, L2 `6.9071e-12`) and step 4 (fold 2, L2 `5.7507e-11`).
- Optimizer step, checkpoint+optimizer reload, and inference reload: PASS on
  both instances; post-reload inference maximum absolute difference was 0.
- Cache: PASS; both instances use the exact 1,857-file Full namespace
  `v1_3f362cdb3ebe8a94_bbcd413100d8ece3`.

## Running folds and outputs

Shared asset root on both instances:
`/root/autodl-fs/DIRECTPP_tabular_mlp/20261028_v3` (resolves to
`/autodl-fs/data/DIRECTPP_tabular_mlp/20261028_v3`).

- Fold 1 / instance 1: training PID `275791`, GPU UUID
  `GPU-67973436-ddfb-1936-b0cb-2cf4e22aec41`; log
  `runtime/fold1_train.log`; output `formal/fold1`; inference follower PID
  `276087`, log `runtime/fold1_followup.log`.
- Fold 2 / instance 2: training PID `56339`, GPU UUID
  `GPU-beefc3a1-51aa-7a0e-9988-f6765abdddd9`; log
  `runtime/fold2_train.log`; output `formal/fold2`; inference follower PID
  `56596`, log `runtime/fold2_followup.log`.
- Instance 1 summary follower PID `276137` waits for all four OOF completion
  receipts, then runs the unchanged Full summarizer; log
  `runtime/summarize_followup.log`.

Both starts record the same config SHA-256
`16199d88e3812c905d26e89fa6d398d2ea53d00305e24abc47d8cc34f4e6bcf7`,
the original cohort/split/input/condition hashes, hardware identity, and fold
normalization hash. Formal training retains the Full policy `training_seed=null`.

The summary follower runs this reproducible command after all four OOF
directories exist (it can also be rerun manually only if `oof_summary/` does not
already exist):

```sh
cd /root/autodl-tmp/DIRECTPP_task_a
/root/miniconda3/bin/python experiments/tabular_mlp/run.py summarize \
  --config reports/tabular_mlp_20261028_v3/config.json
```

OOF predictions and per-subject metrics will appear under
`oof/epoch{165,200}/fold{1,2}` in the shared asset root. Summary CSV files will
appear under the instance-1 report's `oof_summary/`.

## Preserved failures and unresolved scientific risks

- Failed validation namespaces `20261028` and `20261028_v2` were retained. They
  document that an immediate non-zero MLP-gradient assumption was invalid for
  this zero-initialized generator; neither namespace entered formal training.
- The actual completed Full code uses raw BiomedCLIP tracer text features, not
  the later E1 fold-specific tracer adapter. This experiment preserves the
  actual Full tensor. It must not be described as preserving an adapted tracer
  token unless the Full comparator is also rerun with that adapter.
- The historical table contains filled clinical fields, but the upstream
  imputation mechanism and diagnosis dependence were not recovered. The MLP
  uses exactly the values seen by Full; this controls the encoder comparison but
  does not establish that the fields are label-independent.
- Full used no formal training RNG seed. Preserving that policy means Full and
  MLP have independent initializations; the resulting performance delta is not
  a paired-seed causal estimate of encoder choice.
- The completed Full evaluator computes whole normalized-volume SSIM/PSNR/MSE/
  MAE and does not apply a brain mask. This ablation reuses that exact evaluator;
  a claim of same-brain-mask evaluation would be inaccurate.
- Training and OOF are currently in progress. No scientific performance result
  should be reported until both fold completion receipts and all per-subject
  metric hashes have been checked.
