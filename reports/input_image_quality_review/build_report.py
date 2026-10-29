#!/usr/bin/env python3
"""Read-only QC collection and static report builder for Full/OT input images."""

from __future__ import annotations

import argparse
import csv
import html
import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
import torch
from monai.data.utils import pickle_hashing


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "reports/input_image_quality_review"
ASSETS = OUT / "assets"
COHORT = ROOT / "reports/original_author_reproduction_20261020/cohort.json"
SPLIT = ROOT / "reports/original_author_reproduction_20261020/split_manifest.csv"
HASHES = ROOT / "reports/original_author_reproduction_20261020/input_hashes.csv"
CACHE = ROOT / "results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup"
E1_EXCLUSIONS = ROOT / "reports/e1_stage01_20261017/qc_exclusions.json"
E1_GEOMETRY = ROOT / "reports/e1_stage01_20261017/geometry_qc_final.json"
RAW_METRICS = OUT / "raw_qc_metrics.csv"
CACHE_METRICS = OUT / "cache_qc_metrics.csv"
FOCUS = {"016_S_4952", "123_S_4096", "128_S_4842"}
MODS = ("mri", "fdg", "av45")


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return math.nan


def volume_metrics(array: np.ndarray, step: int) -> tuple[dict, np.ndarray]:
    a = np.asarray(array, dtype=np.float32)
    s = a[::step, ::step, ::step]
    finite = np.isfinite(s)
    vals = s[finite]
    if vals.size == 0:
        return {"finite_fraction": 0.0}, np.zeros_like(s, dtype=bool)
    p0, p1, p50, p99, p100 = np.percentile(vals, [0, 1, 50, 99, 100])
    threshold = p1 + 0.05 * (p99 - p1)
    mask = finite & (s > threshold)
    coords = np.argwhere(mask)
    result = {
        "finite_fraction": float(finite.mean()),
        "min": float(p0),
        "p1": float(p1),
        "p50": float(p50),
        "p99": float(p99),
        "max": float(p100),
        "zero_fraction": float(np.mean(vals == 0)),
        "negative_fraction": float(np.mean(vals < 0)),
        "foreground_fraction": float(mask.mean()),
        "mask_threshold": float(threshold),
    }
    if coords.size:
        lo, hi = coords.min(0), coords.max(0)
        center = coords.mean(0)
        shape = np.asarray(mask.shape, dtype=float)
        margins = np.r_[lo, np.asarray(mask.shape) - 1 - hi] / np.r_[shape, shape]
        result.update(
            bbox_x0=int(lo[0] * step), bbox_y0=int(lo[1] * step), bbox_z0=int(lo[2] * step),
            bbox_x1=int(hi[0] * step), bbox_y1=int(hi[1] * step), bbox_z1=int(hi[2] * step),
            com_x=float(center[0] * step), com_y=float(center[1] * step), com_z=float(center[2] * step),
            min_margin_fraction=float(margins.min()),
            border_faces=int(sum((lo == 0).tolist()) + sum((hi == np.asarray(mask.shape) - 1).tolist())),
        )
    else:
        result.update(
            bbox_x0=-1, bbox_y0=-1, bbox_z0=-1, bbox_x1=-1, bbox_y1=-1, bbox_z1=-1,
            com_x=math.nan, com_y=math.nan, com_z=math.nan,
            min_margin_fraction=math.nan, border_faces=6,
        )
    return result, mask


def pair_metrics(a: np.ndarray, b: np.ndarray, shape: tuple[int, ...], step: int) -> dict:
    inter = int(np.count_nonzero(a & b))
    denom = int(np.count_nonzero(a) + np.count_nonzero(b))
    dice = 2 * inter / denom if denom else math.nan
    if not np.any(a) or not np.any(b):
        return {"dice": dice, "com_distance_norm": math.nan}
    ca, cb = np.argwhere(a).mean(0), np.argwhere(b).mean(0)
    com_distance = float(np.linalg.norm((ca - cb) * step) / np.linalg.norm(shape))
    return {"dice": dice, "com_distance_norm": com_distance}


def prefixed(d: dict, prefix: str) -> dict:
    return {f"{prefix}_{k}": v for k, v in d.items()}


def collect(shard_index: int = 0, shard_count: int = 1) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    all_cohort = json.loads(COHORT.read_text())
    cohort = [row for i, row in enumerate(all_cohort) if i % shard_count == shard_index]
    raw_rows, cache_rows = [], []
    total = len(cohort)
    for i, row in enumerate(cohort, 1):
        ptid = row["name"]
        raw_out = {"ptid": ptid, "fold": row["test_fold"]}
        raw_masks = {}
        raw_shape = None
        for mod in MODS:
            path = Path(row[mod])
            image = nib.load(path)
            data = np.asanyarray(image.dataobj, dtype=np.float32)
            metrics, mask = volume_metrics(data, step=3)
            raw_masks[mod] = mask
            raw_shape = image.shape
            axcodes = "".join(nib.aff2axcodes(image.affine))
            zooms = image.header.get_zooms()[:3]
            meta = {
                "path": str(path), "shape": "x".join(map(str, image.shape)), "axcodes": axcodes,
                "voxel_sizes": "x".join(f"{z:.4g}" for z in zooms),
                "affine_det": float(np.linalg.det(image.affine[:3, :3])),
                "qform_code": int(image.header["qform_code"]), "sform_code": int(image.header["sform_code"]),
                "is_zero_placeholder": path.name.endswith("_zero.nii.gz") or not np.any(data),
            }
            raw_out.update(prefixed({**meta, **metrics}, f"raw_{mod}"))
        for mod in ("fdg", "av45"):
            raw_out.update(prefixed(pair_metrics(raw_masks["mri"], raw_masks[mod], raw_shape, 3), f"raw_mri_{mod}"))
        raw_out["raw_within_subject_same_shape"] = len({raw_out[f"raw_{m}_shape"] for m in MODS}) == 1
        raw_out["raw_within_subject_same_axcodes"] = len({raw_out[f"raw_{m}_axcodes"] for m in MODS}) == 1
        raw_rows.append(raw_out)

        cache_file = CACHE / (pickle_hashing(row).decode() + ".pt")
        item = torch.load(cache_file, map_location="cpu", weights_only=False)
        cache_out = {
            "ptid": ptid, "fold": row["test_fold"], "cache_path": str(cache_file),
            "cache_bytes": cache_file.stat().st_size, "cache_internal_ptid": item.get("name"),
            "cache_internal_fold": int(item.get("test_fold")),
        }
        cache_masks = {}
        cache_shape = None
        for mod in MODS:
            data = np.asarray(item[mod][0], dtype=np.float32)
            metrics, mask = volume_metrics(data, step=2)
            cache_masks[mod] = mask
            cache_shape = data.shape
            cache_out.update(prefixed({"shape": "x".join(map(str, data.shape)), **metrics}, f"cache_{mod}"))
        for mod in ("fdg", "av45"):
            cache_out.update(prefixed(pair_metrics(cache_masks["mri"], cache_masks[mod], cache_shape, 2), f"cache_mri_{mod}"))
        cache_out["foreground_start_coord"] = "x".join(map(str, np.asarray(item.get("foreground_start_coord", [])).reshape(-1).tolist()))
        cache_out["foreground_end_coord"] = "x".join(map(str, np.asarray(item.get("foreground_end_coord", [])).reshape(-1).tolist()))
        cache_rows.append(cache_out)
        if i % 25 == 0 or i == total:
            print(f"QC {i}/{total}", flush=True)
    raw_target = RAW_METRICS if shard_count == 1 else OUT / f"raw_qc_metrics.part{shard_index:02d}.csv"
    cache_target = CACHE_METRICS if shard_count == 1 else OUT / f"cache_qc_metrics.part{shard_index:02d}.csv"
    pd.DataFrame(raw_rows).to_csv(raw_target, index=False)
    pd.DataFrame(cache_rows).to_csv(cache_target, index=False)
    print(f"wrote {raw_target} and {cache_target}", flush=True)


def merge_parts() -> None:
    for target, pattern in ((RAW_METRICS, "raw_qc_metrics.part*.csv"), (CACHE_METRICS, "cache_qc_metrics.part*.csv")):
        parts = sorted(OUT.glob(pattern))
        if not parts:
            raise RuntimeError(f"No parts found for {pattern}")
        frame = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True).sort_values("ptid")
        if len(frame) != 1857 or frame.ptid.nunique() != 1857:
            raise RuntimeError(f"Incomplete merged QC for {target.name}: rows={len(frame)}, unique={frame.ptid.nunique()}")
        frame.to_csv(target, index=False)
        print(f"merged {len(parts)} parts -> {target}", flush=True)


def robust_z(series: pd.Series) -> pd.Series:
    x = pd.to_numeric(series, errors="coerce")
    med = x.median()
    mad = (x - med).abs().median()
    if not np.isfinite(mad) or mad == 0:
        return pd.Series(np.zeros(len(x)), index=x.index)
    return 0.67448975 * (x - med) / mad


def load_joined() -> pd.DataFrame:
    raw = pd.read_csv(RAW_METRICS)
    cache = pd.read_csv(CACHE_METRICS)
    cohort = pd.DataFrame(json.loads(COHORT.read_text())).rename(columns={"name": "ptid"})
    df = cohort[["ptid", "test_fold", "mri", "fdg", "av45"]].merge(raw, on="ptid", how="left").merge(cache, on="ptid", how="left")
    df["fold"] = df["test_fold"]
    df["full_ot_generator_role"] = np.where(df["fold"] == 1, "fold 1 held-out test / fold 2 train", "fold 2 held-out test / fold 1 train")
    exclusions = json.loads(E1_EXCLUSIONS.read_text())
    excluded = {r["ptid"] for r in exclusions["excluded"]}
    df["full_membership"] = "included"
    df["ot_membership"] = "included"
    df["e1_status"] = np.where(df.ptid.isin(excluded), "excluded_by_frozen_E1_QC", "included")
    df["has_fdg"] = ~df["raw_fdg_is_zero_placeholder"].astype(bool)
    df["has_av45"] = ~df["raw_av45_is_zero_placeholder"].astype(bool)

    metrics = [
        "raw_mri_zero_fraction", "raw_mri_foreground_fraction", "raw_mri_border_faces",
        "raw_fdg_negative_fraction", "raw_av45_negative_fraction",
        "raw_mri_fdg_com_distance_norm", "raw_mri_av45_com_distance_norm",
        "raw_mri_fdg_dice", "raw_mri_av45_dice",
        "cache_mri_zero_fraction", "cache_mri_foreground_fraction", "cache_mri_border_faces",
        "cache_fdg_zero_fraction", "cache_av45_zero_fraction",
        "cache_mri_fdg_com_distance_norm", "cache_mri_av45_com_distance_norm",
        "cache_mri_fdg_dice", "cache_mri_av45_dice",
    ]
    # Zero-valued PET files are the formal missing-modality representation.
    # Keep them in cohort counts, but do not score their PET-specific metrics as QC anomalies.
    for col in metrics:
        if "fdg" in col:
            df.loc[~df["has_fdg"], col] = np.nan
        if "av45" in col:
            df.loc[~df["has_av45"], col] = np.nan
    zcols = []
    for col in metrics:
        zc = f"z_{col}"
        df[zc] = robust_z(df[col]).abs()
        zcols.append(zc)
    df["auto_score"] = df[zcols].max(axis=1)
    reasons = []
    for _, row in df.iterrows():
        pairs = sorted(((row[z], z[2:]) for z in zcols if np.isfinite(row[z]) and row[z] >= 8.0), reverse=True)
        reasons.append("; ".join(f"{name} robust|z|={score:.2f}" for score, name in pairs[:6]))
    df["candidate_reasons"] = reasons
    raw_z = [c for c in zcols if c.startswith("z_raw_")]
    cache_z = [c for c in zcols if c.startswith("z_cache_")]
    df["raw_outlier_evidence"] = df[raw_z].max(axis=1) >= 8.0
    df["cache_outlier_evidence"] = df[cache_z].max(axis=1) >= 8.0
    df["header_geometry_mismatch"] = ~(df["raw_within_subject_same_shape"].astype(bool) & df["raw_within_subject_same_axcodes"].astype(bool))
    # Manual-review candidate requires independent corroboration in both the source
    # files and the actual training cache, or a direct within-subject header mismatch.
    df["auto_candidate"] = (df["raw_outlier_evidence"] & df["cache_outlier_evidence"]) | df["header_geometry_mismatch"]
    df["candidate_basis"] = np.where(
        df["header_geometry_mismatch"], "within-subject raw header mismatch",
        np.where(df["auto_candidate"], "raw and cache corroboration", "not selected"),
    )
    df["evidence_stage"] = np.select(
        [df["raw_outlier_evidence"] & df["cache_outlier_evidence"], df["raw_outlier_evidence"], df["cache_outlier_evidence"]],
        ["raw_and_cache", "raw_only", "cache_only"],
        default="not_flagged",
    )
    df["confirmed_issue"] = np.where(df.ptid.isin(excluded), "E1 frozen QC confirmed", "")
    df["focus_case"] = df.ptid.isin(FOCUS)
    df["review_priority"] = np.where(df.focus_case, "focus", np.where(df.auto_candidate, "automatic_candidate", "not_flagged"))
    return df


def load_arrays(row: pd.Series) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    raw = {m: np.asanyarray(nib.load(row[m]).dataobj, dtype=np.float32) for m in MODS}
    item = torch.load(row.cache_path, map_location="cpu", weights_only=False)
    cache = {m: np.asarray(item[m][0], dtype=np.float32) for m in MODS}
    return raw, cache


def center_from_mri(a: np.ndarray) -> tuple[int, int, int]:
    vals = a[np.isfinite(a)]
    p1, p99 = np.percentile(vals, [1, 99])
    mask = np.isfinite(a) & (a > p1 + 0.05 * (p99 - p1))
    coords = np.argwhere(mask)
    if coords.size:
        return tuple(np.round(coords.mean(0)).astype(int))
    return tuple(np.asarray(a.shape) // 2)


def slices(a: np.ndarray, c: tuple[int, int, int]) -> list[np.ndarray]:
    return [np.rot90(a[:, :, c[2]]), np.rot90(a[:, c[1], :]), np.rot90(a[c[0], :, :])]


def robust_limits(a: np.ndarray) -> tuple[float, float]:
    v = a[np.isfinite(a)]
    return tuple(np.percentile(v, [1, 99]))


def save_montage(ptid: str, raw: dict, cache: dict, focus: bool) -> list[str]:
    outputs = []
    datasets = [("raw", raw), ("processed", cache)]
    for label, arrays in datasets:
        center = center_from_mri(arrays["mri"])
        fig, axes = plt.subplots(3, 3, figsize=(10.2, 8.6), constrained_layout=True)
        for i, mod in enumerate(MODS):
            vmin, vmax = robust_limits(arrays[mod])
            mod_label = mod.upper() + (" (zero placeholder)" if not np.any(arrays[mod]) else "")
            for j, (view, title) in enumerate(zip(slices(arrays[mod], center), ("axial", "coronal", "sagittal"))):
                axes[i, j].imshow(view, cmap="gray", vmin=vmin, vmax=vmax)
                axes[i, j].set_title(f"{mod_label} · {title}", fontsize=9)
                axes[i, j].axis("off")
        fig.suptitle(f"{ptid} · {label} · MRI-foreground center {center}", fontsize=12)
        filename = f"{ptid}_{label}.png"
        fig.savefig(ASSETS / filename, dpi=135, facecolor="white")
        plt.close(fig)
        outputs.append(filename)
    return outputs


def save_overlay(ptid: str, arrays: dict[str, np.ndarray]) -> str:
    center = center_from_mri(arrays["mri"])
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.4), constrained_layout=True)
    mv = slices(arrays["mri"], center)
    fv = slices(arrays["fdg"], center)
    av = slices(arrays["av45"], center)
    for ax, m, f, a, title in zip(axes, mv, fv, av, ("axial", "coronal", "sagittal")):
        lo, hi = robust_limits(m)
        ax.imshow(m, cmap="gray", vmin=lo, vmax=hi)
        fl = np.percentile(f[np.isfinite(f)], 70)
        al = np.percentile(a[np.isfinite(a)], 70)
        ax.contour(f, levels=[fl], colors=["#d97706"], linewidths=0.8)
        ax.contour(a, levels=[al], colors=["#2563eb"], linewidths=0.8)
        ax.set_title(title, fontsize=9)
        ax.axis("off")
    fig.suptitle(f"{ptid} · processed overlay: MRI + FDG contour (orange) + AV45 contour (blue)", fontsize=11)
    filename = f"{ptid}_processed_overlay.png"
    fig.savefig(ASSETS / filename, dpi=135, facecolor="white")
    plt.close(fig)
    return filename


def save_global_plots(df: pd.DataFrame) -> list[str]:
    files = []
    fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.5), constrained_layout=True)
    for ax, col, label in zip(axes,
        ("cache_mri_zero_fraction", "cache_mri_fdg_com_distance_norm", "cache_mri_av45_com_distance_norm"),
        ("Processed MRI zero fraction", "MRI–FDG COM distance", "MRI–AV45 COM distance")):
        ax.hist(pd.to_numeric(df[col], errors="coerce").dropna(), bins=40, color="#3b6ea8", edgecolor="white")
        ax.set_title(label, fontsize=10)
        ax.set_ylabel("Subjects")
    fn = "global_qc_distributions.png"
    fig.savefig(ASSETS / fn, dpi=150, facecolor="white")
    plt.close(fig); files.append(fn)

    fig, ax = plt.subplots(figsize=(6.3, 4.8), constrained_layout=True)
    ax.scatter(df["cache_mri_fdg_com_distance_norm"], df["cache_mri_av45_com_distance_norm"], s=9, alpha=.45, color="#3b6ea8")
    label_offsets = {"016_S_4952": (5, 2), "123_S_4096": (5, -12), "128_S_4842": (5, 8)}
    for ptid in sorted(FOCUS):
        r = df[df.ptid == ptid].iloc[0]
        ax.scatter(r["cache_mri_fdg_com_distance_norm"], r["cache_mri_av45_com_distance_norm"], s=44, color="#d97706")
        ax.annotate(ptid, (r["cache_mri_fdg_com_distance_norm"], r["cache_mri_av45_com_distance_norm"]), xytext=label_offsets[ptid], textcoords="offset points", fontsize=8)
    ax.set_xlabel("Processed MRI–FDG foreground COM distance / volume diagonal")
    ax.set_ylabel("Processed MRI–AV45 foreground COM distance / volume diagonal")
    ax.grid(alpha=.2)
    fn = "global_alignment_scatter.png"
    fig.savefig(ASSETS / fn, dpi=150, facecolor="white")
    plt.close(fig); files.append(fn)
    return files


def fmt(x, n=4):
    try:
        if pd.isna(x): return "—"
        return f"{float(x):.{n}f}"
    except Exception:
        return html.escape(str(x))


def render() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    df = load_joined().sort_values(["auto_candidate", "auto_score"], ascending=[False, False])
    keep = [c for c in df.columns if not c.startswith("z_")]
    df[keep].to_csv(OUT / "summary.csv", index=False)

    reviewed = df[df.auto_candidate | df.focus_case].copy().sort_values(["focus_case", "auto_score"], ascending=[False, False])
    images = {}
    for i, (_, row) in enumerate(reviewed.iterrows(), 1):
        raw, cache = load_arrays(row)
        images[row.ptid] = save_montage(row.ptid, raw, cache, bool(row.focus_case))
        images[row.ptid].append(save_overlay(row.ptid, cache))
        print(f"render {i}/{len(reviewed)} {row.ptid}", flush=True)
    save_global_plots(df)

    focus_rows = df[df.ptid.isin(FOCUS)].sort_values("ptid")
    candidate_rows = df[df.auto_candidate].sort_values("auto_score", ascending=False)
    confirmed_rows = df[df.confirmed_issue != ""]
    shape_triplets = df[["raw_mri_shape", "raw_fdg_shape", "raw_av45_shape"]].drop_duplicates().shape[0]
    orientation_triplets = df[["raw_mri_axcodes", "raw_fdg_axcodes", "raw_av45_axcodes"]].drop_duplicates().shape[0]

    def table(rows, detailed=False):
        out = ["<table><thead><tr><th>PTID</th><th>Full/OT 角色</th><th>Full</th><th>OT</th><th>E1</th><th>证据阶段</th><th>自动分数</th><th>客观标记</th><th>图像</th></tr></thead><tbody>"]
        for _, r in rows.iterrows():
            links = " ".join(f'<a href="#case-{html.escape(r.ptid)}">查看</a>' for _ in [0] if r.ptid in images)
            out.append(f"<tr><td><code>{html.escape(r.ptid)}</code></td><td>{html.escape(r.full_ot_generator_role)}</td><td>{r.full_membership}</td><td>{r.ot_membership}</td><td>{r.e1_status}</td><td>{r.evidence_stage}</td><td>{fmt(r.auto_score,2)}</td><td>{html.escape(r.candidate_reasons or '—')}</td><td>{links or '—'}</td></tr>")
        return "".join(out) + "</tbody></table>"

    panels = []
    for _, r in reviewed.iterrows():
        path_rows = "".join(f"<tr><th>{m.upper()} raw</th><td><code>{html.escape(str(r[m]))}</code></td></tr>" for m in MODS)
        metric_rows = []
        for m in MODS:
            metric_rows.append(
                f"<tr><td>{m.upper()}</td><td>{r[f'raw_{m}_shape']}</td><td>{r[f'raw_{m}_axcodes']}</td>"
                f"<td>{r[f'raw_{m}_voxel_sizes']}</td><td>{fmt(r[f'raw_{m}_zero_fraction'])}</td>"
                f"<td>{fmt(r[f'raw_{m}_negative_fraction'])}</td><td>{fmt(r[f'cache_{m}_zero_fraction'])}</td>"
                f"<td>{fmt(r[f'cache_{m}_p1'])}</td><td>{fmt(r[f'cache_{m}_p50'])}</td><td>{fmt(r[f'cache_{m}_p99'])}</td></tr>"
            )
        img_html = "".join(f'<figure><a href="assets/{fn}"><img loading="lazy" src="assets/{fn}" alt="{r.ptid} {fn}"></a></figure>' for fn in images[r.ptid])
        panels.append(f"""
        <section class="case" id="case-{html.escape(r.ptid)}">
          <h3>{html.escape(r.ptid)} <span class="badge">fold {int(r.fold)}</span> <span class="badge">{html.escape(r.review_priority)}</span></h3>
          <p>Full/OT 角色：{html.escape(r.full_ot_generator_role)}；Full: included；OT: included；E1: {html.escape(r.e1_status)}；非零 FDG/AV45：{'yes' if r.has_fdg else 'no'}/{'yes' if r.has_av45 else 'no'}；证据阶段：{r.evidence_stage}；自动分数 {fmt(r.auto_score,2)}。</p>
          <p class="small">自动标记：{html.escape(r.candidate_reasons or '未达到自动候选阈值；因指定重点病例展示')}</p>
          <div class="gallery">{img_html}</div>
          <table class="metrics"><thead><tr><th>模态</th><th>raw shape</th><th>raw方向</th><th>raw体素(mm)</th><th>raw零值比例</th><th>raw负值比例</th><th>cache零值比例</th><th>cache p1</th><th>cache p50</th><th>cache p99</th></tr></thead><tbody>{''.join(metric_rows)}</tbody></table>
          <details><summary>数据路径</summary><table>{path_rows}<tr><th>训练缓存</th><td><code>{html.escape(r.cache_path)}</code></td></tr></table></details>
        </section>""")

    css = """
    :root{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#172033;background:#f5f7fa}body{margin:0}.wrap{max-width:1280px;margin:auto;padding:28px}h1{margin-bottom:.25rem}h2{margin-top:2rem;border-bottom:1px solid #d9e0e8;padding-bottom:.45rem}h3{margin-bottom:.4rem}.note{background:#fff7df;border-left:4px solid #d99a21;padding:12px 15px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}.card,.case{background:white;border:1px solid #dce3ea;border-radius:8px;padding:15px}.card b{display:block;font-size:1.55rem;color:#214f7b}.case{margin:18px 0}.badge{display:inline-block;font-size:.76rem;background:#edf3f8;border:1px solid #cad8e5;border-radius:999px;padding:3px 8px;font-weight:500}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:12px}.gallery figure{margin:0}.gallery img{width:100%;height:auto;border:1px solid #dce3ea}table{width:100%;border-collapse:collapse;background:white;font-size:.84rem}th,td{text-align:left;vertical-align:top;padding:7px;border-bottom:1px solid #e5eaf0}th{background:#eef3f7;position:sticky;top:0}code{font-size:.78rem;overflow-wrap:anywhere}.small{font-size:.84rem;color:#536272}.plot{max-width:100%;height:auto;background:white;border:1px solid #dce3ea}.scroll{overflow:auto;max-height:620px;border:1px solid #dce3ea}@media(max-width:700px){.wrap{padding:14px}.metrics{display:block;overflow:auto}}
    """
    document = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Full/OT 输入影像质量复核</title><style>{css}</style></head><body><main class="wrap">
    <h1>Full/OT 输入影像质量复核</h1><p>以下图像用于人工检查空间、强度和训练实际输入。该报告不提供最终因果结论，也不依据 PSNR 排除病例。</p>
    <div class="note"><b>状态定义：</b>“已确认”仅复用已有冻结 QC 记录；“自动候选”由本报告的固定数值规则产生，仍需人工确认。</div>
    <h2>全队列概况</h2><div class="cards">
      <div class="card"><b>{len(df)}</b>Full/OT cohort</div><div class="card"><b>{int((df.fold==1).sum())} / {int((df.fold==2).sum())}</b>fold 1 / fold 2</div>
      <div class="card"><b>{int(df.auto_candidate.sum())}</b>自动候选</div><div class="card"><b>{len(confirmed_rows)}</b>已有冻结 QC 确认</div>
      <div class="card"><b>{int(df.has_fdg.sum())}</b>非零 FDG</div><div class="card"><b>{int(df.has_av45.sum())}</b>非零 AV45</div>
    </div>
    <p class="small">原始文件三模态 shape 组合数：{shape_triplets}；方向组合数：{orientation_triplets}。训练缓存均按正式 Full manifest 定位，OT 复用同一缓存。</p>
    <img class="plot" src="assets/global_qc_distributions.png" alt="全队列QC分布"><img class="plot" src="assets/global_alignment_scatter.png" alt="MRI PET质心距离散点图">
    <h2>筛查规则</h2><p>对 18 个源文件/缓存指标分别按全队列 median/MAD 计算 robust |z|。自动候选要求：源文件至少一个指标 robust |z| ≥ 8，且训练缓存至少一个指标 robust |z| ≥ 8；或同一受试者三模态 raw header 的 shape/方向不一致。指标包括零值/前景比例、PET负值比例、边界接触、MRI–PET 前景 Dice 与归一化质心距离。零占位 PET 保留在 cohort 统计，但不参与对应模态的异常评分。</p>
    <h2>三个指定病例</h2>{table(focus_rows)}
    <h2>已有确认记录</h2>{table(confirmed_rows)}
    <p class="small">E1 冻结规则确认排除仅影响 E1 后续 fitting/inference/evaluation；Full/OT 的正式 1857 人训练与 OOF 仍使用原 cohort。E1 收据记录：016_S_4952 曾进入最初 stage-1 adapter（fold 2 训练侧、fold 1 outer test），随后按冻结 QC 规则在 <code>conditions/qc_exclusion_20261017</code> 重拟合，原结果保留。证据阶段 raw_and_cache 表示源文件和训练缓存均达到筛查阈值，因此不是仅在缓存端出现的标记；它本身不等于最终影像学确认。</p>
    <h2>自动候选病例（需人工复核）</h2><p>共 {len(candidate_rows)} 人。该清单是筛查输出，不是排除清单。</p><div class="scroll">{table(candidate_rows)}</div>
    <h2>病例图像</h2>{''.join(panels)}
    <h2>来源与限制</h2><ul><li>Full 配置与清单：<code>{COHORT}</code>、<code>{SPLIT}</code>、<code>{HASHES}</code></li><li>Full/OT 共享缓存：<code>{CACHE}</code></li><li>OT 当前报告、provenance 与执行代码记录其复制并静态校验 Full cohort/split/input manifest，且复用上述缓存；当前 OT assets 挂载路径下未找到第二份 manifest 文件，因此本次未再次对 OT 独立副本做现文件哈希比较。</li><li>E1 冻结排除记录：<code>{E1_EXCLUSIONS}</code></li><li>原始三模态文件可在训练节点读取；本报告未修改源文件、缓存、split 或实验结果。</li><li>自动筛查不能替代逐病例医学影像复核；未达到阈值不等于已证明无问题。</li></ul>
    </main></body></html>"""
    (OUT / "index.html").write_text(document, encoding="utf-8")
    readme = """# Full/OT 输入影像质量复核\n\n- `index.html`：静态人工审查入口。\n- `summary.csv`：1857 名受试者的路径、fold、原始/缓存 QC 数值和候选标记。\n- `raw_qc_metrics.csv`：原始 MRI/FDG/AV45 的轻量数值筛查。\n- `cache_qc_metrics.csv`：Full/OT 实际复用缓存的轻量数值筛查。\n- `assets/`：全局图、指定病例及自动候选病例的 PNG。\n\n报告只提供客观证据；自动候选不等于确认异常，也不作为排除依据。\n"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")
    print(f"wrote {OUT / 'index.html'} and {OUT / 'summary.csv'}", flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=("collect", "merge", "render", "all"))
    p.add_argument("--shard-index", type=int, default=0)
    p.add_argument("--shard-count", type=int, default=1)
    args = p.parse_args()
    if not 0 <= args.shard_index < args.shard_count:
        p.error("--shard-index must be within --shard-count")
    if args.mode in ("collect", "all"): collect(args.shard_index, args.shard_count)
    if args.mode == "merge": merge_parts()
    if args.mode in ("render", "all"): render()


if __name__ == "__main__":
    main()
