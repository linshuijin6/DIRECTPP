# Mask-restricted PET image quality

| Model | Tracer | N | SSIM ↑ | PSNR (dB) ↑ | MSE ↓ | MAE ↓ |
| --- | --- | --- | --- | --- | --- | --- |
| DIReCT++ Full (e165) | FDG | 1597 | 0.91844 ± 0.04026 | 23.954 ± 2.271 | 0.004763 ± 0.004028 | 0.05257 ± 0.01921 |
| DIReCT++ Full (e165) | AV45 | 1364 | 0.86999 ± 0.06048 | 21.803 ± 2.602 | 0.007959 ± 0.005469 | 0.06845 ± 0.02394 |
| Clinical Regression 3D U-Net (e165) | FDG | 1597 | 0.90208 ± 0.04256 | 23.373 ± 2.019 | 0.005262 ± 0.003889 | 0.05509 ± 0.01795 |
| Clinical Regression 3D U-Net (e165) | AV45 | 1364 | 0.86098 ± 0.05868 | 21.529 ± 2.363 | 0.008237 ± 0.005320 | 0.06976 ± 0.02276 |
| Swin-UNETR (e200; MRI only) | FDG | 1597 | 0.89237 ± 0.03938 | 23.565 ± 2.013 | 0.004997 ± 0.003300 | 0.05404 ± 0.01672 |
| Swin-UNETR (e200; MRI only) | AV45 | 1364 | 0.83615 ± 0.05878 | 21.273 ± 2.429 | 0.008791 ± 0.005652 | 0.07228 ± 0.02363 |

Values are mean ± sample SD across subjects. SSIM is unitless; PSNR is in dB; MSE and MAE use squared and unsquared [0,1] normalized-uptake units, respectively. All models use byte-identical frozen target PET arrays and identical subject-specific masks. The mask is the frozen SynthSeg nonzero-label union, including cortex, white matter, subcortical structures, cerebellum, brainstem, ventricles and CSF; it is not a pure parenchymal mask. SSIM uses the existing E1 3D Gaussian implementation (kernel 7, sigma 1.5, data range 1) and only centers whose entire 7×7×7 window lies inside the mask. The frozen mask QC exclusion removes one subject from each tracer; no new exclusions or spatial/intensity transformations were applied. Full and Clinical U-Net use epoch 165; MRI-only Swin-UNETR uses the prespecified final epoch 200. All predictions are frozen two-fold OOF outputs.
