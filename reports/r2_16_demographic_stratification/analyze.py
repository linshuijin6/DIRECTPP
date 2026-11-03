#!/usr/bin/env python3
"""R2-16: fixed-model demographic subgroup evaluation, CPU only.

No training, inference, calibration, imputation or source writes. Run using the
project's xiaochou Python. A completed output is never silently overwritten.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import sys
import time
import traceback

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, confusion_matrix, roc_auc_score

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CLASSIFICATION = ROOT / "reports/r2_11_classification_3fold"
HELPER = CLASSIFICATION / "statistical_comparison/analyze.py"
TASKS = {"ad_cn": "AD vs CN", "mci_cn": "EMCI+LMCI vs CN",
         "emci_lmci": "EMCI vs LMCI"}
EXPECTED = {"ad_cn": 470, "mci_cn": 741, "emci_lmci": 436}
CONDITIONS = ["mri", "mri_real_fdg", "mri_syn_fdg", "mri_real_av45",
              "mri_syn_av45", "mri_real_both", "mri_syn_both"]
PRIMARY = ["mri", "mri_syn_both", "mri_real_both"]
LABELS = {"mri": "MRI", "mri_real_fdg": "MRI+Real FDG",
          "mri_syn_fdg": "MRI+Syn FDG", "mri_real_av45": "MRI+Real AV45",
          "mri_syn_av45": "MRI+Syn AV45", "mri_real_both": "MRI+Real dual PET",
          "mri_syn_both": "MRI+Syn dual PET"}
METRICS = ["ACC", "AUC", "SEN", "SPE", "balanced_ACC"]
GROUPS = [("overall", "All"), ("age", "Age <75"), ("age", "Age >=75"),
          ("sex", "Female"), ("sex", "Male")]
COMPARISONS = {"A": "mri", "B": "mri_real_both"}
SEED, REPEATS = 20261103, 5000
INPUTS = {
    "predictions": CLASSIFICATION / "final_summary/oof_predictions.csv",
    "splits": CLASSIFICATION / "splits.csv",
    "subjects": ROOT / "reports/r2_11_classification_subjects.csv",
    "observed": ROOT / "reports/e1_stage01_20261017/observed.csv",
    "metadata": ROOT / "reports/e1_stage01_20261017/metadata.csv",
    "clinical_receipt": ROOT / "reports/e1_stage01_20261017/clinical_source_receipt.json",
    "original_fold_metrics": CLASSIFICATION / "final_summary/fold_metrics.csv",
    "original_summary": CLASSIFICATION / "final_summary/summary_metrics.csv",
    "bootstrap_helper": HELPER,
    "analysis_script": Path(__file__).resolve(),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def selected(frame, subgroup):
    if subgroup == "All":
        return np.ones(len(frame), dtype=bool)
    if subgroup == "Age <75":
        return (frame.Age < 75).to_numpy()
    if subgroup == "Age >=75":
        return (frame.Age >= 75).to_numpy()
    return (frame.Sex == {"Female": "F", "Male": "M"}[subgroup]).to_numpy()


def independent_metrics(y, probability, predicted):
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    sen, spe = tp / (tp + fn), tn / (tn + fp)
    return np.array([accuracy_score(y, predicted), roc_auc_score(y, probability),
                     sen, spe, (sen + spe) / 2])


def format_ci(row, metric, delta=False):
    key = metric + ("_delta_pp" if delta else "_mean_pct")
    sign = "+" if delta else ""
    return (f"{row[key]:{sign}.2f} [{row[metric+'_ci_low']:{sign}.2f}, "
            f"{row[metric+'_ci_high']:{sign}.2f}]")


def main():
    start = time.perf_counter()
    if (HERE / "complete.json").exists():
        raise FileExistsError("Completed analysis exists; use an independent directory to rerun")
    hashes = {k: sha(v) for k, v in INPUTS.items()}
    config = dict(seed=SEED, repeats=REPEATS, age_cutoff_years=75,
                  age_bands=["<75", ">=75"], sex_values=["F", "M"],
                  tasks=TASKS, expected_subjects=EXPECTED, conditions=CONDITIONS,
                  primary_conditions=PRIMARY, groups=GROUPS, comparisons=COMPARISONS,
                  positive_classes={"ad_cn": "AD", "mci_cn": "EMCI+LMCI", "emci_lmci": "LMCI"},
                  prediction_threshold=0.5, imputation="none", pooled_auc=False,
                  point_estimate="equal mean of the three within-fold subgroup metrics",
                  bootstrap="paired by PTID across conditions, within task/fold/subgroup/label",
                  rng="NumPy default_rng PCG64; task/group/fold/label order in script",
                  interval="marginal 95% percentile, NumPy linear method; no multiplicity correction",
                  scope="conditional on fixed models/splits and observed subgroup class counts",
                  visit_alignment="unverified: recovered export lacks EXAMDATE/VISCODE",
                  started_utc=datetime.now(timezone.utc).isoformat(), input_sha256=hashes)
    config_path = HERE / "analysis_plan.json"
    if config_path.exists():
        old_config = json.loads(config_path.read_text())
        assert old_config["input_sha256"] == hashes, "Inputs or script changed since plan was frozen"
    else:
        write_json(config_path, config)  # Freeze decisions before computing subgroup performance.
    manifest = pd.DataFrame([dict(name=k, path=str(v.relative_to(ROOT)),
                                  sha256=hashes[k], size_bytes=v.stat().st_size)
                             for k, v in INPUTS.items()])
    manifest.to_csv(HERE / "input_manifest.csv", index=False)
    spec = importlib.util.spec_from_file_location("existing_classification_statistics", HELPER)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    weighted_metrics = helper.weighted_metrics

    p = pd.read_csv(INPUTS["predictions"], dtype={"PTID": str}, float_precision="round_trip")
    splits = pd.read_csv(INPUTS["splits"], dtype={"PTID": str})
    subjects = pd.read_csv(INPUTS["subjects"], dtype={"PTID": str})
    demographic_cols = ["Subject ID", "Age", "Sex", "Research Group"]
    observed = pd.read_csv(INPUTS["observed"], usecols=demographic_cols)
    metadata = pd.read_csv(INPUTS["metadata"], usecols=demographic_cols)
    assert observed["Subject ID"].is_unique and metadata["Subject ID"].is_unique
    pd.testing.assert_frame_equal(observed.sort_values("Subject ID").reset_index(drop=True),
                                  metadata[observed.columns].sort_values("Subject ID").reset_index(drop=True))
    demo = observed.rename(columns={"Subject ID": "PTID", "Research Group": "demographic_diagnosis"})
    assert len(p) == 11529 and set(p.task) == set(TASKS)
    assert set(p.condition) == set(CONDITIONS)
    assert not p.duplicated(["task", "condition", "PTID"]).any()
    assert p.notna().all().all() and np.isfinite(p.p_positive).all()
    assert p.p_positive.between(0, 1).all()
    np.testing.assert_array_equal(p.y_pred, (p.p_positive >= .5).astype(int))
    test = splits.loc[splits.split == "test"].copy()
    assert not test.duplicated(["task", "PTID"]).any()
    joined = test.merge(demo, on="PTID", how="left", validate="many_to_one", indicator=True)
    assert joined._merge.eq("both").all()
    assert joined[["Age", "Sex"]].notna().all().all()
    assert np.isfinite(joined.Age).all() and joined.Age.between(0, 120).all()
    assert joined.Sex.isin(["F", "M"]).all()
    assert joined.diagnosis_original.eq(joined.demographic_diagnosis).all()
    source_diagnosis = subjects.set_index("PTID").diagnosis_original
    assert subjects.PTID.is_unique
    assert joined.diagnosis_original.eq(joined.PTID.map(source_diagnosis)).all()
    for task, wanted_n in EXPECTED.items():
        t = joined.loc[joined.task == task]
        assert len(t) == wanted_n
        positive = {"ad_cn": ["AD"], "mci_cn": ["EMCI", "LMCI"], "emci_lmci": ["LMCI"]}[task]
        np.testing.assert_array_equal(t.y_true, t.diagnosis_original.isin(positive).astype(int))
        for condition in CONDITIONS:
            a = p.loc[(p.task == task) & (p.condition == condition)].sort_values("PTID")
            b = t.sort_values("PTID")
            assert len(a) == wanted_n
            np.testing.assert_array_equal(a[["PTID", "fold", "y_true"]], b[["PTID", "fold", "y_true"]])
    joined = joined.drop(columns="_merge")
    joined["age_group"] = np.where(joined.Age < 75, "Age <75", "Age >=75")
    joined.to_csv(HERE / "test_demographics.csv", index=False)

    rng = np.random.default_rng(SEED)
    counts, fold_rows, summary_rows, contrast_rows = [], [], [], []
    checked_points = checked_resamples = 0
    originals = pd.read_csv(INPUTS["original_summary"]).set_index(["task", "condition"])
    original_folds = pd.read_csv(INPUTS["original_fold_metrics"]).set_index(["task", "condition", "fold"])
    for task in TASKS:
        for dimension, subgroup in GROUPS:
            t = joined.loc[(joined.task == task) & selected(joined, subgroup)]
            for fold in (0, 1, 2, 3):
                sub = t if fold == 0 else t.loc[t.fold == fold]
                n0, n1 = int((sub.y_true == 0).sum()), int((sub.y_true == 1).sum())
                assert min(n0, n1) > 0
                counts.append(dict(task=task, dimension=dimension, subgroup=subgroup,
                                   fold=fold, n=len(sub), n_negative=n0, n_positive=n1,
                                   age_mean=sub.Age.mean(), age_sd=sub.Age.std(ddof=1),
                                   n_female=int(sub.Sex.eq("F").sum()), n_male=int(sub.Sex.eq("M").sum())))
            actual = np.empty((3, len(CONDITIONS), len(METRICS)))
            draws = np.empty((REPEATS, 3, len(CONDITIONS), len(METRICS)))
            for fold in (1, 2, 3):
                people = t.loc[t.fold == fold].sort_values("PTID")
                ids, y = people.PTID.tolist(), people.y_true.to_numpy(dtype=int)
                weights = np.zeros((REPEATS, len(ids)), dtype=np.int64)
                for label in (0, 1):
                    indices = np.flatnonzero(y == label)
                    sample = indices[rng.integers(len(indices), size=(REPEATS, len(indices)))]
                    flat = (np.arange(REPEATS)[:, None] * len(ids) + sample).ravel()
                    weights += np.bincount(flat, minlength=weights.size).reshape(weights.shape)
                    assert np.all(weights[:, indices].sum(axis=1) == len(indices))
                for ci, condition in enumerate(CONDITIONS):
                    q = p.loc[(p.task == task) & (p.condition == condition) & p.PTID.isin(ids)].sort_values("PTID")
                    assert q.PTID.tolist() == ids and q.fold.eq(fold).all()
                    np.testing.assert_array_equal(q.y_true, y)
                    probability, predicted = q.p_positive.to_numpy(), q.y_pred.to_numpy()
                    point = weighted_metrics(y, probability, predicted, np.ones((1, len(ids)), dtype=int))[0]
                    np.testing.assert_allclose(point, independent_metrics(y, probability, predicted), atol=1e-14, rtol=0)
                    checked_points += 1
                    actual[fold - 1, ci] = point
                    draws[:, fold - 1, ci] = weighted_metrics(y, probability, predicted, weights)
                    for replicate in (0, REPEATS - 1):
                        repeated = np.repeat(np.arange(len(ids)), weights[replicate])
                        np.testing.assert_allclose(draws[replicate, fold - 1, ci],
                            independent_metrics(y[repeated], probability[repeated], predicted[repeated]), atol=1e-14, rtol=0)
                        checked_resamples += 1
                    fr = dict(task=task, condition=condition, dimension=dimension, subgroup=subgroup,
                              fold=fold, n=len(ids), n_negative=int((y == 0).sum()), n_positive=int((y == 1).sum()))
                    fr.update({metric + "_pct": point[mi] * 100 for mi, metric in enumerate(METRICS)})
                    fold_rows.append(fr)
                    if subgroup == "All":
                        old = original_folds.loc[(task, condition, fold)]
                        for mi, metric in enumerate(METRICS):
                            np.testing.assert_allclose(point[mi] * 100, old[metric + "_pct"], atol=1e-10, rtol=0)
            points, sd = actual.mean(axis=0) * 100, actual.std(axis=0, ddof=1) * 100
            bootstrap_means = draws.mean(axis=1) * 100
            bounds = np.percentile(bootstrap_means, [2.5, 97.5], axis=0, method="linear")
            for ci, condition in enumerate(CONDITIONS):
                row = dict(task=task, condition=condition, dimension=dimension, subgroup=subgroup,
                           n=len(t), n_negative=int(t.y_true.eq(0).sum()), n_positive=int(t.y_true.eq(1).sum()))
                for mi, metric in enumerate(METRICS):
                    row.update({metric+"_mean_pct": points[ci, mi], metric+"_sd_pp": sd[ci, mi],
                                metric+"_ci_low": bounds[0, ci, mi], metric+"_ci_high": bounds[1, ci, mi]})
                    if subgroup == "All":
                        old = originals.loc[(task, condition)]
                        assert abs(points[ci, mi] - old[metric+"_mean_pct"]) <= .00500001
                        assert abs(sd[ci, mi] - old[metric+"_sd_pp"]) <= .00500001
                summary_rows.append(row)
            target = CONDITIONS.index("mri_syn_both")
            for comparison, reference in COMPARISONS.items():
                ref = CONDITIONS.index(reference)
                delta = points[target] - points[ref]
                delta_boot = bootstrap_means[:, target] - bootstrap_means[:, ref]
                delta_bounds = np.percentile(delta_boot, [2.5, 97.5], axis=0, method="linear")
                row = dict(task=task, comparison=comparison, target="mri_syn_both", reference=reference,
                           dimension=dimension, subgroup=subgroup, n=len(t))
                for mi, metric in enumerate(METRICS):
                    row.update({metric+"_delta_pp": delta[mi], metric+"_ci_low": delta_bounds[0, mi],
                                metric+"_ci_high": delta_bounds[1, mi]})
                contrast_rows.append(row)
            print(f"Computed {task} / {subgroup}: n={len(t)}", flush=True)

    count_table, folds = pd.DataFrame(counts), pd.DataFrame(fold_rows)
    summary, contrasts = pd.DataFrame(summary_rows), pd.DataFrame(contrast_rows)
    assert len(count_table) == 60 and len(folds) == 315 and len(summary) == 105 and len(contrasts) == 30
    # Age and sex are separate, exhaustive partitions of the same overall test cohort.
    for task in TASKS:
        for fold in (0, 1, 2, 3):
            c = count_table.loc[(count_table.task == task) & (count_table.fold == fold)]
            for dim in ("age", "sex"):
                np.testing.assert_array_equal(c.loc[c.dimension == dim, ["n", "n_negative", "n_positive"]].sum(),
                                               c.loc[c.dimension == "overall", ["n", "n_negative", "n_positive"]].iloc[0])
    count_table.to_csv(HERE / "subgroup_counts.csv", index=False)
    folds.to_csv(HERE / "fold_metrics.csv", index=False)
    summary.to_csv(HERE / "summary_metrics.csv", index=False)
    contrasts.to_csv(HERE / "paired_comparisons.csv", index=False)
    summary.loc[summary.condition.isin(PRIMARY) & summary.dimension.ne("overall")].to_csv(HERE / "primary_subgroup_metrics.csv", index=False)
    plot(summary, count_table)
    write_report(summary, contrasts, count_table)
    assert all(sha(INPUTS[k]) == value for k, value in hashes.items()), "Source changed during analysis"
    import matplotlib, scipy, sklearn
    validation = dict(status="passed", original_prediction_rows=len(p), unique_test_subjects=joined.PTID.nunique(),
                      task_subject_rows=len(joined), unmatched_demographics=0, missing_age=0, missing_sex=0,
                      original_predictions_unchanged=True, all_input_hashes_unchanged=True,
                      original_63_fold_metrics_reproduced=True, original_21_mean_sd_reproduced=True,
                      point_checks_against_sklearn=checked_points, bootstrap_resample_checks_against_sklearn=checked_resamples,
                      min_fold_subgroup_class_n=int(count_table.loc[(count_table.fold > 0) & count_table.dimension.ne("overall"), ["n_negative", "n_positive"]].min().min()),
                      rows=dict(counts=len(count_table), folds=len(folds), summaries=len(summary), comparisons=len(contrasts)),
                      versions={"python": sys.version, "numpy": np.__version__, "pandas": pd.__version__,
                                "scipy": scipy.__version__, "sklearn": sklearn.__version__, "matplotlib": matplotlib.__version__},
                      elapsed_seconds=time.perf_counter() - start)
    write_json(HERE / "validation.json", validation)
    outputs = {str(path.relative_to(HERE)): sha(path) for path in HERE.iterdir()
               if path.is_file() and path.suffix in {".csv", ".png", ".pdf", ".svg", ".md", ".json"}
               and path.name not in {"complete.json"} and not path.name.startswith("failure_")}
    write_json(HERE / "complete.json", dict(status="complete", completed_utc=datetime.now(timezone.utc).isoformat(),
                                           elapsed_seconds=validation["elapsed_seconds"], output_sha256=outputs))
    print(json.dumps(validation, ensure_ascii=False, indent=2))


def plot(summary, counts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "pdf.fonttype": 42, "svg.fonttype": "none", "axes.spines.top": False,
                         "axes.spines.right": False, "savefig.facecolor": "white"})
    groups = [g for _, g in GROUPS[1:]]
    colors = ["#56616B", "#1565A9", "#B06517"]
    markers = ["o", "s", "^"]
    fig, axes = plt.subplots(3, 2, figsize=(14, 11), sharex=True)
    for ti, task in enumerate(TASKS):
        for mi, metric in enumerate(["AUC", "balanced_ACC"]):
            ax = axes[ti, mi]
            for ci, condition in enumerate(PRIMARY):
                sub = summary.loc[(summary.task == task) & (summary.condition == condition)].set_index("subgroup").loc[groups]
                val = sub[metric + "_mean_pct"].to_numpy()
                lo, hi = sub[metric + "_ci_low"].to_numpy(), sub[metric + "_ci_high"].to_numpy()
                yy = np.arange(4) + (ci - 1) * .22
                # Separate segments and points also support percentile intervals excluding the estimate.
                ax.hlines(yy, lo, hi, color=colors[ci], linewidth=1.35)
                ax.plot(val, yy, markers[ci], color=colors[ci], markersize=5, linestyle="none")
            c = counts.loc[(counts.task == task) & (counts.fold == 0)].set_index("subgroup")
            labels = [g.replace(">=", "≥") + f"  ({int(c.loc[g, 'n_negative'])}/{int(c.loc[g, 'n_positive'])})" for g in groups]
            ax.set_yticks(np.arange(4), labels if mi == 0 else groups)
            ax.set_ylim(3.55, -.55)
            ax.set_xlim(0, 100)
            ax.set_xticks(np.arange(0, 101, 20))
            ax.axvline(50, color="#999999", linewidth=.7, linestyle="--", zorder=0)
            ax.grid(axis="x", color="#DDDDDD", linewidth=.6)
            ax.set_axisbelow(True)
            ax.set_title(TASKS[task] + " | " + metric.replace("balanced_ACC", "Balanced accuracy"), loc="left", fontsize=11)
            if ti == 2:
                ax.set_xlabel("Three-fold mean (%) and marginal 95% bootstrap CI")
    handles = [Line2D([0], [0], color=colors[i], marker=markers[i], linewidth=1.3, label=LABELS[c]) for i, c in enumerate(PRIMARY)]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, bbox_to_anchor=(.53, .965))
    fig.suptitle("Classification performance by age and sex", fontsize=16, y=.995)
    fig.text(.02, .015, "Left labels: subgroup (negative/positive n). Age and sex evaluated separately.\n"
             "Fixed models and folds; 5,000 paired stratified resamples. Intervals are not multiplicity-adjusted.", fontsize=9)
    fig.subplots_adjust(left=.24, right=.985, top=.895, bottom=.10, hspace=.42, wspace=.30)
    for ext in ("png", "pdf", "svg"):
        fig.savefig(HERE / ("subgroup_performance." + ext), dpi=220)
    plt.close(fig)


def write_report(summary, contrasts, counts):
    lines = ["# R2-16：年龄、性别分层分类性能评价", "",
             "本分析使用现有三折 outer-test 预测；年龄与性别分别分层，不交叉细分。未训练、推理、重新选择 checkpoint、校准概率或调整阈值。", "",
             "## 数据覆盖与分层", "",
             "1,647 条任务–受试者记录对应 906 名唯一受试者；受试者可参与不同任务，各任务独立评价，不合并推断。11,529 条七输入预测均与固定测试名单逐项对应。年龄、性别无缺失，不作插补。", "",
             "| 任务 | 亚组 | 总人数 | 阴性 | 阳性 |", "|---|---|---:|---:|---:|"]
    for row in counts.loc[counts.fold == 0].itertuples():
        lines.append(f"| {TASKS[row.task]} | {row.subgroup} | {row.n} | {row.n_negative} | {row.n_positive} |")
    lines += ["", "正类分别为 AD、EMCI+LMCI、LMCI。年龄界值固定为 75 岁，不根据分层性能修改；女性/男性按源表 F/M。各折亚组两类均存在，最小类别人数为18。", "",
              "## 重点三组的分层性能", "",
              "数值为三折等权均值百分数 [边际95% bootstrap CI]；三折 sample SD 另存 CSV，不当作 CI。完整七输入、五指标见 [summary_metrics.csv](summary_metrics.csv)。", ""]
    for task in TASKS:
        lines += [f"### {TASKS[task]}", "", "| 亚组 | 输入 | AUC | balanced ACC | ACC | SEN | SPE |", "|---|---|---:|---:|---:|---:|---:|"]
        for _, subgroup in GROUPS[1:]:
            for condition in PRIMARY:
                r = summary.loc[(summary.task == task) & (summary.subgroup == subgroup) & (summary.condition == condition)].iloc[0]
                vals = " | ".join(format_ci(r, metric) for metric in ["AUC", "balanced_ACC", "ACC", "SEN", "SPE"])
                lines.append(f"| {subgroup} | {LABELS[condition]} | {vals} |")
        lines.append("")
    lines += ["## 亚组内配对差值", "", "A = MRI+Syn双PET − MRI；B = MRI+Syn双PET − MRI+Real双PET。单位为百分点；同轮配对差值直接构建区间，不由两个独立区间相减。", "",
              "| 任务 | 亚组 | 比较 | ΔAUC [95% CI] | Δbalanced ACC [95% CI] |", "|---|---|---|---:|---:|"]
    for r in contrasts.loc[contrasts.dimension != "overall"].to_dict("records"):
        lines.append(f"| {TASKS[r['task']]} | {r['subgroup']} | {r['comparison']} | {format_ci(r, 'AUC', True)} | {format_ci(r, 'balanced_ACC', True)} |")
    lines += ["", "![Age and sex subgroup performance](subgroup_performance.png)", "",
              "图：重点三组的 AUC 与 balanced accuracy；误差线为边际95%条件性 bootstrap CI。年龄与性别是同一队列的两种分层，不能相加。原始可编辑图见 [SVG](subgroup_performance.svg) 和 [PDF](subgroup_performance.pdf)。", "",
              "## 统计方法与限制", "",
              "每个任务、亚组内，先计算每个 outer fold 的五项指标，再对三折等权平均。AUC只在同折连续阳性概率中计算；不把来自不同折模型的概率混合排序。ACC/SEN/SPE使用既存0.5阈值预测，balanced ACC=(SEN+SPE)/2。", "",
              "Bootstrap固定seed=20261103，NumPy default_rng PCG64，5,000次。在每个task×fold×subgroup×y_true层内有放回抽取与原层等量的PTID，同次抽样权重由七输入共享；每次先算各折指标再等权平均。95% CI取2.5/97.5百分位（linear）。保存All作为复核参考，其CI与分层结果用同一新seed计算，不替换原R2-11统计。", "",
              "本CI条件于已经训练的模型、固定折划分及观察到的亚组类别人数，不包含重新训练、随机种子或重新划分的变异；三折训练集有重叠。所有CI均为未作多重比较校正的边际区间，不作确认性显著性声明。未计算或合并DeLong p值，也不以区间重叠判断亚组间差异。", "",
              "本分析量化人口学分层下的分类表现及合成PET增益，不能证明人口学混杂已消除。年龄与性别分别分层，未相互调整，也未控制临床评分、诊断组内残余年龄差异或其他变量。亚组内收益区间包含0，不等于无收益、等效或非劣效；不同亚组一个区间跨0、另一个不跨0，不等于存在交互作用。", "",
              "人口学字段取自 reports/e1_stage01_20261017/observed.csv，与 metadata.csv 的 Subject ID/Age/Sex/Research Group 逐值一致。该导出缺少 EXAMDATE/VISCODE，无法确认年龄与MRI采集同次访视；本文据此称记录年龄，不声称影像当日年龄。既有临床评分上游填补来源的缺口不因本分析而解除。", "",
              "## 文件与复核", "",
              "- [analysis_plan.json](analysis_plan.json)：计算分层性能前固定的分层、指标、比较、随机种子与输入SHA-256。",
              "- [input_manifest.csv](input_manifest.csv)：源文件路径、大小及哈希；原件只读。",
              "- [test_demographics.csv](test_demographics.csv)：测试名单关联的人口学记录，仅限项目内核查。",
              "- [subgroup_counts.csv](subgroup_counts.csv)：60行，含三折及总人数；fold=0表示三折总人数，不是额外模型。",
              "- [fold_metrics.csv](fold_metrics.csv)：315行；[summary_metrics.csv](summary_metrics.csv)：105行（含21行All）；[primary_subgroup_metrics.csv](primary_subgroup_metrics.csv)：36行。",
              "- [paired_comparisons.csv](paired_comparisons.csv)：30行（含6行All），保留五项差值及CI。",
              "- [validation.json](validation.json)：原63折指标及21组三折mean/SD复算、独立sklearn核验和输入未改写检查。",
              "- [analyze.py](analyze.py)：复用原配对bootstrap的计数加权指标函数；每个点估计及首末抽样用显式重复PTID的sklearn指标交叉验证。",
              "", "复算应将脚本复制到独立的同层报告目录，使用项目默认解释器执行；脚本拒绝覆盖已有complete.json，输入路径按仓库根定位。", ""]
    (HERE / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        write_json(HERE / f"failure_{stamp}.json", dict(status="failed", traceback=traceback.format_exc()))
        raise
