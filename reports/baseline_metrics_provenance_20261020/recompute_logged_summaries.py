"""Read-only arithmetic and identity checks; no ML/image dependencies.

Run from the DIRECTPP project root:
  python reports/baseline_metrics_provenance_20261020/recompute_logged_summaries.py
"""
import argparse
import csv
import json
from pathlib import Path
import re
import statistics

parser = argparse.ArgumentParser()
parser.add_argument("--project-root", type=Path, default=Path.cwd())
args = parser.parse_args()
here = Path(__file__).resolve().parent


def read_json(path):
    return json.loads(path.read_text())


text = (here / "source_extracts/vscode-3002_mri2pet _two trace_new-final_cell11.outputs.txt").read_text()
ptids = set(re.findall(r"(?<![0-9])\d{3}_S_\d+(?![0-9])", text))
train_path = args.project_root / "reports/final165_training_split_audit_20261020/supplied_train_1856.json"
train = {r["name"] for r in read_json(train_path)}
assert ptids == train and len(ptids) == 1856
assert "011_S_4105" not in ptids
rows = []
sid = None
for line in text.splitlines():
    subjects = re.findall(r"(?<![0-9])\d{3}_S_\d+(?![0-9])", line)
    if subjects:
        sid = subjects[-1]
    match = re.search(r"\[(FDG|AV45)\] SSIM: ([\d.]+), PSNR: ([\d.]+)", line)
    if match:
        assert sid is not None
        rows.append((sid, match[1].lower(), float(match[2]), float(match[3])))
assert len(rows) == len({r[:2] for r in rows}) == 2961
original = {}
for tracer, count in [("fdg", 1597), ("av45", 1364)]:
    subset = [r for r in rows if r[1] == tracer]
    assert len(subset) == count
    original[tracer] = dict(n=count, ssim_percent=100*statistics.mean(r[2] for r in subset),
                            psnr=statistics.mean(r[3] for r in subset))

text = (here / "source_extracts/vscode-3003_mri2pet all data_add personal clip_flow_cell16.outputs.txt").read_text()
names = re.findall(r"Subject name: (\d{3}_S_\d+)", text)
val = read_json(here / "single_flow_val_from_original_output.json")
all_data = read_json(here / "single_flow_all_from_original_output.json")
assert names == [r["name"] for r in val] == [r["name"] for r in all_data[800:]]
values = [tuple(map(float, m)) for m in re.findall(
    r"^SSIM: ([\d.e+-]+), PSNR: ([\d.e+-]+), MSE: ([\d.e+-]+), MAE: ([\d.e+-]+)", text, re.M)]
assert len(values) == len(names) == len(set(names)) == 329
single = dict(n=329, **{key: statistics.mean(row[i] for row in values)
                       for i, key in enumerate(["ssim", "psnr", "mse", "mae"])})

figure = list(csv.DictReader((here / "paper_figure2_values.csv").open()))
table = read_json(here / "original_assets/performance_table_extracted.json")["sheets"]["Sheet1"]
for i, row in enumerate(table[2:]):
    for cohort, cols in [("ADNI_FDG", [1, 2, 3, 4]), ("ADNI_AV45", [6, 7, 8, 9]), ("OASIS", [11, 12, 13, 14])]:
        fig = [r for r in figure if r["cohort"] == cohort][i]
        assert [float(fig[k]) for k in ["SSIM_percent", "PSNR", "MSE_percent", "MAE_percent"]] == [row[k] for k in cols]

print(json.dumps(dict(status="PASS_FOR_SCOPED_LOG_AND_TABLE_CHECKS", original165=original,
                     original165_output_membership_equals_train=True, single_flow141=single,
                     figure_excel_numeric_values_equal=84,
                     scope="Saved text-output arithmetic and identities; no inference or paper run certification"), indent=2))
