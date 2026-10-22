"""Validate completed native output and make a descriptive paper comparison."""
from pathlib import Path
import csv
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import statistics

import nibabel as nib

report = Path(__file__).resolve().parent
cfg = json.loads((report / "config.json").read_text())
work = Path(cfg["work"])
assert (work / "exit_code").read_text().strip() == "0", "Native job has not completed successfully"
summary = json.loads((work / "summary.json").read_text())
assert summary["status"] == "COMPLETE" and summary["subjects"] == 329
native = json.loads((work / "native_329_input_manifest.json").read_text())
legacy = json.loads(Path(cfg["manifest"]).read_text())
names = [r["name"] for r in native]
assert names == [r["name"] for r in legacy] and len(set(names)) == 329
rows = list(csv.DictReader((work / "per_subject_metrics.csv").open()))
assert len(rows) == len({(r["ptid"], r["tracer"]) for r in rows})
assert all(r["ptid"] in names for r in rows)
assert all(math.isfinite(float(r[k])) for r in rows for k in ["ssim", "psnr", "mse", "mae"])
checks = json.loads((work / "native_metric_cpu_gpu_check.json").read_text())
assert all(v["absolute_difference"] < 5e-5 for v in checks.values())

output = work / "native_outputs"
assert {p.name.removeprefix("real_mri_").removesuffix(".nii.gz") for p in (output / "data_augmentation_mri").glob("*.nii.gz")} == set(names)
header_checks = []
observed_by_tracer = {}
for tracer in ["fdg", "av45"]:
    observed = {r["ptid"] for r in rows if r["tracer"] == tracer}
    observed_by_tracer[tracer] = observed
    prediction_files = list((output / f"data_augmentation_{tracer}_generated").glob("*.nii.gz"))
    assert {p.name.removeprefix(f"generated_{tracer}_").removesuffix(".nii.gz") for p in prediction_files} == observed
    for path in prediction_files:
        image = nib.load(path)
        assert image.shape == (160, 192, 160)
    header_checks.append(dict(tracer=tracer, predictions=len(prediction_files), shape=[160, 192, 160]))
    current = {k: statistics.mean(float(r[k]) for r in rows if r["tracer"] == tracer)
               for k in ["ssim", "psnr", "mse", "mae"]}
    assert len(observed) == summary["results"][tracer]["n"]
    assert all(abs(current[k] - summary["results"][tracer][k]) < 1e-10 for k in current)

missing_av45 = sorted(set(names) - observed_by_tracer["av45"])
zero_av45 = sorted(r["name"] for r in native if Path(r["av45"]).name.endswith("_zero.nii.gz"))
assert missing_av45 == zero_av45
assert not (set(names) - observed_by_tracer["fdg"])

paper_path = Path(cfg["project_root"]) / "reports/baseline_metrics_provenance_20261020/paper_figure2_values.csv"
paper_rows = list(csv.DictReader(paper_path.open()))
comparison = []
for tracer, cohort in [("fdg", "ADNI_FDG"), ("av45", "ADNI_AV45")]:
    paper = next(r for r in paper_rows if r["cohort"] == cohort and r["method"] == "Ours")
    for metric, field, factor, unit in [("ssim", "SSIM_percent", 100, "percentage points"),
                                      ("psnr", "PSNR", 1, "dB"),
                                      ("mse", "MSE_percent", 100, "percentage points"),
                                      ("mae", "MAE_percent", 100, "percentage points")]:
        actual = summary["results"][tracer][metric] * factor
        reference = float(paper[field])
        comparison.append(dict(tracer=tracer, n=summary["results"][tracer]["n"], metric=metric,
                               paper=reference, replay=actual, delta=actual-reference, unit=unit))
with (report / "paper_comparison.csv").open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(comparison[0]))
    writer.writeheader()
    writer.writerows(comparison)

def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(8*1024**2), b""):
            h.update(block)
    return h.hexdigest()

checkpoint = json.loads((work / "checkpoint_receipt.json").read_text())
assert sha(cfg["checkpoint"]) == checkpoint["sha256"]
receipt = dict(status="PASS_FOR_NATIVE_REPLAY_COMPLETENESS", subjects=329, metric_rows=len(rows),
               input_order_matches_329=True, metric_means_recomputed=True,
               prediction_identity_and_header_checks=header_checks, native_cpu_gpu_checks=checks,
               missing_av45_due_to_zero_placeholder={"count": len(missing_av45), "ptids": missing_av45},
               checkpoint_unchanged=True, checkpoint_sha256=checkpoint["sha256"],
               actual_training_membership="UNRESOLVED; name-set inclusion is not a training receipt",
               original_author_cells_only_for_model_transform_inference_metrics=True,
               limitations=["329 PTIDs use original dual-tracer NIfTI/text inputs, not legacy single-tracer MAT inputs",
                            "Paper final test cohort/checkpoint aggregation binding remains unresolved",
                            "Current dependencies and FP32/TF32 settings are recorded; no historical bitwise claim"])

path = report / "REPORT.md"
text = path.read_text().replace("状态：运行中；不能将本文件当成完成报告。", "状态：全量完成，原始代码进程exit=0；逐人输出与预测文件完整性检查通过。")
if "\n全量结果及与原论文的数值比较\n" in text:
    text = text.split("\n全量结果及与原论文的数值比较\n", 1)[0] + "\n```\n"
lines = ["", "全量结果及与原论文的数值比较", "每项依次为：原论文 / 本次回放 / 回放−原论文。SSIM、MSE、MAE均按原表乘100。"]
for tracer in ["fdg", "av45"]:
    selected = [r for r in comparison if r["tracer"] == tracer]
    lines.append(f"{tracer.upper()} n={selected[0]['n']}：")
    lines.extend(f"  {r['metric'].upper()}: {r['paper']:.4f} / {r['replay']:.4f} / {r['delta']:+.4f}" for r in selected)
lines.extend(["这仅是固定329个PTID、152best及其原预处理下的数值回放；不把数值相近等同于论文协议被复现。",
              "AV45仅n=324，因为5人的原生清单指向_zero.nii.gz全零占位影像；原作者评估单元对这些人只执行FDG。名单：" + "、".join(missing_av45) + "。",
              "权重实际训练被试归属仍未认证；不能将JSON名为train解释为这329人必然训练过，也不能反向认证为独立测试。",
              f"总耗时：{summary['elapsed_seconds']/60:.2f}分钟；推理峰值allocated={summary['peak_allocated_bytes']/1024**3:.2f} GiB，reserved={summary['peak_reserved_bytes']/1024**3:.2f} GiB。",
              "这里是推理峰值，不能与训练显存直接比较。",
              "完整逐人指标和影像仍在artifacts/；对照表paper_comparison.csv，完整性收据verification.json。",
              "本轮没有训练、没有使用E1代码、没有按329人指标挑选权重。",
              "完成时间：" + datetime.now(timezone(timedelta(hours=8))).isoformat(), ""])
assert text.count("```") == 2
text = text.rsplit("```", 1)[0] + "\n".join(lines) + "```\n"
path.write_text(text)
receipt["report_sha256"] = sha(path)
receipt["paper_comparison_sha256"] = sha(report / "paper_comparison.csv")
(report / "verification.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n")
print(json.dumps(dict(results=summary["results"], comparison=comparison, verification=receipt["status"]), indent=2))
