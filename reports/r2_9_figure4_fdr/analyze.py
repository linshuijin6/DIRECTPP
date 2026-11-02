"""Recalculate 392 AD-CN Student tests and four separate 98-ROI BH families.

Only author-confirmed shuijin CSVs are eligible. Earlier R2-8, R2-10 and
R3-5 artifacts are read-only dependencies. This is a new audit calculation,
not recovery of historical p/q values or reproduction of the plotting code.
"""
from __future__ import annotations

import hashlib
import argparse
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
R28 = ROOT / "reports/r2_8_original_roi_stats"
R35 = ROOT / "reports/r3_5_effect_size"
SOURCE = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin"
LUT = Path("/mnt/nfsdata/nfsdata/linshuijin/freesurfer/FreeSurferColorLUT.txt")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def identity_hash(frame):
    records = sorted(map(tuple, frame[["subject", "Research Group"]].to_numpy()))
    return hashlib.sha256(json.dumps(records, ensure_ascii=False).encode()).hexdigest()


def load_reader():
    spec = importlib.util.spec_from_file_location("r28_readonly", R28 / "analyze.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load_roi


def calculate():
    load_roi = load_reader()
    old_audit = pd.read_csv(R28 / "input_audit.csv").set_index(["tracer", "roi_id"])
    names = {}
    for line in LUT.read_text().splitlines():
        fields = line.split()
        if len(fields) > 1 and fields[0].isdigit():
            names[int(fields[0])] = fields[1]
    rows = []
    for tracer in ("AV45", "FDG"):
        directory = SOURCE / f"statistics_of_regions_{tracer.lower()}_adjust"
        files = sorted(directory.glob("region_*.csv"), key=lambda p: int(p.stem.split('_')[1].split('.')[0]))
        expected = old_audit.loc[tracer]
        assert len(files) == len(expected) == 98
        assert {int(p.stem.split('_')[1].split('.')[0]) for p in files} == set(expected.index)
        baseline = None
        for path in files:
            assert SOURCE.resolve() in path.resolve().parents
            valid, audit, groups = load_roi(tracer, path)
            roi = int(audit["roi_id"])
            old = expected.loc[roi]
            assert path.resolve() == Path(old.input_file).resolve()
            assert audit["sha256"] == old.sha256
            for key in ("raw_rows", "valid_pairs", "excluded_rows", "blank_subject_rows", "duplicate_subject_rows"):
                assert audit[key] == old[key]
            if baseline is None:
                baseline = groups
            assert baseline == groups, "Original PTID/group mapping changed across ROIs"
            ad = valid.loc[valid["Research Group"] == "AD"]
            cn = valid.loc[valid["Research Group"] == "CN"]
            assert ad.subject.is_unique and cn.subject.is_unique
            assert not set(ad.subject) & set(cn.subject)
            assert min(len(ad), len(cn)) >= 2
            for mode in ("real", "syn"):
                a, c = ad[mode].to_numpy(), cn[mode].to_numpy()
                test = stats.ttest_ind(a, c, equal_var=True, alternative="two-sided", nan_policy="raise")
                assert np.isfinite(test.pvalue) and np.isfinite(test.statistic)
                pooled = np.sqrt(((len(a)-1)*np.var(a, ddof=1) + (len(c)-1)*np.var(c, ddof=1))
                                 / (len(a)+len(c)-2))
                manual_t = (np.mean(a)-np.mean(c)) / (pooled * np.sqrt(1/len(a)+1/len(c)))
                assert np.isclose(test.statistic, manual_t, rtol=1e-12, atol=1e-13)
                rows.append(dict(
                    tracer=tracer, modality=mode, roi_id=roi, roi_name=names[roi],
                    contrast="AD-CN", test="Student_independent_two_sided", equal_var=True,
                    N_AD=len(a), N_CN=len(c), mean_AD=np.mean(a), sd_AD=np.std(a, ddof=1),
                    mean_CN=np.mean(c), sd_CN=np.std(c, ddof=1), sd_pooled=pooled,
                    t_statistic=float(test.statistic), df=len(a)+len(c)-2,
                    raw_p=float(test.pvalue), family=f"{tracer}_{mode}_AD_vs_CN_98",
                    family_n_tests=98, subjects_AD_sha256=identity_hash(ad),
                    subjects_CN_sha256=identity_hash(cn),
                    source_file=str(path.relative_to(ROOT)), source_sha256=audit["sha256"],
                    raw_rows=audit["raw_rows"], valid_rows_all_groups=audit["valid_pairs"],
                    excluded_rows_all_groups=audit["excluded_rows"],
                    excluded_row_details=audit["excluded_row_details"],
                    result_origin="new_recalculation_not_historical_plot_values"))
    full = pd.DataFrame(rows)
    for _, family in full.groupby("family"):
        assert len(family) == 98
        full.loc[family.index, "bh_q"] = stats.false_discovery_control(family.raw_p.to_numpy(), method="bh")
    full["raw_p_lt_0_05"] = full.raw_p < 0.05
    full["bh_q_lt_0_05"] = full.bh_q < 0.05
    assert len(full) == 392 and full.family.nunique() == 4
    assert not full.duplicated(["tracer", "modality", "roi_id"]).any()
    full = full.sort_values(["tracer", "modality", "roi_id"]).reset_index(drop=True)
    return full


def select_figure(full):
    # Select after correction: Figure 4's 40 rows never form a new FDR family.
    effects = pd.read_csv(R35 / "figure4_effect_sizes.csv")
    assert len(effects) == 20
    selected = full.merge(effects[["tracer", "roi_id", "panel", "panel_order", "figure_label",
                                  "figure_real_annotation", "figure_syn_annotation", "d_real", "d_syn",
                                  "delta_d", "abs_d_difference", "direction_reversed"]],
                          on=["tracer", "roi_id"], how="inner", validate="many_to_one")
    assert len(selected) == 40
    effect_index = effects.set_index(["tracer", "roi_id"])
    for r in selected.itertuples():
        e = effect_index.loc[(r.tracer, r.roi_id)]
        assert e.roi_name == r.roi_name and e.source_sha256 == r.source_sha256
        for group in ("AD", "CN"):
            assert e[f"N_{group}"] == getattr(r, f"N_{group}")
            assert e[f"subjects_{group}_sha256"] == getattr(r, f"subjects_{group}_sha256")
        figure_d = r.t_statistic * np.sqrt(1/r.N_AD + 1/r.N_CN)
        assert np.isclose(getattr(r, f"d_{r.modality}"), figure_d, rtol=1e-11, atol=1e-13)
    selected["figure_annotation"] = np.where(selected.modality == "real",
                                               selected.figure_real_annotation, selected.figure_syn_annotation)
    selected["figure_indicates_significant"] = selected.panel.isin(["C", "D"])
    selected["raw_binary_matches_figure"] = selected.raw_p_lt_0_05 == selected.figure_indicates_significant
    selected["fdr_binary_matches_figure"] = selected.bh_q_lt_0_05 == selected.figure_indicates_significant
    selected["historical_plot_workflow"] = "not_fully_reproduced"
    selected = selected.sort_values(["panel", "panel_order", "modality"]).reset_index(drop=True)
    return selected


def make_report(full, selected, full_sha256):
    mismatch = selected.loc[~selected.fdr_binary_matches_figure]
    both = selected.groupby(["panel", "tracer", "roi_id"]).bh_q_lt_0_05.all()
    lines = ["# R2-9：Student 检验与 Figure 4C–F 的 FDR 核验", "",
             f"按当前授权新复算392项 AD/CN Student 检验，分为4个各98项的 BH-FDR 族。"
             f"图示40条结果中，{40-len(mismatch)}条与原图的显著/不显著分类一致，"
             f"{len(mismatch)}条不一致。**历史绘图程序尚未完全复现；本次 p/q 是新复算值，"
             "不是已恢复的历史绘图 p/q。**", "",
             "**映射更正与结论撤回：**E 前两项是 Left-VentralDC（28）与 Right-VentralDC（60），"
             "作者指出后已放大原图并核对LUT。旧版沿用R2-8误认成侧脑室4/43，"
             "因此旧版“4条不一致”结论撤回。更正后C/D的20条均显著、E/F的20条均不显著，"
             "40条二元分类全部与图面一致。完整392项表本已包含28/60，本次仅更正图示选择，"
             "该完整文件逐字节不变；没有重跑检验或FDR校正。", "",
             "## 本地旧结果检查", "",
             "2026-11-02 检查 Git 未提交文件、`reports/` 与 `scripts/` 的文件名和脚本/报告内容；"
             "在这两个目录包含隐藏和被忽略文件，按 R2-9、FDR、Figure 4、392项与 equal_var=True "
             "定向检索。另按相关文件名补查 `appendix/legacy_only/8_revision_evidence/`。"
             "未找到 R2-9 专用报告、脚本或392项结果，仅命中审稿要求、R2-8 来源核验和上一轮 R3-5 文件。"
             "这是上述范围内未定位，并非已证明全盘不存在；未做全仓库历史扫描。", "",
             "因此此前按用户授权执行补算；本次ROI映射更正复用该完整结果。"
             "R3-5现已同步更正28/60并挂接新复算p/q。", "",
             "## 数据与统计口径", "",
             "仅使用作者确认的两个目录：", "",
             "- `source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/statistics_of_regions_av45_adjust/`",
             "- `source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/statistics_of_regions_fdg_adjust/`", "",
             "每种示踪剂恰好98个 ROI 文件；文件集合、SHA-256、有效行数及排除数均与 R2-8 "
             "`input_audit.csv` 一致。外层同名 abandon 目录未读取。复用 R2-8 的只读 `load_roi()` "
             "边界：空/重复 PTID 或 Real/Syn 任一测量非有限则整行排除；保留原始 `Research Group` "
             "和 PTID，只取精确 AD/CN 标签。每个 ROI 的 Real/Syn 使用同一有效受试者集合，"
             "不同 ROI 保留各自有效人数，不取跨 ROI 交集，不重新归一化、裁剪、插补或混组。", "",
             "`scipy.stats.ttest_ind(AD, CN, equal_var=True, alternative='two-sided')`；"
             "方向为 AD−CN，df=N_AD+N_CN−2。采用样本量加权合并样本方差的 Student 检验；"
             "没有根据结果选择 Student/Welch，也未以方差检验决定方法。", "",
             "四个独立比较族为 AV45×Real、AV45×Syn、FDG×Real、FDG×Syn，各含全部98 ROI 的"
             "原始双侧 p。每族单独做 Benjamini–Hochberg 校正，显著阈值 q<0.05；"
             "没有合并成392项一族，也没有在图示40条或各面板内重新校正。", "",
             "[完整392项](all_392_student_fdr.csv) 保留检验身份、p/q、人数、均值/SD、t/df、"
             "来源哈希、组别身份集合哈希及排除明细。"
             "[图示40条](figure4_cf_40_verification.csv) 从已校正全表筛出，继承其原始 p/q "
             "与98项 family，并加入图面标注、二元核验结论和已有 R3-5 效应量。", "",
             "## 四个98项比较族", "",
             "| 比较族 | 检验数 | p<0.05 | q<0.05 |", "|---|---:|---:|---:|"]
    for key, group in full.groupby("family"):
        lines.append(f"| {key} | {len(group)} | {int(group.raw_p_lt_0_05.sum())} | {int(group.bh_q_lt_0_05.sum())} |")
    lines += ["", "## Figure 4C–F 全部40条核验", "",
              "ROI ID、名称、tracer 和图面顺序沿用已核验的 [R3-5 映射](../r3_5_effect_size/REPORT.md)，"
              "并逐项与同一源文件哈希、AD/CN人数和PTID/组别集合核对。C/E=AV45，D/F=FDG；"
              "C/D 的 Real/Syn 均标 `****`，E/F 均标 `ns`。下表只核对显著/不显著二元分类；"
              "未确认原绘图程序的星号阈值，故不声称复现了四星级别。", "",
              "| 面板/示踪剂 | ROI ID / 解剖名 | PET | N_AD/N_CN | 原图 | Student p | BH q（98 ROI） | q<0.05 | 与图二元一致 |",
              "|---|---|---|---:|---|---:|---:|---|---|"]
    for r in selected.itertuples():
        lines.append(f"| {r.panel}/{r.tracer} | {r.roi_id} {r.roi_name} | {r.modality} | "
                     f"{r.N_AD}/{r.N_CN} | {r.figure_annotation} | {r.raw_p:.8g} | {r.bh_q:.8g} | "
                     f"{'是' if r.bh_q_lt_0_05 else '否'} | {'是' if r.fdr_binary_matches_figure else '**否**'} |")
    lines += ["", "## 与 R3-5 效应量合看", "",
              f"图示20个 tracer×ROI 中，{int(both.sum())}个在 Real/Syn 中均 q<0.05。"
              "以下按 |d_syn|−|d_real| 的绝对值列出其中幅度变化最大的三项，"
              "仅为描述排序，不设置事后“较大”或临床容许阈值：", "",
              "| 面板/示踪剂 | ROI ID / 解剖名 | d_real | d_syn | abs_d_difference |",
              "|---|---|---:|---:|---:|"]
    pairs = selected.loc[selected.modality == "real"].copy()
    keys = {(tr, roi) for (panel, tr, roi), flag in both.items() if flag}
    kept = pairs.loc[[(r.tracer, r.roi_id) in keys for r in pairs.itertuples()]].copy()
    kept["magnitude_change"] = kept.abs_d_difference.abs()
    for r in kept.sort_values("magnitude_change", ascending=False).head(3).itertuples():
        lines.append(f"| {r.panel}/{r.tracer} | {r.roi_id} {r.roi_name} | {r.d_real:+.6f} | "
                     f"{r.d_syn:+.6f} | {r.abs_d_difference:+.6f} |")
    lines += ["",
              "AV45 右海马（53）与 FDG 左丘脑（10）的效应量符号改变均发生在近零效应；"
              "其 Real/Syn 各自的 p/q 见完整核验表。显著性保持不能证明效应量精确保持，"
              "非显著也不证明等效。原稿 precisely preserved 的宽泛表述仍缺少足够支持。", "",
              "## 历史流程与解释边界", "",
              "**历史绘图程序尚未完全复现。**尚未确定 C–F 的精确脚本、实际输入版本、受试者子集、"
              "星号规则及原图是否实际使用 FDR。新计算与图面不一致只说明：在当前确认的 CSV "
              "和固定 Student/98项BH口径下不能复现相应图示分类；不据此认定某个历史绘图环节的根因。"
              "同样，分类一致也不能证明历史实际做过 FDR。", "",
              "这里分析 normalized uptake（任意单位），参考区归一化与 SUV/SUVR 标定仍未核实。"
              "组内分布、等方差和样本代表性没有新增检验；equal_var=True 是本次固定分析口径，"
              "不意味着等方差已得到证实。R2-8 的 Real/Syn配对 q 与这里的 AD/CN独立组 q 不混用。", "",
              "## 复现与完整性", "",
              "运行：`/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python reports/r2_9_figure4_fdr/analyze.py`。"
              f"环境版本：NumPy {np.__version__}、pandas {pd.__version__}、SciPy {scipy.__version__}。"
              "仅写本目录的两个CSV和本报告；不修改原始CSV、稿件、图件、既有 R2-8/10 或 R3-5 文件，"
              "不启动训练/推理，不操作 Notion，不提交或推送 Git。", "",
              "首次补算对全部392个 t 值作合并SD公式核对，并对196个源文件及依赖文件做运行前后哈希检查。"
              "另以标准库csv逐源行独立重读、离均差平方和和t分布尾概率复核392项 p，"
              "以排序/反向累计最小值独立核对四族全部392项 q。本次使用 `--refresh-figure4` "
              "仅重选40条、更新本报告，完整392项文件SHA-256保持不变。", "",
              "| 关键只读依赖 | SHA-256 |", "|---|---|"]
    for p in [R28 / "analyze.py", R28 / "input_audit.csv", R35 / "figure4_effect_sizes.csv",
              ROOT / "manuscript/figures/figure_4.pdf", ROOT / "manuscript/BMEF_main.tex"]:
        lines.append(f"| `{p.relative_to(ROOT)}` | `{digest(p)}` |")
    lines.append(f"| `reports/r2_9_figure4_fdr/all_392_student_fdr.csv` | `{full_sha256}` |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--refresh-figure4", action="store_true",
                        help="Use existing 392-row results; do not run tests or overwrite that CSV")
    args = parser.parse_args()
    protected = [p for d in [R28, R35, ROOT / "reports/r2_10_normalized_calibration"]
                 for p in d.rglob("*") if p.is_file()]
    protected += [p for t in ("av45", "fdg")
                  for p in (SOURCE / f"statistics_of_regions_{t}_adjust").glob("region_*.csv")]
    protected += [ROOT / "manuscript/BMEF_main.tex", ROOT / "manuscript/figures/figure_4.pdf", LUT]
    before = {p: digest(p) for p in protected}
    full_path = OUT / "all_392_student_fdr.csv"
    if args.refresh_figure4:
        protected.append(full_path)
        before[full_path] = digest(full_path)
        full = pd.read_csv(full_path, float_precision="round_trip")
        assert len(full) == 392 and full.groupby(["tracer", "modality"]).size().eq(98).all()
        assert full.family_n_tests.eq(98).all() and full.equal_var.all()
        assert full.test.eq("Student_independent_two_sided").all()
        for source_file, block in full.groupby("source_file"):
            assert block.source_sha256.nunique() == 1
            assert digest(ROOT / source_file) == block.source_sha256.iloc[0]
    else:
        full = calculate()
    selected = select_figure(full)
    full_sha256 = (digest(full_path) if args.refresh_figure4 else hashlib.sha256(
        full.to_csv(index=False, float_format="%.17g").encode()).hexdigest())
    content = make_report(full, selected, full_sha256)
    assert before == {p: digest(p) for p in protected}, "A protected input changed"
    if not args.refresh_figure4:
        full.to_csv(full_path, index=False, float_format="%.17g")
    selected.to_csv(OUT / "figure4_cf_40_verification.csv", index=False, float_format="%.17g")
    (OUT / "REPORT.md").write_text(content)
    print(full.groupby("family").agg(n_tests=("raw_p", "size"), raw_sig=("raw_p_lt_0_05", "sum"),
                                     fdr_sig=("bh_q_lt_0_05", "sum")).to_string())
    print("Figure binary mismatches:")
    print(selected.loc[~selected.fdr_binary_matches_figure,
                       ["panel", "tracer", "roi_id", "modality", "raw_p", "bh_q"]].to_string(index=False))
    print("392 tests / four 98-ROI families / 40 figure entries; protected hashes unchanged.")


if __name__ == "__main__":
    main()
