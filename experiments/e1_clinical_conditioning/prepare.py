"""Freeze E1 identities and audit inputs. Never executes historical notebooks."""
from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import shutil
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import nibabel as nib
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold

from common import CODE, ROOT, SCORES, sha, write_json


def source_audit(out):
    """Code cells only, bounded to the archived research sources, not dependencies."""
    hits, scanned, failures = [], [], []
    pattern = re.compile(r"filtered_subjects_filled|generate_description|fillna|imput|target_cross_sim")
    for path in sorted((ROOT / "source_archive").rglob("*.ipynb")):
        if any(s in path.parts for s in ["monai", "CLIP-main", "generative", "BiomedCLIP"]):
            continue
        try:
            # Source arrays are separate indented JSON members in these archives.
            # Stream past image outputs, never load multi-GB notebooks into RAM.
            with path.open() as f:
                collecting, lines, index = False, [], -1
                for line in f:
                    if re.match(r'^\s*"source"\s*:\s*\[', line):
                        collecting, lines, index = True, [line[line.index("["):]], index+1
                        if line.rstrip().rstrip(",").endswith("]"):
                            text="".join(json.loads(lines[0].rstrip().rstrip(",")))
                            if pattern.search(text):
                                hits.append(dict(path=str(path.relative_to(ROOT)),cell=index,source=text))
                            collecting=False
                    elif collecting:
                        lines.append(line)
                    if collecting and re.match(r'^\s*\]\s*,?\s*$', line):
                        text="".join(json.loads("".join(lines).rstrip().rstrip(",")))
                        if pattern.search(text) or ("MMSE" in text and re.search(r"random|groupby",text)):
                            hits.append(dict(path=str(path.relative_to(ROOT)), cell=index, source=text))
                        collecting=False
            scanned.append(str(path.relative_to(ROOT)))
        except Exception as e:
            failures.append(dict(path=str(path), error=str(e)))
    write_json(out / "source_scope.json", dict(scanned=scanned, failures=failures, matched_cells=len(hits)))
    write_json(out / "source_cells.json", hits)
    return hits


def init(out, asset):
    if (out/"config.json").exists():
        raise RuntimeError("Initialized run already exists; choose a distinct output")
    out.mkdir(parents=True, exist_ok=True)
    asset.mkdir(parents=True, exist_ok=True)
    old = ROOT / "appendix/legacy_only/8_revision_evidence/revision_20261016"
    base = ROOT / "data/vscode-3003/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45"
    hist = base.parent
    sources = {"metadata": base / "filtered_subjects_with_description.csv",
               "filled": base / "filtered_subjects_filled.csv",
               "observed": old / "clinical_observed_subjects.csv",
               "observed_provenance": old / "clinical_observed_provenance.csv",
               "clinical_export": base / "ADNI MRI and FDG and AV45 csv.csv"}
    frozen = {}
    for key, path in sources.items():
        target = out / (key + ".csv")
        shutil.copyfile(path, target)
        frozen[str(target)] = sha(target)
    meta = pd.read_csv(out / "metadata.csv").sort_values("Subject ID").reset_index(drop=True)
    assert len(meta) == meta["Subject ID"].nunique() == 1857
    # Reproduce the published literal template without running its side effects.
    notebook = ROOT / "source_archive/vscode-3003/home/data/liutuo/code/chu li shu ju.ipynb"
    d = json.loads(notebook.read_text())
    function = next(n for n in ast.parse("".join(d["cells"][6]["source"])).body
                    if isinstance(n, ast.FunctionDef) and n.name == "generate_description")
    ns = {}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[])), str(notebook), "exec"), ns)
    assert all(ns["generate_description"](row) == row.Description for _, row in meta.iterrows())
    mapping = {}
    for fold, (_, test) in enumerate(StratifiedKFold(2, shuffle=True, random_state=42).split(meta, meta["Research Group"]), 1):
        mapping.update({meta.loc[i, "Subject ID"]: fold for i in test})
    paths = {}
    for key, folder in [("mri","mri_strip_registered"),("fdg","PET2_FDG_strip_registered"),("av45","PET1_AV45_strip_registered")]:
        paths[key]={}
        for path in sorted((base/folder).glob("*.nii.gz")):
            sid="_".join(path.name.split("_")[:3])
            assert sid not in paths[key], (sid,"duplicate source candidates")
            assert re.fullmatch(r"\d{3}_S_\d+_(MRI_registered|FDG_registered|AV45_registered|zero)\.nii\.gz",path.name),path
            paths[key][sid]=path
    cohort = []
    for _, row in meta.iterrows():
        sid = row["Subject ID"]
        full = row.Description
        short = full.split(" The global Clinical")[0]
        assert short.startswith("Subject is a ") and short.endswith(" kg.")
        assert not re.search(r"CDR|MMSE|GDS|FAQ|NPI|dementia|depression|impairment", short, re.I)
        item = dict(ptid=sid, diagnosis=row["Research Group"], test_fold=mapping[sid],
                    full=full, no_scores=short, age=float(row.Age), sex=row.Sex,
                    weight=float(row.Weight))
        for tracer, folder, suffix in [("mri", "mri_strip_registered", "MRI"),
                                        ("fdg", "PET2_FDG_strip_registered", "FDG"),
                                        ("av45", "PET1_AV45_strip_registered", "AV45")]:
            item[tracer] = str(paths[tracer][sid].resolve())
        item["saved_mri"] = str((hist / "data_augmentation_mri" / f"{sid}.nii.gz").resolve())
        item["mask"] = str((hist / "data_augmentation_mri_fenge" / f"{sid}fenge.nii.gz").resolve())
        assert all(Path(item[k]).exists() for k in ["mri", "fdg", "av45", "saved_mri", "mask"])
        cohort.append(item)
    write_json(out / "cohort_candidate.json", cohort)
    prov = pd.read_csv(out / "observed_provenance.csv")
    rows = []
    idx = meta.set_index("Subject ID")
    for _, p in prov.iterrows():
        sid, field = p.subject, p.variable
        value = float(idx.loc[sid, field])
        matched = p.status == "observed_unique" and np.isfinite(p.observed_value) and float(p.observed_value) == value
        rows.append(dict(ptid=sid, field=field, conditioning_value=value,
                         observed_value=p.observed_value, observed_anchor_status=p.status,
                         origin="observed_value_match_visit_unverified" if matched else "unknown_in_filled_table",
                         diagnostic_derivation="unverified", target_pet_dependency="unverified_upstream",
                         visit_alignment="unverified_no_date", value_sha256=__import__('hashlib').sha256(str(value).encode()).hexdigest()))
    pd.DataFrame(rows).to_csv(out / "score_sources.csv", index=False)
    roi = pd.read_csv(old / "image_derived/regional_agreement_overall.csv")
    roi = roi[roi.tracer == "av45"][["region", "region_name"]].copy()
    assert len(roi) == roi.region.nunique() == 98
    roi.to_csv(out / "roi_labels.csv", index=False)
    texts = json.loads((CODE / "mri2pet _two trace_new-final.ipynb").read_text())
    tree = ast.parse("".join(texts["cells"][1]["source"]))
    tracer_texts = {}
    for n in tree.body:
        if isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name) and n.targets[0].id in ["fdg_text_optimized", "av45_text_optimized"]:
            tracer_texts[n.targets[0].id.split("_")[0]] = ast.literal_eval(n.value)
    write_json(out / "tracer_texts.json", tracer_texts)
    config = dict(experiment="E1_stage01_20261017", report=str(out), assets=str(asset), seed=42,
                  formal_training_authorized=False, model_source=str(CODE),
                  training_cache_mode="fold_memory",training_cache_budget_gib=80,
                  backward_mode="per_tracer_accumulate_one_optimizer_step",
                  training_host_memory_recommended_gib=80,
                  historical_monai=str(ROOT/"source_archive/vscode-3003/home/data/liutuo/code"), shape=[160, 192, 160],
                  conditions=["Full", "No-Scores"], epochs=165, endpoint_epoch_zero_based=140,
                  learning_rate=2.5e-5, adapter_iterations=5000, tau=0.82,
                  adapter_lr=1e-3, adapter_cross_weight=100., frozen_files=frozen,
                  score_interpretation="historical conditioning fields; genuine observed clinical benefit not established",
                  conditioning_scientific_gate="LIMITED_HISTORICAL_FIELDS",
                  key_rois={"av45":[1025,2025,1027,2027,1028,2028,1015,2015,1030,2030],
                            "fdg":[17,53,1023,2023,1008,2008,1015,2015,1030,2030]},
                  statistics=dict(seed=20261017, bootstrap_replicates=10000,
                                  primary="subject-level ROI MAE per tracer", paired_delta="No-Scores minus Full",
                                  primary_adjustment="Holm, two tracers", roi_adjustment="BH,196 ROI MAE tests"))
    write_json(out / "config.json", config)
    source_audit(out)
    print("Created", out, asset, "candidate subjects", len(cohort), flush=True)


_TRANSFORM = None


def setup_worker():
    global _TRANSFORM
    import sys, torch
    sys.path.insert(0, str(ROOT/"source_archive/vscode-3003/home/data/liutuo/code"))
    import monai.transforms as mt
    torch.set_num_threads(1)
    keys = ["mri", "fdg", "av45"]
    _TRANSFORM = mt.Compose([
        mt.Lambdad(keys=keys, func=lambda p: nib.load(p).get_fdata()),
        mt.EnsureChannelFirstd(keys=keys, channel_dim="no_channel"),
        mt.Orientationd(keys=keys, axcodes="LPI"),
        mt.CropForegroundd(keys=keys, source_key="mri", allow_smaller=True),
        mt.HistogramNormalized(keys=["mri"]),
        mt.ResizeWithPadOrCropd(keys=keys, spatial_size=[160,192,160]),
        mt.Spacingd(keys=keys, pixdim=(1.,1.,1.)),
        mt.NormalizeIntensityd(keys=keys), mt.ScaleIntensityd(keys=keys)])


def one_subject(args):
    item, assets = args
    sid = item["ptid"]
    result = dict(ptid=sid)
    hashes = []
    raw_images = {k:nib.load(item[k]) for k in ["mri","fdg","av45"]}
    ref = raw_images["mri"]
    for k, im in raw_images.items():
        if im.shape != ref.shape or not np.allclose(im.affine, ref.affine, atol=1e-6):
            raise ValueError(f"Source geometry mismatch {sid}/{k}")
        hashes.append(dict(ptid=sid, kind=k, path=item[k], sha256=sha(item[k]), bytes=Path(item[k]).stat().st_size))
    proc = _TRANSFORM({k:item[k] for k in raw_images})
    arrays = {k:np.asarray(proc[k], dtype=np.float32).squeeze() for k in raw_images}
    for k, a in arrays.items():
        assert a.shape == (160,192,160) and np.isfinite(a).all(), (sid,k)
        result[k+"_min"] = float(a.min())
        result[k+"_max"] = float(a.max())
        result["has_"+k] = bool(a.max() > a.min())
        if k != "mri" and not result["has_"+k]:
            assert np.all(a == 0), (sid,k,"constant nonzero target")
    assert result["has_mri"] and (result["has_fdg"] or result["has_av45"])
    saved = nib.load(item["saved_mri"]).get_fdata(dtype=np.float32)
    aligned = np.flip(arrays["mri"], (0,1,2))
    result["saved_mri_replay_maxabs"] = float(np.max(np.abs(saved-aligned)))
    result["saved_mri_replay_mae"] = float(np.mean(np.abs(saved-aligned),dtype=np.float64))
    # Historical saved MRI/masks are in the flipped array grid with identity headers.
    # The independent MRI replay is the anchor; PET similarity never chooses a flip.
    result["mri_mask_grid_pass"] = result["saved_mri_replay_maxabs"] <= 2e-6
    mask_im = nib.load(item["mask"])
    mask = mask_im.get_fdata(dtype=np.float32)
    assert mask.shape == saved.shape and np.isfinite(mask).all() and np.array_equal(mask, np.rint(mask))
    mask = np.flip(mask.astype(np.int16), (0,1,2)).copy()
    world_affine = ref.affine @ np.asarray(proc["mri"].affine)
    assert np.allclose(np.asarray(proc["fdg"].affine), np.asarray(proc["mri"].affine))
    assert np.allclose(np.asarray(proc["av45"].affine), np.asarray(proc["mri"].affine))
    centroids = {}
    for label in [17,53,1025,2025]:
        coords = np.argwhere(mask == label)
        centroids[str(label)] = (nib.affines.apply_affine(world_affine,coords.mean(0)).tolist() if len(coords) else None)
    result["left_right_anatomy_pass"] = bool(centroids["17"] and centroids["53"] and centroids["17"][0] < centroids["53"][0])
    # Retain failed scientific checks as explicit blockers while allowing the
    # separately authorized, training-side engineering pilot to finish.
    result["anatomical_centroids_world"] = centroids
    for k in ["mask","saved_mri"]:
        hashes.append(dict(ptid=sid,kind=k,path=item[k],sha256=sha(item[k]),bytes=Path(item[k]).stat().st_size))
    path = Path(assets)/"preprocessed"/f"{sid}.npz"
    np.savez(path, **arrays, mask=mask, affine=world_affine)
    result["cache"] = str(path)
    result["cache_bytes"] = path.stat().st_size
    result["cache_sha256"] = sha(path)
    result["affine"] = world_affine.tolist()
    result["source_affine"] = ref.affine.tolist()
    return result, hashes


def prepare(out, workers):
    start = time.monotonic()
    cfg = json.loads((out/"config.json").read_text())
    items = json.loads((out/"cohort_candidate.json").read_text())
    assets = Path(cfg["assets"])
    (assets/"preprocessed").mkdir(exist_ok=True)
    done, hashes, errors = [], [], []
    # Results are journaled so failures cannot disappear from the receipt.
    with (out/"preprocessing_progress.jsonl").open("a") as log:
        with ProcessPoolExecutor(workers,initializer=setup_worker) as pool:
            futures = {pool.submit(one_subject,(x,str(assets))):x["ptid"] for x in items}
            from concurrent.futures import as_completed
            for future in as_completed(futures):
                sid = futures[future]
                try:
                    row, hh = future.result();done.append(row);hashes.extend(hh)
                    log.write(json.dumps(row)+"\n");log.flush()
                except Exception as e:
                    errors.append(dict(ptid=sid,error=repr(e)))
                if (len(done)+len(errors))%25 == 0:
                    print("preprocessed",len(done),"errors",len(errors),"elapsed",round(time.monotonic()-start),flush=True)
    write_json(out/"preprocessing_errors.json",errors)
    pd.DataFrame(hashes).to_csv(out/"input_hashes.csv",index=False)
    write_json(out/"geometry_qc.json",sorted(done,key=lambda r:r["ptid"]))
    if errors:
        raise RuntimeError(f"{len(errors)} subjects failed; no final cohort frozen")
    qc={r["ptid"]:r for r in done}
    for row in items:
        for key in ["has_fdg","has_av45","cache","cache_sha256"]:
            row[key]=qc[row["ptid"]][key]
    write_json(out/"cohort.json",items)
    pd.DataFrame([{k:v for k,v in x.items() if k not in ["full","no_scores"]} for x in items]).to_csv(out/"cohort.csv",index=False)
    cfg["frozen_files"].update({str(out/f):sha(out/f) for f in ["cohort.json","roi_labels.csv","tracer_texts.json","score_sources.csv"]})
    cfg["evaluation_laterality_gate_pass"] = all(r["left_right_anatomy_pass"] for r in done)
    cfg["evaluation_mri_mask_gate_pass"] = all(r.get("mri_mask_grid_pass",r["saved_mri_replay_maxabs"]<=2e-6) for r in done)
    write_json(out/"config.json",cfg)
    write_json(out/"stage0_receipt.json",dict(subjects=len(items),errors=errors,
        effective_fdg=sum(r["has_fdg"] for r in items),effective_av45=sum(r["has_av45"] for r in items),
        folds={str(f):dict(test=sum(r["test_fold"]==f for r in items),train=sum(r["test_fold"]!=f for r in items)) for f in [1,2]},
        max_mri_replay_error=max(r["saved_mri_replay_maxabs"] for r in done),
        laterality_pass_subjects=sum(r["left_right_anatomy_pass"] for r in done),
        evaluation_status="PASS" if cfg["evaluation_laterality_gate_pass"] else "NO_GO_anatomical_laterality",
        preprocessing_wall_seconds=time.monotonic()-start,cache_bytes=sum(r["cache_bytes"] for r in done),
        unit="normalized uptake (arbitrary units)",
        geometry="Exact MRI replay anchors historical mask array grid; raw affine composed with preprocessing index transform; no PET-based alignment selection"))


if __name__ == "__main__":
    p=argparse.ArgumentParser();p.add_argument("action",choices=["init","prepare"])
    p.add_argument("--out",type=Path,required=True);p.add_argument("--assets",type=Path)
    p.add_argument("--workers",type=int,default=4);a=p.parse_args()
    if a.action=="init":init(a.out.resolve(),a.assets.resolve())
    else:prepare(a.out.resolve(),a.workers)
