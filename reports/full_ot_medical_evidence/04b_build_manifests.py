#!/usr/bin/env python3
"""Build Stage 4B classification manifests without loading images or models."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
E1 = ROOT / "reports/e1_stage01_20261017"
PREDICTIONS = OUT / "02_prediction_identity_checks.csv"
SPATIAL = OUT / "02_spatial_validation_results.json"
TRAIN_SIDE_ROOT = Path("/mnt/datas230/users/linshuijin/DIRECTPP_stage4b_train_side/20261028/epoch165")
SEED = 20261028
INNER_VALIDATION_FRACTION = 0.20

TASKS = {
    "ad_cn": {"diagnoses": {"AD", "CN"}, "positive": {"AD"}, "expected": 469},
    "mci_cn": {"diagnoses": {"EMCI", "LMCI", "CN"}, "positive": {"EMCI", "LMCI"}, "expected": 740},
    "lmci_emci": {"diagnoses": {"LMCI", "EMCI"}, "positive": {"LMCI"}, "expected": 436},
}

CHECKPOINTS = {
    ("Full", 1): Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/first_part_165.pth"),
    ("Full", 2): Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold2/first_part_165.pth"),
    ("OT", 1): Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022/formal/fold1/first_part_165.pth"),
    ("OT", 2): Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022/formal/fold2/first_part_165.pth"),
}
CONDITIONS = {
    "Full": Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/conditions.pt"),
    "OT": Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022/tracer_only_conditions.pt"),
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    os.replace(temp, path)


def main() -> None:
    spatial = json.loads(SPATIAL.read_text())
    expected_checkpoint = {}
    for model, receipts in (("Full", spatial["identity"]["full_receipts"]), ("OT", spatial["identity"]["ot_receipts"])):
        for fold in (1, 2):
            expected_checkpoint[(model, fold)] = receipts[str(fold)]["checkpoint_sha256"]
    checkpoint_identity = {}
    for key, path in CHECKPOINTS.items():
        actual = sha256(path)
        assert actual == expected_checkpoint[key], (key, actual, expected_checkpoint[key])
        receipt = path.with_suffix(".json")
        metadata = json.loads(receipt.read_text())
        assert metadata["fold"] == key[1] and metadata["epoch_one_based"] == 165
        assert metadata["checkpoint_sha256"] == actual
        checkpoint_identity[key] = {
            "path": str(path), "sha256": actual, "bytes": path.stat().st_size,
            "receipt": str(receipt), "receipt_sha256": sha256(receipt),
            "model_sha256": metadata["model_sha256"],
        }

    condition_identity = {
        model: {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}
        for model, path in CONDITIONS.items()
    }
    assert condition_identity["Full"]["sha256"] == "bbcd413100d8ece3e878acffc1969723d091f64c49c57c76b486bd474f84384a"
    assert condition_identity["OT"]["sha256"] == "e1dfd6399d59168c3a7105bd941c4e834b547b3170bdaed3133b300792dc71ec"

    cohort = pd.DataFrame(json.loads((E1 / "cohort.json").read_text())).rename(columns={"test_fold": "e1_test_fold"})
    cohort = cohort[(cohort.ptid != "016_S_4952") & cohort.has_fdg & cohort.has_av45].copy()
    assert len(cohort) == 1105 and cohort.ptid.nunique() == 1105
    hashes = pd.read_csv(E1 / "input_hashes_final.csv")
    hashes = hashes[hashes.kind.isin(["mri", "fdg", "av45"])].pivot(index="ptid", columns="kind", values=["path", "sha256", "bytes"])

    predictions = pd.read_csv(PREDICTIONS)
    predictions = predictions[(predictions.epoch == 165) & predictions["pass"]]
    prediction_map = {}
    for row in predictions.itertuples():
        prediction_map[(row.model, row.ptid, row.tracer)] = row
    generator_folds = predictions.groupby("ptid").fold.agg(lambda values: sorted(set(map(int, values))))
    assert all(len(values) == 1 for values in generator_folds)
    cohort["generator_fold"] = cohort.ptid.map({ptid: values[0] for ptid, values in generator_folds.items()})
    assert cohort.generator_fold.notna().all()
    cohort["generator_fold"] = cohort.generator_fold.astype(int)
    fold_identity_mismatches = int((cohort.e1_test_fold != cohort.generator_fold).sum())
    for row in cohort.itertuples():
        for model in ("Full", "OT"):
            for tracer in ("fdg", "av45"):
                pred = prediction_map[(model, row.ptid, tracer)]
                assert int(pred.fold) == int(row.generator_fold)
                assert pred.checkpoint_sha256 == expected_checkpoint[(model, int(row.generator_fold))]

    outputs = {}
    task_summary = {}
    for task, spec in TASKS.items():
        members = cohort[cohort.diagnosis.isin(spec["diagnoses"])].sort_values("ptid").copy()
        members["label"] = members.diagnosis.isin(spec["positive"]).astype(int)
        assert len(members) == spec["expected"] and members.label.nunique() == 2
        records = []
        for outer_fold in (1, 2):
            train = members[members.generator_fold != outer_fold]
            splitter = StratifiedShuffleSplit(n_splits=1, test_size=INNER_VALIDATION_FRACTION, random_state=SEED + outer_fold)
            inner_train_index, inner_val_index = next(splitter.split(train.ptid, train.label))
            inner_role = {train.iloc[i].ptid: "inner_train" for i in inner_train_index}
            inner_role.update({train.iloc[i].ptid: "inner_validation" for i in inner_val_index})
            for row in members.itertuples():
                role = "outer_test" if int(row.generator_fold) == outer_fold else "outer_train"
                rec = {
                    "task": task, "outer_fold": outer_fold, "ptid": row.ptid, "diagnosis": row.diagnosis,
                    "label": int(row.label), "generator_fold": int(row.generator_fold), "e1_test_fold_audit_only": int(row.e1_test_fold),
                    "outer_role": role,
                    "inner_role": "outer_test" if role == "outer_test" else inner_role[row.ptid],
                    "e1_cache_path": row.cache, "e1_cache_sha256": row.cache_sha256,
                    "mri_array_key": "mri", "real_fdg_array_key": "fdg", "real_av45_array_key": "av45",
                }
                for kind in ("mri", "fdg", "av45"):
                    rec[f"source_{kind}_path"] = hashes.loc[row.ptid, ("path", kind)]
                    rec[f"source_{kind}_sha256"] = hashes.loc[row.ptid, ("sha256", kind)]
                    rec[f"source_{kind}_bytes"] = int(hashes.loc[row.ptid, ("bytes", kind)])
                for model in ("Full", "OT"):
                    identity = checkpoint_identity[(model, outer_fold)]
                    lower = model.lower()
                    rec[f"{lower}_checkpoint_path"] = identity["path"]
                    rec[f"{lower}_checkpoint_sha256"] = identity["sha256"]
                    rec[f"{lower}_checkpoint_receipt"] = identity["receipt"]
                    rec[f"{lower}_condition_path"] = condition_identity[model]["path"]
                    rec[f"{lower}_condition_sha256"] = condition_identity[model]["sha256"]
                    for tracer in ("fdg", "av45"):
                        existing = prediction_map[(model, row.ptid, tracer)]
                        rec[f"{lower}_{tracer}_existing_oof_path"] = existing.prediction
                        rec[f"{lower}_{tracer}_existing_oof_sha256"] = existing.prediction_sha256_actual
                        planned = TRAIN_SIDE_ROOT / f"outer_fold{outer_fold}" / lower / f"generated_{tracer}_{row.ptid}.nii.gz"
                        rec[f"{lower}_{tracer}_selected_path"] = existing.prediction if role == "outer_test" else str(planned)
                        rec[f"{lower}_{tracer}_selected_sha256"] = existing.prediction_sha256_actual if role == "outer_test" else "PENDING_TRAIN_SIDE_INFERENCE"
                        rec[f"{lower}_{tracer}_asset_status"] = "VERIFIED_EXISTING_OOF" if role == "outer_test" else "PLANNED_MISSING"
                        rec[f"{lower}_{tracer}_existing_oof_usage"] = "ALLOWED_OUTER_TEST" if role == "outer_test" else "FORBIDDEN_AS_OUTER_TRAIN_INPUT"
                records.append(rec)
        table = pd.DataFrame(records).sort_values(["outer_fold", "outer_role", "inner_role", "ptid"])
        assert len(table) == 2 * len(members)
        assert not table.duplicated(["outer_fold", "ptid"]).any()
        assert (table[table.outer_role == "outer_test"].generator_fold == table[table.outer_role == "outer_test"].outer_fold).all()
        assert (table[table.outer_role == "outer_train"].generator_fold != table[table.outer_role == "outer_train"].outer_fold).all()
        path = OUT / f"04b_manifest_{task}.csv"
        table.to_csv(path, index=False)
        outputs[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size, "rows": len(table)}
        task_summary[task] = {
            "subjects": len(members), "labels": {str(k): int(v) for k, v in members.label.value_counts().sort_index().items()},
            "diagnoses": {str(k): int(v) for k, v in members.diagnosis.value_counts().sort_index().items()},
            "outer": {
                str(fold): {
                    "test": int((members.generator_fold == fold).sum()),
                    "train": int((members.generator_fold != fold).sum()),
                    "inner_validation": int(((table.outer_fold == fold) & (table.inner_role == "inner_validation")).sum()),
                } for fold in (1, 2)
            },
        }

    config = {
        "stage": "4B_preflight_only", "status": "PREPARED_NOT_INFERRED_NOT_TRAINED", "epoch": 165,
        "generator_outer_folds": [1, 2], "outer_test_rule": "generator_fold == outer_fold",
        "outer_train_rule": "generator_fold != outer_fold",
        "train_side_rule": "use the same G_f checkpoint as outer test; never use outer-train subjects' cross-OOF prediction",
        "tasks": {name: {"diagnoses": sorted(spec["diagnoses"]), "positive": sorted(spec["positive"]),
                         "expected": spec["expected"]} for name, spec in TASKS.items()},
        "conditions": ["MRI", "MRI+Real", "MRI+Full", "MRI+OT"],
        "inner_validation": {"method": "StratifiedShuffleSplit", "fraction": INNER_VALIDATION_FRACTION, "base_seed": SEED,
                             "fold_seed_rule": "base_seed + outer_fold"},
        "generator_checkpoints": {f"{model}_fold{fold}": value for (model, fold), value in checkpoint_identity.items()},
        "conditions_identity": condition_identity, "planned_train_side_root": str(TRAIN_SIDE_ROOT),
        "classification": {"backbone": "MONAI DenseNet121", "spatial_dims": 3, "in_channels": 1,
                           "dual_input_channels": 3, "out_channels": 2, "fits": 24,
                           "loss": "CrossEntropyLoss", "optimizer": "Adam", "learning_rate": 1e-4,
                           "max_epochs": 200, "validation_interval_epochs": 2,
                           "batch_size": "UNVERIFIED_RESOURCE_DEPENDENT; identical across Full/OT",
                           "checkpoint_selection": "maximum inner-validation AUC; deterministic earliest-epoch tie break",
                           "threshold_selection": "maximum inner-validation Youden J at selected checkpoint; tie closest to 0.5 then lower threshold",
                           "training_seed": SEED,
                           "primary_comparison": "paired pooled outer-OOF AUC, MRI+Full minus MRI+OT",
                           "secondary_metrics": ["ACC", "SEN", "SPE", "balanced_ACC"], "confidence_interval": "subject bootstrap 95%"},
    }
    config_path = OUT / "04b_execution_config_draft.json"
    write_json(config_path, config)
    outputs[config_path.name] = {"sha256": sha256(config_path), "bytes": config_path.stat().st_size}
    receipt = {
        "status": "PASS_STATIC_PREFLIGHT", "tasks": task_summary, "outputs": outputs,
        "source_hashes": {str(path.relative_to(ROOT)): sha256(path) for path in [
            OUT / "04a_classification_protocol_recon.md", OUT / "02_spatial_validation_results.json",
            PREDICTIONS, E1 / "cohort.json", E1 / "input_hashes_final.csv",
            ROOT / "experiments/original_author_reproduction/run.py", ROOT / "experiments/tracer_only_control/run.py",
        ]},
        "checkpoint_identity_verified": True, "condition_identity_verified": True,
        "generator_fold_source": "Stage 2 Full/OT Epoch 165 prediction identity; not E1 cohort.test_fold",
        "dual_cohort_e1_vs_generator_fold_mismatches": fold_identity_mismatches,
        "images_or_models_loaded": False, "inference_or_training_run": False,
    }
    receipt_path = OUT / "04b_manifest_receipt.json"
    write_json(receipt_path, receipt)
    print(json.dumps({"status": receipt["status"], "tasks": task_summary, "outputs": outputs}, ensure_ascii=False))


if __name__ == "__main__":
    main()
