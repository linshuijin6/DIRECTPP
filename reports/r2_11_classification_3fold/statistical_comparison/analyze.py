#!/usr/bin/env python3
"""Fixed-model paired stratified bootstrap and within-fold paired DeLong.

Run with the project's existing Python; no training, inference or input writes.
DeLong covariance formulas adapted from yandexdataschool/roc_comparison,
compare_auc_delong_xu.py (fastDeLong), using scipy.stats.rankdata for midranks:
https://github.com/yandexdataschool/roc_comparison/blob/master/compare_auc_delong_xu.py
Reference: DeLong et al. (1988), doi:10.2307/2531595;
Sun and Xu (2014), doi:10.1109/LSP.2014.2337313.

License for the adapted DeLong implementation:
MIT License
Copyright (c) 2021 Nikita Kazeev
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from pathlib import Path
import time

import numpy as np
import pandas as pd
from scipy.stats import norm, rankdata
from sklearn.metrics import roc_auc_score


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "final_summary"
SEED = 20261102
REPEATS = 5000
TASKS = {"ad_cn": (470, "AD vs CN"), "mci_cn": (741, "EMCI+LMCI vs CN"),
         "emci_lmci": (436, "EMCI vs LMCI")}
CONDITIONS = ["mri", "mri_real_fdg", "mri_syn_fdg", "mri_real_av45",
              "mri_syn_av45", "mri_real_both", "mri_syn_both"]
LABELS = ["MRI", "MRI+Real FDG", "MRI+Syn FDG", "MRI+Real AV45",
          "MRI+Syn AV45", "MRI+Real双PET", "MRI+Syn双PET"]
METRICS = ["ACC", "AUC", "SEN", "SPE", "balanced_ACC"]
COMPARISONS = [("A", "mri"), ("B", "mri_real_both")]


def weighted_metrics(y, probabilities, predicted, weights):
    """Exact empirical metrics for PTID multiplicities, including score ties.

    One row of integer weights is one resample. Weighted AUC counts positive-
    negative wins plus half of ties; weights are sampling counts, not model
    weights. Keeping all original subjects with integer counts is identical
    to evaluating the explicitly repeated PTIDs.
    """
    positive = y == 1
    n_positive = weights[:, positive].sum(axis=1)
    n_negative = weights[:, ~positive].sum(axis=1)
    tp = weights[:, positive & (predicted == 1)].sum(axis=1)
    tn = weights[:, ~positive & (predicted == 0)].sum(axis=1)
    sensitivity, specificity = tp / n_positive, tn / n_negative
    order = np.argsort(probabilities, kind="stable")
    sorted_scores = probabilities[order]
    starts = np.r_[0, np.flatnonzero(np.diff(sorted_scores) != 0) + 1]
    ordered = weights[:, order]
    positive_groups = np.add.reduceat(ordered * positive[order], starts, axis=1)
    negative_groups = np.add.reduceat(ordered * (~positive[order]), starts, axis=1)
    auc = (positive_groups * (negative_groups.cumsum(axis=1)
                             - .5 * negative_groups)).sum(axis=1) / (n_positive * n_negative)
    return np.column_stack(((tp + tn) / (n_positive + n_negative), auc,
                            sensitivity, specificity, (sensitivity + specificity) / 2))


def paired_delong(y, target, reference):
    """Fast DeLong covariance with average midranks; two-sided normal test.

    Subjects must already be in identical PTID order in both score arrays.
    Cross-check the adapted midrank covariance against direct structural
    components (pairwise positive/negative kernels) for every actual pair.
    """
    scores = np.vstack((target, reference))
    positive, negative = scores[:, y == 1], scores[:, y == 0]
    m, n = positive.shape[1], negative.shape[1]
    tx = np.vstack([rankdata(x, method="average") for x in positive])
    ty = np.vstack([rankdata(x, method="average") for x in negative])
    tz = np.vstack([rankdata(x, method="average")
                    for x in np.concatenate((positive, negative), axis=1)])
    aucs = tz[:, :m].sum(axis=1) / (m * n) - (m + 1) / (2 * n)
    v_positive = (tz[:, :m] - tx) / n
    v_negative = 1 - (tz[:, m:] - ty) / m
    covariance = np.cov(v_positive, ddof=1) / m + np.cov(v_negative, ddof=1) / n

    wins = (positive[:, :, None] > negative[:, None, :]).astype(float)
    wins += .5 * (positive[:, :, None] == negative[:, None, :])
    direct = np.cov(wins.mean(axis=2), ddof=1) / m + np.cov(wins.mean(axis=1), ddof=1) / n
    np.testing.assert_allclose(covariance, direct, rtol=1e-10, atol=1e-14)
    np.testing.assert_allclose(aucs, wins.mean(axis=(1, 2)), rtol=0, atol=1e-14)
    delta = aucs[0] - aucs[1]
    variance = float(np.array([1., -1.]) @ covariance @ np.array([1., -1.]))
    if variance <= 0:
        raise ValueError("Nonpositive DeLong contrast variance; no p-value can be reported")
    z = delta / np.sqrt(variance)
    return aucs, delta, np.sqrt(variance), z, float(2 * norm.sf(abs(z)))


def main():
    started = time.perf_counter()
    predictions = pd.read_csv(SOURCE / "oof_predictions.csv", dtype={"PTID": str},
                              float_precision="round_trip")
    original = pd.read_csv(SOURCE / "summary_metrics.csv").set_index(["task", "condition"])
    splits = pd.read_csv(HERE.parent / "splits.csv", dtype={"PTID": str})
    test = splits[splits.split == "test"]
    assert len(predictions) == 11529 and len(original) == 21
    assert set(predictions.task) == set(TASKS) and set(predictions.condition) == set(CONDITIONS)
    assert not predictions.duplicated(["task", "condition", "PTID"]).any()
    assert predictions.notna().all().all()
    assert np.isfinite(predictions.p_positive).all() and predictions.p_positive.between(0, 1).all()
    assert np.array_equal(predictions.y_pred, (predictions.p_positive >= .5).astype(int))

    rng = np.random.default_rng(SEED)
    metric_rows, comparison_rows, delong_rows = [], [], []
    checked_resamples = 0
    for task, (n_subjects, _) in TASKS.items():
        # Replicate b refers to one paired draw in every condition and fold.
        draws = np.empty((REPEATS, 3, len(CONDITIONS), len(METRICS)))
        actual = np.empty((3, len(CONDITIONS), len(METRICS)))
        for fold in (1, 2, 3):
            wanted = test[(test.task == task) & (test.fold == fold)].sort_values("PTID")
            ids = wanted.PTID.tolist()
            y = wanted.y_true.to_numpy(dtype=int)
            weights = np.zeros((REPEATS, len(ids)), dtype=np.int64)
            for label in (0, 1):
                indices = np.flatnonzero(y == label)
                sampled = indices[rng.integers(len(indices), size=(REPEATS, len(indices)))]
                flat = (np.arange(REPEATS)[:, None] * len(ids) + sampled).ravel()
                weights += np.bincount(flat, minlength=REPEATS * len(ids)).reshape(weights.shape)
            assert np.all(weights[:, y == 0].sum(axis=1) == np.sum(y == 0))
            assert np.all(weights[:, y == 1].sum(axis=1) == np.sum(y == 1))

            scores = {}
            for ci, condition in enumerate(CONDITIONS):
                p = predictions[(predictions.task == task) & (predictions.condition == condition)
                                & (predictions.fold == fold)].sort_values("PTID")
                assert p.PTID.tolist() == ids and np.array_equal(p.y_true, y)
                probability, predicted = p.p_positive.to_numpy(), p.y_pred.to_numpy()
                scores[condition] = probability
                actual[fold - 1, ci] = weighted_metrics(y, probability, predicted,
                                                       np.ones((1, len(ids)), dtype=int))[0]
                draws[:, fold - 1, ci] = weighted_metrics(y, probability, predicted, weights)
                # Meaningful equivalence check for the vectorized count implementation:
                # explicitly repeat PTIDs and independently calculate selected resamples.
                for b in (0, 1, REPEATS - 1):
                    expanded = np.repeat(np.arange(len(ids)), weights[b])
                    yy, pp, pr = y[expanded], probability[expanded], predicted[expanded]
                    sen, spe = pr[yy == 1].mean(), (pr[yy == 0] == 0).mean()
                    independent = [(yy == pr).mean(), roc_auc_score(yy, pp), sen, spe, (sen + spe) / 2]
                    np.testing.assert_allclose(draws[b, fold - 1, ci], independent, atol=1e-14, rtol=0)
                    checked_resamples += 1

            for comparison_id, reference in COMPARISONS:
                aucs, delta, se, z, p_value = paired_delong(y, scores["mri_syn_both"], scores[reference])
                np.testing.assert_allclose(aucs, actual[fold - 1,
                    [CONDITIONS.index("mri_syn_both"), CONDITIONS.index(reference)], 1], atol=1e-14)
                delong_rows.append(dict(task=task, comparison=comparison_id, target="mri_syn_both",
                    reference=reference, fold=fold, n_test=len(y), n_positive=int(y.sum()),
                    n_negative=int((y == 0).sum()), target_AUC_pct=aucs[0] * 100,
                    reference_AUC_pct=aucs[1] * 100, delta_AUC_pp=delta * 100,
                    delta_AUC_SE_pp=se * 100, z=z, p_value_unadjusted_twosided=p_value,
                    scope="paired within outer test fold; no combined p-value"))

        point = actual.mean(axis=0) * 100
        boot_mean = draws.mean(axis=1) * 100
        for ci, condition in enumerate(CONDITIONS):
            old = original.loc[(task, condition)]
            assert int(old.n_subjects) == n_subjects
            low, high = np.percentile(boot_mean[:, ci], [2.5, 97.5], axis=0, method="linear")
            row = dict(task=task, condition=condition, n_subjects=n_subjects, n_folds=3,
                       bootstrap_repeats=REPEATS, seed=SEED)
            for mi, metric in enumerate(METRICS):
                sample_sd = actual[:, ci, mi].std(ddof=1) * 100
                assert old[metric + "_mean_sd"] == f"{point[ci, mi]:.2f} ± {sample_sd:.2f}"
                row.update({metric + "_point_pct": point[ci, mi],
                    metric + "_original_mean_pct": old[metric + "_mean_pct"],
                    metric + "_original_fold_sd_pp": old[metric + "_sd_pp"],
                    metric + "_original_mean_sd": old[metric + "_mean_sd"],
                    metric + "_ci_lower_pct": low[mi], metric + "_ci_upper_pct": high[mi]})
            metric_rows.append(row)
        for comparison_id, reference in COMPARISONS:
            target_i, reference_i = CONDITIONS.index("mri_syn_both"), CONDITIONS.index(reference)
            delta = point[target_i] - point[reference_i]
            paired_delta = boot_mean[:, target_i] - boot_mean[:, reference_i]
            low, high = np.percentile(paired_delta, [2.5, 97.5], axis=0, method="linear")
            row = dict(task=task, comparison=comparison_id, target="mri_syn_both", reference=reference,
                       n_subjects=n_subjects, n_folds=3, bootstrap_repeats=REPEATS, seed=SEED)
            for mi, metric in enumerate(METRICS):
                row.update({"delta_" + metric + "_pp": delta[mi],
                    "delta_" + metric + "_ci_lower_pp": low[mi],
                    "delta_" + metric + "_ci_upper_pp": high[mi]})
            comparison_rows.append(row)
        print(f"Completed {task}: paired 5000 replicates, 7 conditions, 3 folds", flush=True)

    metric_table, comparisons, delong = map(pd.DataFrame, (metric_rows, comparison_rows, delong_rows))
    assert (len(metric_table), len(comparisons), len(delong)) == (21, 6, 18)
    metric_table.to_csv(HERE / "bootstrap_metrics.csv", index=False, float_format="%.10g")
    comparisons.to_csv(HERE / "paired_comparisons.csv", index=False, float_format="%.10g")
    delong.to_csv(HERE / "delong_by_fold.csv", index=False, float_format="%.10g")
    write_report(metric_table, comparisons, delong, checked_resamples, time.perf_counter() - started)


def interval(row, metric):
    # Preserve a near-zero endpoint's direction rather than printing '-0.00'.
    low = row['delta_' + metric + '_ci_lower_pp']
    high = row['delta_' + metric + '_ci_upper_pp']
    low_text = f"{low:+.4f}" if 0 < abs(low) < .005 else f"{low:+.2f}"
    high_text = f"{high:+.4f}" if 0 < abs(high) < .005 else f"{high:+.2f}"
    return (f"{row['delta_' + metric + '_pp']:+.2f} "
            f"[{low_text}, {high_text}]")


def direction(row, metric):
    if row['delta_' + metric + '_ci_lower_pp'] > 0:
        return "区间完全高于0"
    if row['delta_' + metric + '_ci_upper_pp'] < 0:
        return "区间完全低于0"
    return "区间包含0"


def write_report(metrics, comparisons, delong, checked_resamples, seconds):
    rows = ["# DIReCT++ 分类统计：固定模型的配对bootstrap及逐折DeLong", "",
        "本分析仅使用已完成的63个影像模型最终outer test预测；Clinical-only与MRI+Clinical不纳入。未训练、推理、选择checkpoint或修改原预测。", "",
        "## 六项预先指定比较", "",
        "A= MRI+Syn双PET − MRI；B= MRI+Syn双PET − MRI+Real双PET。点估计是实际三个fold指标均值之差；95% CI为5000次配对分层bootstrap百分位区间。以下差值与区间均为百分点。未校正多重比较，区间均为单项（非同时）95% CI。", "",
        "| 任务 | 比较 | ΔAUC [95% CI] | ΔACC [95% CI] | Δbalanced ACC [95% CI] |",
        "|---|---|---|---|---|"]
    for r in comparisons.to_dict("records"):
        rows.append(f"| {TASKS[r['task']][1]} | {r['comparison']} | "
                    + " | ".join(interval(r, k) for k in ["AUC", "ACC", "balanced_ACC"]) + " |")
    rows += ["", "五项差值（含SEN、SPE）的完整区间均保存在paired_comparisons.csv；没有增加其他组间比较。", "",
             "## 任务分别的解释", ""]
    rows += [
        "AD/CN：在固定模型和划分、未校正多重比较的条件性分析下，Syn双PET相对MRI的ACC、AUC和balanced ACC三项区间均高于0，支持这三个指标的分类增益；不能外推为重新训练或新划分后的普遍增益。", "",
        "MCI/CN：Syn双PET相对MRI的这三项点估计均为负，但区间均包含0，既没有明确增益证据，也不足以断言明确下降；不能继续用本轮结果支持MCI任务统一获益。", "",
        "EMCI/LMCI：Syn双PET相对MRI的balanced ACC提高6.91个百分点，95% CI为[2.02, 11.98]，支持这一条件性改善；ACC与AUC差值区间包含0，不能扩大为所有指标均改善。", "",
        "Syn与Real双PET：三个任务的AUC、balanced ACC差值区间均包含0。AD/CN的SPE差为−4.91个百分点，95% CI为[−8.19, −1.95]，支持条件性的SPE降低；ACC差的区间上界仅−0.00272个百分点，几乎触及0。这一ACC边界结果受有限5000次bootstrap的Monte Carlo近似影响，应谨慎呈现，不写成稳健或经多重比较校正的下降。未改变重采样次数、比较或预测以调整结果。", ""]
    for task, (_, label) in TASKS.items():
        subset = comparisons[comparisons.task == task].set_index("comparison")
        for code, name in [("A", "Syn双PET相对MRI"), ("B", "Syn双PET相对Real双PET")]:
            r = subset.loc[code]
            results = "；".join(f"{k} {interval(r, k)}，{direction(r, k)}" for k in ["ACC", "AUC", "balanced_ACC"])
            rows.append(f"- {label}，{name}：{results}。")
    rows += ["", "只有区间完全位于0某侧的指标，才在本次固定模型、固定划分的条件性重采样分析下支持相应方向。区间包含0时不能断言没有差异，更不能证明Real/Syn等效；同一任务不同指标需分别解释。", "",
             "## 每组指标的95% CI与原有mean±sample SD", "",
             "所有指标为百分数，SD为百分点。每格为“原有mean±sample SD；[bootstrap 95% CI]”。原有mean±SD原样复制，bootstrap不替代fold-wise SD。这里的CI对应三折等权均值，不是pooled OOF指标。", ""]
    for task, (_, label) in TASKS.items():
        rows += [f"### {label}", "", "| 输入 | ACC | AUC | SEN | SPE | balanced ACC |",
                 "|---|---|---|---|---|---|"]
        table = metrics[metrics.task == task].set_index("condition")
        for condition, label in zip(CONDITIONS, LABELS):
            r = table.loc[condition]
            cells = [f"{r[k + '_original_mean_sd']}；[{r[k + '_ci_lower_pct']:.2f}, {r[k + '_ci_upper_pct']:.2f}]"
                     for k in METRICS]
            rows.append("| " + label + " | " + " | ".join(cells) + " |")
        rows.append("")
    rows += ["## 逐outer fold的paired DeLong", "",
        "按PTID严格对齐同一fold的分数，执行双侧paired DeLong。共18项，p值为未校正原始p值；没有合并、平均p值或将单折检验称为三折总体检验。DeLong使用连续阳性分数（非0.5阈值预测）。", "",
        "| 任务 | 比较 | fold | ΔAUC（百分点） | 双侧p（未校正） |",
        "|---|---|---:|---:|---:|"]
    for r in delong.itertuples():
        rows.append(f"| {TASKS[r.task][1]} | {r.comparison} | {r.fold} | {r.delta_AUC_pp:+.2f} | {r.p_value_unadjusted_twosided:.6g} |")
    rows += ["", "18项逐折检验中，仅AD/CN比较A的fold1与fold3出现未校正p<0.05（分别约0.00609、0.02029），fold2为0.11362。其他比较的逐折p均未低于0.05。这些只描述单折检验，不能据此宣布AD/CN的三折总体DeLong显著；也不将未经校准的合并p值用于总体结论。", "",
        "## 审稿回复可用范围与限制", "",
        "- R2-11：提供全部21组五项指标的95%条件性bootstrap CI，保留原有三折mean±sample SD；两类不确定性口径并列，不把SD写成CI。",
        "- R2-12：提供六项预先指定配对差值及CI，说明各指标的方向和不确定性；没有穷举比较或按结果选择比较。不能声称经过多重比较校正的显著性。",
        "- R3-7：补充balanced ACC区间及18项逐折paired DeLong；单折p值不能支持三折总体显著性声明。本轮不建立或宣称总体DeLong p值。",
        "- Bootstrap条件于已经训练完成的模型、固定三折及其测试预测，只反映这一条件下分层受试者抽样的不确定性，不能完整代表重新训练、更换随机种子或更换划分的变异。",
        "- 三折训练集合存在重叠，不应视为三个独立外部实验；本CI也没有消除这种训练依赖。本分析对当前测试集内观察到的类比例和fold人数作条件化。",
        "- 21组×5项区间与6项×5项差值区间均为边际95%区间，未作多重比较校正；不由不显著推断等效、非劣效或无临床差异。",
        "", "## 方法、来源与复算", "",
        f"固定seed={SEED}，使用NumPy default_rng（PCG64），任务顺序ad_cn、mci_cn、emci_lmci；每任务fold1→3、每fold标签0→1，PTID先稳定排序。各fold×y_true层内有放回抽取与原层等量的受试者，5000次；每轮每个PTID的整数重复次数由七种输入共享。各fold独立抽样后，对三个fold的指标等权平均。",
        "整数抽样权重与显式重复PTID完全等价；ACC/SEN/SPE/balanced ACC用重复次数计算，AUC按正负样本对的得分胜出与平局半权计算。概率相同的受试者一起处理，不扰动分数或打破平局。使用np.percentile的2.5/97.5百分位（method='linear'），差值CI直接来自同轮配对差值分布。",
        "点估计从保存预测按原fold重新计算五项指标（仅统计计算，非推理）；差值先用未舍入的实际三折均值相减，再显示两位小数，因此不受summary_metrics.csv两位小数舍入影响。",
        "输入：[oof_predictions.csv](../final_summary/oof_predictions.csv)、[summary_metrics.csv](../final_summary/summary_metrics.csv)、[splits.csv](../splits.csv)。同一task-condition每名被试仅一个outer test预测，63项fold身份/标签/人数与固定名单一致。",
        f"数值核对：原有21组mean±SD全部一致；向量化bootstrap在每fold、每条件的第1/2/5000次抽样与显式重复PTID后用sklearn计算对照，共{checked_resamples}组核对；18项DeLong的midrank协方差均与直接正负样本对structural-components公式一致。完整统计计算耗时{seconds:.1f}秒。",
        "DeLong复用来源：[Yandex School of Data Analysis实现](https://github.com/yandexdataschool/roc_comparison/blob/master/compare_auc_delong_xu.py)，MIT许可已随analyze.py保留；用现有scipy.stats.rankdata替代midrank循环，协方差与双侧正态检验公式不变。原方法：[DeLong等，1988](https://doi.org/10.2307/2531595)；快速算法：[Sun和Xu，2014](https://doi.org/10.1109/LSP.2014.2337313)。没有新增统计框架或依赖。",
        "", "复算（只写本目录四个结果文件，原始输入和模型不写入）：", "",
        "```sh", "/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python -B reports/r2_11_classification_3fold/statistical_comparison/analyze.py", "```", "",
        "输出：[bootstrap_metrics.csv](bootstrap_metrics.csv)（21行）、[paired_comparisons.csv](paired_comparisons.csv)（6行）、[delong_by_fold.csv](delong_by_fold.csv)（18行）及本报告。CSV保留足够数值精度，报告显示两位小数；DeLong p值不转换为百分数。", ""]
    (HERE / "REPORT.md").write_text("\n".join(rows))
    print("\n".join(rows[5:17]), flush=True)


if __name__ == "__main__":
    main()
