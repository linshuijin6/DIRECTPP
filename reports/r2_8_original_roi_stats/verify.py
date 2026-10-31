"""Independent source-row and BH checks for the R2-8 original ROI tables."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SOURCE = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin"
DIRECTORIES = {"AV45": SOURCE / "statistics_of_regions_av45_adjust",
               "FDG": SOURCE / "statistics_of_regions_fdg_adjust"}


def close(actual: float, expected: float, label: str) -> None:
    if not np.isclose(actual, expected, rtol=2e-11, atol=2e-13, equal_nan=True):
        raise AssertionError(f"{label}: table={actual}, source recomputation={expected}")


def check_one(row: pd.Series, real: np.ndarray, syn: np.ndarray) -> None:
    n = len(real)
    d = np.subtract(syn, real)
    mean = np.mean(d)
    sd = np.std(d, ddof=1)
    t = stats.ttest_1samp(d, 0)
    quantities = {
        "n_pairs": n,
        "real_mean": np.mean(real), "syn_mean": np.mean(syn),
        "real_sd": np.std(real, ddof=1), "syn_sd": np.std(syn, ddof=1),
        "mean_difference_syn_minus_real": mean,
        "difference_sd": sd,
        "mean_difference_ci95_lower": stats.t.interval(0.95, n - 1, loc=mean, scale=sd / np.sqrt(n))[0],
        "mean_difference_ci95_upper": stats.t.interval(0.95, n - 1, loc=mean, scale=sd / np.sqrt(n))[1],
        "paired_t_statistic": t.statistic, "paired_t_p_value": t.pvalue,
        "mae": np.abs(d).mean(), "rmse": np.linalg.norm(d) / np.sqrt(n),
        "ba_mean_bias": mean, "ba_loa95_lower": mean - 1.96 * sd,
        "ba_loa95_upper": mean + 1.96 * sd,
    }
    moments = np.cov(np.stack((real, syn)), bias=True)
    quantities["ccc"] = 2 * moments[0, 1] / (
        moments[0, 0] + moments[1, 1] + (real.mean() - syn.mean()) ** 2)
    # Orthogonal two-way ANOVA decomposition, independent of the analysis helper.
    y = np.stack((real, syn), axis=1)
    grand = y.mean()
    row_mean = y.mean(axis=1)
    col_mean = y.mean(axis=0)
    ss_subject = 2 * np.square(row_mean - grand).sum()
    ss_rater = n * np.square(col_mean - grand).sum()
    ss_total = np.square(y - grand).sum()
    ms_subject = ss_subject / (n - 1)
    ms_rater = ss_rater
    ms_error = (ss_total - ss_subject - ss_rater) / (n - 1)
    quantities["icc_a1"] = (ms_subject - ms_error) / (
        ms_subject + ms_error + 2 * (ms_rater - ms_error) / n)
    for name, expected in quantities.items():
        close(row[name], expected, f"{row.tracer}/{row.roi_id}/{row.analysis_group}/{name}")


def main() -> None:
    table = pd.read_csv(HERE / "regional_paired_statistics.csv", dtype={"roi_id": str})
    audit = pd.read_csv(HERE / "input_audit.csv", dtype={"roi_id": str})
    families = pd.read_csv(HERE / "statistical_families.csv")
    assert len(audit) == 196 and len(table) == 1176 and len(families) == 12
    assert table[["tracer", "roi_id", "analysis_group"]].duplicated().sum() == 0
    checked = 0
    for a in audit.itertuples(index=False):
        path = Path(a.input_file)
        assert path.parent == DIRECTORIES[a.tracer]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == a.sha256
        raw = pd.read_csv(path, dtype={"subject": str, "Research Group": str})
        assert len(raw) == a.raw_rows
        assert raw.subject.isna().sum() == 0
        assert raw.subject.duplicated().sum() == 0
        assert raw["Research Group"].isna().sum() == 0
        real_col = f"real_{a.tracer.lower()}_mean"
        syn_col = f"syn_{a.tracer.lower()}_mean"
        finite = np.isfinite(raw[[real_col, syn_col]].to_numpy()).all(axis=1)
        assert finite.sum() == a.valid_pairs
        assert (~finite).sum() == a.excluded_rows
        for row in table[(table.tracer == a.tracer) & (table.roi_id == a.roi_id)].itertuples(index=False):
            group_mask = np.ones(len(raw), dtype=bool) if row.analysis_group == "overall" else (
                raw["Research Group"] == row.analysis_group).to_numpy()
            selected = raw.loc[finite & group_mask]
            check_one(pd.Series(row._asdict()), selected[real_col].to_numpy(),
                      selected[syn_col].to_numpy())
            checked += 1

    # Independent BH implementation: sort p ascending, then reverse cumulative min.
    q_checked = 0
    for family in families.itertuples(index=False):
        selection = (table.tracer == family.tracer) & (table.analysis_group == family.analysis_group)
        frame = table.loc[selection]
        p = frame.paired_t_p_value.to_numpy()
        order = np.argsort(p)
        ranked = p[order] * len(p) / np.arange(1, len(p) + 1)
        q = np.empty_like(p)
        q[order] = np.minimum(1.0, np.minimum.accumulate(ranked[::-1])[::-1])
        np.testing.assert_allclose(frame.fdr_q_value.to_numpy(), q, rtol=2e-11, atol=2e-13)
        assert family.n_tests == len(p) == 98
        assert np.all(frame.fdr_family_n_tests == family.n_tests)
        assert int((q < 0.05).sum()) == family.n_significant_q_lt_0_05
        q_checked += len(p)

    report = HERE / "REPORT.md"
    content = report.read_text()
    heading = "## 独立核验"
    if heading in content:
        content = content.split(heading)[0].rstrip() + "\n"
    content += (f"\n{heading}\n\n"
                f"`verify.py` 从原始 CSV 逐行重读并校验 196 个 SHA-256、原始/排除行数；"
                f"用 NumPy/SciPy 的独立表达式复算全部 {checked} 行统计量，"
                f"以排序及反向累计最小值独立核对全部 {q_checked} 个 BH q 值。"
                f"指定输入目录检查通过，输出没有 E1 测量来源。"
                f"原稿 Figure 4 的实际绘图输入身份与这些 CSV 的一致性仍未核实。\n")
    report.write_text(content)
    print(f"PASS: {len(audit)} source files, {checked} statistics rows, {q_checked} BH q-values")


if __name__ == "__main__":
    main()
