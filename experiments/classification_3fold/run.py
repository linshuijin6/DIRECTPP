#!/usr/bin/env python3
"""Independent subject-level 3-fold classification, adapted from author cells 10/13.

Source: source_archive/vscode-3002/home/ssddata/liutuo/
mri2pet all data-_mri classification-densenet.ipynb (zero-based cells).
The original notebooks and input data are never edited. No batch launcher is provided.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import resource
import socket
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split

ROOT = Path(__file__).resolve().parents[2]
REPORT = ROOT / "reports/r2_11_classification_3fold"
SUBJECTS = ROOT / "reports/r2_11_classification_subjects.csv"
CLINICAL = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/filtered_subjects_with_description.csv"
TASKS = {
    "ad_cn": ({"CN": 0, "AD": 1}, 470),
    "mci_cn": ({"CN": 0, "EMCI": 1, "LMCI": 1}, 741),
    "emci_lmci": ({"EMCI": 0, "LMCI": 1}, 436),
}
CONDITIONS = {
    "mri": ["mri_path"],
    "mri_real_fdg": ["mri_path", "real_fdg_path"],
    "mri_syn_fdg": ["mri_path", "syn_fdg_path"],
    "mri_real_av45": ["mri_path", "real_av45_path"],
    "mri_syn_av45": ["mri_path", "syn_av45_path"],
    "mri_real_both": ["mri_path", "real_fdg_path", "real_av45_path"],
    "mri_syn_both": ["mri_path", "syn_fdg_path", "syn_av45_path"],
    "clinical": [],
    "mri_clinical": ["mri_path"],
}
FEATURES = ["Age", "Sex", "Weight", "MMSE Total Score", "GDSCALE Total Score",
            "Global CDR", "FAQ Total Score", "NPI-Q Total Score"]


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_subjects(path):
    df = pd.read_csv(path, keep_default_na=False)
    required = {"PTID", "diagnosis_original", "five_modalities_complete"}
    required.update(k for v in CONDITIONS.values() for k in v)
    if required - set(df.columns):
        raise ValueError(f"Missing subject columns: {required - set(df.columns)}")
    if df.PTID.eq("").any() or df.PTID.duplicated().any() or df.diagnosis_original.eq("").any():
        raise ValueError("Missing PTID/diagnosis or duplicate PTID")
    df = df[df.five_modalities_complete.astype(str).eq("1")].sort_values("PTID").copy()
    for k in required - {"PTID", "diagnosis_original", "five_modalities_complete"}:
        if df[k].eq("").any() or not all((ROOT / p).is_file() for p in df[k]):
            raise ValueError(f"Incomplete image paths in five-modality cohort: {k}")
    return df


def prepare(args):
    df = load_subjects(args.subjects)
    rows = []
    for task, (mapping, expected) in TASKS.items():
        data = df[df.diagnosis_original.isin(mapping)].copy()
        if len(data) != expected:
            raise ValueError(f"{task}: expected {expected}, found {len(data)}")
        y = data.diagnosis_original.map(mapping).to_numpy()
        skf = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
        for fold, (outer_train, test) in enumerate(skf.split(data.PTID, y), 1):
            train, val = train_test_split(outer_train, test_size=0.15,
                                        stratify=y[outer_train], random_state=42)
            for role, indices in [("train", train), ("validation", val), ("test", test)]:
                for i in sorted(indices):
                    r = data.iloc[i]
                    rows.append(dict(task=task, fold=fold, split=role, PTID=r.PTID,
                                     diagnosis_original=r.diagnosis_original, y_true=int(y[i])))
    result = pd.DataFrame(rows)
    args.splits.parent.mkdir(parents=True, exist_ok=True)
    with args.splits.open("x") as f:
        result.to_csv(f, index=False)
    counts = result.groupby(["task", "fold", "split", "y_true"]).size().unstack(fill_value=0)
    counts.columns = ["negative", "positive"]
    counts["total"] = counts.sum(axis=1)
    counts.to_csv(args.splits.with_name("split_counts.csv"))
    print(counts.to_string(), flush=True)


def metrics(y, probabilities):
    pred = (np.asarray(probabilities) >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    sen, spe = tp / (tp + fn), tn / (tn + fp)
    return dict(ACC=float((tp + tn) / (tp + tn + fp + fn)),
                AUC=float(roc_auc_score(y, probabilities)), SEN=float(sen), SPE=float(spe),
                balanced_ACC=float((sen + spe) / 2))


def fit(args):
    started = time.perf_counter()
    if args.epochs < 2 or args.epochs > 200 or args.epochs % 2:
        raise ValueError("Use an even epoch count between 2 and 200; pilot default is 4")
    # One GPU binding mechanism: physical index -> UUID -> logical cuda:0.
    info = subprocess.check_output([
        "nvidia-smi", "-i", str(args.gpu),
        "--query-gpu=uuid,name,memory.total,memory.free", "--format=csv,noheader,nounits"
    ], text=True).strip().split(", ")
    processes = subprocess.check_output([
        "nvidia-smi", "-i", str(args.gpu), "--query-compute-apps=pid", "--format=csv,noheader"
    ], text=True).strip()
    if processes:
        raise RuntimeError(f"GPU {args.gpu} has compute processes; no training started")
    os.environ["CUDA_VISIBLE_DEVICES"] = info[0]
    import torch
    import psutil
    from monai.data import CacheDataset, DataLoader
    from monai.networks.nets import DenseNet121
    from monai.transforms import Compose, LoadImaged, EnsureChannelFirstd, Identityd

    device = torch.device("cuda:0")
    seed = 42 + list(TASKS).index(args.task) * 100 + args.fold
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    torch.set_num_threads(args.cpu_threads)
    imports_seed_s = time.perf_counter() - started
    df = load_subjects(args.subjects).set_index("PTID")
    splits = pd.read_csv(args.splits)
    selected = splits[(splits.task == args.task) & (splits.fold == args.fold)].copy()
    mapping, expected = TASKS[args.task]
    task_ids = set(df.index[df.diagnosis_original.isin(mapping)])
    if (len(selected) != expected or selected.PTID.duplicated().any()
            or set(selected.PTID) != task_ids
            or set(selected.split) != {"train", "validation", "test"}):
        raise ValueError("Fold does not contain exactly one role per task subject")
    expected_labels = df.loc[selected.PTID, "diagnosis_original"].map(mapping).to_numpy()
    if not np.array_equal(selected.y_true.to_numpy(), expected_labels):
        raise ValueError("Split labels disagree with original diagnoses")
    args.output.mkdir(parents=True, exist_ok=False)
    keys = CONDITIONS[args.condition]
    clinical = args.condition in {"clinical", "mri_clinical"}
    feature_map, preprocessing = {}, None
    if clinical:
        c = pd.read_csv(args.clinical_csv).set_index("Subject ID").loc[selected.PTID, FEATURES]
        c["Sex"] = c.Sex.map({"M": 1, "F": 0})
        c = c.apply(pd.to_numeric, errors="coerce")
        # Only the derived clinical input changes; never write to the clinical source.
        c.loc[c.Weight.isin([0, 2.3]), "Weight"] = np.nan
        training = c.loc[selected.loc[selected.split == "train", "PTID"]]
        medians = training.median()
        filled_train = training.fillna(medians)
        means, std = filled_train.mean(), filled_train.std(ddof=0).replace(0, 1)
        feature_map = {ptid: row.to_numpy(dtype=np.float32)
                       for ptid, row in ((c.fillna(medians) - means) / std).iterrows()}
        preprocessing = dict(fields=FEATURES, medians=medians.to_dict(), means=means.to_dict(),
                             std=std.to_dict(), invalid_weight_values=[0, 2.3],
                             fit_split="train", sex_encoding={"M": 1, "F": 0})
        save_json(args.output / "clinical_preprocessing.json", preprocessing)
    data = {}
    for role in ["train", "validation", "test"]:
        records = []
        for r in selected[selected.split == role].itertuples():
            record = {"PTID": r.PTID, "label": int(r.y_true)}
            record.update({k: str(ROOT / df.at[r.PTID, k]) for k in keys})
            if clinical:
                record["clinical"] = feature_map[r.PTID]
            records.append(record)
        data[role] = records

    # Author cell 10: same active image transforms, cache, batch size and shuffle.
    transforms = Compose([LoadImaged(keys=keys),
                          EnsureChannelFirstd(keys=keys, channel_dim="no_channel"),
                          Identityd(keys=["label"])]) if keys else Compose([Identityd(keys=["label"])])
    load_started = time.perf_counter()
    loaders = {}
    for role in ["train", "validation"]:
        ds = CacheDataset(data=data[role], transform=transforms, num_workers=args.cache_workers,
                          progress=False)
        loaders[role] = DataLoader(ds, batch_size=args.batch_size, shuffle=role == "train",
                                   num_workers=0, generator=torch.Generator().manual_seed(seed))
    data_load_s = time.perf_counter() - load_started
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    model_started = time.perf_counter()
    if args.condition == "clinical":
        model = torch.nn.Linear(len(FEATURES), 2)
    else:
        model = DenseNet121(spatial_dims=3, in_channels=len(keys), out_channels=2)
        if args.condition == "mri_clinical":
            width = model.class_layers.out.in_features
            model.class_layers.out = torch.nn.Identity()
            model.clinical_head = torch.nn.Linear(width + len(FEATURES), 2)
    model = model.to(device)
    loss_function = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
    torch.cuda.synchronize()
    model_init_s = time.perf_counter() - model_started
    metadata = dict(task=args.task, condition=args.condition, fold=args.fold, seed=seed,
                    epochs=args.epochs, batch_size=args.batch_size, lr=1e-4, val_interval=2,
                    split_sizes={k: len(v) for k, v in data.items()},
                    parameters=sum(p.numel() for p in model.parameters()),
                    host=socket.gethostname(), physical_gpu=args.gpu, gpu_uuid=info[0],
                    gpu_name=info[1], gpu_total_MiB=int(info[2]), gpu_free_before_MiB=int(info[3]),
                    initialization_imports_seed_s=imports_seed_s, data_loading_s=data_load_s,
                    model_optimizer_initialization_s=model_init_s,
                    initialization_total_s=time.perf_counter() - started,
                    subjects=str(args.subjects), splits=str(args.splits),
                    clinical_csv=str(args.clinical_csv) if clinical else None,
                    cache_workers=args.cache_workers, cpu_threads=args.cpu_threads,
                    torch_version=torch.__version__,
                    pilot_only=args.epochs < 200, status="running")
    save_json(args.output / "summary.json", metadata)
    print(json.dumps(metadata, ensure_ascii=False), flush=True)

    def forward(batch):
        if not keys:
            return model(batch["clinical"].to(device))
        images = torch.cat([batch[k].to(device) for k in keys], dim=1)
        features = model(images)
        if args.condition == "mri_clinical":
            return model.clinical_head(torch.cat([features, batch["clinical"].to(device)], dim=1))
        return features

    def evaluate(loader):
        model.eval()
        y, prob, ptids = [], [], []
        with torch.no_grad():
            for batch in loader:
                outputs = forward(batch)
                prob.extend(torch.softmax(outputs, dim=1)[:, 1].cpu().tolist())
                y.extend(batch["label"].tolist())
                ptids.extend(batch["PTID"])
        return metrics(y, prob), pd.DataFrame(dict(
            PTID=ptids, task=args.task, condition=args.condition, fold=args.fold,
            y_true=y, p_positive=prob, y_pred=(np.asarray(prob) >= 0.5).astype(int)))

    best_metric, best_epoch, checkpoint_s = -1, -1, []
    history = []
    try:
        # Author cell 13: retain the train/eval, CE, backward and Adam update structure.
        for epoch in range(1, args.epochs + 1):
            torch.cuda.synchronize()
            epoch_started = time.perf_counter()
            model.train()
            epoch_loss, step = 0.0, 0
            for batch in loaders["train"]:
                step += 1
                labels = batch["label"].to(device, dtype=torch.long)
                optimizer.zero_grad()
                outputs = forward(batch)
                loss = loss_function(outputs, labels)
                loss.backward()
                optimizer.step()
                epoch_loss += loss.item()
            torch.cuda.synchronize()
            row = dict(epoch=epoch, loss=epoch_loss / step,
                       train_s=time.perf_counter() - epoch_started,
                       validation_s=None, checkpoint_s=0.0)
            if epoch % 2 == 0:
                val_started = time.perf_counter()
                val_metrics, _ = evaluate(loaders["validation"])
                torch.cuda.synchronize()
                row.update(validation_s=time.perf_counter() - val_started,
                           **{"val_" + k: v for k, v in val_metrics.items()})
                if val_metrics["ACC"] > best_metric:
                    best_metric, best_epoch = val_metrics["ACC"], epoch
                    checkpoint_started = time.perf_counter()
                    torch.save(model.state_dict(), args.output / "best_model.pth")
                    row["checkpoint_s"] = time.perf_counter() - checkpoint_started
                    checkpoint_s.append(row["checkpoint_s"])
            history.append(row)
            pd.DataFrame(history).to_csv(args.output / "history.csv", index=False)
            print(json.dumps(row), flush=True)
        # Only the selected checkpoint sees the final test fold, exactly once.
        reload_started = time.perf_counter()
        model.load_state_dict(torch.load(args.output / "best_model.pth", map_location=device,
                                         weights_only=True))
        torch.cuda.synchronize()
        reload_s = time.perf_counter() - reload_started
        test_load_started = time.perf_counter()
        test_ds = CacheDataset(data=data["test"], transform=transforms,
                               num_workers=args.cache_workers, progress=False)
        test_loader = DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=0)
        test_loading_s = time.perf_counter() - test_load_started
        test_started = time.perf_counter()
        test_metrics, predictions = evaluate(test_loader)
        torch.cuda.synchronize()
        test_s = time.perf_counter() - test_started
        predictions.to_csv(args.output / "test_predictions.csv", index=False)
        save_json(args.output / "test_metrics.json", test_metrics)
        metadata.update(status="complete", best_validation_ACC=best_metric, best_epoch=best_epoch,
                        test_metrics=test_metrics, test_evaluations=1,
                        first_epoch_s=history[0]["train_s"],
                        subsequent_epoch_mean_s=float(np.mean([r["train_s"] for r in history[1:]])),
                        validation_times_s=[r["validation_s"] for r in history if r["validation_s"] is not None],
                        checkpoint_save_times_s=checkpoint_s, checkpoint_reload_s=reload_s,
                        test_data_loading_s=test_loading_s, test_inference_s=test_s,
                        gpu_peak_allocated_MiB=torch.cuda.max_memory_allocated() / 2**20,
                        gpu_peak_reserved_MiB=torch.cuda.max_memory_reserved() / 2**20,
                        cpu_current_RSS_GiB=psutil.Process().memory_info().rss / 2**30,
                        cpu_peak_RSS_GiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 2**20,
                        total_wall_s=time.perf_counter() - started)
    except torch.cuda.OutOfMemoryError as exc:
        metadata.update(status="OOM", error=str(exc),
                        gpu_peak_allocated_MiB=torch.cuda.max_memory_allocated() / 2**20,
                        total_wall_s=time.perf_counter() - started)
        save_json(args.output / "summary.json", metadata)
        raise  # No automatic retry or batch-size search.
    save_json(args.output / "summary.json", metadata)
    print(json.dumps(metadata, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "fit"])
    parser.add_argument("--subjects", type=Path, default=SUBJECTS)
    parser.add_argument("--splits", type=Path, default=REPORT / "splits.csv")
    parser.add_argument("--task", choices=TASKS, default="mci_cn")
    parser.add_argument("--condition", choices=CONDITIONS, default="mri_syn_both")
    parser.add_argument("--fold", type=int, choices=[1, 2, 3], default=1)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch-size", type=int, choices=[1, 2, 5], default=5)
    parser.add_argument("--gpu", type=int, default=0, help="Physical GPU index; UUID binding is internal")
    parser.add_argument("--cache-workers", type=int, default=20)
    parser.add_argument("--cpu-threads", type=int, default=4)
    parser.add_argument("--clinical-csv", type=Path, default=CLINICAL)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare(args)
    else:
        if args.output is None:
            parser.error("fit requires a fresh --output directory")
        fit(args)


if __name__ == "__main__":
    main()
