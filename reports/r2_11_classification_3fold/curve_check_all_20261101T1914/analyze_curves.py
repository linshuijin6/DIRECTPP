"""Inspect every completed fit in the frozen snapshot; never alter training."""
from pathlib import Path
import json
import math

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
TASK = {"mci_cn": "EMCI+LMCI vs CN", "ad_cn": "AD vs CN", "emci_lmci": "EMCI vs LMCI"}
COND = {"mri": "MRI", "mri_real_fdg": "MRI + Real FDG", "mri_syn_fdg": "MRI + Syn FDG",
        "mri_real_av45": "MRI + Real AV45", "mri_syn_av45": "MRI + Syn AV45",
        "mri_real_both": "MRI + Real FDG + Real AV45", "mri_syn_both": "MRI + Syn FDG + Syn AV45"}
STABLE = "末20轮低loss"
RECOVERED = "末段反弹后回落，需观察"
UNSTABLE = "末10轮仍明显反弹"
snap = json.loads((ROOT / "snapshot.json").read_text())
rows, windows, problems, data = [], [], [], []

for entry in sorted(snap["entries"], key=lambda x: (x["task"], x["condition"], x["fold"])):
    source = ROOT / "sources" / entry["id"]
    if not (source / "history.csv").is_file():
        problems.append(dict(id=entry["id"], issue="history missing"))
        continue
    h = pd.read_csv(source / "history.csv")
    meta = json.loads((source / "summary.json").read_text())
    v = h[h.val_ACC.notna()].copy()
    checks = dict(epochs_complete=h.epoch.tolist() == list(range(1, 201)),
                  validation_schedule=v.epoch.tolist() == list(range(2, 201, 2)),
                  finite_loss=bool(np.isfinite(h.loss).all() and h.loss.ge(0).all()),
                  valid_validation_scores=bool(np.isfinite(v[["val_ACC", "val_AUC"]].to_numpy()).all()
                      and v[["val_ACC", "val_AUC"]].ge(0).all().all()
                      and v[["val_ACC", "val_AUC"]].le(1).all().all()),
                  completed_fit=meta.get("status") == "complete" and meta.get("epochs") == 200,
                  one_test_recorded=meta.get("test_evaluations") == 1,
                  checkpoint_file_exists=entry["best_checkpoint_exists"])
    best = v.loc[v.val_ACC.idxmax()]
    saved = h.loc[h.checkpoint_s > 0, "epoch"]
    checks["checkpoint_selection_record"] = bool(int(best.epoch) == meta["best_epoch"]
        and np.isclose(best.val_ACC, meta["best_validation_ACC"])
        and len(saved) and int(saved.iloc[-1]) == meta["best_epoch"])
    for key, passed in checks.items():
        if not passed:
            problems.append(dict(id=entry["id"], issue=key))

    early, late = h[h.epoch <= 20], h[h.epoch >= 151]
    tail20, tail10 = h[h.epoch >= 181], h[h.epoch >= 191]
    ve, vl = v[v.epoch <= 50], v[v.epoch >= 151]
    # Descriptive amplitude groups, NOT a universal scientific convergence test.
    category = STABLE if tail20.loss.max() <= .01 else UNSTABLE if tail10.loss.max() > .1 else RECOVERED
    row = dict(id=entry["id"], instance=entry["instance"], task=entry["task"],
               condition=entry["condition"], fold=entry["fold"], curve_category=category,
               first_loss=float(h.loss.iloc[0]), last_loss=float(h.loss.iloc[-1]),
               early20_loss_mean=float(early.loss.mean()), late50_loss_mean=float(late.loss.mean()),
               late50_loss_max=float(late.loss.max()), tail20_loss_mean=float(tail20.loss.mean()),
               tail20_loss_max=float(tail20.loss.max()), tail10_loss_mean=float(tail10.loss.mean()),
               tail10_loss_max=float(tail10.loss.max()), best_ACC_epoch=int(best.epoch),
               best_validation_ACC=float(best.val_ACC), AUC_at_selected_checkpoint=float(best.val_AUC),
               best_validation_AUC=float(v.val_AUC.max()),
               best_AUC_epoch=int(v.loc[v.val_AUC.idxmax(), "epoch"]),
               late50_val_ACC_mean=float(vl.val_ACC.mean()), late50_val_AUC_mean=float(vl.val_AUC.mean()),
               late50_val_AUC_min=float(vl.val_AUC.min()), late50_val_AUC_max=float(vl.val_AUC.max()),
               early50_val_AUC_mean=float(ve.val_AUC.mean()),
               late_minus_early_val_AUC=float(vl.val_AUC.mean() - ve.val_AUC.mean()),
               record_checks_pass=all(checks.values()), source=entry["source"])
    rows.append(row)
    data.append((entry, meta, h, v, best, category))
    for lo, hi in [(1, 20), (21, 50), (51, 100), (101, 150), (151, 200)]:
        a, b = h[h.epoch.between(lo, hi)], v[v.epoch.between(lo, hi)]
        windows.append(dict(id=entry["id"], first_epoch=lo, last_epoch=hi,
                            loss_mean=float(a.loss.mean()), loss_min=float(a.loss.min()), loss_max=float(a.loss.max()),
                            val_ACC_mean=float(b.val_ACC.mean()), val_ACC_max=float(b.val_ACC.max()),
                            val_AUC_mean=float(b.val_AUC.mean()), val_AUC_max=float(b.val_AUC.max())))

table = pd.DataFrame(rows)
table.to_csv(ROOT / "convergence_summary.csv", index=False)
pd.DataFrame(windows).to_csv(ROOT / "window_statistics.csv", index=False)
counts = table.curve_category.value_counts().to_dict()
result = dict(snapshot_cutoff_utc=snap["cutoff_utc"], expected_fits=snap["completed_fit_count"],
              inspected_fits=len(rows), counts_by_task=table.task.value_counts().to_dict(),
              descriptive_curve_groups=counts, issues=problems,
              grouping_note="Descriptive groups: max loss in epochs181-200<=0.01; otherwise max loss in191-200>0.1 flags late rebound; all other fits are a recovery/watch group. These are not preregistered convergence thresholds or stopping rules.",
              best_epoch_median=float(table.best_ACC_epoch.median()),
              best_epoch_min=int(table.best_ACC_epoch.min()), best_epoch_max=int(table.best_ACC_epoch.max()),
              best_epoch_le100=int(table.best_ACC_epoch.le(100).sum()),
              best_epoch_gt100=int(table.best_ACC_epoch.gt(100).sum()),
              validation_loss_logged=False,
              no_test_metrics_used=True, training_unchanged=True)
(ROOT / "audit.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "axes.spines.top": False, "axes.spines.right": False})
blue, orange, dark = "#235789", "#C46B20", "#454545"
minimum = min(float(h.loss[h.loss > 0].min()) for _, _, h, _, _, _ in data)
maximum = max(float(h.loss.max()) for _, _, h, _, _, _ in data)
ylo, yhi = 10 ** math.floor(math.log10(minimum)), 10 ** math.ceil(math.log10(maximum))
(ROOT / "curves").mkdir(exist_ok=True)
(ROOT / "overviews").mkdir(exist_ok=True)


def draw(pair, item, compact=False):
    entry, meta, h, v, best, category = item
    left, right = pair
    left.semilogy(h.epoch, h.loss, color=blue, linewidth=1.2)
    left.set_ylim(ylo, yhi)
    left.set_ylabel("Training CE (log)")
    right.plot(v.epoch, v.val_ACC, color=blue, linewidth=1.1, label="Val ACC")
    right.plot(v.epoch, v.val_AUC, color=orange, linestyle="--", linewidth=1.1, label="Val AUC")
    right.scatter([best.epoch], [best.val_ACC], color=dark, marker="*", s=55 if compact else 90, zorder=5)
    right.set_ylim(0, 1)
    right.set_ylabel("Internal validation")
    right.legend(loc="lower right", frameon=False, fontsize=7 if compact else 9)
    for ax in pair:
        ax.axvline(best.epoch, color=dark, linestyle=":", linewidth=.9)
        ax.axvspan(151, 200, color="#C7C7C7", alpha=.16, zorder=0)
        ax.set_xlim(1, 200); ax.set_xticks([1, 50, 100, 150, 200]); ax.set_xlabel("Epoch")
        ax.grid(axis="y", alpha=.18)
    title = f"{TASK[entry['task']]} | {COND[entry['condition']]}\nFold {entry['fold']}, instance {entry['instance']}"
    left.set_title(title, fontsize=8 if compact else 10)
    right.set_title(f"Selected epoch {int(best.epoch)} | ACC {best.val_ACC:.3f}", fontsize=8 if compact else 10)


with PdfPages(ROOT / "all_training_curves.pdf") as pdf:
    for item in data:
        fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4), constrained_layout=True)
        draw(axes, item)
        e, meta, *_ = item
        fig.suptitle(f"Train n={meta['split_sizes']['train']}; validation n={meta['split_sizes']['validation']}"
                     " | Raw curves; gray window = epochs151-200; star = selected checkpoint", fontsize=10)
        fig.savefig(ROOT / "curves" / (e["id"] + ".png"), dpi=160)
        pdf.savefig(fig); plt.close(fig)

for start in range(0, len(data), 6):
    subset = data[start:start + 6]
    fig, axes = plt.subplots(3, 4, figsize=(18, 10.5), constrained_layout=True)
    for i in range(6):
        r, c = divmod(i, 2)
        pair = [axes[r, 2*c], axes[r, 2*c+1]]
        if i < len(subset):
            draw(pair, subset[i], compact=True)
        else:
            for ax in pair: ax.set_visible(False)
    fig.suptitle(f"Completed-fit curve audit | models {start+1}-{start+len(subset)} of {len(data)}"
                 " | gray window: epochs151-200", fontsize=12)
    fig.savefig(ROOT / "overviews" / f"overview_{start//6+1:02d}.png", dpi=160)
    plt.close(fig)

lines = ["# 已完成分类模型的训练曲线核验", "", f"快照截止 UTC：{snap['cutoff_utc']}（北京时间19:15左右）。",
         f"共 {len(rows)} 个模型：21个EMCI+LMCI/CN、8个AD/CN；本快照尚无已完成EMCI/LMCI。检查期间新增完成模型未滚动纳入。",
         "", "## 结论", "", "不能将全部模型概括为稳定收敛。训练loss普遍明显下降，但末段稳定性存在差异：", "",
         f"- {counts.get(STABLE, 0)} 个：最后20轮loss始终不超过0.01，末段处于低量级。",
         f"- {counts.get(RECOVERED, 0)} 个：最后20轮存在反弹，最后10轮已回落至较低量级，仍需留意稳定性。",
         f"- {counts.get(UNSTABLE, 0)} 个：最后10轮仍出现loss超过0.1的明显反弹，不能称为末段稳定。",
         "", "上述0.01/0.1仅为描述曲线幅度的分组，不是预设的科学收敛界值，也不是新训练停止规则。",
         f"日志与checkpoint选择记录核验问题数：{len(problems)}。未以训练loss接近零推断泛化性能优良。",
         "", "## 重点观察模型", "", "| 任务/输入/折 | 最后一轮loss | 最后10轮最大loss | 最佳ACC轮 | 最佳验证ACC |", "|---|---:|---:|---:|---:|"]
for x in rows:
    if x["curve_category"] == UNSTABLE:
        lines.append(f"| {TASK[x['task']]} / {COND[x['condition']]} / F{x['fold']} | {x['last_loss']:.6f} | {x['tail10_loss_max']:.4f} | {x['best_ACC_epoch']} | {x['best_validation_ACC']:.2%} |")
lines += ["", "这三例并无NaN/Inf或持续数值爆炸，但末期仍有优化波动。完整训练和validation记录已保存；不能仅看最后一个epoch判定收敛。",
          "", "## 验证与checkpoint", "", f"最佳验证ACC的epoch范围 {result['best_epoch_min']}–{result['best_epoch_max']}，中位数 {result['best_epoch_median']:.0f}；{result['best_epoch_le100']}/{len(rows)} 在100轮以内，另有{result['best_epoch_gt100']}个在100轮以后，其中MRI-only MCI/CN fold2在172轮达到最高验证ACC。不能依据首个样本24轮的最佳点断言所有模型均可早停。",
          "", "有模型训练loss很低而验证AUC后期下降，例如MCI/CN MRI+Real FDG fold2：前50轮平均验证AUC约0.6715，最后50轮约0.6182。验证走势需与训练loss分开解释；本次不进行显著性检验，不把这些描述当作统计结论。",
          "", "29例均检查200个连续epoch、100个偶数轮validation点、有限loss和ACC/AUC、完成状态、单次test记录、best_model存在、首次最高验证ACC与summary最佳epoch及最后一次checkpoint保存轮次一致。这里核验的是选择记录，不额外认证checkpoint权重身份。",
          "", "未记录validation loss，因此不报告其趋势；未利用test分数选择模型或判断收敛，也未修改训练、学习率、验证频率或checkpoint。",
          "", "## 每例摘要", "", "loss均值为最后20轮；验证均值为最后50轮。", "", "| 模型 | 实例 | 首轮→末轮loss | 末20轮均值 | 末段形态 | 最佳ACC轮/值 | 后50轮验证ACC/AUC |", "|---|---:|---:|---:|---|---|---|"]
for x in rows:
    lines.append(f"| {TASK[x['task']]} / {COND[x['condition']]} / F{x['fold']} | {x['instance']} | {x['first_loss']:.4f}→{x['last_loss']:.6g} | {x['tail20_loss_mean']:.6g} | {x['curve_category']} | {x['best_ACC_epoch']} / {x['best_validation_ACC']:.2%} | {x['late50_val_ACC_mean']:.2%} / {x['late50_val_AUC_mean']:.4f} |")
lines += ["", "## 文件", "", "- all_training_curves.pdf：每个模型一页的原始训练loss与内部验证ACC/AUC曲线。",
          "- curves/：每个模型的PNG；overviews/：全部模型的分组总览图。",
          "- convergence_summary.csv：逐模型数值、描述性分组和记录核验；window_statistics.csv：分阶段统计。",
          "- snapshot.json及sources/：固定快照、远端来源和原始日志/summary副本；analyze_curves.py：可重算分析。"]
(ROOT / "REPORT.md").write_text("\n".join(lines) + "\n")
print(json.dumps(result, ensure_ascii=False, indent=2))
