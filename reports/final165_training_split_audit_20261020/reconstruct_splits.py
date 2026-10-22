"""Reconstruct split identities from saved filenames; never load images or train.

Run with an environment containing scikit-learn, for example:
  /home/data/linshuijin/.conda/envs/xiaochou/bin/python reconstruct_splits.py
Prints checks to stdout and does not modify source files.
"""
import csv
import hashlib
import json
from pathlib import Path

import sklearn
from sklearn.model_selection import train_test_split


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def read_json(path):
    return json.loads(path.read_text())


receipt = read_json(HERE / "3002_original_directory_receipt.json")
binding = read_json(HERE / "split_source_binding.json")
maps = {}
for modality, filenames in receipt["files"].items():
    maps[modality] = {"_".join(f.split("_")[:3]): f for f in sorted(filenames)}
    assert len(maps[modality]) == len(filenames), f"Duplicate PTID: {modality}"

mri = maps["mri_strip_registered"]
av45 = maps["PET1_AV45_strip_registered"]
fdg = maps["PET2_FDG_strip_registered"]
paired = [ptid for ptid in mri if ptid in av45 and ptid in fdg]
indices = {ptid: index for index, ptid in enumerate(paired)}
csv_path = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/filtered_subjects_with_description.csv"
assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == (
    "ab18b0439512c0460aa034b6d57be7df72f692209e6ff60eb0e7c064aced8445"
)
with csv_path.open(newline="") as handle:
    descriptions = {row["Subject ID"]: row["Description"] for row in csv.DictReader(handle)}
assert len(paired) == 1857 and set(paired) == set(descriptions)

reconstructed = train_test_split(paired, test_size=1, random_state=42)
counts = {}
for split, expected in zip(("train", "val"), reconstructed):
    path = HERE / ("supplied_train_1856.json" if split == "train" else "supplied_val_1.json")
    expected_hash = binding["supplied_manifest_identity"][split]["sha256"]
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected_hash
    rows = read_json(path)
    assert expected == [row["name"] for row in rows], f"Order mismatch: {split}"
    for row in rows:
        ptid = row["name"]
        assert row["fdg_index"] == row["av45_index"] == indices[ptid]
        assert row["description"] == descriptions[ptid]
        for key, filenames in (("mri", mri), ("av45", av45), ("fdg", fdg)):
            assert Path(row[key]).name == filenames[ptid]
    counts[split] = len(rows)
assert not set(reconstructed[0]) & set(reconstructed[1])

later = train_test_split(paired, test_size=int(len(paired) * 0.1), random_state=42)
for split, expected in zip(("train", "val"), later):
    rows = read_json(HERE.parent / "csv_bound_ckpt_search_20261020" / f"matching_1857_{split}.json")
    assert expected == [row["name"] for row in rows], f"Later split mismatch: {split}"

print(json.dumps({
    "status": "PASS_FOR_IDENTITY_RECONSTRUCTION",
    "sklearn_version": sklearn.__version__, "subjects": len(paired),
    "counts": counts, "validation_subjects": reconstructed[1],
    "all_order_index_description_and_filename_checks": True,
    "later_10_percent_counts": {"train": len(later[0]), "val": len(later[1])},
    "scope": "Saved filenames and supplied manifests; no historical training replay or image-content verification",
}, indent=2))
