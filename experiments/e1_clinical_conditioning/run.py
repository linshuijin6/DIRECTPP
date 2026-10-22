"""Native E1 condition, pilot, training and OOF entrypoints.

Stage 2 is deliberately disabled by the frozen configuration. Pilot checkpoints
cannot be supplied to the formal training action.
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import random
import shutil
import socket
import sys
import time
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
import torch.nn.functional as F
from report_error import email_on_error

from common import CODE, ROOT, TRACERS, active_rows, capture_execution, check_frozen, load_config, new_model, seed_all, sha, tensor_hash, write_json


def hardware():
    import monai, transformers, xformers
    return dict(host=socket.gethostname(), pid=os.getpid(), visible_devices=os.environ.get("CUDA_VISIBLE_DEVICES"),
                allocator_config=os.environ.get("PYTORCH_CUDA_ALLOC_CONF"),
                gpu=torch.cuda.get_device_name(0), torch=torch.__version__, cuda=torch.version.cuda,
                monai=monai.__version__, transformers=transformers.__version__, xformers=xformers.__version__)


def bundle(cfg):
    target=Path(cfg["assets"])/"biomedclip"
    target.mkdir(exist_ok=True)
    for p in (CODE/"BiomedCLIP").iterdir():
        if p.suffix in [".py",".json"]:
            shutil.copyfile(p,target/p.name)
    weight=(ROOT/"results/checkpoints/vscode-3002/home/ssddata/liutuo/BiomedCLIP/model.safetensors").resolve()
    if not (target/weight.name).exists():
        (target/weight.name).symlink_to(weight)
    write_json(Path(cfg["report"])/"biomedclip_bundle.json",dict(path=str(target),
        files={p.name:sha(p) for p in sorted(target.iterdir()) if p.is_file()}))


def biomed(cfg):
    from transformers import AutoModel, AutoProcessor
    p=str(Path(cfg["assets"])/"biomedclip")
    processor=AutoProcessor.from_pretrained(p,trust_remote_code=True,local_files_only=True)
    model=AutoModel.from_pretrained(p,trust_remote_code=True,local_files_only=True).cuda().eval()
    for param in model.parameters():param.requires_grad_(False)
    return processor,model


@torch.inference_mode()
def encode(cfg, rows):
    processor,model=biomed(cfg)
    output=Path(cfg["assets"])/"conditions";output.mkdir(exist_ok=True)
    length_log={}
    for condition,key in [("Full","full"),("No-Scores","no_scores")]:
        # Group by actual token length: preserve the historical input_ids-only
        # invocation without letting PAD tokens or batch composition affect it.
        groups={}
        for i,r in enumerate(rows):
            ids=processor.tokenizer(r[key],truncation=True,max_length=256)["input_ids"]
            raw=processor.tokenizer(r[key],truncation=False)["input_ids"]
            if len(raw)>256:raise RuntimeError(f"Truncated patient prompt {r['ptid']}")
            groups.setdefault(len(ids),[]).append((i,ids))
        emb=np.empty((len(rows),512),np.float32)
        for length,group in groups.items():
            for start in range(0,len(group),64):
                batch=group[start:start+64]
                ids=torch.tensor([x[1] for x in batch],device="cuda")
                feature=model.get_text_features(ids).float().cpu().numpy()
                emb[[x[0] for x in batch]]=feature
        assert np.isfinite(emb).all()
        np.save(output/f"{condition}.npy",emb)
        length_log[condition]={str(k):len(v) for k,v in groups.items()}
    tracer_text=json.loads((Path(cfg["report"])/"tracer_texts.json").read_text())
    # The two tracer texts are encoded together, with their attention masks,
    # matching the adapted-branch feature preparation.
    ids=processor(text=[tracer_text[t] for t in TRACERS],padding=True,truncation=True,max_length=256,return_tensors="pt").to("cuda")
    tracer=model.get_text_features(input_ids=ids["input_ids"],attention_mask=ids["attention_mask"]).float().cpu().numpy()
    np.save(output/"raw_tracers.npy",tracer)
    empty=processor.tokenizer("",return_tensors="pt")["input_ids"].cuda()
    np.save(output/"No-Patient.npy",model.get_text_features(empty).float().cpu().numpy())
    write_json(output/"index.json",dict(ptids=[r["ptid"] for r in rows],tracers=TRACERS,
        files={p.name:sha(p) for p in output.glob("*.npy")},patient_lengths=length_log,
        patient_encoding="equal-length batches, input_ids only, no padding; historical pooling/projection; no extra normalization",
        source_config_sha256=sha(Path(cfg["report"])/"config.json"),hardware=hardware()))
    print("ENCODE COMPLETE",length_log,flush=True)


def slices(a):
    from PIL import Image
    result=[]
    for i in np.linspace(0,a.shape[2]-1,160,dtype=int):
        x=a[:,:,i];x=(x-x.min())/(x.max()-x.min()+1e-5)
        im=Image.fromarray((x*255).astype(np.uint8)).resize((224,224))
        result.append(Image.fromarray(np.stack([np.asarray(im)]*3,axis=-1)))
    return result


@torch.inference_mode()
def features(cfg,rows):
    start=time.monotonic();processor,model=biomed(cfg)
    out=Path(cfg["assets"])/"pet_features";out.mkdir(exist_ok=True)
    ids={t:[] for t in TRACERS};vectors={t:[] for t in TRACERS};timings=[]
    for index,r in enumerate(rows):
        if "cache" not in r:
            # Frozen-encoder work may overlap the CPU preprocessing. It consumes
            # only completed, hashed per-subject caches, never partial files.
            deadline=time.monotonic()+1800
            while True:
                log=Path(cfg["report"])/"preprocessing_progress.jsonl"
                available={x["ptid"]:x for x in (json.loads(line) for line in log.read_text().splitlines())}
                extra=Path(cfg["report"])/"additional_qc.json"
                if extra.exists():available.update({x["ptid"]:x for x in json.loads(extra.read_text())})
                if r["ptid"] in available:
                    q=available[r["ptid"]]
                    r.update({k:q[k] for k in ["cache","cache_sha256","has_fdg","has_av45"]})
                    break
                errors=Path(cfg["report"])/"preprocessing_errors.json"
                if errors.exists() and json.loads(errors.read_text()):raise RuntimeError("Preprocessing failed")
                if time.monotonic()>deadline:raise RuntimeError("Timed out waiting for a completed CPU cache")
                time.sleep(.5)
        with np.load(r["cache"]) as data:
            for tracer in TRACERS:
                if not r["has_"+tracer]:continue
                tick=time.monotonic();images=slices(data[tracer]);v=[]
                for begin in range(0,len(images),40):
                    inputs=processor(images=images[begin:begin+40],return_tensors="pt").to("cuda")
                    v.append(model.get_image_features(**inputs).float())
                vector=torch.cat(v).mean(0).cpu().numpy()
                assert vector.shape==(512,) and np.isfinite(vector).all()
                ids[tracer].append(r["ptid"]);vectors[tracer].append(vector)
                timings.append(time.monotonic()-tick)
        if (index+1)%25==0:print("PET features",index+1,"/",len(rows),"elapsed",round(time.monotonic()-start),flush=True)
    for t in TRACERS:
        np.save(out/f"{t}.npy",np.stack(vectors[t]))
        write_json(out/f"{t}_index.json",dict(ptids=ids[t],sha256=sha(out/f"{t}.npy"),
            cache_binding={r["ptid"]:r["cache_sha256"] for r in rows if r["ptid"] in set(ids[t])},
            frozen_encoder_only=True,adapter_fit=False))
    write_json(out/"receipt.json",dict(volumes=sum(map(len,ids.values())),slices=160*sum(map(len,ids.values())),
        wall_seconds=time.monotonic()-start,per_volume_seconds_median=float(np.median(timings)),
        per_volume_seconds_p90=float(np.percentile(timings,90)),hardware=hardware(),
        precision="float32; no AMP; 160 independently scaled 2D slices; original PIL resize then processor"))


def adapter_dir(cfg):
    # Stage-1 adapters stay in conditions/; QC-revised refits go to a separate subdir.
    d=Path(cfg["assets"])/"conditions"/cfg.get("adapter_subdir","");d.mkdir(parents=True,exist_ok=True);return d


def adapt(cfg,rows):
    out=adapter_dir(cfg);source=Path(cfg["assets"])/"pet_features"
    text=torch.from_numpy(np.load(Path(cfg["assets"])/"conditions"/"raw_tracers.npy"))
    text=F.normalize(text,dim=-1)
    for fold in [1,2]:
        seed_all(cfg["seed"]+fold)
        train={r["ptid"] for r in rows if r["test_fold"]!=fold}
        test={r["ptid"] for r in rows if r["test_fold"]==fold}
        feature=[];used={}
        for tracer in TRACERS:
            index=json.loads((source/f"{tracer}_index.json").read_text())
            assert sha(source/f"{tracer}.npy")==index["sha256"]
            for row in rows:
                if row["has_"+tracer]:
                    assert index["cache_binding"][row["ptid"]]==row["cache_sha256"],"PET feature input cache version mismatch"
            ids=index["ptids"];select=[i for i,sid in enumerate(ids) if sid in train]
            used[tracer]=[ids[i] for i in select]
            assert set(used[tracer]).isdisjoint(test)
            expected={r["ptid"] for r in rows if r["test_fold"]!=fold and r["has_"+tracer]}
            assert set(used[tracer])==expected
            feature.append(F.normalize(torch.from_numpy(np.load(source/f"{tracer}.npy",mmap_mode="r")[select].copy()),dim=-1))
        scale=torch.ones(2,requires_grad=True);bias=(torch.randn(2,512)*.01).requires_grad_()
        opt=torch.optim.Adam([scale,bias],lr=cfg["adapter_lr"])
        for step in range(cfg["adapter_iterations"]):
            opt.zero_grad();v=F.normalize(scale[:,None]*text+bias,dim=-1)
            sims=[F.cosine_similarity(v[i][None],feature[i],dim=1).mean() for i in range(2)]
            cross=F.cosine_similarity(v[0][None],v[1][None])
            loss=-sims[0]-sims[1]+cfg["adapter_cross_weight"]*(cross-cfg["tau"]).square().sum()
            loss.backward();opt.step()
        v=F.normalize(scale[:,None]*text+bias,dim=-1).detach().numpy()
        np.save(out/f"adapter_fold{fold}.npy",v)
        write_json(out/f"adapter_fold{fold}.json",dict(fold=fold,tracers=TRACERS,fit_ptids=used,
            outer_test_ptids=sorted(test),intersection_count=0,iterations=cfg["adapter_iterations"],
            seed=cfg["seed"]+fold,tau=cfg["tau"],loss=float(loss.detach()),
            cross_cosine=float(np.dot(v[0],v[1])),scale=scale.detach().tolist(),
            bias=bias.detach().tolist(),sha256=sha(out/f"adapter_fold{fold}.npy"),
            feature_hashes={t:sha(source/f"{t}.npy") for t in TRACERS},
            shared_by=["Full","No-Scores"],fitting_device="cpu"))
        print("ADAPTER COMPLETE fold",fold,"counts",{t:len(x) for t,x in used.items()},flush=True)


def contexts(cfg,condition):
    p=Path(cfg["assets"])/"conditions";index=json.loads((p/"index.json").read_text())
    assert sha(p/f"{condition}.npy")==index["files"][f"{condition}.npy"]
    a=np.load(p/f"{condition}.npy")
    assert a.shape==(len(index["ptids"]),512) and len(set(index["ptids"]))==len(a) and np.isfinite(a).all()
    return {sid:torch.from_numpy(a[i]) for i,sid in enumerate(index["ptids"])}


def load_adapter(cfg,rows,fold):
    p=adapter_dir(cfg)/f"adapter_fold{fold}"
    receipt=json.loads(p.with_suffix(".json").read_text())
    assert receipt["fold"]==fold and receipt["tau"]==cfg["tau"]
    assert sha(p.with_suffix(".npy"))==receipt["sha256"]
    expected_test={r["ptid"] for r in rows if r["test_fold"]==fold}
    assert set(receipt["outer_test_ptids"])==expected_test
    for t in TRACERS:
        expected={r["ptid"] for r in rows if r["test_fold"]!=fold and r["has_"+t]}
        assert set(receipt["fit_ptids"][t])==expected and expected.isdisjoint(expected_test)
        feature=Path(cfg["assets"])/"pet_features"/f"{t}.npy"
        assert sha(feature)==receipt["feature_hashes"][t]
        binding=json.loads(feature.with_name(f"{t}_index.json").read_text())["cache_binding"]
        assert all(binding[r["ptid"]]==r["cache_sha256"] for r in rows if r["ptid"] in expected)
    a=np.load(p.with_suffix(".npy"));assert a.shape==(2,512) and np.isfinite(a).all()
    return torch.from_numpy(a).cuda()


def verify_caches(rows):
    for r in rows:
        if sha(r["cache"])!=r["cache_sha256"]:raise RuntimeError(f"Cache changed: {r['ptid']}")


def get_data(row,device="cuda"):
    with np.load(row["cache"]) as z:
        return {k:torch.from_numpy(z[k].copy())[None,None].to(device) for k in ["mri","fdg","av45"]}


def batch_step(model,opt,scaler,data,row,patient,adapter,timestep):
    images=data["mri"];times=torch.tensor([timestep],device="cuda",dtype=torch.long);t=times.float()/1000
    cuda_rng=torch.cuda.get_rng_state()
    for attempt in range(8):
        # Recompute the same subject/timestep and stochastic forward at a lower
        # scale after overflow; count only an actual, finite optimizer update.
        if attempt:torch.cuda.set_rng_state(cuda_rng)
        opt.zero_grad(set_to_none=True)
        losses=[]
        for i,tracer in enumerate(TRACERS):
            if not row["has_"+tracer]:continue
            with torch.autocast("cuda",dtype=torch.float16):
                target=data[tracer];context=torch.stack([patient,adapter[i]])[None]
                pred=model(x=t*target+(1-t)*images,timesteps=times,context=context)
                tracer_loss=F.mse_loss((target-images).float(),pred.float())
            assert torch.isfinite(tracer_loss),"Nonfinite pilot/training loss"
            # Gradient of L_FDG + L_AV45 is the sum of branch gradients. Release
            # each graph before the next forward; optimizer/scaler update once.
            scaler.scale(tracer_loss).backward()
            losses.append(tracer_loss.detach())
            del pred,tracer_loss
        loss=sum(losses)
        scaler.unscale_(opt)
        finite=bool(torch.stack([torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None]).all())
        scale=scaler.get_scale()
        if not finite and not scaler.is_enabled():
            raise RuntimeError("Nonfinite gradient with AMP scaling disabled")
        # GradScaler skips optimizer.step on overflow and backs off the scale.
        scaler.step(opt);scaler.update()
        if finite:return float(loss.detach())
        print(json.dumps(dict(event="amp_overflow_retry",ptid=row["ptid"],timestep=timestep,
            attempt=attempt+1,loss=float(loss.detach()),scale_before=scale,scale_after=scaler.get_scale())),flush=True)
    raise RuntimeError(f"Nonfinite gradient persisted after 8 AMP attempts: {row['ptid']}, timestep={timestep}")


@torch.inference_mode()
def prediction(model,data,patient,adapter):
    with torch.autocast("cuda",dtype=torch.float16):
        v=model(x=data["mri"],timesteps=torch.zeros(1,device="cuda",dtype=torch.long),
                context=torch.stack([patient,adapter])[None])
    return torch.clamp(data["mri"].float()+v.float(),0,1).squeeze().cpu().numpy()


def pilot(cfg,rows,steps):
    if not 24<=steps<=98:
        raise ValueError("Pilot needs 24--98 benchmark steps; plus two resume checks, at most 100 updates")
    assert not cfg["formal_training_authorized"]
    out=Path(cfg["assets"])/"pilot";out.mkdir(exist_ok=True)
    receipts=[]
    for fold in [1,2]:
        selected=[]
        for pattern in [(True,True),(True,False),(False,True)]:
            selected += [r for r in rows if r["test_fold"]!=fold and (r["has_fdg"],r["has_av45"])==pattern][:2]
        assert len(selected)==6
        for condition in ["Full","No-Scores"]:
            label=f"fold{fold}_{condition}";folder=out/label
            if (folder/"receipt.json").exists():
                existing=json.loads((folder/"receipt.json").read_text())
                assert existing["config_sha256"]==sha(Path(cfg["report"])/"config.json") and existing["steps"]==steps
                receipts.append(existing);print("Reusing completed identical-config pilot",label,flush=True);continue
            folder.mkdir(exist_ok=False)
            seed_all(cfg["seed"]+fold)
            model=new_model().cuda();initial=tensor_hash(model.state_dict());model.train()
            opt=torch.optim.Adam(model.parameters(),lr=cfg["learning_rate"])
            scaler=torch.amp.GradScaler("cuda")
            ctx=contexts(cfg,condition);adapter=load_adapter(cfg,rows,fold)
            verify_caches(selected)
            cached={r["ptid"]:get_data(r,device="cpu") for r in selected}
            rng=np.random.default_rng(cfg["seed"]+fold)
            torch.cuda.synchronize();torch.cuda.reset_peak_memory_stats();started=time.monotonic()
            timings=[];losses=[];trace=[]
            for step in range(steps):
                row=selected[step%len(selected)];sid=row["ptid"]
                data={k:v.cuda() for k,v in cached[sid].items()}
                # Exercise both original stages, without fitting any test metric.
                timestep=0 if (step//len(selected))%2 else int(rng.integers(0,1000))
                torch.cuda.synchronize();tick=time.monotonic()
                loss=batch_step(model,opt,scaler,data,row,ctx[sid].cuda(),adapter,timestep)
                torch.cuda.synchronize();elapsed=time.monotonic()-tick
                timings.append(elapsed);losses.append(loss)
                trace.append(dict(step=step,ptid=sid,timestep=timestep,seconds=elapsed,loss=loss,
                                  has_fdg=row["has_fdg"],has_av45=row["has_av45"]))
                if step%6==0:print(label,step,"loss",loss,"seconds",round(elapsed,3),flush=True)
            training_seconds=time.monotonic()-started
            peak=torch.cuda.max_memory_allocated();reserved=torch.cuda.max_memory_reserved()
            row=selected[0];data={k:v.cuda() for k,v in cached[row["ptid"]].items()};model.eval()
            inference=[];preds={}
            for i,tracer in enumerate(TRACERS):
                for repeat in range(6):
                    torch.cuda.synchronize();tick=time.monotonic()
                    a=prediction(model,data,ctx[row["ptid"]].cuda(),adapter[i]);torch.cuda.synchronize()
                    if repeat:inference.append(dict(tracer=tracer,seconds=time.monotonic()-tick))
                preds[tracer]=a
                with np.load(row["cache"]) as z:affine=z["affine"]
                p=folder/f"pilot_{tracer}_{row['ptid']}.nii.gz";nib.save(nib.Nifti1Image(a,affine),p)
                loaded=nib.load(p)
                assert np.array_equal(loaded.get_fdata(dtype=np.float32),a) and np.allclose(loaded.affine,affine,atol=1e-5)
            save_start=time.monotonic()
            checkpoint=dict(stage="pilot_only_do_not_use_for_formal_training",fold=fold,condition=condition,
                model=model.state_dict(),optimizer=opt.state_dict(),scaler=scaler.state_dict(),steps=steps,
                config_sha256=sha(Path(cfg["report"])/"config.json"),
                cohort_sha256=sha(Path(cfg["report"])/"cohort.json"),
                condition_sha256=sha(Path(cfg["assets"])/"conditions"/f"{condition}.npy"),
                adapter_sha256=sha(Path(cfg["assets"])/"conditions"/f"adapter_fold{fold}.npy"),
                torch_rng=torch.get_rng_state(),cuda_rng=torch.cuda.get_rng_state_all(),
                numpy_rng=rng.bit_generator.state)
            torch.save(checkpoint,folder/"pilot_only.pt");save_seconds=time.monotonic()-save_start
            final=tensor_hash(model.state_dict())
            state=torch.load(folder/"pilot_only.pt",map_location="cpu",weights_only=False)
            model.load_state_dict(state["model"]);opt.load_state_dict(state["optimizer"]);scaler.load_state_dict(state["scaler"])
            assert tensor_hash(model.state_dict())==final
            a=prediction(model,data,ctx[row["ptid"]].cuda(),adapter[0]);assert np.array_equal(a,preds["fdg"])
            # Verify the next optimizer update against a fresh on-disk restore,
            # including all RNG/scaler state, rather than checking weights alone.
            def restore_and_update():
                saved=torch.load(folder/"pilot_only.pt",map_location="cpu",weights_only=False)
                model.load_state_dict(saved["model"]);opt.load_state_dict(saved["optimizer"]);scaler.load_state_dict(saved["scaler"])
                torch.set_rng_state(saved["torch_rng"]);torch.cuda.set_rng_state_all(saved["cuda_rng"])
                rr=np.random.default_rng();rr.bit_generator.state=saved["numpy_rng"]
                next_t=int(rr.integers(0,1000));model.train()
                loss=batch_step(model,opt,scaler,data,row,ctx[row["ptid"]].cuda(),adapter,next_t)
                return next_t,loss,{k:v.detach().cpu().clone() for k,v in model.state_dict().items()}
            ta,la,sa=restore_and_update();tb,lb,sb=restore_and_update()
            assert ta==tb
            resume_maxabs=max(float((sa[k]-sb[k]).abs().max()) for k in sa)
            # FP16 flash-attention backward is not bitwise deterministic in the
            # archived xformers operator. Preserve the observed error and test
            # at FP16 numerical precision, separately from exact state reload.
            for key in sa:torch.testing.assert_close(sa[key],sb[key],rtol=1e-3,atol=1e-5)
            receipt=dict(fold=fold,condition=condition,selected_train_ptids=[r["ptid"] for r in selected],
                outer_test_overlap=0,initial_model_sha256=initial,final_model_sha256=final,
                steps=steps,warmup_steps=6,training_seconds=training_seconds,
                backward_mode=cfg["backward_mode"],
                steady_seconds_mean=float(np.mean(timings[6:])),steady_seconds_median=float(np.median(timings[6:])),
                steady_seconds_p90=float(np.percentile(timings[6:],90)),peak_allocated_bytes=peak,peak_reserved_bytes=reserved,
                inference=inference,checkpoint_save_seconds=save_seconds,
                checkpoint_bytes=(folder/"pilot_only.pt").stat().st_size,
                output_roundtrip_pass=True,resume_weights_optimizer_scaler_pass=True,prediction_reload_exact=True,
                resume_next_update_pass=True,resume_next_update_maxabs=resume_maxabs,
                resume_next_update_bitwise_exact=(resume_maxabs==0),
                resume_next_update_rtol=1e-3,resume_next_update_atol=1e-5,
                extra_resume_validation_updates=2,
                trace=trace,hardware=hardware(),config_sha256=sha(Path(cfg["report"])/"config.json"),
                purpose="engineering only; trained/benchmarked entirely on outer training side; no quality conclusion")
            write_json(folder/"receipt.json",receipt);receipts.append(receipt)
            print("PILOT COMPLETE",label,"peak GiB",round(peak/1024**3,2),flush=True)
            del model,opt,scaler,data,cached,state,checkpoint,sa,sb;gc.collect();torch.cuda.empty_cache()
    for fold in [1,2]:
        rr=[r for r in receipts if r["fold"]==fold]
        assert rr[0]["initial_model_sha256"]==rr[1]["initial_model_sha256"]
        assert rr[0]["selected_train_ptids"]==rr[1]["selected_train_ptids"]
        assert [(r["ptid"],r["timestep"]) for r in rr[0]["trace"]]==[(r["ptid"],r["timestep"]) for r in rr[1]["trace"]]
    write_json(Path(cfg["report"])/"pilot_receipts.json",receipts)


def checkpoint_identity(cfg,fold,condition):
    return dict(fold=fold,condition=condition,
        config_sha256=sha(Path(cfg["report"])/"config.json"),
        cohort_sha256=sha(Path(cfg["report"])/"cohort.json"),
        adapter_sha256=sha(adapter_dir(cfg)/f"adapter_fold{fold}.npy"),
        adapter_receipt_sha256=sha(adapter_dir(cfg)/f"adapter_fold{fold}.json"),
        condition_sha256=sha(Path(cfg["assets"])/"conditions"/f"{condition}.npy"))


def save_recovery(path,model,opt,scaler,rng,epoch,updates,identity):
    state=dict(stage="formal",checkpoint_format=2,model=model.state_dict(),
        optimizer=opt.state_dict(),scaler=scaler.state_dict(),epoch=epoch,
        optimizer_updates=updates,numpy_rng=rng.bit_generator.state,
        numpy_global_rng=np.random.get_state(),python_rng=random.getstate(),
        torch_rng=torch.get_rng_state(),
        cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else [],**identity)
    tmp=path.with_suffix(".tmp")
    torch.save(state,tmp);os.replace(tmp,path)


def restore_recovery(path,model,opt,scaler,rng,identity):
    ck=torch.load(path,map_location="cpu",weights_only=False)
    if ck.get("stage")!="formal" or ck.get("checkpoint_format")!=2:
        raise RuntimeError("Resume accepts only version-2 formal checkpoints; pilot weights are forbidden")
    if any(ck.get(k)!=v for k,v in identity.items()):
        raise RuntimeError("Resume input/model/condition identity mismatch")
    model.load_state_dict(ck["model"]);opt.load_state_dict(ck["optimizer"]);scaler.load_state_dict(ck["scaler"])
    rng.bit_generator.state=ck["numpy_rng"];np.random.set_state(ck["numpy_global_rng"])
    random.setstate(ck["python_rng"]);torch.set_rng_state(ck["torch_rng"])
    if ck["cuda_rng"]:torch.cuda.set_rng_state_all(ck["cuda_rng"])
    return ck["epoch"]+1,ck["optimizer_updates"]


def train(cfg,rows,fold,condition,resume=None):
    # Explicit user approval is required before an execution agent changes this
    # frozen flag. No CLI switch bypasses it and no pilot checkpoint is accepted.
    if not cfg["formal_training_authorized"]:
        raise RuntimeError("Stage 2 is NOT authorized. Four formal fits remain disabled.")
    clinical=json.loads((Path(cfg["report"])/"clinical_source_receipt.json").read_text())
    if (cfg.get("conditioning_scientific_gate")!="LIMITED_HISTORICAL_FIELDS" or
        clinical.get("training_scope_gate")!="LIMITED_HISTORICAL_FIELDS" or
        clinical.get("confirmed_adverse_dependency_found") is not False):
        raise RuntimeError("Clinical-source scientific gate blocked: target-PET / cross-fold input fitting or unaccepted claim scope")
    if not cfg.get("evaluation_laterality_gate_pass",False):
        raise RuntimeError("Anatomical ROI laterality gate failed; formal training blocked")
    if not cfg.get("evaluation_mri_mask_gate_pass",False):
        raise RuntimeError("MRI/mask binding gate failed; formal training blocked")
    if fold not in [1,2] or condition not in cfg["conditions"]:raise ValueError("fold/condition")
    train_rows=[r for r in rows if r["test_fold"]!=fold]
    out=Path(cfg["assets"])/"formal"/f"fold{fold}_{condition}"
    if resume:
        if Path(resume).resolve()!= (out/"recovery.pt").resolve():
            raise RuntimeError("Resume must use this formal task's recovery.pt")
        if not out.is_dir():raise RuntimeError("Missing formal task directory")
    else:out.mkdir(parents=True,exist_ok=False)
    identity=checkpoint_identity(cfg,fold,condition)
    # Match the core notebook's cached dataset at fold scale. Cache loading is
    # once per fit, not once per epoch, and occurs before allocating the model.
    required=len(train_rows)*3*160*192*160*4
    budget=cfg["training_cache_budget_gib"]*1024**3
    available=int(next(line.split()[1] for line in Path("/proc/meminfo").read_text().splitlines() if line.startswith("MemAvailable:")))*1024
    if required>budget or available<required+16*1024**3:
        raise RuntimeError("Insufficient RAM for approved fold cache; do not silently switch to repeated NFS reads")
    verify_caches(train_rows)
    load_start=time.monotonic()
    cached={r["ptid"]:get_data(r,device="cpu") for r in train_rows}
    print(json.dumps(dict(event="cache_loaded",subjects=len(train_rows),seconds=time.monotonic()-load_start)),flush=True)
    seed_all(cfg["seed"]+fold);model=new_model().cuda();opt=torch.optim.Adam(model.parameters(),lr=cfg["learning_rate"])
    scaler=torch.amp.GradScaler("cuda");ctx=contexts(cfg,condition)
    adapter=load_adapter(cfg,rows,fold)
    rng=np.random.default_rng(cfg["seed"]+fold)
    initial=tensor_hash(model.state_dict());start_epoch=0;updates=0
    if resume:start_epoch,updates=restore_recovery(resume,model,opt,scaler,rng,identity)
    write_json(out/("resume_start.json" if resume else "start.json"),dict(**identity,
        pid=os.getpid(),hardware=hardware(),initial_model_sha256=initial,
        start_epoch=start_epoch,optimizer_updates=updates,resume=str(resume) if resume else None,
        training_subjects=len(train_rows),outer_test_overlap=0,
        asset_root=str(cfg["assets"])))
    torch.cuda.reset_peak_memory_stats()
    for epoch in range(start_epoch,cfg["epochs"]):
        model.train();losses=[]
        epoch_start=time.monotonic()
        for iteration,j in enumerate(rng.permutation(len(train_rows)),1):
            r=train_rows[j];t=0 if epoch>=cfg["endpoint_epoch_zero_based"] else int(rng.integers(0,1000))
            started=time.monotonic()
            data={k:v.cuda() for k,v in cached[r["ptid"]].items()}
            losses.append(batch_step(model,opt,scaler,data,r,ctx[r["ptid"]].cuda(),adapter,t))
            updates+=1
            if iteration<=5 or iteration%100==0 or iteration==len(train_rows):
                event=dict(event="optimizer_step",epoch=epoch,iteration=iteration,optimizer_updates=updates,
                    ptid=r["ptid"],timestep=t,loss=losses[-1],amp_scale=scaler.get_scale(),step_seconds=time.monotonic()-started,
                    peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
                print(json.dumps(event),flush=True)
                if updates==5:write_json(out/"startup_5_updates.json",dict(**identity,pid=os.getpid(),**event))
        print(json.dumps(dict(event="epoch_complete",epoch=epoch,loss=float(np.mean(losses)),seconds=time.monotonic()-epoch_start)),flush=True)
        save_recovery(out/"recovery.pt",model,opt,scaler,rng,epoch,updates,identity)


@torch.inference_mode()
def infer(cfg,rows,checkpoint):
    if not cfg["formal_training_authorized"]:raise RuntimeError("Formal OOF is not authorized")
    ck=torch.load(checkpoint,map_location="cpu",weights_only=False)
    assert ck["stage"]=="formal" and ck["epoch"]==cfg["epochs"]-1
    fold,condition=ck["fold"],ck["condition"]
    assert ck["config_sha256"]==sha(Path(cfg["report"])/"config.json")
    assert ck["cohort_sha256"]==sha(Path(cfg["report"])/"cohort.json")
    ctx=contexts(cfg,condition);p=adapter_dir(cfg)/f"adapter_fold{fold}.npy"
    assert sha(p)==ck["adapter_sha256"]
    assert sha(Path(cfg["assets"])/"conditions"/f"{condition}.npy")==ck["condition_sha256"]
    adapter=load_adapter(cfg,rows,fold);verify_caches([r for r in rows if r["test_fold"]==fold])
    model=new_model().cuda().eval();model.load_state_dict(ck["model"])
    out=Path(cfg["assets"])/"oof"/condition/f"fold{fold}";out.mkdir(parents=True,exist_ok=False)
    index=[]
    for r in rows:
        if r["test_fold"]!=fold:continue
        data=get_data(r)
        with np.load(r["cache"]) as z:affine=z["affine"]
        for i,tracer in enumerate(TRACERS):
            if not r["has_"+tracer]:continue
            a=prediction(model,data,ctx[r["ptid"]].cuda(),adapter[i]);path=out/f"{r['ptid']}_{tracer}.nii.gz"
            nib.save(nib.Nifti1Image(a,affine),path)
            index.append(dict(ptid=r["ptid"],fold=fold,tracer=tracer,condition=condition,path=str(path),
                              sha256=sha(path),checkpoint_sha256=sha(checkpoint)))
    write_json(out/"index.json",index)


@email_on_error()
def main():
    p=argparse.ArgumentParser();p.add_argument("action",choices=["bundle","encode","features","adapt","pilot","train","infer"])
    p.add_argument("--config",type=Path,required=True);p.add_argument("--steps",type=int,default=36)
    p.add_argument("--fold",type=int);p.add_argument("--condition",choices=["Full","No-Scores"]);p.add_argument("--checkpoint",type=Path)
    p.add_argument("--resume",type=Path)
    a=p.parse_args();cfg=load_config(a.config);check_frozen(cfg)
    if a.action not in ["train","infer"] or cfg["formal_training_authorized"]:
        capture_execution(cfg,__file__,a.action)
    cohort_file=Path(cfg["report"])/"cohort.json"
    if a.action in ["encode","features"] and not cohort_file.exists():
        cohort_file=Path(cfg["report"])/"cohort_candidate.json"
    rows=json.loads(cohort_file.read_text()) if cohort_file.exists() else []
    if a.action in ["encode","features","adapt","pilot","train","infer"] and not rows:
        raise RuntimeError("Required frozen/candidate cohort is absent")
    if a.action in ["adapt","pilot","train","infer"]:rows=active_rows(cfg,rows)
    torch.set_num_threads(4)
    if a.action=="bundle":bundle(cfg)
    elif a.action=="encode":encode(cfg,rows)
    elif a.action=="features":features(cfg,rows)
    elif a.action=="adapt":adapt(cfg,rows)
    elif a.action=="pilot":pilot(cfg,rows,a.steps)
    elif a.action=="train":train(cfg,rows,a.fold,a.condition,a.resume)
    elif a.action=="infer":infer(cfg,rows,a.checkpoint)


if __name__=="__main__":
    main()
