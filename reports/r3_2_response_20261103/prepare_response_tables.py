"""Reconstruct descriptive summaries from the existing E1 clinical export.

CPU only; no imputation, training, or modification of archived inputs.
Availability is at the recovered demographic anchor, not ADNI-wide missingness.
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SRC = ROOT / "reports/e1_stage01_20261017"
GROUPS = ["CN", "EMCI", "LMCI", "MCI", "AD"]
SCORES = ["MMSE Total Score", "GDSCALE Total Score", "Global CDR",
          "FAQ Total Score", "NPI-Q Total Score"]


def main():
    meta = pd.read_csv(SRC / "metadata.csv")
    raw = pd.read_csv(SRC / "clinical_export.csv", low_memory=False)
    keys = ["Subject ID", "Sex", "Weight", "Research Group", "Age"]
    assert len(meta) == meta["Subject ID"].nunique() == 1857
    joined = meta[keys].merge(raw, on=keys, how="left", indicator=True)
    assert joined.loc[joined._merge == "both", "Subject ID"].nunique() == len(meta)
    obs = meta[keys].set_index("Subject ID")
    for col in SCORES:
        obs[col] = joined.groupby("Subject ID")[col].agg(
            lambda x: x.dropna().iloc[0] if x.nunique(dropna=True) == 1 else np.nan)
    obs.loc[obs.Weight <= 0, "Weight"] = np.nan
    previous = pd.read_csv(SRC / "observed.csv").set_index("Subject ID")
    pd.testing.assert_frame_equal(obs.sort_index(), previous[obs.columns].sort_index(),
                                  check_dtype=False)
    summaries, missing = [], []
    for col in ["Age", "Sex", "Weight"] + SCORES:
        summary = {"variable": col}
        miss = {"variable": col}
        for group in GROUPS:
            sub = obs.loc[obs["Research Group"] == group, col]
            valid = sub.dropna()
            n, total = len(valid), len(sub)
            miss[group] = f"{total-n}/{total} ({100*(total-n)/total:.1f}%)"
            summary[group] = (f"M/F={int((valid == 'M').sum())}/{int((valid == 'F').sum())}; n={n}"
                              if col == "Sex" else
                              f"{valid.mean():.2f} ± {valid.std(ddof=1):.2f}; n={n}" if n > 1 else
                              f"{valid.iloc[0]:.2f}; SD unavailable; n=1" if n == 1 else "Unavailable; n=0")
        miss["Overall"] = f"{obs[col].isna().sum()}/{len(obs)} ({100*obs[col].isna().mean():.1f}%)"
        summaries.append(summary)
        missing.append(miss)
    pd.DataFrame(summaries).to_csv(OUT / "observed_summary.csv", index=False)
    pd.DataFrame(missing).to_csv(OUT / "missingness_by_group.csv", index=False)
    print("Reconstructed 1,857 subjects; matched archived observed values; wrote two aggregate tables.")
    print(pd.DataFrame(missing).to_string(index=False))


if __name__ == "__main__":
    main()
