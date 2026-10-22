```text
E1 Full：最终165 epoch两折OOF推理与指标

状态：COMPLETE；有效受试者1856人；可用PET配对2961例；精确覆盖冻结留出名单，无缺失、重复。
两折checkpoint均为epoch=164（已完成165 epoch），各153120次更新；模型、优化器有限且身份哈希匹配。

按受试者汇总的均值 ± 样本标准差：
FDG (n=1597): psnr=27.231770 ± 2.077298; ssim7=0.909826 ± 0.038579; ssim11=0.913075 ± 0.034497; mse=0.002198 ± 0.001934; mae=0.024437 ± 0.008549; roi_mae=0.042662 ± 0.021437; brain_mae=0.052354 ± 0.018903
AV45 (n=1364): psnr=24.910773 ± 2.199123; ssim7=0.863928 ± 0.036819; ssim11=0.862259 ± 0.036405; mse=0.003709 ± 0.002314; mae=0.031765 ± 0.009682; roi_mae=0.061204 ± 0.031270; brain_mae=0.068868 ± 0.023822

协议：原始160×192×160全体素网格、data_range=1，无二次归一化；SSIM为sigma=1.5的valid Gaussian窗口7与11。关闭cuDNN TF32，并在各折与原始CPU/GPU实现抽样核对，容差5e-5。
ROI MAE：每人98个冻结ROI中有效ROI的绝对均值差，再按人等权汇总；采用PET无关有效性过滤与冻结物理半球命名。
MSE为每人全体素平方误差均值；MAE为每人全体素绝对误差均值；brain_mae限制在冻结mask>0区域。PSNR按人计算再平均，不能由总体平均MSE倒算。

预测文件目录（未压缩NIfTI，完整索引及SHA见prediction_index.json）：
fold1: /home/linshuijin/DIRECTPP_E1/stage01_20261017/oof/Full_165epoch_20261020/fold1 (1479 files)
fold2: /mnt/datas230/users/linshuijin/DIRECTPP_E1/stage01_20261017/oof/Full_165epoch_20261020/fold2 (1482 files)

证据：summary.json、overall_summary.csv（含95%分层bootstrap CI）、per_subject_metrics.csv、per_fold_summary.csv、per_diagnosis_summary.csv、regions_long.csv、两折snapshot.json/complete.json、原始日志及退出码。
限制：这些是当前E1 Full最终两折OOF结果；No-Scores尚需完成后进行配对比较。所有强度仅称normalized uptake，不能写为SUVR、临床等效或历史论文协议复现。
```
