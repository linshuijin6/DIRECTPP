#!/usr/bin/env python3
"""Generate the static Full-OOF AV45 diagnostic visualization report.

This script is read-only with respect to experiment inputs.  It reads the
frozen epoch-165 metrics, predictions, and preprocessed cache, then writes the
report artifacts under this directory.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import nibabel as nib
import numpy as np
import pandas as pd
import torch
from matplotlib.lines import Line2D
from monai.data.utils import pickle_hashing
from scipy import ndimage


REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = Path(__file__).resolve().parent
ASSET_DIR = REPORT_DIR / "assets"
SOURCE_DIR = REPO_ROOT / "reports/original_author_reproduction_20261020"
METRICS_PATH = SOURCE_DIR / "oof_summary/per_subject_metrics.csv"
OVERALL_PATH = SOURCE_DIR / "oof_summary/overall_summary.csv"
COHORT_PATH = SOURCE_DIR / "cohort.json"
RUNNER_PATH = REPO_ROOT / "experiments/original_author_reproduction/run.py"
CACHE_CANDIDATES = (
    REPO_ROOT / "results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3",
    REPO_ROOT / "results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup",
)
DATA_RANGE = 1.0
IMAGE_SHAPE = (160, 192, 160)
GROUP_LABELS = {"high": "较高", "median": "中位附近", "low": "较低"}
GROUP_LABELS_EN = {"high": "High", "median": "Median-adjacent", "low": "Low"}
GROUP_ORDER = {"high": 0, "median": 1, "low": 2}
GROUP_COLORS = {"high": "#3b6fb6", "median": "#b07a1b", "low": "#a64b4b"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def choose_cache_dir() -> Path:
    for candidate in CACHE_CANDIDATES:
        if candidate.is_dir() and any(candidate.glob("*.pt")):
            return candidate
    raise FileNotFoundError("No populated original-author persistent cache was found")


def fixed_selection(av45: pd.DataFrame) -> pd.DataFrame:
    """Select three high, three median-adjacent, and three low PSNR rows."""
    ordered = av45.sort_values(["psnr", "ptid"], ascending=[False, True]).reset_index(drop=True)
    n = len(ordered)
    if n < 9:
        raise ValueError(f"At least nine AV45 rows are required, found {n}")
    middle = n // 2
    blocks = [
        ordered.iloc[:3].assign(selection_group="high"),
        ordered.iloc[middle - 1 : middle + 2].assign(selection_group="median"),
        ordered.iloc[-3:].assign(selection_group="low"),
    ]
    selected = pd.concat(blocks, ignore_index=True)
    rank_by_ptid = {row.ptid: idx + 1 for idx, row in ordered.iterrows()}
    selected["psnr_rank_desc"] = selected["ptid"].map(rank_by_ptid)
    return selected


def load_cached_subject(cache_dir: Path, cohort_row: dict) -> tuple[dict, Path]:
    cache_path = cache_dir / f"{pickle_hashing(cohort_row).decode()}.pt"
    if not cache_path.exists():
        raise FileNotFoundError(cache_path)
    data = torch.load(cache_path, map_location="cpu", weights_only=False)
    return data, cache_path


def as_volume(value: torch.Tensor | np.ndarray) -> np.ndarray:
    array = value.detach().cpu().numpy() if isinstance(value, torch.Tensor) else np.asarray(value)
    array = np.asarray(array, dtype=np.float32).squeeze()
    if array.shape != IMAGE_SHAPE:
        raise ValueError(f"Expected {IMAGE_SHAPE}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError("Volume contains non-finite values")
    return array


def volume_stats(array: np.ndarray, prefix: str) -> dict[str, float]:
    q1, q50, q99 = np.percentile(array, [1, 50, 99])
    return {
        f"{prefix}_min": float(array.min()),
        f"{prefix}_max": float(array.max()),
        f"{prefix}_p1": float(q1),
        f"{prefix}_p50": float(q50),
        f"{prefix}_p99": float(q99),
    }


def slice_for_view(array: np.ndarray, view: str) -> np.ndarray:
    if view == "axial":
        plane = array[:, :, array.shape[2] // 2]
    elif view == "coronal":
        plane = array[:, array.shape[1] // 2, :]
    elif view == "sagittal":
        plane = array[array.shape[0] // 2, :, :]
    else:
        raise ValueError(view)
    return np.rot90(plane)


def robust_limits(array: np.ndarray, nonzero: bool = False) -> tuple[float, float]:
    values = array[array > 0] if nonzero else array.ravel()
    if values.size == 0:
        return 0.0, 1.0
    lo, hi = np.percentile(values, [1, 99])
    if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
        return float(values.min()), float(values.max() + 1e-6)
    return float(lo), float(hi)


def largest_foreground_component(mri_slice: np.ndarray) -> np.ndarray:
    """Return a simple 2D MRI foreground mask for the optional outline view."""
    mask = ndimage.binary_closing(mri_slice > 0.15, iterations=2)
    labels, count = ndimage.label(mask)
    if count == 0:
        return mask
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return ndimage.binary_fill_holes(labels == sizes.argmax())


def plot_subject_slices(ptid: str, mri: np.ndarray, real: np.ndarray, syn: np.ndarray, output: Path) -> None:
    error = np.abs(real - syn)
    mri_limits = robust_limits(mri, nonzero=True)
    pet_limits = robust_limits(np.concatenate([real.ravel(), syn.ravel()]))
    error_limits = (0.0, max(float(np.percentile(error, 99)), 1e-6))
    views = ("axial", "coronal", "sagittal")
    view_titles = (
        f"Axial / axis 2 (index {IMAGE_SHAPE[2] // 2})",
        f"Coronal / axis 1 (index {IMAGE_SHAPE[1] // 2})",
        f"Sagittal / axis 0 (index {IMAGE_SHAPE[0] // 2})",
    )
    rows = (
        ("MRI", mri, "gray", mri_limits, False),
        ("Real AV45", real, "magma", pet_limits, False),
        ("Syn AV45", syn, "magma", pet_limits, False),
        ("|Real − Syn|", error, "inferno", error_limits, False),
        ("Real + MRI foreground outline", real, "magma", pet_limits, True),
        ("Syn + MRI foreground outline", syn, "magma", pet_limits, True),
    )
    fig, axes = plt.subplots(len(rows), len(views), figsize=(10.8, 15.2), constrained_layout=True)
    for col, title in enumerate(view_titles):
        axes[0, col].set_title(title, fontsize=12, pad=8)
    for row_index, (label, array, cmap, limits, add_outline) in enumerate(rows):
        for col, view in enumerate(views):
            ax = axes[row_index, col]
            image = ax.imshow(slice_for_view(array, view), cmap=cmap, vmin=limits[0], vmax=limits[1])
            if add_outline:
                mask = largest_foreground_component(slice_for_view(mri, view))
                if mask.min() != mask.max():
                    ax.contour(mask.astype(float), levels=[0.5], colors=["#46b3c7"], linewidths=0.8)
            if col == 0:
                ax.set_ylabel(label, fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
            for spine in ax.spines.values():
                spine.set_visible(False)
        if row_index in (1, 3):
            cbar = fig.colorbar(image, ax=axes[row_index, :], shrink=0.72, pad=0.01)
            cbar.ax.tick_params(labelsize=8)
    fig.suptitle(
        f"{ptid} · central slices\nReal/Syn share one display range; outline = largest 2D component of MRI > 0.15",
        fontsize=14,
    )
    fig.savefig(output, dpi=150, facecolor="white")
    plt.close(fig)


def plot_subject_histogram(ptid: str, real: np.ndarray, syn: np.ndarray, output: Path) -> None:
    bins = np.linspace(0, 1, 101)
    real_counts, _ = np.histogram(real, bins=bins)
    syn_counts, _ = np.histogram(syn, bins=bins)
    centers = (bins[:-1] + bins[1:]) / 2
    total = real.size
    fig, ax = plt.subplots(figsize=(8.4, 4.4), constrained_layout=True)
    ax.step(centers, 100 * real_counts / total, where="mid", color="#25364a", linewidth=1.8, label="Real AV45")
    ax.step(centers, 100 * syn_counts / total, where="mid", color="#d4832f", linewidth=1.8, label="Syn AV45")
    ax.set_yscale("symlog", linthresh=0.001)
    ax.set_xlim(0, 1)
    ax.set_xlabel("Normalized uptake")
    ax.set_ylabel("Voxels per bin (%) · symlog")
    ax.set_title(f"{ptid} · full-volume intensity histogram")
    ax.grid(axis="y", color="#d9dee5", linewidth=0.6)
    ax.legend(frameon=False)
    fig.savefig(output, dpi=150, facecolor="white")
    plt.close(fig)


def plot_global_metric_hist(values: pd.Series, metric: str, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 4.7), constrained_layout=True)
    ax.hist(values, bins=35, color="#3b6fb6", edgecolor="white", linewidth=0.6)
    ax.axvline(values.mean(), color="#a64b4b", linestyle="--", linewidth=1.6, label=f"Mean {values.mean():.4g}")
    ax.axvline(values.median(), color="#b07a1b", linestyle=":", linewidth=1.8, label=f"Median {values.median():.4g}")
    ax.set_xlabel("PSNR (dB)" if metric == "PSNR" else "MSE")
    ax.set_ylabel("Subjects")
    ax.set_title(f"Full OOF AV45 · {metric} distribution (n={len(values)})")
    ax.grid(axis="y", color="#d9dee5", linewidth=0.6)
    ax.legend(frameon=False)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


def plot_psnr_mse(av45: pd.DataFrame, selected: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots(figsize=(8.2, 5.1), constrained_layout=True)
    ax.scatter(av45["mse"], av45["psnr"], s=10, alpha=0.35, color="#60758b", linewidths=0, label="All AV45 subjects")
    for group in ("high", "median", "low"):
        part = selected[selected.selection_group == group]
        ax.scatter(
            part["mse"], part["psnr"], s=55, color=GROUP_COLORS[group], edgecolor="white", linewidth=0.7,
            label=f"Selected: {GROUP_LABELS_EN[group]}", zorder=3,
        )
    x = np.linspace(max(float(av45.mse.min()), 1e-8), float(av45.mse.max()), 300)
    ax.plot(x, -10 * np.log10(x), color="#25364a", linewidth=1.2, linestyle="--", label="−10 log10(MSE), data_range=1")
    ax.set_xscale("log")
    ax.set_xlabel("MSE (log scale)")
    ax.set_ylabel("PSNR (dB)")
    ax.set_title(f"Full OOF AV45 · PSNR vs MSE (n={len(av45)})")
    ax.grid(color="#d9dee5", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


def plot_selected_intensity_ranges(summary: pd.DataFrame, output: Path) -> None:
    ordered = summary.sort_values(["selection_group_order", "psnr_rank_desc"]).reset_index(drop=True)
    y = np.arange(len(ordered))
    fig, ax = plt.subplots(figsize=(9.5, 6.1), constrained_layout=True)
    offsets = {"real": -0.16, "syn": 0.16}
    styles = {"real": ("#25364a", "o", "Real AV45"), "syn": ("#d4832f", "s", "Syn AV45")}
    for key in ("real", "syn"):
        color, marker, label = styles[key]
        yy = y + offsets[key]
        ax.hlines(yy, ordered[f"{key}_min"], ordered[f"{key}_max"], color=color, alpha=0.22, linewidth=1.1)
        ax.hlines(yy, ordered[f"{key}_p1"], ordered[f"{key}_p99"], color=color, linewidth=3.0, label=label)
        ax.scatter(ordered[f"{key}_p50"], yy, color=color, marker=marker, s=34, zorder=3)
    labels = [f"{row.ptid} · {GROUP_LABELS_EN[row.selection_group]}" for row in ordered.itertuples()]
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlim(-0.01, 1.01)
    ax.set_xlabel("Normalized uptake · thin=min–max; thick=p1–p99; marker=p50")
    ax.set_title("Selected 9 AV45 cases · full-volume intensity ranges")
    ax.grid(axis="x", color="#d9dee5", linewidth=0.6)
    handles = [
        Line2D([0], [0], color=styles["real"][0], linewidth=3, marker=styles["real"][1], label=styles["real"][2]),
        Line2D([0], [0], color=styles["syn"][0], linewidth=3, marker=styles["syn"][1], label=styles["syn"][2]),
    ]
    ax.legend(handles=handles, frameon=False, loc="lower right")
    fig.savefig(output, dpi=160, facecolor="white")
    plt.close(fig)


def fnum(value: float | int | None, digits: int = 6) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "—"
    return f"{float(value):.{digits}f}"


def metric_cards(av45: pd.DataFrame) -> str:
    stats = [
        ("Subjects", f"{len(av45)}"),
        ("Mean PSNR", f"{av45.psnr.mean():.6f} dB"),
        ("Median PSNR", f"{av45.psnr.median():.6f} dB"),
        ("SD", f"{av45.psnr.std(ddof=1):.6f} dB"),
        ("Minimum", f"{av45.psnr.min():.6f} dB"),
        ("Maximum", f"{av45.psnr.max():.6f} dB"),
    ]
    return "".join(f'<div class="metric"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>' for label, value in stats)


def build_html(av45: pd.DataFrame, summary: pd.DataFrame, checks: dict, source_hashes: dict) -> str:
    table_rows = []
    for row in summary.itertuples():
        table_rows.append(
            "<tr>"
            f"<td>{GROUP_LABELS[row.selection_group]}</td>"
            f"<td><a href=\"#subject-{html.escape(row.ptid)}\">{html.escape(row.ptid)}</a></td>"
            f"<td>{int(row.psnr_rank_desc)}</td><td>{int(row.fold)}</td>"
            f"<td>{row.reported_psnr:.6f}</td><td>{row.reported_mse:.8f}</td><td>{row.reported_mae:.8f}</td>"
            f"<td>{fnum(row.fdg_psnr, 6)}</td>"
            "</tr>"
        )

    subject_sections = []
    for row in summary.itertuples():
        stat_line = (
            f"PSNR {row.reported_psnr:.6f} dB · MSE {row.reported_mse:.8f} · MAE {row.reported_mae:.8f} · "
            f"Real min/max/p1/p50/p99: {row.real_min:.4f} / {row.real_max:.4f} / {row.real_p1:.4f} / {row.real_p50:.4f} / {row.real_p99:.4f} · "
            f"Syn min/max/p1/p50/p99: {row.syn_min:.4f} / {row.syn_max:.4f} / {row.syn_p1:.4f} / {row.syn_p50:.4f} / {row.syn_p99:.4f}"
        )
        subject_sections.append(
            f'<section class="subject" id="subject-{html.escape(row.ptid)}">'
            f'<h3>{html.escape(row.ptid)} <span>{GROUP_LABELS[row.selection_group]} · rank {int(row.psnr_rank_desc)} · fold {int(row.fold)}</span></h3>'
            f'<p class="numbers">{html.escape(stat_line)}</p>'
            f'<a href="assets/{html.escape(row.slice_panel)}"><img src="assets/{html.escape(row.slice_panel)}" alt="{html.escape(row.ptid)} MRI, real AV45, synthetic AV45, error and outline panels" loading="lazy"></a>'
            f'<a href="assets/{html.escape(row.histogram)}"><img class="hist" src="assets/{html.escape(row.histogram)}" alt="{html.escape(row.ptid)} real and synthetic AV45 intensity histogram" loading="lazy"></a>'
            '<p class="back"><a href="#subject-table">返回受试者表</a></p></section>'
        )

    css = """
    :root { color-scheme: light; --ink:#25364a; --muted:#66717f; --line:#d9dee5; --paper:#ffffff; --wash:#f5f7fa; --accent:#3b6fb6; }
    * { box-sizing: border-box; }
    body { margin:0; font-family:Arial, Helvetica, sans-serif; color:var(--ink); background:var(--wash); line-height:1.45; }
    main { width:min(1180px, calc(100% - 32px)); margin:24px auto 56px; }
    header, section { background:var(--paper); border:1px solid var(--line); border-radius:8px; padding:22px; margin:0 0 18px; }
    h1 { margin:0 0 8px; font-size:28px; }
    h2 { margin:0 0 16px; font-size:21px; }
    h3 { margin:0 0 8px; font-size:19px; }
    h3 span { color:var(--muted); font-size:14px; font-weight:normal; }
    p { margin:8px 0; }
    .notice { border-left:4px solid var(--accent); padding-left:12px; }
    .metrics { display:grid; grid-template-columns:repeat(3, minmax(0,1fr)); gap:10px; margin:16px 0; }
    .metric { background:var(--wash); border:1px solid var(--line); border-radius:6px; padding:11px 13px; }
    .metric span { display:block; color:var(--muted); font-size:12px; }
    .metric strong { display:block; margin-top:2px; font-size:18px; }
    .grid { display:grid; grid-template-columns:repeat(2, minmax(0,1fr)); gap:14px; }
    .grid figure { margin:0; }
    .grid img, .subject img { display:block; width:100%; height:auto; border:1px solid var(--line); border-radius:5px; background:white; }
    .subject img.hist { width:min(820px, 100%); margin:14px auto 0; }
    figcaption { color:var(--muted); font-size:13px; margin-top:5px; }
    table { width:100%; border-collapse:collapse; font-variant-numeric:tabular-nums; }
    th, td { border-bottom:1px solid var(--line); padding:9px 8px; text-align:right; white-space:nowrap; }
    th:first-child, td:first-child, th:nth-child(2), td:nth-child(2) { text-align:left; }
    th { background:var(--wash); font-size:12px; }
    .table-wrap { overflow-x:auto; }
    .numbers { color:#384a5d; font-family:ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:12px; overflow-wrap:anywhere; }
    code { background:var(--wash); padding:2px 5px; border-radius:4px; overflow-wrap:anywhere; }
    a { color:#245b9b; }
    .back { text-align:right; font-size:13px; }
    .checks td:first-child { text-align:left; white-space:normal; }
    footer { color:var(--muted); font-size:12px; padding:0 4px; }
    @media (max-width:760px) { .metrics, .grid { grid-template-columns:1fr; } main { width:min(100% - 18px, 1180px); } header, section { padding:15px; } }
    """

    return f"""<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Full OOF AV45 PSNR 诊断型可视化</title><style>{css}</style></head>
<body><main>
<header>
  <h1>Full OOF AV45 PSNR 诊断型可视化</h1>
  <p class="notice">以下图像用于人工检查空间、强度和指标口径。该报告不提供最终因果结论。</p>
  <p>数据：原作者语义重建实验，epoch 165，两折 OOF，AV45。预测在推理时截断至 [0,1]；指标基于完整预处理体积 160×192×160，PSNR 使用 data_range=1，逐受试者计算后取平均。</p>
</header>

<section id="overview"><h2>A. Overview</h2><div class="metrics">{metric_cards(av45)}</div>
  <p>逐受试者源：<code>reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv</code></p>
  <p>计算实现：<code>experiments/original_author_reproduction/run.py</code>；MSE/MAE 为完整预处理体积逐体素均值。</p>
</section>

<section id="subject-table"><h2>B. Subject table</h2>
  <p>固定规则：PSNR 降序、PTID 升序处理并列；取排名 1–3、{len(av45)//2}–{len(av45)//2+2}、{len(av45)-2}–{len(av45)}（1-based）。</p>
  <div class="table-wrap"><table><thead><tr><th>组别</th><th>PTID</th><th>PSNR rank</th><th>fold</th><th>AV45 PSNR</th><th>AV45 MSE</th><th>AV45 MAE</th><th>FDG PSNR</th></tr></thead><tbody>{''.join(table_rows)}</tbody></table></div>
  <p><a href="summary.csv">下载 summary.csv</a></p>
</section>

<section><h2>D. Global quick diagnostics</h2><div class="grid">
  <figure><a href="assets/global_psnr_hist.png"><img src="assets/global_psnr_hist.png" alt="Full OOF AV45 PSNR histogram"></a><figcaption>全部 1365 人的 AV45 PSNR。</figcaption></figure>
  <figure><a href="assets/global_mse_hist.png"><img src="assets/global_mse_hist.png" alt="Full OOF AV45 MSE histogram"></a><figcaption>全部 1365 人的 AV45 MSE。</figcaption></figure>
  <figure><a href="assets/global_psnr_vs_mse.png"><img src="assets/global_psnr_vs_mse.png" alt="Full OOF AV45 PSNR versus MSE"></a><figcaption>全部 1365 人；虚线为 data_range=1 时的公式。</figcaption></figure>
  <figure><a href="assets/selected_intensity_ranges.png"><img src="assets/selected_intensity_ranges.png" alt="Selected nine subjects real and synthetic AV45 intensity ranges"></a><figcaption>固定选择的 9 人；每人的统计基于完整 160×192×160 体积。该图不是全队列强度统计。</figcaption></figure>
</div></section>

<section><h2>指标口径一致性</h2><div class="table-wrap"><table class="checks"><tbody>
  <tr><td>CSV 中 1365 人 PSNR 的均值</td><td>{checks['reported_mean_psnr']:.9f} dB</td></tr>
  <tr><td>由每人 MSE 与 data_range=1 计算 PSNR 后再平均</td><td>{checks['mean_psnr_from_subject_mse']:.9f} dB</td></tr>
  <tr><td>逐行 |CSV PSNR − 公式 PSNR| 最大值</td><td>{checks['max_abs_psnr_formula_diff']:.3e} dB</td></tr>
  <tr><td>先平均 MSE 再换算得到的 PSNR（不同聚合顺序）</td><td>{checks['psnr_from_mean_mse']:.9f} dB</td></tr>
  <tr><td>9 人从现有预测与 GT 重算：PSNR 最大绝对差</td><td>{checks['selected_max_abs_psnr_diff']:.3e} dB</td></tr>
  <tr><td>9 人从现有预测与 GT 重算：MSE 最大绝对差</td><td>{checks['selected_max_abs_mse_diff']:.3e}</td></tr>
  <tr><td>9 人从现有预测与 GT 重算：MAE 最大绝对差</td><td>{checks['selected_max_abs_mae_diff']:.3e}</td></tr>
</tbody></table></div></section>

<section><h2>C. Per-subject visual panels</h2><p>三方向均使用体积中心切片；MRI / Real / Syn / Error 使用相同数组轴和切片索引。Real 与 Syn 共用显示范围；青色线为同层 MRI &gt; 0.15 后最大二维连通区域的外轮廓。</p></section>
{''.join(subject_sections)}

<section><h2>来源校验</h2><div class="table-wrap"><table class="checks"><tbody>
  <tr><td>逐受试者指标 SHA-256</td><td><code>{source_hashes['metrics']}</code></td></tr>
  <tr><td>cohort SHA-256</td><td><code>{source_hashes['cohort']}</code></td></tr>
  <tr><td>评估实现 SHA-256</td><td><code>{source_hashes['runner']}</code></td></tr>
</tbody></table></div></section>
<footer>Generated from existing Full OOF outputs. No training or PET generation is performed by this report.</footer>
</main></body></html>"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-images", action="store_true", help="Only rewrite tables and HTML using existing PNG files")
    args = parser.parse_args()

    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    metrics = pd.read_csv(METRICS_PATH)
    av45 = metrics[(metrics["tracer"] == "av45") & (metrics["epoch"] == 165)].copy()
    if len(av45) != 1365 or av45["ptid"].duplicated().any():
        raise RuntimeError(f"Expected 1365 unique epoch-165 AV45 rows, got {len(av45)}")
    selected = fixed_selection(av45)
    cohort = json.loads(COHORT_PATH.read_text())
    cohort_by_ptid = {row["name"]: row for row in cohort}
    cache_dir = choose_cache_dir()
    fdg = metrics[(metrics["tracer"] == "fdg") & (metrics["epoch"] == 165)].set_index("ptid")["psnr"]

    summary_rows = []
    for selected_row in selected.itertuples():
        cached, cache_path = load_cached_subject(cache_dir, cohort_by_ptid[selected_row.ptid])
        mri = as_volume(cached["mri"])
        real = as_volume(cached["av45"])
        prediction_path = Path(selected_row.prediction)
        if not prediction_path.exists():
            raise FileNotFoundError(prediction_path)
        syn = as_volume(nib.load(prediction_path).get_fdata(dtype=np.float32))
        difference = syn.astype(np.float64) - real.astype(np.float64)
        recalculated_mse = float(np.mean(difference * difference))
        recalculated_mae = float(np.mean(np.abs(difference)))
        recalculated_psnr = float(-10 * np.log10(recalculated_mse / DATA_RANGE**2))
        slice_name = f"{selected_row.ptid}_slices.png"
        hist_name = f"{selected_row.ptid}_hist.png"
        if not args.skip_images:
            plot_subject_slices(selected_row.ptid, mri, real, syn, ASSET_DIR / slice_name)
            plot_subject_histogram(selected_row.ptid, real, syn, ASSET_DIR / hist_name)
        result = {
            "selection_group": selected_row.selection_group,
            "selection_group_order": GROUP_ORDER[selected_row.selection_group],
            "psnr_rank_desc": int(selected_row.psnr_rank_desc),
            "ptid": selected_row.ptid,
            "fold": int(selected_row.fold),
            "epoch": int(selected_row.epoch),
            "reported_psnr": float(selected_row.psnr),
            "reported_mse": float(selected_row.mse),
            "reported_mae": float(selected_row.mae),
            "recalculated_psnr": recalculated_psnr,
            "recalculated_mse": recalculated_mse,
            "recalculated_mae": recalculated_mae,
            "abs_psnr_diff": abs(recalculated_psnr - float(selected_row.psnr)),
            "abs_mse_diff": abs(recalculated_mse - float(selected_row.mse)),
            "abs_mae_diff": abs(recalculated_mae - float(selected_row.mae)),
            "fdg_psnr": float(fdg[selected_row.ptid]) if selected_row.ptid in fdg.index else np.nan,
            **volume_stats(real, "real"),
            **volume_stats(syn, "syn"),
            "prediction_path": str(prediction_path),
            "prediction_sha256": selected_row.prediction_sha256,
            "cache_path": str(cache_path),
            "slice_panel": slice_name,
            "histogram": hist_name,
        }
        summary_rows.append(result)

    summary = pd.DataFrame(summary_rows).sort_values(["selection_group_order", "psnr_rank_desc"])
    summary.to_csv(REPORT_DIR / "summary.csv", index=False, float_format="%.12g")

    formula_psnr = -10 * np.log10(av45["mse"].to_numpy(dtype=float) / DATA_RANGE**2)
    checks = {
        "reported_mean_psnr": float(av45.psnr.mean()),
        "mean_psnr_from_subject_mse": float(formula_psnr.mean()),
        "max_abs_psnr_formula_diff": float(np.max(np.abs(av45.psnr.to_numpy() - formula_psnr))),
        "psnr_from_mean_mse": float(-10 * np.log10(av45.mse.mean() / DATA_RANGE**2)),
        "selected_max_abs_psnr_diff": float(summary.abs_psnr_diff.max()),
        "selected_max_abs_mse_diff": float(summary.abs_mse_diff.max()),
        "selected_max_abs_mae_diff": float(summary.abs_mae_diff.max()),
    }

    if not args.skip_images:
        plot_global_metric_hist(av45.psnr, "PSNR", ASSET_DIR / "global_psnr_hist.png")
        plot_global_metric_hist(av45.mse, "MSE", ASSET_DIR / "global_mse_hist.png")
        plot_psnr_mse(av45, selected, ASSET_DIR / "global_psnr_vs_mse.png")
        plot_selected_intensity_ranges(summary, ASSET_DIR / "selected_intensity_ranges.png")

    source_hashes = {"metrics": sha256(METRICS_PATH), "cohort": sha256(COHORT_PATH), "runner": sha256(RUNNER_PATH)}
    (REPORT_DIR / "index.html").write_text(build_html(av45, summary, checks, source_hashes), encoding="utf-8")
    receipt = {
        "status": "COMPLETE",
        "scope": "static diagnostic visualization only; no causal conclusion",
        "source": "Full OOF epoch 165 AV45",
        "subjects": len(av45),
        "selected_subjects": len(summary),
        "selection_rule": "PSNR descending, PTID ascending tie-break; ranks 1-3, 682-684, 1363-1365",
        "metric_protocol": {"data_range": DATA_RANGE, "volume_shape": list(IMAGE_SHAPE), "aggregation": "per-subject then mean"},
        "checks": checks,
        "source_sha256": source_hashes,
    }
    (REPORT_DIR / "generation_receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
