"""Read-only audit step 1: compare Full vs Tracer-only conditioning at the model forward entry.

- Verifies file SHA-256 of both conditioning assets against run receipts.
- For sample PTIDs, compares the cached forward-entry context (persistent cache
  fdg_index/av45_index actually consumed by train/infer) with the Full
  conditions.pt tokens and with the tracer-only fixed context.
- Checks that Full patient embeddings vary across the whole cohort.
Writes audit_context_results.json next to this script. No training, no writes
outside this audit directory.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path("/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP")
sys.path.insert(0, str(REPO))

import torch  # noqa: E402

FULL_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020")
TRACER_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_tracer_only_assets/20261022")
CACHE = REPO / "results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup"
COHORT = json.loads((REPO / "reports/original_author_reproduction_20261020/cohort.json").read_text())
OUT = Path(__file__).resolve().parent / "audit_context_results.json"

def sha256_file(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 ** 2), b""):
            h.update(b)
    return h.hexdigest()


def tok_hash(t):
    return hashlib.sha256(t.detach().contiguous().numpy().tobytes()).hexdigest()


def cos(a, b):
    return float(torch.nn.functional.cosine_similarity(a.double(), b.double(), dim=0))


def main():
    from monai.data.utils import pickle_hashing

    full_conditions_path = FULL_ASSETS / "conditions.pt"
    control_path = TRACER_ASSETS / "tracer_only_conditions.pt"
    result = {
        "full_conditions_sha256": sha256_file(full_conditions_path),
        "tracer_only_conditions_sha256": sha256_file(control_path),
        "expected_full_conditions_sha256": "bbcd413100d8ece3e878acffc1969723d091f64c49c57c76b486bd474f84384a",
        "expected_tracer_only_conditions_sha256": "e1dfd6399d59168c3a7105bd941c4e834b547b3170bdaed3133b300792dc71ec",
    }
    full = torch.load(full_conditions_path, map_location="cpu", weights_only=False)
    control = torch.load(control_path, map_location="cpu", weights_only=False)
    patients, tracers = full["patient"], full["tracer"]
    empty, control_tracers = control["empty_patient"], control["tracer"]

    assert full["ptids"] == [r["name"] for r in COHORT]
    result["patient_shape"] = list(patients.shape)
    result["tracer_shape"] = list(tracers.shape)
    result["empty_patient_shape"] = list(empty.shape)

    result["tracer_fdg_full_vs_control_equal"] = bool(torch.equal(tracers[0], control_tracers[0]))
    result["tracer_av45_full_vs_control_equal"] = bool(torch.equal(tracers[1], control_tracers[1]))
    result["tracer_fdg_vs_av45_equal"] = bool(torch.equal(tracers[0], tracers[1]))

    hashes = [tok_hash(patients[i]) for i in range(patients.shape[0])]
    result["unique_patient_token_hashes"] = len(set(hashes))
    n = patients.shape[0]
    cos_same = [cos(patients[i], patients[(i + 1) % n]) for i in range(0, n, 37)]
    cos_far = [cos(patients[i], patients[(i + 928) % n]) for i in range(0, n, 37)]
    result["patient_token_pairwise_cosine_sample"] = {
        "adjacent_mean": sum(cos_same) / len(cos_same),
        "adjacent_min": min(cos_same),
        "adjacent_max": max(cos_same),
        "cross_fold_mean": sum(cos_far) / len(cos_far),
        "cross_fold_min": min(cos_far),
    }
    empty_h = tok_hash(empty[0])
    result["empty_patient_hash"] = empty_h
    result["empty_equals_any_full_patient_token"] = empty_h in set(hashes)
    cos_patient_empty = [cos(patients[i], empty[0]) for i in range(n)]
    result["patient_vs_empty_cosine"] = {
        "mean": sum(cos_patient_empty) / len(cos_patient_empty),
        "min": min(cos_patient_empty),
        "max": max(cos_patient_empty),
    }
    result["patient_token_l2norm_mean"] = float(patients.norm(dim=1).mean())
    result["empty_token_l2norm"] = float(empty[0].norm())

    sample_ptids = ["002_S_0295", "002_S_0413", "002_S_1261", "941_S_6854"]
    rows = []
    for row in COHORT:
        if row["name"] in sample_ptids:
            cache_file = CACHE / (pickle_hashing(row).decode() + ".pt")
            entry = torch.load(cache_file, map_location="cpu", weights_only=False)
            i = full["ptids"].index(row["name"])
            ctx_fdg = torch.cat([patients[i].unsqueeze(0), tracers[0].unsqueeze(0)], dim=0)
            ctx_av45 = torch.cat([patients[i].unsqueeze(0), tracers[1].unsqueeze(0)], dim=0)
            rows.append(
                {
                    "ptid": row["name"],
                    "fold": row["test_fold"],
                    "cache_file": str(cache_file),
                    "cache_keys": sorted(entry.keys()),
                    "cached_fdg_index_equals_conditions": bool(torch.equal(entry["fdg_index"], ctx_fdg)),
                    "cached_av45_index_equals_conditions": bool(torch.equal(entry["av45_index"], ctx_av45)),
                    "full_patient_token_hash": tok_hash(patients[i]),
                    "empty_patient_token_hash": empty_h,
                    "patient_vs_empty_max_abs_diff": float((patients[i] - empty[0]).abs().max()),
                    "patient_vs_empty_cosine": cos(patients[i], empty[0]),
                    "tracer_fdg_token_hash": tok_hash(tracers[0]),
                    "tracer_av45_token_hash": tok_hash(tracers[1]),
                    "control_context_fdg_hash": tok_hash(torch.cat([empty[0].unsqueeze(0), control_tracers[0].unsqueeze(0)], dim=0)),
                    "control_context_av45_hash": tok_hash(torch.cat([empty[0].unsqueeze(0), control_tracers[1].unsqueeze(0)], dim=0)),
                }
            )
    result["per_ptid_forward_entry_context"] = rows
    result["all_cached_contexts_match_conditions"] = all(
        r["cached_fdg_index_equals_conditions"] and r["cached_av45_index_equals_conditions"] for r in rows
    )
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
