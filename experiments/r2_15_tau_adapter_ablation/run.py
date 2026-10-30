"""R2-15: isolated, CPU-only sensitivity analysis of the E1 tracer adapters.

This intentionally reproduces E1's adapter objective and optimizer, without
calling E1's ``adapt`` action (which writes into the frozen E1 asset tree).
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "experiments/e1_clinical_conditioning"))
from common import active_rows, check_frozen, load_config, sha  # noqa: E402

TRACERS = ("fdg", "av45")
RESULT_FIELDS = (
    "group", "fold", "tau", "cross_weight", "seed", "train_n_fdg", "train_n_av45",
    "heldout_n_fdg", "heldout_n_av45", "fdg_alignment", "av45_alignment",
    "heldout_fdg_alignment", "heldout_av45_alignment", "cross_tracer_similarity",
    "alignment_loss", "cross_term_loss", "total_loss", "actual_tau_deviation",
    "initial_parameters_sha256", "checkpoint_sha256", "embedding_sha256",
)
METRICS = (
    "fdg_alignment", "av45_alignment", "heldout_fdg_alignment",
    "heldout_av45_alignment", "cross_tracer_similarity", "alignment_loss",
    "cross_term_loss", "total_loss", "actual_tau_deviation",
)


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def parameter_hash(scale: torch.Tensor, bias: torch.Tensor) -> str:
    h = hashlib.sha256()
    for name, value in (("scale", scale), ("bias", bias)):
        h.update(name.encode())
        h.update(value.detach().contiguous().numpy().tobytes())
    return h.hexdigest()


def load_inputs() -> tuple[dict, dict, dict, list[dict], dict]:
    settings = json.loads((HERE / "config.json").read_text())
    source_path = ROOT / settings["source_config"]
    source = load_config(source_path)
    if (source["seed"], source["adapter_lr"], source["adapter_iterations"],
            source["tau"], source["adapter_cross_weight"]) != (42, 1e-3, 5000, 0.82, 100.0):
        raise RuntimeError("The frozen E1 adapter configuration differs from this experiment")
    check_frozen(source)
    all_rows = json.loads((Path(source["report"]) / "cohort.json").read_text())
    rows = active_rows(source, all_rows)
    if len(rows) != 1856 or len({r["ptid"] for r in rows}) != len(rows):
        raise RuntimeError("Unexpected active E1 cohort")
    asset = Path(source["assets"])
    raw_path = asset / "conditions/raw_tracers.npy"
    raw_sha = sha(raw_path)
    if raw_sha != settings["expected_raw_tracers_sha256"]:
        raise RuntimeError("Raw tracer embedding cache changed")
    raw = np.load(raw_path)
    if raw.shape != (2, 512) or raw.dtype != np.float32 or not np.isfinite(raw).all():
        raise RuntimeError("Unexpected raw tracer embedding array")
    text = F.normalize(torch.from_numpy(raw.copy()), dim=-1)
    features = {}
    input_hashes = {
        "source_config": sha(source_path), "experiment_config": sha(HERE / "config.json"),
        "cohort": sha(Path(source["report"]) / "cohort.json"),
        "qc_exclusions": sha(source["qc_exclusions"]), "raw_tracers": raw_sha,
        "e1_adapter_source": sha(ROOT / "experiments/e1_clinical_conditioning/run.py"),
        "ablation_source": sha(HERE / "run.py"),
    }
    for tracer in TRACERS:
        path = asset / "pet_features" / f"{tracer}.npy"
        index_path = path.with_name(f"{tracer}_index.json")
        index = json.loads(index_path.read_text())
        digest = sha(path)
        if digest != index["sha256"] or digest != settings["expected_feature_sha256"][tracer]:
            raise RuntimeError(f"{tracer} PET feature cache changed")
        values = np.load(path, mmap_mode="r")
        ids = index["ptids"]
        if values.shape != (len(ids), 512) or values.dtype != np.float32 or len(ids) != len(set(ids)):
            raise RuntimeError(f"Unexpected {tracer} PET feature index")
        positions = {ptid: i for i, ptid in enumerate(ids)}
        for row in rows:
            if row[f"has_{tracer}"]:
                ptid = row["ptid"]
                if ptid not in positions or index["cache_binding"].get(ptid) != row["cache_sha256"]:
                    raise RuntimeError(f"{tracer} PET feature/subject binding changed: {ptid}")
        features[tracer] = (values, ids, positions)
        input_hashes[f"{tracer}_features"] = digest
        input_hashes[f"{tracer}_index"] = sha(index_path)
    return settings, source, {"text": text, "features": features}, rows, input_hashes


def fold_data(fold: int, rows: list[dict], cache: dict) -> tuple[list[torch.Tensor], list[torch.Tensor], dict]:
    train_ids = {r["ptid"] for r in rows if r["test_fold"] != fold}
    heldout_ids = {r["ptid"] for r in rows if r["test_fold"] == fold}
    if len(train_ids) != 928 or len(heldout_ids) != 928 or train_ids & heldout_ids:
        raise RuntimeError("Unexpected E1 fold membership")
    train_features, heldout_features = [], []
    membership = {"train": {}, "heldout": {}}
    for tracer in TRACERS:
        values, ids, _ = cache["features"][tracer]
        selected_train = [i for i, ptid in enumerate(ids) if ptid in train_ids]
        selected_test = [i for i, ptid in enumerate(ids) if ptid in heldout_ids]
        for selected, side in ((selected_train, "train"), (selected_test, "heldout")):
            actual = [ids[i] for i in selected]
            expected = {r["ptid"] for r in rows if r["ptid"] in
                        (train_ids if side == "train" else heldout_ids) and r[f"has_{tracer}"]}
            if set(actual) != expected or len(actual) != len(expected):
                raise RuntimeError(f"{tracer} {side} feature membership differs from E1 cohort")
            membership[side][tracer] = actual
        train_features.append(F.normalize(torch.from_numpy(np.asarray(values[selected_train]).copy()), dim=-1))
        heldout_features.append(F.normalize(torch.from_numpy(np.asarray(values[selected_test]).copy()), dim=-1))
    return train_features, heldout_features, membership


def objective(scale: torch.Tensor, bias: torch.Tensor, text: torch.Tensor,
              train: list[torch.Tensor], group: dict) -> torch.Tensor:
    """Keep E1's training expression and operation order, including T000's omission."""
    vectors = F.normalize(scale[:, None] * text + bias, dim=-1)
    similarities = [F.cosine_similarity(vectors[i][None], train[i], dim=1).mean() for i in range(2)]
    cross = F.cosine_similarity(vectors[0][None], vectors[1][None])
    if group["cross_weight"] == 0:
        return -similarities[0] - similarities[1]
    return (-similarities[0] - similarities[1]
            + group["cross_weight"] * (cross - group["tau"]).square().sum())


def score(scale: torch.Tensor, bias: torch.Tensor, text: torch.Tensor,
          train: list[torch.Tensor], heldout: list[torch.Tensor], group: dict) -> dict:
    vectors = F.normalize(scale[:, None] * text + bias, dim=-1)
    train_align = [F.cosine_similarity(vectors[i][None], train[i], dim=1).mean() for i in range(2)]
    test_align = [F.cosine_similarity(vectors[i][None], heldout[i], dim=1).mean() for i in range(2)]
    cross = F.cosine_similarity(vectors[0][None], vectors[1][None]).sum()
    align_loss = -train_align[0] - train_align[1]
    if group["cross_weight"] == 0:
        cross_loss = torch.zeros_like(align_loss)
        total = align_loss
        deviation = None
    else:
        deviation = cross - group["tau"]
        cross_loss = group["cross_weight"] * deviation.square()
        total = align_loss + cross_loss
    metrics = {
        "fdg_alignment": float(train_align[0].detach()),
        "av45_alignment": float(train_align[1].detach()),
        "heldout_fdg_alignment": float(test_align[0].detach()),
        "heldout_av45_alignment": float(test_align[1].detach()),
        "cross_tracer_similarity": float(cross.detach()),
        "alignment_loss": float(align_loss.detach()),
        "cross_term_loss": float(cross_loss.detach()),
        "total_loss": float(total.detach()),
        "actual_tau_deviation": None if deviation is None else float(deviation.detach()),
    }
    return metrics


def fit_one(group: dict, fold: int, settings: dict, source: dict, cache: dict,
            train: list[torch.Tensor], heldout: list[torch.Tensor], membership: dict,
            input_hashes: dict) -> dict:
    folder = HERE / "runs" / f"{group['id']}_fold{fold}"
    if folder.exists():
        raise RuntimeError(f"Run output already exists; refusing to overwrite: {folder}")
    folder.mkdir(parents=True)
    seed = source["seed"] + fold
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    scale = torch.ones(2, requires_grad=True)
    bias = (torch.randn(2, 512) * .01).requires_grad_()
    initial_scale, initial_bias = scale.detach().clone(), bias.detach().clone()
    initial_hash = parameter_hash(scale, bias)
    optimizer = torch.optim.Adam([scale, bias], lr=source["adapter_lr"])
    log_path = folder / "optimization_log.csv"
    log_fields = ["step", *METRICS]
    with log_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=log_fields)
        writer.writeheader()
        with torch.no_grad():
            metrics = score(scale, bias, cache["text"], train, heldout, group)
        writer.writerow({"step": 0, **metrics})
        for step in range(1, source["adapter_iterations"] + 1):
            optimizer.zero_grad()
            loss = objective(scale, bias, cache["text"], train, group)
            loss.backward()
            optimizer.step()
            if step % settings["log_interval_steps"] == 0 or step == source["adapter_iterations"]:
                with torch.no_grad():
                    metrics = score(scale, bias, cache["text"], train, heldout, group)
                writer.writerow({"step": step, **metrics})
                handle.flush()
    with torch.no_grad():
        metrics = score(scale, bias, cache["text"], train, heldout, group)
        embedding = F.normalize(scale[:, None] * cache["text"] + bias, dim=-1).numpy()
    if not np.isfinite(embedding).all() or not all(np.isfinite(v) for v in metrics.values() if v is not None):
        raise RuntimeError(f"Nonfinite Adapter result: {group['id']} fold {fold}")
    checkpoint = {
        "group": group["id"], "fold": fold, "tau": group["tau"],
        "cross_weight": group["cross_weight"], "seed": seed,
        "initial_scale": initial_scale, "initial_bias": initial_bias,
        "scale": scale.detach().clone(), "bias": bias.detach().clone(),
        "initial_parameters_sha256": initial_hash, "input_hashes": input_hashes,
        "fit_ptids": membership["train"], "heldout_ptids": membership["heldout"],
        "optimizer": "Adam", "learning_rate": source["adapter_lr"],
        "iterations": source["adapter_iterations"], "dtype": "float32", "device": "cpu",
    }
    torch.save(checkpoint, folder / "adapter.pt")
    np.save(folder / "embedding.npy", embedding)
    row = {
        "group": group["id"], "fold": fold, "tau": group["tau"],
        "cross_weight": group["cross_weight"], "seed": seed,
        "train_n_fdg": len(membership["train"]["fdg"]),
        "train_n_av45": len(membership["train"]["av45"]),
        "heldout_n_fdg": len(membership["heldout"]["fdg"]),
        "heldout_n_av45": len(membership["heldout"]["av45"]),
        **metrics, "initial_parameters_sha256": initial_hash,
        "checkpoint_sha256": sha(folder / "adapter.pt"),
        "embedding_sha256": sha(folder / "embedding.npy"),
    }
    write_json(folder / "receipt.json", {"result": row, "input_hashes": input_hashes,
                                         "optimization_log_sha256": sha(log_path),
                                         "parameters_sha256": parameter_hash(scale, bias)})
    print(f"COMPLETE {group['id']} fold={fold} cross={metrics['cross_tracer_similarity']:.6f}", flush=True)
    return row


def summarize(settings: dict) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rows = []
    for group in settings["groups"]:
        for fold in settings["folds"]:
            folder = HERE / "runs" / f"{group['id']}_fold{fold}"
            receipt = json.loads((folder / "receipt.json").read_text())
            row = receipt["result"]
            if row["group"] != group["id"] or row["fold"] != fold:
                raise RuntimeError("Run receipt identity mismatch")
            if sha(folder / "adapter.pt") != row["checkpoint_sha256"] or sha(folder / "embedding.npy") != row["embedding_sha256"]:
                raise RuntimeError("Run artifact changed")
            rows.append(row)
    with (HERE / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=RESULT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    baseline = {r["fold"]: r for r in rows if r["group"] == "T082"}
    summary_rows = []
    for group in settings["groups"]:
        pair = [r for r in rows if r["group"] == group["id"]]
        item = {"group": group["id"], "tau": group["tau"], "cross_weight": group["cross_weight"]}
        for metric in METRICS:
            values = [r[metric] for r in pair]
            item[f"fold1_{metric}"] = values[0]
            item[f"fold2_{metric}"] = values[1]
            item[f"mean_{metric}"] = None if any(v is None for v in values) else float(np.mean(values))
            base = [baseline[f][metric] for f in (1, 2)]
            item[f"mean_delta_vs_T082_{metric}"] = (
                None if any(v is None for v in values + base)
                else float(np.mean([v - b for v, b in zip(values, base)]))
            )
        summary_rows.append(item)
    with (HERE / "summary.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary_rows[0]))
        writer.writeheader()
        writer.writerows(summary_rows)

    x = np.array([0, 1, 2, 3, 4.5])
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for metric, label, color in (("fdg_alignment", "FDG alignment", "#2878a5"),
                                 ("av45_alignment", "AV45 alignment", "#c45a37")):
        means = [r[f"mean_{metric}"] for r in summary_rows]
        axes[0].plot(x[:4], means[:4], marker="o", color=color, label=label)
        axes[0].scatter([x[4]], [means[4]], marker="D", s=55, color=color)
        for fold in (1, 2):
            vals = [r[f"fold{fold}_{metric}"] for r in summary_rows]
            axes[0].scatter(x[:4], vals[:4], color=color, alpha=.27, s=17)
            axes[0].scatter([x[4]], [vals[4]], color=color, alpha=.27, s=17)
    axes[0].set_ylabel("Mean cosine to subject PET features")
    axes[0].legend(frameon=False)
    cross = [r["mean_cross_tracer_similarity"] for r in summary_rows]
    axes[1].plot(x[:4], cross[:4], marker="o", color="#5a4b9f")
    axes[1].scatter([x[4]], [cross[4]], marker="D", s=55, color="#5a4b9f")
    for fold in (1, 2):
        axes[1].scatter(x, [r[f"fold{fold}_cross_tracer_similarity"] for r in summary_rows],
                        color="#5a4b9f", alpha=.27, s=17)
    axes[1].set_ylabel("FDG–AV45 adapted cosine")
    for axis in axes:
        axis.set_xticks(x, ["0.70", "0.82", "0.90", "0.98", "No cross"])
        axis.set_xlabel("Target τ (No cross has no τ)")
        axis.grid(axis="y", alpha=.2)
    fig.savefig(HERE / "tau_sensitivity.png", dpi=180)
    plt.close(fig)
    print("Wrote results.csv, summary.csv, tau_sensitivity.png", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("preflight", "fit", "summarize", "all"))
    parser.add_argument("--group", choices=("T070", "T082", "T090", "T098", "T000"))
    parser.add_argument("--fold", type=int, choices=(1, 2))
    args = parser.parse_args()
    if args.action == "summarize":
        summarize(json.loads((HERE / "config.json").read_text()))
        return
    settings, source, cache, rows, input_hashes = load_inputs()
    if args.action == "preflight":
        print(json.dumps({"status": "PASS", "active_subjects": len(rows),
                          "source_config": settings["source_config"],
                          "input_hashes": input_hashes}, indent=2))
        return
    if args.action == "fit" and (args.group is None or args.fold is None):
        parser.error("fit requires --group and --fold")
    selected_groups = [g for g in settings["groups"] if args.group is None or g["id"] == args.group]
    selected_folds = settings["folds"] if args.fold is None else [args.fold]
    (HERE / "runs").mkdir(exist_ok=True)
    for fold in selected_folds:
        train, heldout, membership = fold_data(fold, rows, cache)
        for group in selected_groups:
            fit_one(group, fold, settings, source, cache, train, heldout, membership, input_hashes)
    if args.action == "all":
        summarize(settings)


if __name__ == "__main__":
    main()
