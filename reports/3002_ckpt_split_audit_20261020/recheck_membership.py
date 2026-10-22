"""Recheck the extracted historical lists; never access images or training code."""
import datetime
import hashlib
import json
import pathlib
import re


BASE = pathlib.Path(__file__).resolve().parent


def available(path):
    return bool(path) and "/zero/" not in path and "_zero." not in path


def image_id(path):
    matches = re.findall(r"I(\d+)", pathlib.Path(path or "").name, re.I)
    return "I" + str(int(matches[-1])) if matches else ""


def identity(row, kind):
    if kind == "ptid":
        return row["name"]
    if kind == "ptid_date":
        date = row["examdate"].replace("/", "-")
        date = datetime.date(*map(int, date.split("-"))).isoformat()
        return row["name"], date
    return row["name"], image_id(row.get(kind))


def main():
    receipts = json.loads((BASE / "historical_receipts.json").read_text())
    for item in receipts["files"] + receipts["sources"]:
        path = BASE / pathlib.Path(item["extracted_path"]).relative_to(
            "reports/3002_ckpt_split_audit_20261020"
        )
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != item["sha256"]:
            raise ValueError(f"Extracted source SHA mismatch: {path}")

    results = {}
    for revision in ["7bc69a2", "9ba7133"]:
        splits = {
            split: json.loads(
                (BASE / "historical_json" / f"{revision}__{split}_data_with_description.json")
                .read_text()
            )
            for split in ["train", "val"]
        }
        overlaps = {}
        for kind in ["ptid", "ptid_date", "mri", "fdg", "av45", "tau"]:
            sets = [
                {
                    identity(row, kind)
                    for row in splits[split]
                    if kind in ["ptid", "ptid_date"] or available(row.get(kind))
                }
                for split in ["train", "val"]
            ]
            overlaps[kind] = len(sets[0] & sets[1])
        results[revision] = {
            "rows": {split: len(rows) for split, rows in splits.items()},
            "unique_ptids": {
                split: len({row["name"] for row in rows})
                for split, rows in splits.items()
            },
            "train_val_intersections": overlaps,
        }
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
