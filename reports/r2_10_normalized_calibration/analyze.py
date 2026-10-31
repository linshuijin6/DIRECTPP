"""Describe Syn-versus-Real normalized uptake for Figure 4A/B's 16 ROIs.

Run from the repository root:
    python -m reports.r2_10_normalized_calibration.analyze
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from reports.r2_8_original_roi_stats.analyze import INPUTS, load_roi


ROOT = Path(__file__).resolve().parents[2]
R2_8 = ROOT / "reports/r2_8_original_roi_stats"
OUTPUT = Path(__file__).resolve().parent
ROI_IDS = {1025, 2025, 1032, 2032, 1033, 2033, 1028, 2028}


def check_close(actual: float, expected: float, label: str) -> None:
    if not np.isclose(actual, expected, rtol=2e-11, atol=2e-13):
        raise AssertionError(f"{label}: current={actual}, R2-8={expected}")


def main() -> None:
    selection = pd.read_csv(R2_8 / "supplementary_tables/figure4_primary_regions.csv")
    selection = selection[["Tracer", "ROI ID", "ROI anatomical name"]].drop_duplicates()
    assert len(selection) == 16
    assert set(selection.Tracer) == {"AV45", "FDG"}
    for tracer, frame in selection.groupby("Tracer"):
        assert len(frame) == 8 and set(frame["ROI ID"]) == ROI_IDS, tracer

    paired = pd.read_csv(R2_8 / "regional_paired_statistics.csv")
    paired = paired[paired.analysis_group == "overall"].set_index(["tracer", "roi_id"])
    supplementary = pd.read_csv(R2_8 / "supplementary_tables/overall_regional_statistics.csv")
    supplementary = supplementary.set_index(["Tracer", "ROI ID"])
    source_audit = pd.read_csv(R2_8 / "input_audit.csv").set_index(["tracer", "roi_id"])

    results = []
    for selected in selection.itertuples(index=False):
        tracer, roi_id, name = selected
        path = INPUTS[tracer] / f"region_{roi_id}.0.csv"
        data, audit, _ = load_roi(tracer, path)
        key = tracer, roi_id
        old = paired.loc[key]
        old_supp = supplementary.loc[key]
        old_audit = source_audit.loc[key]
        assert audit["sha256"] == old_audit.sha256
        assert audit["raw_rows"] == old_audit.raw_rows
        assert audit["valid_pairs"] == old_audit.valid_pairs
        assert audit["excluded_rows"] == old_audit.excluded_rows
        assert audit["out_of_range_rows_included"] == old_audit.out_of_range_rows_included
        assert str(path.resolve()) == old.input_file == old_audit.input_file
        assert name == old_supp["ROI anatomical name"]

        real = data.real.to_numpy(dtype=float)
        syn = data.syn.to_numpy(dtype=float)
        n = len(real)
        assert n == old.n_pairs == old_supp.N
        bias = float(np.mean(syn - real))
        moments = np.cov(np.stack((real, syn)), bias=True)
        ccc = float(2 * moments[0, 1] / (
            moments[0, 0] + moments[1, 1] + (real.mean() - syn.mean()) ** 2
        ))
        check_close(bias, old.mean_difference_syn_minus_real, f"{key} bias")
        check_close(ccc, old.ccc, f"{key} CCC")
        check_close(bias, old_supp["Mean paired difference (Syn - Real)"], f"{key} supplementary bias")
        check_close(ccc, old_supp.CCC, f"{key} supplementary CCC")
        check_close(old.icc_a1, old_supp["ICC(A,1)"], f"{key} ICC")

        fit = stats.linregress(real, syn)
        critical = stats.t.ppf(0.975, n - 2)
        results.append({
            "Tracer": tracer,
            "ROI ID": roi_id,
            "ROI anatomical name": name,
            "N": n,
            "OLS slope": fit.slope,
            "Slope 95% CI lower": fit.slope - critical * fit.stderr,
            "Slope 95% CI upper": fit.slope + critical * fit.stderr,
            "OLS intercept": fit.intercept,
            "Intercept 95% CI lower": fit.intercept - critical * fit.intercept_stderr,
            "Intercept 95% CI upper": fit.intercept + critical * fit.intercept_stderr,
            "Pearson r": fit.rvalue,
            "R-squared": fit.rvalue ** 2,
            "Observed Real minimum": real.min(),
            "Observed Real maximum": real.max(),
            "Observed Syn minimum": syn.min(),
            "Observed Syn maximum": syn.max(),
            "Mean signed bias (Syn - Real)": bias,
            "Existing CCC": old.ccc,
            "Existing ICC(A,1)": old.icc_a1,
            "Source CSV": str(path.resolve()),
            "Source SHA-256": audit["sha256"],
            "Raw source rows": audit["raw_rows"],
            "Excluded source rows": audit["excluded_rows"],
        })

    result = pd.DataFrame(results)
    assert len(result) == 16 and not result[["Tracer", "ROI ID"]].duplicated().any()
    result.to_csv(OUTPUT / "calibration_results.csv", index=False, float_format="%.17g")
    print("Verified and wrote 16 overall-cohort tracer–ROI regressions.")
    for tracer, frame in result.groupby("Tracer", sort=False):
        print(f"{tracer}: slope median={frame['OLS slope'].median():.6f}, "
              f"range=[{frame['OLS slope'].min():.6f}, {frame['OLS slope'].max():.6f}]; "
              f"intercept median={frame['OLS intercept'].median():.6f}, "
              f"range=[{frame['OLS intercept'].min():.6f}, "
              f"{frame['OLS intercept'].max():.6f}]")


if __name__ == "__main__":
    main()
