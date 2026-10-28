# Stage 4D generator-anchored classification

This directory implements the frozen 3 tasks × 2 outer folds × 4 input
conditions protocol.  It does not infer PET and never constructs synthetic-PET
paths from a filename template.

Static MRI/Real preflight (works before Stage 4C-4 completes):

```bash
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python \
  experiments/classification_2fold/run.py preflight \
  --conditions mri mri_real
```

After the completed Stage 4C-4 receipt and asset index are present, validate all
24 fits and all prediction SHA-256 values:

```bash
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python \
  experiments/classification_2fold/run.py preflight
```

Run or continue all 24 fits on one selected GPU:

```bash
CUDA_VISIBLE_DEVICES=4 \
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python \
  experiments/classification_2fold/run.py all \
  --authorization RUN_STAGE_4D_24_FITS
```

Run one fit with `fit --task ad_cn --outer-fold 1 --condition mri ...`.
Completed fits with matching identities are skipped by `all`; interrupted fits
resume from `last_state.pth`.  A mismatched or incomplete Stage 4C-4 receipt,
frozen-manifest SHA mismatch, cross-OOF train input, duplicate subject, missing
file, or output identity mismatch stops execution.
