"""Recompute R2-8 paired ROI statistics from the preserved author CSVs.

Run from the repository root with the existing xiaochou Python environment.
This script reads only the two explicitly named original-author directories.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = Path(__file__).resolve().parent
SOURCE = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin"
INPUTS = {
    "AV45": SOURCE / "statistics_of_regions_av45_adjust",
    "FDG": SOURCE / "statistics_of_regions_fdg_adjust",
}
ROI_PATTERN = re.compile(r"region_(\d+)\.0\.csv\Z")
ALPHA = 0.05

# Labels transcribed from the original manuscript/figures/figure_4.pdf.
# IDs are checked below against the existing FreeSurfer color LUT.
FIGURE4 = {
    "A": ["ctx-lh-precuneus", "ctx-rh-precuneus", "ctx-lh-frontalpole",
          "ctx-rh-frontalpole", "ctx-lh-temporalpole", "ctx-rh-temporalpole",
          "ctx-lh-superiorfrontal", "ctx-rh-superiorfrontal"],
    "B": ["ctx-lh-precuneus", "ctx-rh-precuneus", "ctx-lh-frontalpole",
          "ctx-rh-frontalpole", "ctx-lh-temporalpole", "ctx-rh-temporalpole",
          "ctx-lh-superiorfrontal", "ctx-rh-superiorfrontal"],
    "C": ["ctx-lh-precuneus", "ctx-lh-inferiortemporal", "ctx-lh-middletemporal",
          "ctx-lh-superiortemporal", "ctx-lh-transversetemporal"],
    "D": ["ctx-lh-isthmuscingulate", "ctx-rh-isthmuscingulate",
          "ctx-lh-supramarginal", "Left-Hippocampus", "Right-Hippocampus"],
    "E": ["Left-Lateral-Ventricle", "Right-Lateral-Ventricle",
          "Right-Hippocampus", "Left-Cerebellum-White-Matter", "Left-Hippocampus"],
    "F": ["Left-Thalamus", "Right-Thalamus", "ctx-lh-parsorbitalis",
          "ctx-lh-lateraloccipital", "ctx-rh-lingual"],
}


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def paired_metrics(real: np.ndarray, syn: np.ndarray) -> dict:
    """One row of statistics; all calculations retain the subject pairing."""
    n = len(real)
    d = syn - real
    bias = float(np.mean(d))
    result = {
        "n_pairs": n,
        "real_mean": float(np.mean(real)),
        "syn_mean": float(np.mean(syn)),
        "mean_difference_syn_minus_real": bias,
        "mae": float(np.mean(np.abs(d))),
        "rmse": float(np.sqrt(np.mean(d * d))),
        "ba_mean_bias": bias,
    }
    reasons = {}
    if n < 2:
        for key in ("real_sd", "syn_sd", "difference_sd", "mean_difference_ci95_lower",
                    "mean_difference_ci95_upper", "paired_t_statistic", "paired_t_p_value",
                    "ccc", "icc_a1", "ba_loa95_lower", "ba_loa95_upper"):
            result[key] = np.nan
            reasons[key] = "fewer_than_2_pairs"
        result["unavailable_reasons"] = json.dumps(reasons, ensure_ascii=False)
        return result

    real_sd = float(np.std(real, ddof=1))
    syn_sd = float(np.std(syn, ddof=1))
    diff_sd = float(np.std(d, ddof=1))
    result.update(real_sd=real_sd, syn_sd=syn_sd, difference_sd=diff_sd,
                  ba_loa95_lower=bias - 1.96 * diff_sd,
                  ba_loa95_upper=bias + 1.96 * diff_sd)

    if diff_sd == 0:
        for key in ("mean_difference_ci95_lower", "mean_difference_ci95_upper",
                    "paired_t_statistic", "paired_t_p_value"):
            result[key] = np.nan
            reasons[key] = "zero_paired_difference_variance"
    else:
        half_width = float(stats.t.ppf(0.975, n - 1) * diff_sd / np.sqrt(n))
        t_test = stats.ttest_rel(syn, real)
        result.update(mean_difference_ci95_lower=bias - half_width,
                      mean_difference_ci95_upper=bias + half_width,
                      paired_t_statistic=float(t_test.statistic),
                      paired_t_p_value=float(t_test.pvalue))

    # Lin CCC uses population moments of the observed paired sample.
    real_var = float(np.var(real))
    syn_var = float(np.var(syn))
    ccc_denominator = real_var + syn_var + (float(np.mean(real)) - float(np.mean(syn))) ** 2
    if ccc_denominator == 0:
        result["ccc"] = np.nan
        reasons["ccc"] = "zero_concordance_denominator"
    else:
        result["ccc"] = float(2 * np.mean((real - np.mean(real)) *
                                             (syn - np.mean(syn))) / ccc_denominator)

    # ICC(A,1): two-way absolute agreement, single measurement; k=2 raters.
    y = np.column_stack((real, syn))
    subject_means = np.mean(y, axis=1)
    rater_means = np.mean(y, axis=0)
    grand_mean = float(np.mean(y))
    ms_subject = float(2 * np.sum((subject_means - grand_mean) ** 2) / (n - 1))
    ms_rater = float(n * np.sum((rater_means - grand_mean) ** 2))
    ms_error = float(np.sum((y - subject_means[:, None] - rater_means[None, :]
                             + grand_mean) ** 2) / (n - 1))
    icc_denominator = ms_subject + ms_error + 2 * (ms_rater - ms_error) / n
    if icc_denominator == 0:
        result["icc_a1"] = np.nan
        reasons["icc_a1"] = "zero_icc_denominator"
    else:
        result["icc_a1"] = (ms_subject - ms_error) / icc_denominator
    result["unavailable_reasons"] = json.dumps(reasons, ensure_ascii=False)
    return result


def load_roi(tracer: str, path: Path) -> tuple[pd.DataFrame, dict, dict]:
    match = ROI_PATTERN.fullmatch(path.name)
    if match is None:
        raise ValueError(f"Unexpected region filename: {path}")
    roi = match.group(1)
    real_col, syn_col = f"real_{tracer.lower()}_mean", f"syn_{tracer.lower()}_mean"
    expected = ["subject", real_col, syn_col, "Research Group"]
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    if list(raw.columns) != expected:
        raise ValueError(f"Unexpected columns in {path}: {list(raw.columns)}")
    blank_subject = raw["subject"].str.strip().eq("")
    blank_group = raw["Research Group"].str.strip().eq("")
    duplicates = raw["subject"].duplicated(keep=False) & ~blank_subject
    values = raw[[real_col, syn_col]].apply(pd.to_numeric, errors="coerce")
    invalid_real = ~np.isfinite(values[real_col].to_numpy())
    invalid_syn = ~np.isfinite(values[syn_col].to_numpy())
    bad_pair = invalid_real | invalid_syn
    exclusions = blank_subject | duplicates | bad_pair
    outside = ((values < 0) | (values > 1)).any(axis=1).to_numpy() & ~bad_pair
    reasons = []
    for i in np.flatnonzero(exclusions):
        why = []
        if blank_subject.iloc[i]:
            why.append("blank_subject")
        if duplicates.iloc[i]:
            why.append("duplicate_subject")
        if invalid_real[i]:
            why.append("invalid_real")
        if invalid_syn[i]:
            why.append("invalid_syn")
        reasons.append({"row_number_in_csv": int(i) + 2, "subject": raw.at[i, "subject"],
                        "reasons": why})
    outliers = [
        {"row_number_in_csv": int(i) + 2, "subject": raw.at[i, "subject"],
         "real": float(values.iloc[i, 0]), "syn": float(values.iloc[i, 1])}
        for i in np.flatnonzero(outside)
    ]
    valid = raw.loc[~exclusions, ["subject", "Research Group"]].copy()
    valid["real"] = values.loc[~exclusions, real_col].to_numpy(dtype=float)
    valid["syn"] = values.loc[~exclusions, syn_col].to_numpy(dtype=float)
    audit = {
        "tracer": tracer, "roi_id": roi, "input_file": str(path.resolve()),
        "sha256": digest(path), "raw_rows": len(raw), "unique_subject_ids": raw["subject"].nunique(),
        "valid_pairs": len(valid), "excluded_rows": int(exclusions.sum()),
        "blank_subject_rows": int(blank_subject.sum()),
        "duplicate_subject_rows": int(duplicates.sum()),
        "blank_group_rows": int(blank_group.sum()),
        "invalid_real_rows": int(invalid_real.sum()),
        "invalid_syn_rows": int(invalid_syn.sum()),
        "incomplete_pair_rows": int((invalid_real ^ invalid_syn).sum()),
        "out_of_range_rows_included": int(outside.sum()),
        "diagnostic_groups_raw_counts": json.dumps(raw["Research Group"].value_counts().to_dict(), ensure_ascii=False),
        "diagnostic_groups_valid_counts": json.dumps(valid["Research Group"].value_counts().to_dict(), ensure_ascii=False),
        "excluded_row_details": json.dumps(reasons, ensure_ascii=False),
        "out_of_range_details": json.dumps(outliers, ensure_ascii=False),
    }
    raw_groups = dict(zip(raw["subject"], raw["Research Group"]))
    return valid, audit, raw_groups


def figure4_table(statistics: pd.DataFrame) -> str:
    lut_path = Path("/mnt/nfsdata/nfsdata/linshuijin/freesurfer/FreeSurferColorLUT.txt")
    if not lut_path.is_file():
        return "图 4 的 ROI ID 未能按现有标签表核验，因此未列出对应表。"
    lut = {}
    for line in lut_path.read_text().splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0].isdigit():
            lut[fields[1]] = fields[0]
    entries = {}
    for panel, labels in FIGURE4.items():
        tracer = "AV45" if panel in "ACE" else "FDG"
        for label in labels:
            roi = lut.get(label)
            if roi is None:
                raise ValueError(f"Figure 4 label has no LUT ID: {label}")
            key = (tracer, roi, label)
            entries.setdefault(key, []).append(panel)
    indexed = statistics.set_index(["tracer", "roi_id", "analysis_group"])
    lines = ["| 示踪剂 | 图 4 面板 | 原图标签 / LUT 标签 | ROI ID | overall N | overall p | overall q |",
             "|---|---|---|---:|---:|---:|---:|"]
    for (tracer, roi, label), panels in entries.items():
        if (tracer, roi, "overall") not in indexed.index:
            raise ValueError(f"Verified Figure 4 ROI absent from source CSVs: {tracer} {roi}")
        row = indexed.loc[(tracer, roi, "overall")]
        display = "Left-Cblm-WM → " + label if label == "Left-Cerebellum-White-Matter" else label
        lines.append(f"| {tracer} | {','.join(panels)} | {display} | {roi} | "
                     f"{int(row['n_pairs'])} | {row['paired_t_p_value']:.3g} | "
                     f"{row['fdr_q_value']:.3g} |")
    return "\n".join(lines)


def describe(series: pd.Series) -> str:
    vals = series.dropna().to_numpy(dtype=float)
    return (f"中位数 {np.median(vals):.4f}，四分位范围 "
            f"[{np.quantile(vals, 0.25):.4f}, {np.quantile(vals, 0.75):.4f}]，"
            f"最小–最大 [{np.min(vals):.4f}, {np.max(vals):.4f}]")


def write_report(statistics: pd.DataFrame, families: pd.DataFrame,
                 audit: pd.DataFrame, subjects: dict) -> None:
    lines = ["# R2-8 原稿区域摄取值配对重算", "",
             "## 来源与口径", "",
             "仅读取原作者保留的两个 `*_adjust` 目录中的 `region_*.csv`：", ""]
    for tracer, directory in INPUTS.items():
        subset = audit[audit.tracer == tracer]
        lines.append(f"- {tracer}: `{directory.resolve()}`；{len(subset)} 个文件，"
                     f"每文件原始 {subset.raw_rows.min()}–{subset.raw_rows.max()} 行，"
                     f"有效配对 {subset.valid_pairs.min()}–{subset.valid_pairs.max()} 人。")
    groups = sorted(set().union(*(set(json.loads(v)) for v in audit.diagnostic_groups_raw_counts)))
    lines += ["", f"原始 `Research Group` 标签：{', '.join(f'`{g}`' for g in groups)}。"
              "`overall` 是所有有效配对，分组逐个保留原标签；未合并 MCI 子类。",
              "两示踪剂队列分别分析，不跨示踪剂合并受试者。指标单位为逐图 min–max 归一化的区域摄取值（任意单位）。",
              "", "## 输入审计", ""]
    for tracer in INPUTS:
        sub = audit[audit.tracer == tracer]
        common = len(set.intersection(*subjects[tracer].values()))
        union = len(set.union(*subjects[tracer].values()))
        lines.append(f"- {tracer}: 共 {sub.raw_rows.sum()} 个原始 ROI 行、"
                     f"{sub.valid_pairs.sum()} 个有效 ROI 配对，排除 {sub.excluded_rows.sum()} 行；"
                     f"ROI 间原始受试者集合交集/并集 {common}/{union}。"
                     f"重复 ID {sub.duplicate_subject_rows.sum()} 行，单侧不完整配对 "
                     f"{sub.incomplete_pair_rows.sum()} 行，空/非数值双侧测量 "
                     f"{sub.excluded_rows.sum() - sub.incomplete_pair_rows.sum()} 行；"
                     f"保留但标记区间外数值 {sub.out_of_range_rows_included.sum()} 行。")
        lines.append(f"  相对首个 ROI 的原始受试者缺失/额外记录分别为 "
                     f"{sub.subjects_missing_vs_first_roi.sum()}/"
                     f"{sub.subjects_extra_vs_first_roi.sum()}；"
                     f"共同受试者的分组标签不一致 {sub.group_mismatches_vs_first_roi.sum()} 项。")
    lines += ["", "每个文件的完整路径、SHA-256、原始行数、分组人数、排除行号与受试者 ID、"
              "异常值见 `input_audit.csv`。有限的区间外数值参与计算，没有裁剪或插补。", "",
              "## 方法", "",
              "每个 tracer × ROI 分别在 overall 和每个原始诊断组内以同一受试者的 "
              "`d = Syn − Real` 计算。SD 使用样本标准差（ddof=1）；95% 均值差 CI "
              "为 `mean(d) ± t(0.975,N−1) × SD(d)/√N`；双侧配对 t 检验使用 SciPy `ttest_rel`。"
              "MAE 为 `mean(|d|)`，RMSE 为 `sqrt(mean(d²))`。",
              "Lin CCC = `2 cov(Real,Syn) / [var(Real)+var(Syn)+(mean(Real)−mean(Syn))²]`，"
              "其中 cov/var 使用 N 分母；ICC(A,1) 为双因素绝对一致性单次测量 ANOVA 公式。"
              "Bland–Altman 均值偏倚等于 `mean(d)`，95% 一致性界限为 "
              "`mean(d) ± 1.96 × SD(d)`（描述性正态近似，非置信区间）。",
              "每个 tracer × analysis_group 的所有可计算 ROI 双侧配对 t 检验 p 值构成一个事先固定的比较族；"
              "SciPy `false_discovery_control(method='bh')` 实施 Benjamini–Hochberg FDR，"
              "显著性阈值 q < 0.05。未做 TOST，也未指定等效界值。", "",
              "## 结果", "",
              "| 示踪剂 | 分组 | ROI 检验数 | q < 0.05 | q ≥ 0.05 |",
              "|---|---|---:|---:|---:|"]
    for row in families.itertuples():
        lines.append(f"| {row.tracer} | {row.analysis_group} | {row.n_tests} | "
                     f"{row.n_significant_q_lt_0_05} | {row.n_nonsignificant_q_ge_0_05} |")
    significant = statistics[statistics.significant_q_lt_0_05]
    if len(significant):
        lines += ["", "校正后显著的完整条目：", "",
                  "| 示踪剂 | ROI ID | 分组 | N | 均值差 (Syn−Real) | 95% CI | p | q |",
                  "|---|---:|---|---:|---:|---|---:|---:|"]
        for row in significant.itertuples():
            lines.append(f"| {row.tracer} | {row.roi_id} | {row.analysis_group} | {row.n_pairs} | "
                         f"{row.mean_difference_syn_minus_real:.6f} | "
                         f"[{row.mean_difference_ci95_lower:.6f}, "
                         f"{row.mean_difference_ci95_upper:.6f}] | "
                         f"{row.paired_t_p_value:.6g} | {row.fdr_q_value:.6g} |")
    lines += ["", "以下分布均跨对应示踪剂的 98 个 **overall ROI**，不是受试者分布：", ""]
    for tracer in INPUTS:
        sub = statistics[(statistics.tracer == tracer) & (statistics.analysis_group == "overall")]
        lines.append(f"- {tracer}: MAE {describe(sub.mae)}；CCC {describe(sub.ccc)}；"
                     f"ICC(A,1) {describe(sub.icc_a1)}。")
        lines.append(f"  Bland–Altman 下界 {describe(sub.ba_loa95_lower)}；"
                     f"上界 {describe(sub.ba_loa95_upper)}。")
    lines += ["", "## 原图 Figure 4 的核验 ROI", "",
              "图中标签按 `manuscript/figures/figure_4.pdf` 目视抄录；ROI ID 用现有 "
              "`/mnt/nfsdata/nfsdata/linshuijin/freesurfer/FreeSurferColorLUT.txt` 核对，"
              "并确认相应原始 CSV 存在。E 面板的 `Left-Cblm-WM` 按图注缩写与 LUT "
              "`Left-Cerebellum-White-Matter` 对应。C–F 是疾病组间图；表内 p/q 仍仅为本次 "
              "Real–Syn overall 配对重算，不能解释为 C–F 的组间检验。", "",
              figure4_table(statistics), "", "## 与原稿表述及限制", ""]
    principal = statistics[(statistics.analysis_group.isin(["CN", "MCI", "AD"])) &
                           (statistics.roi_id.isin(["1025", "2025", "1032", "2032",
                                                   "1033", "2033", "1028", "2028"]))]
    raw_sig = principal[principal.paired_t_p_value < ALPHA]
    fdr_sig = principal[principal.fdr_q_value < ALPHA]
    if len(raw_sig):
        lines.append(f"原稿称 Figure 4 A/B 的主要区域在 CN/MCI/AD 均 `p > 0.05`。"
                     f"本次在 A/B 对应 8 个 ROI × 3 个原始分组 × 2 示踪剂中有 {len(raw_sig)} 项原始 "
                     f"p < 0.05、{len(fdr_sig)} 项 q < 0.05（各组及精确 p/q 见统计 CSV），"
                     f"因此该笼统断言与保存的"
                     f"逐人 CSV 重算不一致。注意原稿图示可能使用不同子集或处理流程；"
                     f"目前未证实其实际绘图输入与这些 CSV 完全相同。")
        lines.append("具体原始 p < 0.05 条目：" + "；".join(
            f"{row.tracer} ROI {row.roi_id} / {row.analysis_group} "
            f"p={row.paired_t_p_value:.6g}, q={row.fdr_q_value:.6g}"
            for row in raw_sig.itertuples()
        ) + "。")
    else:
        lines.append("A/B 对应的原始分组重算未发现 p < 0.05；仍无法据此证明原稿绘图输入"
                     "与这些 CSV 完全相同。")
    lines += ["", "均值偏倚与配对 t 检验只评估平均差异；MAE、CCC、ICC 和一致性界限"
              "提供个体误差与一致性的补充视角。不同 ROI 的观测相关，FDR 仅控制所声明"
              "比较族的多重检验；分组大小与缺失测量按原始文件决定。未核实参考区比值归一化，"
              "因此不得称 SUV/SUVR。**不显著（包括 p > 0.05 或 q ≥ 0.05）不证明等效、"
              "高保真或个体级精度。**", ""]
    (OUTPUT / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    audit_rows, result_rows = [], []
    subjects = {}
    for tracer, directory in INPUTS.items():
        files = sorted(directory.glob("region_*.csv"), key=lambda p: int(ROI_PATTERN.fullmatch(p.name).group(1)))
        if not files:
            raise FileNotFoundError(f"No ROI CSVs in {directory}")
        subjects[tracer] = {}
        first_groups = None
        first_subjects = None
        for path in files:
            valid, audit, raw_groups = load_roi(tracer, path)
            roi = audit["roi_id"]
            subject_set = set(raw_groups)
            subjects[tracer][roi] = subject_set
            if first_groups is None:
                first_groups = raw_groups
                first_subjects = subject_set
            audit["subjects_missing_vs_first_roi"] = len(first_subjects - subject_set)
            audit["subjects_extra_vs_first_roi"] = len(subject_set - first_subjects)
            audit["group_mismatches_vs_first_roi"] = sum(
                raw_groups[subject] != first_groups[subject]
                for subject in subject_set & first_subjects
            )
            audit_rows.append(audit)
            for group in ["overall", *sorted(valid["Research Group"].unique())]:
                subset = valid if group == "overall" else valid[valid["Research Group"] == group]
                if subset.empty:
                    continue
                result_rows.append({"tracer": tracer, "roi_id": roi, "analysis_group": group,
                                    "input_file": audit["input_file"],
                                    **paired_metrics(subset.real.to_numpy(), subset.syn.to_numpy())})
    statistics = pd.DataFrame(result_rows)
    audit = pd.DataFrame(audit_rows)
    family_rows = []
    statistics["fdr_q_value"] = np.nan
    statistics["fdr_family_n_tests"] = 0
    statistics["significant_q_lt_0_05"] = False
    for (tracer, group), frame in statistics.groupby(["tracer", "analysis_group"], sort=False):
        usable = frame["paired_t_p_value"].notna()
        indexes = frame.index[usable]
        p = frame.loc[indexes, "paired_t_p_value"].to_numpy(dtype=float)
        q = stats.false_discovery_control(p, method="bh") if len(p) else np.array([])
        statistics.loc[indexes, "fdr_q_value"] = q
        statistics.loc[frame.index, "fdr_family_n_tests"] = len(p)
        statistics.loc[indexes, "significant_q_lt_0_05"] = q < ALPHA
        family_rows.append({"tracer": tracer, "analysis_group": group,
                            "correction_method": "Benjamini-Hochberg (SciPy false_discovery_control, method=bh)",
                            "n_available_rois": len(frame), "n_tests": len(p),
                            "n_unavailable_p_values": len(frame) - len(p),
                            "n_significant_q_lt_0_05": int(np.sum(q < ALPHA)),
                            "n_nonsignificant_q_ge_0_05": int(np.sum(q >= ALPHA)),
                            "alpha": ALPHA})
    families = pd.DataFrame(family_rows)
    statistics.to_csv(OUTPUT / "regional_paired_statistics.csv", index=False, float_format="%.17g")
    families.to_csv(OUTPUT / "statistical_families.csv", index=False)
    audit.to_csv(OUTPUT / "input_audit.csv", index=False)
    write_report(statistics, families, audit, subjects)
    print(f"Analyzed {len(audit)} files, {len(statistics)} tracer × ROI × group rows, "
          f"{len(families)} FDR families; excluded {audit.excluded_rows.sum()} rows.")


if __name__ == "__main__":
    main()
