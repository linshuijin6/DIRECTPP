# R2-5 fixed-weight cognitive-score removal: Stage 1 pilot

**Status: PILOT COMPLETE; full OOF not started.** This is inference-time conditioning sensitivity of the E1 Full model, not a retrained No-Scores ablation. Intensities are normalized uptake, not clinical SUV/SUVR.

## Execution and identity

The two commands below exited 0. They used the original inference nodes and their frozen asset roots. Each selected subject has both FDG and AV45, and belongs to the checkpoint's original held-out fold.

```sh
ssh 3002 'cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP && PYTHONDONTWRITEBYTECODE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True E1_ASSETS_ROOT=/home/linshuijin/DIRECTPP_E1/stage01_20261017 CUDA_VISIBLE_DEVICES=3 /home/pnxc/Anaconda3/envs/xiaochou/bin/python -u -B experiments/e1_clinical_conditioning/infer_score_removal.py --stage pilot --fold 1'
ssh 3003 'cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP && PYTHONDONTWRITEBYTECODE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True E1_ASSETS_ROOT=/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017 CUDA_VISIBLE_DEVICES=5 /home/data/linshuijin/.conda/envs/xiaochou/bin/python -u -B experiments/e1_clinical_conditioning/infer_score_removal.py --stage pilot --fold 2'
```

Both checkpoints are formal Full epoch index 164 (165 completed epochs), loaded strictly with the original `checkpoint_identity(cfg, fold, "Full")` checks. The alternative inference condition is recorded separately; it does not masquerade as a No-Scores-trained checkpoint.

| Fold | Held-out pilot subjects | Full checkpoint SHA-256 | Fold adapter SHA-256 |
|---|---|---|---|
| 1 | 067_S_2301; 052_S_4959 | `f9455190e0d427783860174ac5a2bbc08e906bfaadd225586d39b674b861f5e9` | `c9285ea53df7b198ab5c825fd32d76fba8b2c41ec7bc0bdcd17e9d88bc56be8c` |
| 2 | 018_S_4399; 137_S_4631 | `fc69fa4e84bb5a85a692eaf923e7db7676f86f2ffb55215c7de80989a767bc14` | `050b95e801e0755b942ac7f30b348906b2f5b700044c38acdf46254987e9d821` |

Frozen patient embedding SHA-256: Full `4d353ad1592613f67c6ef643033a0cbc243a858dc5feafa3410b9f3d7494cd80`; No-Scores `52d08a8935ad5d10ed6e5e979abc02d40b42aee05c1e4c96471054ec7b2c22ba`. No-Scores is the frozen Age + Sex + Weight prompt embedding, not an empty token. The per-subject CSV records cache/MRI, both patient vectors, tracer vector and prediction SHA-256. Both branches use the same in-memory MRI, tracer vector, checkpoint and native E1 FP16 prediction function; only the patient vector argument changes.

## Pilot comparison

Delta is **No-Scores minus Full** for ROI and brain-mask MAE against Real PET; positive means higher error. Voxel MAE measures Full versus No-Scores synthetic PET. All values below are in normalized uptake.

| Fold | Subject | Tracer | Δ ROI MAE | Δ brain MAE | Full–No-Scores voxel MAE |
|---|---|---|---:|---:|---:|
| 1 | 067_S_2301 | FDG | -0.000227 | +0.000188 | 0.001340 |
| 1 | 067_S_2301 | AV45 | -0.002003 | -0.001485 | 0.001783 |
| 1 | 052_S_4959 | FDG | +0.000620 | +0.000800 | 0.001204 |
| 1 | 052_S_4959 | AV45 | +0.000122 | +0.000056 | 0.000921 |
| 2 | 018_S_4399 | FDG | -0.000045 | -0.000001 | 0.000971 |
| 2 | 018_S_4399 | AV45 | -0.000171 | -0.000010 | 0.000859 |
| 2 | 137_S_4631 | FDG | -0.000023 | -0.000150 | 0.000477 |
| 2 | 137_S_4631 | AV45 | -0.001762 | -0.001234 | 0.000913 |

Descriptive pilot means: FDG Δ ROI MAE `+0.000081`, Δ brain MAE `+0.000209`, voxel MAE `0.000998`; AV45 Δ ROI MAE `-0.000954`, Δ brain MAE `-0.000668`, voxel MAE `0.001119`. Four subjects per tracer are too few for formal inference; no pilot p-values or CIs are reported. Per-subject PSNR and SSIM7/11 contrasts are in the CSVs.

All eight Full replays matched the original Full OOF NIfTI **exactly** (maximum and mean voxel absolute differences 0). All eight new NIfTI files were reloaded and their SHA-256 values independently checked against the prediction indexes. The eight `(subject, fold, tracer)` keys are unique, and original training/test subject sets are disjoint by the frozen receipts. The existing Full predictions and checkpoints were not changed.

## Full OOF readiness and stop point

The inference entrypoint has a separate `--stage full` mode. After explicit approval, run the following commands; they have **not** been run:

```sh
ssh 3002 'cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP && PYTHONDONTWRITEBYTECODE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True E1_ASSETS_ROOT=/home/linshuijin/DIRECTPP_E1/stage01_20261017 CUDA_VISIBLE_DEVICES=3 /home/pnxc/Anaconda3/envs/xiaochou/bin/python -u -B experiments/e1_clinical_conditioning/infer_score_removal.py --stage full --fold 1'
ssh 3003 'cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP && PYTHONDONTWRITEBYTECODE=1 PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True E1_ASSETS_ROOT=/mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017 CUDA_VISIBLE_DEVICES=5 /home/data/linshuijin/.conda/envs/xiaochou/bin/python -u -B experiments/e1_clinical_conditioning/infer_score_removal.py --stage full --fold 2'
```

Outputs will be separate from Full OOF at each node's E1 asset root under `oof/R2_5_FullWeights_NoScores_20261030/full/fold{1,2}`; shared metrics and receipts will be under `reports/r2_5_inference_score_removal_20261030/full/fold{1,2}`. After both folds complete, run `summarize_score_removal.py` to obtain FDG/AV45 paired means, 95% fold-stratified subject bootstrap CIs and within-endpoint Holm-adjusted primary comparisons. That summary entrypoint has only been syntax checked; it cannot be exercised against full data until the approved inference completes.

```sh
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python -B experiments/e1_clinical_conditioning/summarize_score_removal.py
```

The pilot supports proceeding: original Full replay and all identities passed. Current available storage exceeds the expected roughly 56 GiB for 2,961 new uncompressed volumes, but GPU availability should be checked again immediately before a full launch. Full inference remains stopped pending approval.
