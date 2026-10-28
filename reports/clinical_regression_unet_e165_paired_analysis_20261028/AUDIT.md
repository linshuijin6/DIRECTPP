# Epoch 165 paired-analysis audit

## Conclusion

**PASS — no material fairness blocker was identified for the prespecified matched-input, whole-framework comparison.** Exactly 2,963 Epoch 165 subject–tracer identities were joined one-to-one on `(PTID, tracer, fold, epoch)`. No duplicate key, missing key, cross-fold subject assignment, or non-finite metric value was found. Statistical interpretation was therefore allowed to proceed.

This conclusion is limited to the frozen OOF outputs and the identities documented below. It does not certify the historical paper run, repeated-training robustness, clinical validity, or the provenance of upstream-filled clinical values.

## OOF coverage

| Tracer | Fold 1 | Fold 2 | Total |
|---|---:|---:|---:|
| FDG | 792 | 806 | 1,598 |
| AV45 | 690 | 675 | 1,365 |

The joined keys exactly equal the effective-tracer identities derived from the frozen split manifest; no subject or tracer row was excluded after inspection.

## Fairness and implementation identity

- **Cohort and split:** both experiments bind to the same 1,857-subject cohort hash, the same two-fold split-manifest hash, and the same 5,571-file MRI/FDG/AV45 content-hash manifest. Each subject belongs to one held-out fold only.
- **Target and grid:** the regression U-Net reads the frozen Full preprocessing cache and exposes only MRI, FDG, and AV45 tensors plus its newly encoded clinical vector. Receipts and configuration checks identify the same `(1, 160, 192, 160)` tensors and the same valid-tracer counts.
- **Preprocessing:** Full applies LPI orientation, MRI foreground crop, MRI histogram normalization, resize/pad/crop to `160×192×160`, 1-mm spacing, per-volume intensity normalization, and scaling. The regression baseline reuses those cached tensors instead of recomputing preprocessing.
- **Postprocessing and metrics:** both inference paths clamp predictions to `[0,1]` and use 3D SSIM (`data_range=1`, kernel 7), PSNR (`max_val=1`), voxelwise MSE, and voxelwise MAE over the complete preprocessed volume. These are **not** brain-mask-restricted metrics.
- **Clinical information:** both receive age, sex, weight, CDR, MMSE, GDS, FAQ, and NPI-Q plus tracer identity. All 1,857 regression rows match the numerical values rendered in the frozen Full text descriptions.
- **Allowed encoding difference:** Full encodes the eight rendered values and tracer descriptions using BiomedCLIP and cross-attention. The regression U-Net fold-standardizes the seven continuous values, encodes sex as F=0/M=1, appends a two-element tracer one-hot, and maps the 10-vector through an MLP to bottleneck FiLM parameters.
- **Allowed architectural difference:** Full is the reconstructed conditional 3D velocity/residual framework; the comparator is a deterministic four-level direct-regression 3D U-Net. The result is a whole-framework matched-information comparison, not a causal ablation of Rectified Flow, BiomedCLIP, or any single component.

## Material limitations retained

- Full used the author-notebook unseeded training policy, whereas the regression baseline used seed 42. Each method has one frozen two-fold OOF training realization; subject-level uncertainty does not estimate across-seed or retraining uncertainty.
- The eight clinical fields are historical filled values. The bounded source audit did not recover the upstream filling method, visit alignment, or prove the absence of target-dependent shortcuts/leakage. Therefore this comparison cannot exclude shortcut effects from clinical-value provenance.
- Intensities are normalized uptake scaled to `[0,1]`, not clinical SUVR. Whole-volume SSIM/PSNR/MSE/MAE cannot establish pathology-region fidelity or individual amyloid-status agreement.
- Full results are a new author-code-semantics reconstruction and must not be described as the original paper's historical experiment.

## Strict integrity checks

| Check | Result |
|---|---|
| full metrics hash matches completion | PASS |
| full metrics hash matches analysis manifest | PASS |
| unet metrics hash matches completion | PASS |
| full completion status and primary epoch | PASS |
| unet completion status and primary epoch | PASS |
| full cohort hash matches config | PASS |
| full split hash matches config | PASS |
| unet reuses full config hash | PASS |
| unet reuses full cohort hash | PASS |
| unet reuses full split hash | PASS |
| unet reuses full input hash manifest | PASS |
| full input hash receipt matches manifest | PASS |
| full conditioning shapes match contract | PASS |
| full cache binds input and condition hashes | PASS |
| unet clinical features hash matches config | PASS |
| clinical metadata hash matches config | PASS |
| clinical source receipt hash matches config | PASS |
| unet runner hash matches config | PASS |
| unet model hash matches config | PASS |
| full model hash matches config | PASS |
| config check pass | PASS |
| prepare receipt pass | PASS |
| split manifest reused not regenerated | PASS |
| diagnosis not used by unet | PASS |
| biomedclip not used by unet | PASS |
| sample grid is 1x160x192x160 | PASS |
| clinical fields are required eight | PASS |
| unet fold1 receipt epoch165 | PASS |
| unet fold1 metrics hash matches receipt | PASS |
| unet fold1 expected counts in receipt | PASS |
| unet fold1 postprocessing clamp only | PASS |
| unet fold2 receipt epoch165 | PASS |
| unet fold2 metrics hash matches receipt | PASS |
| unet fold2 expected counts in receipt | PASS |
| unet fold2 postprocessing clamp only | PASS |
| full no duplicate keys | PASS |
| full all metrics finite | PASS |
| full valid tracers | PASS |
| full valid folds | PASS |
| full nonnegative error metrics | PASS |
| full one held out fold per subject | PASS |
| full expected tracer fold counts | PASS |
| unet no duplicate keys | PASS |
| unet all metrics finite | PASS |
| unet valid tracers | PASS |
| unet valid folds | PASS |
| unet nonnegative error metrics | PASS |
| unet one held out fold per subject | PASS |
| unet expected tracer fold counts | PASS |
| full and unet key sets identical | PASS |
| metrics equal manifest valid tracer set | PASS |
| expected total subject tracer pairs | PASS |
| clinical features cover full cohort | PASS |
| clinical values match full descriptions | PASS |
| same metric implementations in source | PASS |
| both inference paths clamp 0 1 | PASS |
| full preprocessing contract present | PASS |
| unet reuses frozen full tensors | PASS |

## Frozen input SHA-256

| Input | SHA-256 |
|---|---|
| `reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv` | `814bf7d13a1dae5591d3eb3964392e7419f00ff4fd6a18b9bc3c16c436f6091b` |
| `reports/original_author_reproduction_20261020/config.json` | `7f6753b63ba879f37b569d9adee5e7df83c3267d009fc5992ed3ce6c5730036a` |
| `reports/original_author_reproduction_20261020/oof_summary/completion.json` | `7dff000647b4fbf798a45906bc980af23d9806baab19f33a3cb18d0ba5bed525` |
| `reports/original_author_reproduction_20261020/oof_summary/analysis_manifest.json` | `f33c1884c890f4f66fe349b901a6b7dda00a1bba6af7e0541708706d1762c394` |
| `reports/original_author_reproduction_20261020/cohort.json` | `91ee8eeec5ea853c4517df868e85fccd2857164a8e4171ba81e45121e5dc9311` |
| `reports/original_author_reproduction_20261020/split_manifest.csv` | `007e49835ed44c73dea69a94e390dded33c495c21033089f83d05b429519977c` |
| `reports/original_author_reproduction_20261020/input_hashes.csv` | `3f362cdb3ebe8a945b106cc6974e4fbcea9e450474f3cc1f0db28a88ce81ed07` |
| `reports/original_author_reproduction_20261020/input_hashes_receipt.json` | `d38ff430fc8b6ae082ae3b99521e4f513bd5fe5b59c4dbfd9f4fdf28e1337b0b` |
| `reports/original_author_reproduction_20261020/conditioning_receipt.json` | `c4ca0de3ecafcc321ad15430bf5c2694948c898b407b92966ef84533310af186` |
| `reports/original_author_reproduction_20261020/persistent_cache_receipt.json` | `3b22b5d094a588daa9b991376fe1e0e3b27d293e25027083101a5db465313bb7` |
| `experiments/original_author_reproduction/run.py` | `1811340c23d498b5aad1da4f64d68f3a8dd51691f60ff71cfb011e2fa15c3eec` |
| `source_archive/vscode-3002/home/ssddata/liutuo/generative/networks/nets/diffusion_model_unet.py` | `b56b1956b787e85f52fc1a7f46884fea2cbfff81f9c31311db462dda7b378bcc` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/oof_summary/per_subject_metrics.csv` | `1671862dc4ceaca6c877991087e1f84b928e7ebc6adc2304f1ee8efb48057a4f` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/config.json` | `9257a3ba28d3015dae5c47b6b6187d2bb3ae22eaa5850548f28f676f65632ddc` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/oof_summary/completion.json` | `95384d94eb185d6655863d4c8a22970da4362f2b852d0545b1db66f25fc4b31a` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/clinical_features.csv` | `3ef34d4eac02a9e02e7ed73ad3d8b466c6532174232c23117fe208396fa82693` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/config_check.json` | `37f31a2e2ba6474ddee69cc7c1250c21adb63c2dce87e698c6f31911805e4c2d` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/prepare_receipt.json` | `fecd9463d7d5a96bfe3af8b70c69e8a139dd9f9fc7bcbc914651805a54e51b8c` |
| `experiments/clinical_regression_unet/run.py` | `d9f65bf2b2a202d7018db0626a8b09fad37910eddb1377f8784184e6f32808a1` |
| `experiments/clinical_regression_unet/model.py` | `70541de08b5f19cbba4ea04b98002af2b82482bcb301881c0466b4451dc00094` |
| `reports/e1_stage01_20261017/metadata.csv` | `ab18b0439512c0460aa034b6d57be7df72f692209e6ff60eb0e7c064aced8445` |
| `reports/e1_stage01_20261017/clinical_source_receipt.json` | `4caa5dcfc7b742e0974513fa7951d078426f42da11c80bed1650d2104c1b7717` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/oof/epoch165/fold1/metrics.csv` | `9246b311231dffe49435a1fa2d2542462e9f8a97abc772192bdb1765cbcf6ff3` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/oof/epoch165/fold1/complete.json` | `d4e9cb0a4bf7c5a8364aa734dc409333968bad5cc99ecaa094b3413c2c040367` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/oof/epoch165/fold2/metrics.csv` | `3e642b563337e47f1405a2bdf8748a8fb767afdb1be6fc8d6e781c4c57947d74` |
| `reports/clinical_regression_unet_task_a_20261027_instance1/oof/epoch165/fold2/complete.json` | `cadddc46914a172290b224d82c89c2075aba94141b3d918d21d161ec39bf37f9` |
