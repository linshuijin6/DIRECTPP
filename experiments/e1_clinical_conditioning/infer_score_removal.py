"""R2-5: evaluate a frozen Full E1 model with its No-Scores patient token.

Pilot and full OOF are separate, explicit commands. This never trains or edits
the frozen conditions, adapters, checkpoints, or existing Full predictions.
"""
import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

import nibabel as nib
import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[2]
FULL_REPORT = ROOT / "reports/e1_full165_inference_20261020"
REPORT = ROOT / "reports/r2_5_inference_score_removal_20261030"
sys.path.insert(0, str(FULL_REPORT))
from infer_full import image_metrics, load_cpu
from common import TRACERS, active_rows, check_frozen, load_config, new_model, seed_all, sha, write_json
from evaluate import apply_validity, regional, roi_context
from run import checkpoint_identity, contexts, load_adapter, prediction

PILOT = {1: ("067_S_2301", "052_S_4959"),
         2: ("018_S_4399", "137_S_4631")}
REPLAY_RTOL = 1e-3
REPLAY_ATOL = 1e-5


def array_sha(a):
    return hashlib.sha256(np.ascontiguousarray(a).tobytes()).hexdigest()


def preflight(cfg, fold, stage):
    check_frozen(cfg)
    if not cfg["formal_training_authorized"] or not (cfg["evaluation_laterality_gate_pass"] and cfg["evaluation_mri_mask_gate_pass"]):
        raise RuntimeError("Formal inference or anatomical evaluation gate is closed")
    rows = active_rows(cfg, json.loads((Path(cfg["report"]) / "cohort.json").read_text()))
    held = {r["ptid"]: r for r in rows if r["test_fold"] == fold}
    train_ids = {r["ptid"] for r in rows if r["test_fold"] != fold}
    if len(held) != 928 or len(train_ids) != 928 or train_ids.intersection(held):
        raise RuntimeError("Frozen two-fold OOF split mismatch")
    selected = [held[s] for s in PILOT[fold]] if stage == "pilot" else list(held.values())
    if stage == "pilot" and not all(r["has_fdg"] and r["has_av45"] for r in selected):
        raise RuntimeError("Pilot tracer availability changed")

    source = FULL_REPORT / f"fold{fold}"
    snapshot = json.loads((source / "snapshot.json").read_text())
    complete = json.loads((source / "complete.json").read_text())
    checkpoint = source / "checkpoint.pt"
    cksha = sha(checkpoint)
    identity = checkpoint_identity(cfg, fold, "Full")
    if (snapshot["checkpoint_sha256"] != cksha or complete["checkpoint_sha256"] != cksha
            or snapshot["identity"] != identity or set(snapshot["test_ptids"]) != set(held)
            or set(snapshot["training_ptids"]) != train_ids or complete["status"] != "COMPLETE"):
        raise RuntimeError("Full OOF checkpoint or split receipt mismatch")
    ck = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if (ck["stage"] != "formal" or ck["checkpoint_format"] != 2
            or ck["epoch"] != cfg["epochs"] - 1 != 164
            or ck["optimizer_updates"] != 165 * len(train_ids)
            or any(ck.get(k) != v for k, v in identity.items())):
        raise RuntimeError("Full checkpoint identity mismatch")

    full_index = json.loads((source / "prediction_index.json").read_text())
    full = {(e["ptid"], e["tracer"]): e for e in full_index}
    expected = {(r["ptid"], t) for r in held.values() for t in TRACERS if r["has_" + t]}
    if len(full) != len(full_index) or set(full) != expected:
        raise RuntimeError("Full prediction index does not cover the held-out fold")
    with (source / "metrics.csv").open(newline="") as f:
        metrics_rows = list(csv.DictReader(f))
    metrics = {(e["ptid"], e["tracer"]): e for e in metrics_rows}
    if len(metrics) != len(metrics_rows) or set(metrics) != expected:
        raise RuntimeError("Full metric index does not cover the held-out fold")
    for r in selected:
        for t in TRACERS:
            if not r["has_" + t]:
                continue
            entry = full[r["ptid"], t]
            prior = metrics[r["ptid"], t]
            if (entry["fold"] != fold or entry["condition"] != "Full"
                    or entry["checkpoint_sha256"] != cksha
                    or entry["cache_sha256"] != r["cache_sha256"]
                    or int(prior["fold"]) != fold or prior["checkpoint_sha256"] != cksha
                    or prior["cache_sha256"] != r["cache_sha256"]
                    or sha(entry["path"]) != entry["sha256"]):
                raise RuntimeError(f"Full reference mismatch: {r['ptid']} {t}")
    return rows, selected, ck, cksha, full, metrics, checkpoint, identity, snapshot


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("pilot", "full"), required=True)
    parser.add_argument("--fold", type=int, choices=(1, 2), required=True)
    parser.add_argument("--config", type=Path, default=ROOT / "reports/e1_stage01_20261017/config.json")
    args = parser.parse_args()
    cfg = load_config(args.config)
    rows, selected, ck, cksha, full, prior, checkpoint, identity, snapshot = preflight(cfg, args.fold, args.stage)
    full_ctx = contexts(cfg, "Full")
    no_ctx = contexts(cfg, "No-Scores")
    condition_root = Path(cfg["assets"]) / "conditions"
    condition_shas = {c: sha(condition_root / f"{c}.npy") for c in ("Full", "No-Scores")}
    adapter = load_adapter(cfg, rows, args.fold)
    labels = np.genfromtxt(Path(cfg["report"]) / "roi_labels.csv", delimiter=",", names=True,
                           dtype=None, encoding="utf-8")["region"].astype(int)
    invalid, _ = roi_context(cfg, labels)
    report_dir = REPORT / args.stage / f"fold{args.fold}"
    prediction_dir = Path(cfg["assets"]) / "oof/R2_5_FullWeights_NoScores_20261030" / args.stage / f"fold{args.fold}"
    if report_dir.exists() or prediction_dir.exists():
        raise FileExistsError("Use a fresh run: R2-5 output directory already exists")
    torch.set_num_threads(4)
    seed_all(cfg["seed"] + args.fold)
    torch.backends.cudnn.allow_tf32 = False
    model = new_model().cuda().eval()
    model.load_state_dict(ck["model"], strict=True)
    report_dir.mkdir(parents=True, exist_ok=False)
    prediction_dir.mkdir(parents=True, exist_ok=False)
    write_json(report_dir / "run_identity.json", dict(
        stage=args.stage, fold=args.fold, checkpoint_training_condition="Full",
        inference_conditions=["Full", "No-Scores"] if args.stage == "pilot" else ["No-Scores"],
        checkpoint=str(checkpoint), checkpoint_sha256=cksha, checkpoint_identity=identity,
        epoch_zero_based=ck["epoch"], completed_epochs=ck["epoch"] + 1,
        condition_sha256=condition_shas, adapter_sha256=identity["adapter_sha256"],
        source_snapshot_sha256=sha(FULL_REPORT / f"fold{args.fold}/snapshot.json"),
        source_prediction_index_sha256=sha(FULL_REPORT / f"fold{args.fold}/prediction_index.json"),
        source_metrics_sha256=sha(FULL_REPORT / f"fold{args.fold}/metrics.csv"),
        source_training_ptids_sha256=array_sha(np.array(sorted(snapshot["training_ptids"]), dtype="S")),
        source_test_ptids_sha256=array_sha(np.array(sorted(snapshot["test_ptids"]), dtype="S")),
        selected_ptids=[r["ptid"] for r in selected], output=str(prediction_dir),
        precision="native E1 FP16 autocast, cudnn TF32 disabled", script_sha256=sha(__file__),
        interpretation="fixed Full weights with alternative inference-time clinical token"))

    results = []
    index = []
    for row in selected:
        arrays = load_cpu(row)
        data = {"mri": torch.from_numpy(arrays["mri"])[None, None].cuda()}
        ptid = row["ptid"]
        if not row["full"].startswith(row["no_scores"]) or row["full"] == row["no_scores"]:
            raise RuntimeError(f"Unexpected frozen clinical prompt: {ptid}")
        if torch.equal(full_ctx[ptid], no_ctx[ptid]):
            raise RuntimeError(f"Patient embeddings do not differ: {ptid}")
        for i, tracer in enumerate(TRACERS):
            if not row["has_" + tracer]:
                continue
            key = (ptid, tracer)
            reference = nib.load(full[key]["path"]).get_fdata(dtype=np.float32)
            if reference.shape != arrays[tracer].shape or not np.allclose(
                    nib.load(full[key]["path"]).affine, arrays["affine"], atol=1e-5):
                raise RuntimeError(f"Full reference geometry mismatch: {key}")
            replay = None
            if args.stage == "pilot":
                replay = prediction(model, data, full_ctx[ptid].cuda(), adapter[i])
                replay_diff = np.abs(replay - reference)
                if not np.allclose(replay, reference, rtol=REPLAY_RTOL, atol=REPLAY_ATOL):
                    raise RuntimeError(f"Full replay mismatch: {key}, max_abs={replay_diff.max()}")
            pred = prediction(model, data, no_ctx[ptid].cuda(), adapter[i])
            real = arrays[tracer]
            values = image_metrics(real, pred, arrays["mask"] > 0, validate=args.stage == "pilot")
            real_roi = apply_validity(regional(real, arrays["mask"], labels), labels, invalid.get(ptid, set()))
            pred_roi = apply_validity(regional(pred, arrays["mask"], labels), labels, invalid.get(ptid, set()))
            values["roi_mae"] = float(np.nanmean(np.abs(real_roi - pred_roi)))
            values["full_vs_no_scores_voxel_mae"] = float(np.mean(np.abs(reference.astype(np.float64) - pred)))
            values["full_vs_no_scores_brain_mae"] = float(np.mean(np.abs(reference[arrays["mask"] > 0] - pred[arrays["mask"] > 0])))
            target = prediction_dir / f"{ptid}_{tracer}.nii"
            nib.save(nib.Nifti1Image(pred, arrays["affine"]), target)
            if not np.array_equal(nib.load(target).get_fdata(dtype=np.float32), pred):
                raise RuntimeError(f"Saved prediction differs from memory: {key}")
            entry = dict(ptid=ptid, fold=args.fold, tracer=tracer, condition="No-Scores",
                         checkpoint_training_condition="Full", checkpoint_sha256=cksha,
                         cache_sha256=row["cache_sha256"], mri_sha256=array_sha(arrays["mri"]),
                         tracer_embedding_sha256=array_sha(adapter[i].cpu().numpy()),
                         full_patient_sha256=array_sha(full_ctx[ptid].numpy()),
                         no_scores_patient_sha256=array_sha(no_ctx[ptid].numpy()),
                         full_reference_sha256=full[key]["sha256"], prediction_sha256=sha(target),
                         full_replay_max_abs=float(replay_diff.max()) if replay is not None else None,
                         full_replay_mean_abs=float(replay_diff.mean()) if replay is not None else None,
                         **values)
            for metric in ("roi_mae", "brain_mae", "psnr", "ssim7", "ssim11"):
                entry[f"full_{metric}"] = float(prior[key][metric])
                entry[f"delta_{metric}"] = float(values[metric] - float(prior[key][metric]))
            results.append(entry)
            index.append(dict(ptid=ptid, fold=args.fold, tracer=tracer, condition="No-Scores",
                              checkpoint_training_condition="Full", path=str(target), sha256=sha(target),
                              checkpoint_sha256=cksha, cache_sha256=row["cache_sha256"]))
            print(json.dumps(dict(ptid=ptid, fold=args.fold, tracer=tracer,
                                  delta_roi_mae=entry["delta_roi_mae"],
                                  delta_brain_mae=entry["delta_brain_mae"],
                                  full_vs_no_scores_voxel_mae=values["full_vs_no_scores_voxel_mae"],
                                  full_replay_max_abs=entry["full_replay_max_abs"])), flush=True)
    with (report_dir / "per_subject_metrics.csv").open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    write_json(report_dir / "prediction_index.json", index)
    write_json(report_dir / "complete.json", dict(status="COMPLETE", stage=args.stage, fold=args.fold,
        subjects=len(selected), volumes=len(results), checkpoint_sha256=cksha,
        output=str(prediction_dir), replay_tolerance=dict(rtol=REPLAY_RTOL, atol=REPLAY_ATOL)
        if args.stage == "pilot" else None))


if __name__ == "__main__":
    main()
