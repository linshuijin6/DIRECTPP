#!/usr/bin/env python3
"""Finalize completed Stage 4C-4 group receipts into classification-bound assets."""

from __future__ import annotations

import csv
import hashlib
import json
import os
import tempfile
from collections import Counter
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
REPORT_DIR = REPO / "reports/full_ot_medical_evidence"
FORMAL_ROOT = Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4c3_train_side/20261028/epoch165")
GROUP_EXPECTED = {(1, "Full"): 914, (1, "OT"): 914, (2, "Full"): 896, (2, "OT"): 896}
TASKS = ("ad_cn", "mci_cn", "lmci_emci")
OUT_FULL = REPORT_DIR / "04c4_full_prediction_manifest.csv"
OUT_ASSET = REPORT_DIR / "04c4_classification_asset_index.csv"
OUT_REPORT = REPORT_DIR / "04c4_full_inference_report.md"
OUT_RECEIPT = REPORT_DIR / "04c4_full_inference_receipt.json"


class FinalizeError(RuntimeError):
    pass


def sha256(path: Path, chunk_size: int = 8 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_text(path: Path, text: str) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def atomic_json(path: Path, payload: object) -> None:
    atomic_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n")


def atomic_csv(path: Path, rows: list[dict[str, object]], fields: list[str]) -> None:
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def verify_prediction(path: Path, expected_sha: str, expected_bytes: int | None = None) -> None:
    if not path.is_file():
        raise FinalizeError(f"missing prediction: {path}")
    if expected_bytes is not None and path.stat().st_size != expected_bytes:
        raise FinalizeError(f"prediction byte mismatch: {path}")
    if sha256(path) != expected_sha:
        raise FinalizeError(f"prediction SHA mismatch: {path}")


def load_groups() -> tuple[list[dict], dict[tuple[str, int, str, str], dict], list[dict]]:
    records: list[dict] = []
    keyed: dict[tuple[str, int, str, str], dict] = {}
    groups: list[dict] = []
    for fold in (1, 2):
        for model in ("Full", "OT"):
            run_dir = FORMAL_ROOT / f"outer_fold{fold}" / model.lower()
            complete_path = run_dir / "complete.json"
            manifest_path = run_dir / "prediction_manifest.json"
            failure_path = run_dir / "failure.json"
            if failure_path.exists():
                raise FinalizeError(f"group has failure marker: {failure_path}")
            if not complete_path.is_file() or not manifest_path.is_file():
                raise FinalizeError(f"group receipt is incomplete: {run_dir}")
            complete = json.loads(complete_path.read_text())
            if complete.get("status") != "COMPLETE" or complete.get("mode") != "formal":
                raise FinalizeError(f"group not COMPLETE/formal: {run_dir}")
            if complete.get("model") != model or int(complete.get("outer_fold")) != fold or int(complete.get("epoch")) != 165:
                raise FinalizeError(f"group identity mismatch: {run_dir}")
            if not complete.get("cache_tree_unchanged") or not complete.get("selected_cache_sha_unchanged"):
                raise FinalizeError(f"cache invariance failed: {run_dir}")
            if sha256(manifest_path) != complete.get("prediction_manifest_sha256"):
                raise FinalizeError(f"group manifest SHA mismatch: {run_dir}")
            group_records = json.loads(manifest_path.read_text())["records"]
            expected = GROUP_EXPECTED[(fold, model)]
            if len(group_records) != expected or int(complete.get("records")) != expected:
                raise FinalizeError(f"group count mismatch: {run_dir}")
            if len(complete.get("subjects", [])) * 2 != expected:
                raise FinalizeError(f"group subject count mismatch: {run_dir}")
            for rec in group_records:
                key = (model, fold, rec["ptid"], rec["tracer"])
                if key in keyed:
                    raise FinalizeError(f"duplicate formal prediction identity: {key}")
                if rec["model"] != model or int(rec["outer_fold"]) != fold or rec["execution_mode"] != "formal":
                    raise FinalizeError(f"record identity mismatch: {key}")
                if int(rec["generator_fold"]) == fold:
                    raise FinalizeError(f"outer-test subject found in train-side records: {key}")
                if rec["shape"] != "160x192x160" or rec["dtype"] != "float32" or not rec["finite"]:
                    raise FinalizeError(f"record array QC failed: {key}")
                if float(rec["min"]) < -1e-6 or float(rec["max"]) > 1.000001 or float(rec["std"]) <= 0:
                    raise FinalizeError(f"record numeric QC failed: {key}")
                if float(rec["mri_e1_max_abs_error"]) > 2e-6 or not rec["cache_hit_verified"]:
                    raise FinalizeError(f"record MRI/cache QC failed: {key}")
                if rec["cache_sha256_before"] != rec["cache_sha256_after"]:
                    raise FinalizeError(f"record cache changed: {key}")
                verify_prediction(Path(rec["prediction"]), rec["prediction_sha256"], int(rec["bytes"]))
                keyed[key] = rec
                records.append(rec)
            groups.append({
                "model": model, "outer_fold": fold, "subjects": expected // 2, "predictions": expected,
                "runtime_seconds": complete["runtime_seconds"],
                "peak_gpu_memory_bytes": complete["peak_gpu_memory_bytes"],
                "checkpoint_sha256": complete["checkpoint_sha256"],
                "condition_sha256": complete["condition_sha256"],
                "complete_path": str(complete_path), "complete_sha256": sha256(complete_path),
                "manifest_path": str(manifest_path), "manifest_sha256": sha256(manifest_path),
            })
    if len(records) != 3620 or len(keyed) != 3620:
        raise FinalizeError("global formal prediction count is not 3620 unique records")
    for fold in (1, 2):
        full = {(r["ptid"], r["tracer"]) for r in records if r["model"] == "Full" and int(r["outer_fold"]) == fold}
        ot = {(r["ptid"], r["tracer"]) for r in records if r["model"] == "OT" and int(r["outer_fold"]) == fold}
        if full != ot:
            raise FinalizeError(f"Full/OT pairing mismatch in fold {fold}")
    return records, keyed, groups


def build_assets(formal: dict[tuple[str, int, str, str], dict]) -> list[dict[str, object]]:
    receipt = json.loads((REPORT_DIR / "04b_manifest_receipt.json").read_text())
    assets: list[dict[str, object]] = []
    oof_verified: set[tuple[str, str]] = set()
    for task in TASKS:
        manifest_path = REPORT_DIR / f"04b_manifest_{task}.csv"
        expected = receipt["outputs"][manifest_path.name]
        if sha256(manifest_path) != expected["sha256"]:
            raise FinalizeError(f"4B manifest changed: {manifest_path.name}")
        rows = read_csv(manifest_path)
        if len(rows) != int(expected["rows"]):
            raise FinalizeError(f"4B manifest row mismatch: {manifest_path.name}")
        for row in rows:
            fold = int(row["outer_fold"])
            ptid = row["ptid"]
            outer_role = row["outer_role"]
            if outer_role == "outer_test" and int(row["generator_fold"]) != fold:
                raise FinalizeError(f"4B outer-test role mismatch: {task}/{fold}/{ptid}")
            if outer_role == "outer_train" and int(row["generator_fold"]) == fold:
                raise FinalizeError(f"4B outer-train role mismatch: {task}/{fold}/{ptid}")
            out: dict[str, object] = {
                "task": task, "outer_fold": fold, "ptid": ptid, "diagnosis": row["diagnosis"],
                "label": row["label"], "generator_fold": row["generator_fold"],
                "outer_role": outer_role, "inner_role": row["inner_role"],
                "e1_cache_path": row["e1_cache_path"], "e1_cache_sha256": row["e1_cache_sha256"],
                "mri_array_key": row["mri_array_key"], "real_fdg_array_key": row["real_fdg_array_key"],
                "real_av45_array_key": row["real_av45_array_key"],
            }
            for model_lower, model in (("full", "Full"), ("ot", "OT")):
                for tracer in ("fdg", "av45"):
                    if outer_role == "outer_train":
                        rec = formal.get((model, fold, ptid, tracer))
                        if rec is None:
                            raise FinalizeError(f"missing formal train-side asset: {model}/{fold}/{ptid}/{tracer}")
                        path, digest, source = rec["prediction"], rec["prediction_sha256"], "train_side_G_f"
                    else:
                        path = row[f"{model_lower}_{tracer}_existing_oof_path"]
                        digest = row[f"{model_lower}_{tracer}_existing_oof_sha256"]
                        source = "held_out_G_f_OOF"
                        key = (path, digest)
                        if key not in oof_verified:
                            verify_prediction(Path(path), digest)
                            oof_verified.add(key)
                    out[f"{model_lower}_{tracer}_path"] = path
                    out[f"{model_lower}_{tracer}_sha256"] = digest
                    out[f"{model_lower}_{tracer}_source"] = source
            assets.append(out)
    keys = [(r["task"], r["outer_fold"], r["ptid"]) for r in assets]
    if len(keys) != 3290 or len(set(keys)) != 3290:
        raise FinalizeError(f"classification asset index expected 3290 unique rows, found {len(keys)}/{len(set(keys))}")
    return assets


def main() -> int:
    for path in (OUT_FULL, OUT_ASSET, OUT_REPORT, OUT_RECEIPT):
        if path.exists():
            raise FinalizeError(f"refusing to overwrite existing final output: {path}")
    records, formal, groups = load_groups()
    assets = build_assets(formal)
    full_fields = list(records[0])
    atomic_csv(OUT_FULL, sorted(records, key=lambda r: (int(r["outer_fold"]), r["model"], r["ptid"], r["tracer"])), full_fields)
    asset_fields = list(assets[0])
    atomic_csv(OUT_ASSET, sorted(assets, key=lambda r: (r["task"], int(r["outer_fold"]), r["ptid"])), asset_fields)

    by_group = "\n".join(
        f"| {g['model']} | {g['outer_fold']} | {g['subjects']} | {g['predictions']} | "
        f"{float(g['runtime_seconds']):.1f} | {int(g['peak_gpu_memory_bytes']) / 2**30:.2f} |"
        for g in groups
    )
    report = f"""# Stage 4C-4 full train-side PET inference report

## 结论

**COMPLETE。** Full/OT × 两个 generator folds 四组均完成；3,620/3,620 个 train-side PET 通过身份、文件、SHA、数值、MRI/E1 和 cache 不变性核验。Full/OT 在同一 fold 的 PTID×tracer 集合完全一致。

| Model | Outer fold | Subjects | PET | Runtime (s) | Peak GPU GiB |
|---|---:|---:|---:|---:|---:|
{by_group}

## 完整性

- Fold 1：每模型 457 人、914 PET；Fold 2：每模型 448 人、896 PET。
- 总计 905 名唯一 outer-train 受试者、3,620 条唯一 train-side prediction。
- 每条记录均为 Epoch 165、对应 G_f、shape `160×192×160`、float32、finite、范围 `[0,1]`、非恒定。
- 全部记录 `mri_e1_max_abs_error <= 2e-6`，cache hit 已确认，运行前后 cache SHA 不变；四组 complete receipt 均声明 cache tree 不变。
- 未发现 failure marker、额外身份、缺失或重复预测。
- 实际分类输入只通过 `04c4_classification_asset_index.csv` 绑定；outer-train 来自本次正式 receipt，outer-test 来自 4B 冻结 G_f OOF，不使用 cross-OOF 训练输入。

本收口步骤仅汇总和核验已生成预测，没有重新推理、删除或覆盖任何 PET。
"""
    atomic_text(OUT_REPORT, report)
    outputs = {
        OUT_FULL.name: {"sha256": sha256(OUT_FULL), "bytes": OUT_FULL.stat().st_size, "rows": len(records)},
        OUT_ASSET.name: {"sha256": sha256(OUT_ASSET), "bytes": OUT_ASSET.stat().st_size, "rows": len(assets)},
        OUT_REPORT.name: {"sha256": sha256(OUT_REPORT), "bytes": OUT_REPORT.stat().st_size},
    }
    receipt = {
        "status": "COMPLETE", "stage": "4C-4", "epoch": 165,
        "expected_predictions": 3620, "actual_predictions": len(records),
        "unique_prediction_paths": len({r["prediction"] for r in records}),
        "classification_asset_rows": len(assets),
        "full_ot_paired": True, "cache_unchanged": True, "mri_e1_alignment_pass": True,
        "groups": groups, "outputs": outputs,
        "source_4b_manifest_receipt_sha256": sha256(REPORT_DIR / "04b_manifest_receipt.json"),
        "finalizer_sha256": sha256(Path(__file__)),
        "predictions_regenerated": False,
    }
    atomic_json(OUT_RECEIPT, receipt)
    print(json.dumps({"status": "COMPLETE", "predictions": len(records), "assets": len(assets),
                      "receipt": str(OUT_RECEIPT)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
