"""Assemble auditable stage-0 evidence and the final stage-1 acceptance report."""
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import pandas as pd

from common import ROOT, SCORES, TRACERS, load_config, sha, write_json


def freeze(out):
    """Keep scientific failures; do not silently exclude subjects or swap labels."""
    cfg=load_config(out/"config.json")
    records=[json.loads(line) for line in (out/"preprocessing_progress.jsonl").read_text().splitlines()]
    qc={r["ptid"]:r for r in records}
    candidates=json.loads((out/"cohort_candidate.json").read_text())
    if set(qc)!={r["ptid"] for r in candidates}:
        raise RuntimeError("Full input/cache inspection has not finished")
    hashes=pd.read_csv(out/"input_hashes.csv")
    if (out/"additional_input_hashes.json").exists():
        hashes=pd.concat([hashes,pd.DataFrame(json.loads((out/"additional_input_hashes.json").read_text()))],ignore_index=True).drop_duplicates(["ptid","kind"],keep="last")
    hashes.to_csv(out/"input_hashes_final.csv",index=False)
    for row in candidates:
        q=qc[row["ptid"]]
        for key in ["has_fdg","has_av45","cache","cache_sha256"]:row[key]=q[key]
        row["mri_mask_grid_pass"]=q["saved_mri_replay_maxabs"]<=2e-6
        row["anatomical_laterality_pass"]=q["left_right_anatomy_pass"]
    write_json(out/"cohort.json",candidates)
    pd.DataFrame([{k:v for k,v in r.items() if k not in ["full","no_scores"]} for r in candidates]).to_csv(out/"cohort.csv",index=False)
    cfg["evaluation_laterality_gate_pass"]=all(r["anatomical_laterality_pass"] for r in candidates)
    cfg["evaluation_mri_mask_gate_pass"]=all(r["mri_mask_grid_pass"] for r in candidates)
    cfg["formal_training_authorized"]=False
    cfg["frozen_files"].update({str(out/f):sha(out/f) for f in ["cohort.json","cohort_candidate.json","roi_labels.csv","tracer_texts.json","score_sources.csv","input_hashes_final.csv"]})
    write_json(out/"config.json",cfg)
    write_json(out/"geometry_qc_final.json",sorted(qc.values(),key=lambda r:r["ptid"]))
    elapsed=[float(line.rsplit("elapsed ",1)[1]) for line in (out/"preprocessing.log").read_text().splitlines() if "elapsed " in line]
    write_json(out/"stage0_receipt.json",dict(subjects=len(candidates),
        effective_fdg=sum(r["has_fdg"] for r in candidates),effective_av45=sum(r["has_av45"] for r in candidates),
        folds={str(f):dict(test=sum(r["test_fold"]==f for r in candidates),train=sum(r["test_fold"]!=f for r in candidates),
            test_fdg=sum(r["test_fold"]==f and r["has_fdg"] for r in candidates),
            test_av45=sum(r["test_fold"]==f and r["has_av45"] for r in candidates)) for f in [1,2]},
        laterality_pass_subjects=sum(r["anatomical_laterality_pass"] for r in candidates),
        mask_binding_failed=[r["ptid"] for r in candidates if not r["mri_mask_grid_pass"]],
        max_replay_error_among_bound=max(q["saved_mri_replay_maxabs"] for q in qc.values() if q["saved_mri_replay_maxabs"]<=2e-6),
        cache_bytes=sum(q["cache_bytes"] for q in qc.values()),
        preprocessing_wall_seconds_lower_bound=max(elapsed) if elapsed else None,
        evaluation_status="NO_GO" if not (cfg["evaluation_laterality_gate_pass"] and cfg["evaluation_mri_mask_gate_pass"]) else "PASS",
        unit="normalized uptake (arbitrary units)",
        cohort_status="Frozen stage-01 inputs; scientific ROI gates retained as failures, not repaired or silently excluded"))
    print("Frozen input cohort; evaluation gates",cfg["evaluation_laterality_gate_pass"],cfg["evaluation_mri_mask_gate_pass"],flush=True)


def qc_exclude(out):
    """Apply the pre-frozen MRI/mask binding QC rule as an explicit, auditable exclusion.

    cohort.json and the split stay byte-identical; excluded subjects are listed in
    qc_exclusions.json and filtered by common.active_rows for adapt/train/infer/evaluate.
    """
    import shutil
    cfg=load_config(out/"config.json");rows=json.loads((out/"cohort.json").read_text())
    if "qc_exclusions" in cfg:raise RuntimeError("QC exclusion already applied")
    shutil.copyfile(out/"config.json",out/"config.before_qc_exclusion.json")
    geo={r["ptid"]:r for r in json.loads((out/"geometry_qc_final.json").read_text())}
    failed=[r for r in rows if not r["mri_mask_grid_pass"]]
    excluded=[dict(ptid=r["ptid"],diagnosis=r["diagnosis"],test_fold=r["test_fold"],has_fdg=r["has_fdg"],has_av45=r["has_av45"],
        saved_mri_replay_maxabs=geo[r["ptid"]].get("saved_mri_replay_maxabs"),
        reason="MRI replay does not bind historical MRI/mask grid; eight axis-flip probes also failed",
        evidence=["preprocessing_errors.json","016_S_4952_mri_only_orientation_probe.json","geometry_qc_final.json"]) for r in failed]
    write_json(out/"qc_exclusions.json",dict(
        rule="Pre-specified stage-0 QC: mri_mask_grid_pass==False (saved MRI replay maxabs > 2e-6) -> exclude from adapter fitting, generator training, OOF inference and all evaluation",
        decided_by="author instruction 2026-10-17: exclude per pre-specified QC rule",
        selection_independent_of_performance=True,no_resplit=True,cohort_json_unchanged=True,excluded=excluded))
    active=[r for r in rows if r["mri_mask_grid_pass"]]
    cfg["qc_exclusions"]=str(out/"qc_exclusions.json")
    cfg["frozen_files"][str(out/"qc_exclusions.json")]=sha(out/"qc_exclusions.json")
    cfg["evaluation_mri_mask_gate_pass"]=all(r["mri_mask_grid_pass"] for r in active)
    cfg["evaluation_laterality_gate_pass"]=all(r["anatomical_laterality_pass"] for r in active)
    cfg["adapter_subdir"]="qc_exclusion_20261017"
    cfg["formal_training_authorized"]=False
    write_json(out/"config.json",cfg)
    write_json(out/"qc_revision_receipt.json",dict(subjects_before=len(rows),subjects_active=len(active),
        excluded=[e["ptid"] for e in excluded],
        effective_fdg=sum(r["has_fdg"] for r in active),effective_av45=sum(r["has_av45"] for r in active),
        folds={str(f):dict(test=sum(r["test_fold"]==f for r in active),train=sum(r["test_fold"]!=f for r in active),
            test_fdg=sum(r["test_fold"]==f and r["has_fdg"] for r in active),
            test_av45=sum(r["test_fold"]==f and r["has_av45"] for r in active)) for f in [1,2]},
        diagnoses_by_test_fold={str(f):pd.Series([r["diagnosis"] for r in active if r["test_fold"]==f]).value_counts().to_dict() for f in [1,2]},
        mri_mask_gate_pass=cfg["evaluation_mri_mask_gate_pass"],laterality_gate_pass=cfg["evaluation_laterality_gate_pass"],
        adapter_refit_required="stage-1 adapters included the excluded subject (fold-2 training side, fold-1 outer test); refit into conditions/qc_exclusion_20261017, originals preserved",
        config_backup="config.before_qc_exclusion.json"))
    print("QC exclusion applied:",[e["ptid"] for e in excluded],"active",len(active),flush=True)


def laterality_fix(out):
    """Resolve the ROI laterality gate with a documented, global hemisphere-name mapping.

    Root cause (reports/e1_laterality_rootcause_20261017/CORRECTION.md): the historical
    pipeline loaded NIfTI arrays without headers. Raw registered MRIs are stored LAS,
    so the saved identity-header MRI fed to the segmenter is x-mirrored relative to
    its header; the segmenter's left/right names are therefore anatomically swapped
    for every subject. The cached affine (ref.affine @ proc.affine) is the correct
    index->world map (verified by resampling raw MRI) and is kept unchanged.
    Masks and caches are not modified; only the label->physical-hemisphere mapping
    is frozen for reporting. Gate: every subject shows the same mirror on four large
    bilateral pairs. ROI validity is PET-independent: label invalid for a subject when
    voxel count < 10% of the cohort median for that label.
    """
    import shutil
    from concurrent.futures import ThreadPoolExecutor
    from common import active_rows
    cfg=load_config(out/"config.json")
    if "hemisphere_label_map" in cfg:raise RuntimeError("Laterality mapping already applied")
    shutil.copyfile(out/"config.json",out/"config.before_laterality_fix.json")
    rows=active_rows(cfg,json.loads((out/"cohort.json").read_text()))
    geo={r["ptid"]:r for r in json.loads((out/"geometry_qc_final.json").read_text())}
    labels=pd.read_csv(out/"roi_labels.csv")
    gate_pairs=[(2,41),(12,51),(4,43),(10,49)];info_pairs=[(17,53),(18,54),(1025,2025)]
    def one(r):
        import nibabel as nib
        m=np.flip(np.rint(nib.load(r["mask"]).get_fdata(dtype=np.float32)).astype(np.int16),(0,1,2))
        counts=np.bincount(m.ravel().astype(np.int64),minlength=2036)
        aff=np.asarray(geo[r["ptid"]]["affine"]);res={}
        for a,b in gate_pairs+info_pairs:
            if not counts[a] or not counts[b]:res[f"{a}_{b}"]=None;continue
            xa=(aff@np.r_[np.argwhere(m==a).mean(0),1.])[0];xb=(aff@np.r_[np.argwhere(m==b).mean(0),1.])[0]
            res[f"{a}_{b}"]=dict(x_named_left=float(xa),x_named_right=float(xb),mirrored=bool(xa>xb))
        return r["ptid"],counts,res
    with ThreadPoolExecutor(8) as ex:results=list(ex.map(one,rows))
    median={int(l):float(np.median([c[l] for _,c,_ in results])) for l in labels.region}
    invalid={sid:[int(l) for l in labels.region if c[l]<0.1*median[int(l)]] for sid,c,_ in results}
    records=[]
    for sid,_,res in results:
        gate=[res[f"{a}_{b}"] for a,b in gate_pairs]
        ok=all(g is not None and g["mirrored"] for g in gate)
        records.append(dict(ptid=sid,consistent_global_mirror=ok,pairs=res,invalid_rois=invalid[sid]))
    def physical(name):
        for a,b in [("ctx-lh-","ctx-rh-"),("Left-","Right-")]:
            if name.startswith(a):return "right",b+name[len(a):]
            if name.startswith(b):return "left",a+name[len(b):]
        return "midline",name
    name_col=next(c for c in labels.columns if c!="region")
    hmap={int(r["region"]):dict(segmenter_name=r[name_col],physical_hemisphere=physical(r[name_col])[0],
        physical_name=physical(r[name_col])[1]) for r in labels.to_dict("records")}
    write_json(out/"hemisphere_label_map.json",dict(rule="segmenter left/right names are anatomically swapped for all subjects; report physical_name",
        evidence=["reports/e1_laterality_rootcause_20261017/CORRECTION.md","laterality_qc.json"],labels=hmap))
    write_json(out/"roi_validity.json",dict(rule="label invalid for subject if voxel count < 10% of cohort median (PET-independent); excluded from that subject's ROI set",
        cohort_median_voxels=median,invalid_rois={k:v for k,v in invalid.items() if v}))
    write_json(out/"laterality_qc.json",records)
    npass=sum(r["consistent_global_mirror"] for r in records)
    def tally(a,b):
        v=[r["pairs"][f"{a}_{b}"] for r in records]
        return dict(mirrored=sum(x is not None and x["mirrored"] for x in v),not_mirrored=sum(x is not None and not x["mirrored"] for x in v),
                    untested=sum(x is None for x in v))
    for f in ["hemisphere_label_map.json","roi_validity.json","laterality_qc.json"]:cfg["frozen_files"][str(out/f)]=sha(out/f)
    cfg["hemisphere_label_map"]=str(out/"hemisphere_label_map.json");cfg["roi_validity"]=str(out/"roi_validity.json")
    cfg["evaluation_laterality_gate_pass"]=npass==len(records)
    cfg["formal_training_authorized"]=False
    write_json(out/"config.json",cfg)
    write_json(out/"laterality_fix_receipt.json",dict(subjects=len(records),consistent_global_mirror=npass,
        inconsistent=[r["ptid"] for r in records if not r["consistent_global_mirror"]],
        gate_pairs={f"{a}_{b}":tally(a,b) for a,b in gate_pairs},informative_pairs={f"{a}_{b}":tally(a,b) for a,b in info_pairs},
        subjects_with_invalid_rois=sum(bool(v) for v in invalid.values()),invalid_roi_cells=sum(map(len,invalid.values())),
        caches_and_masks_modified=False,gate_pass=cfg["evaluation_laterality_gate_pass"],config_backup="config.before_laterality_fix.json"))
    print("Laterality: consistent global mirror",npass,"/",len(records),flush=True)


def source_receipt(out):
    src=pd.read_csv(out/"score_sources.csv");meta=pd.read_csv(out/"metadata.csv").set_index("Subject ID")
    filled=pd.read_csv(out/"filled.csv").set_index("Subject ID")
    equal={field:bool(np.array_equal(meta[field].sort_index().to_numpy(),filled[field].sort_index().to_numpy())) for field in SCORES}
    assert all(equal.values())
    disagreements=src[src.observed_value.notna() & (src.observed_value!=src.conditioning_value)]
    disagreements.to_csv(out/"observed_vs_conditioning_disagreements.csv",index=False)
    summary=src.groupby(["field","origin"]).size().reset_index(name="count")
    summary.to_csv(out/"score_source_counts.csv",index=False)
    scope=json.loads((out/"source_scope.json").read_text())
    write_json(out/"clinical_source_receipt.json",dict(
        scanned_notebooks=len(scope["scanned"]),scan_failures=scope["failures"],
        actual_full_template_exact_matches=1857,filled_table_numeric_match=equal,
        observed_conditioning_disagreements=len(disagreements),
        confirmed_imputed_cells=None,confirmed_diagnosis_derived_cells=None,
        current_pipeline_direct_target_pet_in_patient_prompt=False,
        upstream_filling_method="not recovered in bounded source scope",
        upstream_target_pet_dependency="not established; unknown is not proof of absence",
        upstream_cross_fold_fit="not established; pre-existing fixed values preserved, no new global imputer fitted",
        diagnosis_dependency="not confirmed; research-group-specific random statistics code is not bound to the patient table",
        training_scope_gate="LIMITED_HISTORICAL_FIELDS",
        confirmed_adverse_dependency_found=False,
        adverse_dependency_search_scope="bounded recovered-source audit; False means no confirmed finding, not proven absence",
        allowed_interpretation="Incremental contribution of historical conditioning fields; not authentic observed-score benefit or exclusion of shortcuts",
        clinical_visit_alignment="unverified; EXAMDATE/VISCODE absent"))


def io_benchmark(out):
    import socket
    cfg=load_config(out/"config.json");rows=json.loads((out/"cohort.json").read_text())
    selected=[]
    for pattern in [(True,True),(True,False),(False,True)]:
        selected += [r for r in rows if r["test_fold"]!=1 and
                     (r["has_fdg"],r["has_av45"])==pattern][-2:]
    times=[]
    for repeat in range(3):
        for r in selected:
            tick=time.monotonic()
            with np.load(r["cache"]) as z:
                arrays=[z[k].copy() for k in ["mri","fdg","av45"]]
                assert all(a.shape==(160,192,160) for a in arrays)
            times.append(dict(ptid=r["ptid"],repeat=repeat,seconds=time.monotonic()-tick))
    first=[r["seconds"] for r in times if r["repeat"]==0];warm=[r["seconds"] for r in times if r["repeat"]>0]
    write_json(out/"io_benchmark.json",dict(host=socket.gethostname(),selected_train_fold=1,
        selected_ptids=[r["ptid"] for r in selected],measurements=times,
        first_pass_mean_seconds=float(np.mean(first)),warm_mean_seconds=float(np.mean(warm)),
        mean_seconds=float(max(np.mean(first),np.mean(warm))),
        cache_status="OS/NFS caches uncontrolled; first pass is not guaranteed cold; no global cache dropping",
        contents="three float32 volumes per subject, copied into CPU memory; no test performance computed"))


def figures(out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cfg=load_config(out/"config.json");rows=json.loads((out/"cohort.json").read_text())
    choices=[]
    for fold in [1,2]:
        for r in [x for x in rows if x["test_fold"]==fold and x["has_fdg"] and x["has_av45"]][:2]:choices.append(r)
    choices += [r for r in rows if not r["mri_mask_grid_pass"]][:2]
    fig,axes=plt.subplots(len(choices),3,figsize=(13,4*len(choices)),squeeze=False)
    coords=[]
    for j,r in enumerate(choices):
        with np.load(r["cache"]) as z:
            mri=z["mri"];mask=z["mask"];aff=z["affine"]
            pos=np.argwhere((mask==17)|(mask==53));k=int(np.median(pos[:,2]))
            for i,key in enumerate(["mri","fdg","av45"]):
                ax=axes[j,i];ax.imshow(mri[:,:,k].T,origin="lower",cmap="gray",vmin=0,vmax=1)
                if key!="mri":ax.imshow(z[key][:,:,k].T,origin="lower",cmap="magma",vmin=0,vmax=1,alpha=.35)
                ax.contour((mask[:,:,k]==17).T,levels=[.5],colors=["red"],linewidths=.6)
                ax.contour((mask[:,:,k]==53).T,levels=[.5],colors=["cyan"],linewidths=.6)
                ax.set_title(f"{r['ptid']} fold {r['test_fold']} {key}\nmask binding={r['mri_mask_grid_pass']}")
                ax.set_xlabel("image index x; increases toward physical Right")
                ax.set_ylabel("image index y; increases toward physical Posterior")
            for label in [17,53]:
                c=np.argwhere(mask==label).mean(0);world=np.asarray(aff)@np.r_[c,1.]
                coords.append(dict(ptid=r["ptid"],label=label,world_x=float(world[0]),world_y=float(world[1]),world_z=float(world[2])))
    fig.suptitle("E1 fixed-grid QC: label 17=red (nominal Left); label 53=cyan (nominal Right).\nLaterality FAIL retained; overlays do not establish quantitative PET validity.",fontsize=12)
    fig.tight_layout(rect=(0,0,1,.96));fig.savefig(out/"spatial_qc.png",dpi=140);fig.savefig(out/"spatial_qc.pdf");plt.close(fig)
    pd.DataFrame(coords).to_csv(out/"spatial_qc_landmarks.csv",index=False)


def report(out):
    from common import active_rows
    cfg=load_config(out/"config.json");all_rows=json.loads((out/"cohort.json").read_text());rows=active_rows(cfg,all_rows)
    stage0=json.loads((out/"stage0_receipt.json").read_text())
    qcrev=json.loads((out/"qc_revision_receipt.json").read_text())
    lat=json.loads((out/"laterality_fix_receipt.json").read_text())
    probe=json.loads((out/"full_fold_cache_probe.json").read_text())
    pilots=json.loads((out/"pilot_receipts.json").read_text())
    features=json.loads((Path(cfg["assets"])/"pet_features/receipt.json").read_text())
    adapters={f:json.loads((Path(cfg["assets"])/"conditions"/cfg["adapter_subdir"]/f"adapter_fold{f}.json").read_text()) for f in [1,2]}
    for f,ad in adapters.items():
        test={r["ptid"] for r in rows if r["test_fold"]==f}
        assert set(ad["outer_test_ptids"])==test and all(test.isdisjoint(v) for v in ad["fit_ptids"].values())
    budget=[]
    for p in pilots:
        by_pattern={}
        for pattern in [(True,True),(True,False),(False,True)]:
            count=sum(r["test_fold"]!=p["fold"] and (r["has_fdg"],r["has_av45"])==pattern for r in rows)
            random=[x["seconds"] for x in p["trace"][6:] if (x["has_fdg"],x["has_av45"])==pattern and x["timestep"]!=0]
            endpoint=[x["seconds"] for x in p["trace"][6:] if (x["has_fdg"],x["has_av45"])==pattern and x["timestep"]==0]
            sec=count*(140*np.mean(random)+25*np.mean(endpoint))
            by_pattern[str(pattern)]=dict(train_subjects=count,random_step_seconds=float(np.mean(random)),
                endpoint_step_seconds=float(np.mean(endpoint)),gpu_hours=float(sec/3600))
        budget.append(dict(fold=p["fold"],condition=p["condition"],patterns=by_pattern,
                           training_gpu_hours=sum(x["gpu_hours"] for x in by_pattern.values())))
    pure=sum(x["training_gpu_hours"] for x in budget)
    infer_per_volume=float(np.mean([x["seconds"] for p in pilots for x in p["inference"]]))
    nvol=qcrev["effective_fdg"]+qcrev["effective_av45"]
    infer_hours=2*nvol*infer_per_volume/3600
    io=json.loads((out/"io_benchmark.json").read_text())
    preload_hours=4*probe["wall_seconds"]/3600
    streaming_io_low=2*len(rows)*cfg["epochs"]*io["warm_mean_seconds"]/3600
    streaming_io_high=2*len(rows)*cfg["epochs"]*io["first_pass_mean_seconds"]/3600
    feature_hours=features["wall_seconds"]/3600
    base=pure+infer_hours+preload_hours
    low,high=base*1.2,base*1.3
    peak=max(p["peak_reserved_bytes"] for p in pilots)
    rss_gib=probe["peak_rss_bytes"]/1024**3
    write_json(out/"measured_budget.json",dict(hardware=pilots[0]["hardware"],fits=budget,pure_training_gpu_hours=pure,
        fold_cache_preload_seconds_measured=probe["wall_seconds"],fold_cache_peak_rss_bytes_measured=probe["peak_rss_bytes"],
        fold_cache_preload_hours_four_fits=preload_hours,inference_seconds_per_tracer_volume=infer_per_volume,
        training_cache_mode=cfg["training_cache_mode"],training_host_ram_budget_gib=cfg["training_cache_budget_gib"],
        streaming_read_hours_warm_scenario=streaming_io_low,streaming_read_hours_first_pass_scenario=streaming_io_high,
        two_condition_network_inference_gpu_hours=infer_hours,feature_extraction_measured_gpu_hours=feature_hours,
        budget_scope="new stage-2 allocation for 1856 active subjects; stage-1 feature cache excluded",
        planned_total_gpu_hours_low=low,planned_total_gpu_hours_high=high,
        calendar_days_single_gpu=[low/24,high/24],calendar_days_two_equivalent_gpus=[low/48,high/48],
        peak_reserved_bytes=peak,cache_bytes=stage0["cache_bytes"],two_condition_predictions_float32_bytes=2*nvol*160*192*160*4,
        pilot_steps_per_fit=pilots[0]["steps"],historical_138_gpu_hours_verified=False,
        caveat="Extrapolated from short training-side pilot on RTX3090 (repeated RAM-cached examples, not full epochs). Fold RAM cache preload and peak RSS measured once on fold 1 (928 subjects). A6000 throughput unmeasured."))
    source=json.loads((out/"clinical_source_receipt.json").read_text())
    gates=[dict(item="subject identities / two folds / modality audit",status="PASS",evidence="cohort.json; qc_exclusions.json; qc_revision_receipt.json"),
           dict(item="MRI/mask binding (after pre-specified QC exclusion of 016_S_4952)",status="PASS" if cfg["evaluation_mri_mask_gate_pass"] else "FAIL",evidence="qc_exclusions.json; preprocessing_errors.json"),
           dict(item="ROI anatomical laterality (global segmenter L/R naming swap, consistent in all subjects; physical names frozen)",status="PASS" if cfg["evaluation_laterality_gate_pass"] else "FAIL",evidence="laterality_fix_receipt.json; hemisphere_label_map.json; reports/e1_laterality_rootcause_20261017/CORRECTION.md"),
           dict(item="PET-independent ROI validity",status="PASS",evidence="roi_validity.json"),
           dict(item="Full / No-Scores PTID embeddings and comparable initialization",status="PASS",evidence="conditions/index.json; pilot_receipts.json"),
           dict(item="fold-local adapter refit on active cohort, no held-out PET",status="PASS",evidence=f"conditions/{cfg['adapter_subdir']}/adapter_fold1.json, adapter_fold2.json"),
           dict(item="training-side pilot / checkpoint reload / output roundtrip",status="PASS",evidence="pilot_receipts.json; evaluation_pipeline_check.json"),
           dict(item="fold RAM cache measured",status="PASS",evidence="full_fold_cache_probe.json"),
           dict(item="physical SUV/SUVR / authentic observed clinical contribution",status="LIMITED_NOT_CLAIMED",evidence="clinical_source_receipt.json; score_sources.csv"),
           dict(item="formal stage2 authorization",status="NOT_GRANTED",evidence="config.json: formal_training_authorized=false")]
    blockers=[g["item"] for g in gates if g["status"]=="FAIL"]
    rec="GO_PENDING_AUTHORIZATION" if not blockers else "NO_GO"
    write_json(out/"acceptance.json",dict(recommendation=rec,gates=gates,blockers=blockers,
        stage01_completed=True,formal_training_started=False,formal_training_authorized=False,
        acceptable_limits=["Historical conditioning field contribution only","Normalized-space reconstruction fidelity only",
            "New E1 folds separate from historical paper results","Single-seed conditional uncertainty; no clinical equivalence or disease-effect preservation claims",
            "Segmenter hemisphere names are swapped; lateralized ROI results use physical names from hemisphere_label_map.json"],
        needed_before_stage2="Explicit author authorization of the four formal fits and the revised budget"))
    n_bad=lat["subjects_with_invalid_rois"]
    txt=f"""# E1 阶段0–1验收报告（修订版）

结论：**{'科学验收通过，等待阶段2授权（GO_PENDING_AUTHORIZATION）' if rec!='NO_GO' else 'NO-GO'}**。四次正式训练未启动，`formal_training_authorized=false`。

## 本次修订解决的两项阻止项

1. MRI/mask绑定：`016_S_4952`按阶段0预设QC规则（保存MRI重放误差>2e-6，八种轴翻转均无法绑定）排除出adapter拟合、训练、OOF推理和全部评价。未重新划分；`cohort.json`字节不变，排除名单见`qc_exclusions.json`。有效队列{qcrev['subjects_active']}人（FDG {qcrev['effective_fdg']}、AV45 {qcrev['effective_av45']}）；两折留出各{qcrev['folds']['1']['test']}/{qcrev['folds']['2']['test']}人。两折adapter已在有效队列上重拟合至`conditions/{cfg['adapter_subdir']}/`（fold1 FDG/AV45 {len(adapters[1]['fit_ptids']['fdg'])}/{len(adapters[1]['fit_ptids']['av45'])}、fold2 {len(adapters[2]['fit_ptids']['fdg'])}/{len(adapters[2]['fit_ptids']['av45'])}），与留出集合交集为0；阶段1原adapter保留不动。
2. ROI侧别：根因是历史分割的左右命名对全部被试统一反转，而不是缓存仿射或个别病例错误。推测机制（未直接复现分割步骤）：历史流程以无头数组读取LAS存储的MNI配准MRI，并以identity头保存后分割，分割器按identity头理解左右，导致“Left/Right”名称与实际半球互换。原始配准MRI本身未镜像（20/20例与MNI模板的未翻转相关高于x翻转）。缓存仿射`ref.affine @ proc.affine`经原始MRI重采样验证是正确的索引→世界映射（10例相关系数0.988–0.999，x镜像映射仅0.58–0.75）。在该仿射下，白质、壳核、侧脑室、丘脑四对大结构在{lat['consistent_global_mirror']}/{lat['subjects']}人中全部呈一致镜像，无例外。
   - 处理：不交换mask标签、不翻转网格、不改缓存；冻结`hemisphere_label_map.json`，报告时用物理半球名称（如label 17报告为物理Right-Hippocampus）。
   - 子代理最初结论（“仿射叠加两次”）不成立，已在`reports/e1_laterality_rootcause_20261017/CORRECTION.md`更正；其全队列“零镜像”统计反映的是同一一致性。曾按其建议生成的错误修正文件已移至`superseded_wrong_affine_fix/`，未被任何入口使用。
   - 对E1：主要终点ROI MAE是对全部有效ROI取均值，与半球命名无关；预设关键ROI均为双侧成对，选择不变。仅涉及单侧的报告需用物理名称。
   - 历史论文若有单侧ROI表述，可能存在同样的命名互换；本轮未修改论文，建议作者单独核对。
3. ROI有效性（与PET无关）：某标签体素数低于队列中位数10%时，该被试该ROI视为无效。{n_bad}人共{lat['invalid_roi_cells']}个ROI单元无效；其中7人各有20–24个无效ROI（整体分割质量差），按原计划只计“共同有效ROI”，并在98区完整者敏感性分析中自然排除，不新增被试排除。

## 已通过与解释限制（保留）

- Full/No-Scores 168/20 tokens，无截断、按PTID绑定；两条件同折初始化、样本及t序列一致。
- 评分来源：观测可追溯值与实际条件值有{source['observed_conditioning_disagreements']}个字段不一致；填补方法未恢复，未确认诊断派生或直接PET依赖（不能据此宣称不存在）。结论限定为历史conditioning fields贡献。
- 强度：normalized uptake（arbitrary units），不称SUV/SUVR、临床等效或已排除shortcut。
- 新E1两折与历史结果隔离，不与历史指标计算增益。
- AMP下恢复后一步更新最大参数差约2.8e-6，属数值容差内重放，非逐位复现（xformers flash backward非确定）。

## 实测预算（{qcrev['subjects_active']}人有效队列）

- 硬件：{pilots[0]['hardware']['host']}，{pilots[0]['hardware']['gpu']}；训练峰值reserved显存{peak/1024**3:.2f} GiB（24 GB卡余量小，配方为逐tracer反传＋expandable allocator）。
- 四次165-epoch纯训练外推：{pure:.1f} GPUh；推理{infer_per_volume:.3f}秒/卷，两条件共{infer_hours:.2f} GPUh。
- 单折RAM缓存实测：928人装载{probe['wall_seconds']:.0f}秒，峰值RSS {rss_gib:.1f} GiB；建议每fit 80 GiB主机内存，两fit并发需约160 GiB。
- 合计（含装载及20–30%余量）：{low:.1f}–{high:.1f} GPUh，单卡约{low/24:.1f}–{high/24:.1f}天，两卡约{low/48:.1f}–{high/48:.1f}天。
- 若每epoch重读NFS：额外{streaming_io_low:.1f}–{streaming_io_high:.1f}小时，入口不会自动切换。
- 已发生且可复用：冻结PET特征{feature_hours:.2f} GPUh；预处理缓存{stage0['cache_bytes']/1e9:.1f} GB（datas230）。3014本地SSD约余22 GB，不做本地整折缓存。
- 基于3090短试跑外推；A6000未测；论文138 GPUh未验证。

## 停止边界

阶段0–1完成。唯一剩余条件是作者明确批准四次正式训练及上述预算；批准后需将`formal_training_authorized`改为true（训练入口其余门槛已通过）。旧`spatial_qc.png`的标题/轴注释沿用修订前假设，仅作历史记录。

证据：`acceptance.json`、`qc_exclusions.json`、`qc_revision_receipt.json`、`laterality_fix_receipt.json`、`hemisphere_label_map.json`、`roi_validity.json`、`full_fold_cache_probe.json`、`measured_budget.json`、`pilot_receipts.json`。大文件：{cfg['assets']}。
"""
    (out/"ACCEPTANCE_REPORT.md").write_text(txt)
    write_json(out/"implementation_sha256.json",{str(p.relative_to(ROOT)):sha(p) for p in (ROOT/"experiments/e1_clinical_conditioning").glob("*.py")})
    print("REPORT COMPLETE:",rec,flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["freeze","qc-exclude","laterality-fix","source-receipt","io","figures","report"])
    p.add_argument("--out",type=Path,required=True);a=p.parse_args();out=a.out.resolve()
    {"freeze":freeze,"qc-exclude":qc_exclude,"laterality-fix":laterality_fix,"source-receipt":source_receipt,"io":io_benchmark,"figures":figures,"report":report}[a.action](out)
