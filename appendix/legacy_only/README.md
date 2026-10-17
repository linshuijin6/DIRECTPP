# DIRECTPP (DIReCT++) Project Workspace

> **Associated Manuscript**: *Precision Synthesis of Multi-Tracer PET via VLM-Modulated Rectified Flow for Stratifying Mild Cognitive Impairment*
> **Manuscript ID**: BMEF-D-26-00169 (BME Frontiers, Major Revision)
> **Owner**: linshuijin (replicated from liutuo's original project)
> **Execution Node**: Available across compute nodes via /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP

---

## 1. Directory Structure

- 1_code/:
  - 
otebooks/: Core training & inference notebooks (mri2pet _two trace_new-final.ipynb, mri2pet _two trace_github.ipynb, mri2pet _clip_pretrain -Copy1.ipynb for Eq. 1 optimization)
  - generative/: MONAI Generative Models package (3D Rectified Flow UNet, schedulers, inferers)
  - BiomedCLIP/: Local pretrained BiomedCLIP model weights and tokenizers
  - liutuo_utils.py: 3D visualization, metrics, and helper functions
- 2_checkpoints/:
  - low_generator/: Converged Rectified Flow checkpoints (irst_part_165.pth used for final evaluation and GitHub, irst_part_150Best.pth)
  - 	ext_features/: Optimized modality guidance vectors from Eq. (1) with $\tau=0.82$ (v45_text_feature.pt, dg_text_feature.pt, image feature vectors)
  - classification/: 3-Fold cross-validation checkpoints (est_model_fold_1.pth, est_model_fold_2.pth, est_model_fold_3.pth, est_metric_model_classification3d_array.pth)
- 3_classification/:
  - DenseNet-3D classification notebooks for AD vs CN, MCI vs CN, EMCI vs LMCI under 3-fold cross-validation with full cell outputs preserved.
- 4_analysis_and_figures/:
  - scripts/: Figure plotting & statistical testing scripts (	iqintu.py, iolin.py, rain_labels.json, shuijin_code.ipynb, shuijin rader figure.ipynb, paper data statistics .ipynb)
  - statistics_av45/ & statistics_fdg/: Subject-level SUV means across all 98 SynthSeg anatomical brain regions (egion_*.csv). Ready for ICC/CCC, Bland-Altman, and TOST analyses without re-inference.
- 5_data_splits/:
  - metadata/: Complete cohort metadata iltered_subjects_with_description.csv (1,857 unique subjects, strict subject-disjoint).
  - splits/: 	rain_data_with_description.json (500 subjects) & al_data_with_description.json (39 subjects).
  - ebuild_core_split_subject_disjoint.py: Subject-level partition verification script.
- 6_test_eval_results/:
  - 	est1_baselines/: Pre-generated 3D PET volumes across all comparator methods (CycleGAN, Swin-UNet, DDIM, SegGuidedDif, Rectified Flow baseline, Ours).
  - oasis_external/: OASIS-3 external validation generated volumes.
- data/:
  - data_augmentation_av45_generated/: Synthesized AV-45 PET volumes for downstream classifiers.
  - data_augmentation_fdg_generated/: Synthesized FDG PET volumes for downstream classifiers.

---

## 2. Python Environment

The original verified conda environment is:
`ash
conda activate /home/pnxc/Anaconda3/envs/xiaochou
# or directly:
/home/pnxc/Anaconda3/envs/xiaochou/bin/python
`
Core packages:
- PyTorch: 2.6.0+cu118 (CUDA enabled)
- MONAI: 1.5.1
- Transformers: 4.40.2
- Scikit-learn: 1.7.2
- Pandas: 2.2.3

