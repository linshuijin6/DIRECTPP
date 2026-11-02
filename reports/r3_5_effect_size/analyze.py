"""R3-5: descriptive AD-minus-CN Cohen's d for all Figure 4C-F ROIs.

Run with the xiaochou Python interpreter. Reads only the approved shuijin ROI
CSVs and existing evidence; writes only this directory's CSV and REPORT.md.
No hypothesis tests, FDR computation, training, inference, or network writes.
The GitHub discovery receipt below records the authoring session, not a live
GitHub check performed by rerunning this script.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
R28 = ROOT / "reports/r2_8_original_roi_stats"
SOURCE = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin"
LUT = Path("/mnt/nfsdata/nfsdata/linshuijin/freesurfer/FreeSurferColorLUT.txt")
GITHUB_COMMIT = "bd4e231c520461e31c6b770638df048f928d1e06"
# R2-8 mapping except E's first two items: author correction, PDF reinspection
# and LUT confirm Left/Right-VentralDC 28/60; R2-8's 4/43 mapping is wrong.
PANELS = {
    "C": ("AV45", [(1025, "ctx-lh-precuneus"), (1009, "ctx-lh-inferiortemporal"),
                   (1015, "ctx-lh-middletemporal"), (1030, "ctx-lh-superiortemporal"),
                   (1034, "ctx-lh-transversetemporal")]),
    "D": ("FDG", [(1010, "ctx-lh-isthmuscingulate"), (2010, "ctx-rh-isthmuscingulate"),
                  (1031, "ctx-lh-supramarginal"), (17, "Left-Hippocampus"),
                  (53, "Right-Hippocampus")]),
    "E": ("AV45", [(28, "Left-VentralDC"), (60, "Right-VentralDC"),
                   (53, "Right-Hippocampus"), (7, "Left-Cerebellum-White-Matter"),
                   (17, "Left-Hippocampus")]),
    "F": ("FDG", [(10, "Left-Thalamus"), (49, "Right-Thalamus"),
                  (1019, "ctx-lh-parsorbitalis"), (1011, "ctx-lh-lateraloccipital"),
                  (2013, "ctx-rh-lingual")]),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity_hash(frame):
    # PTID and original group label; sorting changes only fingerprint order.
    records = sorted(map(tuple, frame[["subject", "Research Group"]].to_numpy()))
    return hashlib.sha256(json.dumps(records, ensure_ascii=False).encode()).hexdigest()


def mapping_check():
    # Parse code literals without importing/executing the historical analysis.
    tree = ast.parse((R28 / "analyze.py").read_text())
    prior = next(ast.literal_eval(n.value) for n in tree.body
                 if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "FIGURE4" for t in n.targets))
    lut = {}
    for line in LUT.read_text().splitlines():
        fields = line.split()
        if len(fields) > 1 and fields[0].isdigit():
            lut[int(fields[0])] = fields[1]
    report = (R28 / "REPORT.md").read_text()
    for panel, (tracer, items) in PANELS.items():
        labels = [name for _, name in items]
        if panel == "E":
            assert prior[panel][:2] == ["Left-Lateral-Ventricle", "Right-Lateral-Ventricle"]
            assert labels[:2] == ["Left-VentralDC", "Right-VentralDC"]
            assert prior[panel][2:] == labels[2:]
        else:
            assert prior[panel] == labels
        for roi, name in items:
            assert lut[roi] == name
            if panel == "E" and roi in (28, 60):
                # Correct the documented historical mapping error, without
                # changing the protected R2-8 files or accepting other drift.
                continue
            display = "Left-Cblm-WM → " + name if roi == 7 else name
            expected = f"| {tracer} | {panel} | {display} | {roi} |"
            if panel == "C" and roi == 1025:
                expected = f"| {tracer} | A,C | {name} | {roi} |"
            assert expected in report, expected


def compute():
    mapping_check()
    old_audit = pd.read_csv(R28 / "input_audit.csv").set_index(["tracer", "roi_id"])
    old_stats = pd.read_csv(R28 / "regional_paired_statistics.csv").set_index(
        ["tracer", "roi_id", "analysis_group"])
    baseline_groups = {}
    rows = []
    for panel, (tracer, items) in PANELS.items():
        for order, (roi, name) in enumerate(items, 1):
            path = SOURCE / f"statistics_of_regions_{tracer.lower()}_adjust/region_{roi}.0.csv"
            assert SOURCE.resolve() in path.resolve().parents
            old = old_audit.loc[(tracer, roi)]
            assert path.resolve() == Path(old.input_file).resolve()
            assert sha256(path) == old.sha256, path
            raw = pd.read_csv(path, dtype=str, keep_default_na=False)
            cols = [f"real_{tracer.lower()}_mean", f"syn_{tracer.lower()}_mean"]
            assert list(raw.columns) == ["subject", *cols, "Research Group"]
            groups = dict(zip(raw.subject, raw["Research Group"]))
            baseline_groups.setdefault(tracer, groups)
            assert groups == baseline_groups[tracer], "PTID/group assignment differs across ROIs"
            values = raw[cols].apply(pd.to_numeric, errors="coerce")
            blank = raw.subject.str.strip().eq("")
            duplicate = raw.subject.duplicated(keep=False) & ~blank
            finite = np.isfinite(values).all(axis=1)
            valid = ~blank & ~duplicate & finite
            assert len(raw) == old.raw_rows
            assert int((~valid).sum()) == old.excluded_rows
            assert int(valid.sum()) == old.valid_pairs
            ad_cn = raw["Research Group"].isin(["AD", "CN"])
            selected = raw.loc[valid & ad_cn].copy()
            selected[cols] = values.loc[selected.index]
            assert selected.subject.is_unique
            assert not set(selected.loc[selected["Research Group"] == "AD", "subject"]) & set(
                selected.loc[selected["Research Group"] == "CN", "subject"])
            row = dict(panel=panel, panel_order=order, tracer=tracer, roi_id=roi,
                       roi_name=name, figure_label="Left-Cblm-WM" if roi == 7 else name,
                       contrast="AD-CN", uptake_unit="normalized uptake (arbitrary units)")
            for group in ("AD", "CN"):
                sub = selected.loc[selected["Research Group"] == group]
                row[f"N_{group}"] = len(sub)
                assert len(sub) >= 2
                row[f"subjects_{group}_sha256"] = identity_hash(sub)
                for mode, col in zip(("real", "syn"), cols):
                    row[f"{mode}_{group}_mean"] = float(sub[col].mean())
                    row[f"{mode}_{group}_sd"] = float(sub[col].std(ddof=1))
                    previous = old_stats.loc[(tracer, roi, group)]
                    assert len(sub) == previous.n_pairs
                    for suffix in ("mean", "sd"):
                        assert np.isclose(row[f"{mode}_{group}_{suffix}"],
                                          previous[f"{mode}_{suffix}"], rtol=1e-12, atol=1e-14)
            for mode in ("real", "syn"):
                n_ad, n_cn = row["N_AD"], row["N_CN"]
                pooled = np.sqrt(((n_ad - 1) * row[f"{mode}_AD_sd"] ** 2
                                  + (n_cn - 1) * row[f"{mode}_CN_sd"] ** 2)
                                 / (n_ad + n_cn - 2))
                assert np.isfinite(pooled) and pooled > 0
                row[f"sd_pooled_{mode}"] = float(pooled)
                row[f"d_{mode}"] = (row[f"{mode}_AD_mean"] - row[f"{mode}_CN_mean"]) / pooled
            row["delta_d"] = row["d_syn"] - row["d_real"]
            row["abs_d_difference"] = abs(row["d_syn"]) - abs(row["d_real"])
            row["direction_reversed"] = row["d_real"] * row["d_syn"] < 0
            row["absolute_effect_change"] = ("increase" if row["abs_d_difference"] > 0
                                             else "decrease" if row["abs_d_difference"] < 0 else "unchanged")
            row.update(figure_real_annotation="****" if panel in "CD" else "ns",
                       figure_syn_annotation="****" if panel in "CD" else "ns",
                       r2_9_status="not_located", r2_9_real_p="", r2_9_real_q="",
                       r2_9_syn_p="", r2_9_syn_q="", r2_9_fdr_classification="unverified",
                       both_fdr_significant="unverified", large_change_flag="no_prespecified_threshold",
                       source_file=str(path.relative_to(ROOT)), source_sha256=sha256(path),
                       raw_rows=len(raw), valid_rows_all_groups=int(valid.sum()),
                       excluded_rows_all_groups=int((~valid).sum()),
                       excluded_AD_CN_rows=int((~valid & ad_cn).sum()),
                       excluded_row_details=old.excluded_row_details,
                       retained_AD_CN_outside_0_1=int(((values.loc[selected.index] < 0)
                                                     | (values.loc[selected.index] > 1)).any(axis=1).sum()))
            rows.append(row)
    frame = pd.DataFrame(rows)
    assert len(frame) == 20 and not frame.duplicated(["tracer", "roi_id"]).any()
    assert frame.groupby("panel").size().to_dict() == dict(C=5, D=5, E=5, F=5)
    fdr_path = ROOT / "reports/r2_9_figure4_fdr/all_392_student_fdr.csv"
    if fdr_path.exists():
        fdr = pd.read_csv(fdr_path, float_precision="round_trip")
        assert len(fdr) == 392 and fdr.groupby(["tracer", "modality"]).size().eq(98).all()
        assert fdr.family_n_tests.eq(98).all()
        assert fdr.test.eq("Student_independent_two_sided").all() and fdr.equal_var.all()
        indexed = fdr.set_index(["tracer", "roi_id", "modality"])
        for i, row in frame.iterrows():
            significant = []
            for mode in ("real", "syn"):
                stat = indexed.loc[(row.tracer, row.roi_id, mode)]
                assert stat.source_sha256 == row.source_sha256
                for group in ("AD", "CN"):
                    assert stat[f"N_{group}"] == row[f"N_{group}"]
                    assert stat[f"subjects_{group}_sha256"] == row[f"subjects_{group}_sha256"]
                assert np.isclose(row[f"d_{mode}"], stat.t_statistic * np.sqrt(1/stat.N_AD + 1/stat.N_CN),
                                  rtol=1e-11, atol=1e-13)
                frame.at[i, f"r2_9_{mode}_p"] = float(stat.raw_p)
                frame.at[i, f"r2_9_{mode}_q"] = float(stat.bh_q)
                significant.append(bool(stat.bh_q < 0.05))
            frame.at[i, "r2_9_status"] = "new_recalculation_not_historical_plot_values"
            frame.at[i, "both_fdr_significant"] = all(significant)
            frame.at[i, "r2_9_fdr_classification"] = (
                "both_significant" if all(significant) else "both_non_significant" if not any(significant)
                else "real_only" if significant[0] else "syn_only")
    return frame


def report(frame):
    lines = [
        "# R3-5：Figure 4C–F 的 AD−CN Cohen’s d", "",
        "20 个图示 tracer×ROI 全部覆盖（40 个 Real/Syn 组间统计标注）。两处效应量符号改变："
        "AV45 右海马、FDG 左丘脑，但均发生在接近零的效应量上。最大绝对幅度变化为 "
        f"{frame.abs_d_difference.abs().max():.4f}。指定 CSV 支持 C/D 的疾病差异方向大体保持，"
        "不足以认定原稿的 **precisely preserved**，也不构成临床等效性证据。", "",
        "**映射更正：**作者指出并经放大原图及 LUT 复核，E 前两项应为 Left/Right-VentralDC "
        "（28/60），此前沿用 R2-8 的 Left/Right-Lateral-Ventricle（4/43）有误。"
        "本报告及 CSV 已替换为28/60；撤回旧版由4/43引出的图面显著性不一致判断。"
        "R2-8 原文件按保护要求保留，该映射错误不影响其按ROI ID记录的数值统计。", "",
        "## 1. 来源、映射与受试者", "",
        "核查日期：2026-11-02。仅读取作者确认的 `shuijin/statistics_of_regions_av45_adjust/` "
        "与 `shuijin/statistics_of_regions_fdg_adjust/`，共同前缀为 "
        "`source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/`。外层同名 abandon 目录未读取。",
        "",
        "直接目视核对 [原图](../../manuscript/figures/figure_4.pdf) 与 "
        "[稿件图注及原句](../../manuscript/BMEF_main.tex)：C/E 为 AV45，D/F 为 FDG；"
        "均比较原始标签 AD 与 CN，绿色 CN、红色 AD，实心半小提琴为 Real，斜线半小提琴为 Syn；"
        "实线括号为 Real，虚线括号为 Syn。C/D 每个 ROI 两条括号均为 `****`，E/F 均为 `ns`。"
        "星号仅如实抄录，不赋予未经核实的 p/q 数值或阈值。",
        "",
        "下表顺序沿用图面；E 前两项依作者更正、放大原图和 FreeSurferColorLUT 核对为28/60，"
        "其余ID/名称沿用 [R2-8 表](../r2_8_original_roi_stats/REPORT.md) 并交叉核对LUT。"
        "E 的 `Left-Cblm-WM` 对应 ID 7 `Left-Cerebellum-White-Matter`。",
        "",
        "每个 ROI 的 Real/Syn 使用同一批有效 PTID：保留原 `subject`（PTID）与 `Research Group` "
        "对应关系，只取精确标签 AD/CN；不合并其他组，不重新归一化、裁剪或插补。"
        "排除空/重复 PTID 或任一测量非有限的整行，边界与 R2-8 一致。20 文件的 SHA-256、"
        "行数、排除数及 AD/CN 均值/SD/N 均与 R2-8 已存结果逐项一致；"
        "同示踪剂各文件的原始 PTID→组别映射一致。",
        "",
        "AV45 每项 N_AD=179、N_CN=511；FDG 除左海马外每项 303/371，左海马 302/371。"
        "FDG 左海马排除 AD `010_S_0786`（CSV 第178行，双侧非有限）；"
        "AV45 小脑白质排除 LMCI `128_S_4842`（第1117行），不影响本次 AD/CN。"
        "所选文件无空/重复 PTID；本次保留的 AD/CN 值均在 [0,1]，未因数值范围筛选。"
        "CSV 保留来源哈希、分组身份集合哈希和排除明细，可回溯受试者集合；两示踪剂不合并。",
        "",
        "**来源边界：**已确认指定源数据、图面 tracer/ROI/组别及既有映射；"
        "尚未证明这批 CSV 就是历史 C–F 的精确绘图输入。"
        "[R2-8 来源核验](../r2_8_original_roi_stats/FIGURE4_SOURCE_CHECK.md) 的数值/形状对应性"
        "主要针对 A/B，不能扩展成 C–F 绘图流程证明。", "",
        "## 2. 方法与完整结果", "",
        "分别对 Real 和 Syn 计算独立两组样本效应量：", "",
        "`s_p = sqrt(((N_AD−1) s_AD² + (N_CN−1) s_CN²) / (N_AD+N_CN−2))`", "",
        "`d = (mean_AD − mean_CN) / s_p`；所有组内 SD 为样本 SD（ddof=1）。"
        "`delta_d = d_syn − d_real`；`abs_d_difference = |d_syn| − |d_real|`。"
        "这不是 Real−Syn 配对差的 Cohen’s dz。单位为 normalized uptake（任意单位），不称 SUV/SUVR。",
        "",
        "下表均值±SD 保留5位，效应量保留6位；[CSV](figure4_effect_sizes.csv) 保留完整计算精度、"
        "合并SD和逐项来源信息。", "",
        "| 面板/示踪剂 | ROI ID / 解剖名 | N_AD/N_CN | Real AD 均值±SD | Real CN 均值±SD | Syn AD 均值±SD | Syn CN 均值±SD |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for r in frame.itertuples():
        cells = [f"{getattr(r, f'{m}_{g}_mean'):.5f}±{getattr(r, f'{m}_{g}_sd'):.5f}"
                 for m, g in [("real", "AD"), ("real", "CN"), ("syn", "AD"), ("syn", "CN")]]
        lines.append(f"| {r.panel}/{r.tracer} | {r.roi_id} {r.roi_name} | {r.N_AD}/{r.N_CN} | "
                     + " | ".join(cells) + " |")
    lines += ["", "| 面板/示踪剂 | ROI ID | d_real | d_syn | delta_d | abs_d_difference | 方向 | 绝对效应量 | R2-9 FDR分类 |",
              "|---|---:|---:|---:|---:|---:|---|---|---|"]
    for r in frame.itertuples():
        direction = "**反向（近零）**" if r.direction_reversed else "同向"
        lines.append(f"| {r.panel}/{r.tracer} | {r.roi_id} | {r.d_real:+.6f} | {r.d_syn:+.6f} | "
                     f"{r.delta_d:+.6f} | {r.abs_d_difference:+.6f} | {direction} | "
                     f"{'增加' if r.abs_d_difference > 0 else '减小'} | "
                     f"{ {'both_significant': '均显著', 'both_non_significant': '均不显著', 'real_only': '仅Real显著', 'syn_only': '仅Syn显著'}.get(r.r2_9_fdr_classification, '未定位')} |")
    lines += ["", "## 3. 方向、幅度及原稿表述", "",
              "C 中 AV45 五项均为 AD>CN，Real d=1.5133–1.6831、Syn d=1.5288–1.6437；"
              "D 中 FDG 五项均为 AD<CN，Real d=−1.3972 至 −0.4848、Syn d=−1.3201 至 −0.4308。"
              "C/D 十项有九项绝对效应量减小，仅 AV45 左横颞回略增（+0.0156）。"
              f"全部20项中{int((frame.abs_d_difference < 0).sum())}项绝对效应量减小、"
              f"{int((frame.abs_d_difference > 0).sum())}项增加。", "",
              "需要明确呈现的差异：", "",
              "- 最大绝对幅度变化：FDG 右侧峡部扣带回（2010），d −1.397180→−1.320097，"
              "|d| 减小0.077082（约5.5%）；左侧峡部扣带回（1010）−1.253072→−1.177431，"
              "减小0.075640（约6.0%）。",
              "- FDG 左缘上回（1031）−0.484757→−0.430784，|d| 减小0.053973（约11.1%），"
              "为 C/D 十项中相对减幅最大者。这里百分比仅描述幅度变化，没有统计或临床阈值含义。",
              "- **符号改变：**AV45 右海马（E/53）−0.006832→+0.000552；"
              "FDG 左丘脑（F/10）−0.009660→+0.058216。两处原始效应均接近零，"
              "不能据此认定疾病效应出现可靠反转。",
              "- E 中 AV45 Left/Right-VentralDC（28/60）的 Real/Syn 均 q≥0.05，"
              "与图面 ns 一致；原先侧脑室4/43不属于这些图示条目。",
              "",
              "**对 precisely preserved 的判断：**指定 CSV 的 C/D 大体保留组间方向及效应量级，"
              "但存在上述幅度差异；E/F 还有近零效应的符号改变。没有事先规定的效应量保持容许界值，"
              "不能把最大0.0771差值简单判为临床明显或临床可忽略，也不能将相近 d 或显著性保持"
              "解释成精确保持。若最终写入回复，证据支持较窄的“组间差异方向大体保持，并报告效应量变化”。"
              "本轮不修改原稿。", "",
              "## 4. R2-9新复算证据及与 R2-8/10 的关系", "",
              "初次核查时，本地 `reports/` 文件清单及当前 Git 树未找到 R2-9 Figure 4 FDR 审计文件。"
              "通过 GitHub 连接器只读核查了仓库 `linshuijin6/DIRECTPP` 的主分支 reports 目录、"
              "`Figure 4 FDR` / `r2_9` 文件检索、`R2-9` issue/commit 检索和分支发现；"
              "均未定位对应逐项结果。主分支核实为 "
              f"[`{GITHUB_COMMIT[:7]}`](https://github.com/linshuijin6/DIRECTPP/tree/{GITHUB_COMMIT}/reports)。"
              "这是本次可见范围内的未定位，不表示历史审计不存在；没有对全历史归档展开追查。",
              "",
              "随后按作者授权完成 [R2-9新复算](../r2_9_figure4_fdr/REPORT.md)："
              "双侧Student检验、AV45/FDG×Real/Syn四个独立98 ROI的BH族。"
              "本CSV的r2_9_*_p/q来自该392项全表，不是恢复的历史绘图值；图示子集没有重新校正。"
              "更正28/60后，C/D十个ROI的Real/Syn均显著，E/F十个ROI均不显著，40条二元分类全部与图面一致。"
              "其中FDG 2010、1010、1031均保留FDR显著性，但|d|分别减小0.0771、0.0756、0.0540；"
              "没有预设“较大变化”阈值，不作临床重要性判定。历史绘图检验身份及实际FDR流程仍未核实。",
              "",
              "[R2-8](../r2_8_original_roi_stats/REPORT.md) 的配对均值差、CCC、ICC、MAE、"
              "Bland–Altman 回答 Real/Syn 平均差异和个体一致性；其中配对 q 不属于 AD/CN 组间检验。"
              "[R2-10](../r2_10_normalized_calibration/REPORT.md) 是 A/B 的16项 overall OLS 回归，"
              "与本次 C–F 仅共享 AV45 左楔前叶（1025），不能直接扩展到其余区域或 AD/CN 分层。"
              "本次 d 补充疾病组间的标准化差异，不能替代一致性指标、临床 SUV/SUVR 校准或等效性分析。",
              "",
              "## 5. 未核实事项与复现", "",
              "未核实历史 C–F 绘图脚本、精确输入版本/受试者子集、图面 p/q 的实际生成与校正流程，"
              "以及参考区比值归一化。AD/CN 作为两个互斥受试者组计算；样本代表性、历史选择过程、"
              "独立性前提和等方差假设未新增检验。合并SD只是本次按要求定义 d 的分母，"
              "不证明等方差成立。所有 d 均为描述性点估计，没有置信区间或显著性结论。",
              "",
              "运行：`/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python reports/r3_5_effect_size/analyze.py`。"
              "脚本只写本目录 CSV/Markdown；GitHub 检索记录是本次会话已完成的只读核查，"
              "重跑脚本不会重新联网。受保护输入在运行前后核验 SHA-256。", "",
              "本次会话另以标准库 csv/statistics/math 独立重读20个源文件，以组内离均差平方和"
              "复算合并SD，核对全部80组均值/SD、40个 d 及40个差值，均一致；"
              "本地报告链接存在，新增p/q明确标记为R2-9新复算来源，输出目录仅含指定三个文件。", "",
              "本次读取的主要证据文件 SHA-256：", "",
              "| 文件 | SHA-256 |", "|---|---|"]
    for p in evidence_files():
        label = str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p)
        lines.append(f"| `{label}` | `{sha256(p)}` |")
    return "\n".join(lines) + "\n"


def evidence_files():
    return [ROOT / "manuscript/BMEF_main.tex", ROOT / "manuscript/figures/figure_4.pdf",
            R28 / "analyze.py", R28 / "REPORT.md", R28 / "input_audit.csv",
            R28 / "regional_paired_statistics.csv", R28 / "FIGURE4_SOURCE_CHECK.md",
            ROOT / "reports/r2_10_normalized_calibration/REPORT.md", LUT,
            ROOT / "reports/r2_9_figure4_fdr/all_392_student_fdr.csv"]


def main():
    protected = evidence_files() + [
        SOURCE / f"statistics_of_regions_{tracer.lower()}_adjust/region_{roi}.0.csv"
        for tracer, items in PANELS.values() for roi, _ in items]
    before = {p: sha256(p) for p in protected}
    frame = compute()
    content = report(frame)
    assert before == {p: sha256(p) for p in protected}
    frame.to_csv(OUT / "figure4_effect_sizes.csv", index=False, float_format="%.17g")
    (OUT / "REPORT.md").write_text(content)
    print(frame[["panel", "tracer", "roi_id", "N_AD", "N_CN", "d_real", "d_syn",
                 "delta_d", "abs_d_difference", "direction_reversed"]].to_string(index=False))
    print("20 ROIs / 40 annotations; protected input hashes unchanged; no p/q tests run.")


if __name__ == "__main__":
    main()
