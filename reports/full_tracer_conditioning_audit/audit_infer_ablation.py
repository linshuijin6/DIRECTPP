"""Read-only audit step 2: fixed-weight inference ablation on the trained Full checkpoints.

Uses the already-trained Full fold1/fold2 epoch-165 checkpoints, the same cached MRI
and tracer targets, and varies ONLY the patient token in the forward-entry context:
actual / empty / shuffled / actual-repeat (numerical noise control).
Also hooks cross-attention to_k/to_v to prove K/V depend on the patient token.
No training; writes only into this audit directory.
"""
import hashlib, json, sys
from pathlib import Path

REPO = Path("/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP")
sys.path.insert(0, str(REPO))
import torch
from experiments.original_author_reproduction import run as full

FULL_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020")
TRACER_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022")
CACHE = REPO / "results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup"
COHORT = json.loads((REPO / "reports/original_author_reproduction_20261020/cohort.json").read_text())
OUT = Path(__file__).resolve().parent / "audit_infer_ablation_results.json"

def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(8 * 1024 ** 2), b""):
            h.update(b)
    return h.hexdigest()

def load_batch(ptid):
    from monai.data.utils import pickle_hashing
    row = next(r for r in COHORT if r["name"] == ptid)
    e = torch.load(CACHE / (pickle_hashing(row).decode() + ".pt"), map_location="cpu", weights_only=False)
    return {k: (v.unsqueeze(0) if torch.is_tensor(v) else [v]) for k, v in e.items()}

def diff_stats(a, b, mask=None):
    d = (a - b)
    if mask is not None:
        dm = d[mask]
        return {
            "max_abs": float(d.abs().max()),
            "mean_abs": float(d.abs().mean()),
            "rmse": float((d ** 2).mean().sqrt()),
            "mask_mae": float(dm.abs().mean()),
            "mask_frac": float(mask.float().mean()),
        }
    return {"max_abs": float(d.abs().max()), "mean_abs": float(d.abs().mean()), "rmse": float((d ** 2).mean().sqrt())}

def main():
    full_conditions = torch.load(FULL_ASSETS / "conditions.pt", map_location="cpu", weights_only=False)
    control = torch.load(TRACER_ASSETS / "tracer_only_conditions.pt", map_location="cpu", weights_only=False)
    patients, tracers = full_conditions["patient"], full_conditions["tracer"]
    empty = control["empty_patient"][0]
    ptids = full_conditions["ptids"]

    results = {}
    for fold in (1, 2):
        ckpt = FULL_ASSETS / f"formal/fold{fold}/first_part_165.pth"
        ckpt_sha = sha256_file(ckpt)
        state = torch.load(ckpt, map_location="cpu", weights_only=False)
        model = full.new_model().cuda().eval()
        model.load_state_dict(state["model"])
        held_out = [r["name"] for r in COHORT if r["test_fold"] == fold]
        sample = [p for p in (["002_S_0729", "941_S_6854", "002_S_0295", "002_S_1261"] if fold == 1 else ["002_S_0295", "941_S_6345", "002_S_0413", "941_S_6962"]) if p in held_out][:3]
        fold_rows = {"checkpoint": str(ckpt), "checkpoint_sha256": ckpt_sha, "subjects": {}}
        for ptid in sample:
            batch = load_batch(ptid)
            i = ptids.index(ptid)
            mri = batch["mri"].cuda()
            mask = batch["mri"][0, 0] > 0.01
            mask_cuda = batch["mri"] > 0.01
            timestep = torch.tensor([0], device="cuda", dtype=torch.long)
            subj = {}
            for tracer in ("fdg", "av45"):
                target = batch[tracer]
                if torch.all((target == 0) | (target == 1)):
                    continue
                j = (i + 7) % len(ptids)
                ctx = {
                    "actual": torch.stack([patients[i], tracers[0 if tracer == "fdg" else 1]]).unsqueeze(0).cuda(),
                    "empty": torch.stack([empty, tracers[0 if tracer == "fdg" else 1]]).unsqueeze(0).cuda(),
                    "shuffled": torch.stack([patients[j], tracers[0 if tracer == "fdg" else 1]]).unsqueeze(0).cuda(),
                }
                outs = {}
                with torch.no_grad():
                    for name, c in ctx.items():
                        v = model(x=mri, timesteps=timestep, context=c)
                        outs[name] = torch.clamp(mri + v, 0, 1).float()
                    v = model(x=mri, timesteps=timestep, context=ctx["actual"])
                    outs["actual_repeat"] = torch.clamp(mri + v, 0, 1).float()
                subj[tracer] = {
                    "patient_cos_actual_vs_shuffled": float(torch.nn.functional.cosine_similarity(patients[i].double(), patients[j].double(), dim=0)),
                    "actual_vs_empty": diff_stats(outs["actual"], outs["empty"], mask_cuda),
                    "actual_vs_shuffled": diff_stats(outs["actual"], outs["shuffled"], mask_cuda),
                    "actual_vs_repeat_same_condition": diff_stats(outs["actual"], outs["actual_repeat"], mask_cuda),
                    "target_mae_actual": float((outs["actual"].cpu() - target).abs().mean()),
                    "target_mae_empty": float((outs["empty"].cpu() - target).abs().mean()),
                }
            fold_rows["subjects"][ptid] = subj
        results[f"fold{fold}"] = fold_rows
        del model
        torch.cuda.empty_cache()

    # Cross-attention K/V dependence: hook to_k/to_v of every attn2 (cross-attention).
    ckpt = FULL_ASSETS / "formal/fold1/first_part_165.pth"
    state = torch.load(ckpt, map_location="cpu", weights_only=False)
    model = full.new_model().cuda().eval()
    model.load_state_dict(state["model"])
    captured = {}
    hooks = []
    for name, module in model.named_modules():
        if name.endswith("attn2.to_k") or name.endswith("attn2.to_v"):
            hooks.append(module.register_forward_hook(
                lambda m, inp, out, n=name: captured.setdefault(n, []).append(out.detach().clone())))
    batch = load_batch("002_S_0729")
    i = ptids.index("002_S_0727" if False else "002_S_0729")
    mri = batch["mri"].cuda()
    ts = torch.tensor([0], device="cuda", dtype=torch.long)
    ctxA = torch.stack([patients[i], tracers[0]]).unsqueeze(0).cuda()
    ctxE = torch.stack([empty, tracers[0]]).unsqueeze(0).cuda()
    with torch.no_grad():
        model(x=mri, timesteps=ts, context=ctxA)
        model(x=mri, timesteps=ts, context=ctxE)
    for h in hooks:
        h.remove()
    kv = {}
    for n, outs in captured.items():
        if len(outs) == 2:
            kv[n] = {"max_abs_diff": float((outs[0] - outs[1]).abs().max()), "shape": list(outs[0].shape)}
    results["cross_attention_kv_fold1_e165_fdg"] = {
        "n_hooked_kv_layers": len(kv),
        "k_max_abs_diff_max": max(v["max_abs_diff"] for k, v in kv.items() if ".to_k" in k),
        "v_max_abs_diff_max": max(v["max_abs_diff"] for k, v in kv.items() if ".to_v" in k),
        "per_layer": kv,
    }
    OUT.write_text(json.dumps(results, indent=2) + "\n")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
