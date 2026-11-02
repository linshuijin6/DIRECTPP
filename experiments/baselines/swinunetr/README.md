# SwinUNETR MRI-to-PET baseline

This isolated experiment implements the recovered MONAI 3D SwinUNETR candidate
as a single-tracer, MRI-only PET regression model. It uses the frozen Full
cohort, split and PersistentDataset cache; it does not create a new split.

## Frozen protocol

- MONAI `SwinUNETR`, `spatial_dims=3`, one input/output channel, `feature_size=48`.
  MONAI 1.5 has no `img_size` constructor argument; the full input remains
  `160×192×160`.
- Independent FDG and AV45 models for folds 1 and 2; each uses only valid PET
  targets from its training side. Placeholder zero targets are excluded.
- MSE, Adam at `1e-5`, batch size 1, 200 epochs, CUDA float16 autocast and
  activation checkpointing. No held-out validation or checkpoint selection.
- The recovered candidate loop used 800 epochs; this run uses the user-fixed
  200-epoch budget and does not claim that 200 matches Figure 2's final run.
- Every 10 epochs: append the training MSE summary and atomically update the
  rolling `recovery.pt`. Weight-only persistent milestones are epochs 50, 100,
  150 and 200. Epoch 200 is the only OOF evaluation endpoint.
- OOF inference is run once on each corresponding held-out fold after the
  final checkpoint is fixed. Predictions are clamped to `[0,1]`; metrics are
  full-volume 3D SSIM (range 1, kernel 7), PSNR (max 1), MSE and MAE.
- No fixed RNG seed was found in the recovered Swin training cells. Initial
  and recovery RNG states are recorded. The Full run also records no fixed
  training seed.

## Prepare and inspect

Use new, non-existing report and asset paths. Large checkpoints and predictions
belong under assets and must stay out of Git.

```bash
python experiments/baselines/swinunetr/run.py prepare \
  --full-config reports/original_author_reproduction_20261020/config.json \
  --cache-dir <verified-full-cache> \
  --out reports/swinunetr_2fold_20261029 \
  --assets <isolated-swinunetr-assets>

python experiments/baselines/swinunetr/run.py check-config \
  --config reports/swinunetr_2fold_20261029/config.json

python experiments/baselines/swinunetr/run.py smoke-test --size 64
```

The cache check compares the complete MONAI `pickle_hashing` key set with the
frozen cohort, then verifies a cached subject's identity, tensor shape and
finite values. It rejects missing or extra entries.

## Full-size cost preflight

Run only on an exclusive GPU or after a verified safe handoff. The allocation
system must provide a fresh JSON receipt with `allocation_status` (`EXCLUSIVE`
or `SAFE_HANDOFF`), `gpu_uuid`, `host`, `issued_utc`, `issued_by`, and
`protection_id`. Bind exactly that UUID through `CUDA_VISIBLE_DEVICES`. The
preflight creates a fresh model and optimizer, reads only FDG Fold 1 training
subjects from the Full cache, performs warm-up plus measured forward,
backward and optimizer steps, and writes `cuda_preflight.json`. It does not
touch formal run state or held-out data.

```bash
CUDA_VISIBLE_DEVICES=<allocated-gpu-uuid> \
  /home/pnxc/Anaconda3/envs/xiaochou/bin/python -B \
  experiments/baselines/swinunetr/run.py smoke-test \
  --cuda --full-sample --tracer FDG --steps 10 --warmup-steps 2 \
  --config reports/swinunetr_2fold_20261029/config.json \
  --resource-receipt <allocation-receipt.json>
```

Do not proceed to formal training if the full-size preflight fails, the cache
identity check fails, resource estimates exceed available compute/storage, or
the allocation receipt does not establish exclusive/safe-handoff ownership.

## Train, infer and summarize

Start only FDG Fold 1 for the initial instance. The runner requires the same
fresh allocation receipt and checks that its UUID matches the visible device.
Resume only from that tracer/fold's rolling recovery file.

```bash
CUDA_VISIBLE_DEVICES=<allocated-gpu-uuid> \
  /home/pnxc/Anaconda3/envs/xiaochou/bin/python -u \
  experiments/baselines/swinunetr/run.py train \
  --config reports/swinunetr_2fold_20261029/config.json \
  --tracer FDG --fold 1 --resource-receipt <allocation-receipt.json> \
  --log-path <assets>/logs/fdg_fold1.log

python experiments/baselines/swinunetr/run.py train \
  --config <config> --tracer FDG --fold 1 \
  --resource-receipt <fresh-allocation-receipt.json> \
  --log-path <assets>/logs/fdg_fold1.log \
  --resume <assets>/formal/FDG/fold1/recovery.pt

python experiments/baselines/swinunetr/run.py infer \
  --config <config> --tracer FDG --fold 1 --epoch 200
python experiments/baselines/swinunetr/run.py summarize --config <config>
```

After the FDG Fold 1 resource cost and run state are reviewed, schedule other
instances separately. This README does not authorize launching them.
