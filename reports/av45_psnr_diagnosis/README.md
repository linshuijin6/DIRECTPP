# AV45 PSNR diagnosis report

本目录是 Full OOF epoch 165 AV45 的静态诊断型可视化报告，只整理现有结果，不提供最终因果结论。

- `index.html`：直接打开的主报告。
- `summary.csv`：固定选择的 9 名受试者、已有指标、重算指标与强度分位数。
- `assets/`：全局指标图、9 人切片图和强度直方图。
- `generation_receipt.json`：数据口径、固定选择规则、来源哈希和一致性检查。
- `generate_report.py`：从现有 epoch 165 OOF 指标、预测和预处理缓存重新生成报告。

生成命令：

```sh
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python reports/av45_psnr_diagnosis/generate_report.py
```

脚本不训练模型，不运行推理，也不生成新的 PET 预测。
